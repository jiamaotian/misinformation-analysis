#!/usr/bin/env python3
"""Local, streaming, auditable implementation of plan.md. Never edits source ZIPs."""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import datetime as dt
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import urlsplit
import zipfile

import duckdb
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

OVERALL = ['NEEDS_MORE_RATINGS', 'CURRENTLY_RATED_HELPFUL', 'CURRENTLY_RATED_NOT_HELPFUL']
HEADERS = {
    'batSignals': 'tweetId noteRequestFeedEligibleAtMillis apiSmallFeedEligibleAtMillis apiLargeFeedEligibleAtMillis apiXlFeedEligibleAtMillis sourceLinks suggestions',
    'notes': 'noteId noteAuthorParticipantId createdAtMillis tweetId classification believable harmful validationDifficulty misleadingOther misleadingFactualError misleadingManipulatedMedia misleadingOutdatedInformation misleadingMissingImportantContext misleadingUnverifiedClaimAsFact misleadingSatire notMisleadingOther notMisleadingFactuallyCorrect notMisleadingOutdatedButNotWhenWritten notMisleadingClearlySatire notMisleadingPersonalOpinion trustworthySources summary isMediaNote isCollaborativeNote',
    'ratings': 'noteId raterParticipantId createdAtMillis version agree disagree helpful notHelpful helpfulnessLevel helpfulOther helpfulInformative helpfulClear helpfulEmpathetic helpfulGoodSources helpfulUniqueContext helpfulAddressesClaim helpfulImportantContext helpfulUnbiasedLanguage notHelpfulOther notHelpfulIncorrect notHelpfulSourcesMissingOrUnreliable notHelpfulOpinionSpeculationOrBias notHelpfulMissingKeyPoints notHelpfulOutdated notHelpfulHardToUnderstand notHelpfulArgumentativeOrBiased notHelpfulOffTopic notHelpfulSpamHarassmentOrAbuse notHelpfulIrrelevantSources notHelpfulOpinionSpeculation notHelpfulNoteNotNeeded ratedOnTweetId ratingSourceBucketed suggestion suggestionId',
    'noteStatusHistory': 'noteId noteAuthorParticipantId createdAtMillis timestampMillisOfFirstNonNMRStatus firstNonNMRStatus timestampMillisOfCurrentStatus currentStatus timestampMillisOfLatestNonNMRStatus mostRecentNonNMRStatus timestampMillisOfStatusLock lockedStatus timestampMillisOfRetroLock currentCoreStatus currentExpansionStatus currentGroupStatus currentDecidedBy currentModelingGroup timestampMillisOfMostRecentStatusChange timestampMillisOfNmrDueToMinStableCrhTime currentMultiGroupStatus currentModelingMultiGroup timestampMinuteOfFinalScoringOutput timestampMillisOfFirstNmrDueToMinStableCrhTime timestampMillisAbovePcrhThreshold',
    'userEnrollment': 'participantId enrollmentState successfulRatingNeededToEarnIn timestampOfLastStateChange timestampOfLastEarnOut modelingPopulation modelingGroup numberOfTimesEarnedOut',
}
HEADERS = {k: v.split() for k, v in HEADERS.items()}
CATEGORIES = {
    'classification': ['MISINFORMED_OR_POTENTIALLY_MISLEADING', 'NOT_MISLEADING'],
    'believable': ['BELIEVABLE_BY_MANY', 'BELIEVABLE_BY_FEW'],
    'harmful': ['CONSIDERABLE_HARM', 'LITTLE_HARM'],
    'validationDifficulty': ['EASY', 'CHALLENGING'],
    'helpfulnessLevel': ['HELPFUL', 'SOMEWHAT_HELPFUL', 'NOT_HELPFUL'],
    'ratingSourceBucketed': ['DEFAULT', 'POPULATION_SAMPLED'],
    'enrollmentState': ['newUser', 'earnedIn', 'earnedOutAcknowledged', 'atRisk', 'removed', 'apiEarnedIn'],
    'modelingPopulation': ['CORE', 'EXPANSION', 'EXPANSION_PLUS'],
}
for _c in ['currentStatus', 'lockedStatus']:
    CATEGORIES[_c] = OVERALL
for _c in ['firstNonNMRStatus', 'mostRecentNonNMRStatus']:
    CATEGORIES[_c] = OVERALL[1:]
for _c in ['currentCoreStatus', 'currentExpansionStatus', 'currentGroupStatus', 'currentMultiGroupStatus']:
    CATEGORIES[_c] = OVERALL + ['FIRM_REJECT', 'NEEDS_YOUR_HELP']
INTS = {'version', 'currentModelingGroup', 'currentModelingMultiGroup', 'timestampMinuteOfFinalScoringOutput', 'successfulRatingNeededToEarnIn', 'modelingGroup', 'numberOfTimesEarnedOut'}
IDS = {'noteId', 'tweetId', 'ratedOnTweetId', 'suggestionId'}
PARTICIPANTS = {'noteAuthorParticipantId', 'raterParticipantId', 'participantId'}
TEXT = {'summary', 'suggestion', 'sourceLinks', 'suggestions'}
NULL_MINUS_ONE = {'tweetId', 'ratedOnTweetId', 'suggestionId'}
TIME_MINUS_ONE = {'timestampMillisOfMostRecentStatusChange', 'timestampMillisOfNmrDueToMinStableCrhTime', 'timestampMillisOfFirstNmrDueToMinStableCrhTime'}
RULES_URL = 'https://raw.githubusercontent.com/twitter/communitynotes/main/documentation/under-the-hood/download-data.md'


def qi(s):
    return '"' + s.replace('"', '""') + '"'


def qs(s):
    return "'" + str(s).replace("'", "''") + "'"


def kind(c):
    if c in IDS:
        return 'id'
    if c in PARTICIPANTS:
        return 'participant'
    if c in INTS:
        return 'integer'
    if 'Millis' in c or c.startswith('timestampOf'):
        return 'timestamp'
    if c in TEXT:
        return 'text'
    if c in CATEGORIES or c == 'currentDecidedBy':
        return 'category'
    return 'boolean'


def integer_expr(c):
    s = qi(c)
    if c == 'modelingGroup':
        return f"CASE WHEN regexp_full_match({s}, '[0-9]+(\\.0+)?') THEN try_cast({s} AS BIGINT) END"
    return f"CASE WHEN regexp_full_match({s}, '-?[0-9]+') THEN try_cast({s} AS BIGINT) END"


def value_expr(c):
    s, k = qi(c), kind(c)
    if k == 'boolean':
        return f"CASE {s} WHEN '0' THEN false WHEN '1' THEN true ELSE NULL END"
    if k == 'id':
        return f"CASE WHEN regexp_full_match({s}, '[1-9][0-9]*') THEN {s} END"
    if k == 'participant':
        return f"nullif({s}, '')"
    if k == 'integer':
        v = integer_expr(c)
        return f"CASE WHEN ({v}) {'>' if c == 'version' else '>='} 0 THEN ({v}) END"
    if k == 'timestamp':
        return integer_expr(c)  # Preserve the signed source epoch and known sentinels.
    if k == 'category':
        return f"nullif(trim({s}), '')"
    return s  # Text is preserved exactly; trimming is a separate companion.


def inverse_expr(c, prefix=''):
    s = prefix + qi(c)
    if kind(c) == 'boolean':
        return f"CASE WHEN {s} IS NULL THEN '' WHEN {s} THEN '1' ELSE '0' END"
    return f"coalesce(cast({s} AS VARCHAR), '')"


def source_expr(c, prefix=''):
    return f"coalesce(map_extract_value({prefix}_raw_values, {qs(c)}), {inverse_expr(c, prefix)})"


def time_expr(c):
    v = value_expr(c)
    if c == 'timestampMillisAbovePcrhThreshold':
        v = f"CASE WHEN ({v}) <> -1 THEN abs(cast(({v}) AS HUGEINT)) END"
    elif c == 'timestampOfLastEarnOut':
        v = f"CASE WHEN ({v}) <> 1 THEN ({v}) END"
    # Avoid conversion exceptions; units are unchanged in the original column.
    return f"CASE WHEN ({v}) BETWEEN 1 AND 253402300799999 THEN epoch_ms(cast(({v}) AS BIGINT))::TIMESTAMPTZ END"


def issue_rules(group):
    """All rules are evaluated on raw strings, BEFORE applying a treatment."""
    rules = []
    def add(c, code, condition, action='retain original; leave unusable typed value null; unresolved'):
        rules.append((c, code, condition, action))
    for c in HEADERS[group]:
        s, k, v = qi(c), kind(c), value_expr(c)
        if k == 'id':
            sent = f" AND {s} <> '-1'" if c in NULL_MINUS_ONE else ''
            add(c, 'invalid_identifier', f"({s} = '' OR NOT regexp_full_match({s}, '[1-9][0-9]*')){sent}")
        elif k == 'participant':
            add(c, 'participant_format', f"NOT regexp_full_match({s}, '[A-F0-9]{{64}}')", 'retain original identifier; unresolved; never recase or pad')
        elif k == 'boolean':
            add(c, 'invalid_boolean', f"{s} NOT IN ('','0','1')")
        elif k == 'integer':
            add(c, 'invalid_integer', f"{s} <> '' AND ({v}) IS NULL")
            if c == 'version':
                add(c, 'unknown_version', f"({v}) NOT IN (1,2)", 'retain version; unresolved; do not harmonize')
        elif k == 'category' and c in CATEGORIES:
            known = ','.join(qs(x) for x in CATEGORIES[c])
            add(c, 'unknown_category', f"trim({s}) <> '' AND trim({s}) NOT IN ({known})", 'retain unknown category; unresolved; do not remap')
        elif k == 'timestamp':
            allowed = ['-1'] if c in TIME_MINUS_ONE or 'EligibleAtMillis' in c else []
            if c == 'timestampOfLastEarnOut':
                allowed = ['1']
            if c == 'timestampMillisAbovePcrhThreshold':
                cond = f"({v}) IS NULL OR ({v}) = 0 OR abs(cast(({v}) AS HUGEINT)) > 253402300799999"
            else:
                cond = f"({v}) IS NULL OR ({v}) <= 0 OR ({v}) > 253402300799999"
            exc = ' AND '+s+' NOT IN ('+','.join(qs(x) for x in allowed)+')' if allowed else ''
            add(c, 'invalid_timestamp', f"{s} <> ''{exc} AND ({cond})", 'retain raw epoch; unavailable UTC companion; unresolved')
            add(c, 'suspicious_timestamp_range', f"({time_expr(c)}) IS NOT NULL AND (({time_expr(c)}) < TIMESTAMPTZ '2021-01-01 00:00:00+00' OR ({time_expr(c)}) > CAST($run_time AS TIMESTAMPTZ))", 'retain timestamp and UTC value; unresolved; inspection time is not an analysis cutoff')
            if c in {'timestampMillisOfNmrDueToMinStableCrhTime', 'timestampMillisOfFirstNmrDueToMinStableCrhTime'}:
                add(c, 'unverified_minus_one_semantics', f"{s} = '-1'", 'retain -1; UTC companion null; meaning unresolved')
        if c in {'summary', 'suggestion'}:
            cond = f"trim({s}) = ''" if c == 'summary' else f"{s} <> '' AND trim({s}) = ''"
            add(c, 'blank_text', cond, 'retain original text; trimmed companion blank; unresolved')
    if group == 'notes':
        add('classification', 'missing_classification', "trim(classification) = ''", 'retain note; classification unknown; no imputation')
        misleading = ' OR '.join(f'{qi(c)} = \'1\'' for c in HEADERS[group] if c.startswith('misleading'))
        notmisleading = ' OR '.join(f'{qi(c)} = \'1\'' for c in HEADERS[group] if c.startswith('notMisleading'))
        add('classification', 'classification_reason_disagreement', f"(classification = 'NOT_MISLEADING' AND ({misleading})) OR (classification = 'MISINFORMED_OR_POTENTIALLY_MISLEADING' AND ({notmisleading}))", 'retain category and reason flags; unresolved')
    if group == 'ratings':
        for a,b in [('agree','disagree'), ('helpful','notHelpful')]:
            add(a, 'contradictory_binary_pair', f'{qi(a)}=\'1\' AND {qi(b)}=\'1\'', 'retain both responses; unresolved; no imputation')
        add('helpfulnessLevel', 'version_level_mismatch', "(version='1' AND helpfulnessLevel<>'') OR (version='2' AND helpfulnessLevel='')", 'retain original version and response; unresolved')
    if group == 'noteStatusHistory':
        for a,b in [('timestampMillisOfFirstNonNMRStatus','firstNonNMRStatus'),('timestampMillisOfLatestNonNMRStatus','mostRecentNonNMRStatus'),('timestampMillisOfStatusLock','lockedStatus')]:
            add(a, 'status_time_pair_mismatch', f"({qi(a)}='') <> ({qi(b)}='')", 'retain both fields; unresolved')
        add('timestampMillisOfFirstNonNMRStatus', 'resolved_missing_history', "currentStatus IN ('CURRENTLY_RATED_HELPFUL','CURRENTLY_RATED_NOT_HELPFUL') AND timestampMillisOfFirstNonNMRStatus=''", 'retain current status; first-resolution time unavailable; no invented event')
        for c in HEADERS[group]:
            if kind(c) == 'timestamp' and c != 'createdAtMillis':
                add(c, 'event_before_creation', f"({time_expr(c)}) < ({time_expr('createdAtMillis')})", 'retain original; flag event timing; exclude invalid elapsed time only with documented metric denominator')
        add('timestampMillisOfLatestNonNMRStatus', 'latest_before_first', f"({time_expr('timestampMillisOfLatestNonNMRStatus')}) < ({time_expr('timestampMillisOfFirstNonNMRStatus')})", 'retain both; unresolved')
    if group == 'userEnrollment':
        add('timestampOfLastEarnOut', 'earnout_count_disagreement', "(timestampOfLastEarnOut='1') <> (numberOfTimesEarnedOut='0')", 'retain both; never-earned-out claim marked contradictory; unresolved')
    return rules


def connection(output):
    c = duckdb.connect()
    c.execute("SET threads=2; SET memory_limit='3GB'; SET TimeZone='UTC'; SET preserve_insertion_order=true")
    c.execute(f"SET temp_directory={qs(output / 'scratch')}; SET max_temp_directory_size='8GB'")
    return c


def emit(event, **kw):
    print(json.dumps({'event':event, **kw}, ensure_ascii=False, default=str), flush=True)


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str)+'\n')
    tmp.replace(path)


def disk_guard(path):
    if shutil.disk_usage(path).free < 3 * 1024**3:
        raise RuntimeError('Less than 3 GiB free: stopping safely; source files unchanged.')


def output_is_isolated(path):
    repo=Path(__file__).resolve().parents[1]
    if not path.resolve().is_relative_to(repo):
        return True
    result=subprocess.run(['git','check-ignore','--quiet',str(path/'cleaned'/'probe.parquet')],cwd=repo,check=False)
    return result.returncode==0


def batches(path, group, limit=None):
    with zipfile.ZipFile(path) as z:
        members = [m for m in z.namelist() if not m.endswith('/')]
        if len(members) != 1:
            raise ValueError(f'Unexpected ZIP members: {path.name}')
        member = members[0]
        with z.open(member) as f:
            header = f.readline().decode('utf-8-sig').rstrip('\r\n').split('\t')
            if header != HEADERS[group]:
                raise ValueError(f'Schema drift in {path.name}: {header}')
            # Fail closed on malformed width/encoding; never skip or silently renumber.
            reader = pacsv.open_csv(f,
                read_options=pacsv.ReadOptions(column_names=header, block_size=16*1024*1024, use_threads=False),
                parse_options=pacsv.ParseOptions(delimiter='\t', quote_char=False, ignore_empty_lines=False),
                convert_options=pacsv.ConvertOptions(column_types={c:pa.string() for c in header}, strings_can_be_null=False))
            offset = 0
            for b in reader:
                if limit is not None:
                    if offset >= limit:
                        break
                    b = b.slice(0, min(b.num_rows, limit-offset))
                yield b, member, offset
                offset += b.num_rows


def manifest(raw):
    out = []
    for group in HEADERS:
        paths = sorted(raw.glob(group+'-*.zip'))
        if not paths:
            raise ValueError(f'Missing dataset {group}')
        for p in paths:
            h = hashlib.sha256()
            with p.open('rb') as f:
                for chunk in iter(lambda:f.read(8*1024*1024), b''):
                    h.update(chunk)
            s = p.stat()
            out.append({'path':str(p), 'group':group, 'size':s.st_size, 'mtime_ns':s.st_mtime_ns, 'sha256':h.hexdigest()})
    return out


def profile(c, files, output, run_time, limit):
    """Complete the entire source profile before any cleaning is published."""
    results = {}
    for item in files:
        p, group = Path(item['path']), item['group']
        report_path = output/'reports'/'profile'/f'{p.stem}.json'
        if report_path.exists():
            results[p.name] = json.loads(report_path.read_text()); continue
        total = 0
        columns = {n:collections.Counter() for n in HEADERS[group]}
        cats = {n:collections.Counter() for n in HEADERS[group] if kind(n) in {'category','boolean'} or n=='version'}
        issues = collections.Counter()
        rules = issue_rules(group)
        expressions = ['count(*)']
        for n in HEADERS[group]:
            s = qi(n)
            expressions += [f"count(*) FILTER (WHERE {s}='')", f"count(*) FILTER (WHERE {s}<>trim({s}))", f"count(*) FILTER (WHERE {s}='-1')", f"max(length({s}))"]
        expressions += [f'count(*) FILTER (WHERE {cond})' for _,_,cond,_ in rules]
        last = time.monotonic()
        for b, member, offset in batches(p, group, limit):
            c.register('raw', b)
            params = {'run_time':run_time} if '$run_time' in ','.join(expressions) else {}
            vals = c.execute('SELECT '+','.join(expressions)+' FROM raw', params).fetchone()
            total += vals[0]; j = 1
            for n in HEADERS[group]:
                for name in ['blank','surrounding_whitespace','minus_one']:
                    columns[n][name] += vals[j]; j += 1
                columns[n]['max_characters'] = max(columns[n]['max_characters'], vals[j] or 0); j += 1
            for n,code,_,_ in rules:
                issues[n+':'+code] += vals[j]; j+=1
            for n in cats:
                for v,count in c.execute(f'SELECT {qi(n)},count(*) FROM raw GROUP BY 1').fetchall():
                    cats[n][v] += count
            if time.monotonic()-last > 20:
                emit('profile_progress', file=p.name, rows=total); last=time.monotonic()
        r = {'file':p.name, 'dataset':group, 'scope':'full' if limit is None else f'first {limit} per file', 'rows':total, 'columns':columns, 'categories':cats, 'flag_counts':{k:v for k,v in issues.items() if v}, 'malformed_rows':0, 'rows_changed':0, 'rows_dropped':0}
        save(report_path,r); results[p.name]=r
        emit('profile_file_complete', file=p.name, rows=total, flags=sum(issues.values()), changed=0, dropped=0)
    save(output/'reports'/'01_profile.json', results)
    emit('stage_complete', stage='full_source_profile', rows=sum(x['rows'] for x in results.values()), changed=0, dropped=0)
    return results


FLAG_SCHEMA = pa.schema([(x,pa.string()) for x in ['dataset','source_file','source_member']] + [('source_row',pa.int64())] + [(x,pa.string()) for x in ['column','rule','original_value','decision']])


class Sink:
    def __init__(self, path):
        self.path, self.writer, self.rows = path, None, 0
        path.parent.mkdir(parents=True,exist_ok=True)
    def write(self, table):
        if not table.num_rows:
            return
        if self.writer is None:
            self.writer = pq.ParquetWriter(self.path, table.schema, compression='zstd', compression_level=3)
        self.writer.write_table(table, row_group_size=131072)
        self.rows += table.num_rows
    def close(self):
        if self.writer:
            self.writer.close()
            self.writer = None


def valid_url(s):
    try:
        u=urlsplit(s)
        return u.scheme in {'http','https'} and bool(u.hostname) and not re.search(r'\s',s)
    except ValueError:
        return False


def nested_requests(b, p, member, offset):
    """Return explicit flags first; unknown object keys remain in the parsed JSON."""
    links, suggestions, flags = [], [], []
    for i,(source,raw) in enumerate(zip(b.column('sourceLinks').to_pylist(), b.column('suggestions').to_pylist())):
        def flag(col,rule,original,decision):
            flags.append(('batSignals',p.name,member,offset+i+1,col,rule,original,decision))
        tokens = [x.strip() for x in source.split(',')] if source else []
        if any(not valid_url(x) for x in tokens):
            flag('sourceLinks','invalid_source_url',source,'retain malformed URL tokens unchanged; unresolved; no prefix repair')
        links.append(tokens)
        try:
            value = json.loads(raw)
            if not isinstance(value,list):
                raise ValueError('not a list')
            for obj in value:
                if not isinstance(obj,dict):
                    flag('suggestions','nonobject_suggestion',raw,'preserve original element; unresolved'); continue
                sid = obj.get('suggestion_id')
                if (isinstance(sid,int) and not isinstance(sid,bool) and sid>0) or (isinstance(sid,str) and re.fullmatch('[1-9][0-9]*',sid)):
                    obj['suggestion_id']=str(sid)
                else:
                    flag('suggestions','invalid_nested_id',raw,'retain original nested ID; unresolved')
                if not isinstance(obj.get('suggestion'),str):
                    flag('suggestions','invalid_nested_text',raw,'retain original nested text; unresolved')
                url=obj.get('source_link')
                if not isinstance(url,str) or (url and not valid_url(url)):
                    flag('suggestions','invalid_nested_url',raw,'retain original source_link; unresolved; no repair')
            suggestions.append(json.dumps(value,ensure_ascii=False,separators=(',',':')))
        except (ValueError,TypeError):
            flag('suggestions','invalid_json_array',raw,'retain original JSON text; parsed companion null; unresolved')
            suggestions.append(None)
    table=pa.Table.from_arrays([pa.array([x[j] for x in flags], type=f.type) for j,f in enumerate(FLAG_SCHEMA)],schema=FLAG_SCHEMA)
    return pa.array(links,type=pa.list_(pa.string())),pa.array(suggestions,type=pa.string()),table


def flag_query(group, rules):
    entries=[]
    for col,code,cond,decision in rules:
        entries.append(f"CASE WHEN ({cond}) THEN struct_pack(\"column\":={qs(col)}, rule:={qs(code)}, original_value:={qi(col)}, decision:={qs(decision)}) END")
    return f"SELECT {qs(group)} AS dataset, _source_file AS source_file, _source_member AS source_member, _source_row AS source_row, f.column, f.rule, f.original_value, f.decision FROM (SELECT *,unnest(list_filter([{','.join(entries)}],x->x IS NOT NULL)) f FROM raw)"


def clean_query(group, profile=None):
    casts=[f'{value_expr(n)} AS {qi(n)}' for n in HEADERS[group]]
    source_map=[]
    changes=[]
    for n in HEADERS[group]:
        v=value_expr(n)
        inv=f"CASE WHEN ({v}) IS NULL THEN '' WHEN ({v}) THEN '1' ELSE '0' END" if kind(n)=='boolean' else f"coalesce(cast(({v}) AS VARCHAR),'')"
        needs_override=kind(n) not in {'text','participant'}
        if profile is not None:
            issues=profile.get('flag_counts',{})
            stats=profile.get('columns',{}).get(n,{})
            if kind(n)=='boolean' and not issues.get(n+':invalid_boolean',0):needs_override=False
            if kind(n)=='category' and stats.get('surrounding_whitespace')==0:needs_override=False
            if kind(n)=='id' and not issues.get(n+':invalid_identifier',0) and stats.get('minus_one')==0:needs_override=False
            if n=='version' and set(profile.get('categories',{}).get(n,{})) <= {'1','2',''}:needs_override=False
        if needs_override:
            source_map.append(f"CASE WHEN {qi(n)} <> ({inv}) THEN struct_pack(key:={qs(n)},value:={qi(n)}) END")
        change='true' if kind(n) in {'boolean','integer','timestamp'} else f"{qi(n)} <> coalesce(cast(({v}) AS VARCHAR),'') OR ({qi(n)}='' AND ({v}) IS NULL)"
        if kind(n)=='text':
            change=f"{qi(n)} <> trim({qi(n)})" if n in {'summary','suggestion'} else 'false'
        changes.append(f"CASE WHEN {change} THEN {1 << HEADERS[group].index(n)}::UBIGINT ELSE 0::UBIGINT END")
    companions=[]
    for n in HEADERS[group]:
        if kind(n)=='timestamp':
            companions.append(f'{time_expr(n)} AS {qi(n+"_utc")}')
            if 'EligibleAtMillis' in n:
                companions.append(f"CASE WHEN {qi(n)}='-1' THEN 'ineligible' WHEN ({time_expr(n)}) IS NOT NULL THEN 'eligible' ELSE 'unknown' END AS {qi(n+'_state')}")
        if n in {'summary','suggestion'}:
            companions.append(f'trim({qi(n)}) AS {qi(n+"_trimmed")}')
    if group=='noteStatusHistory':
        n=qi('timestampMillisAbovePcrhThreshold');v=value_expr('timestampMillisAbovePcrhThreshold')
        companions.append(f"CASE WHEN {n}='' THEN 'no_recorded_event' WHEN {n}='-1' THEN 'cleared' WHEN ({time_expr('timestampMillisAbovePcrhThreshold')}) IS NULL THEN 'invalid' WHEN ({v})>0 THEN 'above_threshold' WHEN ({v}) < -1 THEN 'no_longer_above' ELSE 'invalid' END AS pcrh_state")
    if group=='userEnrollment':
        companions.append("CASE WHEN timestampOfLastEarnOut='1' AND numberOfTimesEarnedOut='0' THEN true WHEN timestampOfLastEarnOut<>'1' AND try_cast(numberOfTimesEarnedOut AS BIGINT)>0 THEN false ELSE NULL END AS never_earned_out_consistent")
    entries='['+','.join(source_map)+']' if source_map else '[]::STRUCT(key VARCHAR,value VARCHAR)[]'
    return 'SELECT '+','.join(casts+companions+['_source_file','_source_member','_source_row',f"map_from_entries(list_filter({entries},x->x IS NOT NULL)) AS _raw_values",'('+ ' + '.join(changes)+') AS _changed_mask'] )+' FROM raw'


def check_contract(output):
    contract = hashlib.sha256(json.dumps({'columns':{g:[clean_query(g),issue_rules(g)] for g in HEADERS},'nested_rules':inspect.getsource(nested_requests),'reader':inspect.getsource(batches)},sort_keys=True).encode()).hexdigest()
    contract_path=output/'reports'/'normalization_contract.json'
    if contract_path.exists() and json.loads(contract_path.read_text())['sha256']!=contract:
        raise ValueError('Normalization rules changed; use a new output directory instead of mixing versions.')
    if not contract_path.exists():
        save(contract_path,{'sha256':contract,'meaning':'Exact normalization SQL and validation conditions used for all partitions.'})


def transform(c, files, profiles, output, run_time, limit):
    check_contract(output)
    for item in files:
        group,p=item['group'],Path(item['path'])
        report_path=output/'reports'/'transform'/f'{p.stem}.json'
        if report_path.exists():
            emit('transform_resumed', file=p.name); continue
        disk_guard(output)
        clean_path=output/'cleaned'/group/(p.stem+'.parquet')
        flags_path=output/'audit'/(p.stem+'-flags.parquet')
        cs,fs=Sink(clean_path.with_suffix('.partial')),Sink(flags_path.with_suffix('.partial'))
        all_rules=issue_rules(group)
        # The completed full profile already flags zero/nonzero anomalies before treatment.
        # Re-evaluate only nonzero rules; the unchanged-source manifest guards this shortcut.
        preflags=profiles[p.name].get('flag_counts')
        rules=[r for r in all_rules if preflags is None or preflags.get(r[0]+':'+r[1],0)]
        fq=flag_query(group,rules) if rules else None
        changed=collections.Counter();nulls=collections.Counter();flag_counts=collections.Counter();mapping=collections.Counter()
        changed_rows=0;flagged_rows=0;last=time.monotonic();roundtrip_checked=0;companions=collections.Counter()
        try:
            for b,member,offset in batches(p,group,limit):
                b=b.append_column('_source_file',pa.array([p.name]*b.num_rows)).append_column('_source_member',pa.array([member]*b.num_rows)).append_column('_source_row',pa.array(range(offset+1,offset+b.num_rows+1),type=pa.int64()))
                c.register('raw',b)
                params={'run_time':run_time} if fq and '$run_time' in fq else {}
                ft=c.execute(fq,params).to_arrow_table() if fq else pa.Table.from_batches([],schema=FLAG_SCHEMA)
                links=suggestions=None
                if group=='batSignals':
                    links,suggestions,nt=nested_requests(b,p,member,offset)
                    ft=pa.concat_tables([ft.cast(FLAG_SCHEMA),nt])
                # Write the flags before evaluating/publishing cleaned values.
                fs.write(ft)
                if ft.num_rows:
                    c.register('flag_batch',ft)
                    flagged_rows+=c.execute('SELECT count(distinct source_row) FROM flag_batch').fetchone()[0]
                    for col,rule,n in c.execute('SELECT "column",rule,count(*) FROM flag_batch GROUP BY 1,2').fetchall():flag_counts[col+':'+rule]+=n
                t=c.execute(clean_query(group,profiles[p.name] if 'columns' in profiles[p.name] else None)).to_arrow_table()
                if links is not None:
                    t=t.append_column('sourceLinks_list',links).append_column('suggestions_parsed',suggestions)
                c.register('clean_batch',t)
                # Verify all original tokens in a deterministic first/last-row batch sample.
                # Complete source provenance + sparse exceptions remain available for every row.
                sample_rows=sorted(set([offset+1,offset+b.num_rows]))
                mismatch=' OR '.join(f'({source_expr(n,"t.")}) IS DISTINCT FROM r.{qi(n)}' for n in HEADERS[group])
                bad=c.execute(f'SELECT count(*) FROM clean_batch t JOIN raw r USING (_source_row) WHERE t._source_row IN ({",".join(map(str,sample_rows))}) AND ({mismatch})').fetchone()[0]
                if bad:raise AssertionError('Original-value reconstruction failed')
                roundtrip_checked+=len(sample_rows)
                change_counts=c.execute('SELECT '+','.join(f'count(*) FILTER(WHERE (_changed_mask & {1<<i})<>0)' for i,n in enumerate(HEADERS[group]))+', count(*) FILTER(WHERE _changed_mask<>0) FROM clean_batch').fetchone()
                for n,count in zip(HEADERS[group],change_counts):changed[n]+=count
                changed_rows+=change_counts[-1]
                for n in t.column_names:nulls[n]+=t.column(n).null_count
                for n in t.column_names:
                    if n not in HEADERS[group] and not n.startswith('_'):companions[n]+=t.num_rows-t.column(n).null_count
                # Explicit mapping counts, including numeric and categorical sentinel handling.
                for n in HEADERS[group]:
                    if kind(n) in {'boolean','category'} or n in NULL_MINUS_ONE or kind(n)=='timestamp':
                        if kind(n) in {'boolean','category'}:
                            rows=c.execute(f'SELECT {qi(n)},cast(({value_expr(n)}) AS VARCHAR),count(*) FROM raw GROUP BY 1,2').fetchall()
                        else:
                            rows=c.execute(f"SELECT {qi(n)},cast(({value_expr(n)}) AS VARCHAR),count(*) FROM raw WHERE {qi(n)} IN ('','-1','0','1') GROUP BY 1,2").fetchall()
                        for old,new,count in rows:mapping[json.dumps([n,old,new])]+=count
                cs.write(t);disk_guard(output)
                if time.monotonic()-last>20:
                    emit('transform_progress',file=p.name,rows=cs.rows,flag_events=fs.rows);last=time.monotonic()
            cs.close();fs.close()
            assert cs.rows==profiles[p.name]['rows'],(p.name,cs.rows,profiles[p.name]['rows'])
            cs.path.replace(clean_path)
            if fs.path.exists():fs.path.replace(flags_path)
            r={'file':p.name,'dataset':group,'stage':'typing_sentinels_normalization','rows_before':cs.rows,'rows_after':cs.rows,'source_columns':len(HEADERS[group]),'output_columns':len(t.column_names),'changed_rows':changed_rows,'changed_cells':sum(changed.values()),'changed_by_column':changed,'change_count_definition':'Source-column type/value transformations; separately listed companion columns are additions, not overwrites.','added_companion_nonnull_counts':companions,'original_token_roundtrip_rows_checked':roundtrip_checked,'roundtrip_scope':'First and last row of every streamed batch; not a full row-by-row roundtrip test.','null_after':nulls,'flag_events':fs.rows,'distinct_flagged_rows':flagged_rows,'flag_counts':flag_counts,'value_mappings':[{'column':json.loads(k)[0],'before':json.loads(k)[1],'after':json.loads(k)[2],'count':v} for k,v in mapping.items()],'rows_dropped':0,'metric_exclusions':0,'unresolved':'All anomaly flags retained; no speculative repairs. Known sentinel mappings follow rules.json.'}
            save(report_path,r)
            emit('stage_complete',stage='typing_sentinels_normalization',file=p.name,rows_before=cs.rows,rows_after=cs.rows,changed_rows=changed_rows,flag_events=fs.rows,dropped=0)
        finally:
            cs.close();fs.close()


def transform_worker(item, profiles, output, run_time, limit):
    c=connection(output)
    c.execute("SET threads=1; SET memory_limit='2GB'")
    c.execute(f"SET temp_directory={qs(output/'scratch'/item['group']/Path(item['path']).stem)}")
    try:
        transform(c,[item],profiles,output,run_time,limit)
    finally:
        c.close()


def write_rules(output,run_time):
    rules={}
    for group,columns in HEADERS.items():
        rules[group]={}
        for n in columns:
            rules[group][n]={'kind':kind(n),'sql':value_expr(n),'reconstruction':source_expr(n),'mapping':'0=false;1=true;blank=null;other=flag then derived null' if kind(n)=='boolean' else 'See SQL and value_mappings in transformation report','datetime_sql':time_expr(n) if kind(n)=='timestamp' else None,'unit':'milliseconds since Unix epoch -> UTC companion; signed source value retained' if kind(n)=='timestamp' else 'epoch minutes retained, not converted' if n=='timestampMinuteOfFinalScoringOutput' else 'not applicable'}
        rules[group]['validation_rules']=[{'column':n,'rule':code,'condition':cond,'decision':action} for n,code,cond,action in issue_rules(group)]
    save(output/'reports'/'rules.json',{'inspection_time_utc':run_time,'source_documentation':RULES_URL,'columns':rules,'normalization_sql':{g:clean_query(g) for g in HEADERS},'change_mask_order':HEADERS,'text':'Original text retained; *_trimmed is trim(original), internal whitespace unchanged. sourceLinks_list splits comma and trims each token; suggestions_parsed parses JSON and converts valid nested IDs to strings; raw JSON retained.','audit':'_changed_mask records per-row type/value conversions: bit i corresponds to source header position i (zero-based). _raw_values stores only non-reconstructible original tokens. Other originals are losslessly reconstructible using column-specific inverse expressions. No raw TSV is copied. Full profile flags are evaluated before conversion; nonzero flags are materialized before cleaned values.','denominators':'No analytic cohort or cutoff selected; no metrics computed in normalization.'})


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--raw-dir',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,required=True)
    ap.add_argument('--stage',choices=['profile','transform','validate','all'],default='all')
    ap.add_argument('--workers',type=int,choices=[1,2],default=2,help='At most two independent partition transformations; validation stays sequential')
    ap.add_argument('--limit-per-file',type=int,help='Testing only; outputs explicitly marked as sampled')
    args=ap.parse_args();raw=args.raw_dir.resolve();out=args.output_dir.resolve()
    if out==raw or raw in out.parents or out in raw.parents:
        ap.error('Output must be separate from the source tree')
    if not output_is_isolated(out):
        ap.error('Output inside this repository must be Git-ignored; use data/cleaning_run')
    out.mkdir(parents=True,exist_ok=True);disk_guard(out)
    mp=out/'manifest.json'
    if mp.exists():
        m=json.loads(mp.read_text())
        if m['raw_dir']!=str(raw) or m['limit_per_file']!=args.limit_per_file:raise ValueError('Resume configuration differs')
        for f in m['files']:
            s=Path(f['path']).stat()
            if s.st_size!=f['size'] or s.st_mtime_ns!=f['mtime_ns']:raise ValueError('Source changed since manifest')
    else:
        emit('fingerprinting_sources')
        m={'raw_dir':str(raw),'limit_per_file':args.limit_per_file,'run_time':dt.datetime.now(dt.timezone.utc).isoformat(),'files':manifest(raw)}
        save(mp,m)
    c=connection(out);write_rules(out,m['run_time'])
    try:
        if args.stage in {'all','profile'}:
            profiles=profile(c,m['files'],out,m['run_time'],args.limit_per_file)
        else:
            profiles=json.loads((out/'reports'/'01_profile.json').read_text())
        if args.stage in {'all','transform'}:
            check_contract(out)
            if args.workers==1:
                transform(c,m['files'],profiles,out,m['run_time'],args.limit_per_file)
            else:
                with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
                    futures=[pool.submit(transform_worker,item,profiles,out,m['run_time'],args.limit_per_file) for item in m['files']]
                    for future in concurrent.futures.as_completed(futures):future.result()
        if args.stage in {'all','validate'}:
            from validate_communitynotes import validate
            validate(c,out,m,profiles)
    except Exception as e:
        save(out/'reports'/'failure.json',{'error':str(e),'stage':args.stage,'action':'Stopped without silently dropping rows. Completed partitions retained for inspection; incomplete .partial files are not final outputs.'})
        raise
    finally:
        c.close()


if __name__=='__main__':
    main()

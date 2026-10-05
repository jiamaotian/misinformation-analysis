"""Full-output validation and auditable views; never rewrites cleaned partitions."""
from pathlib import Path
import collections
import hashlib
import json
import shutil
import time

from clean_communitynotes import HEADERS, qi, qs, source_expr, save, emit, disk_guard, output_is_isolated, kind


def parquet(c, query, path):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.partial')
    c.execute(f"COPY ({query}) TO {qs(temp)} (FORMAT PARQUET, COMPRESSION ZSTD)")
    temp.replace(path)
    return c.execute(f'SELECT count(*) FROM read_parquet({qs(path)})').fetchone()[0]


def duplicate_checks(c, out, group):
    """Check each archive, then check keys spanning archives; bound ratings memory."""
    report_path=out/'reports'/f'duplicates-{group}.json'
    if report_path.exists():
        return json.loads(report_path.read_text())
    keys=['noteId','raterParticipantId'] if group=='ratings' else ['tweetId'] if group=='batSignals' else ['participantId'] if group=='userEnrollment' else ['noteId']
    keysql=','.join(qi(k) for k in keys)
    valid=' AND '.join(qi(k)+' IS NOT NULL' for k in keys)
    c.execute(f'CREATE OR REPLACE TEMP TABLE duplicate_keys AS SELECT {keysql} FROM {qi(group)} WHERE false')
    parts=sorted((out/'cleaned'/group).glob('*.parquet'))
    for part in parts:
        disk_guard(out)
        if group=='ratings':
            # Hashes are ONLY a memory-saving candidate filter. Collisions are rechecked
            # using exact keys, and removal still compares complete original records.
            c.execute(f'CREATE OR REPLACE TEMP TABLE repeated_hashes AS SELECT hash({keysql}) AS key_hash FROM read_parquet({qs(part)}) WHERE {valid} GROUP BY 1 HAVING count(*)>1')
            if c.execute('SELECT count(*) FROM repeated_hashes').fetchone()[0]:
                c.execute(f'INSERT INTO duplicate_keys SELECT {keysql} FROM read_parquet({qs(part)}) WHERE {valid} AND hash({keysql}) IN (SELECT key_hash FROM repeated_hashes) GROUP BY {keysql} HAVING count(*)>1')
        else:
            c.execute(f'INSERT INTO duplicate_keys SELECT {keysql} FROM read_parquet({qs(part)}) WHERE {valid} GROUP BY {keysql} HAVING count(*)>1')
        emit('duplicate_partition_checked',dataset=group,file=part.name)
    # Only note IDs spanning partitions need a cross-partition rater-key check.
    if len(parts)>1:
        first=qi(keys[0])
        c.execute(f'CREATE OR REPLACE TEMP TABLE spanning_keys AS SELECT {first} FROM {qi(group)} WHERE {valid} GROUP BY {first} HAVING count(distinct _source_file)>1')
        c.execute(f'INSERT INTO duplicate_keys SELECT {keysql} FROM {qi(group)} WHERE {valid} AND {first} IN (SELECT {first} FROM spanning_keys) GROUP BY {keysql} HAVING count(*)>1')
    c.execute('CREATE OR REPLACE TEMP TABLE duplicate_keys AS SELECT DISTINCT * FROM duplicate_keys')
    nkeys=c.execute('SELECT count(*) FROM duplicate_keys').fetchone()[0]
    duplicate_path=out/'audit'/f'{group}-duplicate-records.parquet'
    exclusions=out/'audit'/f'{group}-duplicate-exclusions.parquet'
    exact_removed=conflict_groups=0
    if nkeys:
        # Compare complete reconstructed ORIGINAL records, not hashes or cleaned values.
        original='struct_pack('+','.join(qi(n)+':='+source_expr(n,'t.') for n in HEADERS[group])+')'
        c.execute(f'CREATE OR REPLACE TEMP TABLE duplicate_records AS SELECT t.*,to_json({original}) original_record FROM {qi(group)} t SEMI JOIN duplicate_keys USING ({keysql})')
        # Flag every duplicate group before creating exclusion decisions.
        parquet(c,'SELECT *, \'duplicate_candidate_key\' AS validation_flag FROM duplicate_records',duplicate_path)
        conflict_groups=c.execute(f'SELECT count(*) FROM (SELECT {keysql} FROM duplicate_records GROUP BY {keysql} HAVING count(distinct original_record)>1)').fetchone()[0]
        query=f"SELECT _source_file,_source_row,'identical original source record; retain first by source filename and row; prevents double-counting' AS reason FROM (SELECT *,row_number() OVER (PARTITION BY {keysql},original_record ORDER BY _source_file,_source_row) rn FROM duplicate_records) WHERE rn>1"
        exact_removed=parquet(c,query,exclusions)
    else:
        parquet(c,f"SELECT _source_file,_source_row,''::VARCHAR AS reason FROM {qi(group)} WHERE false",exclusions)
    total=c.execute(f'SELECT count(*) FROM {qi(group)}').fetchone()[0]
    report={'dataset':group,'input_rows':total,'retained_cleaned_rows':total,'duplicate_key_groups':nkeys,'conflicting_key_groups_retained':conflict_groups,'identical_copies_excluded_from_analysis_view':exact_removed,'analysis_view_rows':total-exact_removed,'exclusion_manifest':str(exclusions),'reason':'Only exact original-record duplicates are excluded; conflicting values are retained and flagged. Source partitions unchanged.','metric_exclusions':0}
    save(report_path,report)
    emit('stage_complete',stage='duplicate_handling',**report)
    return report


def cross_checks(c,out):
    report_path=out/'reports'/'04_cross_table.json'
    if report_path.exists():
        return json.loads(report_path.read_text())
    # One row per note lookup prevents multiplying ratings or status rows.
    c.execute('CREATE OR REPLACE TEMP TABLE note_lookup AS SELECT noteId,count(*) AS note_records,min(createdAtMillis) AS note_created,min(noteAuthorParticipantId) AS author FROM notes_analysis WHERE noteId IS NOT NULL GROUP BY noteId')
    c.execute('CREATE OR REPLACE TEMP TABLE status_lookup AS SELECT noteId,count(*) AS status_records FROM noteStatusHistory_analysis WHERE noteId IS NOT NULL GROUP BY noteId')
    c.execute('CREATE OR REPLACE TEMP TABLE enrollment_lookup AS SELECT participantId,count(*) AS enrollment_records FROM userEnrollment_analysis WHERE participantId IS NOT NULL GROUP BY participantId')
    counts={}
    spec={
        'notes': "SELECT n._source_file,n._source_row,CASE WHEN n.tweetId IS NULL THEN 'unavailable_post_id' WHEN b.tweetId IS NULL THEN 'post_not_in_request_table' ELSE 'matched_request' END request_match,CASE WHEN s.noteId IS NULL THEN 'no_status_match' WHEN s.status_records>1 THEN 'ambiguous_status_match' ELSE 'matched_status' END status_match,CASE WHEN e.participantId IS NULL THEN 'no_author_enrollment_match' WHEN e.enrollment_records>1 THEN 'ambiguous_author_enrollment' ELSE 'matched_author_enrollment' END author_match FROM notes_analysis n LEFT JOIN (SELECT DISTINCT tweetId FROM batSignals_analysis WHERE tweetId IS NOT NULL) b USING(tweetId) LEFT JOIN status_lookup s USING(noteId) LEFT JOIN enrollment_lookup e ON n.noteAuthorParticipantId=e.participantId",
        'noteStatusHistory': "SELECT s._source_file,s._source_row,CASE WHEN n.noteId IS NULL THEN 'no_note_match' WHEN n.note_records>1 THEN 'ambiguous_note_match' ELSE 'matched_note' END note_match,CASE WHEN n.note_records=1 THEN s.createdAtMillis IS DISTINCT FROM n.note_created ELSE false END creation_mismatch,CASE WHEN n.note_records=1 THEN s.noteAuthorParticipantId IS DISTINCT FROM n.author ELSE false END author_mismatch FROM noteStatusHistory_analysis s LEFT JOIN note_lookup n USING(noteId)",
        'ratings': "SELECT r._source_file,r._source_row,CASE WHEN n.noteId IS NULL THEN 'no_note_match' WHEN n.note_records>1 THEN 'ambiguous_note_match' ELSE 'matched_note' END note_match,CASE WHEN n.note_records=1 THEN r.createdAtMillis_utc IS NOT NULL AND r.createdAtMillis<n.note_created ELSE false END rating_before_creation,CASE WHEN e.participantId IS NULL THEN 'no_rater_enrollment_match' WHEN e.enrollment_records>1 THEN 'ambiguous_rater_enrollment' ELSE 'matched_rater_enrollment' END rater_match FROM ratings_analysis r LEFT JOIN note_lookup n USING(noteId) LEFT JOIN enrollment_lookup e ON r.raterParticipantId=e.participantId",
        'batSignals': "SELECT b._source_file,b._source_row,CASE WHEN n.tweetId IS NULL THEN 'no_note_match' ELSE 'matched_at_least_one_note' END note_match FROM batSignals_analysis b LEFT JOIN (SELECT DISTINCT tweetId FROM notes_analysis WHERE tweetId IS NOT NULL) n USING(tweetId)",
    }
    for group,query in spec.items():
        disk_guard(out)
        path=out/'audit'/f'{group}-join-flags.parquet'
        n=parquet(c,query,path)
        original=c.execute(f'SELECT count(*) FROM {qi(group+"_analysis")}').fetchone()[0]
        assert n==original, 'Join multiplied or removed records'
        c.execute(f'CREATE OR REPLACE TEMP VIEW join_flags AS SELECT * FROM read_parquet({qs(path)})')
        cols=[x[0] for x in c.execute('DESCRIBE join_flags').fetchall() if not x[0].startswith('_')]
        counts[group]={'rows_before':n,'rows_after':n,'flags':{},'rows_dropped':0,'metric_exclusions':0}
        for col in cols:
            counts[group]['flags'][col]={str(v):count for v,count in c.execute(f'SELECT {qi(col)},count(*) FROM join_flags GROUP BY 1').fetchall()}
        save(out/'reports'/f'join-{group}.json',counts[group])
        emit('stage_complete',stage='cross_table_flags',dataset=group,**counts[group])
    # Counts keep all source eras and every unmatched note ID. No cohort/filter or wide join.
    summary=out/'summaries'/'ratings_by_note.parquet'
    query="""SELECT noteId,count(*) rating_count,
        count(*) FILTER(WHERE version=1) legacy_rating_count,
        count(*) FILTER(WHERE version=2) version2_rating_count,
        count(*) FILTER(WHERE helpfulnessLevel IN ('HELPFUL','SOMEWHAT_HELPFUL','NOT_HELPFUL')) valid_level_count,
        count(*) FILTER(WHERE helpfulnessLevel='HELPFUL') helpful_count,
        count(*) FILTER(WHERE helpfulnessLevel='SOMEWHAT_HELPFUL') somewhat_helpful_count,
        count(*) FILTER(WHERE helpfulnessLevel='NOT_HELPFUL') not_helpful_count,
        min(createdAtMillis_utc) first_rating_utc,max(createdAtMillis_utc) last_rating_utc
        FROM ratings_analysis GROUP BY noteId"""
    summary_rows=parquet(c,query,summary)
    input_count=c.execute('SELECT count(*) FROM ratings_analysis').fetchone()[0]
    accounted=c.execute(f'SELECT sum(rating_count) FROM read_parquet({qs(summary)})').fetchone()[0]
    assert input_count==accounted
    counts['rating_summary']={'input_rows':input_count,'output_note_groups':summary_rows,'sum_rating_count':accounted,'rows_excluded':0,'reason':'Explicit aggregation to note grain; all ratings accounted for; legacy helpfulness is never imputed.','missing_time':'min/max ignores null UTC timestamps; source ratings retained and transformation null counts reported.'}
    save(report_path,counts);emit('stage_complete',stage='rating_summary',**counts['rating_summary'])
    return counts


def catalog_sql(out):
    statements=["SET TimeZone='UTC';"]
    for group,columns in HEADERS.items():
        statements.append(f'CREATE OR REPLACE VIEW {qi(group)} AS SELECT * FROM read_parquet({qs(out/"cleaned"/group/"*.parquet")});')
        exclusions=out/'audit'/f'{group}-duplicate-exclusions.parquet'
        statements.append(f'CREATE OR REPLACE VIEW {qi(group+"_analysis")} AS SELECT t.* FROM {qi(group)} t ANTI JOIN read_parquet({qs(exclusions)}) e ON t._source_file=e._source_file AND t._source_row=e._source_row;')
        original=','.join(source_expr(n)+' AS '+qi(n) for n in columns)
        statements.append(f'CREATE OR REPLACE VIEW {qi(group+"_source_values")} AS SELECT _source_file,_source_member,_source_row,{original} FROM {qi(group)};')
        before='CASE field '+' '.join('WHEN '+qs(n)+' THEN '+source_expr(n) for n in columns)+' END'
        targets={n:n+'_utc' if kind(n)=='timestamp' else n+'_trimmed' if n in {'summary','suggestion'} else n for n in columns}
        after='CASE field '+' '.join('WHEN '+qs(n)+' THEN cast('+qi(targets[n])+' AS VARCHAR)' for n in columns)+' END'
        target='CASE field '+' '.join('WHEN '+qs(n)+' THEN '+qs(targets[n]) for n in columns)+' END'
        fields=','.join(f'({qs(n)},{1<<i}::UBIGINT)' for i,n in enumerate(columns))
        statements.append(f'CREATE OR REPLACE VIEW {qi(group+"_cell_changes")} AS SELECT _source_file,_source_member,_source_row,field AS column_name,{target} AS target_column,{before} AS original_value,{after} AS typed_value FROM {qi(group)} CROSS JOIN (VALUES {fields}) mapping(field,bit_value) WHERE (_changed_mask & bit_value)<>0;')
    return '\n\n'.join(statements)+'\n'


def write_summary(out,profiles,duplicates,cross):
    transforms=[json.loads(p.read_text()) for p in sorted((out/'reports'/'transform').glob('*.json'))]
    lines=['# Cleaning run report','', 'All raw ZIPs were read locally and left unchanged. Original TSVs were not copied into the project. Cleaned Parquet and record-level audits are Git-ignored.','', '## Full input and output accounting','', '| Dataset | Input rows | Cleaned rows | Flag events | Exact copies excluded only from analysis view |','|---|---:|---:|---:|---:|']
    for group in HEADERS:
        r=[x for x in transforms if x['dataset']==group]
        lines.append(f"| {group} | {sum(x['rows_before'] for x in r):,} | {sum(x['rows_after'] for x in r):,} | {sum(x['flag_events'] for x in r):,} | {duplicates[group]['identical_copies_excluded_from_analysis_view']:,} |")
    lines+=['','## Transformations and unresolved findings','', 'Every source column has an explicit rule in `reports/rules.json`. Each partition report lists mapping counts, changed cells/rows, null counts, flags, and before/after row counts. Flags were recorded before applying typed conversions. Suspicious values were retained; no speculative category remapping, imputation, clipping, or URL repair was performed.','', 'UTC companions use milliseconds since Unix epoch; source epochs and negative sentinel values are retained. Scoring-minute metadata was not converted. Legacy rating levels remain missing. Original tokens can be reconstructed through the `*_source_values` SQL views; `*_cell_changes` decodes the change mask and provides a per-cell conversion audit without materializing billions of redundant audit events.','', '### Flag counts (events can overlap on one row)','', '| Dataset and rule | Events |','|---|---:|']
    counts=collections.Counter()
    for r in transforms:
        for k,v in r['flag_counts'].items():counts[r['dataset']+':'+k]+=v
    lines += [f'| `{k}` | {v:,} |' for k,v in sorted(counts.items())]
    lines+=['','## Cross-table checks','', 'Join flags preserve every input analysis row and distinguish unmatched from ambiguous matches. Unmatched rows are not deleted or treated as proof that no corresponding contribution exists. Ratings are aggregated before any future note-level join. No coverage denominator, feed, observation window, cutoff, or completed-response metric has been selected.','', 'Detailed results: `reports/04_cross_table.json`; record references: `audit/*-join-flags.parquet`.','', '## Reproducibility','', '`manifest.json` records SHA-256 hashes of each input ZIP. `catalog.sql` defines local read-only analysis and audit views. `reports/05_validation.json` records final checks, including source integrity.']
    (out/'CLEANING_REPORT.md').write_text('\n'.join(lines)+'\n')


def validate(c,out,manifest,profiles):
    for group in HEADERS:
        c.execute(f'CREATE OR REPLACE VIEW {qi(group)} AS SELECT * FROM read_parquet({qs(out/"cleaned"/group/"*.parquet")})')
        expected=sum(x['rows'] for x in profiles.values() if x['dataset']==group)
        actual=c.execute(f'SELECT count(*) FROM {qi(group)}').fetchone()[0]
        assert actual==expected,(group,expected,actual)
    duplicates={}
    for group in HEADERS:
        duplicates[group]=duplicate_checks(c,out,group)
        path=out/'audit'/f'{group}-duplicate-exclusions.parquet'
        c.execute(f'CREATE OR REPLACE VIEW {qi(group+"_analysis")} AS SELECT t.* FROM {qi(group)} t ANTI JOIN read_parquet({qs(path)}) e ON t._source_file=e._source_file AND t._source_row=e._source_row')
    cross=cross_checks(c,out)
    sql=catalog_sql(out);(out/'catalog.sql').write_text(sql)
    c.execute(sql)
    emit('verifying_source_hashes')
    for item in manifest['files']:
        h=hashlib.sha256()
        with open(item['path'],'rb') as f:
            for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
        assert h.hexdigest()==item['sha256'],'Raw ZIP changed'
    assert output_is_isolated(out),'Record-level outputs are not isolated from Git'
    result={'status':'passed','scope':'full dataset' if manifest['limit_per_file'] is None else 'sample test only','source_hashes_unchanged':True,'source_files':len(manifest['files']),'all_input_rows_retained_in_cleaned_partitions':True,'joins_preserve_analysis_row_counts':True,'rating_aggregation_reconciles':True,'no_analysis_cohort_or_cutoff_selected':True,'utc_timezone':'UTC','record_level_outputs_git_ignored_or_outside_repo':True,'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*communitynotes.py')},'output_bytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file()),'dependencies':{'duckdb':__import__('duckdb').__version__,'pyarrow':__import__('pyarrow').__version__}}
    save(out/'reports'/'05_validation.json',result)
    write_summary(out,profiles,duplicates,cross)
    emit('complete',**result)

#!/usr/bin/env python3
"""Disk-backed, chunked Community Notes cleaner. Python 3.10+, pandas >=2.0."""
import argparse, csv, glob, json, sqlite3, subprocess, shutil
from pathlib import Path
from collections import Counter
import pandas as pd

LEVELS = {'HELPFUL','SOMEWHAT_HELPFUL','NOT_HELPFUL'}
STATUSES = {'CURRENTLY_RATED_HELPFUL','CURRENTLY_RATED_NOT_HELPFUL','NEEDS_MORE_RATINGS'}

def expand(patterns):
    files = sorted({str(Path(p).resolve()) for pat in patterns for p in glob.glob(str(Path(pat).expanduser()))})
    if not files: raise ValueError(f'No inputs matched: {patterns}')
    return files

def integer_ms(s):
    # Never route identifiers or integer timestamps through floating point.
    ok = s.str.fullmatch(r'\d{1,16}', na=False)
    n = pd.to_numeric(s.where(ok), errors='coerce').astype('Int64')
    return n.where(n.between(0, 253402300799999))

def first_seen(conn, table, values):
    """Batch sorted inserts to avoid one random disk transaction per source row."""
    conn.execute('DROP TABLE IF EXISTS temp.batch')
    conn.execute('CREATE TEMP TABLE batch (i INTEGER, v BLOB)')
    conn.executemany('INSERT INTO batch VALUES (?,?)', enumerate(values))
    indices = [r[0] for r in conn.execute(
        f'SELECT MIN(b.i) FROM batch b LEFT JOIN {table} s ON s.h=b.v '
        'WHERE s.h IS NULL GROUP BY b.v')]
    conn.execute(f'INSERT OR IGNORE INTO {table} SELECT DISTINCT v FROM batch ORDER BY v')
    keep = [False] * len(values)
    for i in indices: keep[i] = True
    return keep

def clean(kind, files, out, chunksize, cutoff, conn, max_rows=None):
    if max_rows is not None and max_rows <= 0: raise ValueError('A positive bounded max_rows is required')
    required = {'noteId','createdAtMillis'} | ({'raterParticipantId','helpfulnessLevel'} if kind=='ratings' else {'firstNonNMRStatus','timestampMillisOfFirstNonNMRStatus','currentStatus'})
    headers=[]
    for f in files:
        with open(f, newline='', encoding='utf-8') as stream:
            h=next(csv.reader(stream, delimiter='\t'))
        if not required.issubset(h): raise ValueError(f'{f}: missing {required-set(h)}')
        if len(h)!=len(set(h)): raise ValueError('Duplicate headers')
        if any(c.startswith(('qc_', 'meta_')) or c.endswith(('_clean', '_utc')) or c in {'response_time_hours','createdAtUtc'} for c in h):
            raise ValueError('Source columns collide with derived column namespace')
        headers.append(h)
    if any(h!=headers[0] for h in headers): raise ValueError('Input shards have different schemas; reconcile snapshots first')
    conn.execute('DROP TABLE IF EXISTS seen')
    conn.execute('DROP TABLE IF EXISTS keys')
    conn.execute('CREATE TABLE seen (h BLOB PRIMARY KEY) WITHOUT ROWID')
    conn.execute('CREATE TABLE keys (h BLOB PRIMARY KEY) WITHOUT ROWID')
    report={'kind':kind,'inputs':[{'path':f,'bytes':Path(f).stat().st_size,'mtime_ns':Path(f).stat().st_mtime_ns} for f in files], 'counts':Counter(), 'missing':Counter(), 'categories':Counter(), 'columns':headers[0], 'timestamp_ranges':{}}
    count=report['counts']; first=True
    dest=out/f'{kind}_clean.tsv.gz'
    for f in files:
        if max_rows is not None and count['input'] >= max_rows: break
        offset=0
        for df in pd.read_csv(f,sep='\t',dtype='string',keep_default_na=False,na_filter=False,chunksize=min(chunksize,max_rows) if max_rows else chunksize,on_bad_lines='error'):
            if max_rows is not None:
                df=df.iloc[:max_rows-count['input']].copy()
                if df.empty: break
            count['input']+=len(df)
            # Compare serialized original field values before normalization; exact equality only.
            hashes=[json.dumps(row,ensure_ascii=False,separators=(',',':')).encode() for row in df.itertuples(index=False,name=None)]
            keep=first_seen(conn, 'seen', hashes)
            count['exact_duplicates_removed']+=len(df)-sum(keep)
            source_rows=pd.Series(range(offset+2,offset+len(df)+2),index=df.index); offset+=len(df)
            df=df.loc[keep].copy()
            df['meta_source_file']=Path(f).name;df['meta_source_record']=source_rows.loc[df.index]
            for col in headers[0]:
                # Keep raw source fields; add normalized fields only where needed.
                report['missing'][col]+=int(df[col].eq('').sum())
            keycols=['noteId']+(['raterParticipantId'] if kind=='ratings' else [])
            for col in keycols: df[col+'_clean']=df[col].str.strip()
            df['qc_noteId_invalid']=~df['noteId_clean'].str.fullmatch(r'[1-9][0-9]*',na=False)
            good=~df['qc_noteId_invalid']
            if kind=='ratings':
                df['qc_raterParticipantId_invalid']=df['raterParticipantId_clean'].eq('')
                good &= ~df['qc_raterParticipantId_invalid']
            df['qc_key_valid']=good
            if 'noteAuthorParticipantId' in df:
                df['qc_noteAuthorParticipantId_invalid']=df['noteAuthorParticipantId'].str.strip().eq('')
            normalized=[]
            for c in headers[0]:
                if c=='createdAtMillis' or 'timestampMillis' in c or c.startswith('timestampMinute'):
                    n=integer_ms(df[c].str.strip());df[c+'_clean']=n
                    millis=n.where(n.le(253402300799999//60000))*60000 if c.startswith('timestampMinute') else n
                    millis=millis.where(millis.between(0,253402300799999))
                    df['qc_'+c+'_missing']=df[c].str.strip().eq('')
                    utc=pd.to_datetime(millis,unit='ms',utc=True,errors='coerce')
                    df[c+'_utc']=utc.astype('string')
                    df['qc_'+c+'_invalid']=millis.isna() & ~df['qc_'+c+'_missing']
                    df['qc_'+c+'_utc_unrepresentable']=n.notna() & utc.isna()
                    df['qc_'+c+'_after_cutoff']=millis.gt(cutoff).fillna(False)
                    count['invalid_or_missing_'+c]+=int(n.isna().sum())
                    if n.notna().any():
                        prev=report['timestamp_ranges'].get(c,[int(n.min()),int(n.max())])
                        report['timestamp_ranges'][c]=[min(prev[0],int(n.min())),max(prev[1],int(n.max()))]
                    normalized.append(c)
            df['createdAtUtc']=pd.to_datetime(df['createdAtMillis_clean'],unit='ms',utc=True,errors='coerce').astype('string')
            df['qc_created_by_cutoff']=df['createdAtMillis_clean'].le(cutoff).fillna(False)
            if kind=='ratings':
                level=df['helpfulnessLevel'].str.strip().str.upper();df['helpfulnessLevel_clean']=level
                df['qc_valid_helpfulness']=level.isin(LEVELS)
                count['valid_helpfulness']+=int(df['qc_valid_helpfulness'].sum())
                count['helpful']+=int(level.eq('HELPFUL').sum())
                report['categories'].update(level.value_counts().to_dict())
            else:
                s=df['firstNonNMRStatus'].str.strip().str.upper(); df['firstNonNMRStatus_clean']=s
                end=df['timestampMillisOfFirstNonNMRStatus_clean'];start=df['createdAtMillis_clean']
                valid=good & s.isin(STATUSES-{'NEEDS_MORE_RATINGS'}) & start.notna() & end.notna() & end.ge(start) & start.le(cutoff) & end.le(cutoff)
                df['qc_response_eligible']=valid.fillna(False)
                df['qc_negative_latency']=end.lt(start).fillna(False)
                df['qc_status_time_inconsistent']=(s.isin(STATUSES-{'NEEDS_MORE_RATINGS'}) ^ end.notna())
                df['qc_currentStatus_invalid']=~df['currentStatus'].str.strip().str.upper().isin(STATUSES)
                df['qc_firstNonNMRStatus_invalid']=~s.isin(STATUSES | {''})
                df['response_time_hours']=((end-start)/3600000).where(valid)
                count['response_eligible']+=int(valid.sum());count['negative_latency']+=int(end.lt(start).sum())
                count['status_time_inconsistent']+=int((s.isin(STATUSES-{'NEEDS_MORE_RATINGS'}) ^ end.notna()).sum())
                report['categories'].update(df['currentStatus'].value_counts().to_dict())
            keyhashes=[json.dumps(row,separators=(',',':')).encode()
                       for row in df[[c+'_clean' for c in keycols]].itertuples(index=False,name=None)]
            repeated=[not fresh for fresh in first_seen(conn, 'keys', keyhashes)]
            df['qc_repeated_key']=repeated
            count['repeated_key_retained']+=sum(repeated)
            count['invalid_key_retained']+=int((~good).sum());count['output']+=len(df)
            for c in df.columns:
                if c.startswith('qc_'): count[c]+=int(df[c].sum())
            df.to_csv(dest,sep='\t',index=False,mode='w' if first else 'a',header=first,compression={'method':'gzip','compresslevel':1});first=False
            conn.commit()
            if max_rows is not None and count['input'] >= max_rows: break
            print(f'{kind}: {count["input"]:,} input / {count["output"]:,} output',flush=True)
    assert count['input']==count['output']+count['exact_duplicates_removed']
    report['row_reconciliation_passed']=True
    report['unique_normalized_keys']=conn.execute('SELECT COUNT(*) FROM keys').fetchone()[0]
    report['output']=str(dest);report['cutoff_ms']=cutoff
    report['scope']='NOT full: bounded prefix sample' if max_rows else 'All rows of supplied shards ONLY; completeness of X release unverified.'
    report['max_rows']=max_rows
    report['is_full_dataset']=False
    report['all_supplied_rows_processed']=max_rows is None
    report['qc_counts_scope']='retained rows after exact deduplication'
    report['alignment']='Conversation-documented Peyton policy; Peyton source unavailable for direct comparison' 
    if kind=='status': report['join_ready_unique_noteId']=count['repeated_key_retained']==0 and count['invalid_key_retained']==0
    (out/f'{kind}_validation.json').write_text(json.dumps(report,indent=2))
    return report

def native_run(kind, files, out, cutoff, run_rows=2000000):
    """Compile the optional standard C++17/zlib accelerator; no package download."""
    source=Path(__file__).with_name('full_worker.cpp')
    build=Path(__file__).with_name('.build');build.mkdir(exist_ok=True)
    executable=build/'full_worker'
    if not executable.exists() or executable.stat().st_mtime_ns < source.stat().st_mtime_ns:
        compiler=shutil.which('clang++') or shutil.which('g++')
        if not compiler: raise RuntimeError('C++17 compiler unavailable; use --engine pandas')
        subprocess.run([compiler,'-O3','-std=c++17',str(source),'-lz','-o',str(executable)],check=True)
    required={'noteId','createdAtMillis'} | ({'raterParticipantId','helpfulnessLevel'} if kind=='ratings' else {'firstNonNMRStatus','timestampMillisOfFirstNonNMRStatus','currentStatus'})
    schema=None
    for file in files:
        with open(file,newline='',encoding='utf-8') as stream: header=next(csv.reader(stream,delimiter='\t'))
        if not required.issubset(header): raise ValueError(f'Missing required fields in {file}')
        if len(header)!=len(set(header)): raise ValueError('Duplicate source headers')
        if any(c.startswith(('qc_','meta_')) or c.endswith(('_clean','_utc')) or c in {'response_time_hours','createdAtUtc'} for c in header):
            raise ValueError('Source columns collide with derived namespace')
        if schema is not None and header!=schema: raise ValueError('Shard schemas differ')
        schema=header
    subprocess.run([str(executable),kind,str(out),str(cutoff),str(run_rows),*files],check=True)
    report_path=out/f'{kind}_validation.json'
    report=json.loads(report_path.read_text())
    report['inputs']=[{'path':file,'bytes':Path(file).stat().st_size,'mtime_ns':Path(file).stat().st_mtime_ns} for file in files]
    report_path.write_text(json.dumps(report,indent=2))
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ratings',nargs='+');p.add_argument('--status',nargs='+')
    p.add_argument('--only',choices=['ratings','status'],help='Run one dataset independently')
    p.add_argument('--output',required=True);p.add_argument('--chunksize',type=int,default=100000)
    p.add_argument('--cutoff',required=True,help='ISO UTC analysis cutoff, inclusive')
    p.add_argument('--max-rows',type=int,default=None,help='Optional sample cap; omitted means ALL supplied records')
    p.add_argument('--engine',choices=['auto','native','pandas'],default='auto')
    p.add_argument('--run-rows',type=int,default=2000000,help='External-sort memory bound in records')
    a=p.parse_args()
    if a.max_rows is not None and a.max_rows <= 0: p.error('max-rows must be positive')
    if a.run_rows<=0: p.error('run-rows must be positive')
    if a.engine=='native' and a.max_rows is not None: p.error('native processes whole supplied files; use pandas for samples')
    if a.chunksize<=0: p.error('chunksize must be positive')
    kinds=[a.only] if a.only else ['status','ratings']
    files={k:expand(getattr(a,k) or []) for k in kinds}
    for kind,paths in files.items():
        if len({Path(file).name for file in paths})!=len(paths):
            raise ValueError(f'{kind}: source basenames must be unique for unambiguous provenance')
    if set(files.get('ratings',[]))&set(files.get('status',[])): raise ValueError('Inputs overlap')
    cutoff=pd.Timestamp(a.cutoff)
    if cutoff.tzinfo is None: raise ValueError('Cutoff requires timezone, e.g. 2026-10-02T23:59:59.999Z')
    cutoff=cutoff.value//10**6
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()): raise ValueError('Output must be empty: use a new run directory')
    (out/'RUNNING').write_text('Incomplete until SUCCESS.json exists')
    try:
        engine=('native' if a.max_rows is None else 'pandas') if a.engine=='auto' else a.engine
        if engine=='native':
            reports={k:native_run(k,files[k],out,cutoff,a.run_rows) for k in kinds}
        else:
            with sqlite3.connect(out/'audit.sqlite') as conn:
                conn.execute('PRAGMA journal_mode=OFF');conn.execute('PRAGMA synchronous=OFF')
                conn.execute('PRAGMA cache_size=-65536');conn.execute('PRAGMA temp_store=MEMORY')
                reports={k:clean(k,files[k],out,a.chunksize,cutoff,conn,a.max_rows) for k in kinds}
            (out/'audit.sqlite').unlink()
        (out/'SUCCESS.json').write_text(json.dumps({'status':'complete_supplied_files' if a.max_rows is None else 'complete_bounded_sample_NOT_full','reports':list(reports),'release_complete':False,'is_full_dataset':False,'all_supplied_rows_processed':a.max_rows is None,'max_rows_per_dataset':a.max_rows},indent=2))
        (out/'RUNNING').unlink()
    except Exception as e:
        (out/'FAILED.txt').write_text(repr(e));raise
if __name__=='__main__': main()

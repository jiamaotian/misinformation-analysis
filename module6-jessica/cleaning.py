"""Reproducible Community Notes coverage cleaning; raw files are never changed."""
from pathlib import Path
import argparse, csv, hashlib, json, sqlite3, sys, tempfile
from collections import Counter
import pandas as pd

csv.field_size_limit(1_000_000_000)
ROOT = Path(__file__).resolve().parent
FEED = 'noteRequestFeedEligibleAtMillis'
CUTOFF = '2026-09-12T23:59:59Z'
RULES = [
 ('R1', 'Read all original TSV columns as strings; preserve IDs and leading zeros. Trim outer whitespace only in IDs and timestamp fields. Preserve prose and classification labels.', 'Avoid ID precision loss and unintended changes to text.'),
 ('R2', 'Remove only fully identical source rows across Notes files. Exclude all remaining records with conflicting repeated noteId; never select an arbitrary winner.', 'Repeated tweetId across different notes is a valid one-to-many relationship.'),
 ('R3', 'Interpret -1 in eligibility fields as not eligible. Keep missing optional fields. Invalid/missing IDs and invalid timestamps cannot enter the analysis cohort.', 'Missing eligibility does not mean eligible; missing prose does not invalidate a key.'),
 ('R4', 'Use noteRequestFeedEligibleAtMillis only. Include unique eligible posts on or before the fixed UTC cutoff. A note counts only when eligibility <= creation <= cutoff.', 'Match the Phase 1 coverage definition; notes before eligibility do not count.'),
 ('R5', 'Aggregate qualifying notes to one row per tweetId before joining. Keep every eligible request, including unmatched ones.', 'Prevent multiple notes from multiplying the coverage denominator.'),
 ('R6', 'Unmatched means no qualifying note observed in supplied files, not proof of no note on X. Preserve suspicious values in raw sources and report exclusions.', 'File completeness and snapshot alignment are not established by a successful join.')]

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def save_json(path, value):
 path.write_text(json.dumps(value,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')

def millis(series, cutoff_ms):
 # Integer syntax is required; do not silently round fractional timestamps.
 v=pd.to_numeric(series.where(series.str.fullmatch(r'\d{1,15}',na=False)),errors='coerce')
 return v.where(v.gt(0) & v.le(253402300799999))

def audit_and_stage(raw, out, cutoff):
 out.mkdir(parents=True,exist_ok=True)
 cutoff_ms=int(pd.Timestamp(cutoff).timestamp()*1000)
 if pd.Timestamp(cutoff).tzinfo is None: raise ValueError('Cutoff must include timezone.')
 notes=sorted(raw.rglob('notes-*.tsv')); req=sorted(raw.rglob('batSignals-*.tsv'))
 if not notes or len(req)!=1: raise ValueError('Need notes-*.tsv and exactly one batSignals-*.tsv below data/raw.')
 tempdb=tempfile.TemporaryDirectory(prefix='coverage-db-')
 db=Path(tempdb.name)/'working.sqlite'
 con=sqlite3.connect(db)
 con.execute('CREATE TABLE notes (digest TEXT PRIMARY KEY, noteId TEXT, tweetId TEXT, created_raw TEXT, created_ms INTEGER, source TEXT, source_row INTEGER)')
 audits=[]; manifest=[]; counts=Counter(); schemas=None
 for p in notes:
  print('Reading', p.name, flush=True)
  manifest.append({'file':p.relative_to(raw).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
  file_rows=0; missing=Counter(); whitespace=Counter()
  for chunk in pd.read_csv(p,sep='\t',dtype='string',keep_default_na=False,chunksize=50000):
   if schemas is None: schemas=list(chunk.columns)
   if list(chunk.columns)!=schemas: raise ValueError('Notes schemas differ: '+p.name)
   if not {'noteId','tweetId','createdAtMillis'}.issubset(chunk.columns): raise ValueError('Missing required Notes fields')
   missing.update({c:int(chunk[c].eq('').sum()) for c in chunk})
   whitespace.update({c:int(chunk[c].ne(chunk[c].str.strip()).sum()) for c in chunk})
   times=millis(chunk.createdAtMillis.str.strip(),cutoff_ms)
   values=[]
   for i,(row,t) in enumerate(zip(chunk.itertuples(index=False,name=None),times)):
    d=dict(zip(chunk.columns,row)); nid=d['noteId'].strip(); tid=d['tweetId'].strip()
    digest=hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    values.append((digest,nid,tid,d['createdAtMillis'],None if pd.isna(t) else int(t),p.name,file_rows+i+2))
   before=con.total_changes
   con.executemany('INSERT OR IGNORE INTO notes VALUES (?,?,?,?,?,?,?)',values)
   counts['exact_note_duplicates']+=len(chunk)-(con.total_changes-before)
   file_rows+=len(chunk)
  con.commit(); counts['raw_notes']+=file_rows
  audits += [{'dataset':p.name,'column':c,'raw_type':'string','rows':file_rows,'blank_values':missing[c],'outer_whitespace':whitespace[c]} for c in schemas]
 con.execute('CREATE INDEX note_ids ON notes(noteId)'); con.execute('CREATE INDEX tweet_ids ON notes(tweetId)')
 con.execute('CREATE TABLE conflicts AS SELECT noteId FROM notes GROUP BY noteId HAVING COUNT(*)>1')
 con.execute('CREATE INDEX conflict_ids ON conflicts(noteId)')
 counts['conflicting_note_ids']=con.execute('SELECT COUNT(*) FROM conflicts').fetchone()[0]
 counts['conflicting_note_rows']=con.execute('SELECT COUNT(*) FROM notes WHERE noteId IN (SELECT noteId FROM conflicts)').fetchone()[0]
 # Decimal IDs only; keep their textual representation.
 con.execute("CREATE TABLE usable_notes AS SELECT * FROM notes WHERE noteId<>'' AND noteId NOT GLOB '*[^0-9]*' AND tweetId<>'' AND tweetId NOT GLOB '*[^0-9]*' AND created_ms IS NOT NULL AND noteId NOT IN (SELECT noteId FROM conflicts)")
 con.execute('CREATE INDEX usable_tweet_ids ON usable_notes(tweetId)')
 counts['usable_notes']=con.execute('SELECT COUNT(*) FROM usable_notes').fetchone()[0]
 counts['invalid_note_ids']=con.execute("SELECT COUNT(*) FROM notes WHERE noteId='' OR noteId GLOB '*[^0-9]*' OR tweetId='' OR tweetId GLOB '*[^0-9]*'").fetchone()[0]
 counts['invalid_note_time']=con.execute('SELECT COUNT(*) FROM notes WHERE created_ms IS NULL').fetchone()[0]
 counts['notes_after_cutoff']=con.execute('SELECT COUNT(*) FROM usable_notes WHERE created_ms>?',(cutoff_ms,)).fetchone()[0]
 counts['unique_note_tweets']=con.execute('SELECT COUNT(DISTINCT tweetId) FROM usable_notes').fetchone()[0]
 p=req[0]; r=pd.read_csv(p,sep='\t',dtype='string',keep_default_na=False)
 manifest.append({'file':p.relative_to(raw).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
 audits += [{'dataset':p.name,'column':c,'raw_type':'string','rows':len(r),'blank_values':int(r[c].eq('').sum()),'outer_whitespace':int(r[c].ne(r[c].str.strip()).sum())} for c in r]
 counts['raw_requests']=len(r); counts['exact_request_duplicates']=int(r.duplicated().sum())
 r=r.drop_duplicates().copy(); r['tweetId']=r.tweetId.str.strip()
 counts['repeated_request_ids']=int(r.tweetId.duplicated().sum())
 if counts['repeated_request_ids']: raise ValueError('Conflicting request IDs need review; no arbitrary deduplication allowed.')
 r['eligibility_ms']=millis(r[FEED].str.strip(),cutoff_ms)
 counts['not_eligible_sentinel']=int(r[FEED].str.strip().eq('-1').sum())
 counts['invalid_or_missing_eligibility']=int((r.eligibility_ms.isna() & r[FEED].str.strip().ne('-1')).sum())
 counts['invalid_request_id']=int((~r.tweetId.str.fullmatch(r'\d+',na=False)).sum())
 counts['eligibility_after_cutoff']=int(r.eligibility_ms.gt(cutoff_ms).sum())
 eligible=r.loc[r.tweetId.str.fullmatch(r'\d+',na=False)&r.eligibility_ms.notna()&r.eligibility_ms.le(cutoff_ms),['tweetId','eligibility_ms']].copy()
 eligible['eligibility_ms']=eligible.eligibility_ms.astype('int64')
 eligible.to_sql('requests',con,index=False,if_exists='replace'); con.execute('CREATE UNIQUE INDEX request_ids ON requests(tweetId)')
 counts['eligible_posts']=len(eligible)
 pd.DataFrame(audits).to_csv(out/'column_audit.csv',index=False)
 save_json(out/'source_manifest.json',manifest)
 stage={'tempdb':tempdb,'con':con,'counts':counts,'raw':raw,'out':out,'cutoff':cutoff,'cutoff_ms':cutoff_ms,'notes':notes,'request':p,'eligible':eligible,'manifest':manifest}
 save_json(out/'proposed_rules.json',RULES)
 return stage

def build_coverage(s):
 con=s['con']; c=s['counts']; ms=s['cutoff_ms']; out=s['out']
 # Requests are unique; SQL groups each one-to-many relation to post level.
 result=pd.read_sql_query('''SELECT r.tweetId,r.eligibility_ms,COUNT(n.noteId) AS observed_note_count,
 SUM(CASE WHEN n.created_ms<r.eligibility_ms THEN 1 ELSE 0 END) AS pre_eligibility_note_count,
 SUM(CASE WHEN n.created_ms>=r.eligibility_ms AND n.created_ms<=? THEN 1 ELSE 0 END) AS qualifying_note_count,
 MIN(CASE WHEN n.created_ms>=r.eligibility_ms AND n.created_ms<=? THEN n.created_ms END) AS first_qualifying_note_ms
 FROM requests r LEFT JOIN usable_notes n ON r.tweetId=n.tweetId GROUP BY r.tweetId,r.eligibility_ms ORDER BY r.tweetId''',con,params=(ms,ms))
 result['tweetId']=result.tweetId.astype('string')
 result['first_qualifying_note_ms']=result.first_qualifying_note_ms.astype('Int64')
 result['has_qualifying_note']=result.qualifying_note_count.gt(0)
 result['eligibility_utc']=pd.to_datetime(result.eligibility_ms,unit='ms',utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
 result['followup_days_at_cutoff']=((ms-result.eligibility_ms)/86400000).round(6)
 result['recent_under_7_days']=result.followup_days_at_cutoff.lt(7)
 result['observation_status']=result.has_qualifying_note.map({True:'qualifying_note_observed',False:'no_qualifying_note_observed'})
 result['cutoff_utc']=s['cutoff']
 assert len(result)==c['eligible_posts'] and result.tweetId.is_unique
 c['matched_any_note']=int(result.observed_note_count.gt(0).sum()); c['unmatched_any_note']=int(result.observed_note_count.eq(0).sum())
 c['covered_posts']=int(result.has_qualifying_note.sum()); c['no_qualifying_note_observed']=len(result)-c['covered_posts']
 c['qualifying_notes']=int(result.qualifying_note_count.sum()); c['pre_eligibility_notes']=int(result.pre_eligibility_note_count.sum())
 c['coverage_rate']=c['covered_posts']/len(result) if len(result) else None
 c['merge_rows']=len(result); c['note_tweets_without_eligible_request']=con.execute('SELECT COUNT(DISTINCT tweetId) FROM usable_notes WHERE tweetId NOT IN (SELECT tweetId FROM requests)').fetchone()[0]
 c['deduplicated_note_rows']=con.execute('SELECT COUNT(*) FROM notes').fetchone()[0]
 c['invalid_or_conflicting_note_rows']=c['deduplicated_note_rows']-c['usable_notes']
 c['recent_posts']=int(result.recent_under_7_days.sum())
 assert c['raw_notes']==c['exact_note_duplicates']+c['usable_notes']+c['invalid_or_conflicting_note_rows']
 mature=result.loc[~result.recent_under_7_days]
 c['at_least_7_days_posts']=len(mature); c['at_least_7_days_covered']=int(mature.has_qualifying_note.sum())
 c['missing_expected_notes_files']=[f'notes-{i:05d}.tsv' for i in range(5) if f'notes-{i:05d}.tsv' not in [p.name for p in s['notes']]]
 c['cutoff_utc']=s['cutoff']; c['scope']='supplied-files observation; snapshot completeness not verified'
 result.to_csv(out/'coverage_cleaned.csv',index=False)
 result.isna().sum().rename('missing_after').rename_axis('column').to_csv(out/'output_missing.csv')
 save_json(out/'full_data_checks.json',dict(c))
 s['coverage']=result
 return result

def record_checks(s):
 r=s['coverage']; chosen=[]
 categories=[('multiple qualifying notes',r.qualifying_note_count.gt(1)),('pre-eligibility note excluded',r.pre_eligibility_note_count.gt(0)),('no note match',r.observed_note_count.eq(0)),('recent eligibility retained',r.recent_under_7_days),('qualifying note observed',r.has_qualifying_note)]
 for label,mask in categories:
  rows=r.loc[mask & ~r.tweetId.isin([x[1] for x in chosen])]
  if len(rows): chosen.append((label,rows.iloc[0].tweetId))
 for tid in r.tweetId:
  if len(chosen)>=5: break
  if tid not in [x[1] for x in chosen]: chosen.append(('ordinary eligible request',tid))
 ids={tid for _,tid in chosen}; originals={tid:[] for tid in ids}; seen=set()
 # Independent CSV scan of original bytes for the chosen posts; no cleaned table lookup.
 conflicts={x[0] for x in s['con'].execute('SELECT noteId FROM conflicts')}
 for p in s['notes']:
  with p.open(encoding='utf-8',newline='') as f:
   for line,d in enumerate(csv.DictReader(f,delimiter='\t'),2):
    tid=d['tweetId'].strip()
    if tid not in ids: continue
    digest=hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    duplicate=digest in seen; seen.add(digest)
    originals[tid].append({'file':p.name,'line':line,'noteId':d['noteId'],'createdAtMillis':d['createdAtMillis'],'exact_duplicate':duplicate})
 original_requests={}
 with s['request'].open(encoding='utf-8',newline='') as f:
  for d in csv.DictReader(f,delimiter='\t'):
   if d['tweetId'].strip() in ids: original_requests[d['tweetId'].strip()]=d[FEED]
 checks=[]
 for label,tid in chosen:
  actual=r.loc[r.tweetId.eq(tid)].iloc[0]; e=int(original_requests[tid].strip()); qualifying=[]
  assert e==int(actual.eligibility_ms)
  for d in originals[tid]:
   v=d['createdAtMillis'].strip(); nid=d['noteId'].strip()
   if not d['exact_duplicate'] and nid.isdecimal() and nid not in conflicts and v.isdecimal() and e<=int(v)<=s['cutoff_ms']: qualifying.append(int(v))
  expected=len(qualifying); ok=expected==int(actual.qualifying_note_count)
  assert ok
  checks.append({'case':label,'tweetId':tid,'original_eligibility_ms':e,'original_notes':originals[tid],'expected_qualifying_note_count':expected,'actual_qualifying_note_count':int(actual.qualifying_note_count),'expected_first_note_ms':min(qualifying) if qualifying else None,'actual_first_note_ms':None if pd.isna(actual.first_qualifying_note_ms) else int(actual.first_qualifying_note_ms),'match':ok,'reason':'Count unique valid notes only when eligibility <= creation <= cutoff; preserve the eligible post even with zero observed notes.'})
  assert checks[-1]['expected_first_note_ms']==checks[-1]['actual_first_note_ms']
 save_json(s['out']/'five_record_checks.json',checks)
 first=r.set_index('tweetId').loc[[tid for _,tid in chosen]].reset_index()
 sample=pd.concat([first,r.loc[~r.tweetId.isin(ids)].sample(n=min(50-len(first),len(r)-len(first)),random_state=576)],ignore_index=True)
 sample.to_csv(s['out']/'coverage_sample.csv',index=False)
 return checks

def run(raw=ROOT/'data/raw',out=ROOT/'evidence',cutoff=CUTOFF):
 s=audit_and_stage(Path(raw),Path(out),cutoff)
 build_coverage(s); record_checks(s)
 print(json.dumps(dict(s['counts']),indent=2))
 s['con'].close(); s['tempdb'].cleanup()
 return dict(s['counts'])

if __name__=='__main__':
 a=argparse.ArgumentParser(); a.add_argument('--raw',type=Path,default=ROOT/'data/raw'); a.add_argument('--out',type=Path,default=ROOT/'evidence'); a.add_argument('--cutoff',default=CUTOFF); args=a.parse_args()
 run(args.raw,args.out,args.cutoff)

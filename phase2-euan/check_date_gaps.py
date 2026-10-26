"""Synthetic audit; run: python check_date_gaps.py. No real CSV required."""
from pathlib import Path
import hashlib, json
from datetime import datetime, timezone
import pandas as pd
from coverage_analysis import analyze_coverage, FEEDS

def ms(s):
    return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
start='2026-09-11T00:00:00Z'; end='2026-09-13T00:00:00Z'
a=ms(start); b=ms(end); day=86400000
# Five selected mature requests; two covered. Other rows challenge boundaries,
# maturity, invalid eligibility, and accidental filtering by note creation.
times=[a-1,a,a+1,a+day,b-1,b,b+day,a+day//2,-1]
requests=pd.DataFrame({'tweetId':[str(i) for i in range(1,10)]})
for field in FEEDS.values(): requests[field]=[str(t) for t in times]
# IDs 2 and 4 covered. ID 3 has an early note; ID 5 has a late note.
notes=pd.DataFrame([
 ('1','101',a+1000),('2','102',a),('2','103',a+2000),
 ('3','104',a),('4','105',a+day+2000),('5','106',b-1+7*day+1),
 ('6','107',b+1000)],columns=['tweetId','noteId','createdAtMillis']).astype('string')
checks=[]
def run(label, **kwargs):
    config=dict(cutoff='2026-10-16T04:02:00Z',start=start,end=end)
    config.update(kwargs)
    out=analyze_coverage(requests,notes,**config)
    field=FEEDS[config.get('feed','Standard')]; low=ms(config['start']) if config.get('start') else None; high=ms(config['end']) if config.get('end') else None
    limit=ms(config['cutoff']); window=7*day
    selected=[]; covered=[]
    # Separate integer/list oracle, not a pandas merge or backend subtraction.
    for row in requests.to_dict('records'):
        t=int(row[field]); tid=row['tweetId']
        if t<=0 or (low is not None and t<low) or (high is not None and t>=high) or t+window>limit: continue
        selected.append(tid)
        if any(n['tweetId']==tid and t<=int(n['createdAtMillis'])<=t+window and int(n['createdAtMillis'])<=limit for n in notes.to_dict('records')): covered.append(tid)
    gaps=sorted(set(selected)-set(covered)); actual=out['summary']
    assert sorted(out['requests'].tweetId)==sorted(selected)
    assert sorted(out['gaps'].tweetId)==gaps
    assert actual['no_observed_note']==len(gaps)
    assert len(out['gaps'])==int(out['weekly'].no_observed_note.sum())==len(gaps)
    checks.append(dict(case=label,selected_ids=sorted(selected),covered_ids=sorted(covered),gap_ids=gaps,eligible=actual['eligible_requests'],covered=actual['covered_requests'],gaps=actual['no_observed_note'],passed=True))
run('half-open range: start included, end excluded')
assert checks[-1]['selected_ids']==['2','3','4','5','8'] and checks[-1]['gap_ids']==['3','5','8']
run('equivalent timezone offsets',start='2026-09-10T17:00:00-07:00',end='2026-09-12T17:00:00-07:00')
run('start only',end=None)
run('end only',start=None)
run('empty date range cohort',start='2026-08-01T00:00:00Z',end='2026-08-02T00:00:00Z')
run('maturity boundary within selected dates',cutoff='2026-09-18T00:00:00Z')
for label,kw in [('equal bounds',dict(start=start,end=start)),('reversed bounds',dict(start=end,end=start)),('timezone omitted',dict(start='2026-09-11'))]:
    try: analyze_coverage(requests,notes,cutoff='2026-10-16T04:02:00Z',end=end,**kw) if 'end' not in kw else analyze_coverage(requests,notes,cutoff='2026-10-16T04:02:00Z',**kw)
    except ValueError as exc: checks.append(dict(case=label,passed=True,error=str(exc)))
    else: raise AssertionError(label)
report={'source_sha256':hashlib.sha256(Path(__file__).with_name('coverage_analysis.py').read_bytes()).hexdigest(),'pandas_version':pd.__version__,'scope':'Synthetic backend audit only; no UI or real-data provenance certification','checks':checks}
Path(__file__).with_name('audit_results.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))

"""Stream a raw ratings ZIP into the local prepared dataset without changing source files."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'outputs/dashboard'
COLS = ['noteId','raterParticipantId','createdAtMillis','helpfulnessLevel']


def merge_ratings(existing, incoming):
    combined = pd.concat([existing, incoming],ignore_index=True)
    exact = combined.duplicated(COLS)
    unique = combined.loc[~exact].copy()
    conflict = unique.duplicated(['noteId','raterParticipantId'],keep=False)
    return unique.loc[~conflict].copy(), int(exact.sum()), int(conflict.sum())


def add(path):
    path=Path(path)
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    sha=h.hexdigest()
    report=json.loads((OUT/'validation.json').read_text())
    if any(x['sha256']==sha for x in report.get('additional_ratings',[])):
        print('This archive has already been added.'); return
    notes=pd.read_parquet(OUT/'notes.parquet'); ids=set(notes.noteId)
    existing=pd.read_parquet(OUT/'ratings.parquet')
    parts=[]; scanned=0; invalid=0; after=0; before=0
    cutoff=pd.Timestamp(report['cutoff_utc']).value//1000000
    note_times=pd.to_numeric(notes.set_index('noteId').createdAtMillis)
    with zipfile.ZipFile(path) as z:
        members=[m for m in z.namelist() if m.endswith('.tsv') and not m.startswith('__MACOSX/')]
        if not members: raise ValueError('No TSV files in archive')
        for member in members:
            with z.open(member) as f:
                for chunk in pd.read_csv(f,sep='\t',dtype='string',keep_default_na=False,usecols=COLS,chunksize=100000):
                    scanned+=len(chunk)
                    chunk=chunk.loc[chunk.noteId.isin(ids)].copy()
                    t=pd.to_numeric(chunk.createdAtMillis,errors='coerce')
                    good=chunk.raterParticipantId.str.strip().ne('') & t.notna() & t.gt(0)
                    invalid+=int((~good).sum()); after+=int((good & t.gt(cutoff)).sum())
                    before+=int((good & t.lt(chunk.noteId.map(note_times))).sum())
                    chunk=chunk.loc[good & t.le(cutoff) & t.ge(chunk.noteId.map(note_times))].copy()
                    chunk['qc_key_valid']='True'
                    chunk['qc_valid_helpfulness']=chunk.helpfulnessLevel.str.strip().str.upper().isin(['HELPFUL','SOMEWHAT_HELPFUL','NOT_HELPFUL']).map(str)
                    chunk['meta_source_file']=member
                    if len(chunk): parts.append(chunk)
                    if scanned%1000000==0: print(f'Scanned {scanned:,} ratings',flush=True)
    incoming=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame(columns=COLS)
    merged,duplicates,conflicts=merge_ratings(existing,incoming)
    audit=dict(archive=path.name,sha256=sha,rows_scanned=scanned,usable_matched_rows=len(incoming),
        invalid_matched_rows=invalid,after_cutoff_matched_rows=after,precreation_matched_rows=before,
        duplicate_rows_removed=duplicates,conflicting_pair_rows_excluded=conflicts,
        ratings_before=len(existing),ratings_after=len(merged),notes_with_ratings_before=int(existing.noteId.nunique()),
        notes_with_ratings_after=int(merged.noteId.nunique()),cutoff_utc=report['cutoff_utc'],snapshot_verified=False)
    backup=OUT/'before_rating_import'
    backup.mkdir(exist_ok=True)
    for name in ['ratings.parquet','validation.json']: shutil.copy2(OUT/name,backup/name)
    merged.to_parquet(OUT/'ratings.next.parquet',index=False)
    report.setdefault('additional_ratings',[]).append(audit)
    report['notes_with_observed_ratings']=int(merged.noteId.nunique())
    report['scope']+=' Additional raw ratings imports are independently filtered and reported under additional_ratings; original cleaned-output checks refer to the initial inputs.'
    (OUT/'validation.next.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'ratings.next.parquet').replace(OUT/'ratings.parquet')
    (OUT/'validation.next.json').replace(OUT/'validation.json')
    print(json.dumps(audit,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('zip');add(p.parse_args().zip)

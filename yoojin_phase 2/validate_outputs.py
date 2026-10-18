"""Independent, bounded-memory audit of every source/output field and QC count."""
import argparse, hashlib, json, sqlite3, tempfile, zlib
from pathlib import Path
from collections import Counter
from contextlib import ExitStack
import pandas as pd

def validate(root, chunksize=50000, notes=None, engine="auto"):
    root=Path(root);success=json.loads((root/'SUCCESS.json').read_text())
    if engine=='native' or (engine=='auto' and success.get('all_supplied_rows_processed')):
        from native_validation import validate_native
        return validate_native(root,notes)
    results={'scope':'All supplied records' if success.get('all_supplied_rows_processed') else 'NOT full: bounded sample only','datasets':{}}
    join=None
    if notes:
        from integration_audit import JoinAudit
        first=json.loads((root/f"{success['reports'][0]}_validation.json").read_text())
        join=JoinAudit(notes,first['cutoff_ms'])
    for kind in success['reports']:
        with ExitStack() as resources:
            report=json.loads((root/f'{kind}_validation.json').read_text());counts=report['counts']
            if counts['exact_duplicates_removed']:
                from duplicate_audit import audit_removed_rows
                results['datasets'][kind]=audit_removed_rows(root,kind,report,chunksize,join)
                continue
            cap=report.get('max_rows');seen_input=seen_output=dups=0;qc=Counter();invalid=0
            reader=resources.enter_context(pd.read_csv(root/f'{kind}_clean.tsv.gz',sep='\t',dtype=str,keep_default_na=False,chunksize=chunksize))
            with tempfile.TemporaryDirectory() as temp:
                db=None
                if counts['exact_duplicates_removed']:
                    db=sqlite3.connect(str(Path(temp)/'seen.sqlite'))
                    db.execute('CREATE TABLE seen (h BLOB, row BLOB, PRIMARY KEY(h,row)) WITHOUT ROWID')
                for item in report['inputs']:
                    path=Path(item['path'])
                    if not path.exists(): raise FileNotFoundError(f'Original input required: {path}')
                    if path.stat().st_size!=item['bytes'] or path.stat().st_mtime_ns!=item['mtime_ns']:raise ValueError(f'Source changed after cleaning: {path}')
                    offset=0
                    for source in resources.enter_context(pd.read_csv(path,sep='\t',dtype=str,keep_default_na=False,chunksize=chunksize)):
                        if cap is not None:
                            source=source.iloc[:max(0,cap-seen_input)]
                            if source.empty:break
                        seen_input+=len(source)
                        record=pd.Series(range(offset+2,offset+len(source)+2),index=source.index);offset+=len(source)
                        expected=source
                        if db is not None:
                            keep=[]
                            for row in source.itertuples(index=False,name=None):
                                raw=json.dumps(row,ensure_ascii=False,separators=(',',':')).encode()
                                keep.append(db.execute('INSERT OR IGNORE INTO seen VALUES (?,?)',(hashlib.sha256(raw).digest(),zlib.compress(raw,1))).rowcount==1)
                            db.commit();dups+=len(source)-sum(keep);expected=source.loc[keep]
                        if expected.empty:continue
                        try:actual=reader.get_chunk(len(expected))
                        except StopIteration:raise ValueError('Output ended early')
                        pd.testing.assert_frame_equal(actual[report['columns']].reset_index(drop=True),expected.reset_index(drop=True))
                        if not actual.meta_source_file.eq(path.name).all():raise ValueError('Wrong source file provenance')
                        if actual.meta_source_record.tolist()!=record.loc[expected.index].astype(str).tolist():raise ValueError('Wrong source row provenance')
                        badnote=~actual.noteId.str.strip().str.fullmatch('[1-9][0-9]*')
                        if actual.qc_noteId_invalid.tolist()!=badnote.map(str).tolist():raise ValueError('Incorrect noteId flags')
                        badkey=badnote.copy()
                        if kind=='ratings':
                            badrater=actual.raterParticipantId.str.strip().eq('')
                            if actual.qc_raterParticipantId_invalid.tolist()!=badrater.map(str).tolist():raise ValueError('Incorrect participant flags')
                            badkey |= badrater
                            level=actual.helpfulnessLevel.str.strip().str.upper()
                            if actual.qc_valid_helpfulness.tolist()!=level.isin(['HELPFUL','SOMEWHAT_HELPFUL','NOT_HELPFUL']).map(str).tolist():raise ValueError('Incorrect helpfulness flags')
                        if actual.qc_key_valid.tolist()!=(~badkey).map(str).tolist():raise ValueError('Incorrect key flags')
                        invalid+=int(badkey.sum())
                        for col in actual:
                            if col.startswith('qc_'):
                                if not actual[col].isin(['True','False']).all():raise ValueError(f'Nonboolean QC: {col}')
                                qc[col]+=int(actual[col].eq('True').sum())
                        if join: join.add(kind,actual)
                        seen_output+=len(actual)
                        if seen_input%1000000<chunksize:print(f'{kind} independently verified {seen_input:,} input rows',flush=True)
                    if cap is not None and seen_input>=cap:break
                try:extra=reader.get_chunk(1)
                except StopIteration:extra=pd.DataFrame()
                if len(extra):raise ValueError('Unexplained extra output rows')
                if db:db.close()
            if seen_input!=counts['input'] or seen_output!=counts['output'] or dups!=counts['exact_duplicates_removed']:raise ValueError('Row reconciliation mismatch')
            if invalid!=counts.get('invalid_key_retained',0):raise ValueError('Invalid key count mismatch')
            for col,n in qc.items():
                if n!=counts.get(col,0):raise ValueError(f'QC count mismatch: {col}')
            results['datasets'][kind]={'checks':'PASS','input_rows':seen_input,'rows':seen_output,'exact_duplicates_removed':dups,'source_fields_preserved':True,'provenance_checked':True,'invalid_keys_retained':invalid,'qc_counts':dict(qc)}
    if join:join.finish(root)
    (root/'independent_validation.json').write_text(json.dumps(results,indent=2));return results
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--chunksize',type=int,default=50000);p.add_argument('--notes',nargs='+');p.add_argument('--engine',choices=['auto','native','pandas'],default='auto');a=p.parse_args()
    if a.chunksize<=0:p.error('chunksize must be positive')
    print(json.dumps(validate(a.root,a.chunksize,a.notes,a.engine),indent=2))

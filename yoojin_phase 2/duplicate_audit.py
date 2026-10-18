"""Stream source/output alignment; prove each removed row equals an earlier retained row.

Memory depends on chunk size and the number of removals, not total source size.
No full-row SQLite index is built for tens of millions of source records.
"""
import json
from pathlib import Path
from collections import Counter
from contextlib import ExitStack
import pandas as pd

def source_chunks(report,size):
    total=0;cap=report.get('max_rows')
    for file_index,item in enumerate(report['inputs']):
        path=Path(item['path']);stat=path.stat()
        if stat.st_size!=item['bytes'] or stat.st_mtime_ns!=item['mtime_ns']:raise ValueError('Original input changed')
        offset=0
        with pd.read_csv(path,sep='\t',dtype=str,keep_default_na=False,chunksize=size) as reader:
            for frame in reader:
                if cap is not None:frame=frame.iloc[:max(0,cap-total)]
                if frame.empty:break
                frame=frame.reset_index(drop=True)
                yield file_index,path.name,offset,total,frame
                offset+=len(frame);total+=len(frame)
                if cap is not None and total>=cap:return

class BufferedOutput:
    def __init__(self,reader,files,size):self.reader=reader;self.order=files;self.size=size;self.pending=pd.DataFrame();self.eof=False
    def take(self,file_index,start,end):
        while not self.eof:
            if len(self.pending):
                last=self.pending.iloc[-1];last_file=self.order[last.meta_source_file];last_record=int(last.meta_source_record)
                if last_file>file_index or (last_file==file_index and last_record>=end):break
            try:new=self.reader.get_chunk(self.size)
            except StopIteration:self.eof=True;break
            self.pending=pd.concat([self.pending,new],ignore_index=True) if len(self.pending) else new.reset_index(drop=True)
        if self.pending.empty:return self.pending
        fi=self.pending.meta_source_file.map(self.order)
        if fi.isna().any():raise ValueError('Unknown output source file')
        rec=pd.to_numeric(self.pending.meta_source_record,errors='raise')
        if ((fi<file_index)|((fi==file_index)&rec.lt(start))).any():raise ValueError('Output provenance is out of source order')
        mask=fi.eq(file_index)&rec.le(end)
        picked=self.pending.loc[mask].reset_index(drop=True);self.pending=self.pending.loc[~mask].reset_index(drop=True)
        if len(picked) and not pd.to_numeric(picked.meta_source_record).is_monotonic_increasing:raise ValueError('Non-monotonic source record numbers')
        if len(picked) and picked.meta_source_record.duplicated().any():raise ValueError('Repeated source provenance')
        return picked
    def finish(self):
        if len(self.pending):raise ValueError('Extra output rows')
        try:extra=self.reader.get_chunk(1)
        except StopIteration:return
        if len(extra):raise ValueError('Extra output rows')

def audit_removed_rows(root,kind,report,size,join=None):
    counts=report['counts'];columns=report['columns'];files={Path(item['path']).name:i for i,item in enumerate(report['inputs'])}
    if len(files)!=len(report['inputs']):raise ValueError('Input basenames must be unique for provenance audit')
    keys=['noteId','raterParticipantId','createdAtMillis'] if kind=='ratings' else ['noteId','createdAtMillis']
    keyindices=[columns.index(c) for c in keys]
    removed={};removed_positions=set();candidate_keys=set();qc=Counter();seen_input=seen_output=invalid=dups=0
    with pd.read_csv(Path(root)/f'{kind}_clean.tsv.gz',sep='\t',dtype=str,keep_default_na=False,chunksize=size) as reader:
        buffered=BufferedOutput(reader,files,size)
        for fi,name,offset,base,source in source_chunks(report,size):
            actual=buffered.take(fi,offset+2,offset+len(source)+1)
            locations=pd.to_numeric(actual.meta_source_record).astype(int).to_numpy()-offset-2 if len(actual) else []
            expected=source.iloc[locations].reset_index(drop=True)
            if len(actual):pd.testing.assert_frame_equal(actual[columns].reset_index(drop=True),expected)
            keep=set(map(int,locations))
            for i in (j for j in range(len(source)) if j not in keep):
                row=tuple(source.iloc[i]);seq=base+i
                removed[row]=min(seq,removed.get(row,seq));removed_positions.add(seq)
                candidate_keys.add(tuple(row[c] for c in keyindices));dups+=1
            seen_input+=len(source);seen_output+=len(actual)
            if len(actual):
                badnote=~actual.noteId.str.strip().str.fullmatch('[1-9][0-9]*')
                if actual.qc_noteId_invalid.tolist()!=badnote.map(str).tolist():raise ValueError('Incorrect note flags')
                badkey=badnote.copy()
                if kind=='ratings':
                    badrater=actual.raterParticipantId.str.strip().eq('')
                    if actual.qc_raterParticipantId_invalid.tolist()!=badrater.map(str).tolist():raise ValueError('Incorrect participant flags')
                    badkey|=badrater
                    level=actual.helpfulnessLevel.str.strip().str.upper()
                    if actual.qc_valid_helpfulness.tolist()!=level.isin(['HELPFUL','SOMEWHAT_HELPFUL','NOT_HELPFUL']).map(str).tolist():raise ValueError('Incorrect helpfulness flags')
                if actual.qc_key_valid.tolist()!=(~badkey).map(str).tolist():raise ValueError('Incorrect key flags')
                invalid+=int(badkey.sum())
                for col in actual:
                    if col.startswith('qc_'):
                        if not actual[col].isin(['True','False']).all():raise ValueError('Nonboolean QC')
                        qc[col]+=int(actual[col].eq('True').sum())
                if join:join.add(kind,actual)
            if seen_input%1000000<size:print(f'{kind} independently aligned {seen_input:,} input rows',flush=True)
        buffered.finish()
    if (seen_input,seen_output,dups)!=(counts['input'],counts['output'],counts['exact_duplicates_removed']):raise ValueError('Dedup row counts differ')
    # A second streaming pass visits only candidate keys for exact comparisons.
    # Every removed full row must equal an earlier source row that was retained.
    found=set()
    for fi,name,offset,base,source in source_chunks(report,size):
        mask=pd.MultiIndex.from_frame(source[keys]).isin(candidate_keys)
        for values in source.loc[mask].itertuples(index=True,name=None):
            seq=base+int(values[0]);row=tuple(values[1:])
            if row in removed and seq<removed[row] and seq not in removed_positions:found.add(row)
        if len(found)==len(removed):break
    if len(found)!=len(removed):raise ValueError('A removed source row has no earlier exact retained match')
    if invalid!=counts.get('invalid_key_retained',0):raise ValueError('Invalid key count mismatch')
    for col,n in qc.items():
        if n!=counts.get(col,0):raise ValueError(f'QC count mismatch: {col}')
    return {'checks':'PASS','input_rows':seen_input,'rows':seen_output,'exact_duplicates_removed':dups,'source_fields_preserved':True,'provenance_checked':True,'removed_rows_verified_against_earlier_retained_source':True,'invalid_keys_retained':invalid,'qc_counts':dict(qc)}

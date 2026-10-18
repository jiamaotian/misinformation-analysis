"""Audit joins and additive metrics against explicitly supplied Notes shards."""
import glob,json
from pathlib import Path
from collections import Counter,defaultdict
import pandas as pd
class JoinAudit:
    def __init__(self,patterns,cutoff_ms):
        self.files=sorted({str(Path(p).resolve()) for pattern in patterns for p in glob.glob(str(Path(pattern).expanduser()))})
        if not self.files:raise ValueError('No Notes files matched')
        notes=pd.concat([pd.read_csv(f,sep='\t',dtype=str,keep_default_na=False) for f in self.files],ignore_index=True).drop_duplicates()
        notes['noteId_clean']=notes.noteId.str.strip()
        self.invalid=int((~notes.noteId_clean.str.fullmatch('[1-9][0-9]*')).sum())
        notes=notes.loc[notes.noteId_clean.str.fullmatch('[1-9][0-9]*')]
        if notes.noteId_clean.duplicated().any():raise ValueError('Conflicting Notes noteId: reconcile before joining')
        self.notes=notes.set_index('noteId_clean');self.cutoff=cutoff_ms;self.stats={};self.matched={};self.response=[];self.pernote=defaultdict(lambda:[0,0])
    def add(self,kind,x):
        c=self.stats.setdefault(kind,Counter());ids=x.noteId_clean;m=ids.isin(self.notes.index)
        self.matched.setdefault(kind,set()).update(ids[m]);c['rows_matching_supplied_notes']+=int(m.sum());c['rows_unmatched_supplied_notes']+=int((~m).sum())
        if kind=='status':
            note_start=ids.map(self.notes.createdAtMillis);start=pd.to_numeric(note_start,errors='coerce')
            end=pd.to_numeric(x.timestampMillisOfFirstNonNMRStatus_clean,errors='coerce')
            mismatch=m & note_start.ne(x.createdAtMillis)
            c['creation_time_mismatches']+=int(mismatch.sum())
            valid=m & ~mismatch & x.qc_key_valid.eq('True') & x.firstNonNMRStatus_clean.isin(['CURRENTLY_RATED_HELPFUL','CURRENTLY_RATED_NOT_HELPFUL']) & start.ge(0) & end.ge(start) & start.le(self.cutoff) & end.le(self.cutoff)
            self.response.extend(((end-start)/3600000)[valid].tolist());c['matched_response_eligible']+=int(valid.sum())
        else:
            valid=x.qc_key_valid.eq('True') & x.qc_valid_helpfulness.eq('True') & x.qc_created_by_cutoff.eq('True')
            helpful=x.helpfulnessLevel_clean.eq('HELPFUL')
            c['valid_ratings_by_cutoff']+=int(valid.sum());c['helpful_ratings_by_cutoff']+=int((valid & helpful).sum())
            c['repeated_keys_retained']+=int(x.qc_repeated_key.eq('True').sum())
            sub=pd.DataFrame({'noteId':ids[valid&m],'helpful':helpful[valid&m].astype(int)})
            for nid,row in sub.groupby('noteId').helpful.agg(['size','sum']).iterrows():
                self.pernote[nid][0]+=int(row['size']);self.pernote[nid][1]+=int(row['sum'])
    def finish(self,root):
        report={'notes_files':self.files,'notes_unique_valid_ids':len(self.notes),'invalid_note_ids_excluded_from_join':self.invalid,'notes_scope':'Supplied raw Notes shards; NOT verified as Peyton final output','status_join_cardinality':'many source Notes checked unique; Status uniqueness checked in cleaner report','datasets':{}}
        for kind,c in self.stats.items():
            d=dict(c);d['notes_without_match']=len(self.notes)-len(self.matched[kind])
            if kind=='ratings':d['observed_helpfulness']=c['helpful_ratings_by_cutoff']/c['valid_ratings_by_cutoff'] if c['valid_ratings_by_cutoff'] else None
            report['datasets'][kind]=d
        report['matched_notes_response_median_hours']=float(pd.Series(self.response).median()) if self.response else None
        report['limitations']=['Incomplete release inventory; unmatched is not zero activity','Peyton final source/output not accessible through supplied private GitHub link','Different local file modification dates do not verify a common download snapshot','Cutoff inherited from original notebook; team agreement remains required']
        root=Path(root);(root/'integration_with_supplied_notes.json').write_text(json.dumps(report,indent=2))
        rows=[{'noteId':nid,'valid_ratings':v[0],'helpful_ratings':v[1],'observed_helpfulness':v[1]/v[0]} for nid,v in sorted(self.pernote.items())]
        pd.DataFrame(rows,columns=['noteId','valid_ratings','helpful_ratings','observed_helpfulness']).to_csv(root/'ratings_for_supplied_notes.csv',index=False)
        return report

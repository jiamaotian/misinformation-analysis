import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
import zipfile

import pyarrow as pa

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from clean_communitynotes import (HEADERS, FLAG_SCHEMA, batches, clean_query, connection,
    flag_query, issue_rules, nested_requests, source_expr)
from validate_communitynotes import duplicate_checks


class CleaningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.out=Path(self.tmp.name)
        self.c=connection(self.out)
    def tearDown(self):
        self.c.close();self.tmp.cleanup()
    def clean(self,group,rows):
        table=pa.table({n:[r.get(n,'') for r in rows] for n in HEADERS[group]})
        table=table.append_column('_source_file',pa.array(['fixture.zip']*len(rows))).append_column('_source_member',pa.array(['fixture.tsv']*len(rows))).append_column('_source_row',pa.array(range(1,len(rows)+1),type=pa.int64()))
        self.c.register('raw',table)
        q=flag_query(group,issue_rules(group))
        flags=self.c.execute(q,{'run_time':'2026-10-02T00:00:00Z'} if '$run_time' in q else {}).to_arrow_table()
        result=self.c.execute(clean_query(group)).to_arrow_table()
        self.c.register('result',result)
        # Every original token must be exactly recoverable, even invalid values.
        rebuilt=self.c.execute('SELECT '+','.join(source_expr(n)+' AS "'+n+'"' for n in HEADERS[group])+' FROM result').to_arrow_table()
        for n in HEADERS[group]:self.assertEqual(rebuilt[n].to_pylist(),table[n].to_pylist())
        return result.to_pylist(),flags.to_pylist()

    def test_sentinels_do_not_become_epoch_dates(self):
        rows,flags=self.clean('batSignals',[{'tweetId':'123','noteRequestFeedEligibleAtMillis':'-1','apiSmallFeedEligibleAtMillis':'1790000000000','apiLargeFeedEligibleAtMillis':'0'}])
        self.assertEqual(rows[0]['noteRequestFeedEligibleAtMillis'],-1)
        self.assertIsNone(rows[0]['noteRequestFeedEligibleAtMillis_utc'])
        self.assertEqual(rows[0]['noteRequestFeedEligibleAtMillis_state'],'ineligible')
        self.assertEqual(rows[0]['apiSmallFeedEligibleAtMillis_utc'].utcoffset().total_seconds(),0)
        self.assertTrue(any(f['rule']=='invalid_timestamp' for f in flags))

    def test_pcrh_signed_history_and_minute_metadata(self):
        vals=['','-1','1790000000000','-1790000000000','0']
        rows,flags=self.clean('noteStatusHistory',[{'noteId':str(i+1),'timestampMillisAbovePcrhThreshold':v,'timestampMinuteOfFinalScoringOutput':'29845679'} for i,v in enumerate(vals)])
        self.assertEqual([r['pcrh_state'] for r in rows],['no_recorded_event','cleared','above_threshold','no_longer_above','invalid'])
        self.assertEqual(rows[2]['timestampMillisAbovePcrhThreshold_utc'],rows[3]['timestampMillisAbovePcrhThreshold_utc'])
        self.assertEqual(rows[0]['timestampMinuteOfFinalScoringOutput'],29845679)
        self.assertNotIn('timestampMinuteOfFinalScoringOutput_utc',rows[0])

    def test_legacy_ratings_not_imputed(self):
        rows,flags=self.clean('ratings',[{'noteId':'123','version':'1','helpful':'1','notHelpful':'0','ratedOnTweetId':'-1','suggestionId':'-1','agree':'1','disagree':'1'}])
        self.assertIsNone(rows[0]['helpfulnessLevel'])
        self.assertTrue(rows[0]['helpful'])
        self.assertIsNone(rows[0]['ratedOnTweetId'])
        self.assertTrue(any(f['rule']=='contradictory_binary_pair' for f in flags))

    def test_unusual_values_preserved_and_flagged(self):
        original='  中文 “quoted” https://example.org/a  '
        rows,flags=self.clean('notes',[{'noteId':'9007199254740993123','tweetId':'-1','classification':' NEW_CATEGORY ','summary':original,'isMediaNote':'2','createdAtMillis':'12.5'}])
        self.assertEqual(rows[0]['noteId'],'9007199254740993123')
        self.assertEqual(rows[0]['summary'],original)
        self.assertEqual(rows[0]['summary_trimmed'],original.strip())
        self.assertEqual(rows[0]['classification'],'NEW_CATEGORY')
        self.assertIsNone(rows[0]['isMediaNote'])
        self.assertIsNone(rows[0]['createdAtMillis_utc'])
        self.assertTrue({'invalid_boolean','unknown_category','invalid_timestamp'} <= {f['rule'] for f in flags})

    def test_enrollment_integral_group_and_contradiction(self):
        rows,flags=self.clean('userEnrollment',[{'participantId':'A'*64,'modelingGroup':'33.0','timestampOfLastEarnOut':'1','numberOfTimesEarnedOut':'2','modelingPopulation':'EXPANSION_PLUS'}])
        self.assertEqual(rows[0]['modelingGroup'],33)
        self.assertIsNone(rows[0]['timestampOfLastEarnOut_utc'])
        self.assertIsNone(rows[0]['never_earned_out_consistent'])
        self.assertTrue(any(f['rule']=='earnout_count_disagreement' for f in flags))
        rows,_=self.clean('userEnrollment',[{'modelingGroup':'13.5'}])
        self.assertIsNone(rows[0]['modelingGroup'])

    def test_missing_history_not_filled_and_submodel_retained(self):
        rows,flags=self.clean('noteStatusHistory',[{'noteId':'123','currentStatus':'CURRENTLY_RATED_HELPFUL','currentCoreStatus':'FIRM_REJECT','currentExpansionStatus':'NEEDS_YOUR_HELP','timestampMillisOfCurrentStatus':'1790000000000'}])
        self.assertIsNone(rows[0]['timestampMillisOfFirstNonNMRStatus_utc'])
        self.assertEqual(rows[0]['currentCoreStatus'],'FIRM_REJECT')
        self.assertTrue(any(f['rule']=='resolved_missing_history' for f in flags))

    def test_large_nested_json_urls_and_unknown_keys(self):
        raw=json.dumps([{'suggestion_id':9007199254740993123,'suggestion':'字'*160000,'source_link':'bad://url','extra':'keep'}])
        b=pa.table({'sourceLinks':['ttps://example.org'], 'suggestions':[raw]})
        links,parsed,flags=nested_requests(b,Path('fixture.zip'),'fixture.tsv',0)
        self.assertEqual(links[0].as_py(),['ttps://example.org'])
        obj=json.loads(parsed[0].as_py())[0]
        self.assertEqual(obj['suggestion_id'],'9007199254740993123')
        self.assertEqual(obj['extra'],'keep')
        self.assertEqual(flags.num_rows,2)

    def test_tsv_literal_quotes_large_fields_and_fail_closed(self):
        p=self.out/'batSignals-00000.zip'
        vals=['123','-1','-1','-1','-1','',json.dumps([{'suggestion':'"'+'x'*160000}])]
        with zipfile.ZipFile(p,'w') as z:z.writestr('batSignals.tsv','\t'.join(HEADERS['batSignals'])+'\n'+'\t'.join(vals)+'\n')
        result=list(batches(p,'batSignals'))
        self.assertEqual(result[0][0]['suggestions'][0].as_py(),vals[-1])
        with zipfile.ZipFile(p,'w') as z:z.writestr('batSignals.tsv','\t'.join(HEADERS['batSignals'])+'\n123\tbad\n')
        with self.assertRaises(pa.ArrowInvalid):list(batches(p,'batSignals'))

    def test_duplicate_values_not_deduplicated_after_normalization(self):
        # Only two identical source rows are duplicates; whitespace-different source stays.
        self.clean('notes',[{'noteId':'123','classification':'NOT_MISLEADING'}, {'noteId':'123','classification':'NOT_MISLEADING'}, {'noteId':'123','classification':' NOT_MISLEADING '}])
        path=self.out/'cleaned'/'notes'/'notes-00000.parquet';path.parent.mkdir(parents=True)
        self.c.execute(f"COPY result TO '{path}' (FORMAT PARQUET)")
        self.c.execute(f"CREATE VIEW notes AS SELECT * FROM read_parquet('{path}')")
        r=duplicate_checks(self.c,self.out,'notes')
        self.assertEqual(r['retained_cleaned_rows'],3)
        self.assertEqual(r['identical_copies_excluded_from_analysis_view'],1)
        self.assertEqual(r['conflicting_key_groups_retained'],1)

    def test_complete_cli_reconciles_rows_and_hashes(self):
        raw=self.out/'raw';raw.mkdir()
        output=self.out/'output'
        for group,columns in HEADERS.items():
            row={n:'' for n in columns}
            values={'noteId':'123','tweetId':'123','raterParticipantId':'A'*64,'noteAuthorParticipantId':'A'*64,'participantId':'A'*64,'createdAtMillis':'1790000000000','classification':'NOT_MISLEADING','summary':' 中文 ','version':'1','helpful':'1','notHelpful':'0','currentStatus':'CURRENTLY_RATED_HELPFUL','currentCoreStatus':'FIRM_REJECT','enrollmentState':'earnedIn','modelingPopulation':'CORE','modelingGroup':'13.0','timestampOfLastEarnOut':'1','numberOfTimesEarnedOut':'0','sourceLinks':'ttps://example.org','suggestions':'[]'}
            row.update({k:v for k,v in values.items() if k in row})
            with zipfile.ZipFile(raw/(group+'-00000.zip'),'w') as z:
                z.writestr(group+'.tsv','\t'.join(columns)+'\n'+'\t'.join(row[n] for n in columns)+'\n')
        script=Path(__file__).resolve().parents[1]/'scripts'/'clean_communitynotes.py'
        completed=subprocess.run([sys.executable,str(script),'--raw-dir',str(raw),'--output-dir',str(output),'--workers','2'],capture_output=True,text=True,timeout=90)
        self.assertEqual(completed.returncode,0,completed.stderr)
        result=json.loads((output/'reports'/'05_validation.json').read_text())
        self.assertTrue(result['source_hashes_unchanged'])
        self.assertTrue(result['joins_preserve_analysis_row_counts'])
        self.c.execute((output/'catalog.sql').read_text())
        for group in HEADERS:
            self.assertEqual(self.c.execute('SELECT count(*) FROM "'+group+'"').fetchone()[0],1)
        self.assertIsNone(self.c.execute('SELECT helpfulnessLevel FROM ratings').fetchone()[0])
        self.assertEqual(self.c.execute("SELECT typed_value FROM notes_cell_changes WHERE target_column='summary_trimmed'").fetchone()[0],'中文')
        self.assertEqual(self.c.execute("SELECT modelinGgroup FROM userEnrollment_source_values").fetchone()[0],'13.0')

    def test_rating_duplicates_within_and_across_partitions(self):
        base={'noteId':'123','raterParticipantId':'A'*64,'version':'1','helpful':'1','notHelpful':'0'}
        folder=self.out/'cleaned'/'ratings';folder.mkdir(parents=True)
        self.clean('ratings',[base,base])
        self.c.execute(f"COPY (SELECT * REPLACE ('ratings-00000.zip' AS _source_file) FROM result) TO '{folder/'ratings-00000.parquet'}' (FORMAT PARQUET)")
        self.clean('ratings',[dict(base,helpful='0',notHelpful='1')])
        self.c.execute(f"COPY (SELECT * REPLACE ('ratings-00001.zip' AS _source_file) FROM result) TO '{folder/'ratings-00001.parquet'}' (FORMAT PARQUET)")
        self.c.execute(f"CREATE VIEW ratings AS SELECT * FROM read_parquet('{folder/'*.parquet'}')")
        r=duplicate_checks(self.c,self.out,'ratings')
        self.assertEqual(r['duplicate_key_groups'],1)
        self.assertEqual(r['identical_copies_excluded_from_analysis_view'],1)
        self.assertEqual(r['conflicting_key_groups_retained'],1)


if __name__=='__main__':unittest.main()

"""Synthetic behavior checks; these are not findings about the real datasets."""
from tempfile import TemporaryDirectory
from pathlib import Path
import pandas as pd
from clean_notes_requests import run, REQUEST_TIMES


def test_workflow():
    with TemporaryDirectory() as folder:
        folder = Path(folder)
        notes = pd.DataFrame([
            ['001', '9007199254740993', '1609459200000', 'NA'],
            ['001', '9007199254740993', '1609459200000', 'NA'],
            ['002', '9007199254740993', 'bad', '  '],
            ['002', '123', '-1', 'conflicting note'],
            ['', '', '', 'missing IDs'],
            ['003', '456', '1893456000000', 'future'],
            ['004', '-1', '999999999999999999999999', 'out of range'],
        ], columns=['noteId', 'tweetId', 'createdAtMillis', 'summary'])
        requests = pd.DataFrame([
            ['9007199254740993', '1609459200000', '', '0', 'bad'],
            ['789', '1609459200000', '', '', ''],
            ['789', '1609459200001', '', '', ''],
        ], columns=['tweetId'] + REQUEST_TIMES)
        np, rp = folder / 'notes.tsv', folder / 'requests.tsv'
        notes.to_csv(np, sep='\t', index=False)
        requests.to_csv(rp, sep='\t', index=False)
        tables, manifest = run(np, rp, folder / 'out', cutoff='2026-10-15T00:00:00Z')
        cleaned = tables['notes_clean']
        assert len(cleaned) == 6
        assert cleaned.qc_key_conflict.sum() == 2
        assert cleaned.qc_createdAtMillis_invalid.sum() == 2
        assert cleaned.qc_createdAtMillis_nonpositive.sum() == 1
        assert cleaned.qc_createdAtMillis_after_cutoff.sum() == 1
        assert str(cleaned.iloc[0].createdAtMillis_utc) == '2021-01-01 00:00:00+00:00'
        assert cleaned.iloc[0].noteId == '001'
        assert cleaned.iloc[0].summary == 'NA'
        rel = tables['tweet_relationships'].set_index('tweetId')
        assert rel.loc['9007199254740993', 'notes_rows'] == 2
        assert rel.loc['789', 'request_rows'] == 2
        assert rel.loc['456', 'relationship'] == 'notes_only'
        assert '-1' not in rel.index
        assert manifest['checks']['saved_original_fields_verified']
        preview, pm = run(np, rp, folder / 'out', preview_rows=1)
        assert pm['scope'] == 'preview'
        assert (folder / 'out/preview/notes_clean.csv').is_file()
        assert len(pd.read_csv(folder / 'out/notes_clean.csv')) == 6
    print('Synthetic workflow checks passed.')


if __name__ == '__main__':
    test_workflow()

"""Peyton's Phase 2 cleaning. Run this file or use the accompanying notebook."""
from pathlib import Path
import argparse
import hashlib
import json
import pandas as pd

DEFAULT_RAW = Path(__file__).resolve().parent / 'data' / 'raw'
SOURCE_URL = 'https://communitynotes.x.com/guide/en/under-the-hood/download-data'
REQUEST_TIMES = ['noteRequestFeedEligibleAtMillis', 'apiSmallFeedEligibleAtMillis',
                 'apiLargeFeedEligibleAtMillis', 'apiXlFeedEligibleAtMillis']


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def blank(series):
    return series.str.strip().eq('')


def valid_id(series):
    # Positive decimal identifiers; never pass IDs through floating point.
    return series.str.fullmatch(r'[0-9]+').fillna(False) & series.str.contains(r'[1-9]', regex=True).fillna(False)


def load_source(path, required, preview_rows=None):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f'Missing input: {path}. Update the input path or place the agreed file there.')
    df = pd.read_csv(path, sep='\t', dtype='string', keep_default_na=False, nrows=preview_rows)
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f'{path.name}: missing required columns {sorted(missing)}')
    if any(c.startswith('qc_') or c.endswith('_utc') for c in df.columns):
        raise ValueError('Input contains derived-column names; use the original TSV.')
    return df


def profile(df, dataset, stage):
    return pd.DataFrame([dict(dataset=dataset, stage=stage, column=c,
        dtype=str(df[c].dtype), rows=len(df), empty=int(df[c].eq('').sum()),
        whitespace_only=int((blank(df[c]) & df[c].ne('')).sum()),
        blank_total=int(blank(df[c]).sum())) for c in df.columns])


def prepare(raw, dataset, key, timestamps, cutoff=None):
    """Remove exact source-row repeats only. Preserve all other original values."""
    source_columns = list(raw.columns)
    clean = raw.drop_duplicates().copy()
    clean['qc_source_row'] = clean.index + 1  # 1-based data-record number, excluding header
    for col in ['tweetId'] + (['noteId'] if dataset == 'notes' else []):
        clean[f'qc_{col}_missing'] = blank(clean[col])
        clean[f'qc_{col}_invalid'] = ~blank(clean[col]) & ~valid_id(clean[col])
    clean['qc_key_conflict'] = valid_id(clean[key]) & clean.duplicated(key, keep=False)
    for col in timestamps:
        values = clean[col]
        missing = blank(values)
        integer = values.str.fullmatch(r'-?\d+').fillna(False)
        # Conversion is for dates only; source milliseconds remain exact strings.
        numeric = pd.to_numeric(values.where(integer), errors='coerce')
        # Bound conversion to pandas nanosecond-safe dates before casting.
        safe = numeric.where(numeric.between(-9223372036854, 9223372036854))
        dates = pd.to_datetime(safe.astype('Int64'), unit='ms', utc=True, errors='coerce')
        clean[f'{col}_utc'] = dates.where(numeric.gt(0))
        clean[f'qc_{col}_missing'] = missing
        clean[f'qc_{col}_invalid'] = ~missing & (~integer | dates.isna())
        clean[f'qc_{col}_nonpositive'] = numeric.le(0).fillna(False)
        if cutoff is not None:
            clean[f'qc_{col}_after_cutoff'] = dates.gt(cutoff).fillna(False)
    for col in source_columns:
        if col.startswith(('misleading', 'notMisleading')) or col in ['trustworthySources', 'isMediaNote', 'isCollaborativeNote']:
            clean[f'qc_{col}_unexpected_binary'] = ~blank(clean[col]) & ~clean[col].isin(['0', '1'])
    # Do not interpret eligibility ordering or blanks without documented semantics.
    pd.testing.assert_frame_equal(clean[source_columns], raw.drop_duplicates())
    reconciliation = dict(dataset=dataset, input_rows=len(raw), output_rows=len(clean),
        exact_duplicate_rows_removed=int(raw.duplicated().sum()),
        conflicting_key_rows=int(clean['qc_key_conflict'].sum()),
        original_columns=len(source_columns), added_columns=len(clean.columns)-len(source_columns))
    assert reconciliation['input_rows'] == reconciliation['output_rows'] + reconciliation['exact_duplicate_rows_removed']
    flags = [dict(dataset=dataset, flag=c, count=int(clean[c].sum()))
             for c in clean if c.startswith('qc_') and c != 'qc_source_row']
    return clean, reconciliation, flags


def relationships(notes, requests):
    """Aggregate first: this relationship report cannot multiply source rows."""
    n = notes.loc[valid_id(notes.tweetId)].groupby('tweetId').size().rename('notes_rows')
    r = requests.loc[valid_id(requests.tweetId)].groupby('tweetId').size().rename('request_rows')
    report = pd.concat([n, r], axis=1).fillna(0).astype('int64').reset_index()
    report['relationship'] = 'both'
    report.loc[report.request_rows.eq(0), 'relationship'] = 'notes_only'
    report.loc[report.notes_rows.eq(0), 'relationship'] = 'requests_only'
    assert report.notes_rows.sum() == valid_id(notes.tweetId).sum()
    assert report.request_rows.sum() == valid_id(requests.tweetId).sum()
    return report


def run(notes_path=DEFAULT_RAW / 'notes-00001.tsv', requests_path=DEFAULT_RAW / 'batSignals-00000.tsv',
        output_dir=None, cutoff=None, snapshot_label=None, preview_rows=None):
    if preview_rows is not None and preview_rows < 1:
        raise ValueError('preview_rows must be positive or None')
    if cutoff is not None:
        cutoff = pd.Timestamp(cutoff)
        if cutoff.tzinfo is None:
            raise ValueError('Cutoff must include a timezone, e.g. 2026-10-15T00:00:00Z')
        cutoff = cutoff.tz_convert('UTC')
    out = Path(output_dir or Path(__file__).parent / 'outputs').expanduser().resolve()
    if preview_rows is not None:
        out = out / 'preview'
    paths = {'notes': Path(notes_path).expanduser().resolve(),
             'requests': Path(requests_path).expanduser().resolve()}
    # Validate both paths before spending time on either dataset.
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(f'Missing input: {path}. Update the notebook configuration.')
        if out == path.parent or path.is_relative_to(out):
            raise ValueError('Keep source inputs outside the output folder.')
    hashes = {name: sha256(path) for name, path in paths.items()}
    raw_notes = load_source(paths['notes'], ['noteId', 'tweetId', 'createdAtMillis'], preview_rows)
    raw_requests = load_source(paths['requests'], ['tweetId'] + REQUEST_TIMES, preview_rows)
    notes, ncounts, nflags = prepare(raw_notes, 'notes', 'noteId', ['createdAtMillis'], cutoff)
    requests, rcounts, rflags = prepare(raw_requests, 'requests', 'tweetId', REQUEST_TIMES, cutoff)
    relations = relationships(notes, requests)
    profiles = pd.concat([profile(raw_notes, 'notes', 'before'),
        profile(notes[list(raw_notes.columns)], 'notes', 'after'),
        profile(raw_requests, 'requests', 'before'),
        profile(requests[list(raw_requests.columns)], 'requests', 'after')], ignore_index=True)
    out.mkdir(parents=True, exist_ok=True)
    tables = {'notes_clean': notes, 'note_requests_clean': requests,
              'column_profile': profiles, 'cleaning_report': pd.DataFrame([ncounts, rcounts]),
              'quality_flags': pd.DataFrame(nflags + rflags), 'tweet_relationships': relations,
              'relationship_summary': relations.groupby('relationship').size().rename('distinct_tweets').reset_index()}
    for name, df in tables.items():
        df.to_csv(out / f'{name}.csv', index=False)
    for name, df in [('notes', notes), ('requests', requests)]:
        flags = [c for c in df if c.startswith('qc_') and c != 'qc_source_row']
        df.loc[df[flags].any(axis=1)].head(100).to_csv(out / f'{name}_flagged_sample.csv', index=False)
        # Verify disk output IDs and source fields, including literal text and blanks.
        saved = pd.read_csv(out / ('notes_clean.csv' if name == 'notes' else 'note_requests_clean.csv'),
                            dtype='string', keep_default_na=False)
        raw = raw_notes if name == 'notes' else raw_requests
        pd.testing.assert_frame_equal(saved[list(raw.columns)], raw.drop_duplicates().reset_index(drop=True))
    assert hashes == {name: sha256(path) for name, path in paths.items()}, 'Source file changed during run'
    manifest = dict(scope='preview' if preview_rows else 'full agreed files', preview_rows=preview_rows,
        source_url=SOURCE_URL, snapshot_label=snapshot_label, cutoff_utc=str(cutoff) if cutoff is not None else None,
        pandas_version=pd.__version__, inputs={name: {'path': str(path), 'sha256': hashes[name]} for name, path in paths.items()},
        policy='Remove exact duplicate source rows; retain and flag all other concerns; preserve original fields.',
        limitations=['Agreed files do not establish platform-wide coverage.',
                     'Missing eligibility dates and nonpositive values are flagged, not assigned undocumented meanings.',
                     'No eligibility ordering or request-to-note causal/timing assumptions are applied.',
                     'Future-date validation is unavailable without an explicit snapshot cutoff.' if cutoff is None else 'Dates checked against supplied cutoff.',
                     'Snapshot date/version unknown.' if not snapshot_label else 'Snapshot label supplied by user.'],
        checks={'row_counts_reconciled': True, 'source_hashes_unchanged': True, 'saved_original_fields_verified': True})
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Completed {manifest["scope"]}. Outputs: {out}')
    print(tables['cleaning_report'].to_string(index=False))
    return tables, manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notes', default=str(DEFAULT_RAW / 'notes-00001.tsv'))
    parser.add_argument('--requests', default=str(DEFAULT_RAW / 'batSignals-00000.tsv'))
    parser.add_argument('--output-dir')
    parser.add_argument('--cutoff', help='Verified observation cutoff, including timezone')
    parser.add_argument('--snapshot-label')
    parser.add_argument('--preview-rows', type=int)
    args = parser.parse_args()
    run(args.notes, args.requests, args.output_dir, args.cutoff, args.snapshot_label, args.preview_rows)

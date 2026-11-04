"""Audit every supplied cleaned row and build compact local dashboard inputs.

Checks cleaned-output structure, QC counts, keys and joins, not original-source preservation.
Run once: .venv/bin/python prepare_dashboard.py
"""
from pathlib import Path
import hashlib
import json
from collections import Counter
import argparse

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/dashboard'
LEVELS = ['HELPFUL', 'SOMEWHAT_HELPFUL', 'NOT_HELPFUL']
FEEDS = ['noteRequestFeedEligibleAtMillis', 'apiSmallFeedEligibleAtMillis', 'apiLargeFeedEligibleAtMillis', 'apiXlFeedEligibleAtMillis']


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def prepare():
    import pandas as pd
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'scope': 'Full cleaned-output scan; original source files not revalidated. Selected shards only.',
              'cutoff_utc': '2026-10-02T23:59:59.999Z', 'cutoff_verified': False,
              'cutoff_evidence': 'See dashboard_policy.json for the current shared provisional cutoff decision.',
              'datasets': {}}
    report.update(json.loads((ROOT / 'dashboard_policy.json').read_text()))
    paths = {'notes': ROOT / 'phase2-peyton/outputs/notes_clean.csv',
             'requests': ROOT / 'phase2-peyton/outputs/note_requests_clean.csv'}
    notes = pd.read_csv(paths['notes'], dtype='string', keep_default_na=False,
                        usecols=['noteId','tweetId','createdAtMillis','classification','isMediaNote','isCollaborativeNote'])
    requests = pd.read_csv(paths['requests'], dtype='string', keep_default_na=False, usecols=['tweetId'] + FEEDS)
    for name, df, key in [('notes', notes, 'noteId'), ('requests', requests, 'tweetId')]:
        invalid = ~df[key].str.fullmatch(r'[1-9][0-9]*', na=False)
        repeated = df[key].duplicated(keep=False)
        report['datasets'][name] = {'rows': len(df), 'invalid_keys': int(invalid.sum()),
                                    'repeated_keys': int(repeated.sum()), 'sha256': digest(paths[name])}
        if invalid.any() or repeated.any():
            raise ValueError(f'{name}: invalid or repeated keys require reconciliation')
    ids = set(notes.noteId)
    matched = {}
    for kind in ['status', 'ratings']:
        path = ROOT / f'yoojin_phase 2/{kind}_clean.tsv.gz'
        previous = json.loads((ROOT / 'yoojin_phase 2/evidence' /
                               ('ratings_validation.json' if kind == 'ratings' else 'status_cleaning_report.json')).read_text())
        cols = pd.read_csv(path, sep='\t', nrows=0).columns.tolist()
        required = ['noteId','createdAtMillis','meta_source_file']
        required += (['raterParticipantId','helpfulnessLevel'] if kind == 'ratings' else
                     ['timestampMillisOfFirstNonNMRStatus','firstNonNMRStatus','currentStatus'])
        qc = [c for c in cols if c.startswith('qc_')]
        counts = Counter(); rows = 0; parts = []; sources = Counter(); seen_status = set(); duplicate_status = 0
        invalid_keys = 0; bad_times = 0; min_time = None; max_time = None
        for chunk in pd.read_csv(path, sep='\t', dtype='string', keep_default_na=False,
                                 usecols=list(dict.fromkeys(required + qc)), chunksize=100000):
            rows += len(chunk)
            for col in qc:
                if not chunk[col].isin(['True','False']).all():
                    raise ValueError(f'{kind}: malformed {col}')
                counts[col] += int(chunk[col].eq('True').sum())
            bad = ~chunk.noteId.str.fullmatch(r'[1-9][0-9]*', na=False)
            if kind == 'ratings':
                bad |= chunk.raterParticipantId.str.strip().eq('')
                expected = chunk.helpfulnessLevel.str.strip().str.upper().isin(LEVELS)
                if not expected.eq(chunk.qc_valid_helpfulness.eq('True')).all():
                    raise ValueError('Rating helpfulness flags disagree with values')
            else:
                duplicate_status += int(chunk.noteId.duplicated().sum())
                unique = set(chunk.noteId)
                duplicate_status += len(unique & seen_status)
                seen_status.update(unique)
            if not (~bad).eq(chunk.qc_key_valid.eq('True')).all():
                raise ValueError(f'{kind}: key flags disagree with values')
            invalid_keys += int(bad.sum())
            times = pd.to_numeric(chunk.createdAtMillis, errors='coerce')
            bad_times += int((times.isna() | times.le(0)).sum())
            valid = times[times.gt(0)]
            if len(valid):
                min_time = int(valid.min()) if min_time is None else min(min_time, int(valid.min()))
                max_time = int(valid.max()) if max_time is None else max(max_time, int(valid.max()))
            sources.update(chunk.meta_source_file.value_counts().to_dict())
            part = chunk.loc[chunk.noteId.isin(ids)]
            if len(part): parts.append(part)
            if rows % 1000000 == 0: print(f'{kind}: {rows:,} rows checked', flush=True)
        if rows != previous['counts']['output']:
            raise ValueError(f'{kind}: supplied row count differs from saved report')
        mismatches = {k: {'actual':v, 'reported':previous['counts'].get(k)} for k,v in counts.items()
                      if v != previous['counts'].get(k,0)}
        if mismatches or duplicate_status: raise ValueError(f'{kind}: QC or uniqueness mismatch: {mismatches}, {duplicate_status}')
        matched[kind] = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=required+qc)
        report['datasets'][kind] = dict(rows=rows, invalid_keys=invalid_keys, invalid_creation_times=bad_times,
            qc_counts=dict(counts), qc_counts_match_saved_report=True, source_files=dict(sources),
            matched_rows=len(matched[kind]), unmatched_rows=rows-len(matched[kind]),
            min_created_ms=min_time,max_created_ms=max_time,sha256=digest(path))
        if kind == 'status': report['datasets'][kind]['duplicate_note_ids'] = duplicate_status
    ratings = matched['ratings']
    duplicates = ratings.duplicated(['noteId','raterParticipantId'], keep=False)
    report['matched_rating_repeated_pair_rows'] = int(duplicates.sum())
    # Quarantine all ambiguous matched pairs; no arbitrary first-row selection.
    ratings = ratings.loc[~duplicates].copy()
    status = matched['status']
    notes = notes.merge(status, on='noteId', how='left', suffixes=('', '_status'), validate='one_to_one', indicator=True)
    report['notes_without_status'] = int(notes['_merge'].eq('left_only').sum())
    report['notes_with_status'] = int(notes['_merge'].eq('both').sum())
    report['notes_with_observed_ratings'] = int(notes.noteId.isin(ratings.noteId).sum())
    report['requests_with_matching_post'] = int(requests.tweetId.isin(notes.tweetId).sum())
    report['notes_without_matching_request'] = int((~notes.tweetId.isin(requests.tweetId)).sum())
    report['rating_pair_validation_scope'] = 'Actual pair uniqueness checked for matched cohort; full-file repeated-key flags reconciled to prior report.'
    report['status'] = 'PASS cleaned-output and integration checks; snapshot remains unverified'
    notes.drop(columns='_merge').to_parquet(OUT/'notes.parquet', index=False)
    ratings.to_parquet(OUT/'ratings.parquet', index=False)
    requests.to_parquet(OUT/'requests.parquet', index=False)
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'yoojin_phase 2/evidence/dashboard_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='datasets'},indent=2),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--raw-url', help='Direct shared ZIP download URL')
    source.add_argument('--raw-zip', type=Path, help='Existing local raw ZIP')
    source.add_argument('--raw-dir', type=Path, help='Index all ZIPs in an existing raw-data folder without copying them')
    parser.add_argument('--sha256', help='Expected SHA-256 of the raw ZIP')
    args = parser.parse_args()
    if args.sha256 and not (args.raw_url or args.raw_zip):
        parser.error('--sha256 requires --raw-url or --raw-zip')
    if args.raw_dir:
        from raw_dataset import index_raw_directory
        index_raw_directory(args.raw_dir)
    elif args.raw_url or args.raw_zip:
        from raw_dataset import import_raw_zip
        import_raw_zip(url=args.raw_url, local_zip=args.raw_zip, expected_sha256=args.sha256)
    else:
        prepare()


if __name__ == '__main__':
    main()

"""Auditable cleaning of one complete Community Notes status-history snapshot."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd

STATUSES = {'NEEDS_MORE_RATINGS', 'CURRENTLY_RATED_HELPFUL', 'CURRENTLY_RATED_NOT_HELPFUL'}
REQUIRED = ['noteId', 'createdAtMillis', 'currentStatus']


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load_source(path):
    # Read every row, preserving large identifiers and leading zeros exactly.
    return pd.read_csv(path, sep='\t', dtype='string', keep_default_na=False)


def clean(raw, snapshot_date):
    missing = set(REQUIRED) - set(raw.columns)
    if missing:
        raise ValueError(f'Missing required columns: {sorted(missing)}')
    cutoff = pd.Timestamp(snapshot_date)
    cutoff = cutoff.tz_localize('UTC') if cutoff.tzinfo is None else cutoff.tz_convert('UTC')
    source_columns = list(raw.columns)
    df = raw.copy()
    df.insert(0, 'source_row', range(1, len(df) + 1))
    # Detect exact duplicates BEFORE standardization; do not silently resolve conflicts.
    exact = raw.duplicated(keep='first')
    df['exact_duplicate'] = exact
    changes = []
    missing_counts = []
    for col in source_columns:
        before = df[col].copy()
        after = before.str.strip().replace('', pd.NA)
        if col in ['currentStatus', 'firstNonNMRStatus', 'mostRecentNonNMRStatus']:
            after = after.str.upper()
        df[col] = after
        changed = before.fillna('<NULL>').ne(after.fillna('<NULL>'))
        changes.append({'column': col, 'changed_values': int(changed.sum())})
        missing_counts.append({'column': col, 'blank_before': int(before.str.strip().eq('').sum()),
                               'missing_after': int(after.isna().sum())})
    df['invalid_note_id'] = ~df['noteId'].str.fullmatch(r'\d+', na=False)
    nonexact = df.loc[~exact]
    repeated = nonexact.loc[nonexact['noteId'].notna() & nonexact['noteId'].duplicated(False), 'noteId']
    df['conflicting_note_id'] = df['noteId'].isin(repeated)
    df['unknown_status'] = ~df['currentStatus'].isin(STATUSES)
    conversions = []
    for col in [c for c in source_columns if c.endswith('Millis')]:
        value = df[col]
        integer = value.str.fullmatch(r'-?\d+', na=False)
        number = pd.to_numeric(value.where(integer), errors='coerce')
        # Negative values are treated as unset, not as pre-1970 events; retain raw values.
        parsed = pd.to_datetime(number.where(number.ge(0)), unit='ms', utc=True, errors='coerce')
        invalid = value.notna() & (~integer | (number.ge(0) & parsed.isna()))
        df[col + '_utc'] = parsed
        df[col + '_invalid'] = invalid
        df[col + '_future'] = parsed.gt(cutoff)
        conversions.append({'column': col, 'invalid_count': int(invalid.sum()),
                            'negative_unset_count': int(number.lt(0).sum()),
                            'future_count': int(parsed.gt(cutoff).sum())})
    for col in [c for c in source_columns if c.endswith('Millis') and c != 'createdAtMillis']:
        df[col + '_before_creation'] = df[col + '_utc'].lt(df['createdAtMillis_utc'])
    df['invalid_creation'] = df['createdAtMillis_utc'].isna() | df['createdAtMillis_future']
    df['eligible'] = ~(df['exact_duplicate'] | df['invalid_note_id'] |
                       df['conflicting_note_id'] | df['unknown_status'] | df['invalid_creation'])
    df['note_age_hours'] = (cutoff - df['createdAtMillis_utc']).dt.total_seconds() / 3600
    # Note age is observation age, not a completed response time.
    metric = df.loc[df['eligible']].copy()
    n = len(metric)
    counts = metric['currentStatus'].value_counts().reindex(sorted(STATUSES), fill_value=0)
    metrics = pd.DataFrame({'currentStatus': counts.index, 'note_count': counts.values})
    metrics['denominator'] = n
    metrics['share'] = metrics['note_count'] / n if n else float('nan')
    # Mutually exclusive reasons reconcile counts even when flags overlap.
    remaining = pd.Series(True, index=df.index)
    waterfall = []
    for flag in ['exact_duplicate', 'invalid_note_id', 'conflicting_note_id', 'unknown_status', 'invalid_creation']:
        removed = remaining & df[flag]
        waterfall.append({'reason': flag, 'excluded_rows': int(removed.sum())})
        remaining &= ~df[flag]
    assert int(remaining.sum()) == n
    assert len(raw) == n + sum(x['excluded_rows'] for x in waterfall)
    assert metric['noteId'].is_unique
    assert int(metrics['note_count'].sum()) == n
    audit = {'starting_rows': len(raw), 'eligible_rows': n,
             'exact_duplicate_rows': int(exact.sum()),
             'repeated_id_rows_after_exact_removal': len(repeated),
             'repeated_ids_after_exact_removal': int(repeated.nunique()),
             'snapshot_cutoff_utc': cutoff.isoformat(), 'exclusions': waterfall,
             'conversions': conversions, 'text_changes': changes,
             'missing_counts': missing_counts,
             'missing_in_eligible': {c: int(metric[c].isna().sum()) for c in source_columns},
             'merges': 'Not applicable: one status-history table; no joins.'}
    return df, metrics, audit


def run(source, output, snapshot_date, synthetic=False):
    source, output = Path(source), Path(output)
    digest = sha256(source)
    raw = load_source(source)
    cleaned, metrics, audit = clean(raw, snapshot_date)
    audit.update({'source': str(source), 'source_sha256': digest,
                  'data_kind': 'SYNTHETIC demonstration' if synthetic else 'REAL full input file',
                  'pandas_version': pd.__version__})
    output.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output / 'cleaned_status.csv', index=False)
    metrics.to_csv(output / 'status_metrics.csv', index=False)
    # Deterministic sample: flagged cases first, then ordinary cases, <=50 total.
    sample = cleaned.sort_values(['eligible', 'source_row'], kind='stable').head(50)
    sample.to_csv(output / 'cleaned_sample.csv', index=False)
    (output / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    assert sha256(source) == digest, 'Original source changed during processing'
    return raw, cleaned, metrics, audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--snapshot-date', required=True, help='Actual snapshot cutoff, ISO date/time')
    parser.add_argument('--synthetic', action='store_true')
    args = parser.parse_args()
    _, _, _, audit = run(args.source, args.output, args.snapshot_date, args.synthetic)
    print(json.dumps(audit, indent=2))

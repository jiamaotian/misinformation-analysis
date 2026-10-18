"""Euan: observed coverage backend. Real metrics require row data and verified cutoff."""
from pathlib import Path
import argparse
import json
import pandas as pd

FEEDS = {'Standard': 'noteRequestFeedEligibleAtMillis', 'Small': 'apiSmallFeedEligibleAtMillis', 'Large': 'apiLargeFeedEligibleAtMillis', 'XL': 'apiXlFeedEligibleAtMillis'}

def utc(value):
    t = pd.Timestamp(value)
    if t.tzinfo is None:
        raise ValueError('Supply a timezone, e.g. 2026-10-01T00:00:00Z')
    return t.tz_convert('UTC')

def millis(series):
    s = series.astype('string')
    n = pd.to_numeric(s.where(s.str.fullmatch(r'\d+').fillna(False)), errors='coerce')
    return pd.to_datetime(n.where(n.gt(0)), unit='ms', utc=True, errors='coerce')

def analyze_coverage(requests, notes, *, cutoff, feed='Standard', window_days=7, start=None, end=None):
    """Return request outcomes, weekly aggregates, gaps and summary.

    Proposed rules: unique tweetId per request; inclusive event boundaries;
    date filters use [start,end); UTC weeks start Monday. Median time covers
    only first qualifying notes observed within the selected window.
    Inputs are never modified. No status/rating data is used.
    """
    if cutoff is None:
        raise ValueError('Verified observation cutoff is required for real metrics.')
    cutoff = utc(cutoff)
    if feed not in FEEDS or window_days not in (7, 14, 28):
        raise ValueError('Invalid feed or window; use Standard/Small/Large/XL and 7/14/28.')
    r, n = requests.copy(), notes.copy()
    field = FEEDS[feed]
    for frame, columns in [(r, ['tweetId', field]), (n, ['tweetId', 'noteId', 'createdAtMillis'])]:
        missing = set(columns) - set(frame.columns)
        if missing:
            raise ValueError(f'Missing columns: {sorted(missing)}')
        for col in ['tweetId'] + (['noteId'] if 'noteId' in columns else []):
            frame[col] = frame[col].astype('string')
            if not frame[col].str.fullmatch(r'0*[1-9]\d*').fillna(False).all():
                raise ValueError(f'Invalid {col}; reconcile with data cleaner.')
    if r.tweetId.duplicated().any() or n.noteId.duplicated().any():
        raise ValueError('Repeated request tweetId or noteId: reconcile before analysis.')
    r['eligibility_utc'] = millis(r[field])
    n['note_utc'] = millis(n.createdAtMillis)
    r['window_end_utc'] = r.eligibility_utc + pd.Timedelta(days=window_days)
    invalid = r.eligibility_utc.isna()
    selected = ~invalid
    if start is not None:
        selected &= r.eligibility_utc.ge(utc(start))
    if end is not None:
        selected &= r.eligibility_utc.lt(utc(end))
    if start is not None and end is not None and utc(start) >= utc(end):
        raise ValueError('start must be earlier than end.')
    mature = selected & r.window_end_utc.le(cutoff)
    cohort = r.loc[mature, ['tweetId', 'eligibility_utc', 'window_end_utc']].copy()
    valid_notes = n.loc[n.note_utc.notna() & n.note_utc.le(cutoff), ['tweetId', 'noteId', 'note_utc']]
    candidates = cohort.merge(valid_notes, on='tweetId', how='inner', validate='one_to_many')
    qualifying = candidates.loc[candidates.note_utc.ge(candidates.eligibility_utc) & candidates.note_utc.le(candidates.window_end_utc)]
    first = qualifying.groupby('tweetId').note_utc.min().rename('first_note_utc')
    result = cohort.join(first, on='tweetId')
    result['covered'] = result.first_note_utc.notna()
    result['time_to_first_note_hours'] = (result.first_note_utc - result.eligibility_utc).dt.total_seconds() / 3600
    result['eligibility_week_utc'] = result.eligibility_utc.dt.normalize() - pd.to_timedelta(result.eligibility_utc.dt.dayofweek, unit='D')
    weekly = result.groupby('eligibility_week_utc').agg(eligible_requests=('tweetId', 'size'), covered_requests=('covered', 'sum')).reset_index()
    weekly['no_observed_note'] = weekly.eligible_requests - weekly.covered_requests
    weekly['coverage_rate'] = weekly.covered_requests / weekly.eligible_requests
    eligible, covered = len(result), int(result.covered.sum())
    median = result.time_to_first_note_hours.median() if covered else float("nan")
    summary = dict(feed=feed, window_days=window_days, cutoff_utc=cutoff.isoformat(), start=start, end=end,
        eligible_requests=eligible, covered_requests=covered, no_observed_note=eligible-covered,
        coverage_rate=covered/eligible if eligible else None,
        no_observed_note_rate=(eligible-covered)/eligible if eligible else None,
        median_time_to_first_note_hours=None if pd.isna(median) else float(median), completed_request_count=covered,
        invalid_or_nonpositive_eligibility_all_requests=int(invalid.sum()),
        immature_requests_in_selected_dates=int((selected & ~mature).sum()),
        invalid_note_times_all_notes=int(n.note_utc.isna().sum()),
        notes_after_cutoff_all_notes=int(n.note_utc.gt(cutoff).sum()),
        limitation='Observed in supplied files only; unmatched requests do not establish platform-wide absence.')
    return {'summary': summary, 'requests': result, 'weekly': weekly, 'gaps': result.loc[~result.covered].copy()}

def save_results(results, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name in ['requests', 'weekly', 'gaps']:
        results[name].to_csv(folder / f'coverage_{name}.csv', index=False)
    (folder / 'coverage_summary.json').write_text(json.dumps(results['summary'], indent=2), encoding='utf-8')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--requests', required=True)
    p.add_argument('--notes', required=True)
    p.add_argument('--cutoff', required=True, help='Verified cutoff with timezone; never guess')
    p.add_argument('--feed', choices=list(FEEDS), default='Standard')
    p.add_argument('--window-days', type=int, choices=[7,14,28], default=7)
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--output', default='outputs/real')
    args = p.parse_args()
    data = analyze_coverage(pd.read_csv(args.requests, dtype='string', keep_default_na=False), pd.read_csv(args.notes, dtype='string', keep_default_na=False), cutoff=args.cutoff, feed=args.feed, window_days=args.window_days, start=args.start, end=args.end)
    save_results(data, args.output)
    print(json.dumps(data['summary'], indent=2))

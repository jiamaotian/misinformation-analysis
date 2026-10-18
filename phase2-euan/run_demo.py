"""Synthetic acceptance checks only. Outputs are NOT real project findings."""
import pandas as pd
from coverage_analysis import analyze_coverage, save_results

base = pd.Timestamp('2026-01-01T00:00:00Z')
def ms(hours):
    return str(int((base + pd.Timedelta(hours=hours)).timestamp()*1000))
r = pd.DataFrame({'tweetId': [str(i) for i in range(1,12)], 'noteRequestFeedEligibleAtMillis': [ms(0)]*10+[ms(240)]})
n = pd.DataFrame({'tweetId':['1','1','1','2','3','4','5','6'], 'noteId':[str(i) for i in range(1,9)], 'createdAtMillis':[ms(0),ms(4),ms(8),ms(24),ms(48),ms(168),ms(-1),ms(169)]})
out = analyze_coverage(r,n,cutoff='2026-01-12T00:00:00Z')
s = out['summary']
assert (s['eligible_requests'], s['covered_requests'], s['no_observed_note']) == (10,4,6)
assert s['coverage_rate'] == .4
assert s['immature_requests_in_selected_dates'] == 1
assert out['requests'].set_index('tweetId').loc['4','time_to_first_note_hours'] == 168
assert s['median_time_to_first_note_hours'] == 36
empty = analyze_coverage(r,n,cutoff='2026-01-02T00:00:00Z')
assert empty['summary']['coverage_rate'] is None
assert empty['summary']['median_time_to_first_note_hours'] is None
no_notes = analyze_coverage(r,n.iloc[:0],cutoff='2026-01-12T00:00:00Z')
assert no_notes['summary']['covered_requests'] == 0
assert no_notes['summary']['median_time_to_first_note_hours'] is None
try:
    analyze_coverage(r,n,cutoff=None)
except ValueError:
    pass
else:
    raise AssertionError('Unknown cutoff must be rejected')
out['summary']['data_mode'] = 'SYNTHETIC DEMO ONLY - NOT REAL FINDINGS'
save_results(out, 'outputs/SYNTHETIC_DEMO_ONLY')
print('PASS: 10 mature requests, 4 covered, 40%, 6 gaps. SYNTHETIC ONLY.')
print('PASS: inclusive boundaries, multiple notes counted once, immature exclusion, empty cohort, no notes, unknown cutoff.')

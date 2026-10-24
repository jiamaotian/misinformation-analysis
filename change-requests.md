# Audit claims and change requests

## Claims

- **Peyton Tom:** backend Coverage observation-window selection (`window_days=7/14/28`) and observed coverage rate. Version audited: `67b7bc82f5147d7669718b85a42580691eb41884`.
- Additional evidence: a multi-window synthetic fixture with changing maturity denominators, checked against a separate integer-arithmetic implementation. This extends the existing coverage demo; it does not claim teammates' earlier checks as Peyton's work.
- Scope: existing backend analysis, not a dashboard. AI assisted with check code, execution and drafting; Peyton reviewed the results and supplied personal explanations in the individual submission.

## PT-01 — Dashboard test outside current audit scope

- Status: superseded as a prerequisite for Peyton's audit; no UI failure claimed.
- The original request to obtain a dashboard does not apply to this backend audit. The team has not built a running dashboard. Future interface interactions remain untested.
- No dashboard implementation or backend fix is requested on the basis of the passing checks below.

## PT-02 — Verify cutoff and source scope before real windowed reporting

- Status: open, known provenance limitation; not a newly discovered calculation bug.
- Evidence: `phase2-euan/COVERAGE_HANDOFF.md` calls its cutoff provisional and documents partial-Notes-shard scope. The backend rejects a missing cutoff but cannot verify the provenance of a supplied timestamp.
- Request to the team: document the verified UTC cutoff, exact source hashes and shard scope; rerun the real-data analysis if these change. Until verified, retain provisional/partial-shard labels and do not present the results as validated full-snapshot coverage.
- Acceptance: a reproducible source manifest supports the cutoff and scope, and results identify that provenance. Any future dashboard must also follow the specifications' unverified-cutoff warning/suppression requirement; that interaction is outside this audit.

## Findings and evidence

The window-selection feature and coverage calculation passed the synthetic cases tested. Coverage means covered eligible requests divided by eligible requests, not notes divided by requests. Multiple qualifying notes count a request only once.

Fixture: requests 1–10 become eligible January 1, 2026; request 11 becomes eligible January 20. Cutoff is February 1, 2026 at 00:00 UTC. Request 1 has notes at days 0 and 1; requests 2, 3, 5 and 6 have notes at days 7, 8, 14 and 28. Request 4 has only a note before eligibility; requests 7–10 have none. Request 11 has a note at eligibility.

| Window | Expected eligible | Expected covered IDs | Expected rate | Actual |
|---|---:|---|---:|---|
| 7 days | 11 | 1, 2, 11 | 27.3% | Matches |
| 14 days | 10 | 1, 2, 3, 5 | 40.0% | Matches |
| 28 days | 10 | 1, 2, 3, 5, 6 | 50.0% | Matches |

Request 11 has only 12 days of observation, so it leaves the denominator for 14/28 days. Inclusive boundaries, pre-eligibility exclusion, multiple notes, half-open dates, empty denominator and missing cutoff handling were checked. Weekly totals reconcile. The committed latest28 aggregates also reconcile to 305 covered / 11,318 eligible = 2.6948224068%; this is output-internal consistency, not independent verification of raw inputs.

Remaining uncertainty: real-data completeness, cleaning/matching correctness and cutoff provenance are not established. Only Standard feed and selected synthetic inputs were tested. Small/Large/XL feeds and UI interactions remain untested. The separate reference implementation was also AI-written; it is not independent human verification.

## Reproduce the check

The complete script is embedded here so teammates do not need Peyton's uncommitted local audit files. In a Git clone of this repository at the audited commit above, create `audit-peyton/` and save the code below as `audit-peyton/check_coverage.py`. With Python and pandas installed (recorded run: pandas 3.0.6), run from the repository root:

```bash
python audit-peyton/check_coverage.py
```

Use normal Python execution, not `python -O`, which disables assertions. The check imports the committed `phase2-euan/coverage_analysis.py` and reads the committed `phase2-euan/results/latest28/coverage_summary.json` and `coverage_weekly.csv`. Git must be available to record the checkout version. No raw datasets are needed. It prints results and writes `audit-peyton/coverage_evidence.json`; failed checks raise an error. Running at a different commit records that version and may produce different results.

```python
"""AI-assisted synthetic audit; no raw-data or UI verification claimed."""
import importlib.util
import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('coverage_backend', ROOT / 'phase2-euan/coverage_analysis.py')
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)
DAY = 86_400_000
BASE = 1_767_225_600_000  # 2026-01-01 00:00 UTC
def stamp(day):
    return str(BASE + int(day * DAY))

# Requests 1–10 begin Jan 1; request 11 begins Jan 20.
# 1 has multiple notes; 2 is exactly at 7 days; 3 just after;
# 4 has only a pre-eligibility note; 5 is exactly at 14 days;
# 6 is exactly at 28 days; 7–10 have no notes; 11 has a same-day note.
requests = pd.DataFrame({
    'tweetId': [str(i) for i in range(1, 12)],
    'noteRequestFeedEligibleAtMillis': [stamp(0)] * 10 + [stamp(19)],
})
notes = pd.DataFrame({
    'tweetId': ['1', '1', '2', '3', '4', '5', '6', '11'],
    'noteId': [str(i) for i in range(1, 9)],
    'createdAtMillis': [stamp(d) for d in [0, 1, 7, 8, -1, 14, 28, 19]],
})
cutoff_ms = int(stamp(31))

def independent(window, start=None, end=None):
    """Integer arithmetic and Python loops, independent of backend joins."""
    eligible, covered = [], []
    for row in requests.to_dict('records'):
        origin = int(row['noteRequestFeedEligibleAtMillis'])
        if start is not None and origin < start:
            continue
        if end is not None and origin >= end:
            continue
        if origin + window * DAY > cutoff_ms:
            continue
        eligible.append(row['tweetId'])
        if any(n['tweetId'] == row['tweetId'] and
               origin <= int(n['createdAtMillis']) <= origin + window * DAY
               for n in notes.to_dict('records')):
            covered.append(row['tweetId'])
    return eligible, covered

evidence = {'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'pandas': pd.__version__, 'scope': 'Synthetic backend checks; UI untested', 'checks': []}
# Expected counts written from the fixture before executing the backend.
for window, expected in [(7, (11, 3)), (14, (10, 4)), (28, (10, 5))]:
    result = backend.analyze_coverage(requests, notes, cutoff='2026-02-01T00:00:00Z', window_days=window)
    summary = result['summary']
    eligible, covered = independent(window)
    assert (len(eligible), len(covered)) == expected
    assert (summary['eligible_requests'], summary['covered_requests']) == expected
    assert summary['coverage_rate'] == len(covered) / len(eligible)
    assert set(result['requests'].tweetId) == set(eligible)
    assert set(result['requests'].loc[result['requests'].covered, 'tweetId']) == set(covered)
    assert summary['no_observed_note'] == len(eligible) - len(covered)
    assert int(result['weekly'].eligible_requests.sum()) == len(eligible)
    assert int(result['weekly'].covered_requests.sum()) == len(covered)
    evidence['checks'].append({'window_days': window, 'eligible': len(eligible),
                               'covered': len(covered), 'rate': summary['coverage_rate'], 'passed': True})

# Half-open dates include Jan 1, exclude Jan 20.
filtered = backend.analyze_coverage(requests, notes, cutoff='2026-02-01T00:00:00Z',
    start='2026-01-01T00:00:00Z', end='2026-01-20T00:00:00Z')['summary']
assert (filtered['eligible_requests'], filtered['covered_requests']) == (10, 2)
empty = backend.analyze_coverage(requests, notes, cutoff='2026-01-02T00:00:00Z')['summary']
assert empty['coverage_rate'] is None and empty['median_time_to_first_note_hours'] is None
try:
    backend.analyze_coverage(requests, notes, cutoff=None)
except ValueError:
    pass
else:
    raise AssertionError('Missing cutoff must be rejected')
evidence['additional_checks'] = ['half-open date range passed', 'empty denominator returns None', 'missing cutoff rejected']

# Existing aggregates: consistency only, not independent verification of raw inputs.
folder = ROOT / 'phase2-euan/results/latest28'
saved = json.loads((folder / 'coverage_summary.json').read_text())
weekly = pd.read_csv(folder / 'coverage_weekly.csv')
assert int(weekly.eligible_requests.sum()) == saved['eligible_requests'] == 11318
assert int(weekly.covered_requests.sum()) == saved['covered_requests'] == 305
assert abs(saved['coverage_rate'] - 305 / 11318) < 1e-12
evidence['saved_aggregate_check'] = {'eligible': 11318, 'covered': 305,
    'percentage': 100 * 305 / 11318, 'scope': 'Output-internal reconciliation only'}
path = Path(__file__).with_name('coverage_evidence.json')
path.write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(evidence, indent=2))
```

# Euan — Coverage backend handoff

Status: reusable backend implemented; synthetic acceptance tests passed; supplied real-data shard analyzed. This is a partial-Notes integration result, not a platform-wide estimate or a claim that the entire team project is finished.

## Inputs and provenance

Inputs: notes-00001.tsv (15,718 rows) and batSignals-00000.tsv (502,151 rows), newly supplied by Euan and cleaned using Peyton's clean_notes_requests.py. Exact duplicate rows removed: 0; conflicting keys: 0. File hashes differ from Peyton's earlier manifest; these results do not reproduce that older snapshot. notes-00004 is not used in these runs. Raw and cleaned input datasets are distributed separately; this small package contains code and outputs.

The download page displayed “Data includes contributions up until 9:02 PM · Oct 15, 2026.” The user confirmed Los Angeles local display time; the analysis provisionally interprets it as 2026-10-16T04:02:00Z. The page's actual timezone localization and alignment of both downloaded files to that cutoff have not been independently verified. Team confirmation remains required before final dashboard use. The code requires an explicitly supplied cutoff and does not infer it from data maxima.

## Definitions

Unit: one request tweetId in the cleaned request file (unique in this input). Standard uses noteRequestFeedEligibleAtMillis; Small, Large and XL use their corresponding api feed eligibility fields. Confirm feed semantics with the team. IDs remain strings.

Eligibility time is a feed eligibility event, not a proven user-submission timestamp. A positive parseable eligibility time is required. Negative sentinel values are excluded and counted, without assigning undocumented meaning to -1.

For a W-day observation window, retain only requests with eligibility + W days <= cutoff. Filter request eligibility with start <= eligibility < end, in UTC. A covered request has at least one matching-tweet note with eligibility <= note creation <= eligibility + W days. Count each request once regardless of number of notes. Earlier notes do not qualify. Use the first qualifying note for time-to-first-note hours.

Coverage rate = covered requests / eligible requests. No-observed-note count = eligible - covered. These are descriptive labels for the supplied Notes shard, not proof of an unmet need. Missing note times are excluded and reported; duplicate IDs cause a validation error rather than silent deduplication.

Median waiting time is conditional on coverage within the window; no-note requests keep missing waiting times, not zero. Zero denominators and absent completed events produce null (display as N/A). Rates are fractions; round only for display. Weekly grouping uses Monday 00:00 UTC. Overall rates use total counts, never unweighted averages of weekly rates.

## Results: partial Notes shard

| Scope | Eligible requests | Covered | No observed qualifying note | Coverage | Median hours among covered |
|---|---:|---:|---:|---:|---:|
| All mature historical requests | 25,408 | 542 | 24,866 | 2.13% | 0.580339 (34.8 min) |
| Latest 28 complete UTC dates: Sep 11–Oct 8, 2026 | 11,318 | 305 | 11,013 | 2.69% | 0.420191 (25.2 min) |

Both runs use Standard, W=7 days and the provisionally interpreted cutoff above. All-history exclusions: 3,990 immature requests; 472,753 invalid/nonpositive Standard eligibility timestamps. The latter count describes the entire input, not missing records assignable to the selected 28-day period. Latest28 immature count: 0. Invalid note times and notes after the adopted cutoff: 0.

The latest28 date interval is [2026-09-11T00:00:00Z, 2026-10-09T00:00:00Z). Sep 7 and Oct 5 week bins, if present, contain only the selected dates within those weeks. The CLI defaults to all mature history when dates are omitted; the UI must supply the latest28 range explicitly.

## Interface and outputs

analyze_coverage(requests, notes, *, cutoff, feed='Standard', window_days=7, start=None, end=None) returns:
- summary: counts, rates, median and exclusions.
- requests: one row per mature selected request with coverage flag, first qualifying note time and hours.
- weekly: eligible, covered, no-observed-note and coverage_rate by eligibility_week_utc.
- gaps: request rows without an observed qualifying note.

save_results(results, folder) writes these tables and JSON. Latest28 includes all four output files. All-history includes the two user-uploaded aggregate files only. Request-level outputs are backend intermediates; dashboard exports should expose aggregates with filter settings, units and snapshot information, not full raw datasets.

Coverage filters are independent of Jessica's classification/rating/status filters. A selected week can filter the request-result table to recompute cards while preserving the overview. These UI interactions and export wrappers are not implemented here; Phase 3 owns the interface. Jessica's response endpoint is distinct from request-to-first-note time.

## Reproduce

```bash
python -m pip install -r requirements.txt
python run_demo.py
python coverage_analysis.py --requests data/note_requests_clean.csv --notes data/notes_clean.csv --cutoff "2026-10-16T04:02:00Z" --feed Standard --window-days 7 --start "2026-09-11T00:00:00Z" --end "2026-10-09T00:00:00Z" --output outputs/partial_notes_standard_7d_latest28
```

Use the above cutoff only with its stated provisional provenance, or substitute a team-verified cutoff and rerun. Synthetic outputs from run_demo.py must remain labeled and separate from real results.

## Validation and remaining work

Synthetic checks: 10 mature requests, 4 covered, 40%, 6 gaps; multiple notes counted once; inclusive boundaries; before/after-window exclusion; immature exclusion; empty cohort; zero-note input; unknown cutoff rejected. User's local pandas 2.3.3 demo passed. All-history weekly totals reconcile to 25,408/542/24,866; latest28 weekly totals reconcile to 11,318/305/11,013 and every weekly rate is verified. Latest28 was rerun successfully against the cleaned real input files.

Before final integration: agree canonical dataset version and scope with Peyton; obtain all relevant Notes shards for complete-snapshot coverage or obtain explicit team acceptance of shard-only scope; verify cutoff/timezone; confirm feed/window/boundary conventions and sentinel meaning; rerun against canonical inputs; integrate definitions into BUILD_SPEC.md; perform team fresh-agent test. No fresh-agent test or main-branch merge is claimed here.

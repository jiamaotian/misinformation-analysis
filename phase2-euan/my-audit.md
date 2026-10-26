# Module 9 — Coverage Date Filter and No-Observed-Note Audit

**Author:** Euan (Yun Wei)  
**Status:** Backend audit report; synthetic checks rerun locally by Euan with AI assistance.  
**Feature:** Coverage eligibility-date filter (`start`, `end`).  
**Number:** `no_observed_note`.  
**Version:** User-uploaded `coverage_analysis.py`, SHA-256 `58057aec9b06ac2ef5a1bb430d9251ad3c08ac2525e57bf31c19dcb15692d262`. GitHub file page supplied by Euan identifies its latest file-changing commit as `93bc9a7`. The source hash above pins the exact uploaded bytes tested; the full repository tree was not independently retrieved.

## Intended user and requirement

A Community Notes Product Manager selects an eligibility-date interval to investigate observed coverage gaps. BUILD_SPEC.md sections 2.2 and 3.1 define UTC, half-open dates (`start <= eligibility < end`), a positive feed-specific eligibility timestamp, and maturity (`eligibility + W <= cutoff`). No observed note means a selected mature request has no matching note created between eligibility and the inclusive end of its observation window. It does not establish platform-wide absence or unmet need.

This audit evaluates the existing backend callable as the implemented feature. It does not claim to audit a deployed dashboard or its date widgets. The evidence establishes backend behavior only; whether this satisfies the assignment's app-feature requirement remains unconfirmed. It is not an end-to-end app audit.

## Reproducible evidence

Files: `coverage_analysis.py`, `check_date_gaps.py`, and generated `audit_results.json`.

```bash
python -m pip install "pandas>=2.2,<3"
python check_date_gaps.py
```

Euan reran the script locally in VS Code with pandas 2.3.3 and supplied the generated JSON; all nine checks passed. An earlier assistant run with pandas 2.2.3 produced the same case results. The check imports the uploaded backend unchanged. A separate reference calculation uses Python integer milliseconds, loops and set membership rather than pandas filtering/joins. Both calculations were AI-assisted; this is not claimed as independently authored student code or a second-agent verification. The audit also inspects the exact predicates and their implications below.

## Hand-calculated fixture

Use Standard, W=7 days, start S=`2026-09-11T00:00:00Z`, end E=`2026-09-13T00:00:00Z`, and a synthetic cutoff `2026-10-16T04:02:00Z`. This supplied timestamp is test configuration, not verified real-data provenance. All valid fixture requests are mature at this cutoff.

| tweetId | Eligibility | Note evidence | Expected selected? | Expected gap? |
|---|---|---|---|---|
| 1 | S minus 1 ms | Note inside selected calendar dates | No | No |
| 2 | S | Two qualifying notes | Yes | No |
| 3 | S plus 1 ms | Note 1 ms before eligibility | Yes | Yes |
| 4 | S plus 1 day | Qualifying note | Yes | No |
| 5 | E minus 1 ms | Note 1 ms after its 7-day window | Yes | Yes |
| 6 | E | Qualifying note | No | No |
| 7 | E plus 1 day | None | No | No |
| 8 | S plus 12 hours | None | Yes | Yes |
| 9 | -1 sentinel | None | No | No |

Selected IDs are {2,3,4,5,8}; covered IDs are {2,4}; gap IDs are {3,5,8}. Therefore eligible=5, covered=2, and no observed note=3. Request 2 counts once despite two notes. Request 1 proves that a note inside the chosen calendar dates does not make an out-of-range request eligible. The metric counts requests, not notes; its unit is an integer request count, its range is 0 through the selected mature request count, and the corresponding share uses that selected mature count as denominator.

## Expected versus actual

| Check | Expected eligible / covered / gaps | Actual | Conclusion |
|---|---|---|---|
| Half-open date range | 5 / 2 / 3; selected IDs {2,3,4,5,8} | Exact match | Pass |
| Equivalent -07:00 bounds | 5 / 2 / 3, same IDs | Exact match | Pass |
| Start only | 7 / 3 / 4 | Exact match | Pass |
| End only | 6 / 3 / 3 | Exact match | Pass |
| Empty August cohort | 0 / 0 / 0 | Exact match | Pass |
| Cutoff changed to Sep 18 00:00 UTC | Only ID 2 mature: 1 / 1 / 0 | Exact match | Pass |
| Equal bounds | ValueError | ValueError | Pass |
| Reversed bounds | ValueError | ValueError | Pass |
| Timezone omitted | ValueError | ValueError | Pass |

For every successful case, the test checks selected IDs, gap IDs, summary gap count, gap-table length, and summed weekly gaps against the reference result. See JSON for actual outputs.

## Calculation and assumption inspection

In `analyze_coverage`, `field = FEEDS[feed]` followed by `r['eligibility_utc'] = millis(r[field])` establishes the date-filter origin. The predicates `r.eligibility_utc.ge(utc(start))` and `r.eligibility_utc.lt(utc(end))` implement the inclusive start and exclusive end. Replacing `.lt` with `.le` would wrongly include ID 6 and change this fixture from 5/2/3 to 6/3/3; checking only the final gap number would miss that boundary error. This is why selected membership is checked as well.

The maturity mask is applied after date selection. Thus a date-selected request can still be excluded if it has insufficient observation time. Gap rows use `~result.covered`, while the summary uses `eligible-covered`; agreement of the row IDs, table length and weekly sums establishes consistency for these fixtures. An empty cohort has gap count zero, but its rate should be unavailable, not interpreted as zero coverage. The script does not independently assert all empty-rate fields.

## Findings, requested changes, and uncertainty

No calculation defect was observed in the tested date filter or gap count. Do not invent a bug to satisfy the assignment.

Proposed request **EW-01** (confirm ID is unused): preserve this date-boundary/membership regression check with the team code. Acceptance: the committed script reproduces all nine checks, including the exact selected and gap IDs. This is a test-coverage improvement, not a claim that the current calculation is wrong.

Existing **PT-02** already records provisional cutoff and partial-shard provenance. That limitation is retained, not claimed as a new discovery. Tests do not validate the real 11,013-gap result, source completeness, source hashes/cutoff alignment, other feed mappings, web widgets, display rounding, exports, performance or end-to-end filter independence. Results support only this uploaded backend and these synthetic cases.

## Personal contribution and AI disclosure

I selected the eligibility-date filter and no-observed-note count as my audit scope, supplied the backend and handoff, identified the file-changing commit through GitHub, and reran the provided check locally in VS Code. I reviewed the core hand calculation: five selected mature requests minus two covered requests equals three gaps. My local result uses pandas 2.3.3 and matches the expected memberships and counts.

ChatGPT inspected the implementation, generated the fixture and reference-check code, executed an initial run, and helped draft this report. I did not independently author the reference code or claim a teammate's audit. The separate integer-based check is AI-assisted; the code-predicate analysis above provides the additional calculation-depth evidence.

My conclusion is limited: no defect was observed in the tested date-filter and gap-count cases. Passing these synthetic checks does not establish full app correctness or validate real-data provenance. My evidence adds exact date and gap membership, timezone equivalence, and invalid/open-ended interval checks, distinct from Peyton's observation-window/rate audit.

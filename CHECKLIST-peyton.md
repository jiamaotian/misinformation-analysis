# Peyton Tom — Module 6 checklist

Scope: all 26,896,815 rating records and 35 source fields in the local `ratings-00007.tsv`. Historical one-week outputs are not used as evidence for full-file preparation. Source: [official Community Notes download page](https://communitynotes.x.com/guide/en/under-the-hood/download-data).

## 1. Project vision — Done
Help a Community Notes product manager understand response time and prioritize rating effort. Business question: how quickly do notes reach Helpful, and how many are still waiting at the same cutoff? Planned measures: median completed time, unresolved count/share, and median unresolved wait. The metrics are defined, not yet calculated. Evidence: `objectives.md`, Vision B; `peyton-tom.ipynb`, dashboard plan.

## 2. Define one row — Done
One row is one submitted rating. (`noteId`, `raterParticipantId`) uniquely identifies rows in this downloaded file according to the full-file audit; this is an observed property, not a guarantee for future data. Individual note IDs and participant IDs repeat legitimately. Evidence: `evidence/peyton/duplicate_audit.json`.

## 3. Preserve the source — Unresolved
Read the original `~/Downloads/ratings-00007.tsv` without writing to it. Load with pandas, tab delimiter, string types, automatic NA inference disabled, and 100,000-row chunks. SHA-256: `3f7e3a42a5bcc2282bd8c079865f98610fec14b553cc92db134a4b85d3c0ab10`. The user confirmed the official download-page URL, but the actual download date/snapshot version and cutoff remain unknown. This limits freshness and observation-window claims. Evidence: `outputs/peyton-inspection/inspection_manifest.json`; `clean_peyton.py`.

## 4. Inspect columns and types — Done
Inspect all 35 fields as strings, preserve the original milliseconds, and derive `rating_date_utc` with UTC millisecond conversion plus `invalid_rating_date`. Inspection found zero invalid conversions and zero nonpositive timestamps. Failed values would remain in the source field, with missing derived dates and flags; no rows are dropped. Evidence: `flag_counts.csv` and `column_rules_and_evidence.csv` in `outputs/peyton-inspection/`.

## 5. Standardize text — Done
Preserve exact labels, suggestion text, whitespace, and IDs, including leading zeros. No unsupported trimming or regrouping is performed. The before/after report includes ordinary, whitespace-only, sentinel, nonempty-text, and leading-zero cases. Evidence: `evidence/peyton/text_before_after.md` and `record_checks.json`. All five selected records preserved every original field, including whitespace and leading zeros.

## 6. Investigate duplicates — Done
Full-file comparisons found zero exact duplicate rows and zero repeated note/rater pairs. Separately, 467,097 note IDs repeat, involving 26,851,827 rows; 685,151 participant IDs repeat, involving 26,749,034 rows. Those are multiple ratings, not duplicate records. All rows are retained. The report distinguishes repeated groups, all participating rows, and excess occurrences. Evidence: `evidence/peyton/duplicate_audit.json`; `verify_peyton.py`, `duplicates()`.

## 7. Handle missing data — Done
Before preparation, `suggestion` contains 26,880,490 empty strings and 9 whitespace-only strings: 26,880,499 blank values (99.9393%). The other 34 fields have zero empty/whitespace-only values. Preserve these optional blanks; do not discard ratings or fill contributor text. Sentinel IDs are handled separately from blankness. Because every original field is preserved and checked before writing, the blank counts are unchanged after preparation. Evidence: `evidence/peyton/column_rules_and_evidence.csv`; `clean_peyton.py`, Section 3.

## 8. Check suspicious values — Unresolved
No invalid/nonpositive dates, unexpected binary values, or unexpected helpfulness labels were found. Format/sentinel checks flagged 25,516 `ratedOnTweetId` values and 26,891,658 `suggestionId` values. Preserve them; the official schema does not establish the sentinel meanings. Do not treat flagged values as valid join keys. Without a verified cutoff, future-date checking remains incomplete. These limits affect date validation and possible future joins, not the decision to retain submitted ratings. Evidence: `flag_counts.csv`, `flagged_sample.csv`; `DECISIONS-peyton.md`.

## 9. Verify merges — Not applicable
No source tables are joined. A one-to-one metadata merge combines column rules with inspection profiles on `column`. Future Notes/Status History joins will require separate relationship and unmatched-key checks. Evidence: `clean_peyton.py`, Section 2.

## 10. Reconcile changes — Done
Starting and final counts are both 26,896,815 rows. Preparation preserved all 35 source fields, added two derived fields, and removed zero rows. Every prepared chunk was asserted equal to its original source fields before writing; the source SHA-256 was checked again. Both preparation runs completed these checks. Evidence: `evidence/peyton/transformation_report.csv`; `clean_peyton.py`, Section 3. An additional full readback comparison was omitted at the user’s request to limit verification.

## 11. Check calculations — Done
Each complete category distribution uses 26,896,815 rating records. Category totals are asserted equal to the row count; there are no incomplete category counts. Empty strings remain countable categories, rather than being silently excluded. All source timestamps parsed, so the inspected date range is supported by 26,896,815 records. Suggestion missingness does not reduce rating denominators. Planned outcome metrics separately show completed, unresolved, and unknown records with contributing counts; ratings alone cannot calculate them. Evidence: `category_counts.csv`, `inspection_manifest.json`; notebook dashboard plan.

## 12. Verify individual records — Done
Five AI-assisted expectations were saved before preparation using original strings and independent standard-library date arithmetic. Cases include optional blank text, a post sentinel, whitespace-only text, a nonempty suggestion, and a leading-zero participant ID. Expected reasons are recorded before comparing actual output. Evidence: `evidence/peyton/record_expectations.json`; all five actual results matched in `record_checks.json`, including UTC dates, invalid-date flags, and every original source field. These are agent-assisted checks, not a claim that the student manually performed them.

## 13. Test reproducibility — Unresolved
The cleaning script completed in a fresh Python process, and the notebook’s cleaning cells completed a second preparation run from the same source. Row counts, source hash, and reported flags agree. The extended notebook run was stopped during a redundant duplicate audit at the user’s request to limit verification time. The final all-output hash comparison and complete saved Run All were not completed, so full notebook reproducibility is not claimed. To run the optional extended check later: `python reproduce_peyton.py`. Evidence: `evidence/peyton/reproducibility.json` and the two local run logs.

## 14. Document remaining limitations — Done
Unknown source date/version/cutoff and sentinel semantics limit temporal and join interpretations. One Ratings shard does not establish platform-wide activity. Full status-history data, an agreed event definition, and an observation cutoff are still needed for response-time analysis. First non-NMR is not necessarily first Helpful. Preparation does not establish causal effects of additional ratings. Evidence: `DECISIONS-peyton.md`; notebook dashboard plan.

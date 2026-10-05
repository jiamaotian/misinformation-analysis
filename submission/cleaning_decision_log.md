# Cleaning Decision Log

This log summarizes the main cleaning decisions used in `scripts/clean_communitynotes.py`. Full rule SQL is in `data/cleaning_run/reports/rules.json` locally and summarized in `submission/evidence/validation_summary.md`.

| Area | Rule | Reason | Check |
|---|---|---|---|
| Raw files | Read ZIPs directly; do not extract or edit them | Preserve source integrity | Manifest SHA-256 verified before and after run |
| Provenance | Add `_source_file`, `_source_member`, `_source_row` to every cleaned row | Make every value traceable to raw source | Full roundtrip checks in validation summary |
| IDs | Keep large IDs as strings; known `-1` usable-key sentinels become null typed IDs with original token recoverable | Avoid precision loss and false joins | Manual cases 1-3; column comparison |
| Booleans | Convert `0`/`1` to false/true; invalid values become null and flagged | Make binary fields typed without guessing invalid values | Unit tests and column comparison |
| Categories | Trim category labels; preserve unknown nonblank labels and flag them | Avoid speculative remapping | Profile and transform reports |
| Timestamps | Preserve original integer epoch values; add nullable UTC companions | Keep raw values auditable while enabling time analysis | UTC mismatch checks; manual cases 4-5 |
| Timestamp sentinels | Interpret sentinel values by field, not globally | `-1` and `1` have field-specific meanings | Rules report; manual cases |
| PCRH signed time | Use absolute milliseconds for UTC companion and derive `pcrh_state` from sign | Sign carries status information | Manual case 4; `companions.json` summary |
| Scoring minute | Keep `timestampMinuteOfFinalScoringOutput` as integer metadata, not UTC | It is a scoring-output minute, not an event epoch | Manual case 4 |
| Text | Preserve original text; add trimmed companions for `summary` and `suggestion` | Avoid changing content while exposing whitespace-only cases | Text trim checks and flags |
| Source links | Split comma-separated `sourceLinks` into list; retain malformed links and flag them | Do not repair URLs without evidence | Manual case 1; nested URL checks |
| Nested suggestions | Parse JSON and convert valid nested IDs to strings; retain original JSON | Preserve nested structure and exact large IDs | Manual case 1; nested full check |
| Duplicates | Keep base cleaned rows; exclude only exact original-record copies from analysis views | Do not drop conflicting data | Duplicate reports show zero exclusions in full run |
| Joins | Preserve left-row cardinality and write join flags; do not drop unmatched records | Nonmatches may reflect snapshot scope, not invalid rows | Join reports and reproducibility check |
| Ratings summary | Aggregate ratings by note only as an explicit summary; keep legacy and version-2 counts separate | Avoid multiplying rows in note-level analysis | `ratings_by_note` reconciliation |

## Checked Codex Suggestion

Codex suggested that `timestampOfLastStateChange=1736527963` in the userEnrollment manual case looked like a suspicious timestamp range but should not be automatically multiplied by 1000 or replaced by `timestampOfLastEarnOut`.

I checked this suggestion by querying the actual cleaned row and the audit flag:

- Cleaned row: `data/cleaning_run/cleaned/userEnrollment/userEnrollment-00000.parquet`, `_source_row=1224917`
- Result: original integer retained; UTC companion is `1970-01-21 02:22:07.963000+00:00`; `timestampOfLastEarnOut` remains separate as `2024-04-03 15:58:35.303000+00:00`
- Audit: `data/cleaning_run/audit/userEnrollment-00000-flags.parquet` records `timestampOfLastStateChange:suspicious_timestamp_range`

The conclusion is recorded in `submission/evidence/manual_cases.md`: the value is retained and flagged as unresolved, not silently repaired.


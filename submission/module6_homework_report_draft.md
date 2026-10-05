# Module 6 Homework Report Draft

Student name: PO-YING, HO

Branch name: `clean-poying`

Branch URL: `https://github.com/jiamaotian/misinformation-analysis/tree/clean-poying`

Remote: `https://github.com/jiamaotian/misinformation-analysis.git`

Submission commit ID: 206d1671ca8ccd047492429c541bc37dce6f2919

This draft is intended to be copied into the final Gradescope PDF after student review. It is not the final PDF and has not been committed or pushed.

## Work Attribution

The student reviewed and confirmed the expected outcomes for the five difficult manual cases before actual cleaned outputs were checked.

Codex performed the mechanical repo work: reading project files, querying cleaned Parquet/audit outputs, rerunning the full pipeline, comparing reproducibility outputs, creating the small `submission/` folder, and drafting this report. Statements such as "queried", "checked", or "reran" refer to Codex-executed checks unless explicitly described as student review.

This report does not claim that the student personally ran DuckDB queries or the reproducibility run. The student should review this draft before final PDF submission.

## Data Source, Version, And Date Notes

Data source: public X/Twitter Community Notes download ZIPs.

Local raw path used by the completed run: `/Users/bobo/dso576/project/raw/communitynotes/data`.

Raw source files used: 17 ZIP files across five tables: `batSignals`, `notes`, `ratings`, `noteStatusHistory`, and `userEnrollment`.

Important date distinction:

- The run manifest records local raw file modification times from `2026-10-02T22:57:14.561223+00:00` to `2026-10-02T23:03:44.514467+00:00`.
- These modification times are not necessarily download dates.
- Actual download date reported by the student: 2026-09-15.
- The exact upstream Community Notes dataset version was not independently confirmed.
- Full cleaning run time was `2026-10-03T05:16:25.665994+00:00`.

Raw ZIPs, full cleaned Parquet files, and full row-level audit outputs remain local-only under Git-ignored `data/`.

## Project Vision, Research Question, Unit, And Metrics

This project keeps both directions documented in `objectives.md`.

Coverage direction: A Community Notes Product Manager at X wants to identify which posts or note requests need targeted note-writing effort to reduce gaps in Community Notes coverage.

Response Time direction: A Community Notes Product Manager at X wants to identify which types of notes need additional rating effort to reduce time required to reach a clear status.

Analysis units retained by the cleaning output:

- Request/post level: `batSignals`, keyed by `tweetId`.
- Note level: `notes` and `noteStatusHistory`, keyed by `noteId`.
- Rating level: `ratings`, keyed by `(noteId, raterParticipantId)` for candidate duplicate checks.
- Contributor snapshot level: `userEnrollment`, keyed by `participantId`.

Candidate metrics from project documents:

- Coverage: eligible request coverage rate, uncovered request rate, coverage gap between groups, eligibility-to-first-note time.
- Response Time: helpful display rate, median time to first Helpful or first non-NMR status, long-wait unresolved rate, status reversal rate.

Confirmed direction and unresolved analysis choices:

- The project will keep both Coverage and Response Time as active directions.
- Feed choice is unresolved.
- Observation period is unresolved.
- Cutoff date is unresolved.
- Final metric denominators are unresolved.
- For Response Time, the endpoint is unresolved: first non-NMR, first Helpful, locked status, or another event.

## Teacher Checklist

| # | Item | Status | Evidence and notes |
|---:|---|---|---|
| 1 | 專題願景與問題 | Done | `objectives.md` defines both Coverage and Response Time directions; this report preserves both. |
| 2 | 每列定義 | Done | Table grains are documented above and preserved in the cleaner. Evidence: `plan.md`, `scripts/clean_communitynotes.py`, validation row counts below. |
| 3 | 保留來源 | Done | Every cleaned row has `_source_file`, `_source_member`, `_source_row`; raw ZIP hashes and full source reconstruction were checked. |
| 4 | 欄位與型態 | Done | All 98 source columns have explicit rules; schema/type comparisons passed in reproducibility checks. |
| 5 | 文字標準化 | Done | Original text is retained; trimmed/list/parsed companions are added. Evidence: decision log and manual cases. |
| 6 | 重複資料 | Done | Candidate-key duplicate groups and exact duplicate rows were checked separately; both are zero for all five tables. |
| 7 | 缺失資料 | Done | Missing and sentinel handling is documented and checked. Before/after missing counts for affected fields are in Appendix A. |
| 8 | 可疑值 | Done | Suspicious values are flagged before treatment and retained when unresolved. Evidence: suspicious-value table and manual cases. |
| 9 | 合併驗證 | Done | Join keys, expected relationships, before/after row counts, and unmatched counts are listed below. |
| 10 | 筆數與總數核對 | Done | Source and cleaned row counts match for all tables; ratings summary reconciles to all ratings. |
| 11 | 計算與分母 | Unresolved | Some denominators are verified, such as valid `helpfulnessLevel`; final Coverage/Response Time denominators remain unresolved. |
| 12 | 五筆紀錄核對 | Done | Five student-reviewed expected outcomes and Codex-queried actual results are included below. |
| 13 | 可重現性 | Done | Fresh full run passed validation; old/new outputs had matching file lists and content fingerprints, with only metadata/order differences. |
| 14 | 剩餘限制 | Done | Remaining unresolved items are listed at the end. |

## Row Counts And Duplicate Checks

Different duplicate types are separated:

- Candidate-key duplicate groups: repeated logical keys such as `noteId` or `(noteId, raterParticipantId)`.
- Exact duplicate rows: complete source-record copies.
- Analysis exclusions: exact duplicate copies removed from analysis views, if any.

| Table | Candidate key | Raw rows | Cleaned rows | Candidate-key duplicate groups | Exact duplicate rows | Analysis exclusions |
|---|---|---:|---:|---:|---:|---:|
| `batSignals` | `tweetId` | 487,851 | 487,851 | 0 | 0 | 0 |
| `notes` | `noteId` | 3,137,735 | 3,137,735 | 0 | 0 | 0 |
| `ratings` | `noteId`, `raterParticipantId` | 235,530,477 | 235,530,477 | 0 | 0 | 0 |
| `noteStatusHistory` | `noteId` | 3,343,818 | 3,343,818 | 0 | 0 | 0 |
| `userEnrollment` | `participantId` | 1,497,640 | 1,497,640 | 0 | 0 | 0 |

Evidence: `data/module6_validation/*-keys.json`, `submission/evidence/validation_summary.md`, `submission/evidence/run_summary.json`.

## Field Types, Type Conversion Failures, And Missing Values

All source rows were retained. Type conversion changed storage type for many values, for example `0`/`1` to booleans and epoch integers to timestamp companions. These are type changes, not row drops.

Verified type-conversion result:

- Mapping mismatches against the recorded SQL contract: 0 across all checked source columns.
- Nonblank boolean/integer/timestamp parse-to-null failures in the full-column comparison: 0.
- Known sentinel-to-null typed values are not counted as parse failures. Examples: `notes.tweetId=-1`, `ratings.ratedOnTweetId=-1`, and `ratings.suggestionId=-1`.
- Suspicious or invalid values remain retained and flagged. Example: `userEnrollment.timestampOfLastStateChange` has two flag events on two different rows: `invalid_timestamp` = 1 (source row 687,733, raw value `0`) and `suspicious_timestamp_range` = 1 (source row 1,224,917, raw value `1736527963`).

Affected missing-value examples are in Appendix A. The most important ones:

| Field | Raw missing or sentinel condition | Cleaned missing/NULL | Handling |
|---|---:|---:|---|
| `notes.tweetId` | 8 rows with sentinel `-1` | 8 NULL usable IDs | Note retained; unavailable for tweetId joins |
| `notes.classification` | 2 raw blanks | 2 NULL | Note retained; classification unknown |
| `ratings.helpfulnessLevel` | 34,394 raw blanks | 34,394 NULL | Legacy ratings retained; not in valid-level denominator |
| `ratings.ratedOnTweetId` | 2,631,448 sentinel/unusable IDs | 2,631,448 NULL | Rating retained; unavailable for this join key |
| `ratings.suggestionId` | 235,514,406 sentinel/unusable IDs | 235,514,406 NULL | Rating retained; original token recoverable |
| `noteStatusHistory.timestampMillisOfFirstNonNMRStatus` | 2,767,657 raw blanks | 2,767,657 NULL | Status row retained; unavailable for completed first-non-NMR timing |
| `userEnrollment.timestampOfLastStateChange` | 0 raw blanks; 1 invalid timestamp flag and 1 suspicious range flag on two different rows | typed integer retained; UTC companion has 1 missing/unusable value in column comparison | Retained and flagged; not auto-repaired |

## Suspicious Values

Flag events can overlap on the same row, so event counts are not the same as distinct row counts.

| Table | Flag events | Distinct flagged rows | Main rules |
|---|---:|---:|---|
| `batSignals` | 9 | 5 | malformed source URLs and nested source URLs |
| `notes` | 4 | 4 | missing classification and blank text |
| `ratings` | 13 | 13 | blank suggestion text |
| `noteStatusHistory` | 2,175,237 | 2,174,994 | unverified `-1` stable-NMR semantics; resolved missing first history |
| `userEnrollment` | 549 | 549 | earn-out disagreement = 547; `timestampOfLastStateChange:invalid_timestamp` = 1; `timestampOfLastStateChange:suspicious_timestamp_range` = 1 |

Handling: suspicious values are retained with original source references and conservative treatment. No row is deleted solely because it is suspicious.

## Join Checks

Join validation preserved row counts. Unmatched rows were flagged, not dropped. These checks are not final Coverage or Response Time denominators.

| Join | Key | Expected relation | Rows before | Rows after | Matched | Unmatched incl. unavailable | Unavailable left key |
|---|---|---|---:|---:|---:|---:|---:|
| notes -> requests | `tweetId` | many notes to request/post lookup | 3,137,735 | 3,137,735 | 170,383 | 2,967,352 | 8 |
| notes -> status | `noteId` | note to status lookup | 3,137,735 | 3,137,735 | 2,897,146 | 240,589 | 0 |
| status -> notes | `noteId` | status to note lookup | 3,343,818 | 3,343,818 | 2,897,146 | 446,672 | 0 |
| notes -> authors | `noteAuthorParticipantId=participantId` | many notes to enrollment lookup | 3,137,735 | 3,137,735 | 3,137,735 | 0 | 0 |
| ratings -> notes | `noteId` | many ratings to note lookup | 235,530,477 | 235,530,477 | 212,762,691 | 22,767,786 | 0 |
| ratings -> raters | `raterParticipantId=participantId` | many ratings to enrollment lookup | 235,530,477 | 235,530,477 | 235,530,477 | 0 | 0 |
| requests -> notes | `tweetId` with distinct note tweet IDs | request/post to at-least-one-note lookup | 487,851 | 487,851 | 111,372 | 376,479 | 0 |

Additional checks:

- Matched note/status creation-time disagreements: 0.
- Matched note/status author disagreements: 0.
- Matched ratings earlier than note creation: 0.

Evidence: `data/module6_validation/joins.json`, `submission/evidence/validation_summary.md`.

## Verified Calculations And Effective Denominators

These are verified cleaning/validation denominators, not final project denominators.

`helpfulnessLevel` distribution:

| Value | Count |
|---|---:|
| `HELPFUL` | 144,595,094 |
| `SOMEWHAT_HELPFUL` | 6,092,969 |
| `NOT_HELPFUL` | 84,808,020 |
| Missing legacy level | 34,394 |

Effective denominator for valid `helpfulnessLevel` distribution: 235,496,083. This equals version-2 rating count. It is not a Coverage denominator and not a Response Time denominator.

Helpful share among valid `helpfulnessLevel` ratings: 144,595,094 / 235,496,083 = 61.4002%.

Other verified denominators:

- Total ratings: 235,530,477.
- Distinct note groups in `ratings_by_note`: 3,215,297.
- Sum of `rating_count` in `ratings_by_note`: 235,530,477.
- Status rows: 3,343,818.
- Status rows with nonmissing first non-NMR time: 576,161.
- Currently resolved status rows: 419,954.
- Currently resolved rows missing first non-NMR time: 1,357.

Feed state counts are verified but final feed choice is unresolved:

| Feed field | Eligible | Ineligible | Unknown |
|---|---:|---:|---:|
| `noteRequestFeedEligibleAtMillis` | 28,597 | 459,254 | 0 |
| `apiSmallFeedEligibleAtMillis` | 28,964 | 458,887 | 0 |
| `apiLargeFeedEligibleAtMillis` | 168,583 | 319,268 | 0 |
| `apiXlFeedEligibleAtMillis` | 487,506 | 345 | 0 |

## Cleaning Decision Log

| Area | Rule | Reason | Check |
|---|---|---|---|
| Raw files | Read ZIPs directly; do not extract or edit them | Preserve source integrity | Manifest SHA-256 verified before and after run |
| Provenance | Add `_source_file`, `_source_member`, `_source_row` to every row | Make every cleaned value traceable | Full TSV roundtrip checks |
| IDs | Store large IDs as strings | Avoid precision loss | Manual cases 1-3 |
| ID sentinels | Known `-1` usable-key sentinels become null typed IDs; raw tokens remain recoverable | Avoid false joins on `-1` | Manual cases 2-3 |
| Booleans | Convert `0`/`1` to false/true; invalid values are flagged | Typed binary analysis without guessing | Unit tests and validation summary |
| Categories | Trim structured category labels; preserve unknown nonblank labels | Avoid speculative remapping | Rules and transform reports |
| Timestamps | Preserve original integers and add nullable UTC companions | Keep raw values auditable | Manual cases 4-5 |
| PCRH signed time | Use absolute milliseconds for UTC companion and derive `pcrh_state` from sign | Sign contains state information | Manual case 4 |
| Scoring minute | Keep `timestampMinuteOfFinalScoringOutput` as integer metadata | It is not an epoch event timestamp | Manual case 4 |
| Text | Preserve original text; add trimmed companions | Avoid changing content while exposing whitespace issues | Validation summary text checks |
| URLs/nested suggestions | Split source links, parse nested JSON, convert valid nested IDs to strings, flag malformed URLs | Preserve structure without unsupported repair | Manual case 1 |
| Duplicates | Keep base rows; exclude only exact original-record copies from analysis views | Avoid dropping conflicting data | Duplicate reports show zero exclusions |
| Joins | Preserve left-row cardinality and write join flags | Nonmatches may reflect snapshot scope | Join validation reports |

## Five Record Checks

The student reviewed and confirmed expected outcomes before actual cleaned results were queried. Codex later queried actual cleaned rows and audit flags. The expected results below are summarized from the previously confirmed expectations and were not rewritten to match the actual output.

| Case | Raw value(s) | Expected result and reason | Actual result | Match? |
|---|---|---|---|---|
| 1. `batSignals`, row 14,509 | `sourceLinks="yuujihttps://x.com/..."`; nested `source_link="Yuujihttps://x.com/..."`; small/standard feed `-1`; large/XL `1784756989691` | Keep request and raw values; split source links but do not repair malformed prefixes; `-1` feed values become ineligible/null UTC; large/XL become eligible UTC; nested `suggestion_id` becomes string to avoid precision loss. | `sourceLinks_list` retained malformed token; `suggestions_parsed` has string `"2080047309124174174"`; standard/small `ineligible`; large/XL `eligible` at `2026-07-22 21:49:49.691000+00:00`; URL flags recorded. | Yes |
| 2. `notes`, row 114 | `tweetId="-1"`; blank `classification`, `believable`, `harmful`, `validationDifficulty`; `isCollaborativeNote="1"` | Keep note; make `tweetId` unavailable for joins; keep classification and related fields missing; convert binary fields; preserve summary text. Reason: missing classification and unavailable tweet ID do not invalidate note-level record. | `tweetId=NULL`; classification-related fields NULL; `isMediaNote=false`; `isCollaborativeNote=true`; summary preserved; `classification:missing_classification` flag. | Yes |
| 3. `ratings`, row 1 | version `1`; `helpful="1"`; `notHelpful="0"`; blank `helpfulnessLevel`; `ratedOnTweetId="-1"`; `suggestionId="-1"` | Keep legacy rating; preserve helpful/notHelpful; do not infer `helpfulnessLevel`; exclude from valid-level denominator. Reason: legacy binary format is separate from new level format. | `version=1`; `helpful=true`; `notHelpful=false`; `helpfulnessLevel=NULL`; `ratedOnTweetId=NULL`; `suggestionId=NULL`. | Yes |
| 4. `noteStatusHistory`, row 595 | `timestampMillisAbovePcrhThreshold="-1788540132611"`; `timestampMinuteOfFinalScoringOutput="29845679"`; current status NMR but core/expansion Helpful | Preserve signed PCRH value; derive UTC from absolute value and `no_longer_above`; keep scoring minute as integer, not UTC; do not overwrite current overall status from submodels. | PCRH UTC `2026-09-04 16:42:12.611000+00:00`; `pcrh_state="no_longer_above"`; scoring minute has no `_utc`; current status remains `NEEDS_MORE_RATINGS`; NMR stable-time `-1` flagged unresolved. | Yes |
| 5. `userEnrollment`, row 1,224,917 | `timestampOfLastStateChange="1736527963"`; `timestampOfLastEarnOut="1712159915303"`; `modelingGroup="13.0"` | Keep participant; flag suspicious timestamp range/unit; do not multiply by 1000 or overwrite from earn-out time; parse exact integral group as 13. Reason: unit issue is plausible but unconfirmed. | State-change integer retained; UTC companion `1970-01-21 02:22:07.963000+00:00`; earn-out UTC remains separate; `modelingGroup=13`; suspicious timestamp flag recorded. | Yes, with analytic use unresolved |

## Codex Suggestion Check

Codex suggested that `timestampOfLastStateChange=1736527963` in Case 5 should be treated as suspicious and not automatically converted as seconds or overwritten with `timestampOfLastEarnOut`.

Student role: reviewed the expected treatment and confirmed it should remain conservative.

Codex role: queried the cleaned row and audit flag. The query found that the pipeline retained the raw integer, produced a 1970 UTC companion, kept `timestampOfLastEarnOut` separate, and recorded `suspicious_timestamp_range`.

Conclusion: the Codex suggestion was checked against actual cleaned output and audit evidence. It remains an unresolved data-quality issue, not a repaired value.

## Reproducibility Summary

Codex executed a fresh full run to `data/repro_cleaning_run` without overwriting `data/cleaning_run`.

Results:

- New run validation: passed.
- File list: 86 old files and 86 new files; no missing or extra files.
- Parquet files compared: 35.
- Schema/type mismatches: none.
- Row count mismatches: none.
- Order-insensitive content fingerprint mismatches: none.
- Differences observed: run metadata, run-specific paths, JSON list ordering, and row order in four SQL-derived outputs.

Evidence copied into the submission folder:

- `submission/evidence/reproducibility_report.md`
- `submission/evidence/reproducibility_comparison_summary.json`

## Sample Data

The Git-safe cleaned sample contains 5 total data rows, one per table, selected from the five manual difficult cases.

Files:

- `submission/cleaned_sample/batSignals_manual_case_sample.csv`
- `submission/cleaned_sample/notes_manual_case_sample.csv`
- `submission/cleaned_sample/ratings_manual_case_sample.csv`
- `submission/cleaned_sample/noteStatusHistory_manual_case_sample.csv`
- `submission/cleaned_sample/userEnrollment_manual_case_sample.csv`

Selection method and source rows are documented in `submission/sample_manifest.json`.

## Appendix A: Missing Counts For Affected Fields

Fields with raw blanks, sentinel-to-null handling, UTC companion missingness, or validation-relevant NULL counts are listed here. Mapping mismatches were 0. This appendix is based on `data/module6_validation/column_comparison.md`; no data was rerun for this update.

| Table | Field | Raw empty count | Cleaned NULL count | Nonblank parse-to-null failures | Notes |
|---|---|---:|---:|---:|---|
| `batSignals` | `noteRequestFeedEligibleAtMillis_utc` | 0 in source field | 459,254 | 0 | UTC companion null when feed is ineligible |
| `batSignals` | `apiSmallFeedEligibleAtMillis_utc` | 0 in source field | 458,887 | 0 | UTC companion null when feed is ineligible |
| `batSignals` | `apiLargeFeedEligibleAtMillis_utc` | 0 in source field | 319,268 | 0 | UTC companion null when feed is ineligible |
| `batSignals` | `apiXlFeedEligibleAtMillis_utc` | 0 in source field | 345 | 0 | UTC companion null when feed is ineligible |
| `batSignals` | `sourceLinks` | 372,919 | 0 | N/A | Text preserved; empty text remains empty; list companion can be empty |
| `notes` | `tweetId` | 0 | 8 | N/A | `-1` sentinel made unusable typed ID |
| `notes` | `classification` | 2 | 2 | N/A | Missing classification retained |
| `notes` | `believable` | 3,113,054 | 3,113,054 | N/A | Missing category retained |
| `notes` | `harmful` | 3,113,054 | 3,113,054 | N/A | Missing category retained |
| `notes` | `validationDifficulty` | 3,113,054 | 3,113,054 | N/A | Missing category retained |
| `ratings` | `helpfulnessLevel` | 34,394 | 34,394 | N/A | Legacy ratings retained; no imputation |
| `ratings` | `ratedOnTweetId` | 0 | 2,631,448 | N/A | `-1` sentinel made unusable typed ID |
| `ratings` | `suggestion` | 235,503,178 | 0 | N/A | Text preserved; blank text remains blank |
| `ratings` | `suggestionId` | 0 | 235,514,406 | N/A | `-1` sentinel made unusable typed ID |
| `noteStatusHistory` | `timestampMillisOfFirstNonNMRStatus` | 2,767,657 | 2,767,657 | 0 | Missing milestone retained |
| `noteStatusHistory` | `firstNonNMRStatus` | 2,767,657 | 2,767,657 | N/A | Missing milestone category retained |
| `noteStatusHistory` | `timestampMillisOfLatestNonNMRStatus` | 2,767,657 | 2,767,657 | 0 | Missing latest non-NMR time retained |
| `noteStatusHistory` | `mostRecentNonNMRStatus` | 2,767,657 | 2,767,657 | N/A | Missing latest non-NMR status retained |
| `noteStatusHistory` | `timestampMillisOfStatusLock` | 240,179 | 240,179 | 0 | Missing lock time retained |
| `noteStatusHistory` | `lockedStatus` | 240,179 | 240,179 | N/A | Missing lock status retained |
| `noteStatusHistory` | `timestampMillisOfRetroLock` | 3,342,306 | 3,342,306 | 0 | Missing retro-lock time retained |
| `noteStatusHistory` | `currentCoreStatus` | 706,547 | 706,547 | N/A | Missing submodel status retained |
| `noteStatusHistory` | `currentExpansionStatus` | 183,861 | 183,861 | N/A | Missing submodel status retained |
| `noteStatusHistory` | `currentGroupStatus` | 2,289,825 | 2,289,825 | N/A | Missing group status retained |
| `noteStatusHistory` | `currentModelingGroup` | 2,289,825 | 2,289,825 | 0 | Missing group id retained |
| `noteStatusHistory` | `timestampMillisOfMostRecentStatusChange_utc` | 0 in source field | 1,093,544 | 0 | UTC companion null for `-1` sentinel/no recorded change |
| `noteStatusHistory` | `timestampMillisOfNmrDueToMinStableCrhTime` | 1,170,025 | 1,170,025 | 0 | Blank retained as missing; `-1` semantics flagged separately |
| `noteStatusHistory` | `timestampMillisOfNmrDueToMinStableCrhTime_utc` | 1,170,025 source blanks plus `-1`/unavailable values | 3,343,787 | 0 | UTC companion null for blanks and sentinel/unavailable values |
| `noteStatusHistory` | `currentMultiGroupStatus` | 3,280,453 | 3,280,453 | N/A | Missing multigroup status retained |
| `noteStatusHistory` | `currentModelingMultiGroup` | 3,280,453 | 3,280,453 | 0 | Missing multigroup id retained |
| `noteStatusHistory` | `timestampMillisOfFirstNmrDueToMinStableCrhTime` | 3,112,207 | 3,112,207 | 0 | Blank retained as missing; `-1` semantics flagged separately |
| `noteStatusHistory` | `timestampMillisOfFirstNmrDueToMinStableCrhTime_utc` | 3,112,207 source blanks plus `-1`/unavailable values | 3,112,325 | 0 | UTC companion null for blanks and sentinel/unavailable values |
| `noteStatusHistory` | `timestampMillisAbovePcrhThreshold` | 3,317,870 | 3,317,870 | 0 | PCRH absent vs signed values handled separately |
| `noteStatusHistory` | `timestampMillisAbovePcrhThreshold_utc` | 3,317,870 source blanks plus unavailable/invalid PCRH values | 3,324,230 | 0 | UTC companion null when no recorded event or invalid/unavailable |
| `userEnrollment` | `timestampOfLastStateChange` | 0 | 0 | 0 | Raw integer retained |
| `userEnrollment` | `timestampOfLastStateChange_utc` | 0 source blanks | 1 | 0 | One invalid timestamp has null UTC companion; also flagged suspicious range |
| `userEnrollment` | `timestampOfLastEarnOut` | 0 | 0 | 0 | Raw integer retained, including sentinel |
| `userEnrollment` | `timestampOfLastEarnOut_utc` | 0 source blanks | 1,407,922 | 0 | UTC companion null for documented never-earned-out sentinel |
| `userEnrollment` | `never_earned_out_consistent` | derived field | 547 | N/A | Null where earn-out sentinel and count disagree |

## Remaining Limitations And Missing Information

- Submission commit ID: 206d1671ca8ccd047492429c541bc37dce6f2919
- Exact upstream dataset version: TBD / not confirmed.
- Actual download date: 2026-09-15, as reported by the student. Local raw file modification times are recorded separately and are not claimed as download dates.
- Coverage and Response Time are both retained as confirmed project directions.
- Feed choice, observation period, cutoff date, and final metric denominators remain Unresolved.
- Response Time endpoint remains Unresolved: first non-NMR, first Helpful, locked status, or another event.
- Some sentinel semantics remain unresolved, especially NMR stable-time `-1` meanings.
- Suspicious timestamp unit issues are retained and flagged but not resolved.
- Cross-table nonmatches are preserved and flagged; their real-world causes are not proven by the available snapshots.
- This is still a draft report, not the final Gradescope PDF.

# BUILD_SPEC — Observed Coverage and Response-Time Monitor

**DSO 576 | Project Area 6: Misinformation on Social Media | Phase 2 → Phase 3 handoff**  
**Team contributions:** Julia — vision and use cases; Kaitlyn — dashboard specification; Peyton — Notes/Note Requests cleaning; Yoojin — Ratings/Note Status History cleaning; Euan — coverage backend; Jessica — response-time and ratings backend / integration.  
**Document purpose:** One implementable product and data contract for the Phase 3 dashboard MVP. This is a **specification**, not a claim that the Phase 3 UI or every proposed interaction has already been implemented.

## 1. Vision and decision support

### 1.1 Target user and decision

The primary user is a **Community Notes Product Manager** monitoring how extensively eligible posts receive notes, how long notes take to reach a first non–Needs More Ratings (non-NMR) status, and how rating activity and observed rating helpfulness vary. The Product Manager uses the results to **prioritize investigation** of observed coverage gaps and longer waiting patterns, not to infer that adding contributors or ratings will cause improvements.

The dashboard consolidates Note Requests, Notes, Ratings, and Note Status History, avoiding manual comparisons across disconnected files. It is an **observational** monitoring tool; it does not prove misinformation prevalence, causal effects, platform-wide coverage, or cross-contributor agreement.

### 1.2 Core use cases (select → see → decide)

| Use case | User selects / inputs | Dashboard shows | User decides |
|---|---|---|---|
| UC1 — Coverage | Request-eligibility date interval; one feed; observation window | Eligible requests; covered requests; no observed qualifying note; weekly counts/rates | Which periods merit investigation for observed gaps |
| UC2 — Time to first non-NMR | Note-creation dates; classification and note type; observation window | Mature eligible notes; first non-NMR completions; no recorded transition; median completed-event hours; by-classification counts | Which note groups merit further investigation for slower transitions |
| UC3 — Rating activity and observed helpfulness | Same Response cohort controls | Early ratings versus completed response time; rating activity by date; HELPFUL/SOMEWHAT_HELPFUL/NOT_HELPFUL counts/shares | Which cohorts or periods merit deeper review, without causal claims |

Every MVP component below serves at least one of UC1–UC3. Coverage and Response/Ratings filters are **independent**.

## 2. One-page dashboard specification

### 2.1 Starting view and layout

Build **one scrollable page**, no tabs. In order:

1. **Header:** title, short purpose, data-source/shard labels, snapshot provenance and verified UTC cutoff or prominent **unverified cutoff** warning.
2. **Coverage (UC1):** local date/feed/window controls; three KPI cards (eligible, covered/rate, no observed note); weekly coverage chart and weekly counts table.
3. **Response Time & Ratings (UC2–3):** local note-created date, classification, note type, and window controls; four KPI cards (eligible notes, reached first non-NMR/completion rate, no recorded transition, median hours with completed-event N); completed versus no-recorded-transition stacked bars by classification; early ratings–response-time scatter.
4. **Rating Helpfulness (UC3):** HELPFUL/SOMEWHAT_HELPFUL/NOT_HELPFUL counts and percentage distribution, explicit denominator, and excluded/missing/legacy ratings count.
5. **Review candidates:** descriptive flags for low observed coverage or long waits, always with cohort sizes and caveats; no causal recommendations.
6. **Footer:** metric/data-quality definitions, exclusion counts, version/scope notices and export of **filtered aggregate tables**, not raw records.

### 2.2 Shared units and boundary conventions

- All event timestamps are interpreted as **UTC Unix milliseconds**. UTC weekly bins begin **Monday 00:00 UTC**.
- Default observation window **W = 7 days**; offer **7 / 14 / 28 days**. This is the dashboard-design proposal, **pending team sign-off** against the existing backend.
- Default date range is the **latest 28 complete UTC dates for which each record can mature by the verified cutoff**; specify date interval as half-open `[start, end)`.
- A completed event at the **window boundary** is included (`event_time <= start_event + W`). A request's note must also be at or after its eligibility event (`note_created >= eligibility_time`).
- Time-window denominator requires **maturity**: `origin_timestamp + W <= verified_cutoff`. Show excluded immature counts; don't silently change dates. If no trustworthy cutoff exists, **warn and suppress time-window KPI computation** instead of inventing one.
- Keep integer counts; compute fractions without rounding, display percentages and hours to **one decimal place**; comma-separate counts. Show **N/A** and reason for empty denominator or no completions.

## 3. Exact metric contracts and filters

### 3.1 Coverage (UC1; backend owner: Euan)

**Unit:** one distinct eligible request `tweetId` in the provided Note Requests cohort. The feed-specific eligibility field is selected from:

| Feed | Timestamp column |
|---|---|
| Standard | `noteRequestFeedEligibleAtMillis` |
| Small | `apiSmallFeedEligibleAtMillis` |
| Large | `apiLargeFeedEligibleAtMillis` |
| XL | `apiXlFeedEligibleAtMillis` |

Eligibility is a **feed eligibility event**, not necessarily a user-submission time. Retain only positive, parseable timestamps with `start <= eligibility < end` and `eligibility + W <= cutoff`. Negative sentinel values are excluded and counted, **not assigned guessed meanings**.

A request is **observed covered** if at least one matching `Notes.tweetId` was created at `eligibility <= createdAtMillis <= eligibility + W`. Count each request once. Earlier or late notes do not qualify.

| Metric / output | Computation | Source / filtering |
|---|---|---|
| Eligible requests | Distinct mature selected request `tweetId` count | Requests feed/date/W/cutoff |
| Covered requests | Number of eligible requests with ≥1 qualifying observed note | Requests joined to Notes via `tweetId`; each request counted once |
| Observed coverage rate | `covered / eligible` | Null if zero eligible |
| No observed note | `eligible - covered`; share `(eligible - covered)/eligible` | Not proof that a post needs a note |
| Time to first qualifying note | `(min qualifying Notes.createdAtMillis - eligibility) / 3_600_000` | Only covered requests; median conditional on coverage |
| Weekly chart/table | Eligible/covered/no-observed-note/rate by `eligibility_week_utc` | Overall rate computed from **pooled counts**, never average of weekly rates |

**Backend handoff:** `phase2-euan/coverage_analysis.py` exports `analyze_coverage(requests, notes, *, cutoff, feed='Standard', window_days=7, start=None, end=None)` returning `summary`, `requests`, `weekly`, `gaps`; `save_results(results, folder)` writes tables/JSON. Euan's handoff and results are in `phase2-euan/COVERAGE_HANDOFF.md` and `phase2-euan/results/`.

### 3.2 Response time (UC2; backend owner: Jessica)

**Unit:** one valid, unique `Notes.noteId` in the selected note-created date range and note-type/classification selection. Join Status History by `noteId` (**one-to-one**, never many-to-many). Preserve **Unknown** classification.

**Proposed fixed-window dashboard definitions** (Kaitlyn's design; build target):

1. **Eligible notes:** valid notes created in selected `[start, end)`, mature under `createdAtMillis + W <= verified_cutoff`, with usable note creation time; explicitly report invalid, duplicate, unmatched status and inconsistent-history exclusions. Decide with the team whether unmatched status belongs in the dashboard denominator (the specification proposes reporting unmatched separately; no silent exclusion).
2. **Completed within W:** first non-NMR status is `CURRENTLY_RATED_HELPFUL` or `CURRENTLY_RATED_NOT_HELPFUL`, first-event timestamp exists, `createdAtMillis <= timestampMillisOfFirstNonNMRStatus <= createdAtMillis + W`, and event at/before cutoff. `NEEDS_MORE_RATINGS` is not completion.
3. **No recorded transition within W:** `eligible notes - completed within W`; includes later transitions, with explicit distinction from missing or invalid status history. This is an observed classification, **not proof of never resolving**.
4. **Completion rate:** `completed within W / eligible notes`, null if no eligible notes.
5. **Median response time:** median of `(timestampMillisOfFirstNonNMRStatus - Notes.createdAtMillis)/3_600_000` over **completed within W only**; report completed-event `N`. Uncompleted response times stay null, not 0.
6. **Classification bars:** completed/no recorded transition **counts** by classification (including Unknown), showing group denominators.

**Existing Phase 2 implementation:** `phase2-jessica/response_ratings_analysis.py` implements `calculate_response_time(notes, status, cutoff_ms=None)` and `summarize_response_time(response_df)` with note-to-first-non-NMR timing and classification summary. `phase2-jessica/run_real_analysis.py` reads actual cleaned files and saves results. **Important gap:** the committed real-data figures include first non-NMR transitions observed by the cutoff **without imposing Kaitlyn's 7-day maturity and completion window**. They are baseline observed results, **not** the fixed-window dashboard KPI. The fixed-window filters/denominator must be implemented or reconciled explicitly before a compliant Phase 3 view reports them.

### 3.3 Rating activity and helpfulness (UC3; backend owner: Jessica)

**Unit:** one rating on a note in the selected Response cohort. Join by `noteId`; ensure ratings do not multiply across status rows. Preserve note IDs as strings. Apply Yoojin's cleaned validity flags where available, and disclose removed or unmatched ratings.

| Output | Proposed dashboard metric (Kaitlyn) | Source columns |
|---|---|---|
| Early ratings scatter | **One point per completed note**; X = valid rating count with `note_created <= rating_created <= note_created + 24h`; Y = hours to first non-NMR, max W days | Ratings `noteId`, `createdAtMillis`, validity, Notes creation, Status first non-NMR |
| Rating activity over time | Counts by UTC rating day/week for selected response cohort and configured window | Ratings `createdAtMillis`, `noteId` |
| Rating helpfulness distribution | Counts/shares of `HELPFUL`, `SOMEWHAT_HELPFUL`, `NOT_HELPFUL` for valid ratings on selected eligible notes **after note creation and within W**, using only three valid categories as denominator | Ratings `helpfulnessLevel` (or `helpfulnessLevel_clean`), `createdAtMillis`, validity; Notes `noteId` |
| Missing/legacy exclusions | Separately display invalid/missing/legacy helpfulness levels and unmatched notes | Cleaning quality flags plus join reconciliation |

`observed_helpful_share = HELPFUL_valid_matched / (HELPFUL + SOMEWHAT_HELPFUL + NOT_HELPFUL)_valid_matched`. This measures **rating distribution, not official note status or broad agreement**. One contributor-note duplicate policy must match the agreed canonical cleaning rules; do not silently choose a different policy for streaming and in-memory code.

**Existing Phase 2 implementation:** `calculate_rating_activity`, `prepare_activity_scatter`, `calculate_helpfulness`, `summarize_helpfulness`, `build_dashboard_data` in `phase2-jessica/response_ratings_analysis.py`; large-file chunked runner in `phase2-jessica/run_real_analysis.py`. The committed real run counts all valid matched ratings **up to a provisional cutoff** and outputs all note-level scatter rows, including unresolved notes; it does **not** yet implement the strict first-24-hour rating scatter, W-day post-creation helpfulness restriction, or 2,000-point display sampling. Phase 3 must not label those current aggregate files as compliant early-rating/windowed visualizations without adaptation.

### 3.4 Local filter contracts

| Section | Filters | Effects |
|---|---|---|
| Coverage | Eligibility date `[start,end)`; feed Standard/Small/Large/XL; W=7/14/28 days | Only Coverage cards, weekly chart and table; selecting a week recomputes its cards while retaining full overview |
| Response/Ratings | Note-created `[start,end)`; classification multi-select incl. Unknown; note type All/Media/Non-media/Collaborative/Unknown; W=7/14/28 days | Response cards, classification bars, scatter, helpfulness and rating trends; **never Coverage** |

Note-type categories may overlap; classification is not the same as note type. Define note types using available Notes indicators (`isMediaNote`, `isCollaborativeNote`), and Unknown for missing/unusable flags; do not assume a mutually exclusive categorical field. Reset buttons are **section-local**. Filter changes clear dependent chart selections. Chart hover supplies units and denominators; optional scatter selection shows read-only detail without changing KPIs.

If eligible completed points exceed **2,000**, show a **deterministically sampled**, labeled scatter (e.g., stable hash of noteId); all cards and aggregates retain the **full** eligible cohort.

## 4. Data contract, reconciliation and provenance

### 4.1 Sources and cleaning owners

| Table | Relevant keys / columns | Cleaning source |
|---|---|---|
| Note Requests | `tweetId`, feed eligibility timestamps | `phase2-peyton/clean_notes_requests.py` |
| Notes | `noteId`, `tweetId`, `createdAtMillis`, `classification`, media/collaborative indicators | `phase2-peyton/clean_notes_requests.py` |
| Ratings | `noteId`, `raterParticipantId`, `createdAtMillis`, `helpfulnessLevel`; cleaned/validity fields | `yoojin_phase 2/clean_ratings_status.py` |
| Note Status History | `noteId`, `createdAtMillis`, `firstNonNMRStatus`, `timestampMillisOfFirstNonNMRStatus`, `qc_response_eligible` | `yoojin_phase 2/clean_ratings_status.py` |

The source-table unit is **request tweet**, **note**, **rating**, and **note status history row**, respectively. Keep original IDs as strings to prevent precision loss; never join Ratings × Status History raw rows without first establishing a one-note status key and aggregating ratings by note. Keep original raw values and derived QC fields distinguishable. Invalid values should be counted and documented, not fabricated.

### 4.2 Canonical snapshot decision — not yet established

**The team has not demonstrated one reconciled canonical snapshot covering all four tables.** This is a material Phase 2 open decision, not just a display footnote. For a final grade-ready version, agree and record a single scope, snapshot/cutoff, exact input file hashes, shard list, normalized keys, cleaning exclusions, and join counts; rerun both backend modules when needed. If a common snapshot cannot be produced, explicitly identify outputs as **independent partial-shard demonstrations**, keep provenance next to each section, and do not compare them as if they covered the same platform population.

Known current provenance:

- Euan's Coverage handoff used `notes-00001.tsv` (15,718 rows) plus `batSignals-00000.tsv` (502,151 rows), with a **provisional** cutoff of `2026-10-16T04:02:00Z`, derived from a local download-page display. See `phase2-euan/COVERAGE_HANDOFF.md`; its source hashes differ from Peyton's earlier manifest.
- Jessica's reproduced local clean inputs used `notes-00001.tsv` (20,523 rows), `batSignals-00000.tsv` (478,892 rows), `noteStatusHistory-00000.tsv` (3,272,318 rows), and `ratings-00006.tsv` (27,045,028 rows), with a **provisional** `2026-10-02T23:59:59.999Z` Ratings/Status cutoff; these are selected shards, not a full release. The cleaned output files were too large for Git and remain local; code, checks and aggregates are in `phase2-jessica/`.
- Yoojin's previously validated independent source files had different observed row counts from Jessica's local run. Matching file basenames **does not establish matching content**.

**Jessica's committed observed-baseline results** (not fixed 7-day KPI): 20,523 Notes cohort; 15,675 matched Status rows; 808 notes with observed first non-NMR; median of observed completed events **6.352078 hours**; 6,121 valid matched ratings across 478 notes; observed Helpful share **0.431792**. These are descriptive of selected file subsets with their stated cutoff; missing ratings in the selected shard must not be interpreted as zero activity platform-wide. Aggregates: `phase2-jessica/results/`.

### 4.3 Reproduction and quality checks

- Peyton: `phase2-peyton/README.md`, `FINDINGS.md`, `evidence/manifest.json`, `evidence/quality_flags.csv`; cleaned outputs generated locally under `phase2-peyton/outputs/` and Git-ignored.
- Yoojin: `yoojin_phase 2/README.md` and `evidence/`; locally generated `status_clean.tsv.gz`, `ratings_clean.tsv.gz` and validation JSON, not committed as large files.
- Euan: `phase2-euan/COVERAGE_HANDOFF.md`, `coverage_analysis.py`, `run_demo.py`, and results folders.
- Jessica: `phase2-jessica/README.md`, `response_ratings_analysis.py`, `test_response_ratings.py`, `run_real_analysis.py`, six output CSV/JSON files. Nine local synthetic unit tests and four **output-internal** aggregate reconciliation checks have passed; these do **not** independently certify the raw-data calculations or parity between streaming and in-memory implementations.
- Before production-style use, check source hashes; unique Note and Status IDs; request/tweet matching; rating participant–note duplicate policy; negative/after-cutoff timestamps; unmatched joins; status eligibility; time maturity; numerator/denominator reconciliation; and source-shard coverage.

## 5. Architecture and technical design

Build independently testable layers with **explicit DataFrame contracts** and no UI-dependent global state:

1. **Source/config layer:** local paths or configurable filesystem mount, source manifest with shard/hash, verified cutoff and analysis policy; configuration validates before KPI computation.
2. **Cleaning/QC layer:** run Peyton's and Yoojin's supplied scripts; output normalized DataFrames or compressed tables and diagnostics. Preserve source values and exclusion counts.
3. **Analysis layer:** coverage service (`analyze_coverage`) and response/ratings service (Jessica's functions/streaming runner). Neither analysis service imports UI state or the other's internals.
4. **Aggregation/cache layer:** cache aggregate results by `(source fingerprint, cutoff, section filters, W, metric version)`; invalidate on any input/metric change. Prefer precomputed note-level aggregates and stream large Ratings rather than reading ~27M rows into application memory per interaction.
5. **Presentation layer (Phase 3):** a local **Streamlit** single-page dashboard is the recommended implementation choice; pandas is appropriate for small aggregates, with disk-backed Parquet/CSV (Parquet preferred when available) for cached filtered summaries. This UI/tool choice is an **integration recommendation**, not a claim that Julia/Kaitlyn already agreed on it. No external database is necessary for the selected-shard MVP; use explicit configs for later deployment.
6. **Export layer:** aggregate-only CSVs plus metadata (filters, units, W, UTC cutoff, source scope). Do not expose full raw tables through dashboard exports.

**Responsiveness:** filtering must work on cached small aggregates or indexed/preaggregated note-level datasets; costly streaming scans occur in a preprocessing step, not during each widget change. Precompute early-24h rating counts, W-specific response completion flags, classification/note-type tags, and daily trends for supported windows. Avoid silently replacing an expensive query with a statistically different calculation.

## 6. Interaction/error behavior

- At startup show section default cohorts with cutoff/source labeling; if cutoff is **unverified**, prominently warn and do **not** present fixed-window maturity rates as validated.
- On filter change, show **Updating** while retaining prior values as stale; on failure show an actionable error and Retry, not zero-filled fake results.
- Click coverage week to recalculate Coverage cards/table only; clear selection to restore all-week totals.
- Classification selection changes Response/Helpfulness only; chart-hover details do not change filters, and scatter selection doesn't alter KPI denominators.
- On zero eligible requests, zero eligible notes, no completed events or no valid ratings, display **N/A** with reason.
- Exports must exactly match visible filtered aggregates and embed filter values, units and cutoff/snapshot references.

## 7. Build order for Phase 3

| Order | Independently testable deliverable | Acceptance gate |
|---|---|---|
| 1 | Confirm canonical shard(s), cutoff, status/duplicate/maturity policy; produce versioned data manifest | No implicit mixed snapshot and no unknown cutoff for windowed results |
| 2 | Harmonize cleaners and compare QC/join reports | Reconciled source/exclusion counts and reproducible preprocessing |
| 3 | Adapt Euan coverage service to selected feed/date/W configs | Hand-calculated fixtures and weekly sums agree |
| 4 | Adapt Jessica response/ratings service to W-day maturity, 24h early ratings, selected cohorts, and streaming parity | Synthetic fixtures + subset/full scan reconciliation agree |
| 5 | Materialize normalized note-level and weekly/daily aggregates; caching | Section filter recomputes without loading raw Ratings again |
| 6 | Build single-page layout: header, independent section filters, KPI cards, charts, details, footer | Each chart has a matching defined metric, denominator and scope |
| 7 | Add interactions, deterministic scatter sampling, error/N/A/warning states and exports | Filter independence, export consistency and empty cases pass |
| 8 | Fresh-agent implementation walkthrough and end-to-end smoke test | No unresolved product/data assumptions needed to start Phase 3 |

## 8. Acceptance tests (implementation contracts)

| Fixture / interaction | Expected behavior |
|---|---|
| 10 eligible requests, 4 covered (one tweet has 3 notes) | 10 eligible, 4 covered, 40.0% coverage, 6 no observed note |
| Note created before eligibility or after W | Not counted as newly covered; exactly at eligibility or W boundary counts |
| Request has only 3 observed days, W=7 | Immature and excluded from denominator; reported separately |
| 5 mature notes: 3 first non-NMR at 2, 10, 30h; 1 first non-NMR after W; 1 none | 3 completed, 2 without recorded transition **within W**, completion 60.0%, median 10 hours |
| Classification changes from All to one class | Response/Helpfulness change; Coverage untouched |
| 7 Helpful, 1 Somewhat Helpful, 2 Not Helpful, plus 3 invalid/legacy levels | Valid N=10, Helpful 70.0%; 3 excluded levels shown |
| Early rating on note at creation+24h | Included; rating after 24h excluded from early scatter count |
| No requests, completed notes or valid ratings | Corresponding rate/median is N/A with reason |
| Select coverage week, export, then reset | Export matches selected totals; reset only Coverage |
| More than 2,000 completed scatter points | Reproducible, labeled ≤2,000 points; KPIs still use full cohort |
| Cutoff unverified; filters require W maturity | Configuration warning, no falsely validated fixed-window KPI |
| Status or Rating join has duplicate or unmatched keys | No join multiplication; exclusions and matching denominators reported |

**Verification ownership:** The Phase 2 contributors' recorded tests cover portions of this table, but **the full table has not been verified end-to-end**. The remaining cases are explicit Phase 3 implementation gates, not assumed passing tests.

## 9. Final Phase 2 handoff and known open decisions

**Repository structure:** `phase2-peyton/`, `yoojin_phase 2/`, `phase2-euan/`, `phase2-jessica/`, root `BUILD_SPEC.md`; large source and cleaned datasets remain out of Git, with reproducible script/config/manifest instructions.

**Required team decisions before treating this as a single coherent final source:**

1. **Canonical inputs:** choose and record exact Notes, Requests, Ratings, Status shards/snapshots and SHA-256 hashes. Otherwise disclose separate partial-shard demonstrations instead of calling them canonical.
2. **Verified UTC cutoff:** Euan and Jessica currently use different provisional cutoffs; establish the one to apply across a rebuilt comparison or label each independent cohort distinctly.
3. **Window policy:** approve W=7 default, 14/28 options, full observation/maturity denominators and whether status-unmatched Notes are excluded versus retained with a diagnostic cohort.
4. **Rating policy:** reconcile duplicate participant-note ratings and post-creation/event-time windows in both in-memory and streaming interfaces.
5. **Technical choice:** approve Streamlit + pandas + precomputed cached aggregates, or record the team's alternative.
6. **Fresh-agent test:** hand this repository plus the **final** spec to a fresh coding agent, log each question/guess and resolve consequential gaps **before submission**. No completed test is claimed here.

**Phase 2 submission check:** Commit the reconciled `BUILD_SPEC.md` to **main**, preserve cleaning/backend code and generated small aggregates, ensure all stated limitations are transparent, then follow **Gradescope's actual file/link instructions**. The assignment provides deliverables but does not in the materials reviewed specify whether Gradescope expects a Markdown upload, repository URL or archive. Do not submit an unverified format or claim the complete dataset is in the Git repository.

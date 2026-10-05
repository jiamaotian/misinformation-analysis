# Column-by-column cleaning proposal

## 1. Inspection results and scope

The proposal covers **all 98 columns across five datasets**. No raw files were modified, copied into the project, added to Git, or uploaded.

| Dataset | Inspection completed | Main findings |
|---|---|---|
| Note Requests / `batSignals` | **All 487,851 rows** | Unique `tweetId`; no malformed row widths. Standard-feed eligibility is `-1` in 459,254 rows. All `suggestions` values parse as JSON arrays. Five `sourceLinks` cells contain malformed URL prefixes. |
| Notes | **75,011 rows**: first 20,000 from `00000`, plus every row in `00001`–`00004` | Eight `tweetId = -1`; two missing classifications; both occur in collaborative notes. 2,745 summaries have surrounding whitespace. |
| Ratings | **180,000 rows**: first 20,000 from each of nine files | 14,201 version-1 ratings have blank `helpfulnessLevel`; version-2 sample ratings have populated levels. `ratedOnTweetId` and `suggestionId` contain `-1`. |
| Note Status History | **All 3,343,818 rows** | Unique `noteId`; no malformed row widths. **1,357 currently Helpful/Not Helpful notes lack first non-NMR timestamps**. Submodel statuses include `FIRM_REJECT` and `NEEDS_YOUR_HELP`. |
| User Enrollment | **All 1,497,640 rows** | Unique `participantId`; no malformed row widths. Group IDs use strings such as `13.0`. **547 rows disagree between the last-earn-out sentinel and earn-out count**. |

No duplicate candidate keys or exact duplicate rows were found in the inspected Notes/Ratings samples; this does **not** establish full-file uniqueness. These prefix samples are nonrandom and cannot support population percentages.

The extra status column is now explained: official documentation records `timestampMillisAbovePcrhThreshold` as added on September 18, 2026. Its negative timestamps encode meaningful state, so a blanket “negative number → missing” rule would lose information. [Official data documentation](https://raw.githubusercontent.com/twitter/communitynotes/main/documentation/under-the-hood/download-data.md)

## 2. Shared rules

These are proposed transformations for a future cleaned dataset, not changes to the source files.

The following requirements apply to every column rule and take precedence over any shorthand such as “map,” “null,” “collapse,” or “exclude” below:

1. **Explain every row exclusion.** Preserve source records. Before removing a row from a derived table or excluding it from a metric, document the rule, evidence, reason, affected record references, and count. State which output or metric is affected and how its denominator changes. This includes identical-duplicate removal and malformed-record handling. Keep malformed records traceable in a local exception log; never silently skip them.
2. **Document every unit or category change.** Record the source and target column, original and resulting type/unit/category, exact formula or mapping, rationale, and affected count. Preserve original values. This includes UTC datetime conversion, sentinel-to-null mappings, `0`/`1` to Boolean conversion, category whitespace trimming, and derived category labels. Do not merge or rename categories without an explicit documented mapping.
3. **Flag suspicious values before deciding their treatment.** First record the original value, source reference, validation rule, and why it is suspicious. Then document the chosen treatment and supporting evidence before applying it. A flag alone does not justify deletion, replacement, capping, or imputation. If evidence is insufficient, retain the original, leave any unusable derived value null with a reason, and keep the issue unresolved.
4. **Report after each major transformation.** Complete the change report described below before proceeding to the next major stage, even when the result is “no changes.” Reports must distinguish observed issues, actions taken, and unresolved flags.

| Rule | Proposed behavior |
|---|---|
| Reading | Stream ZIP members locally as UTF-8 TSV. Preserve literal quotes and validate column counts. Support large cells: one sampled `suggestions` value contains **160,321 characters**. Never silently skip malformed rows. |
| Provenance | Associate each record with source archive, member, and data-row number. Record every changed or invalid cell and its original value. |
| Missing values | Treat empty structured fields as null. Do not globally replace `0`, `1`, `-1`, `[]`, or literal text such as `"NA"`. |
| IDs | Store IDs as strings, never floating-point numbers. Positive decimal strings are expected for note/post/suggestion IDs. Preserve participant IDs exactly; flag unexpected format rather than changing case or padding. |
| Binary fields | Document the `0` → false and `1` → true mapping and affected counts. Blank remains null. Flag other values first; after recording the treatment reason, leave their derived Boolean value null and retain the original. Never fill missing with `0`. |
| Categories | Trim surrounding whitespace in structured categories. Preserve case and unknown nonblank categories, with a flag. Do not guess replacements. |
| Timestamps | Keep original integer values and add UTC datetime companions for valid timestamps. Use milliseconds except where specifically noted. Apply field-specific sentinel rules below. |
| Invalid cells | Preserve the record and original value. Flag the issue before choosing treatment. Document why a typed value must remain null and explain any metric-specific exclusion, including its affected count and denominator. |
| Duplicates | In a future full scan, flag duplicate groups first. Only after documenting exact equality, the retention rule, and affected counts, collapse identical source records in an analysis view, retaining all source references. Explain why each removed copy would otherwise double-count the same record. Flag conflicting records sharing a candidate key; do not arbitrarily keep the first or latest. |
| Extreme values | Flag suspicious times or counts; do not cap, replace, or discard them solely because they are unusual. |

For timestamps with unclear sentinel semantics, preserve the raw number and mark the datetime unavailable. This gives implementation a safe action without inventing meaning.

**Required report after each major transformation**

Major stages include parsing and typing, missing-value/sentinel handling, unit/category/text normalization, duplicate handling, and joins or metric-specific filtering. If a stage runs in chunks, accumulate its counts and report the whole stage before starting the next one.

| Report item | Required information |
|---|---|
| Transformation and reason | Stage name, dataset, columns, applied rule, and evidence supporting the action. |
| Before and after | Input/output row and column counts; changed cell and distinct affected-row counts; missing, invalid, and duplicate counts for affected fields. State the inspection scope and denominator. |
| Unit and category audit | Original and target units/types, timezone, formulas, and value mappings with counts. For example, record milliseconds since Unix epoch → UTC datetime with `unit="ms"`; never describe this as an unexplained date conversion. |
| Row accounting | Rows retained, duplicate copies removed from the analysis view, structural exceptions, and metric-specific exclusions, each with reasons and source references. Report unique excluded-row counts separately from overlapping reason counts. For joins, also explain unmatched rows and any row multiplication. |
| Suspicious-value decisions | Flags raised before treatment, action taken for each issue, supporting evidence, and remaining unresolved flags. Include illustrative before/after examples only when needed and keep record-level audit material local and outside Git. |
| Validation and user update | Reconciliation/check results and a concise user-facing summary of what changed, why, and what remains unresolved. Report zero changes explicitly when applicable. |

## 3. Rules for every column

Columns sharing the same rule are grouped below; each column is named explicitly.

**A. Note Requests — 7 columns**

| Column | Proposed cleaning rule |
|---|---|
| `tweetId` | Required positive decimal-string key. Missing/invalid IDs cannot participate in coverage joins. Check uniqueness across the full table. |
| `noteRequestFeedEligibleAtMillis` | Convert positive integer milliseconds to UTC. Map `-1` to no eligibility datetime and an explicit `ineligible` state. Blank or invalid values mean unknown, not ineligible. |
| `apiSmallFeedEligibleAtMillis` | Same eligibility rule, independently for the small feed. |
| `apiLargeFeedEligibleAtMillis` | Same eligibility rule, independently for the large feed. |
| `apiXlFeedEligibleAtMillis` | Same eligibility rule, independently for the extra-large feed. Do not require membership or timestamp ordering across feeds. |
| `sourceLinks` | Preserve original text. Locally, nonblank cells are predominantly comma-separated URLs, **not JSON arrays**. Split on commas and trim each token in a derived list; validate each as an HTTP(S) URL with a host. Preserve order and duplicates. Flag malformed tokens without repairing prefixes. Blank means no recorded links. |
| `suggestions` | Parse JSON arrays while retaining original text. Preserve `[]` as a known empty list, distinct from missing or invalid JSON. Validate each element as an object; preserve extra keys. Convert nested `suggestion_id` to a string without float conversion; preserve `suggestion` text; validate nonblank `source_link` separately. |

The full request scan found **387,602 suggestion objects**, all with integer `suggestion_id` and string `suggestion`/`source_link` values. Invalid URLs must not cause the containing request to disappear.

**B. Notes — 24 columns**

| Column(s) | Proposed cleaning rule |
|---|---|
| `noteId` | Required positive decimal-string key; check uniqueness across all five files. |
| `noteAuthorParticipantId` | Preserve as string. Sample values are 64-character uppercase hexadecimal identifiers; flag deviations without rewriting them. Missing author information does not invalidate an otherwise usable note. |
| `createdAtMillis` | Parse positive integer milliseconds to UTC as note creation time. Invalid time blocks time-based metrics, not retention of the note. |
| `tweetId` | Positive decimal string for joins. Map observed `-1` to unavailable post ID with a sentinel flag. Retain the note for note-level analysis; never join `-1` values together. |
| `classification` | Accept observed `MISINFORMED_OR_POTENTIALLY_MISLEADING` and `NOT_MISLEADING`. Preserve the two observed blanks as unknown; do not infer classification from text or reason flags. |
| `believable` | Nullable category: observed `BELIEVABLE_BY_MANY`, `BELIEVABLE_BY_FEW`. Preserve blanks and historical values. |
| `harmful` | Nullable category: observed `CONSIDERABLE_HARM`, `LITTLE_HARM`. Preserve blanks and historical values. |
| `validationDifficulty` | Nullable category: observed `EASY`, `CHALLENGING`. Preserve blanks and historical values. |
| `misleadingOther`, `misleadingFactualError`, `misleadingManipulatedMedia`, `misleadingOutdatedInformation`, `misleadingMissingImportantContext`, `misleadingUnverifiedClaimAsFact`, `misleadingSatire` | Apply the binary rule to each column. Preserve multiple simultaneous selections. Flag apparent disagreement with classification; do not overwrite either field. |
| `notMisleadingOther`, `notMisleadingFactuallyCorrect`, `notMisleadingOutdatedButNotWhenWritten`, `notMisleadingClearlySatire`, `notMisleadingPersonalOpinion` | Apply the binary rule to each column. All-zero rows are allowed; do not infer a classification from them. |
| `trustworthySources` | Apply the binary rule. Treat it as a recorded response, not independently verified source quality. |
| `summary` | Preserve original Unicode, punctuation, URLs, and internal spacing. Add a trimmed text companion; flag blank-after-trimming content. Do not lowercase, translate, remove URLs, or deduplicate notes by text. |
| `isMediaNote` | Apply the binary rule. |
| `isCollaborativeNote` | Apply the binary rule; retain for stratification. Do not assume all files have the same note-type distribution. |

The inspected smaller Notes files contain **55,011 collaborative notes**, while the first 20,000 rows of `notes-00000` contain none. Taking only the first file would miss this observed distinction.

**C. Ratings — 35 columns**

As you selected, **keep legacy and newer rating formats separate**.

| Column(s) | Proposed cleaning rule |
|---|---|
| `noteId` | Required positive decimal string; join to Notes/Status using this field. |
| `raterParticipantId` | Required string for identifying raters and checking the candidate key `(noteId, raterParticipantId)`. Flag unusual format; do not overwrite it. |
| `createdAtMillis` | Parse positive milliseconds to UTC as the rating timestamp. When a note matches, flag ratings earlier than note creation; retain originals and exclude invalid elapsed-time calculations. |
| `version` | Parse as nullable positive integer. Observed values are `1` and `2`; preserve and flag any additional version instead of mapping it to a known version. |
| `agree`, `disagree` | Apply the binary rule. Flag simultaneous `1` values. Allow both to be `0`; do not require them to sum to one. |
| `helpful`, `notHelpful` | Apply the binary rule. Preserve legacy responses; flag simultaneous `1` values. Do not use them to fill `helpfulnessLevel`. |
| `helpfulnessLevel` | Accept `HELPFUL`, `SOMEWHAT_HELPFUL`, `NOT_HELPFUL`. Keep blank legacy values null. For helpfulness distributions, report valid-level ratings and excluded/missing counts separately. |
| `helpfulOther`, `helpfulInformative`, `helpfulClear`, `helpfulEmpathetic`, `helpfulGoodSources`, `helpfulUniqueContext`, `helpfulAddressesClaim`, `helpfulImportantContext`, `helpfulUnbiasedLanguage` | Apply the binary rule individually. Retain all fields and multiple selections. Analyze historical fields within their applicable rating format; do not interpret every zero as a comparable response across eras. |
| `notHelpfulOther`, `notHelpfulIncorrect`, `notHelpfulSourcesMissingOrUnreliable`, `notHelpfulOpinionSpeculationOrBias`, `notHelpfulMissingKeyPoints`, `notHelpfulOutdated`, `notHelpfulHardToUnderstand`, `notHelpfulArgumentativeOrBiased`, `notHelpfulOffTopic`, `notHelpfulSpamHarassmentOrAbuse`, `notHelpfulIrrelevantSources`, `notHelpfulOpinionSpeculation`, `notHelpfulNoteNotNeeded` | Apply the binary rule individually. Do not collapse similarly named historical/current fields or force helpful and unhelpful reason groups to be mutually exclusive. |
| `ratedOnTweetId` | Positive decimal string; map `-1` to unavailable with a sentinel flag. Preserve separately from the note’s `tweetId`; do not overwrite discrepancies. |
| `ratingSourceBucketed` | Preserve observed `DEFAULT` and `POPULATION_SAMPLED`. Blank remains unknown, not `DEFAULT`. Preserve and flag additional categories. |
| `suggestion` | Preserve original text; add a trimmed companion. Blank means no recorded suggestion, not an invalid rating. |
| `suggestionId` | Positive decimal string; map `-1` to unavailable with a sentinel flag. Do not require an ID whenever suggestion text exists, or infer one from text. |

A rating and its note can legitimately refer to different posts for media notes. The schema also documents changes to older rating questions. [Official field definitions](https://raw.githubusercontent.com/twitter/communitynotes/main/documentation/under-the-hood/download-data.md)

**D. Note Status History — 24 columns**

For the rules below, the three **overall statuses** are `NEEDS_MORE_RATINGS`, `CURRENTLY_RATED_HELPFUL`, and `CURRENTLY_RATED_NOT_HELPFUL`.

| Column(s) | Proposed cleaning rule |
|---|---|
| `noteId` | Required positive decimal-string key. Full-scan uniqueness passed. |
| `noteAuthorParticipantId` | Preserve string; compare with matching Notes author. Flag disagreement without choosing one automatically. |
| `createdAtMillis` | Parse as note creation time in UTC; compare with matching Notes creation time and flag disagreement. |
| `timestampMillisOfFirstNonNMRStatus` | Positive milliseconds or null. Check against note creation and pair with `firstNonNMRStatus`. Do not fill from current-status or lock timestamps. |
| `firstNonNMRStatus` | Nullable Helpful/Not Helpful category. Keep missing as unknown history; do not automatically label the note “never resolved.” |
| `timestampMillisOfCurrentStatus` | Positive milliseconds to UTC. Keep distinct from the most recent status-change timestamp. |
| `currentStatus` | Validate against the three overall statuses. Preserve/flag any additional value; do not reconstruct from submodel outputs. |
| `timestampMillisOfLatestNonNMRStatus` | Positive milliseconds or null. Check pairing with `mostRecentNonNMRStatus`; flag values earlier than the first non-NMR timestamp. |
| `mostRecentNonNMRStatus` | Nullable Helpful/Not Helpful category. Do not overwrite with `currentStatus`. |
| `timestampMillisOfStatusLock` | Positive milliseconds or null; check pairing with `lockedStatus`. |
| `lockedStatus` | Nullable overall-status category. Do not force equality with current status. |
| `timestampMillisOfRetroLock` | Positive milliseconds or null. Preserve observed historical values; do not replace them with a single assumed date. |
| `currentCoreStatus`, `currentExpansionStatus`, `currentGroupStatus`, `currentMultiGroupStatus` | Nullable categories. Allow the observed overall statuses plus `FIRM_REJECT` and `NEEDS_YOUR_HELP`; preserve/flag future categories. Never map these extra submodel values into an overall status automatically. |
| `currentDecidedBy` | Preserve the full model/rule label, including version. Do not strip version information or merge labels. |
| `currentModelingGroup`, `currentModelingMultiGroup` | Nullable nonnegative integer group identifiers. Preserve `0` as a distinct placeholder if encountered. Do not enforce the outdated range 0–13; local groups extend to 33. |
| `timestampMillisOfMostRecentStatusChange` | Positive milliseconds to UTC; `-1` becomes no recorded change datetime with a separate sentinel flag. Do not infer that the current status is NMR. |
| `timestampMillisOfNmrDueToMinStableCrhTime` | Positive milliseconds to UTC; distinguish blank from `-1` in quality metadata. Keep both datetime-null; do not assign an unverified meaning to `-1`. |
| `timestampMinuteOfFinalScoringOutput` | Preserve as integer scoring metadata. **Do not parse as milliseconds** or use as a note-resolution event; no datetime conversion is needed for this project. |
| `timestampMillisOfFirstNmrDueToMinStableCrhTime` | Positive milliseconds to UTC; preserve blank versus `-1` separately. Never fill from the similarly named field above. |
| `timestampMillisAbovePcrhThreshold` | Preserve signed integer. Blank → no recorded threshold event; `-1` → cleared; positive → timestamp and above-threshold state; other negative → timestamp from absolute value and no-longer-above-threshold state. Zero/unparseable → flagged invalid. |

The PCRH interpretation follows the documented encoding. [Official PCRH definition](https://raw.githubusercontent.com/twitter/communitynotes/main/documentation/under-the-hood/download-data.md)

For the **1,357 resolved notes lacking first non-NMR times**, retain their current statuses and flag unavailable milestone history. Exclude them from completed time-to-first-non-NMR calculations, and report their count separately.

**E. User Enrollment — 8 columns**

| Column | Proposed cleaning rule |
|---|---|
| `participantId` | Required string key; preserve exactly. Full-scan uniqueness passed. |
| `enrollmentState` | Preserve the six observed categories: `newUser`, `earnedIn`, `earnedOutAcknowledged`, `atRisk`, `removed`, `apiEarnedIn`. Preserve/flag additional values. Do not rename values merely to match older documentation. |
| `successfulRatingNeededToEarnIn` | Nullable nonnegative integer. All full-scan values passed this numeric check. Do not impose a guessed maximum. |
| `timestampOfLastStateChange` | Positive milliseconds to UTC. Flag invalid values; do not derive from the last earn-out time. |
| `timestampOfLastEarnOut` | Preserve raw integer. `1` → null datetime plus “never earned out” indicator; positive valid epoch values → UTC datetime. Flag other values. |
| `modelingPopulation` | Preserve observed `CORE`, `EXPANSION`, `EXPANSION_PLUS`; preserve/flag additional categories. |
| `modelingGroup` | Parse exact integral representations such as `13.0` into nullable integers. Preserve zero; do not round nonintegral values or cap IDs at 13. |
| `numberOfTimesEarnedOut` | Nullable nonnegative integer. Preserve observed values, including the maximum of 27. Flag disagreement with the last-earn-out sentinel; do not change either field to force consistency. |

The `timestampOfLastEarnOut = 1` convention is explicitly documented. [Official enrollment definition](https://raw.githubusercontent.com/twitter/communitynotes/main/documentation/under-the-hood/download-data.md)

## 4. Cross-table checks and acceptance criteria

- **Preserve table grain.** Requests are post-level; Notes and Status are note-level; Ratings are rating-level; Enrollment is participant-level. Repeated `tweetId` in Notes and repeated `noteId` in Ratings are expected.
- **Keep unmatched records.** Missing joins receive a match-status flag. They do not prove absence of a note, rating, or participant. Status metadata can remain after note deletion. [Snapshot documentation](https://raw.githubusercontent.com/twitter/communitynotes/main/documentation/under-the-hood/download-data.md)
- **Retain notes created before eligibility.** They are not automatically erroneous; they simply do not meet the Vision’s “new note after eligibility” coverage event.
- **Avoid join multiplication.** Aggregate ratings by note before attaching note-level summaries; count distinct eligible posts for coverage.
- **Separate cleaning from analysis choices.** Preserve all four feeds and all dates. Do not select a feed, observation window, or cutoff during cleaning. Do not equate first non-NMR with first Helpful.
- **Test sentinel cases explicitly:** feed `-1`, unavailable ID `-1`, enrollment timestamp `1`, PCRH positive/negative/`-1`/blank, and minute-based scoring metadata.
- **Test information preservation:** long JSON cells, multilingual text, malformed URL prefixes, missing classification, all-zero reason fields, legacy ratings, new submodel categories, and conflicting duplicate keys.
- **Reconcile counts:** every input row must be accounted for as retained, an identical duplicate in the analysis view, or a flagged structural exception. No unexplained row loss.
- **Verify the audit trail:** every removal or metric exclusion has a reason and affected count; every unit/category conversion has an explicit mapping or formula; every suspicious-value treatment is preceded by a recorded flag and decision. Undocumented changes fail acceptance.
- **Verify stage reports:** each major transformation has a before/after report and user-facing summary, including unchanged stages, denominator changes, and unresolved issues. Do not proceed to the next major stage until its report is complete.
- **Before applying globally:** complete Notes/Ratings profiling across all partitions. Additional values must be retained and flagged under these rules, not silently dropped.

This proposal adds typed fields, derived companions, provenance, and quality flags only to future local analytical outputs. It makes no source-file changes and requires no public API changes.

# Community Notes Coverage: Individual Cleaning Report

Jiamao Tian | DSO 576 Module 6 | Coverage scope only. Initial submission commit: 811b5887373768cfeef625da856b8bbe2e52af14. This is individual evidence for the group reconciliation, not a claim that the team has reconciled its results.

# Result and scope

Observed coverage in the supplied files: 15,188 / 28,929 = 52.5010%. Requests with no qualifying note observed: 13,741. These are file-based observations, not population estimates. Expected Notes files missing: None of the five expected filenames is missing; aligned snapshot completeness remains unverified.

# 1. Vision and analysis question - Done

A Community Notes Product Manager must decide where additional note-writing or rating effort should be directed to improve coverage and reduce response time while maintaining broad agreement. This individual assignment prepares the coverage branch only. Among posts eligible for the main note-request feed by the cutoff, how many have at least one observed note created on or after eligibility and by the cutoff? Written notes are not necessarily Helpful or publicly displayed.

# 2. Define one row - Done

Raw requests: one post and its feed eligibility fields, with tweetId expected unique. Raw Notes: one note, with noteId expected unique; multiple notes per tweetId are valid. Final coverage_cleaned.csv: exactly one eligible post per tweetId. All final analysis columns are included in the sample.

# 3. Preserve the source - Done

Original files are read only from data/raw. source_manifest.json records exact filenames, byte counts and SHA-256 hashes. Source supplied by the student: X Community Notes public data, https://communitynotes.x.com/guide/en/under-the-hood/download-data . The original files were downloaded on 2026-09-28. The preparation date is 2026-10-04. Reproduction requires the same source files, not a new live download; current public downloads may differ.

# 4. Columns and types - Done

All raw fields are read as strings. tweetId and noteId remain strings, avoiding floating-point rounding. Selected timestamps require positive integer millisecond syntax and are converted to numeric/UTC derived fields. Invalid Notes IDs after exact deduplication: 2 (including negative/sentinel IDs, which cannot identify a valid post). Invalid Notes timestamps after exact deduplication: 0. Missing/invalid main-feed eligibility excluding -1: 0. Invalid request IDs: 0. Failed required fields are excluded from the analysis, not repaired by guessing. See column_audit.csv for every original column.

# 5. Standardize text - Done

The audited ID and selected timestamp fields have zero outer-whitespace values in the submitted snapshot, so trimming changes no values in these fields. Example: original tweetId 1253353708961902596 remains 1253353708961902596 in the cleaned sample. Identifiers are strings; meaningful prose, capitalization and leading zeros are preserved. No case-normalization or spelling correction is needed for the analytical fields. See column_audit.csv. The -1 eligibility interpretation is a missing/eligibility rule, not an example of text standardization.

# 6. Duplicates - Done

Raw Notes rows: 3,125,451; fully identical repeated rows removed: 20,523; distinct remaining conflicting noteIds: 0, involving 0 rows. Conflicting IDs are excluded altogether. Exact duplicate request rows: 0; repeated request IDs after exact deduplication: 0. Conflicting request IDs stop the run for review. Repeated tweetIds in Notes are retained.

# 7. Missing data - Done

Original blank counts appear in column_audit.csv; missing counts for every output column appear in output_missing.csv. Optional text blanks are retained in the preserved source and do not exclude posts. 449,959 main-feed -1 values mean not eligible; they are not filled with dates. The final cohort contains no missing tweetId or eligibility_ms. first_qualifying_note_ms remains blank for 13,741 posts because no qualifying note was observed. The derived count is zero for those posts; this does not establish absence on X.

# 8. Suspicious values - Done

Fixed analytical cutoff: 2026-09-12T23:59:59Z. This is a deliberate common calculation boundary near the end of the request data, not a verified export timestamp. Eligibility after cutoff: 4; usable notes after cutoff: 44,924. Those are outside the analysis window, not inherently erroneous. Pre-eligibility notes attached to cohort posts: 14,104; retain them in the observed-note count but exclude them from qualifying-note counts. Recent requests (<7 days follow-up): 2,835; flag them rather than delete them.

# 9. Verify merges - Done

Join key: tweetId. Requests-to-notes is one-to-many; aggregate to post level before using the result. Input usable notes: 3,104,926, covering 2,108,019 unique posts. Eligible request rows: 28,929; output rows: 28,929. Requests matching any usable note: 19,675; matching none: 9,254. Note tweetIds outside the eligible request cohort: 2,088,344. Final tweetId uniqueness and unchanged denominator are asserted.

# 10. Reconcile changes - Done

Notes reconciliation: 3,125,451 raw = 20,523 exact duplicates removed + 2 invalid/conflicting rows excluded + 3,104,926 usable notes. Requests: 478,892 raw -> 28,929 eligible post-level output. Request exclusions are determined by exact duplicates, invalid keys, -1/missing/invalid eligibility and cutoff. Counters for these reasons are provided separately and may overlap if a future file has several problems on the same row. Coverage count 15,188 plus no qualifying note observed 13,741 equals denominator 28,929.

# 11. Check calculations - Done

Numerator counts distinct eligible posts with qualifying_note_count > 0, not total notes. Denominator is all 28,929 valid eligible posts by cutoff, including unmatched posts. There are 27,245 qualifying notes. The >=7-day follow-up subset contains 26,094 posts and 13,606 observed covered posts; this is a sensitivity description, not a corrected estimate. No classification grouping is used, because unanswered posts have no note classification. Missing first-note times are not converted to zero time.

# 12. Five original-to-cleaned record checks - Done

Five independent raw-to-output checks from the original run pass. However, the cases were selected after cleaning; the original run does not establish that case-specific expectations were written beforehand. validation/expected_records.json now fixes expectations and individual reasons for a follow-up verification. This is a disclosed later validation, not a reconstruction of the original chronology. Follow-up verification status: PASS. The follow-up reopens all original source files, verifies their SHA-256 hashes, computes the five outcomes independently, and compares them with fixed expectations and the saved cleaned output. Student review is still required.

# 13. Reproducibility - Done

Run python reproduce.py from the project root. It launches cleaning.py in two fresh Python processes, hashes all deterministic evidence/output files, and asserts equality. Recorded result: {'status': 'PASS', 'fresh_process_runs': 2, 'output_hashes_match': {'column_audit.csv': True, 'coverage_cleaned.csv': True, 'coverage_sample.csv': True, 'five_record_checks.json': True, 'full_data_checks.json': True, 'output_missing.csv': True, 'proposed_rules.json': True, 'source_manifest.json': True}, 'python': '3.9.6', 'pandas': '2.2.3', 'reportlab': '4.4.9'}. The notebook can also be restarted and run all; it calls the same reproducibility workflow.

# 14. Remaining limitations - Done

All five expected Notes files were included in the local run. Even all five filenames do not prove complete, contemporaneous exports or include deleted notes. Unmatched records are observational, not verified coverage gaps. Recent requests have less follow-up. Main-feed eligibility is distinct from other feed eligibility, and -1 in the main feed is not overridden by an API feed. This assignment measures note writing only, not helpfulness, public display, misinformation truth, broad agreement, or response time. Source retrieval date is documented, but redistribution terms and snapshot alignment remain unverified. Group reconciliation and GitHub upload remain student/team actions.

# Cleaning decision log

R1: Read all original TSV columns as strings; preserve IDs and leading zeros. Trim outer whitespace only in IDs and timestamp fields. Preserve prose and classification labels. Reason: Avoid ID precision loss and unintended changes to text. Verification: Check column_audit.csv for source types and whitespace; compare original and sample identifiers for the five cases. IDs are stored as strings.
R2: Remove only fully identical source rows across Notes files. Exclude all remaining records with conflicting repeated noteId; never select an arbitrary winner. Reason: Repeated tweetId across different notes is a valid one-to-many relationship. Verification: Check exact duplicates (20,523) separately from conflicting note IDs (0); record 5 shows two identical source rows yielding one qualifying note.
R3: Interpret -1 in eligibility fields as not eligible. Keep missing optional fields. Invalid/missing IDs and invalid timestamps cannot enter the analysis cohort. Reason: Missing eligibility does not mean eligible; missing prose does not invalidate a key. Verification: Check blank counts and invalid-field counters. Main-feed sentinel exclusions: 449,959; output_missing.csv records remaining missing first-note times.
R4: Use noteRequestFeedEligibleAtMillis only. Include unique eligible posts on or before the fixed UTC cutoff. A note counts only when eligibility <= creation <= cutoff. Reason: Match the Phase 1 coverage definition; notes before eligibility do not count. Verification: Compare original eligibility and creation timestamps with the cutoff in the five checks; specifically exclude the pre-eligibility note in record 2.
R5: LEFT JOIN eligible requests to usable notes on tweetId, then GROUP BY the unique request key to obtain one row per post. Keep unmatched requests. Reason: Prevent multiple notes from multiplying the coverage denominator. Verification: Assert output tweetId uniqueness and 28,929 eligible rows = 28,929 output rows; the LEFT JOIN preserves unmatched posts.
R6: Unmatched means no qualifying note observed in supplied files, not proof of no note on X. Preserve suspicious values in raw sources and report exclusions. Reason: File completeness and snapshot alignment are not established by a successful join. Verification: Report unmatched posts (9,254) separately from posts with no qualifying note (13,741); retain snapshot and interpretation limitations.

# Rule revision log

Before implementation, the uploaded original files were audited. The initial idea to concatenate Notes was refined to remove fully identical cross-file duplicates, because the original audit found them. The simplistic any-note match was replaced with the Phase 1 temporal definition (eligibility <= creation <= cutoff). The initial test used four uploaded Notes files. The subsequent local run included all five expected Notes files. During submission review, the R5 description was corrected to match the existing LEFT JOIN followed by GROUP BY implementation. This was a documentation correction; cleaning.py and the analytic results were not changed. Case-specific fixed expectations were added for a disclosed follow-up check after the initial run.

# Sample selection

Up to 50 actual cleaned post rows: first include the five difficult/representative cases, then select remaining rows without replacement using random_state=576. All columns of the final analysis dataset are included. This is an inspection sample, not a representative basis for the reported full-input checks. No raw note text, author participant IDs, source links or suggestion prose is included in the final analysis schema.

# Codex verification response

Suggestion checked: remove fully identical cross-file Notes rows, while retaining distinct notes for the same post. Verification: an independent csv.DictReader pass rereads the raw TSVs and hashes all fields for each selected row, instead of relying on the cleaning SQL table. For tweetId 1253353708961902596, noteId 2082124719525130520 appears in notes-00001.tsv at record 7 and notes-00002.tsv at record 4, with creation time 1785252350875 after eligibility 1785245256671. The raw-row comparison identifies the second occurrence as an exact duplicate. Expected qualifying count is 1, and the saved cleaned count is 1. As a countercheck, tweetId 1701209223000916034 has five distinct qualifying notes and retains count 5. Conclusion: exact-row removal avoids double counting without discarding valid distinct notes. Evidence: five_record_checks.json and the optional follow-up verification. These checks are code-assisted; the report does not claim an unperformed manual inspection by the student.

# Submission and team reconciliation

The assignment has two submission descriptions: a ZIP with report/code/README/data evidence, and a final GitHub/group instruction specifying an individual branch with .py, notebook and sample plus one reconciled group checklist PDF. This package supports both. Use this report as the individual evidence; the group should reconcile differences and submit its own final PDF. Do not label this report as a completed team reconciliation. The module handout did not provide separate decision-log or Codex-response templates beyond the checklist; explicit sections are supplied here.

# Record check 1: multiple qualifying notes

tweetId: 1701209223000916034; original eligibility ms: 1788045189412.
Original note: noteId 2094516064558391710; createdAtMillis 1788206518674; source notes-00000.tsv, record 659969; exact duplicate False.
Original note: noteId 2094862136073945305; createdAtMillis 1788289028558; source notes-00000.tsv, record 2054309; exact duplicate False.
Original note: noteId 2093901142178636199; createdAtMillis 1788059909755; source notes-00000.tsv, record 2308675; exact duplicate False.
Original note: noteId 2094490763425927284; createdAtMillis 1788200486414; source notes-00000.tsv, record 2760061; exact duplicate False.
Original note: noteId 2094469045630259357; createdAtMillis 1788195308488; source notes-00000.tsv, record 2809781; exact duplicate False.
Fixed follow-up expected count: 5; saved actual count: 5. Expected first qualifying ms: 1788059909755; actual: 1788059909755. Counts and earliest times match: True.
Reason: Five distinct note IDs have creation times at or after eligibility and before the cutoff. Retain all five notes, count this post once in the coverage numerator, and use the earliest qualifying creation time.

# Record check 2: pre-eligibility note excluded

tweetId: 1396932077422092289; original eligibility ms: 1786581785791.
Original note: noteId 2087552260653944944; createdAtMillis 1786546218442; source notes-00000.tsv, record 1880122; exact duplicate False.
Fixed follow-up expected count: 0; saved actual count: 0. Expected first qualifying ms: None; actual: None. Counts and earliest times match: True.
Reason: The note was created at 1786546218442, before eligibility at 1786581785791. Keep the post in the denominator but exclude this note from qualifying coverage; the first qualifying time remains missing.

# Record check 3: no note match

tweetId: 1149982212609196032; original eligibility ms: 1782755886709.
Original notes: no matching note found in the supplied files.
Fixed follow-up expected count: 0; saved actual count: 0. Expected first qualifying ms: None; actual: None. Counts and earliest times match: True.
Reason: No note for this post was found in the supplied Notes files. Retain the eligible post with zero qualifying notes and a missing first-note time; this is an observation about the files, not proof of no note on X.

# Record check 4: recent eligibility retained

tweetId: 1414372054380339202; original eligibility ms: 1789245501655.
Original notes: no matching note found in the supplied files.
Fixed follow-up expected count: 0; saved actual count: 0. Expected first qualifying ms: None; actual: None. Counts and earliest times match: True.
Reason: The post became eligible shortly before the cutoff. Retain it with a recent-under-seven-days flag. No note was observed, so its qualifying count is zero and first-note time is missing.

# Record check 5: qualifying note observed

tweetId: 1253353708961902596; original eligibility ms: 1785245256671.
Original note: noteId 2082124719525130520; createdAtMillis 1785252350875; source notes-00001.tsv, record 7; exact duplicate False.
Original note: noteId 2082124719525130520; createdAtMillis 1785252350875; source notes-00002.tsv, record 4; exact duplicate True.
Fixed follow-up expected count: 1; saved actual count: 1. Expected first qualifying ms: 1785252350875; actual: 1785252350875. Counts and earliest times match: True.
Reason: The same fully identical note row occurs in notes-00001.tsv and notes-00002.tsv. Count the note once after exact-row deduplication. Its creation time follows eligibility and precedes the cutoff.

# GitHub submission information

Branch: jessica-module6-cleaning
Branch URL: https://github.com/jiamaotian/misinformation-analysis/tree/jessica-module6-cleaning
Code commit ID: 811b5887373768cfeef625da856b8bbe2e52af14
The commit identifies the submitted code/evidence version. This report may be regenerated in a subsequent documentation commit. A branch URL alone does not establish a successful push.

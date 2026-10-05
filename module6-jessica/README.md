# Community Notes Coverage Cleaning — Jiamao Tian

This is the individual DSO 576 Module 6 coverage cleaning workflow. It does not perform the response-time analysis. Read UPDATE_INSTRUCTIONS_CN.md for the final verification and submission steps.

## Run

The submitted full-data run used Python 3.9.6, pandas 2.2.3 and reportlab 4.4.9. From this folder:

```bash
python -m pip install -r requirements.txt
python reproduce.py
```

On macOS, use `python3` if `python` is unavailable. With an existing uv course environment: `uv run --with pandas==2.2.3 --with reportlab==4.4.9 python reproduce.py` (or install requirements into your active course environment). The ordinary pip command above is the primary tested workflow.

`reproduce.py` runs the complete pipeline twice in separate Python processes and compares SHA-256 hashes. It then regenerates REPORT.md and REPORT.pdf from your actual results. Large input processing can take several minutes and needs temporary disk space; progress is printed at completion of each run. Keep the terminal open.

## Inputs and exact snapshot

Put the original files anywhere below `data/raw/`:

- Exactly one `batSignals-00000.tsv` (a suffix such as `(1)` is accepted).
- `notes-00000.tsv`, `notes-00001.tsv`, `notes-00002.tsv`, `notes-00003.tsv`, `notes-00004.tsv`.

Do not put a second copy of the request file there. The code discovers Notes recursively, reads 50,000 rows at a time, audits all columns, and uses a temporary SQLite database to avoid holding the full Notes dataset in memory. A missing shard is reported explicitly; the code still supports testing on the available files. Conflicting request IDs stop the run for review. Conflicting note IDs are counted and excluded, with this limitation reported.

The initial authoring test used four uploaded Notes files. The subsequent student-local run used all five Notes files and the request file. The supplied evidence describes that full local run: 3,125,451 raw Notes rows and 28,929 eligible posts. Raw TSVs are intentionally excluded from this update package; preserve your existing data/raw directory.

Source identified in the project: https://communitynotes.x.com/guide/en/under-the-hood/download-data . The original files were downloaded on 2026-09-28. Exact filenames, bytes and SHA-256 values are recorded in `evidence/source_manifest.json`. Preparation date 2026-10-04 is not a download date. To reproduce the exact historical results, the instructor needs these exact files from the student; newer downloads can yield different results. Redistribution terms were not verified; raw prose/participant data are excluded from the code package.

## Definition and rules

Metric: distinct main-feed eligible posts with an observed note created at or after eligibility and by 2026-09-12 23:59:59 UTC, divided by all valid distinct main-feed eligible posts by that cutoff. This fixed analytical boundary is near the end of the request data and is not asserted to be an export timestamp. All expected filenames still do not prove aligned snapshots.

Read `CLEANING_RULES.md` before applying the code. Every raw column is initially read as a string. Exact row duplicates are removed across files; repeated tweetIds with different noteIds are valid. -1 eligibility means not eligible. Optional missing text is preserved in source, not imputed. Required invalid keys/timestamps do not enter the analysis. Notes before eligibility or after cutoff are outside the qualifying window. Unmatched posts stay in the denominator. All output fields describe the supplied-files observation, not a verified absence of a note on X.

## Outputs

- `REPORT.pdf` and editable `REPORT.md`: 14 checklist responses, decisions, five record checks, Codex verification and limitations.
- `data/processed/coverage_cleaned.csv`: one eligible post per row.
- `data/sample/coverage_sample.csv`: <=50 actual rows with every final analysis column, including selected difficult cases.
- `evidence/column_audit.csv`: all source columns, string types, blank and whitespace counts.
- `evidence/full_data_checks.json`: full-input row reconciliation, duplicates, invalid timestamps, joins, denominator and numerator.
- `evidence/five_record_checks.json`: original source rows for five selected posts and independent expected/actual comparisons.
- `evidence/source_manifest.json`, `proposed_rules.json`, `reproducibility.json`.

CSV identifier columns must be read with `dtype={'tweetId':'string'}`. Spreadsheet programs may otherwise round long IDs. The final CSV contains only analytic fields; omitted note text/classification is outside the post-level coverage question. Raw files preserve all original columns.

## Notebook

Open `notebooks/cleaning.ipynb` in VS Code. Select your Python environment, click Restart Kernel, then Run All. The notebook starts the same fresh-process workflow and displays checks and samples. Do not run the notebook and terminal pipeline simultaneously in the same folder. The .py script contains the actual reusable cleaning implementation; the notebook explains and inspects it.

## GitHub and submission

The assignment specifically asks for individual `.py`, notebook and sample on your own project branch, followed by team reconciliation and one group checklist PDF. It also describes a ZIP submission. This package supports both, but the group still must reconcile results before its final PDF submission. Do not upload `data/raw`, the complete processed dataset, `.venv`, or temporary databases to GitHub. `.gitignore` covers those directories. Copy code, notebook, README, rules, report, evidence and sample into your personal branch of the group repository. The group PDF is not automatically completed by this individual workflow.

AI assistance: Codex helped implement and check this workflow, as permitted by the assignment. The student must understand the rules, inspect the five record checks, and take responsibility for the submitted results.


## Submission review update

Run `python3 verify_submission.py` after reading `validation/expected_records.json`. It verifies original file hashes, independently rescans the originals for five fixed cases, compares the saved full cleaned output and sample, writes `validation/followup_verification.json`, and regenerates the report. This is a later verification of already-known cases, not evidence of expectations predating the initial run. The cleaning algorithm is unchanged. No full pipeline rerun is required for these documentation corrections. If you rerun the full pipeline, run this verifier afterwards as well.

After commit and push, put the code commit ID into SUBMISSION_METADATA.json and run `python3 make_report.py`. Refresh the last notebook cell and save. The report may cite the preceding code commit to avoid a self-referential commit ID.

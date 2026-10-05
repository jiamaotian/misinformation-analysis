# misinformation-analysis

Misinformation on Social Media - Module 6 data cleaning submission.

## Branch

- Branch name: `clean-poying`
- Remote: `https://github.com/jiamaotian/misinformation-analysis.git`
- Branch URL: `https://github.com/jiamaotian/misinformation-analysis/tree/clean-poying`
- Submission commit ID: TBD after the final submission commit is created.

## Data Source

This project cleans the public X/Twitter Community Notes download files. The raw ZIP files are kept outside Git and are not included in this repository.

- Source documentation referenced by the cleaning code: `https://raw.githubusercontent.com/twitter/communitynotes/main/documentation/under-the-hood/download-data.md`
- Local raw data path used for validation: `/Users/bobo/dso576/project/raw/communitynotes/data`
- Raw ZIP files in the completed full run: 17
- Raw local file timestamp range: `2026-10-02T22:57:14.561223+00:00` to `2026-10-02T23:03:44.514467+00:00`
- Full cleaning run timestamp: `2026-10-03T05:16:25.665994+00:00`
- Actual download date: 2026-09-15, as reported by the student.

The run manifest stores SHA-256 hashes for every raw ZIP. Raw ZIPs, full cleaned Parquet files, and full audit outputs remain local-only under Git-ignored `data/`.

## Repository Contents

- `scripts/clean_communitynotes.py`: streaming cleaning pipeline.
- `scripts/validate_communitynotes.py`: full-output validation, duplicate checks, joins, summaries, and catalog generation.
- `requirements-cleaning.txt`: runtime dependencies used by the cleaning pipeline.
- `docs/CLEANING.md`: detailed setup, execution, output, and validation guide.
- `tests/`: unit tests for sentinel values, timestamps, nested JSON, duplicates, and failure behavior.
- `plan.md`: cleaning plan and rule rationale.
- `submission/`: small submit-ready evidence, sample data, and report draft.

## Install

```sh
uv venv .venv --python python3
uv pip install --python .venv/bin/python -r requirements-cleaning.txt
```

Dependencies used in the verified run:

- Python 3.13.2
- duckdb 1.5.6
- pyarrow 25.0.1
- pytz 2026.4

## Run

Set the raw and output paths for your machine:

```sh
RAW_DIR=/path/to/communitynotes/data
OUT_DIR=data/cleaning_run
```

Run tests:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Run the full cleaner:

```sh
.venv/bin/python scripts/clean_communitynotes.py \
  --raw-dir "$RAW_DIR" \
  --output-dir "$OUT_DIR"
```

For lower disk pressure, use sequential transformation:

```sh
.venv/bin/python scripts/clean_communitynotes.py \
  --raw-dir "$RAW_DIR" \
  --output-dir "$OUT_DIR" \
  --workers 1
```

Do not reuse an output directory if the normalization rules changed. Use a new output directory for reproducibility checks.

## Expected Outputs

The full run writes local-only outputs under the selected output directory:

- `manifest.json`: raw ZIP source paths, file sizes, modification times, and SHA-256 hashes.
- `cleaned/<dataset>/*.parquet`: cleaned typed tables with provenance and companion columns.
- `audit/*-flags.parquet`: suspicious values and conservative decisions.
- `audit/*-duplicate-exclusions.parquet`: exact duplicate exclusions from analysis views, if any.
- `audit/*-join-flags.parquet`: cross-table match status without dropping rows.
- `summaries/ratings_by_note.parquet`: rating counts by note.
- `reports/*.json`: profile, transform, duplicate, join, and final validation reports.
- `catalog.sql`: DuckDB views over local Parquet files.
- `CLEANING_REPORT.md`: human-readable run summary.

## Submission Materials

The `submission/` folder contains only small files intended for Git:

- `submission/cleaned_sample/`: five cleaned sample rows, one per table, covering the manual difficult cases.
- `submission/sample_manifest.json`: sample selection method and source rows.
- `submission/evidence/`: copied validation, manual-check, and reproducibility summaries from local validation outputs.
- `submission/cleaning_decision_log.md`: concise rule/decision/check log.
- `submission/module6_homework_report_draft.md`: draft report with the 14-item checklist and evidence locations.

The sample contains 5 total rows, below the 50-row limit. It does not include raw ZIPs, full cleaned datasets, or full row-level audit outputs.

## Known Limitations

- The cleaner does not choose a final analysis cohort, feed, observation window, cutoff, coverage denominator, or response-time denominator.
- Ambiguous sentinel meanings are retained and flagged instead of guessed.
- Suspicious timestamp unit issues are not auto-corrected.
- Invalid URLs are flagged and retained; prefixes are not repaired.
- Cross-table non-matches are preserved and flagged, not interpreted as proof that no matching contribution exists.
- Some SQL-derived outputs are content-reproducible but not row-order stable unless an explicit final `ORDER BY` is added.

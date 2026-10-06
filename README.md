# Community Notes data cleaning

This project creates reproducible, analysis-ready data for an **Observed
Coverage and Response-Time Monitor**. It uses the public X Community Notes data
for Note Requests, Notes, Ratings, and Note Status History.

**Project vision:** A Community Notes Product Manager must decide where
additional note-writing or rating effort should be directed to improve coverage
and reduce response time while maintaining broad agreement.

**Business question:** Where do lower observed coverage, longer response times,
or lower observed rating outcomes suggest that additional note-writing or
rating effort may warrant investigation?

The monitor uses four co-primary descriptive metrics:

1. observed coverage;
2. response time;
3. rating activity; and
4. observed helpfulness.

Comparisons must use an explicitly selected period and data-supported cohort,
with denominators, missingness, unmatched records, and sample sizes reported.
No one metric is sufficient to redirect contributor effort. The results do not
establish causal effects or automatically recommend where contributors should
work.

## Data version and provenance

- Source: [X Community Notes data download](https://x.com/i/communitynotes/download-data).
- Download date: **2026-10-04**.
- Snapshot description shown at download: the data include contributions made
  prior to **9:03 PM on October 1, 2026**. The source timezone was not recorded,
  so no timezone is inferred here.
- Local source directory: `Project_data_1004/`.
- Source-file modification metadata and row/schema information are captured by
  each run in `source_manifest.csv`.
- Raw TSV files are never overwritten and are excluded from Git.

The download date and contribution cutoff identify the project snapshot. They
are not the same date: the files were downloaded after the stated contribution
cutoff.

To inspect an individual TSV in VS Code/Python:

```python
import pandas as pd

data = pd.read_csv("path/to/file.tsv", sep="\t")
```

The production cleaning workflow uses DuckDB for bounded-memory processing of
the full dataset, especially the 236-million-row Ratings table.

## Repository structure

```text
README.md                         Project overview and run instructions
plan.md                           Inspected data and approved cleaning plan
DATA_DICTIONARY.md                Output grains, fields, and metric definitions
validation_report.md              Full validation and reproducibility report
MODULE6_CHECKLIST.md              Fourteen-item assignment checklist
HW6.md                            Completed assignment responses for items 4–14
CLEANING_DECISION_LOG.md          Decisions, reasons, checks, and affected rows
RECORD_CHECKS.md                  Five Original → Expected → Actual checks
data_cleaning.ipynb               Notebook walkthrough of inspection, cleaning, and validation
requirements.txt                  Pinned Python dependencies
scripts/clean_community_notes.py  Reproducible cleaning and validation pipeline
scripts/clean_data.py             Compatibility entry point
scripts/compare_cleaned_outputs.py Independent-run logical comparison
Project_data_1004/                Local raw data; TSV files are not committed
cleaned_v2/                       Generated outputs; only small reports committed
```

## Run the workflow

For a notebook-based walkthrough of source sampling, data-quality profiles,
cleaned outputs, and validation checks, see [data_cleaning.ipynb](data_cleaning.ipynb).
The notebook uses the existing `cleaned_v2/` outputs by default; its full-scale
pipeline rerun is opt-in because the Ratings source contains 236 million rows.

From this repository on Windows PowerShell:

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe scripts\clean_community_notes.py `
  --input-dir Project_data_1004 --output-dir cleaned_v2 `
  --threads 4 --memory-limit 4GB
```

The output directory must be absent or empty. The pipeline refuses to overwrite
a nonempty run directory.

To reproduce into a separate directory and compare logical output:

```powershell
..\.venv\Scripts\python.exe scripts\clean_community_notes.py `
  --input-dir Project_data_1004 --output-dir cleaned_repro `
  --threads 4 --memory-limit 4GB
..\.venv\Scripts\python.exe scripts\compare_cleaned_outputs.py `
  cleaned_v2 cleaned_repro `
  --output cleaned_repro\reproducibility_comparison.csv
```

## Dependencies

- Python 3
- `duckdb==1.5.6`
- `pandas==3.0.6`

## Expected outputs

The canonical `cleaned_v2/` run contains:

- row-preserving `note_request_clean.parquet`, `notes_clean.parquet`,
  `ratings_clean.parquet`, and `note_status_clean.parquet`;
- grain-safe `ratings_by_note.parquet`, `notes_analysis.parquet`, and
  `coverage_analysis.parquet`;
- `community_notes_v2.duckdb` views;
- validation CSVs for source inventory, missingness, categories, timestamps,
  duplicates, joins, suspicious values, transformations, metrics, and human
  review; and
- `validation_summary.json`.

Generated Parquet/DuckDB outputs require roughly 17 GiB and are excluded from
Git. The small canonical validation CSVs and `validation_summary.json` should be
committed as assignment evidence.

## Limitations

- The source tables cover different date ranges, so unmatched keys do not prove
  that a corresponding real-world record does not exist.
- The data lack sufficient post-level topic, language, exposure, and engagement
  metadata for many subgroup comparisons.
- The data are observational; associations are not causal effects.
- The supplied Status file is one row per note, not a complete event history.
- Four eligibility fields produce different coverage denominators. The four
  co-primary metrics are approved, but the eligibility feed and analysis window
  must still be selected and reported for each comparison.
- Semantics remain unresolved for some Status `-1` values, 20,009 other-negative
  PCRH timestamps, and legacy version-1 helpfulness fields.
- These files must not be presented as representative of the full Community
  Notes population.

## GitHub submission metadata

- Branch name: `Julia-Chen`
- Branch URL: https://github.com/jiamaotian/misinformation-analysis/tree/Julia-Chen
- Current pre-submission HEAD: `6c1e55be04028209f1c22aed1e91fe39c1cb7584`
- Final assignment commit ID: `8310948`

After committing the final materials, run `git rev-parse HEAD` and replace the
pending line with that exact commit ID. Do not label the current pre-submission
HEAD as the final assignment commit.

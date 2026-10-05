# Local Community Notes cleaning

This pipeline implements `plan.md`. It reads the external ZIP archives without extracting or editing them. All cleaned tables, record-level audit material, reports, and temporary spill files live under the Git-ignored `data/` directory. No upload or Git staging is performed.

## Run

```sh
uv venv .venv --python python3
uv pip install --python .venv/bin/python -r requirements-cleaning.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/clean_communitynotes.py \
  --raw-dir /Users/bobo/dso576/project/raw/communitynotes/data \
  --output-dir data/cleaning_run
```

The default command runs full profiling, transformation, and validation. `--stage profile`, `--stage transform`, and `--stage validate` allow separate checkpoints; transformation requires the completed full profile. `--limit-per-file N` is for testing only and must use a separate output directory. Sampled outputs are explicitly marked and must not be used as population results.

Completed partitions have JSON reports and can be resumed. Incomplete writes use `.partial` filenames and are not read as final Parquet. A changed normalization contract requires a fresh output directory. A failure stops processing and records `reports/failure.json`; it never silently skips malformed input. Source size and modification time are checked on resume; SHA-256 hashes are calculated before the first run and verified again at final validation.

## Outputs

- `cleaned/<dataset>/*.parquet`: all source rows, typed fields, UTC/text/nested-data companions, provenance, sparse original tokens, and change masks.
- `audit/*-flags.parquet`: suspicious values flagged before conversion, original value, source location, validation rule, and conservative treatment. Counts are events and may overlap within one row.
- `audit/*-duplicate-records.parquet`: duplicate candidate keys, when any exist, with reconstructed original records. Conflicting values are retained.
- `audit/*-duplicate-exclusions.parquet`: only exact original-record copies excluded from the analysis view, with reasons and source references. Base cleaned tables keep every row.
- `audit/*-join-flags.parquet`: match status and cross-table inconsistencies without changing input row counts. Missing matches are not treated as proof that a contribution never existed.
- `summaries/ratings_by_note.parquet`: rating counts by note, keeping legacy/version-2 counts separate. This is an explicit aggregation, not row deletion. All input ratings reconcile to the sum of counts.
- `reports/`: full profiles, exact SQL rules, value mapping counts, before/after transformation reports, duplicate and join checks, and final source-integrity results.
- `CLEANING_REPORT.md`: human-readable summary of the completed run.
- `catalog.sql`: local views over Parquet; no data are embedded in the SQL.

## Audit behavior

Every source row has `_source_file`, `_source_member`, and `_source_row` (one-based data row, excluding the header). `_raw_values` stores original strings only when they cannot be reconstructed exactly from typed fields. Binary conversion is reversible as false → `0`, true → `1`; a missing typed value defaults back to the original empty token unless overridden in `_raw_values`. For example, `modelingGroup='13.0'` retains its exact original token in the sparse map, while `tweetId='-1'` becomes a null usable ID with its original sentinel retained there.

The SQL views `<dataset>_source_values` reconstruct original tokens. `<dataset>_cell_changes` decodes `_changed_mask` (bit positions follow the original header order) into a per-cell audit, generated on demand to avoid storing billions of repetitive binary-conversion records. Type changes count as changes even if their printed numeric value is the same. Companion-column additions are reported separately with nonnull counts. Source text remains verbatim; `summary_trimmed`, `suggestion_trimmed`, `sourceLinks_list`, and `suggestions_parsed` are additions.

Sentinel handling is field-specific. Original timestamp integers are retained, while `_utc` companions are nullable UTC timestamps. `timestampMinuteOfFinalScoringOutput` remains integer minute metadata. PCRH negative timestamps retain their meaning through a UTC companion and `pcrh_state`; they are not converted blindly to missing values. Unexpected category labels and extreme values are retained and flagged. No missing legacy `helpfulnessLevel` is imputed.

All flags precede treatment. An unresolved anomaly remains flagged even when its typed companion is null. Known encoding conversions use `reports/rules.json` and partition mapping counts. No feed, analysis window, or data cutoff is selected. Invalid timing flags do not cause a whole source record to disappear. No response-time or coverage denominator is computed by this cleaning job.

## Read the results

```python
from pathlib import Path
import duckdb

run = Path('data/cleaning_run').resolve()
con = duckdb.connect()
con.execute("SET memory_limit='3GB'; SET threads=2")
con.execute((run / 'catalog.sql').read_text())
print(con.sql('SELECT noteId, summary_trimmed FROM notes_analysis LIMIT 5'))
print(con.sql('SELECT * FROM notes_cell_changes LIMIT 10'))
```

The base views retain every cleaned row. `*_analysis` views exclude only copies documented in the exact-duplicate manifests. Use source references to join anomaly flags; avoid joining all ratings directly to post-level rows. Status and enrollment are snapshots, not complete event histories.

## Validation and resource limits

Tests cover sentinel meaning, exact large IDs, UTC units, legacy ratings, unknown categories, contradictory values, long nested JSON, literal quotes, malformed-row failure, exact original-token reconstruction, and duplicate conflicts. Runtime checks reconcile full-file row counts, preserve join cardinality, verify aggregated rating totals, sample original-token reconstruction at each batch boundary, and rehash every source ZIP. Batch-boundary reconstruction is a sample check, not a full roundtrip of all rows.

The process streams 16 MiB TSV batches into Zstandard-compressed Parquet. By default, two independent partition workers run transformations, each with one DuckDB thread and a 2 GB managed-memory limit; use `--workers 1` for sequential execution. Profiling and validation use 3 GB of managed memory. DuckDB temporary spill is capped at 8 GB per connection; Python/Arrow use additional batch memory. Processing stops when free disk space falls below 3 GiB at a checkpoint. Large ratings partitions are checked separately for duplicate keys, followed by a cross-partition check, to avoid a single enormous key table.

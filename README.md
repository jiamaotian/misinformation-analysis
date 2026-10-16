# misinformation-analysis
Misinformation on Social Media

## Peyton Tom — Module 6

| Information | Details |
|---|---|
| Student | Peyton Tom |
| Course | DSO 576 |
| Assignment | Module 6 — Project Data Cleaning |
| Project | Misinformation on Social Media — Community Notes |
| Individual branch | `peyton-tom` |
| Branch link | [Peyton's branch](https://github.com/jiamaotian/misinformation-analysis/tree/peyton-tom) |
| Notebook | `peyton-tom.ipynb` |
| Cleaning script | `clean_peyton.py` |
| Submitted commit ID | Pending — the assignment files have not been committed yet |


Start with `peyton-tom.ipynb`. It follows the class style: load in chunks, inspect every column, propose rules, flag concerns, review, and then prepare data with change reports. The same cleaning code is also in `clean_peyton.py`, organized into VS Code `# %%` sections. Choose the notebook for step-by-step explanation or the script for a terminal run; both produce the same output files.

### File organization

| File or folder | Purpose |
|---|---|
| `phase1_data_exploration.ipynb` | Original team exploration; unchanged |
| `peyton-tom.ipynb` | Individual explanation, cleaning, checks, and dashboard plan |
| `clean_peyton.py` | Runnable version of the notebook's cleaning code |
| `requirements-peyton.txt` | Dependencies for both workflows |
| `outputs/peyton-inspection/` | Current inspection and optional prepared tables; ignored by Git |
| `archive/peyton-status-demo/` | Superseded synthetic example; not part of the active workflow |

The homework requests both a cleaning `.py` and a notebook `.ipynb`. The class handout's `dashboard.py` is a separate app, to build after the plan and required note/status data are ready. It is not the cleaning script.

### Data and run instructions

Source: [Community Notes public data](https://communitynotes.x.com/guide/en/under-the-hood/download-data), local `~/Downloads/ratings-00007.tsv`. The revised default inspects **every row and every column**, with no one-week selection. The exact input hash is saved; the download date and snapshot cutoff still need confirmation.

Use Python 3.11 or newer. From `misinformation-analysis`, run:

```bash
python -m pip install -r requirements-peyton.txt
python clean_peyton.py
```

Or select the same Python environment and run `peyton-tom.ipynb` in order. Both workflows contain the same code. `PREPARE_DATA = True` after review: preserve all source values and rows, and add UTC dates and invalid-date flags. The full-file CSV is several GB. Keep settings synchronized between files.

Current outputs in ignored `outputs/peyton-inspection/`:

- `column_rules_and_evidence.csv`: one proposed rule per column, missingness, whitespace, and observed examples.
- `category_counts.csv`: observed category counts; any vocabulary limit is disclosed in the manifest.
- `flag_counts.csv` and `flagged_sample.csv`: full-file flag counts and up to 50 review records. Flags do not trigger removal.
- `inspection_manifest.json`: source hash, schema, row count, observed date range, and limitations.
- With preparation enabled: `ratings_prepared.csv`, `prepared_sample.csv`, and `transformation_report.csv`.

Preparation preserves all original columns, category labels, IDs, and rows. It adds `rating_date_utc` (a UTC representation of the original milliseconds) and `invalid_rating_date`; invalid values stay in the table. Each major step reports counts and original-value preservation. The inspection reports within-chunk flags; `verify_peyton.py duplicates` separately audits exact rows, note/rater pairs, note IDs, and rater IDs across the entire file. No rows are removed.

The previous one-week outputs under `outputs/peyton-ratings/` remain historical results, not outputs of the revised workflow. The earlier synthetic example is archived separately.

The response-time dashboard plan remains in the notebook: completed-time median, unresolved count, and median waiting time together. Full Note Status History data and a verified cutoff are still needed. Ratings alone cannot calculate these metrics.

See `CHECKLIST-peyton.md` for statuses and evidence. Five AI-assisted expectations are saved before preparation in `evidence/peyton/record_expectations.json`. `reproduce_peyton.py` runs the script and then every notebook cell in a fresh kernel, comparing output hashes. Document the source version and review the evidence before preparing your PDF. No files have been committed or pushed automatically.

### Work in small steps, as in the handout

Use focused prompts that name a file, task, limit, and check. For example: “Review the date-conversion cell in `peyton-tom.ipynb`. Preserve `raw` and all selected-week rows. Check that daily grouped counts equal the cleaned row count.” Review the inspection output before changing a field that may already be correct.

The team notebooks and project documents remain unchanged. The old synthetic status-history script and its sample outputs have been moved into `archive/peyton-status-demo/` to distinguish them from the current real Ratings workflow.

### Verified data-quality findings

The full-file missingness audit examined **26,896,815 rows and all 35 source columns**. Only `suggestion` was empty: 26,880,490 missing entries plus 9 whitespace-only entries (99.9393%). The other 34 columns had zero missing or whitespace-only entries. Empty suggestion text is not a reason to discard a rating. Sentinel values such as `-1` are not counted as empty strings and need separate interpretation.

The earlier cleaned table covered the declared February 9–15 week: **919,045 rating records on 14,829 distinct notes**. Full-file missingness evidence must not be described as a full-file duplicate or cleaning audit.

The saved Phase 1 status schema contains creation time and first non-NMR time in the same table. That supports a basic time-to-first-non-NMR analysis once `data/noteStatusHistory-00000.tsv` and its observation cutoff are available. First non-NMR may be Helpful or Not Helpful; it does not establish time to first Helpful. The original notebook saves previews and references the TSV, but does not embed the full data.

The revised 35-column inspection covers 26,896,815 rows. All reported category counts reconcile. ID format/sentinel interpretation and the snapshot cutoff remain unresolved. Final preparation and verification results are recorded in `CHECKLIST-peyton.md`.

### Optional extended reproducibility check

Use Python 3.11+ and the pinned dependencies in `requirements-peyton.txt`:

```bash
python -m pip install -r requirements-peyton.txt
python reproduce_peyton.py
```

The reproducibility command runs the script, starts a fresh notebook kernel, executes every cell (including duplicate and record checks), saves the executed notebook, and compares all inspection/preparation CSV and JSON hashes between runs. It can take tens of minutes and needs space for a multi-GB prepared CSV and temporary duplicate-audit data.

`verify_peyton.py expectations` is initial setup only: it refuses to overwrite existing expectations. Keep those expectations unchanged when checking actual output. `verify_peyton.py duplicates` and `verify_peyton.py verify` can also run separately. The five cases include a blank suggestion, a post-ID sentinel, whitespace-only text, nonempty contributor text, and a participant ID beginning with zero. These are AI-assisted checks, not a claim of manual student verification.

The full raw/prepared files stay in ignored local folders. Small audit reports and record-check evidence are in `evidence/peyton/`; review these files when assembling the submission.

### Current verification status

Both full-file preparation passes completed. The extended notebook verification was stopped during its repeat duplicate audit to limit runtime; a complete saved Run All and final all-output hash comparison are not claimed. See `CHECKLIST-peyton.md` for the final statuses. For just the five-record comparison, run `python verify_peyton.py records`; this avoids another full inspection or duplicate audit.

# Peyton — Phase 2: Notes and Note Request

This workflow is separate from the Module 6 Ratings work. The agreed scope is every row in `notes-00001.tsv` and `batSignals-00000.tsv`. Ratings and Status History are not inputs.

## Start here

Open `peyton_notes_requests.ipynb` and select the existing project `.venv` kernel. Run the cells in order. The notebook imports the accompanying cleaning script so both entry points use the same rules. Inputs default to `data/raw/` inside this workflow folder. The user confirmed `notes-00001.tsv` in place of the originally mentioned `notes-00002.tsv`. Desktop ZIP archives were extracted here without modifying them.

For a quick first run, set `PREVIEW_ROWS = 1000`. Preview outputs are isolated in `outputs/preview/`; relationship results for a preview are incomplete. Set `PREVIEW_ROWS = None` for final full-file cleaning.

From the project folder, the equivalent terminal command is:

```bash
.venv/bin/python phase2-peyton/clean_notes_requests.py
```

Dependencies are in `requirements.txt` (also available in the existing project environment). The workflow loads both files into memory and performs a readback verification; available RAM must accommodate them. It overwrites its own output reports on rerun, never source data.

## Cleaning decisions

- Keep IDs and all original fields as strings. Preserve text, whitespace, original timestamps, and literal labels. Empty and whitespace-only fields are counted explicitly; they are not filled with invented values.
- Remove only identical rows across all original fields. Report the number removed. Conflicting repeated note IDs or request tweet IDs remain flagged for review.
- Repeated tweet IDs in Notes are legitimate candidates for multiple notes per tweet; they are not a deletion rule.
- Add UTC dates from millisecond timestamps. Flag missing, malformed, unrepresentable, and nonpositive values separately. Nonpositive source values remain preserved; their derived UTC dates are left missing, and their semantics need confirmation. Nonblank binary indicator values outside 0/1 are flagged.
- Check dates against a cutoff only when the team provides a verified cutoff with a timezone. Do not substitute today's date or the largest observed timestamp.
- Compare positive decimal tweet IDs using a per-tweet count table. Report both, notes-only, and requests-only membership. Preserve unmatched rows. No raw-table join or assumption about eligibility timestamp order is made.
- The eligibility fields describe eligibility events; do not automatically label them the time someone requested a note.

Schema reference: https://communitynotes.x.com/guide/en/under-the-hood/download-data . The team's Phase 1 notebook supplies the expected columns; this workflow validates required columns against the actual inputs at runtime. Additional source columns are retained and included in missingness profiles.

## Outputs and review

`outputs/notes_clean.csv` and `outputs/note_requests_clean.csv` are the cleaned deliverables. Read them with `dtype='string', keep_default_na=False` to preserve IDs and blanks. CSV itself does not store types.

`cleaning_report.csv` reconciles input, output, and duplicate-removal counts. `column_profile.csv` reports before/after blank counts and types. `quality_flags.csv` summarizes concerns. `tweet_relationships.csv` and `relationship_summary.csv` describe key overlap. Each flagged sample contains at most 100 records; use the full output flags for comprehensive review. `manifest.json` records scope, source hashes, cutoff, software version, limitations, and successful checks.

Before submitting:

1. Run the full agreed files, not only the preview.
2. Review missing identifiers, key conflicts, and timestamp flags. Any additional deletion or correction requires a documented reason supported by the data.
3. Record the actual download/snapshot information and cutoff if available; otherwise disclose that they are unknown.
4. Save the executed notebook, script, cleaned datasets, and reports according to the team's submission arrangements. Large CSVs are ignored by Git locally; share them through the team's agreed storage.
5. Explain what changed and why using the actual counts. Do not present synthetic test results as dataset findings.

## Current status

The source files are available in `data/raw/`. See `FINDINGS.md` for completed-run results. The accompanying test uses small synthetic fixtures solely to verify cleaning behavior.

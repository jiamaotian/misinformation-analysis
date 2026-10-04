# Community Notes data cleaning — Yoojin Hwang

## GitHub submission
Branch: `YoojinHwnag`
Branch URL: https://github.com/jiamaotian/misinformation-analysis/tree/YoojinHwnag
Submitted commit ID: fb02f33

This folder is prepared for submission; the final commit ID must be added to both this README and the PDF after upload. Confirm instructor repository access.

## Source and scope
X Community Notes Public Data: https://communitynotes.x.com/guide/en/under-the-hood/download-data
Downloaded October 2, 2026.
Original files: notes-00002.tsv, ratings-00006.tsv, noteStatusHistory-00000.tsv, batSignals-00000.tsv.
Keep the original TSV files unchanged in ~/Downloads, or adjust the notebook paths. Large original TSV files are not included in this submission folder.

The checks cover each supplied file, not every partition of the entire public-data release. Coverage is limited to the supplied Notes file. The basic `ratings` DataFrame is a 1,000-row sample; the combined section 7 scan verifies the full 27,038,662-row Ratings file once.

## Environment and run instructions
The analysis was run in Python 3.14.7 with pandas. Install the dependencies in requirements.txt in the selected environment, for example:

```sh
python -m pip install -r requirements.txt
```

The version ranges specify compatible requirements, not an exact lock of the original environment. pandas 3 is required by the notebook's string dtype selection. sqlite3, tempfile, pathlib, csv, and argparse are Python standard-library modules.

Open data_cleaning_organized.ipynb in VS Code/Jupyter, select that Python environment, restart the kernel, and run all cells. This repeats the full Ratings scan once and may take several minutes; temporary disk space is required for its key database. Notebook outputs are stored inline.

To recreate only the submission sample and record checks (no Ratings scan):

```sh
python prepare_submission.py
```

Optional source/output overrides:

```sh
python prepare_submission.py --notes /path/to/notes-00002.tsv --output-dir /path/to/output
```

## Expected files and results
- notes_cleaned_sample.csv: 50 Notes rows, all 24 original columns; source values and selected-row order preserved. No imputation or deletion is applied.
- Module_6_Homework_submission.pdf: checklist, decision log, record checks, and Codex verification explanation.

The sample includes all six tweetId=-1 rows (one also has a missing classification), the three specified normal verification IDs, and the first remaining rows until 50 are selected. It is not random or representative. Empty CSV fields preserve missing source information and are not zeros.

Full analysis: key duplicates 0; Ratings 27,038,662; HELPFUL 16,820,314 (62.21%). Response-time count 552; median 6.49916625 hours. Coverage counts (covered/eligible): 550/28,597, 556/28,964, 2,092/168,583, 3,119/487,506. Verification cutoff: October 2, 2026, 23:59:59.999 UTC.

## Reproducibility and Codex check
The saved main notebook has sequential execution counts 1–31 and no stored errors. The sample script was executed twice; the sample CSV and printed record checks were identical. The five record checks and cleaning decision log are included in the PDF.

Codex first suggested counting duplicate rows within each chunk. I checked that method and found it could miss duplicates across chunks. The final combined scan uses a disk-backed unique key over noteId and raterParticipantId. It found zero duplicate pairs and zero missing keys, so identical full rows are also ruled out. No duplicate rows were removed.

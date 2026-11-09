# Community Notes Explorer

An interactive dashboard for Community Notes product managers reviewing observed note coverage,
status progression, and rating activity in supplied X Community Notes data. Use it to identify
periods and note classifications worth further investigation. It does not estimate the causal effect
of additional writing/rating effort or establish broad agreement or readiness to display a note.

## Run the app

Use Python 3.12. From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run main.py
```

Open http://localhost:8501. The app reads the prepared tables in `outputs/dashboard/`.
**Do not run preparation just to launch the app.** Existing prepared files include additional ratings
imports that the original preparation command alone does not reproduce.

## What users can do

- Coverage: select a feed, supported request eligibility dates, and a 7/14/28-day window.
  Use **Focus week** to update the cards, table, and export while retaining the full overview chart.
- Response: select classifications, supported note creation dates, and a window. Compare first
  Helpful, first Not Helpful, and no recorded transition outcomes. The median measures hours to
  either first status, among completed events only.
- Review groups: compare counts and percentages without transitions, median first-day ratings
  among those notes, and counts/percentages with no observed first-day ratings.
- Ratings: compare helpfulness within the same observation window. An expandable scatter shows
  first-day activity versus completed response time; it is exploratory, not evidence of causation.
- Reset each section independently and download filtered aggregates with scope metadata.

Each record needs its full selected window before the cutoff. First-day activity always means
24 hours. No eligible records yields N/A; an eligible cohort with no observed events can yield 0%.
The sections have independent date filters. Only supported dates appear in their selectors; the
endpoints of a supported range do not guarantee full dataset coverage between them.

## Data scope and existing timestamp

Existing shared provisional cutoff: **October 2, 2026, 23:59:59.999 UTC**.
It is recorded in `dashboard_policy.json` and the prepared validation report. Calculations and
exports retain the provisional designation. This update does not confirm missing source metadata.

Current local prepared data:

- 15,430 notes, all marked **collaborative and non-media**.
- 499,888 request rows (feed eligibility and maturity exclusions apply).
- 107,712 matched ratings across 5,370 notes, before selected-cohort/window filtering.
- Status records match 10,638 notes; 4,792 have no matching status history.

Coverage is **observed coverage in the supplied Notes subset**, not all notes on X. Absence from
this subset is not proof a post received no Community Note. Unmatched or unusable status histories
are excluded from response calculations, not labeled unresolved. Helpful and Not Helpful first
statuses are reported separately; neither the combined completion rate nor rating helpfulness is a
measure of contributor agreement. Notes without a recorded transition may have later events.

The supplied rating overlap includes February 4–10 and additional dates from July 17 onward.
Latest selectable note dates are September 25, September 18, and September 4 for 7/14/28 days,
respectively, subject to matched status/rating coverage. Rating-file omissions can look like low
activity. Scatter plots sample at most 2,000 completed notes with a fixed seed; other aggregates
use the full selected cohort. First-day ratings can occur after the status transition.

## Validation and tests

`outputs/dashboard/validation.json` records original cleaned-file checks, source hashes, join gaps,
and additional raw-ratings imports. Additional imports apply ID/time checks, remove identical rows,
and exclude conflicting participant/note pairs. These checks do not certify snapshot completeness.

```bash
python -m pip install pytest
python -m pytest test_dashboard.py test_window_analysis.py test_add_dashboard_ratings.py
```

## Rebuild data (optional, requires local source files)

Back up `outputs/dashboard/` first. `prepare_dashboard.py` replaces the prepared tables.
It requires Peyton's cleaned notes/requests in `phase2-peyton/outputs/`, Yoojin's cleaned
ratings/status files in `yoojin_phase 2/`, and the original cleaning reports under its `evidence/`.
Then run the additional imports to reproduce the current ratings:

```bash
python prepare_dashboard.py
python add_dashboard_ratings.py /path/to/ratings-00008.zip
python add_dashboard_ratings.py /path/to/ratings-00006.zip
```

The checked `ratings-00001.zip` added no matches and is unnecessary for the current rating totals.
`ratings-00002.zip` was checked only and also had no matching IDs. Reusing a different snapshot
with the same filename may produce different results; compare hashes in the validation report.
Retain original archives locally; they are not needed by the running app. Each import keeps a
backup of its preceding ratings table and report under `outputs/dashboard/before_rating_import/`.

## Deployment and submission

Repository: https://github.com/jiamaotian/misinformation-analysis

Select branch `main`, entry point `main.py`, and Python 3.12 on Streamlit Community Cloud.
The deployment needs the four prepared files: `notes.parquet`, `ratings.parquet`, `requests.parquet`,
and `validation.json` under `outputs/dashboard/`. This package includes the expanded ratings and current interface. After deployment, verify the
hosted results against the bundled data.

Live app: [Community Notes Explorer](https://misinformation-analysis-6f5zzljdq2yngdkuzbc7hv.streamlit.app/)

 Demo video: [View the group walkthrough](https://drive.google.com/file/d/1VJbC9qQY6Ov4QrYARLvkxoithlB2j9eB/view?usp=sharing)
Before submitting, test the deployed app without login and with the laptop server stopped. Check
filters, reset, exports, and an empty selection. Confirm the README counts match the deployed data.
The demo should explain the user decision, units, interactions, difficult case, and one limitation.
Public showcase preference: **Decide later.**


Raw archive sharing/import options contributed by the team are documented in [RAW_DATA_IMPORT.md](RAW_DATA_IMPORT.md). These inventory/import commands do not clean or rebuild dashboard data.

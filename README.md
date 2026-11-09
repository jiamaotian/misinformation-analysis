# Community Notes Explorer

- **Live app:** [Community Notes Explorer](https://misinformation-analysis-6f5zzljdq2yngdkuzbc7hv.streamlit.app/)
- **Demo video:** [View the group walkthrough](https://drive.google.com/file/d/1VJbC9qQY6Ov4QrYARLvkxoithlB2j9eB/view?usp=sharing)
- **GitHub repository:** [misinformation-analysis](https://github.com/jiamaotian/misinformation-analysis)

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

## Data scope and analysis cutoff

**Configured analysis cutoff: October 2, 2026 at 23:59:59.999 UTC. This cutoff is provisional, not a verified dataset snapshot or download date.**

`dashboard_policy.json` records this choice and `cutoff_verified: false`. Its evidence text says
Peyton designated the shared provisional cutoff on November 2, 2026. The prepared
`outputs/dashboard/validation.json` carries the same values; the running app reads its cutoff
from that validation file. Editing the policy alone does not update prepared results.
Original download dates and completeness through the cutoff remain unverified. Using one cutoff
does not establish that the source shards came from one reconciled snapshot.

The app currently computes exploratory windowed results under this provisional cutoff and labels
exports `cutoff_verified=False`. It does not suppress those results until verification. This differs
from the original specifications' proposed unverified-cutoff suppression behavior.

### Prepared data

The counts below were checked directly against the prepared Parquet files on November 8, 2026.
Those three files and `validation.json` match the files in GitHub `main` at commit `acdb32c`.
This comparison verifies the repository package, not which revision the live host is serving.

| Prepared data | Scope before date/window/classification filtering |
|---|---|
| Notes | 15,430 distinct note IDs, all marked collaborative and non-media |
| Requests | 499,888 distinct request tweet IDs; positive eligibility and maturity depend on the selected feed |
| Ratings | 107,712 rows matched to 5,370 of the supplied notes |
| Status joins | 10,638 supplied notes have a matching status record; 4,792 do not |

The initial preparation scanned 3,343,818 cleaned status rows and 27,038,662 cleaned rating rows.
Only 3,499 of those initial rating rows matched the Notes subset. Importing `ratings-00008.zip`
added 104,210 rows; importing `ratings-00006.zip` added 3 net rows after removing 3,358 duplicate
rows. These produce the current 107,712-row prepared ratings table. The validation report's
`datasets.ratings` describes the initial scan, not the final expanded ratings total.

Stored note creation timestamps range from **February 4 through October 14, 2026**. There are
**1,367 stored notes after the configured cutoff**; storing them does not make them eligible for
windowed analysis. Prepared rating timestamps range from **February 4 through October 2, 2026**,
with no prepared ratings after the cutoff. These are observed timestamp bounds, not proof of
continuous or complete observation between them.

### Dates available in the app

Coverage dates refer to **request feed eligibility**, not rating activity. Positive, parseable
eligibility timestamps have the following stored bounds, before maturity filtering:

| Feed | Earliest UTC eligibility date | Latest stored UTC eligibility date |
|---|---|---|
| Standard | November 5, 2025 | October 15, 2026 |
| Small | November 3, 2025 | October 15, 2026 |
| Large | October 29, 2025 | October 15, 2026 |
| XL | February 11, 2026 | October 15, 2026 |

For all four feeds, the latest selectable eligibility date is **September 25, 2026** for 7 days,
**September 18, 2026** for 14 days, and **September 4, 2026** for 28 days. The calculation requires
the exact eligibility timestamp plus the full window to fall at or before the cutoff. Dates without
supported records do not appear as slider endpoints.

Response dates refer to **note creation**. With the current files, selectable dates are
**February 4–6 and February 8–10, 2026**, plus the following continuous date ranges:

| Observation window | Additional selectable note-creation dates, UTC |
|---|---|
| 7 days | July 17–September 25, 2026 |
| 14 days | July 17–September 18, 2026 |
| 28 days | July 17–September 4, 2026 |

The Response selector derives these dates from mature notes with usable matched status history
and at least one row in the supplied matched-ratings table. This does not require that rating to
fall within the selected window. The subsequent calculation applies the rating time rules.
All eligible notes inside the selected start/end interval can enter the denominator, including
notes without ratings and notes on intermediate dates that are not selectable endpoints.
Date options use all classifications; selecting a classification can still yield an empty result.

Both sections default to supported dates within the final 28 calendar dates ending on their latest
supported date. The UI shows inclusive start/end dates and converts the end to the next midnight
for a half-open calculation interval. All dates are UTC; weekly coverage bins start Monday.

### Interpretation and limitations

Coverage measures new qualifying notes in the **supplied Notes subset**, not all Community Notes
on X. A request counts once if at least one matching note appears from eligibility through the
inclusive window end. An absent note in these files does not prove no note exists elsewhere.

Response excludes unmatched or unusable status histories rather than labeling them unresolved.
The first non-NMR transition can be Helpful or Not Helpful. The median uses only transitions
completed within the window. A later transition counts as no transition within that window.
First outcomes do not establish current status or whether X displayed a note.

Helpfulness shares use valid Helpful, Somewhat Helpful and Not Helpful ratings on the eligible
Response cohort, from note creation through the inclusive window end. Missing/legacy levels are
excluded and counted. Individual rating opinions do not establish contributor agreement or official
note status. First-day counts always use the first 24 hours, including the boundary, and can include
ratings after the first status transition.

Rating-file omissions can look like low activity. The scatter uses up to 2,000 completed notes
with a fixed random seed; aggregate calculations use the full selected eligible cohort. The app
hides the scatter when there are no completions or all completed notes have zero observed first-day
ratings. Results describe supplied historical data and cannot establish causal effects.

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
Retain original archives locally; they are not needed by the running app. Each import overwrites the backup in
`outputs/dashboard/before_rating_import/` with its preceding ratings table and report; this folder
is not a versioned archive of every import.

## Deployment and submission

Select branch `main`, entry point `main.py`, and Python 3.12 on Streamlit Community Cloud.
The deployment needs the four prepared files: `notes.parquet`, `ratings.parquet`, `requests.parquet`,
and `validation.json` under `outputs/dashboard/`. These prepared files and the reviewed windowed
app code match GitHub `main` at commit `acdb32c`. Confirm the deployed revision and compare its
results with the repository package before submission; a repository comparison alone does not
verify the live deployment or anonymous access.

Public showcase preference: **Decide later.**

Raw archive sharing/import options are documented in [RAW_DATA_IMPORT.md](RAW_DATA_IMPORT.md)
on the main branch. Those inventory/import commands do not clean or rebuild dashboard data.

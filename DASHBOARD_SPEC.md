# Dashboard Specification

Community Notes Dashboard — Coverage & Response Time

This is Member 2's proposed dashboard design. The 7-day observation window, default feed and first non-NMR endpoint require team confirmation. Numbers in the mockup are illustrative, not actual results.

## 1. Page Layout

Use one scrollable page with two independent analysis sections; no tabs are needed for the MVP.

| Position | Content |
|---|---|
| Header | Dashboard title, purpose, data snapshot date and UTC cutoff |
| Coverage | Local filters → three KPI cards → weekly coverage chart and weekly counts table |
| Response Time & Ratings | Local filters → four KPI cards → completion-by-classification chart and rating-activity scatter plot |
| Rating Helpfulness | Helpful / Somewhat Helpful / Not Helpful distribution, counts and valid-rating denominator |
| Review Candidates | Short descriptions of observed coverage gaps and waiting-note patterns; no causal recommendations |
| Footer | Data quality and definitions; export filtered aggregate results |

Coverage helps identify periods with lower observed note coverage. Response Time helps identify note groups with longer waits and examine their rating activity.

## 2. Metrics and Charts

Proposed observation window: 7 days. Include only requests or notes with a full observation window before the verified data cutoff. Show excluded and incomplete-observation counts separately. Use UTC throughout.

| Metric / chart | Question answered | Data source | Calculation / display |
|---|---|---|---|
| Eligible requests | How many requests can be evaluated? | Note Requests | Count requests eligible for the selected feed and dates with a full observation window |
| Covered requests and coverage rate | How many received a new note within the window? | Note Requests + Notes | Count requests receiving at least one new note after eligibility and within the window; divide by eligible requests. Count each request once |
| No observed note | How many had no observed qualifying note? | Note Requests + Notes | Eligible requests minus covered requests; show count and percentage. This does not prove that a post needs a note |
| Weekly coverage chart and table | Which periods have lower coverage? | Note Requests + Notes | Group by eligibility week; show eligible, covered, no-observed-note counts and coverage rate. Overall rate uses total counts, not an average of weekly rates |
| Eligible notes | How many notes support response-time analysis? | Notes + Note Status History | Count mature notes in the selected creation period with usable timing/history information; disclose exclusions |
| Reached non-NMR | How many reached a recorded status within the window? | Notes + Note Status History | Count first non-NMR events within the window; divide by eligible notes. Non-NMR includes Helpful and Not Helpful |
| No recorded transition | How many have no recorded transition within the window? | Notes + Note Status History | Eligible notes minus completed events. A later event does not count as completion within the selected window |
| Median response time | How long did completed events take? | Notes + Note Status History | Median hours from note creation to first non-NMR, among events completed within the window; always show the completed-note count |
| Completion by classification | How does completion differ by note classification? | Notes + Note Status History | Stacked counts of completed events and no recorded transitions; show group sizes and retain an Unknown category |
| Early ratings vs. response time | How are early rating activity and completed response time associated? | Ratings + Notes + Note Status History | One point per completed note: ratings received in the first 24 hours on x; hours to first non-NMR on y. Linear axes; y cannot exceed the observation window. No causal interpretation |
| Rating helpfulness | How were notes in this cohort rated? | Ratings for the selected response-time note cohort | Count valid Helpful, Somewhat Helpful and Not Helpful ratings within the observation window after note creation. Divide each by all valid-level ratings; show missing/legacy exclusions separately |

Important distinctions:
- Coverage concerns requests; Response Time concerns notes; Helpfulness concerns ratings.
- First non-NMR is not the same as first Helpful. Rating helpfulness is not a note's status.
- Unmatched status records, invalid times and inconsistent event history are excluded from timing metrics and counted separately. Missing first-event history for currently resolved notes cannot be treated as zero waiting time.
- Notes with no first-event record and current NMR may be shown as having no recorded transition; this does not prove they never resolved.
- If the scatter plot contains more than 2,000 completed notes, show a reproducible sample with a sample label. KPI and aggregate calculations must still use the full eligible cohort.

## 3. Filters

| Section | Filter | Proposed default | What it affects |
|---|---|---|---|
| Coverage | Request eligibility dates | Latest 28 complete days with a full observation window, based on the verified cutoff | Coverage cards, weekly chart and table |
| Coverage | Feed: Standard / Small / Large / XL | Standard; select one feed at a time | Coverage only |
| Coverage | Observation window: 7 / 14 / 28 days | 7 days | Coverage eligibility and covered-event calculations |
| Response | Note-created dates | Latest 28 complete days with a full observation window | Response charts/cards and Rating Helpfulness |
| Response | Classification, including Unknown | All | Response and Helpfulness only; never Coverage |
| Response | Note type: All / Media / Non-media / Collaborative / Unknown | All | Response and Helpfulness only; categories may overlap |
| Response | Observation window: 7 / 14 / 28 days | 7 days | Response completion and rating-helpfulness period |

Users may select more recent dates, but records without full observation time are disclosed and excluded from fixed-window denominators. Do not silently change the selected dates or window. If the data cutoff is unconfirmed, show a configuration warning instead of calculated time-window metrics.

## 4. Interactions and Special Cases

- Click a coverage week to update the Coverage cards and table. Keep the weekly overview visible and label the selected week. Response and Helpfulness remain unchanged. Clear week selection to restore totals.
- Classification charts provide hover details; use the named filter to change the response cohort. Do not silently filter unrelated sections.
- Hover over charts to see counts, rates, units and relevant denominators. Scatter selection may show a read-only detail list, but does not change KPI denominators.
- Reset Coverage and Reset Response restore only their own section's defaults. Changing filters clears dependent chart selections.
- Display percentages and hours to one decimal place; counts use thousands separators. Do not round before calculation.
- Zero denominator or no completed events: show N/A with a reason, not 0%, zero hours, NaN or Infinity.
- Show missing values, timing exclusions and immature-record counts clearly. Explain formulas and limitations in Data quality & definitions.
- While updating, label previous results as Updating; on failure show an error and Retry, not fabricated zero values.
- Export filtered aggregate tables with filter settings, units and snapshot date. Export must match the displayed scope; do not export full raw datasets.
- Review candidates describe low observed coverage and waiting patterns with group sizes. They must not claim that adding writers or ratings will cause improvement.

## 5. Acceptance Checks

| Example | Expected result |
|---|---|
| 10 eligible requests; 4 receive new notes, including one with three notes | 10 eligible, 4 covered, 40.0% coverage and 6 without an observed note |
| A note is created before request eligibility or after its 7-day window | It does not qualify for 7-day coverage. An event exactly at eligibility or at the 7-day boundary is included under the proposed boundary rule |
| A request has only 3 days of observation, with a 7-day window selected | Excluded from the coverage denominator and counted as immature |
| Classification changes from All to one category | Response and Helpfulness update; Coverage is unchanged |
| 5 eligible notes: three complete at 2, 10 and 30 hours; one completes after 7 days; one has no recorded transition | 3 completed, 2 without a transition within 7 days, completion rate 60.0%, median 10 hours |
| 7 Helpful, 1 Somewhat Helpful, 2 Not Helpful, plus 3 missing legacy levels | Valid denominator 10, Helpful 70.0%; three missing levels shown separately |
| No eligible requests, no completed events or no valid ratings | Corresponding rate or median is N/A with a clear explanation |
| Select a coverage week, export, then reset | Export matches the selected table; reset restores Coverage totals without changing Response filters |
| Scatter shows a sample of a large cohort | Sampling is labeled; KPI and aggregate totals still use the full cohort |

Before final team submission, confirm the default feed, observation window, response endpoint, data cutoff and timing exclusions with Members 3–6. This document is the dashboard-design contribution; it does not claim the backend or Phase 3 interface has been implemented.

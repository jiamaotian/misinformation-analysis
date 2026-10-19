
# Phase 2 — Response Time & Ratings Backend

**Owner:** Jessica  
**Project:** DSO 576 — Community Notes Misinformation Dashboard

## Purpose

This module provides reusable backend functions for analyzing
Community Notes response time, rating activity, and observed
helpfulness.

The outputs support the Phase 3 dashboard MVP.

## Data Sources

The analysis uses three cleaned datasets:

1. **Notes** — cleaned by Peyton
2. **Ratings** — cleaned by Yoojin
3. **Note Status History** — cleaned by Yoojin

All three datasets are joined using `noteId`.

## Metrics

### 1. Response Time

Response time measures the number of hours between note
creation and the first non-NMR status.

Formula:

Response Time (hours) =
(First Non-NMR Timestamp - Note Creation Timestamp) / 3,600,000

Only valid timestamps and non-NMR statuses are included.
Notes without a first non-NMR status have missing response times.

The dashboard reports the median response time overall
and by note classification.

### 2. Rating Activity

Rating activity measures the number of valid ratings
associated with each note.

Notes with no valid ratings receive a rating count of zero
within the supplied rating dataset.

### 3. Observed Helpfulness

Observed Helpfulness =
HELPFUL Ratings / All Valid Helpfulness Ratings

Valid categories:
- HELPFUL
- SOMEWHAT_HELPFUL
- NOT_HELPFUL

The metric is descriptive and does not represent the
official Community Notes scoring decision.

## Python Functions

- `calculate_response_time()`
- `summarize_response_time()`
- `calculate_rating_activity()`
- `prepare_activity_scatter()`
- `calculate_helpfulness()`
- `summarize_helpfulness()`
- `build_dashboard_data()`

## Dashboard Outputs

`build_dashboard_data()` returns:

- `median_response_hours`
- `observed_helpful_share`
- `response_summary`
- `rating_activity`
- `activity_vs_response`
- `helpfulness_summary`

## Tests

Run from the project root:

```bash
python phase2-jessica/test_response_ratings.py
```

The test suite checks calculations, missing values,
invalid ratings, duplicate IDs, cleaning flags,
and dashboard output structures.

## Limitations

- Metrics describe observed records, not the complete
  Community Notes population.
- Unmatched records do not establish a true absence of ratings.
- The analysis requires an aligned data snapshot.
- The current implementation uses in-memory pandas DataFrames.
  Large datasets may require chunked processing.
- Observed helpfulness is not equivalent to broad agreement.
- Repeated ratings by the same participant are deduplicated
  by retaining the first encountered record; this policy
  must be reconciled with the canonical team dataset.
```

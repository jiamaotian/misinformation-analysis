
"""
DSO 576 - Phase 2
Jessica: Response Time and Ratings Backend Analysis

This module calculates:
1. Time to first non-NMR status
2. Median response time by note classification
3. Rating activity per note
4. Rating activity versus response time
5. Observed helpfulness
6. Helpfulness distribution by classification

Input: Cleaned pandas DataFrames from Peyton and Yoojin.
Output: Reusable values and pandas DataFrames for Phase 3.

Run tests:
    python phase2-jessica/test_response_ratings.py
"""

import pandas as pd


# --------------------------------------------------
# Constants
# --------------------------------------------------

VALID_LEVELS = (
    "HELPFUL",
    "SOMEWHAT_HELPFUL",
    "NOT_HELPFUL",
)

NON_NMR_STATUSES = (
    "CURRENTLY_RATED_HELPFUL",
    "CURRENTLY_RATED_NOT_HELPFUL",
)

MILLISECONDS_PER_HOUR = 3_600_000


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def _require_columns(df, columns):
    """Check that the required columns exist."""

    missing = set(columns) - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )


def _normalize_ids(df):
    """Keep valid note IDs as strings to avoid precision loss."""

    _require_columns(df, ["noteId"])

    result = df.copy()

    result["noteId"] = (
        result["noteId"]
        .astype("string")
        .str.strip()
    )

    valid_ids = result["noteId"].str.fullmatch(
        r"[1-9][0-9]*",
        na=False
    )

    return result.loc[valid_ids].copy()


def _clean_flag(series):
    """Interpret boolean flags from cleaned CSV/TSV files."""

    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .isin(["true", "1"])
    )


def _clean_levels(series):
    """Normalize helpfulness labels."""

    return (
        series.astype("string")
        .str.strip()
        .str.upper()
    )


def _valid_ratings(ratings):
    """Apply shared validity and duplicate-rating rules."""

    _require_columns(
        ratings,
        ["noteId", "helpfulnessLevel"]
    )

    r = _normalize_ids(ratings)

    # Use Yoojin's cleaning flags if available.
    if "qc_valid_helpfulness" in r.columns:
        r = r.loc[
            _clean_flag(r["qc_valid_helpfulness"])
        ].copy()

    if "qc_key_valid" in r.columns:
        r = r.loc[
            _clean_flag(r["qc_key_valid"])
        ].copy()

    r["helpfulnessLevel"] = _clean_levels(
        r["helpfulnessLevel"]
    )

    r = r.loc[
        r["helpfulnessLevel"].isin(VALID_LEVELS)
    ].copy()

    # One rating per participant per note.
    if "raterParticipantId" in r.columns:

        r["raterParticipantId"] = (
            r["raterParticipantId"]
            .astype("string")
            .str.strip()
        )

        r = r.loc[
            r["raterParticipantId"].notna()
            & r["raterParticipantId"].ne("")
        ].copy()

        r = r.drop_duplicates(
            subset=["noteId", "raterParticipantId"],
            keep="first"
        )

    else:
        r = r.drop_duplicates()

    return r


# --------------------------------------------------
# 1. Response Time
# --------------------------------------------------

def calculate_response_time(notes, status, cutoff_ms=None):
    """
    Calculate hours between note creation and first non-NMR status.

    Unresolved notes retain NaN response times.
    Negative or invalid response times are excluded.

    Returns a note-level DataFrame.
    """

    _require_columns(
        notes,
        [
            "noteId",
            "createdAtMillis",
            "classification",
        ]
    )

    _require_columns(
        status,
        [
            "noteId",
            "timestampMillisOfFirstNonNMRStatus",
            "firstNonNMRStatus",
        ]
    )

    n = _normalize_ids(notes)
    s = _normalize_ids(status)

    if n["noteId"].duplicated().any():
        raise ValueError(
            "Notes contains duplicate noteId values"
        )

    if s["noteId"].duplicated().any():
        raise ValueError(
            "Status contains duplicate noteId values"
        )

    status_columns = [
        "noteId",
        "timestampMillisOfFirstNonNMRStatus",
        "firstNonNMRStatus",
    ]

    if "qc_response_eligible" in s.columns:
        status_columns.append("qc_response_eligible")

    s = s[status_columns].copy()

    result = n[
        ["noteId", "createdAtMillis", "classification"]
    ].merge(
        s,
        on="noteId",
        how="left",
        validate="one_to_one"
    )

    start = pd.to_numeric(
        result["createdAtMillis"],
        errors="coerce"
    )

    end = pd.to_numeric(
        result["timestampMillisOfFirstNonNMRStatus"],
        errors="coerce"
    )

    status_values = (
        result["firstNonNMRStatus"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    valid_status = status_values.isin(
        NON_NMR_STATUSES
    )

    valid = (
        valid_status
        & start.gt(0)
        & end.ge(start)
    )

    # Respect Yoojin's cleaned status eligibility.
    if "qc_response_eligible" in result.columns:

        valid = (
            valid
            & _clean_flag(result["qc_response_eligible"])
        )

    # Optional observation cutoff.
    if cutoff_ms is not None:

        valid = (
            valid
            & start.le(cutoff_ms)
            & end.le(cutoff_ms)
        )

    result["response_time_hours"] = (
        ((end - start) / MILLISECONDS_PER_HOUR)
        .where(valid.fillna(False))
    )

    return result


# --------------------------------------------------
# 2. Response Time Summary
# --------------------------------------------------

def summarize_response_time(response_df):
    """
    Aggregate response times by note classification.

    Returns:
        classification
        total_notes
        resolved_notes
        median_response_hours
    """

    _require_columns(
        response_df,
        [
            "classification",
            "response_time_hours",
        ]
    )

    summary = (
        response_df
        .groupby(
            "classification",
            dropna=False
        )
        .agg(
            total_notes=(
                "response_time_hours",
                "size"
            ),
            resolved_notes=(
                "response_time_hours",
                "count"
            ),
            median_response_hours=(
                "response_time_hours",
                "median"
            ),
        )
        .reset_index()
    )

    return summary


# --------------------------------------------------
# 3. Rating Activity
# --------------------------------------------------

def calculate_rating_activity(notes, ratings):
    """
    Count valid ratings received by each note.

    Notes without valid ratings receive rating_count = 0.
    """

    _require_columns(
        notes,
        ["noteId"]
    )

    n = _normalize_ids(notes)

    if n["noteId"].duplicated().any():
        raise ValueError(
            "Notes contains duplicate noteId values"
        )

    r = _valid_ratings(ratings)

    rating_counts = (
        r.groupby("noteId")
        .size()
        .reset_index(name="rating_count")
    )

    result = (
        n[["noteId"]]
        .merge(
            rating_counts,
            on="noteId",
            how="left",
            validate="one_to_one"
        )
    )

    result["rating_count"] = (
        result["rating_count"]
        .fillna(0)
        .astype("int64")
    )

    return result


# --------------------------------------------------
# 4. Rating Activity vs. Response Time
# --------------------------------------------------

def prepare_activity_scatter(
    response_df,
    rating_activity
):
    """
    Prepare note-level data for the dashboard scatterplot.

    X-axis: Rating count
    Y-axis: Response time (hours)
    """

    _require_columns(
        response_df,
        [
            "noteId",
            "classification",
            "response_time_hours",
        ]
    )

    _require_columns(
        rating_activity,
        [
            "noteId",
            "rating_count",
        ]
    )

    scatter = response_df[
        [
            "noteId",
            "classification",
            "response_time_hours",
        ]
    ].merge(
        rating_activity,
        on="noteId",
        how="left",
        validate="one_to_one"
    )

    scatter["rating_count"] = (
        scatter["rating_count"]
        .fillna(0)
        .astype("int64")
    )

    return scatter


# --------------------------------------------------
# 5. Observed Helpfulness
# --------------------------------------------------

def calculate_helpfulness(ratings, notes):
    """
    Join valid ratings with note classification.

    HELPFUL ratings are observed responses, not
    official Community Notes scoring decisions.
    """

    _require_columns(
        notes,
        [
            "noteId",
            "classification",
        ]
    )

    n = _normalize_ids(notes)

    if n["noteId"].duplicated().any():
        raise ValueError(
            "Notes contains duplicate noteId values"
        )

    r = _valid_ratings(ratings)

    helpfulness = r.merge(
        n[
            ["noteId", "classification"]
        ],
        on="noteId",
        how="inner",
        validate="many_to_one"
    )

    return helpfulness


# --------------------------------------------------
# 6. Helpfulness Summary
# --------------------------------------------------

def summarize_helpfulness(helpfulness_df):
    """
    Calculate rating counts and shares by classification.

    Rating shares use valid matched ratings as
    their denominator.
    """

    _require_columns(
        helpfulness_df,
        [
            "classification",
            "helpfulnessLevel",
        ]
    )

    counts = (
        helpfulness_df
        .groupby(
            [
                "classification",
                "helpfulnessLevel",
            ],
            dropna=False
        )
        .size()
        .reset_index(name="rating_count")
    )

    counts["total_ratings"] = (
        counts.groupby(
            "classification",
            dropna=False
        )["rating_count"]
        .transform("sum")
    )

    counts["rating_share"] = (
        counts["rating_count"]
        / counts["total_ratings"]
    )

    return counts


# --------------------------------------------------
# 7. Build Complete Dashboard Backend Data
# --------------------------------------------------

def build_dashboard_data(
    notes,
    ratings,
    status,
    cutoff_ms=None
):
    """
    Generate reusable outputs for Jessica's dashboard panels.

    Returns a dictionary containing:
        median_response_hours
        observed_helpful_share
        response_summary
        rating_activity
        activity_vs_response
        helpfulness_summary
    """

    # Response-time analysis
    response = calculate_response_time(
        notes,
        status,
        cutoff_ms=cutoff_ms
    )

    response_summary = summarize_response_time(
        response
    )

    overall_median = (
        response["response_time_hours"]
        .median()
    )

    # Rating activity analysis
    activity = calculate_rating_activity(
        notes,
        ratings
    )

    scatter = prepare_activity_scatter(
        response,
        activity
    )

    # Helpfulness analysis
    helpfulness = calculate_helpfulness(
        ratings,
        notes
    )

    helpfulness_summary = summarize_helpfulness(
        helpfulness
    )

    if len(helpfulness) > 0:

        helpful_share = (
            helpfulness["helpfulnessLevel"]
            .eq("HELPFUL")
            .mean()
        )

    else:
        helpful_share = float("nan")

    return {
        "median_response_hours": overall_median,
        "observed_helpful_share": helpful_share,
        "response_summary": response_summary,
        "rating_activity": activity,
        "activity_vs_response": scatter,
        "helpfulness_summary": helpfulness_summary,
    }
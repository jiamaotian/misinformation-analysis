
"""
DSO 576 - Phase 2
Jessica: Real Community Notes Response Time & Ratings Analysis

Uses cleaned outputs from Peyton and Yoojin.
Processes large files in chunks and saves dashboard-ready results.

Run from project root:
    python phase2-jessica/run_real_analysis.py
"""

from pathlib import Path
from collections import Counter
import json

import pandas as pd

from response_ratings_analysis import (
    calculate_response_time,
    summarize_response_time,
    prepare_activity_scatter,
)

ROOT = Path(__file__).resolve().parent.parent
JESSICA = ROOT / "phase2-jessica"

NOTES_PATH = ROOT / "phase2-peyton/outputs/notes_clean.csv"
RATINGS_PATH = JESSICA / "cleaned_data/ratings_clean.tsv.gz"
STATUS_PATH = JESSICA / "cleaned_data/status_clean.tsv.gz"
SUCCESS_PATH = JESSICA / "cleaned_data/SUCCESS.json"
OUTPUT = JESSICA / "results"

CUTOFF = pd.Timestamp("2026-10-02T23:59:59.999Z")
CUTOFF_MS = CUTOFF.value // 1_000_000
CHUNK_SIZE = 100_000

LEVELS = [
    "HELPFUL",
    "SOMEWHAT_HELPFUL",
    "NOT_HELPFUL",
]


def valid_flag(series):
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .isin(["true", "1"])
    )


def valid_id(series):
    return series.astype("string").str.fullmatch(
        r"[1-9][0-9]*", na=False
    )


def check_inputs():
    """Verify required inputs and cleaning completion."""

    for path in [NOTES_PATH, RATINGS_PATH, STATUS_PATH, SUCCESS_PATH]:
        if not path.is_file():
            raise FileNotFoundError(f"Missing file: {path}")

    success = json.loads(SUCCESS_PATH.read_text())

    if (
        success.get("status") != "complete_supplied_files"
        or set(success.get("reports", [])) != {"ratings", "status"}
    ):
        raise ValueError("Cleaning outputs are not fully validated.")

    print("PASS: Required cleaned input files found")


def load_notes():
    """Load Peyton's cleaned Notes and select valid cohort."""

    notes = pd.read_csv(
        NOTES_PATH,
        dtype="string",
        keep_default_na=False,
    )

    required = ["noteId", "createdAtMillis", "classification"]

    if not set(required).issubset(notes.columns):
        raise ValueError("Notes missing required columns")

    total = len(notes)

    notes["noteId"] = notes["noteId"].str.strip()

    created = pd.to_numeric(
        notes["createdAtMillis"], errors="coerce"
    )

    valid = (
        valid_id(notes["noteId"])
        & created.gt(0)
        & created.le(CUTOFF_MS)
    )

    notes = notes.loc[valid, required].copy()

    if notes["noteId"].duplicated().any():
        raise ValueError("Duplicate valid noteId in Notes")

    print(f"Notes input rows: {total:,}")
    print(f"Notes in cutoff cohort: {len(notes):,}")

    return notes, total


def load_matching_status(note_ids):
    """Read Status History in chunks, keeping matching Notes."""

    columns = [
        "noteId",
        "timestampMillisOfFirstNonNMRStatus",
        "firstNonNMRStatus",
        "qc_response_eligible",
    ]

    matches = []
    scanned = 0

    reader = pd.read_csv(
        STATUS_PATH,
        sep="\t",
        compression="gzip",
        dtype="string",
        usecols=columns,
        chunksize=CHUNK_SIZE,
        keep_default_na=False,
    )

    for chunk in reader:
        scanned += len(chunk)

        matched = chunk.loc[
            chunk["noteId"].isin(note_ids)
        ].copy()

        if not matched.empty:
            matches.append(matched)

        if scanned % 1_000_000 < CHUNK_SIZE:
            print(f"Status scanned: {scanned:,}")

    if matches:
        status = pd.concat(matches, ignore_index=True)
    else:
        status = pd.DataFrame(columns=columns)

    if status["noteId"].duplicated().any():
        raise ValueError("Duplicate matching Status noteId")

    print(f"Status matched rows: {len(status):,}")

    return status, scanned


def aggregate_ratings(note_ids, classifications):
    """
    Stream cleaned Ratings and aggregate matched records.

    Retain the first encountered valid participant-note
    rating, consistent with the current backend policy.
    """

    rating_counts = Counter()
    helpfulness_counts = Counter()
    daily_counts = Counter()

    seen_pairs = set()

    scanned = 0
    valid_matched = 0
    duplicate_pairs = 0

    columns = [
        "noteId",
        "raterParticipantId",
        "helpfulnessLevel",
        "createdAtMillis",
        "qc_valid_helpfulness",
        "qc_key_valid",
    ]

    reader = pd.read_csv(
        RATINGS_PATH,
        sep="\t",
        compression="gzip",
        dtype="string",
        usecols=columns,
        chunksize=CHUNK_SIZE,
        keep_default_na=False,
    )

    for chunk in reader:
        scanned += len(chunk)

        chunk = chunk.loc[
            chunk["noteId"].isin(note_ids)
        ].copy()

        if chunk.empty:
            continue

        timestamps = pd.to_numeric(
            chunk["createdAtMillis"], errors="coerce"
        )

        levels = (
            chunk["helpfulnessLevel"]
            .str.strip()
            .str.upper()
        )

        valid = (
            valid_flag(chunk["qc_valid_helpfulness"])
            & valid_flag(chunk["qc_key_valid"])
            & levels.isin(LEVELS)
            & timestamps.gt(0)
            & timestamps.le(CUTOFF_MS)
            & chunk["raterParticipantId"].str.strip().ne("")
        )

        chunk = chunk.loc[valid].copy()

        for row in chunk.itertuples(index=False):
            note_id = str(row.noteId)
            rater_id = str(row.raterParticipantId).strip()
            pair = (note_id, rater_id)

            if pair in seen_pairs:
                duplicate_pairs += 1
                continue

            seen_pairs.add(pair)

            level = str(row.helpfulnessLevel).strip().upper()
            classification = classifications[note_id]

            rating_counts[note_id] += 1
            helpfulness_counts[(classification, level)] += 1
            valid_matched += 1

            day = pd.to_datetime(
                int(row.createdAtMillis),
                unit="ms",
                utc=True,
            ).strftime("%Y-%m-%d")

            daily_counts[day] += 1

        if scanned % 1_000_000 < CHUNK_SIZE:
            print(f"Ratings scanned: {scanned:,}")

    activity = pd.DataFrame({
        "noteId": sorted(note_ids),
    })

    activity["rating_count"] = (
        activity["noteId"]
        .map(rating_counts)
        .fillna(0)
        .astype("int64")
    )

    summary_rows = []

    for classification in sorted(set(classifications.values())):
        total = sum(
            helpfulness_counts[(classification, level)]
            for level in LEVELS
        )

        for level in LEVELS:
            count = helpfulness_counts[(classification, level)]

            summary_rows.append({
                "classification": classification,
                "helpfulnessLevel": level,
                "rating_count": count,
                "total_ratings": total,
                "rating_share": count / total if total else None,
            })

    helpfulness = pd.DataFrame(summary_rows)

    daily = pd.DataFrame(
        sorted(daily_counts.items()),
        columns=["rating_date_utc", "rating_count"],
    )

    audit = {
        "ratings_rows_scanned": scanned,
        "valid_matched_ratings": valid_matched,
        "duplicate_participant_note_pairs": duplicate_pairs,
        "distinct_notes_with_observed_ratings": len(rating_counts),
    }

    return activity, helpfulness, daily, audit


def save_results(
    notes,
    response,
    activity,
    helpfulness,
    daily,
    audit,
):
    OUTPUT.mkdir(parents=True, exist_ok=True)

    response_summary = summarize_response_time(response)

    scatter = prepare_activity_scatter(response, activity)

    response_summary.to_csv(
        OUTPUT / "response_summary.csv", index=False
    )

    activity.to_csv(
        OUTPUT / "rating_activity.csv", index=False
    )

    scatter.to_csv(
        OUTPUT / "activity_vs_response.csv", index=False
    )

    helpfulness.to_csv(
        OUTPUT / "helpfulness_summary.csv", index=False
    )

    daily.to_csv(
        OUTPUT / "rating_activity_daily.csv", index=False
    )

    total_valid_ratings = int(helpfulness["rating_count"].sum())

    helpful_ratings = int(
        helpfulness.loc[
            helpfulness["helpfulnessLevel"] == "HELPFUL",
            "rating_count",
        ].sum()
    )

    summary = {
        "analysis": "Jessica - Response Time and Ratings",
        "cutoff_utc": CUTOFF.isoformat(),
        "notes_in_cohort": int(len(notes)),
        "notes_with_matching_status": audit["notes_with_matching_status"],
        "notes_with_first_non_nmr": int(
            response["response_time_hours"].notna().sum()
        ),
        "median_response_hours": (
            float(response["response_time_hours"].median())
            if response["response_time_hours"].notna().any()
            else None
        ),
        "valid_matched_ratings": total_valid_ratings,
        "observed_helpful_share": (
            helpful_ratings / total_valid_ratings
            if total_valid_ratings else None
        ),
        **audit,
        "data_scope": (
            "Selected supplied Community Notes shards only; "
            "download snapshots may differ."
        ),
        "interpretation": (
            "Unmatched records are not evidence of no rating "
            "or no status in the full platform dataset."
        ),
    }

    (OUTPUT / "metrics_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )

    print("\n=== REAL ANALYSIS SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print(f"\nResults saved to: {OUTPUT}")


def main():
    print("Jessica - Real Data Backend Analysis\n")

    check_inputs()

    notes, original_notes_count = load_notes()

    note_ids = set(notes["noteId"])

    classifications = dict(
        zip(notes["noteId"], notes["classification"])
    )

    status, status_scanned = load_matching_status(note_ids)

    response = calculate_response_time(
        notes,
        status,
        cutoff_ms=CUTOFF_MS,
    )

    print(
        "Notes reaching first non-NMR:",
        response["response_time_hours"].notna().sum(),
    )

    print("\nProcessing cleaned ratings in chunks...")

    activity, helpfulness, daily, audit = aggregate_ratings(
        note_ids, classifications
    )

    audit["original_notes_rows"] = original_notes_count
    audit["status_rows_scanned"] = status_scanned
    audit["notes_with_matching_status"] = len(status)

    save_results(
        notes,
        response,
        activity,
        helpfulness,
        daily,
        audit,
    )


if __name__ == "__main__":
    main()

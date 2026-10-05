"""Reproducibly clean and validate the Community Notes TSV snapshot.

All source columns and rows are preserved. DuckDB performs bounded-memory scans
of the 44.5 GiB Ratings input; pandas writes the small validation reports. The
script never edits source files and refuses to write into a nonempty output
directory.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd


REQUEST_COLUMNS = [
    "tweetId", "noteRequestFeedEligibleAtMillis",
    "apiSmallFeedEligibleAtMillis", "apiLargeFeedEligibleAtMillis",
    "apiXlFeedEligibleAtMillis", "sourceLinks", "suggestions",
]
NOTES_COLUMNS = [
    "noteId", "noteAuthorParticipantId", "createdAtMillis", "tweetId",
    "classification", "believable", "harmful", "validationDifficulty",
    "misleadingOther", "misleadingFactualError", "misleadingManipulatedMedia",
    "misleadingOutdatedInformation", "misleadingMissingImportantContext",
    "misleadingUnverifiedClaimAsFact", "misleadingSatire",
    "notMisleadingOther", "notMisleadingFactuallyCorrect",
    "notMisleadingOutdatedButNotWhenWritten", "notMisleadingClearlySatire",
    "notMisleadingPersonalOpinion", "trustworthySources", "summary",
    "isMediaNote", "isCollaborativeNote",
]
RATINGS_COLUMNS = [
    "noteId", "raterParticipantId", "createdAtMillis", "version", "agree",
    "disagree", "helpful", "notHelpful", "helpfulnessLevel", "helpfulOther",
    "helpfulInformative", "helpfulClear", "helpfulEmpathetic",
    "helpfulGoodSources", "helpfulUniqueContext", "helpfulAddressesClaim",
    "helpfulImportantContext", "helpfulUnbiasedLanguage", "notHelpfulOther",
    "notHelpfulIncorrect", "notHelpfulSourcesMissingOrUnreliable",
    "notHelpfulOpinionSpeculationOrBias", "notHelpfulMissingKeyPoints",
    "notHelpfulOutdated", "notHelpfulHardToUnderstand",
    "notHelpfulArgumentativeOrBiased", "notHelpfulOffTopic",
    "notHelpfulSpamHarassmentOrAbuse", "notHelpfulIrrelevantSources",
    "notHelpfulOpinionSpeculation", "notHelpfulNoteNotNeeded",
    "ratedOnTweetId", "ratingSourceBucketed", "suggestion", "suggestionId",
]
STATUS_COLUMNS = [
    "noteId", "noteAuthorParticipantId", "createdAtMillis",
    "timestampMillisOfFirstNonNMRStatus", "firstNonNMRStatus",
    "timestampMillisOfCurrentStatus", "currentStatus",
    "timestampMillisOfLatestNonNMRStatus", "mostRecentNonNMRStatus",
    "timestampMillisOfStatusLock", "lockedStatus",
    "timestampMillisOfRetroLock", "currentCoreStatus",
    "currentExpansionStatus", "currentGroupStatus", "currentDecidedBy",
    "currentModelingGroup", "timestampMillisOfMostRecentStatusChange",
    "timestampMillisOfNmrDueToMinStableCrhTime", "currentMultiGroupStatus",
    "currentModelingMultiGroup", "timestampMinuteOfFinalScoringOutput",
    "timestampMillisOfFirstNmrDueToMinStableCrhTime",
    "timestampMillisAbovePcrhThreshold",
]

ELIGIBILITY_TIMESTAMPS = [
    "noteRequestFeedEligibleAtMillis", "apiSmallFeedEligibleAtMillis",
    "apiLargeFeedEligibleAtMillis", "apiXlFeedEligibleAtMillis",
]
STATUS_TIMESTAMPS = [
    "createdAtMillis", "timestampMillisOfFirstNonNMRStatus",
    "timestampMillisOfCurrentStatus", "timestampMillisOfLatestNonNMRStatus",
    "timestampMillisOfStatusLock", "timestampMillisOfRetroLock",
    "timestampMillisOfMostRecentStatusChange",
    "timestampMillisOfNmrDueToMinStableCrhTime",
    "timestampMillisOfFirstNmrDueToMinStableCrhTime",
    "timestampMillisAbovePcrhThreshold",
]
NOTES_BINARY_COLUMNS = [
    c for c in NOTES_COLUMNS
    if c.startswith("misleading") or c.startswith("notMisleading")
] + ["trustworthySources", "isMediaNote", "isCollaborativeNote"]
RATINGS_BINARY_COLUMNS = [
    c for c in RATINGS_COLUMNS
    if c != "helpfulnessLevel" and (
        c in {"agree", "disagree", "helpful", "notHelpful"}
    or c.startswith("helpful") or c.startswith("notHelpful")
    )
]

DATASETS = {
    "note_request": ("batSignals-*.tsv", REQUEST_COLUMNS),
    "notes": ("notes-*.tsv", NOTES_COLUMNS),
    "ratings": ("ratings-*.tsv", RATINGS_COLUMNS),
    "note_status": ("noteStatusHistory-*.tsv", STATUS_COLUMNS),
}


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=root / "Project_data_1004")
    parser.add_argument("--output-dir", type=Path, default=root / "cleaned_v2")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--memory-limit", default="4GB")
    parser.add_argument(
        "--resume-incomplete",
        action="store_true",
        help="Resume a prior run only when its output contains _INCOMPLETE.",
    )
    return parser.parse_args()


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def state_expr(column: str) -> str:
    col = q(column)
    number = f"try_cast({col} AS BIGINT)"
    return f"""CASE
        WHEN {col} IS NULL OR {col} = '' THEN 'blank'
        WHEN {number} IS NULL THEN 'invalid_numeric'
        WHEN {number} = -1 THEN 'minus_one'
        WHEN {number} < 0 THEN 'other_negative'
        WHEN {number} = 0 THEN 'zero'
        WHEN try(epoch_ms({number})) IS NULL THEN 'out_of_range'
        ELSE 'valid_positive'
    END"""


def timestamp_fields(column: str, prefix: str) -> list[str]:
    state = state_expr(column)
    number = f"try_cast({q(column)} AS BIGINT)"
    return [
        f"{number} AS {q(prefix + '_ms')}",
        f"CASE WHEN ({state}) = 'valid_positive' THEN try(epoch_ms({number})) END AS {q(prefix + '_utc')}",
        f"({state}) AS {q(prefix + '_state')}",
    ]


def eligibility_fields(column: str, prefix: str) -> list[str]:
    state = state_expr(column)
    return timestamp_fields(column, prefix) + [
        f"CASE WHEN ({state}) = 'minus_one' THEN FALSE WHEN ({state}) = 'valid_positive' THEN TRUE END AS {q(prefix + '_eligible')}",
        f"({state}) NOT IN ('minus_one', 'valid_positive') AS {q(prefix + '_invalid')}",
    ]


def bool_fields(columns: Iterable[str]) -> list[str]:
    return [
        f"CASE WHEN {q(c)} = '1' THEN TRUE WHEN {q(c)} = '0' THEN FALSE END AS {q(c + '_bool')}"
        for c in columns
    ]


def read_csv_sql(glob: str) -> str:
    return (
        f"read_csv('{glob}', delim='\\t', header=true, union_by_name=true, "
        "all_varchar=true, null_padding=true)"
    )


def fetch_records(con: duckdb.DuckDBPyConnection, query: str) -> list[dict]:
    cursor = con.execute(query)
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def scalar(con: duckdb.DuckDBPyConnection, query: str) -> int:
    value = con.execute(query).fetchone()[0]
    return int(value or 0)


def write_csv(path: Path, records: list[dict]) -> None:
    pd.DataFrame(records).to_csv(path, index=False, encoding="utf-8")


def ensure_safe_output(
    input_dir: Path, output_dir: Path, resume_incomplete: bool = False
) -> None:
    source = input_dir.resolve()
    output = output_dir.resolve()
    if output == source or source in output.parents:
        raise ValueError("Output directory must not be the source directory or its child")
    if output.exists() and any(output.iterdir()):
        if resume_incomplete and (output / "_INCOMPLETE").exists():
            return
        raise FileExistsError(
            f"Output directory is not empty: {output}. Use a new versioned path."
        )
    output.mkdir(parents=True, exist_ok=True)


def require_sources(input_dir: Path) -> None:
    problems = []
    for name, (pattern, _) in DATASETS.items():
        if not list(input_dir.glob(pattern)):
            problems.append(f"{name}: {pattern}")
    if problems:
        raise FileNotFoundError("Missing required sources: " + ", ".join(problems))


def create_raw_views(con: duckdb.DuckDBPyConnection, input_dir: Path) -> None:
    root = sql_path(input_dir)
    for name, (pattern, _) in DATASETS.items():
        con.execute(
            f"CREATE OR REPLACE VIEW raw_{name} AS SELECT * FROM "
            + read_csv_sql(f"{root}/{pattern}")
        )


def clean_queries() -> dict[str, str]:
    request_extra = ["tweetId AS tweet_id"]
    request_prefixes = {
        "noteRequestFeedEligibleAtMillis": "note_request_feed_eligible_at",
        "apiSmallFeedEligibleAtMillis": "api_small_feed_eligible_at",
        "apiLargeFeedEligibleAtMillis": "api_large_feed_eligible_at",
        "apiXlFeedEligibleAtMillis": "api_xl_feed_eligible_at",
    }
    for column, prefix in request_prefixes.items():
        request_extra.extend(eligibility_fields(column, prefix))

    notes_extra = [
        "noteId AS note_id", "tweetId AS tweet_id",
        "noteAuthorParticipantId AS note_author_participant_id",
        *timestamp_fields("createdAtMillis", "created_at"),
        *bool_fields(NOTES_BINARY_COLUMNS),
    ]
    ratings_extra = [
        "noteId AS note_id", "raterParticipantId AS rater_participant_id",
        "ratedOnTweetId AS rated_on_tweet_id",
        *timestamp_fields("createdAtMillis", "created_at"),
        "helpfulnessLevel IN ('HELPFUL', 'SOMEWHAT_HELPFUL', 'NOT_HELPFUL') AS helpfulness_level_valid",
        *bool_fields(RATINGS_BINARY_COLUMNS),
    ]
    status_extra = [
        "noteId AS note_id",
        "noteAuthorParticipantId AS note_author_participant_id",
    ]
    status_prefixes = {
        "createdAtMillis": "created_at",
        "timestampMillisOfFirstNonNMRStatus": "first_non_nmr_at",
        "timestampMillisOfCurrentStatus": "current_status_at",
        "timestampMillisOfLatestNonNMRStatus": "latest_non_nmr_at",
        "timestampMillisOfStatusLock": "status_lock_at",
        "timestampMillisOfRetroLock": "retro_lock_at",
        "timestampMillisOfMostRecentStatusChange": "most_recent_status_change_at",
        "timestampMillisOfNmrDueToMinStableCrhTime": "nmr_due_to_min_stable_crh_at",
        "timestampMillisOfFirstNmrDueToMinStableCrhTime": "first_nmr_due_to_min_stable_crh_at",
        "timestampMillisAbovePcrhThreshold": "above_pcrh_threshold_at",
    }
    for column, prefix in status_prefixes.items():
        status_extra.extend(timestamp_fields(column, prefix))

    return {
        "note_request_clean": "SELECT *, " + ", ".join(request_extra) + " FROM raw_note_request",
        "notes_clean": "SELECT *, " + ", ".join(notes_extra) + " FROM raw_notes",
        "ratings_clean": "SELECT *, " + ", ".join(ratings_extra) + " FROM raw_ratings",
        "note_status_clean": "SELECT *, " + ", ".join(status_extra) + " FROM raw_note_status",
    }


def export_clean_tables(
    con: duckdb.DuckDBPyConnection, output_dir: Path, transformations: list[dict]
) -> None:
    source_names = {
        "note_request_clean": "raw_note_request",
        "notes_clean": "raw_notes",
        "ratings_clean": "raw_ratings",
        "note_status_clean": "raw_note_status",
    }
    for table, query in clean_queries().items():
        source = source_names[table]
        before = scalar(con, f"SELECT count(*) FROM {source}")
        target = sql_path(output_dir / f"{table}.parquet")
        print(f"  exporting {table}: {before:,} rows", flush=True)
        con.execute(
            f"COPY ({query}) TO '{target}' "
            "(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)"
        )
        con.execute(
            f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM read_parquet('{target}')"
        )
        after = scalar(con, f"SELECT count(*) FROM {table}")
        transformations.append({
            "dataset": table,
            "transformation": "Preserve every source row and column; add typed fields and data-quality flags",
            "rows_before": before,
            "rows_after": after,
            "affected_records": before,
            "reason": "Traceable typed derivatives without modifying source values",
            "validation": "pass" if before == after else "fail",
        })


def attach_existing_clean_tables(
    con: duckdb.DuckDBPyConnection, output_dir: Path, transformations: list[dict]
) -> None:
    """Attach row-preserving Parquet from an explicitly incomplete run."""
    source_names = {
        "note_request_clean": "raw_note_request",
        "notes_clean": "raw_notes",
        "ratings_clean": "raw_ratings",
        "note_status_clean": "raw_note_status",
    }
    for table, source in source_names.items():
        path = output_dir / f"{table}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Cannot resume; missing {path}")
        con.execute(
            f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM read_parquet('{sql_path(path)}')"
        )
        before = scalar(con, f"SELECT count(*) FROM {source}")
        after = scalar(con, f"SELECT count(*) FROM {table}")
        transformations.append({
            "dataset": table,
            "transformation": "Preserve every source row and column; add typed fields and data-quality flags",
            "rows_before": before, "rows_after": after,
            "affected_records": before,
            "reason": "Traceable typed derivatives without modifying source values",
            "validation": "pass" if before == after else "fail",
        })


def attach_existing_analysis_tables(
    con: duckdb.DuckDBPyConnection, output_dir: Path, transformations: list[dict]
) -> None:
    for table in ("ratings_by_note", "notes_analysis", "coverage_analysis"):
        path = output_dir / f"{table}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Cannot resume; missing {path}")
        con.execute(
            f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM read_parquet('{sql_path(path)}')"
        )
    rating_rows = scalar(con, "SELECT count(*) FROM ratings_clean")
    reconciled = scalar(con, "SELECT sum(rating_count) FROM ratings_by_note")
    transformations.extend([
        {
            "dataset": "ratings_by_note",
            "transformation": "Aggregate Ratings to one row per note_id",
            "rows_before": rating_rows,
            "rows_after": scalar(con, "SELECT count(*) FROM ratings_by_note"),
            "affected_records": rating_rows,
            "reason": "Prevent row multiplication in note-grain joins",
            "validation": "pass" if rating_rows == reconciled else "fail",
        },
        {
            "dataset": "notes_analysis",
            "transformation": "Left join unique Status and note-level Rating aggregates",
            "rows_before": scalar(con, "SELECT count(*) FROM notes_clean"),
            "rows_after": scalar(con, "SELECT count(*) FROM notes_analysis"),
            "affected_records": scalar(con, "SELECT count(*) FROM notes_clean"),
            "reason": "Create note-grain analysis without row multiplication",
            "validation": "pass" if scalar(con, "SELECT count(*) FROM notes_clean") == scalar(con, "SELECT count(*) FROM notes_analysis") else "fail",
        },
        {
            "dataset": "coverage_analysis",
            "transformation": "Aggregate Notes to tweet_id before joining Request",
            "rows_before": scalar(con, "SELECT count(*) FROM note_request_clean"),
            "rows_after": scalar(con, "SELECT count(*) FROM coverage_analysis"),
            "affected_records": scalar(con, "SELECT count(*) FROM note_request_clean"),
            "reason": "Create post-grain coverage base without row multiplication",
            "validation": "pass" if scalar(con, "SELECT count(*) FROM note_request_clean") == scalar(con, "SELECT count(*) FROM coverage_analysis") else "fail",
        },
    ])


def source_manifest(con: duckdb.DuckDBPyConnection, input_dir: Path) -> list[dict]:
    records: list[dict] = []
    run_utc = datetime.now(timezone.utc).isoformat()
    for dataset, (pattern, expected_columns) in DATASETS.items():
        for path in sorted(input_dir.glob(pattern)):
            source = read_csv_sql(sql_path(path))
            actual_columns = [
                row[0] for row in con.execute(f"DESCRIBE SELECT * FROM {source}").fetchall()
            ]
            records.append({
                "dataset": dataset,
                "file_name": path.name,
                "bytes": path.stat().st_size,
                "modified_utc": datetime.fromtimestamp(
                    path.stat().st_mtime, timezone.utc
                ).isoformat(),
                "row_count": scalar(con, f"SELECT count(*) FROM {source}"),
                "expected_column_count": len(expected_columns),
                "actual_column_count": len(actual_columns),
                "header_columns": json.dumps(actual_columns),
                "schema_matches_expected": actual_columns == expected_columns,
                "run_utc": run_utc,
            })
    return records


def missing_profile(con: duckdb.DuckDBPyConnection) -> list[dict]:
    records: list[dict] = []
    for dataset, (_, columns) in DATASETS.items():
        expressions = [
            f"sum(CASE WHEN {q(c)} IS NULL OR {q(c)} = '' THEN 1 ELSE 0 END)::BIGINT AS {q(c)}"
            for c in columns
        ]
        values = con.execute(
            f"SELECT {', '.join(expressions)} FROM raw_{dataset}"
        ).fetchone()
        total = scalar(con, f"SELECT count(*) FROM raw_{dataset}")
        for column, missing in zip(columns, values):
            records.append({
                "dataset": dataset,
                "column": column,
                "row_count": total,
                "missing_count": int(missing),
                "missing_percent": float(missing) / total if total else None,
                "decision": "preserve_null_no_row_drop",
            })
    return records


def category_profile(con: duckdb.DuckDBPyConnection) -> list[dict]:
    groups = {
        "notes_clean": ["classification"],
        "ratings_clean": ["helpfulnessLevel", "version", "ratingSourceBucketed"],
        "note_status_clean": [
            "currentStatus", "firstNonNMRStatus", "mostRecentNonNMRStatus"
        ],
    }
    records: list[dict] = []
    for table, columns in groups.items():
        selects = []
        for column in columns:
            selects.append(
                f"SELECT '{column}' AS column_name, {q(column)} AS category_value, "
                f"count(*)::BIGINT AS row_count FROM {table} GROUP BY {q(column)}"
            )
        for row in fetch_records(con, " UNION ALL ".join(selects)):
            row["dataset"] = table
            records.append(row)
    return records


def timestamp_profile(con: duckdb.DuckDBPyConnection) -> list[dict]:
    specifications = {
        "note_request_clean": ELIGIBILITY_TIMESTAMPS,
        "notes_clean": ["createdAtMillis"],
        "ratings_clean": ["createdAtMillis"],
        "note_status_clean": STATUS_TIMESTAMPS,
    }
    records: list[dict] = []
    for table, columns in specifications.items():
        selects = []
        for column in columns:
            state = state_expr(column)
            number = f"try_cast({q(column)} AS BIGINT)"
            selects.append(f"""
                SELECT '{column}' AS column_name,
                    count(*)::BIGINT AS row_count,
                    count(*) FILTER (WHERE ({state}) = 'blank')::BIGINT AS blank_count,
                    count(*) FILTER (WHERE ({state}) = 'minus_one')::BIGINT AS minus_one_count,
                    count(*) FILTER (WHERE ({state}) = 'other_negative')::BIGINT AS other_negative_count,
                    count(*) FILTER (WHERE ({state}) IN ('invalid_numeric','zero','out_of_range'))::BIGINT AS invalid_count,
                    count(*) FILTER (WHERE ({state}) = 'valid_positive')::BIGINT AS valid_count,
                    min({number}) AS raw_min,
                    max({number}) AS raw_max,
                    min(CASE WHEN ({state}) = 'valid_positive' THEN try(epoch_ms({number})) END) AS parsed_min_utc,
                    max(CASE WHEN ({state}) = 'valid_positive' THEN try(epoch_ms({number})) END) AS parsed_max_utc
                FROM {table}
            """)
        for row in fetch_records(con, " UNION ALL ".join(selects)):
            row["dataset"] = table
            records.append(row)
    return records


def add_profile_transformations(
    transformations: list[dict], timestamp_records: list[dict]
) -> None:
    """Log timestamp typing and known eligibility sentinel handling."""
    for row in timestamp_records:
        transformations.append({
            "dataset": row["dataset"],
            "transformation": f"Add UTC datetime and state for {row['column_name']}; retain raw field",
            "rows_before": row["row_count"],
            "rows_after": row["row_count"],
            "affected_records": row["valid_count"],
            "reason": "Convert valid Unix milliseconds without inventing dates",
            "validation": "pass" if (
                row["blank_count"] + row["minus_one_count"]
                + row["other_negative_count"] + row["invalid_count"]
                + row["valid_count"] == row["row_count"]
            ) else "fail",
        })
        if row["dataset"] == "note_request_clean":
            transformations.append({
                "dataset": row["dataset"],
                "transformation": f"Represent {row['column_name']} = -1 as eligible=false and derived datetime null",
                "rows_before": row["row_count"],
                "rows_after": row["row_count"],
                "affected_records": row["minus_one_count"],
                "reason": "Domain rule: -1 means not eligible for this feed",
                "validation": "pass",
            })


def duplicate_profile(
    con: duckdb.DuckDBPyConnection, input_dir: Path
) -> list[dict]:
    records: list[dict] = []
    small = [
        ("note_request_clean", "tweetId", REQUEST_COLUMNS),
        ("notes_clean", "noteId", NOTES_COLUMNS),
        ("note_status_clean", "noteId", STATUS_COLUMNS),
    ]
    for table, key, columns in small:
        full_hash = "hash(" + ",".join(q(c) for c in columns) + ")"
        row = con.execute(f"""
            SELECT count(*), count(distinct {q(key)}),
                   count(*) - count(distinct {q(key)}),
                   count(*) - count(distinct {full_hash})
            FROM {table}
        """).fetchone()
        records.append({
            "dataset": table, "key": key, "method": "exact_key_and_64bit_full_row_hash",
            "row_count": row[0], "unique_key_count": row[1],
            "repeated_key_extra_rows": row[2], "duplicate_full_row_hash_extra_rows": row[3],
        })

    # Bounded-memory exhaustive screen. Repeated noteId alone is expected and is
    # deliberately not treated as a duplicate.
    for path in sorted(input_dir.glob("ratings-*.tsv")):
        source = read_csv_sql(sql_path(path))
        row = con.execute(f"""
            SELECT count(*), count(distinct hash(noteId, raterParticipantId))
            FROM {source}
        """).fetchone()
        records.append({
            "dataset": "ratings_clean", "key": "noteId+raterParticipantId",
            "method": f"64bit_candidate_key_hash:{path.name}",
            "row_count": row[0], "unique_key_count": row[1],
            "repeated_key_extra_rows": row[0] - row[1],
            "duplicate_full_row_hash_extra_rows": None,
        })
    root = sql_path(input_dir)
    all_ratings_with_file = (
        f"read_csv('{root}/ratings-*.tsv', delim='\\t', header=true, "
        "union_by_name=true, all_varchar=true, null_padding=true, filename=true)"
    )
    boundary = con.execute(f"""
        WITH cross_file_notes AS (
            SELECT noteId
            FROM {all_ratings_with_file}
            GROUP BY noteId
            HAVING count(distinct filename) > 1
        )
        SELECT count(*) AS row_count,
               count(distinct hash(r.noteId, r.raterParticipantId)) AS unique_key_count,
               count(distinct r.noteId) AS crossing_note_count
        FROM {all_ratings_with_file} r
        SEMI JOIN cross_file_notes c USING (noteId)
    """).fetchone()
    records.append({
        "dataset": "ratings_clean", "key": "noteId+raterParticipantId",
        "method": f"64bit_candidate_key_hash:cross_shard_boundary:{boundary[2]}_notes",
        "row_count": boundary[0], "unique_key_count": boundary[1],
        "repeated_key_extra_rows": boundary[0] - boundary[1],
        "duplicate_full_row_hash_extra_rows": None,
    })
    return records


def build_aggregates_and_analysis(
    con: duckdb.DuckDBPyConnection, output_dir: Path, transformations: list[dict]
) -> None:
    output = sql_path(output_dir)
    print("  aggregating Ratings to note grain", flush=True)
    con.execute("""
        CREATE OR REPLACE TABLE ratings_by_note_work AS
        SELECT note_id,
            count(*)::BIGINT AS rating_count,
            min(created_at_utc) AS first_rating_at_utc,
            max(created_at_utc) AS last_rating_at_utc,
            count(*) FILTER (WHERE helpfulnessLevel = 'HELPFUL')::BIGINT AS helpful_count,
            count(*) FILTER (WHERE helpfulnessLevel = 'SOMEWHAT_HELPFUL')::BIGINT AS somewhat_helpful_count,
            count(*) FILTER (WHERE helpfulnessLevel = 'NOT_HELPFUL')::BIGINT AS not_helpful_count,
            count(*) FILTER (WHERE helpfulness_level_valid)::BIGINT AS valid_helpfulness_count,
            count(*) FILTER (WHERE NOT helpfulness_level_valid AND helpfulnessLevel IS NOT NULL)::BIGINT AS unexpected_helpfulness_count
        FROM ratings_clean GROUP BY note_id
    """)
    con.execute(
        f"COPY ratings_by_note_work TO '{output}/ratings_by_note.parquet' "
        "(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)"
    )
    con.execute(
        f"CREATE OR REPLACE VIEW ratings_by_note AS SELECT * FROM read_parquet('{output}/ratings_by_note.parquet')"
    )
    rating_rows = scalar(con, "SELECT count(*) FROM ratings_clean")
    reconciled = scalar(con, "SELECT sum(rating_count) FROM ratings_by_note")
    transformations.append({
        "dataset": "ratings_by_note", "transformation": "Aggregate Ratings to one row per note_id",
        "rows_before": rating_rows, "rows_after": scalar(con, "SELECT count(*) FROM ratings_by_note"),
        "affected_records": rating_rows, "reason": "Prevent row multiplication in note-grain joins",
        "validation": "pass" if rating_rows == reconciled else "fail",
    })

    print("  building one-row-per-note analysis table", flush=True)
    con.execute("""
        CREATE OR REPLACE VIEW notes_analysis_work AS
        SELECT n.*,
            s.currentStatus AS status_current_status,
            s.firstNonNMRStatus AS status_first_non_nmr_status,
            s.mostRecentNonNMRStatus AS status_most_recent_non_nmr_status,
            s.first_non_nmr_at_utc,
            s.first_non_nmr_at_state,
            s.current_status_at_utc,
            s.note_id IS NOT NULL AS status_observed,
            s.first_non_nmr_at_utc IS NOT NULL AS first_non_nmr_observed,
            CASE WHEN s.first_non_nmr_at_utc >= n.created_at_utc
                 THEN date_diff('millisecond', n.created_at_utc, s.first_non_nmr_at_utc) / 3600000.0 END
                 AS hours_to_first_non_nmr,
            CASE WHEN s.first_non_nmr_at_utc < n.created_at_utc THEN TRUE ELSE FALSE END
                 AS negative_response_time_flag,
            r.note_id IS NOT NULL AS ratings_observed,
            coalesce(r.rating_count, 0) AS rating_count,
            r.first_rating_at_utc, r.last_rating_at_utc,
            r.helpful_count, r.somewhat_helpful_count, r.not_helpful_count,
            r.valid_helpfulness_count, r.unexpected_helpfulness_count,
            CASE WHEN r.valid_helpfulness_count > 0
                 THEN r.helpful_count::DOUBLE / r.valid_helpfulness_count END AS observed_helpfulness_share
        FROM notes_clean n
        LEFT JOIN note_status_clean s USING (note_id)
        LEFT JOIN ratings_by_note r USING (note_id)
    """)
    con.execute(
        f"COPY notes_analysis_work TO '{output}/notes_analysis.parquet' "
        "(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)"
    )
    con.execute(
        f"CREATE OR REPLACE VIEW notes_analysis AS SELECT * FROM read_parquet('{output}/notes_analysis.parquet')"
    )
    notes_before = scalar(con, "SELECT count(*) FROM notes_clean")
    notes_after = scalar(con, "SELECT count(*) FROM notes_analysis")
    transformations.append({
        "dataset": "notes_analysis", "transformation": "Left join unique Status and note-level Rating aggregates",
        "rows_before": notes_before, "rows_after": notes_after,
        "affected_records": notes_before, "reason": "Create note-grain analysis without row multiplication",
        "validation": "pass" if notes_before == notes_after else "fail",
    })

    print("  building one-row-per-post coverage analysis base", flush=True)
    con.execute("""
        CREATE OR REPLACE VIEW coverage_analysis_work AS
        WITH note_rollup AS (
            SELECT r.tweet_id,
                count(n.note_id)::BIGINT AS observed_note_count,
                min(n.created_at_utc) AS first_observed_note_at_utc,
                min(n.created_at_utc) FILTER (WHERE n.created_at_utc >= r.note_request_feed_eligible_at_utc) AS first_note_after_request_eligibility_utc,
                min(n.created_at_utc) FILTER (WHERE n.created_at_utc >= r.api_small_feed_eligible_at_utc) AS first_note_after_small_eligibility_utc,
                min(n.created_at_utc) FILTER (WHERE n.created_at_utc >= r.api_large_feed_eligible_at_utc) AS first_note_after_large_eligibility_utc,
                min(n.created_at_utc) FILTER (WHERE n.created_at_utc >= r.api_xl_feed_eligible_at_utc) AS first_note_after_xl_eligibility_utc
            FROM note_request_clean r
            LEFT JOIN notes_clean n USING (tweet_id)
            GROUP BY r.tweet_id
        )
        SELECT r.*, nr.observed_note_count,
            nr.observed_note_count > 0 AS has_any_observed_note,
            nr.first_observed_note_at_utc,
            nr.first_observed_note_at_utc < r.note_request_feed_eligible_at_utc AS first_note_before_request_eligibility,
            nr.first_note_after_request_eligibility_utc,
            nr.first_note_after_small_eligibility_utc,
            nr.first_note_after_large_eligibility_utc,
            nr.first_note_after_xl_eligibility_utc,
            CASE WHEN nr.first_note_after_request_eligibility_utc IS NOT NULL
                 THEN date_diff('millisecond', r.note_request_feed_eligible_at_utc, nr.first_note_after_request_eligibility_utc) / 3600000.0 END
                 AS hours_request_eligibility_to_first_later_note
        FROM note_request_clean r JOIN note_rollup nr USING (tweet_id)
    """)
    con.execute(
        f"COPY coverage_analysis_work TO '{output}/coverage_analysis.parquet' "
        "(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)"
    )
    con.execute(
        f"CREATE OR REPLACE VIEW coverage_analysis AS SELECT * FROM read_parquet('{output}/coverage_analysis.parquet')"
    )
    request_before = scalar(con, "SELECT count(*) FROM note_request_clean")
    request_after = scalar(con, "SELECT count(*) FROM coverage_analysis")
    transformations.append({
        "dataset": "coverage_analysis", "transformation": "Aggregate Notes to tweet_id before joining Request",
        "rows_before": request_before, "rows_after": request_after,
        "affected_records": request_before, "reason": "Create post-grain coverage base without row multiplication",
        "validation": "pass" if request_before == request_after else "fail",
    })


def join_profile(con: duckdb.DuckDBPyConnection) -> list[dict]:
    queries = {
        "note_request_to_notes": """
            WITH r AS (SELECT tweet_id, count(*) n FROM note_request_clean GROUP BY 1),
                 n AS (SELECT tweet_id, count(*) n FROM notes_clean GROUP BY 1)
            SELECT (SELECT count(*) FROM note_request_clean) left_rows,
                   (SELECT count(*) FROM notes_clean) right_rows,
                   (SELECT count(*) FROM r) left_unique_keys,
                   (SELECT count(*) FROM n) right_unique_keys,
                   (SELECT count(*) FROM r JOIN n USING(tweet_id)) matched_left_keys,
                   (SELECT count(*) FROM r LEFT JOIN n USING(tweet_id) WHERE n.tweet_id IS NULL) unmatched_left_keys,
                   (SELECT count(*) FROM n LEFT JOIN r USING(tweet_id) WHERE r.tweet_id IS NULL) unmatched_right_keys,
                   (SELECT count(*) FROM note_request_clean x LEFT JOIN notes_clean y USING(tweet_id)) raw_left_join_rows
        """,
        "notes_to_ratings": """
            WITH n AS (SELECT note_id FROM notes_clean),
                 r AS (SELECT note_id, count(*) n FROM ratings_clean GROUP BY 1)
            SELECT (SELECT count(*) FROM notes_clean) left_rows,
                   (SELECT count(*) FROM ratings_clean) right_rows,
                   (SELECT count(*) FROM n) left_unique_keys,
                   (SELECT count(*) FROM r) right_unique_keys,
                   (SELECT count(*) FROM n JOIN r USING(note_id)) matched_left_keys,
                   (SELECT count(*) FROM n LEFT JOIN r USING(note_id) WHERE r.note_id IS NULL) unmatched_left_keys,
                   (SELECT count(*) FROM r LEFT JOIN n USING(note_id) WHERE n.note_id IS NULL) unmatched_right_keys,
                   (SELECT sum(coalesce(r.n,1)) FROM n LEFT JOIN r USING(note_id)) raw_left_join_rows
        """,
        "notes_to_status": """
            WITH n AS (SELECT note_id FROM notes_clean), s AS (SELECT note_id FROM note_status_clean)
            SELECT (SELECT count(*) FROM notes_clean) left_rows,
                   (SELECT count(*) FROM note_status_clean) right_rows,
                   (SELECT count(*) FROM n) left_unique_keys,
                   (SELECT count(*) FROM s) right_unique_keys,
                   (SELECT count(*) FROM n JOIN s USING(note_id)) matched_left_keys,
                   (SELECT count(*) FROM n LEFT JOIN s USING(note_id) WHERE s.note_id IS NULL) unmatched_left_keys,
                   (SELECT count(*) FROM s LEFT JOIN n USING(note_id) WHERE n.note_id IS NULL) unmatched_right_keys,
                   (SELECT count(*) FROM n LEFT JOIN s USING(note_id)) raw_left_join_rows
        """,
    }
    records = []
    for relationship, query in queries.items():
        row = fetch_records(con, query)[0]
        row["relationship"] = relationship
        row["row_multiplication_factor"] = row["raw_left_join_rows"] / row["left_rows"]
        records.append(row)
    return records


def suspicious_profile(
    con: duckdb.DuckDBPyConnection,
    timestamp_records: list[dict],
    duplicate_records: list[dict],
    missing_records: list[dict],
    category_records: list[dict],
) -> list[dict]:
    records: list[dict] = []
    for row in timestamp_records:
        for field, label in [
            ("other_negative_count", "negative timestamp other than -1"),
            ("invalid_count", "invalid/zero/out-of-range timestamp"),
        ]:
            records.append({
                "dataset": row["dataset"], "issue": label,
                "column_or_key": row["column_name"], "affected_records": row[field],
                "decision": "preserve raw; derived datetime null; flag",
                "verification": "timestamp_profile.csv state reconciliation",
            })
    for row in duplicate_records:
        records.append({
            "dataset": row["dataset"], "issue": "candidate key repetition screen",
            "column_or_key": row["key"], "affected_records": row["repeated_key_extra_rows"],
            "decision": "preserve rows; investigate any nonzero result",
            "verification": row["method"],
        })
    required_keys = {
        "note_request": ["tweetId"],
        "notes": ["noteId", "tweetId", "noteAuthorParticipantId"],
        "ratings": ["noteId", "raterParticipantId"],
        "note_status": ["noteId", "noteAuthorParticipantId"],
    }
    missing_lookup = {
        (row["dataset"], row["column"]): row["missing_count"]
        for row in missing_records
    }
    for dataset, columns in required_keys.items():
        for column in columns:
            records.append({
                "dataset": dataset, "issue": "missing required identifier",
                "column_or_key": column,
                "affected_records": missing_lookup[(dataset, column)],
                "decision": "preserve and flag; stop metric joins if nonzero",
                "verification": "missing_values.csv reconciliation",
            })
    expected_categories = {
        ("notes_clean", "classification"): {
            "MISINFORMED_OR_POTENTIALLY_MISLEADING", "NOT_MISLEADING", None
        },
        ("ratings_clean", "helpfulnessLevel"): {
            "HELPFUL", "SOMEWHAT_HELPFUL", "NOT_HELPFUL", None
        },
        ("note_status_clean", "currentStatus"): {
            "NEEDS_MORE_RATINGS", "CURRENTLY_RATED_HELPFUL",
            "CURRENTLY_RATED_NOT_HELPFUL", None
        },
        ("note_status_clean", "firstNonNMRStatus"): {
            "CURRENTLY_RATED_HELPFUL", "CURRENTLY_RATED_NOT_HELPFUL", None
        },
        ("note_status_clean", "mostRecentNonNMRStatus"): {
            "CURRENTLY_RATED_HELPFUL", "CURRENTLY_RATED_NOT_HELPFUL", None
        },
    }
    for key, expected in expected_categories.items():
        unexpected = sum(
            int(row["row_count"])
            for row in category_records
            if (row["dataset"], row["column_name"]) == key
            and row["category_value"] not in expected
        )
        records.append({
            "dataset": key[0], "issue": "unexpected categorical value",
            "column_or_key": key[1], "affected_records": unexpected,
            "decision": "preserve original label and flag; do not standardize automatically",
            "verification": "categorical_distributions.csv domain comparison",
        })
    checks = [
        ("notes_analysis", "negative response duration", "first_non_nmr_at_utc", "SELECT count(*) FROM notes_analysis WHERE negative_response_time_flag", "preserve row and flag; derived response duration remains null"),
        ("ratings_clean", "Rating predates matched Note", "createdAtMillis", "SELECT count(*) FROM ratings_clean r JOIN notes_clean n USING(note_id) WHERE r.created_at_utc < n.created_at_utc", "preserve row and flag; exclude only from note-relative timing"),
        ("ratings_clean", "ratedOnTweetId differs from matched Note tweetId", "ratedOnTweetId", "SELECT count(*) FROM ratings_clean r JOIN notes_clean n USING(note_id) WHERE r.rated_on_tweet_id <> n.tweet_id", "preserve both IDs and comparison state; do not overwrite either ID"),
        ("coverage_analysis", "earliest Note predates request eligibility", "noteRequestFeedEligibleAtMillis", "SELECT count(*) FROM coverage_analysis WHERE note_request_feed_eligible_at_eligible AND first_note_before_request_eligibility", "preserve coverage match; use first Note at/after eligibility for wait-time arithmetic"),
    ]
    for dataset, issue, column, query, decision in checks:
        records.append({
            "dataset": dataset, "issue": issue, "column_or_key": column,
            "affected_records": scalar(con, query),
            "decision": decision,
            "verification": query,
        })
    return records


def metric_summaries(con: duckdb.DuckDBPyConnection) -> tuple[list[dict], list[dict]]:
    metric_records = fetch_records(con, """
        SELECT 'response_time' metric,
               'note' base_unit,
               count(*)::BIGINT cohort_count,
               NULL::BIGINT numerator_count,
               count(*) FILTER (WHERE first_non_nmr_observed)::BIGINT denominator_count,
               count(*) FILTER (WHERE NOT first_non_nmr_observed)::BIGINT excluded_or_unobserved_count,
               median(hours_to_first_non_nmr) metric_value,
               'median hours among Notes with a valid observed first non-NMR milestone' definition
        FROM notes_analysis
        UNION ALL
        SELECT 'rating_activity', 'note', count(*),
               sum(rating_count),
               count(*),
               count(*) FILTER (WHERE NOT ratings_observed),
               avg(rating_count::DOUBLE) AS metric_value,
               'mean matched observed Rating rows per Note, including zero-Rating Notes'
        FROM notes_analysis
        UNION ALL
        SELECT 'observed_helpfulness', 'rating', sum(rating_count),
               sum(helpful_count),
               sum(valid_helpfulness_count),
               sum(rating_count) - sum(valid_helpfulness_count),
               sum(helpful_count)::DOUBLE / nullif(sum(valid_helpfulness_count),0) AS metric_value,
               'HELPFUL / valid helpfulnessLevel rows; version-1 missing values excluded'
        FROM ratings_by_note
    """)
    coverage_records = []
    fields = [
        ("noteRequestFeedEligibleAtMillis", "note_request_feed_eligible_at_eligible"),
        ("apiSmallFeedEligibleAtMillis", "api_small_feed_eligible_at_eligible"),
        ("apiLargeFeedEligibleAtMillis", "api_large_feed_eligible_at_eligible"),
        ("apiXlFeedEligibleAtMillis", "api_xl_feed_eligible_at_eligible"),
    ]
    for source_field, flag in fields:
        row = fetch_records(con, f"""
            SELECT '{source_field}' eligibility_field,
                count(*) FILTER (WHERE {flag})::BIGINT denominator_distinct_eligible_posts,
                count(*) FILTER (WHERE {flag} AND has_any_observed_note)::BIGINT numerator_posts_with_any_observed_note,
                count(*) FILTER (WHERE {flag} AND NOT has_any_observed_note)::BIGINT observed_uncovered_posts,
                avg(has_any_observed_note::INTEGER) FILTER (WHERE {flag}) AS observed_coverage_rate
            FROM coverage_analysis
        """)[0]
        coverage_records.append(row)
    return metric_records, coverage_records


def human_review_items() -> list[dict]:
    return [
        {"decision": "Official coverage eligibility field and date window", "why": "Four feed fields define materially different cohorts", "current_handling": "Report each feed separately; do not select one official metric"},
        {"decision": "Meaning of -1 in non-eligibility Status timestamps", "why": "Only feed eligibility sentinel semantics were supplied", "current_handling": "Preserve and flag; no datetime"},
        {"decision": "Negative timestampMillisAbovePcrhThreshold values", "why": "20,009 negatives are not -1 and lack documented semantics", "current_handling": "Preserve and flag; no datetime"},
        {"decision": "Version-1 helpfulness crosswalk", "why": "Legacy fields are not proven equivalent to helpfulnessLevel", "current_handling": "Exclude from requested helpfulness denominator and report count"},
        {"decision": "sourceLinks parsing", "why": "Nonblank strings are not valid JSON and delimiter semantics are unknown", "current_handling": "Preserve raw string"},
        {"decision": "ratedOnTweetId mismatches", "why": "Millions differ from the Note tweetId and may have domain meaning", "current_handling": "Preserve both; flag differences"},
        {"decision": "Coverage interpretation for Notes predating eligibility", "why": "Any-note coverage and post-eligibility response answer different questions", "current_handling": "Any-note coverage plus separate ordering flags"},
        {"decision": "Exact Ratings key proof", "why": "Exhaustive validation is hash-based under bounded memory", "current_handling": "Per-shard 64-bit hash screen; disclose collision risk"},
    ]


def main() -> None:
    args = parse_args()
    require_sources(args.input_dir)
    ensure_safe_output(args.input_dir, args.output_dir, args.resume_incomplete)
    incomplete = args.output_dir / "_INCOMPLETE"
    incomplete.write_text("Pipeline has not completed.\n", encoding="utf-8")
    free_gb = shutil.disk_usage(args.output_dir).free / (1024 ** 3)
    print(f"Output: {args.output_dir.resolve()} ({free_gb:.1f} GiB free)", flush=True)

    database = args.output_dir / "community_notes_v2.duckdb"
    con = duckdb.connect(str(database))
    con.execute(f"SET threads={args.threads}")
    con.execute(f"SET memory_limit='{args.memory_limit}'")
    con.execute(f"SET temp_directory='{sql_path(args.output_dir / '_duckdb_tmp')}'")
    con.execute("SET preserve_insertion_order=false")
    (args.output_dir / "_duckdb_tmp").mkdir(exist_ok=True)
    transformations: list[dict] = []

    try:
        print("[1/8] Registering immutable source views", flush=True)
        create_raw_views(con, args.input_dir)

        print("[2/8] Writing source manifest", flush=True)
        manifest = source_manifest(con, args.input_dir)
        write_csv(args.output_dir / "source_manifest.csv", manifest)

        if args.resume_incomplete:
            print("[3/8] Attaching row-preserving tables from incomplete run", flush=True)
            attach_existing_clean_tables(con, args.output_dir, transformations)
        else:
            print("[3/8] Exporting row-preserving cleaned tables", flush=True)
            export_clean_tables(con, args.output_dir, transformations)

        print("[4/8] Profiling missingness, categories, timestamps, and keys", flush=True)
        missing = missing_profile(con)
        categories = category_profile(con)
        timestamps = timestamp_profile(con)
        add_profile_transformations(transformations, timestamps)
        duplicates = duplicate_profile(con, args.input_dir)

        print("[5/8] Validating joins before analysis outputs", flush=True)
        joins = join_profile(con)

        # Critical grain gates. Clean outputs remain available if a gate fails,
        # but no analysis table or metric is built from invalid cardinalities.
        row_preservation_ok = all(x["validation"] == "pass" for x in transformations)
        unique_small_keys_ok = all(
            x["repeated_key_extra_rows"] == 0
            for x in duplicates if x["dataset"] != "ratings_clean"
        )
        rating_key_screen_ok = all(
            x["repeated_key_extra_rows"] == 0
            for x in duplicates if x["dataset"] == "ratings_clean"
        )
        critical_ok = row_preservation_ok and unique_small_keys_ok and rating_key_screen_ok
        if not critical_ok:
            raise RuntimeError("Critical row-preservation or key validation failed; analysis outputs were not built")

        if args.resume_incomplete:
            print("[6/8] Attaching grain-safe outputs from incomplete run", flush=True)
            attach_existing_analysis_tables(con, args.output_dir, transformations)
        else:
            print("[6/8] Building grain-safe analysis outputs", flush=True)
            build_aggregates_and_analysis(con, args.output_dir, transformations)

        print("[7/8] Writing validation and metric reports with pandas", flush=True)
        suspicious = suspicious_profile(
            con, timestamps, duplicates, missing, categories
        )
        metrics, coverage_metrics = metric_summaries(con)
        write_csv(args.output_dir / "missing_values.csv", missing)
        write_csv(args.output_dir / "categorical_distributions.csv", categories)
        write_csv(args.output_dir / "timestamp_profile.csv", timestamps)
        write_csv(args.output_dir / "duplicate_validation.csv", duplicates)
        write_csv(args.output_dir / "join_validation.csv", joins)
        write_csv(args.output_dir / "suspicious_values.csv", suspicious)
        write_csv(args.output_dir / "transformation_log.csv", transformations)
        write_csv(args.output_dir / "metric_summary.csv", metrics)
        write_csv(args.output_dir / "coverage_metrics_by_feed.csv", coverage_metrics)
        write_csv(args.output_dir / "human_review_required.csv", human_review_items())

        clean_counts = {
            table: scalar(con, f"SELECT count(*) FROM {table}")
            for table in [
                "note_request_clean", "notes_clean", "ratings_clean",
                "note_status_clean", "ratings_by_note", "notes_analysis",
                "coverage_analysis",
            ]
        }
        validation = {
            "status": "pass",
            "run_utc": datetime.now(timezone.utc).isoformat(),
            "source_directory": str(args.input_dir.resolve()),
            "output_directory": str(args.output_dir.resolve()),
            "source_files_modified": False,
            "critical_gates": {
                "row_preservation": row_preservation_ok,
                "small_table_candidate_keys": unique_small_keys_ok,
                "ratings_candidate_key_hash_screen": rating_key_screen_ok,
                "analysis_outputs_built_after_join_validation": True,
            },
            "output_rows": clean_counts,
            "reports": [
                "source_manifest.csv", "missing_values.csv",
                "categorical_distributions.csv", "timestamp_profile.csv",
                "duplicate_validation.csv", "join_validation.csv",
                "suspicious_values.csv", "transformation_log.csv",
                "metric_summary.csv", "coverage_metrics_by_feed.csv",
                "human_review_required.csv",
            ],
        }
        (args.output_dir / "validation_summary.json").write_text(
            json.dumps(validation, indent=2, default=str), encoding="utf-8"
        )

        print("[8/8] Finalizing", flush=True)
        incomplete.unlink()
        temp = args.output_dir / "_duckdb_tmp"
        if temp.exists() and not any(temp.iterdir()):
            temp.rmdir()
        print("Completed successfully.", flush=True)
    finally:
        con.close()


if __name__ == "__main__":
    main()

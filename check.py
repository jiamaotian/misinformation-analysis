import hashlib
import json
import platform
from pathlib import Path

import pandas as pd
import response_ratings_analysis as backend


def show(label, value):
    print(
        f"{label}: "
        + json.dumps(value, ensure_ascii=False, sort_keys=True)
    )


def check_error(label, operation):
    try:
        operation()
    except ValueError as error:
        show(label, str(error))
    else:
        raise AssertionError(f"{label}: expected ValueError")


def main():
    # 1. Known helpfulness counts: 7 / 1 / 2 valid, 3 invalid.
    notes = pd.DataFrame({
        "noteId": ["1", "2"],
        "classification": ["MISLEADING", "NOT_MISLEADING"],
        "createdAtMillis": [1_000_000, 1_000_000],
    })

    ratings = pd.DataFrame({
        "noteId": ["1"] * 13,
        "raterParticipantId": [f"p{i}" for i in range(13)],
        "helpfulnessLevel": (
            ["HELPFUL"] * 7
            + ["SOMEWHAT_HELPFUL"]
            + ["NOT_HELPFUL"] * 2
            + ["UNKNOWN", "", None]
        ),
    })

    result = backend.calculate_helpfulness(ratings, notes)
    counts = result["helpfulnessLevel"].value_counts().to_dict()

    assert counts == {
        "HELPFUL": 7,
        "SOMEWHAT_HELPFUL": 1,
        "NOT_HELPFUL": 2,
    }
    assert len(result) == 10
    assert len(ratings) - len(result) == 3

    # Independent arithmetic, based on the fixture's known counts.
    expected_share = 7 / (7 + 1 + 2)
    actual_share = result["helpfulnessLevel"].eq("HELPFUL").mean()
    assert abs(actual_share - expected_share) < 1e-12

    summary = backend.summarize_helpfulness(result)
    assert abs(summary["rating_share"].sum() - 1) < 1e-12

    show("valid_counts", counts)
    show("invalid_levels_excluded", len(ratings) - len(result))
    show("helpful_share", float(actual_share))
    show("summary", summary.to_dict("records"))

    # 2. Conflicting participant-note duplicate and unmatched note ID.
    expanded = pd.concat([
        ratings,
        pd.DataFrame({
            "noteId": ["1", "999"],
            "raterParticipantId": ["p0", "unmatched"],
            "helpfulnessLevel": ["NOT_HELPFUL", "HELPFUL"],
        }),
    ], ignore_index=True)

    matched = backend.calculate_helpfulness(expanded, notes)
    activity = backend.calculate_rating_activity(notes, expanded)

    assert len(matched) == 10
    assert matched["helpfulnessLevel"].eq("HELPFUL").sum() == 7
    assert not matched["noteId"].eq("999").any()
    assert matched.loc[
        matched["raterParticipantId"].eq("p0"),
        "helpfulnessLevel",
    ].tolist() == ["HELPFUL"]
    assert activity["rating_count"].tolist() == [10, 0]

    show("duplicate_and_unmatched", {
        "input_rows": len(expanded),
        "valid_before_join": len(backend._valid_ratings(expanded)),
        "matched_rows": len(matched),
        "kept_p0": matched.loc[
            matched["raterParticipantId"].eq("p0"),
            "helpfulnessLevel",
        ].tolist(),
        "activity": activity.to_dict("records"),
    })

    duplicate_notes = pd.concat(
        [notes, notes.iloc[[0]]], ignore_index=True
    )

    check_error(
        "duplicate_notes_helpfulness",
        lambda: backend.calculate_helpfulness(ratings, duplicate_notes),
    )
    check_error(
        "duplicate_notes_activity",
        lambda: backend.calculate_rating_activity(
            duplicate_notes, ratings
        ),
    )

    # 3. Seven-day counterexample.
    hour = 3_600_000
    day = 24 * hour
    origin = 1_700_000_000_000
    cutoff = origin + 10 * day
    window = 7 * day

    window_notes = pd.DataFrame({
        "noteId": ["1", "2", "3", "4", "5", "6"],
        "classification": ["TEST"] * 6,
        "createdAtMillis": [origin] * 5 + [origin + 6 * day],
    })

    status = pd.DataFrame({
        "noteId": ["1", "2", "3", "4", "6", "999"],
        "timestampMillisOfFirstNonNMRStatus": [
            origin + 2 * hour,
            origin + 10 * hour,
            origin + 30 * hour,
            origin + 8 * day,
            origin + 6 * day + hour,
            origin + hour,
        ],
        "firstNonNMRStatus": ["CURRENTLY_RATED_HELPFUL"] * 6,
    })

    response = backend.calculate_response_time(
        window_notes, status, cutoff_ms=cutoff
    )

    observed_hours = [
        None if pd.isna(value) else float(value)
        for value in response["response_time_hours"]
    ]

    assert observed_hours == [2.0, 10.0, 30.0, 192.0, None, 1.0]
    assert response["response_time_hours"].count() == 5
    assert response["response_time_hours"].median() == 10.0

    show("window_backend_hours", observed_hours)
    show(
        "window_backend_summary",
        backend.summarize_response_time(response).to_dict("records"),
    )

    # Independent seven-day calculation using integer comparisons.
    # This section does not use backend filtering or summary helpers.
    creation = dict(zip(
        window_notes["noteId"],
        window_notes["createdAtMillis"],
    ))
    transitions = dict(zip(
        status["noteId"],
        status["timestampMillisOfFirstNonNMRStatus"],
    ))

    mature_ids = [
        note_id
        for note_id, created in creation.items()
        if created + window <= cutoff
    ]

    completed_hours = [
        (transitions[note_id] - creation[note_id]) / hour
        for note_id in mature_ids
        if (
            note_id in transitions
            and creation[note_id] <= transitions[note_id]
            <= creation[note_id] + window
        )
    ]

    assert mature_ids == ["1", "2", "3", "4", "5"]
    assert sorted(completed_hours) == [2.0, 10.0, 30.0]

    show("independent_7day", {
        "eligible": len(mature_ids),
        "completed": len(completed_hours),
        "without_transition_within_window": (
            len(mature_ids) - len(completed_hours)
        ),
        "completion_rate": len(completed_hours) / len(mature_ids),
        "median_hours": sorted(completed_hours)[1],
        "excluded_immature": len(window_notes) - len(mature_ids),
    })

    # 4. Duplicate and unmatched Notes/Status IDs.
    check_error(
        "duplicate_notes_response",
        lambda: backend.calculate_response_time(
            pd.concat(
                [window_notes, window_notes.iloc[[0]]],
                ignore_index=True,
            ),
            status,
        ),
    )

    check_error(
        "duplicate_status",
        lambda: backend.calculate_response_time(
            window_notes,
            pd.concat(
                [status, status.iloc[[0]]], ignore_index=True
            ),
        ),
    )

    assert response["noteId"].tolist() == window_notes["noteId"].tolist()
    assert not response["noteId"].eq("999").any()
    assert response.loc[
        response["noteId"].eq("5"), "response_time_hours"
    ].isna().all()

    show("unmatched_status", {
        "status_only_999_in_output": bool(
            response["noteId"].eq("999").any()
        ),
        "note_5_hours": None,
    })

    # 5. Exactly-at-seven-days boundary.
    boundary_status = status.iloc[[0]].copy()
    boundary_status["timestampMillisOfFirstNonNMRStatus"] = (
        origin + window
    )

    boundary_result = backend.calculate_response_time(
        window_notes.iloc[[0]],
        boundary_status,
        cutoff_ms=origin + window,
    )

    assert boundary_result["response_time_hours"].iloc[0] == 168.0
    show("boundary_7_days_hours", 168)

    # 6. Empty valid-rating denominator.
    empty_status = pd.DataFrame({
        "noteId": [],
        "timestampMillisOfFirstNonNMRStatus": [],
        "firstNonNMRStatus": [],
    })

    empty_result = backend.build_dashboard_data(
        notes, ratings.iloc[0:0], empty_status
    )

    assert pd.isna(empty_result["observed_helpful_share"])
    show("empty_helpful_share", "NaN")

    show("runtime", {
        "python": platform.python_version(),
        "pandas": pd.__version__,
    })
    show(
        "source_sha256",
        hashlib.sha256(
            Path(backend.__file__).read_bytes()
        ).hexdigest(),
    )

    print("ALL INDEPENDENT ASSERTIONS PASSED")


if __name__ == "__main__":
    main()
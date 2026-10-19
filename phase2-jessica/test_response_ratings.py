
"""
Jessica - Phase 2 Backend Tests
DSO 576: Community Notes Misinformation Dashboard

Tests:
1. Response time calculations
2. Rating activity counts
3. Observed helpfulness distribution
4. Missing status and zero-rating notes
5. Duplicate note IDs
6. Invalid helpfulness values
7. Compatibility with Yoojin's cleaning flags

Run:
    python phase2-jessica/test_response_ratings.py
"""

import pandas as pd

from response_ratings_analysis import (
    calculate_response_time,
    summarize_response_time,
    calculate_rating_activity,
    prepare_activity_scatter,
    calculate_helpfulness,
    summarize_helpfulness,
    build_dashboard_data,
)


def create_test_data():
    """Create small, controlled datasets with known expected results."""

    notes = pd.DataFrame({
        "noteId": ["1", "2", "3", "4"],
        "createdAtMillis": [
            1_000_000,
            2_000_000,
            3_000_000,
            4_000_000,
        ],
        "classification": [
            "MISINFORMED_OR_POTENTIALLY_MISLEADING",
            "MISINFORMED_OR_POTENTIALLY_MISLEADING",
            "NOT_MISLEADING",
            "NOT_MISLEADING",
        ],
    })

    ratings = pd.DataFrame({
        "noteId": ["1", "1", "2", "3", "3"],
        "raterParticipantId": ["A", "B", "C", "D", "E"],
        "helpfulnessLevel": [
            "HELPFUL",
            "NOT_HELPFUL",
            "HELPFUL",
            "SOMEWHAT_HELPFUL",
            "HELPFUL",
        ],
    })

    status = pd.DataFrame({
        "noteId": ["1", "2", "3", "4"],
        "timestampMillisOfFirstNonNMRStatus": [
            8_200_000,   # Note 1: 2 hours
            16_400_000,  # Note 2: 4 hours
            21_000_000,  # Note 3: 5 hours
            "",          # Note 4: unresolved
        ],
        "firstNonNMRStatus": [
            "CURRENTLY_RATED_HELPFUL",
            "CURRENTLY_RATED_NOT_HELPFUL",
            "CURRENTLY_RATED_HELPFUL",
            "",
        ],
    })

    return notes, ratings, status


def test_response_time():
    notes, ratings, status = create_test_data()

    result = calculate_response_time(notes, status)

    times = result.set_index("noteId")["response_time_hours"]

    assert times["1"] == 2.0
    assert times["2"] == 4.0
    assert times["3"] == 5.0
    assert pd.isna(times["4"])

    summary = summarize_response_time(result)

    assert len(summary) == 2

    print("PASS: Response time calculations")


def test_rating_activity():
    notes, ratings, status = create_test_data()

    activity = calculate_rating_activity(notes, ratings)

    counts = activity.set_index("noteId")["rating_count"]

    assert counts["1"] == 2
    assert counts["2"] == 1
    assert counts["3"] == 2
    assert counts["4"] == 0

    print("PASS: Rating activity calculations")


def test_helpfulness():
    notes, ratings, status = create_test_data()

    helpfulness = calculate_helpfulness(ratings, notes)
    summary = summarize_helpfulness(helpfulness)

    assert len(helpfulness) == 5

    helpful = helpfulness[
        helpfulness["helpfulnessLevel"] == "HELPFUL"
    ]

    assert len(helpful) == 3

    overall_share = (
        helpfulness["helpfulnessLevel"] == "HELPFUL"
    ).mean()

    assert abs(overall_share - 0.6) < 1e-9

    for classification, group in summary.groupby("classification"):
        assert abs(group["rating_share"].sum() - 1.0) < 1e-9

    print("PASS: Observed helpfulness calculations")


def test_missing_status():
    notes, ratings, status = create_test_data()

    result = calculate_response_time(notes, status)

    unresolved = result[result["noteId"] == "4"]

    assert unresolved["response_time_hours"].isna().all()

    print("PASS: Missing status handling")


def test_duplicate_note_ids():
    notes, ratings, status = create_test_data()

    duplicate_notes = pd.concat(
        [notes, notes.iloc[[0]]],
        ignore_index=True,
    )

    try:
        calculate_response_time(duplicate_notes, status)
    except ValueError:
        print("PASS: Duplicate noteId detection")
        return

    raise AssertionError(
        "Duplicate noteId should raise ValueError"
    )


def test_invalid_ratings():
    notes, ratings, status = create_test_data()

    invalid_rating = pd.DataFrame({
        "noteId": ["1"],
        "raterParticipantId": ["INVALID"],
        "helpfulnessLevel": ["UNKNOWN"],
    })

    modified_ratings = pd.concat(
        [ratings, invalid_rating],
        ignore_index=True,
    )

    helpfulness = calculate_helpfulness(modified_ratings, notes)

    assert len(helpfulness) == 5

    print("PASS: Invalid rating exclusion")


def test_cleaning_flags():
    """Verify compatibility with Yoojin's cleaned-data flags."""

    notes, ratings, status = create_test_data()

    ratings["qc_valid_helpfulness"] = [
        True, True, False, True, True
    ]

    status["qc_response_eligible"] = [
        True, True, False, False
    ]

    helpfulness = calculate_helpfulness(ratings, notes)

    assert len(helpfulness) == 4

    response = calculate_response_time(notes, status)

    times = response.set_index("noteId")["response_time_hours"]

    assert times["1"] == 2.0
    assert times["2"] == 4.0
    assert pd.isna(times["3"])
    assert pd.isna(times["4"])

    print("PASS: Cleaning flag compatibility")


def test_activity_scatter():
    notes, ratings, status = create_test_data()

    response = calculate_response_time(notes, status)
    activity = calculate_rating_activity(notes, ratings)

    scatter = prepare_activity_scatter(response, activity)

    assert len(scatter) == 4

    assert "response_time_hours" in scatter.columns
    assert "rating_count" in scatter.columns
    assert "classification" in scatter.columns

    print("PASS: Scatterplot dataset")


def test_full_dashboard_output():
    notes, ratings, status = create_test_data()

    results = build_dashboard_data(notes, ratings, status)

    expected_keys = {
        "median_response_hours",
        "observed_helpful_share",
        "response_summary",
        "rating_activity",
        "activity_vs_response",
        "helpfulness_summary",
    }

    assert expected_keys.issubset(results.keys())

    assert results["median_response_hours"] == 4.0
    assert abs(results["observed_helpful_share"] - 0.6) < 1e-9

    print("PASS: Full dashboard backend output")


def run_all_tests():
    print("=" * 50)
    print("Jessica - Phase 2 Backend Tests")
    print("=" * 50)

    test_response_time()
    test_rating_activity()
    test_helpfulness()
    test_missing_status()
    test_duplicate_note_ids()
    test_invalid_ratings()
    test_cleaning_flags()
    test_activity_scatter()
    test_full_dashboard_output()

    print("=" * 50)
    print("ALL 9 TESTS PASSED!")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()


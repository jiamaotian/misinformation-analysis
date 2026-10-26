from pathlib import Path
import sys
import pandas as pd

sys.path.insert(0, str((Path(__file__).resolve().parent / "phase2-euan").resolve()))
from coverage_analysis import analyze_coverage


def ms(iso_time):
    return str(int(pd.Timestamp(iso_time).timestamp() * 1000))

requests = pd.DataFrame({
    "tweetId": ["101", "102", "103", "104", "105", "106"],
    "noteRequestFeedEligibleAtMillis": [
        ms("2026-10-01T00:00:00Z"), ms("2026-10-02T00:00:00Z"), "-1",
        ms("2026-10-07T00:00:00Z"), ms("2026-09-30T00:00:00Z"), ms("2026-10-03T00:00:00Z")
    ],
    "apiSmallFeedEligibleAtMillis": [
        "-1", ms("2026-10-02T00:00:00Z"), ms("2026-10-04T00:00:00Z"),
        ms("2026-10-07T00:00:00Z"), "-1", "-1"
    ],
    "apiLargeFeedEligibleAtMillis": ["-1"] * 6,
    "apiXlFeedEligibleAtMillis": [
        ms("2026-10-01T00:00:00Z"), "-1", "-1", "-1", "-1",
        ms("2026-10-03T00:00:00Z")
    ],
})
notes = pd.DataFrame({
    "tweetId": pd.Series(dtype="string"),
    "noteId": pd.Series(dtype="string"),
    "createdAtMillis": pd.Series(dtype="string"),
})

expected = {
    "Standard": {"101", "102", "106"},
    "Small": {"102"},
    "Large": set(),
    "XL": {"101", "106"},
}

for feed, expected_ids in expected.items():
    result = analyze_coverage(
        requests, notes,
        feed=feed,
        start="2026-10-01T00:00:00Z",
        end="2026-10-08T00:00:00Z",
        window_days=7,
        cutoff="2026-10-10T00:00:00Z",
    )
    actual_ids = set(result["requests"]["tweetId"])
    actual_count = result["summary"]["eligible_requests"]
    print(feed, "expected:", len(expected_ids), "actual:", actual_count,
          "IDs:", sorted(actual_ids))
    assert actual_ids == expected_ids
    assert actual_count == len(expected_ids)
print("All four feed checks passed.")
"""Small, saved Phase 2 tables used by the local dashboard."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
FILES = {
    "coverage": "phase2-euan/results/latest28/coverage_requests.csv",
    "coverage_meta": "phase2-euan/results/latest28/coverage_summary.json",
    "response": "phase2-jessica/results/activity_vs_response.csv",
    "helpfulness": "phase2-jessica/results/helpfulness_summary.csv",
    "response_meta": "phase2-jessica/results/metrics_summary.json",
}


def fingerprint():
    return tuple((name, (ROOT / path).stat().st_mtime_ns,
                  (ROOT / path).stat().st_size) for name, path in FILES.items())


def load_data():
    result = {}
    for name, path in FILES.items():
        source = ROOT / path
        result[name] = (json.loads(source.read_text()) if source.suffix == ".json"
                        else pd.read_csv(source, dtype={"noteId": "string", "tweetId": "string"}))
    coverage = result["coverage"]
    for col in ("eligibility_utc", "eligibility_week_utc"):
        coverage[col] = pd.to_datetime(coverage[col], utc=True, format="ISO8601", errors="raise")
    values = coverage["covered"].astype(str).str.lower()
    if not values.isin(["true", "false"]).all():
        raise ValueError("Coverage contains invalid covered flags")
    coverage["covered"] = values.eq("true")
    for name in ("response", "helpfulness"):
        result[name]["classification"] = result[name]["classification"].fillna("Unknown")
    return result


def weekly_coverage(frame):
    out = frame.groupby("eligibility_week_utc").agg(
        eligible_requests=("covered", "size"), covered_requests=("covered", "sum")
    ).reset_index()
    out["no_observed_note"] = out.eligible_requests - out.covered_requests
    out["coverage_percent"] = 100 * out.covered_requests / out.eligible_requests
    return out


def response_summary(frame):
    return frame.groupby("classification").agg(
        notes=("noteId", "size"), recorded_events=("response_time_hours", "count"),
        median_hours=("response_time_hours", "median")
    ).reset_index()


def export_csv(frame, **metadata):
    result = frame.copy()
    for key, value in metadata.items():
        result[key] = value
    return result.to_csv(index=False).encode("utf-8")

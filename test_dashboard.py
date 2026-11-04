import io
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from dashboard_data import export_csv, load_data, weekly_coverage


def test_coverage_counts_and_export():
    frame = pd.DataFrame({"eligibility_week_utc": pd.to_datetime(["2026-01-05"] * 10, utc=True),
                          "covered": [True] * 4 + [False] * 6})
    result = weekly_coverage(frame)
    assert result.iloc[0].coverage_percent == 40
    assert result.iloc[0].no_observed_note == 6
    exported = pd.read_csv(io.BytesIO(export_csv(result, selected_week="2026-01-05")))
    assert exported.iloc[0].selected_week == "2026-01-05"
    assert exported.iloc[0].covered_requests == 4
    assert weekly_coverage(frame.iloc[:0]).empty


def test_saved_counts_reconcile():
    data = load_data()
    assert len(data["coverage"]) == data["coverage_meta"]["eligible_requests"]
    assert data["coverage"].covered.sum() == data["coverage_meta"]["covered_requests"]
    assert len(data["response"]) == data["response_meta"]["notes_in_cohort"]


def test_app_opens_directly_to_dashboard():
    app = AppTest.from_file(str(Path(__file__).with_name("dashboard.py"))).run(timeout=30)
    assert not app.exception
    assert not app.sidebar.radio
    assert app.title[0].value == "Community Notes • Coverage & Response"

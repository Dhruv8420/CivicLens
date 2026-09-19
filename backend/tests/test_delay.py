"""
Unit tests for CivicLens Delay Detector.

Tests cover:
1.  Clearly delayed In Progress project
2.  Clearly delayed Stalled project
3.  Completed project after deadline is NOT flagged
4.  In Progress project before deadline is NOT flagged
5.  Planning project after deadline is NOT flagged
6.  Missing revised completion date
7.  Invalid date handling
8.  Exact deadline boundary
9.  days_delayed calculation
10. severity range 0.0-1.0
11. required result fields
12. detector name
13. full 100-row dataset runs successfully
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from app.engine.detectors.delay import detect, detect_flagged, _parse_date


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_row(pid: str, revised_date, status: str) -> dict:
    return {
        "project_id": pid,
        "revised_completion_date": revised_date,
        "status": status,
    }


REF_DATE = date(2026, 9, 18)  # fixed reference for deterministic tests


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def delayed_df() -> pd.DataFrame:
    """Projects that should be flagged as delayed."""
    return pd.DataFrame([
        # In Progress, deadline 200 days ago
        _make_row("D-001", "2026-03-01", "In Progress"),
        # Stalled, deadline 100 days ago
        _make_row("D-002", "2026-06-10", "Stalled"),
    ])


@pytest.fixture
def not_delayed_df() -> pd.DataFrame:
    """Projects that should NOT be flagged."""
    return pd.DataFrame([
        # Completed — even though deadline passed
        _make_row("N-001", "2025-01-01", "Completed"),
        # In Progress but deadline is in the future
        _make_row("N-002", "2027-06-01", "In Progress"),
        # Planning — deadline passed but Planning is excluded
        _make_row("N-003", "2025-06-01", "Planning"),
    ])


@pytest.fixture
def edge_df() -> pd.DataFrame:
    """Edge cases: missing dates, invalid dates, exact boundary."""
    return pd.DataFrame([
        _make_row("E-001", None, "In Progress"),           # missing
        _make_row("E-002", "", "In Progress"),              # empty string
        _make_row("E-003", "not-a-date", "In Progress"),    # invalid
        _make_row("E-004", "2026-09-18", "In Progress"),    # exact ref date
        _make_row("E-005", "2026-09-17", "In Progress"),    # 1 day past
    ])


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Load the actual sample_projects.csv."""
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_projects.csv"
    return pd.read_csv(data_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestDelayDetector:

    # --- Core detection ---

    def test_delayed_in_progress_detected(self, delayed_df: pd.DataFrame):
        """An In Progress project past its deadline MUST be flagged."""
        flagged = detect_flagged(delayed_df, reference_date=REF_DATE)
        flagged_ids = {r["project_id"] for r in flagged}
        assert "D-001" in flagged_ids

    def test_delayed_stalled_detected(self, delayed_df: pd.DataFrame):
        """A Stalled project past its deadline MUST be flagged."""
        flagged = detect_flagged(delayed_df, reference_date=REF_DATE)
        flagged_ids = {r["project_id"] for r in flagged}
        assert "D-002" in flagged_ids

    def test_completed_not_flagged(self, not_delayed_df: pd.DataFrame):
        """A Completed project must NEVER be flagged, even if past deadline."""
        results = detect(not_delayed_df, reference_date=REF_DATE)
        n001 = next(r for r in results if r["project_id"] == "N-001")
        assert not n001["is_flagged"]

    def test_in_progress_before_deadline_not_flagged(self, not_delayed_df: pd.DataFrame):
        """An In Progress project before its deadline must NOT be flagged."""
        results = detect(not_delayed_df, reference_date=REF_DATE)
        n002 = next(r for r in results if r["project_id"] == "N-002")
        assert not n002["is_flagged"]

    def test_planning_not_flagged(self, not_delayed_df: pd.DataFrame):
        """A Planning project must NOT be flagged even if deadline passed."""
        results = detect(not_delayed_df, reference_date=REF_DATE)
        n003 = next(r for r in results if r["project_id"] == "N-003")
        assert not n003["is_flagged"]

    def test_unknown_status_not_flagged(self):
        """Unknown statuses must not be treated as delay-eligible."""
        df = pd.DataFrame([
            _make_row("U-001", "2026-01-01", "Cancelled")
        ])

        results = detect(df, reference_date=REF_DATE)
        result = results[0]

        assert not result["is_flagged"]
        assert result["status"] == "Cancelled"

    # --- Edge cases ---

    def test_missing_date_not_flagged(self, edge_df: pd.DataFrame):
        """Missing revised_completion_date must not be flagged."""
        results = detect(edge_df, reference_date=REF_DATE)
        e001 = next(r for r in results if r["project_id"] == "E-001")
        assert not e001["is_flagged"]
        assert "missing or invalid" in e001["reason"].lower()

    def test_empty_date_not_flagged(self, edge_df: pd.DataFrame):
        """Empty string date must not be flagged."""
        results = detect(edge_df, reference_date=REF_DATE)
        e002 = next(r for r in results if r["project_id"] == "E-002")
        assert not e002["is_flagged"]

    def test_invalid_date_not_flagged(self, edge_df: pd.DataFrame):
        """Invalid date string must not crash and must not be flagged."""
        results = detect(edge_df, reference_date=REF_DATE)
        e003 = next(r for r in results if r["project_id"] == "E-003")
        assert not e003["is_flagged"]

    def test_exact_deadline_not_flagged(self, edge_df: pd.DataFrame):
        """A project whose deadline is exactly the reference date is NOT delayed."""
        results = detect(edge_df, reference_date=REF_DATE)
        e004 = next(r for r in results if r["project_id"] == "E-004")
        assert not e004["is_flagged"], "Exact deadline should not be flagged (> 0, not >= 0)"

    def test_one_day_past_is_flagged(self, edge_df: pd.DataFrame):
        """A project 1 day past deadline MUST be flagged."""
        results = detect(edge_df, reference_date=REF_DATE)
        e005 = next(r for r in results if r["project_id"] == "E-005")
        assert e005["is_flagged"]
        assert e005["days_delayed"] == 1

    # --- days_delayed calculation ---

    def test_days_delayed_calculation(self, delayed_df: pd.DataFrame):
        """days_delayed must equal reference_date - revised_completion_date."""
        results = detect(delayed_df, reference_date=REF_DATE)
        d001 = next(r for r in results if r["project_id"] == "D-001")
        expected = (REF_DATE - date(2026, 3, 1)).days
        assert d001["days_delayed"] == expected

    def test_unflagged_days_delayed_is_zero(self, not_delayed_df: pd.DataFrame):
        """Non-flagged projects must have days_delayed = 0."""
        results = detect(not_delayed_df, reference_date=REF_DATE)
        for r in results:
            if not r["is_flagged"]:
                assert r["days_delayed"] == 0

    # --- Severity ---

    def test_severity_range(self, delayed_df: pd.DataFrame):
        """Severity must be between 0.0 and 1.0 inclusive."""
        results = detect(delayed_df, reference_date=REF_DATE)
        for r in results:
            assert 0.0 <= r["severity"] <= 1.0

    def test_severity_increases_with_delay(self):
        """A longer delay should produce higher severity."""
        short = pd.DataFrame([_make_row("S-001", "2026-09-01", "In Progress")])
        long = pd.DataFrame([_make_row("L-001", "2024-01-01", "In Progress")])
        short_r = detect(short, reference_date=REF_DATE)[0]
        long_r = detect(long, reference_date=REF_DATE)[0]
        assert long_r["severity"] > short_r["severity"]

    # --- Result structure ---

    def test_result_fields_present(self, delayed_df: pd.DataFrame):
        """Every result must contain all required fields."""
        required_fields = {
            "project_id", "detector", "is_flagged",
            "revised_completion_date", "reference_date",
            "days_delayed", "status", "severity", "reason",
        }
        results = detect(delayed_df, reference_date=REF_DATE)
        for r in results:
            missing = required_fields - set(r.keys())
            assert not missing, f"{r['project_id']} missing: {missing}"

    def test_detector_name(self, delayed_df: pd.DataFrame):
        """Detector field must always be 'delay'."""
        for r in detect(delayed_df, reference_date=REF_DATE):
            assert r["detector"] == "delay"

    def test_flagged_have_reason(self, delayed_df: pd.DataFrame):
        """Flagged projects must have a non-empty reason."""
        for r in detect_flagged(delayed_df, reference_date=REF_DATE):
            assert r["reason"]
            assert "days past" in r["reason"].lower()

    # --- Date parser ---

    def test_parse_date_iso_string(self):
        assert _parse_date("2026-03-01") == date(2026, 3, 1)

    def test_parse_date_none(self):
        assert _parse_date(None) is None

    def test_parse_date_invalid(self):
        assert _parse_date("not-a-date") is None

    def test_parse_date_empty(self):
        assert _parse_date("") is None

    # --- Full dataset ---

    def test_handles_full_dataset(self, sample_df: pd.DataFrame):
        """Detector must run without errors on the full 100-row dataset."""
        results = detect(sample_df, reference_date=REF_DATE)
        assert len(results) == 100
        flagged = [r for r in results if r["is_flagged"]]
        # We planted 3 delay anomalies + 1 compound; expect at least 3
        assert len(flagged) >= 3, f"Expected >= 3 flags, got {len(flagged)}"

    def test_missing_column_raises(self):
        """Detector must raise ValueError if required columns are missing."""
        bad_df = pd.DataFrame([{"project_id": "P-001"}])
        with pytest.raises(ValueError, match="missing required columns"):
            detect(bad_df)

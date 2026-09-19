"""
Unit tests for CivicLens Cost Overrun Detector.

Tests cover:
1.  Clear cost overrun is detected.
2.  Normal project is not detected.
3.  Exactly 20% threshold is NOT flagged.
4.  Just above 20% IS flagged.
5.  No-overrun case where revised equals original.
6.  Revised cost below original.
7.  Invalid zero original cost.
8.  Invalid negative original cost.
9.  Custom threshold.
10. Correct percentage calculation.
11. Severity is between 0.0 and 1.0.
12. Required result fields.
13. Detector name.
14. Flagged projects have a reason.
15. Full 100-row sample_projects.csv runs successfully.
16. Missing required columns raises ValueError.
"""

from pathlib import Path

import pandas as pd
import pytest

from app.engine.detectors.cost_overrun import (
    detect,
    detect_flagged,
    _compute_overrun_pct,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_row(pid: str, original: float, revised: float) -> dict:
    return {
        "project_id": pid,
        "original_cost_lakhs": original,
        "revised_cost_lakhs": revised,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def overrun_df() -> pd.DataFrame:
    """Projects with clear cost overruns (>20%)."""
    return pd.DataFrame([
        _make_row("O-001", 1000, 1500),  # 50% overrun
        _make_row("O-002", 1000, 2000),  # 100% overrun
    ])


@pytest.fixture
def normal_df() -> pd.DataFrame:
    """Projects within the default 20% threshold."""
    return pd.DataFrame([
        _make_row("N-001", 1000, 1100),  # 10% overrun
        _make_row("N-002", 1000, 1050),  # 5% overrun
        _make_row("N-003", 1000, 1000),  # 0% overrun
    ])


@pytest.fixture
def invalid_df() -> pd.DataFrame:
    """Projects with zero or negative original cost."""
    return pd.DataFrame([
        _make_row("I-001", 0, 500),       # zero
        _make_row("I-002", -100, 500),     # negative
        _make_row("I-003", 1000, 1500),    # normal (control)
    ])


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Load the actual sample_projects.csv."""
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_projects.csv"
    return pd.read_csv(data_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestCostOverrunDetector:

    # --- Core detection ---

    def test_clear_overrun_detected(self, overrun_df: pd.DataFrame):
        """Projects with >20% overrun MUST be flagged."""
        flagged = detect_flagged(overrun_df)
        flagged_ids = {r["project_id"] for r in flagged}
        assert "O-001" in flagged_ids, "50% overrun not detected"
        assert "O-002" in flagged_ids, "100% overrun not detected"

    def test_normal_project_not_detected(self, normal_df: pd.DataFrame):
        """Projects within threshold must NOT be flagged."""
        flagged = detect_flagged(normal_df)
        assert len(flagged) == 0, f"Expected 0 flags, got {len(flagged)}"

    def test_exactly_20_pct_not_flagged(self):
        """Exactly 20% overrun must NOT be flagged (> not >=)."""
        df = pd.DataFrame([_make_row("B-001", 1000, 1200)])
        flagged = detect_flagged(df)
        assert len(flagged) == 0

    def test_just_above_20_pct_flagged(self):
        """Just above 20% overrun MUST be flagged."""
        df = pd.DataFrame([_make_row("B-002", 1000, 1201)])
        flagged = detect_flagged(df)
        assert len(flagged) == 1
        assert flagged[0]["project_id"] == "B-002"

    def test_no_overrun_revised_equals_original(self):
        """Revised == original means 0% overrun, not flagged."""
        df = pd.DataFrame([_make_row("E-001", 1000, 1000)])
        results = detect(df)
        r = results[0]
        assert not r["is_flagged"]
        assert r["cost_overrun_pct"] == 0.0
        assert r["direction"] == "no_overrun"

    def test_revised_below_original(self):
        """Revised < original is a negative overrun, not flagged."""
        df = pd.DataFrame([_make_row("E-002", 1000, 900)])
        results = detect(df)
        r = results[0]
        assert not r["is_flagged"]
        assert r["cost_overrun_pct"] < 0
        assert r["direction"] == "no_overrun"

    # --- Invalid original cost ---

    def test_zero_original_cost(self, invalid_df: pd.DataFrame):
        """Zero original cost must be handled as non-computable, not flagged."""
        results = detect(invalid_df)
        i001 = next(r for r in results if r["project_id"] == "I-001")
        assert not i001["is_flagged"]
        assert i001["direction"] == "invalid_original_cost"
        assert i001["cost_overrun_pct"] == 0.0
        assert i001["severity"] == 0.0
        assert "cannot be calculated" in i001["reason"].lower()

    def test_negative_original_cost(self, invalid_df: pd.DataFrame):
        """Negative original cost must be handled as non-computable."""
        results = detect(invalid_df)
        i002 = next(r for r in results if r["project_id"] == "I-002")
        assert not i002["is_flagged"]
        assert i002["direction"] == "invalid_original_cost"
        assert i002["severity"] == 0.0

    # --- Custom threshold ---

    def test_custom_threshold(self):
        """Detector must respect a custom threshold value."""
        df = pd.DataFrame([_make_row("C-001", 1000, 1150)])
        # 15% overrun
        assert len(detect_flagged(df, threshold=10.0)) == 1   # 15 > 10
        assert len(detect_flagged(df, threshold=20.0)) == 0   # 15 < 20

    # --- Percentage calculation ---

    def test_correct_percentage_calculation(self):
        """Overrun percentage must be calculated correctly."""
        assert _compute_overrun_pct(1000, 1250) == 25.0
        assert _compute_overrun_pct(1000, 1000) == 0.0
        assert _compute_overrun_pct(1000, 900) == -10.0
        assert _compute_overrun_pct(500, 750) == 50.0
        assert _compute_overrun_pct(0, 500) is None
        assert _compute_overrun_pct(-100, 500) is None

    # --- Severity ---

    def test_severity_range(self, overrun_df: pd.DataFrame):
        """Severity must be between 0.0 and 1.0 inclusive."""
        results = detect(overrun_df)
        for r in results:
            assert 0.0 <= r["severity"] <= 1.0

    def test_severity_values(self):
        """Severity should scale linearly up to 1.0 at 100% overrun."""
        df = pd.DataFrame([
            _make_row("S-001", 1000, 1500),   # 50% -> sev 0.5
            _make_row("S-002", 1000, 2000),   # 100% -> sev 1.0
            _make_row("S-003", 1000, 3000),   # 200% -> sev 1.0 (capped)
        ])
        results = detect(df)
        s001 = next(r for r in results if r["project_id"] == "S-001")
        s002 = next(r for r in results if r["project_id"] == "S-002")
        s003 = next(r for r in results if r["project_id"] == "S-003")
        assert s001["severity"] == 0.5
        assert s002["severity"] == 1.0
        assert s003["severity"] == 1.0

    def test_unflagged_severity_is_zero(self, normal_df: pd.DataFrame):
        """Non-flagged results must have severity 0.0."""
        results = detect(normal_df)
        for r in results:
            assert r["severity"] == 0.0

    # --- Result structure ---

    def test_result_fields_present(self, overrun_df: pd.DataFrame):
        """Every result must contain all required fields."""
        required_fields = {
            "project_id", "detector", "is_flagged",
            "original_cost_lakhs", "revised_cost_lakhs",
            "cost_overrun_pct", "threshold", "severity",
            "direction", "reason",
        }
        results = detect(overrun_df)
        for r in results:
            missing = required_fields - set(r.keys())
            assert not missing, f"{r['project_id']} missing: {missing}"

    def test_detector_name(self, overrun_df: pd.DataFrame):
        """Detector field must always be 'cost_overrun'."""
        for r in detect(overrun_df):
            assert r["detector"] == "cost_overrun"

    def test_flagged_have_reason(self, overrun_df: pd.DataFrame):
        """Flagged projects must have a non-empty reason."""
        for r in detect_flagged(overrun_df):
            assert r["reason"]
            assert "above the original cost" in r["reason"].lower()

    # --- Full dataset ---

    def test_handles_full_dataset(self, sample_df: pd.DataFrame):
        """Detector must run without errors on the full 100-row dataset."""
        results = detect(sample_df)
        assert len(results) == 100
        flagged = [r for r in results if r["is_flagged"]]
        # We planted 3 cost overruns + 1 compound
        assert len(flagged) >= 3, f"Expected >= 3 flags, got {len(flagged)}"

    # --- Error handling ---

    def test_missing_column_raises(self):
        """Detector must raise ValueError if required columns are missing."""
        bad_df = pd.DataFrame([{"project_id": "P-001"}])
        with pytest.raises(ValueError, match="missing required columns"):
            detect(bad_df)

"""
Unit tests for CivicLens Progress Mismatch Detector.

Tests cover:
1. A clear mismatch is detected.
2. A normal (aligned) project is NOT detected.
3. Financial progress ahead of physical progress.
4. Physical progress ahead of financial progress.
5. Threshold boundary behavior.
6. Zero/invalid revised cost handling.
7. All required result fields are present.
8. Full 100-project dataset runs successfully.
"""

from pathlib import Path

import pandas as pd
import pytest

from app.engine.detectors.progress_mismatch import (
    detect,
    detect_flagged,
    _safe_financial_progress,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_row(
    pid: str,
    expenditure: float,
    revised_cost: float,
    physical_pct: float,
) -> dict:
    return {
        "project_id": pid,
        "expenditure_lakhs": expenditure,
        "revised_cost_lakhs": revised_cost,
        "physical_progress_pct": physical_pct,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def aligned_df() -> pd.DataFrame:
    """Projects where financial and physical progress are closely aligned."""
    return pd.DataFrame([
        _make_row("A-001", 500, 1000, 50.0),   # fin=50%, phys=50% -> 0pp
        _make_row("A-002", 750, 1000, 70.0),   # fin=75%, phys=70% -> 5pp
        _make_row("A-003", 200, 1000, 25.0),   # fin=20%, phys=25% -> 5pp
        _make_row("A-004", 900, 1000, 85.0),   # fin=90%, phys=85% -> 5pp
    ])


@pytest.fixture
def mismatch_df() -> pd.DataFrame:
    """Projects with clear mismatches in both directions."""
    return pd.DataFrame([
        # Financial ahead: spent 80% but only 30% physically done
        _make_row("M-001", 800, 1000, 30.0),
        # Physical ahead: spent 10% but claims 60% physically done
        _make_row("M-002", 100, 1000, 60.0),
        # Aligned (control)
        _make_row("M-003", 500, 1000, 50.0),
    ])


@pytest.fixture
def zero_cost_df() -> pd.DataFrame:
    """Projects with zero or negative revised cost."""
    return pd.DataFrame([
        _make_row("Z-001", 500, 0, 50.0),     # zero
        _make_row("Z-002", 500, -100, 50.0),   # negative
        _make_row("Z-003", 500, 1000, 50.0),   # normal (control)
    ])


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Load the actual sample_projects.csv."""
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_projects.csv"
    return pd.read_csv(data_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestProgressMismatchDetector:

    def test_clear_mismatch_is_detected(self, mismatch_df: pd.DataFrame):
        """Projects with >25pp gap MUST be flagged."""
        flagged = detect_flagged(mismatch_df)
        flagged_ids = {r["project_id"] for r in flagged}
        assert "M-001" in flagged_ids, "Financial-ahead mismatch not detected"
        assert "M-002" in flagged_ids, "Physical-ahead mismatch not detected"

    def test_aligned_project_not_detected(self, aligned_df: pd.DataFrame):
        """Projects within threshold must NOT be flagged."""
        flagged = detect_flagged(aligned_df)
        assert len(flagged) == 0, f"Expected 0 flags, got {len(flagged)}"

    def test_financial_ahead_direction(self, mismatch_df: pd.DataFrame):
        """When spending outpaces physical work, direction must be financial_ahead."""
        results = detect(mismatch_df)
        m001 = next(r for r in results if r["project_id"] == "M-001")
        assert m001["is_flagged"]
        assert m001["direction"] == "financial_ahead"
        assert m001["financial_progress_pct"] > m001["physical_progress_pct"]

    def test_physical_ahead_direction(self, mismatch_df: pd.DataFrame):
        """When physical work outpaces spending, direction must be physical_ahead."""
        results = detect(mismatch_df)
        m002 = next(r for r in results if r["project_id"] == "M-002")
        assert m002["is_flagged"]
        assert m002["direction"] == "physical_ahead"
        assert m002["physical_progress_pct"] > m002["financial_progress_pct"]

    def test_threshold_boundary_below(self):
        """A mismatch exactly at the threshold must NOT be flagged."""
        df = pd.DataFrame([_make_row("B-001", 750, 1000, 50.0)])
        # fin=75%, phys=50% -> gap = 25pp, threshold = 25 -> NOT flagged (> not >=)
        flagged = detect_flagged(df, threshold=25.0)
        assert len(flagged) == 0

    def test_threshold_boundary_above(self):
        """A mismatch just above the threshold MUST be flagged."""
        df = pd.DataFrame([_make_row("B-002", 755, 1000, 50.0)])
        # fin=75.5%, phys=50% -> gap = 25.5pp > 25 -> flagged
        flagged = detect_flagged(df, threshold=25.0)
        assert len(flagged) == 1
        assert flagged[0]["project_id"] == "B-002"

    def test_custom_threshold(self):
        """Detector must respect a custom threshold value."""
        df = pd.DataFrame([_make_row("C-001", 600, 1000, 50.0)])
        # fin=60%, phys=50% -> gap = 10pp
        assert len(detect_flagged(df, threshold=5.0)) == 1   # 10 > 5
        assert len(detect_flagged(df, threshold=15.0)) == 0   # 10 < 15

    def test_zero_revised_cost(self, zero_cost_df: pd.DataFrame):
        """Zero revised cost must be handled as non-computable, not flagged."""
        results = detect(zero_cost_df)
        assert len(results) == 3

        z001 = next(r for r in results if r["project_id"] == "Z-001")
        assert not z001["is_flagged"]
        assert z001["direction"] == "invalid_cost"
        assert z001["financial_progress_pct"] == 0.0
        assert z001["mismatch_pct"] == 0.0
        assert z001["severity"] == 0.0
        assert "could not be computed" in z001["reason"].lower()
        assert "zero or negative" in z001["reason"].lower()

    def test_negative_revised_cost(self, zero_cost_df: pd.DataFrame):
        """Negative revised cost must be handled as non-computable, not flagged."""
        results = detect(zero_cost_df)
        z002 = next(r for r in results if r["project_id"] == "Z-002")
        assert not z002["is_flagged"]
        assert z002["direction"] == "invalid_cost"
        assert z002["severity"] == 0.0

    def test_safe_financial_progress_function(self):
        """Direct test of the safe division helper."""
        assert _safe_financial_progress(500, 1000) == 50.0
        assert _safe_financial_progress(0, 1000) == 0.0
        assert _safe_financial_progress(500, 0) is None
        assert _safe_financial_progress(500, -100) is None

    def test_result_fields_present(self, mismatch_df: pd.DataFrame):
        """Every result must contain all required fields."""
        required_fields = {
            "project_id", "detector", "is_flagged",
            "financial_progress_pct", "physical_progress_pct",
            "mismatch_pct", "threshold", "severity",
            "direction", "reason",
        }
        results = detect(mismatch_df)
        for r in results:
            missing = required_fields - set(r.keys())
            assert not missing, f"{r['project_id']} missing fields: {missing}"

    def test_detector_name(self, mismatch_df: pd.DataFrame):
        """Detector field must always be 'progress_mismatch'."""
        for r in detect(mismatch_df):
            assert r["detector"] == "progress_mismatch"

    def test_severity_range(self, mismatch_df: pd.DataFrame):
        """Severity must be between 0.0 and 1.0 inclusive."""
        for r in detect(mismatch_df):
            assert 0.0 <= r["severity"] <= 1.0

    def test_flagged_have_reason(self, mismatch_df: pd.DataFrame):
        """Flagged projects must have a non-empty reason."""
        for r in detect_flagged(mismatch_df):
            assert r["reason"], f"{r['project_id']} flagged but reason empty"

    def test_handles_full_dataset(self, sample_df: pd.DataFrame):
        """Detector must run without errors on the full 100-row dataset."""
        results = detect(sample_df)
        assert len(results) == 100
        flagged = [r for r in results if r["is_flagged"]]
        # We planted 4 progress mismatches
        assert len(flagged) >= 4, f"Expected >= 4 flags, got {len(flagged)}"

    def test_missing_column_raises(self):
        """Detector must raise ValueError if required columns are missing."""
        bad_df = pd.DataFrame([{"project_id": "P-001"}])
        with pytest.raises(ValueError, match="missing required columns"):
            detect(bad_df)

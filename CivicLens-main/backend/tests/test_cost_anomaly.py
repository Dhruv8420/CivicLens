"""
Unit tests for CivicLens Cost Anomaly Detector (IQR method).

Tests verify:
1. A clearly extreme project is detected.
2. A normal project is NOT detected.
3. IQR calculations are performed independently by sector.
4. All required result fields are present.
5. The detector handles a valid full DataFrame correctly.
"""
from pathlib import Path

import pandas as pd
# pyrefly: ignore [missing-import]
import pytest

from app.engine.detectors.cost_anomaly import (
    detect,
    detect_flagged,
    _compute_sector_bounds,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def normal_df() -> pd.DataFrame:
    """Small DataFrame where all costs are within IQR bounds per sector."""
    return pd.DataFrame([
        {"project_id": "P-001", "original_cost_lakhs": 500, "sector": "Transport"},
        {"project_id": "P-002", "original_cost_lakhs": 600, "sector": "Transport"},
        {"project_id": "P-003", "original_cost_lakhs": 550, "sector": "Transport"},
        {"project_id": "P-004", "original_cost_lakhs": 580, "sector": "Transport"},
        {"project_id": "P-005", "original_cost_lakhs": 520, "sector": "Transport"},
        {"project_id": "P-006", "original_cost_lakhs": 300, "sector": "Education"},
        {"project_id": "P-007", "original_cost_lakhs": 350, "sector": "Education"},
        {"project_id": "P-008", "original_cost_lakhs": 320, "sector": "Education"},
        {"project_id": "P-009", "original_cost_lakhs": 310, "sector": "Education"},
        {"project_id": "P-010", "original_cost_lakhs": 330, "sector": "Education"},
    ])


@pytest.fixture
def extreme_df() -> pd.DataFrame:
    """
    DataFrame with one extreme outlier in Transport (P-006 = 50000)
    and one clear outlier in Education (P-012 = 5000), surrounded by
    normal peers.
    """
    return pd.DataFrame([
        # Transport: normal range 500–700
        {"project_id": "P-001", "original_cost_lakhs": 500, "sector": "Transport"},
        {"project_id": "P-002", "original_cost_lakhs": 600, "sector": "Transport"},
        {"project_id": "P-003", "original_cost_lakhs": 550, "sector": "Transport"},
        {"project_id": "P-004", "original_cost_lakhs": 620, "sector": "Transport"},
        {"project_id": "P-005", "original_cost_lakhs": 580, "sector": "Transport"},
        {"project_id": "P-006", "original_cost_lakhs": 50000, "sector": "Transport"},  # extreme
        # Education: normal range 300–400
        {"project_id": "P-007", "original_cost_lakhs": 300, "sector": "Education"},
        {"project_id": "P-008", "original_cost_lakhs": 350, "sector": "Education"},
        {"project_id": "P-009", "original_cost_lakhs": 320, "sector": "Education"},
        {"project_id": "P-010", "original_cost_lakhs": 380, "sector": "Education"},
        {"project_id": "P-011", "original_cost_lakhs": 340, "sector": "Education"},
        {"project_id": "P-012", "original_cost_lakhs": 5000, "sector": "Education"},  # extreme
    ])


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Load the actual sample_projects.csv for integration-level check."""
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_projects.csv"
    return pd.read_csv(data_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestCostAnomalyDetector:
    """Tests for the IQR-based cost anomaly detector."""

    def test_extreme_project_is_detected(self, extreme_df: pd.DataFrame):
        """An obviously extreme cost MUST be flagged."""
        flagged = detect_flagged(extreme_df)
        flagged_ids = {r["project_id"] for r in flagged}

        assert "P-006" in flagged_ids, "Transport outlier (50000) not detected"
        assert "P-012" in flagged_ids, "Education outlier (5000) not detected"

    def test_normal_project_is_not_detected(self, normal_df: pd.DataFrame):
        """Projects with costs within the IQR fences must NOT be flagged."""
        flagged = detect_flagged(normal_df)
        assert len(flagged) == 0, f"Expected 0 flags, got {len(flagged)}: {flagged}"

    def test_sector_independent_calculations(self, extreme_df: pd.DataFrame):
        """IQR bounds must be computed independently per sector."""
        bounds = _compute_sector_bounds(extreme_df)

        assert "Transport" in bounds
        assert "Education" in bounds

        # Transport and Education must have different bounds
        assert bounds["Transport"]["upper"] != bounds["Education"]["upper"], (
            "Sector bounds should differ when cost profiles differ"
        )

    def test_result_fields_present(self, extreme_df: pd.DataFrame):
        """Every result dict must contain all required fields."""
        required_fields = {
            "project_id", "detector", "is_flagged", "original_cost_lakhs",
            "sector", "lower_bound", "upper_bound", "severity",
            "direction", "reason",
        }

        results = detect(extreme_df)
        assert len(results) > 0, "detect() returned no results"

        for result in results:
            missing = required_fields - set(result.keys())
            assert not missing, f"Result for {result.get('project_id')} missing fields: {missing}"

    def test_detector_name_is_cost_anomaly(self, extreme_df: pd.DataFrame):
        """The detector field must always be 'cost_anomaly'."""
        results = detect(extreme_df)
        for r in results:
            assert r["detector"] == "cost_anomaly"

    def test_flagged_have_reason(self, extreme_df: pd.DataFrame):
        """Flagged projects must have a non-empty reason string."""
        flagged = detect_flagged(extreme_df)
        for r in flagged:
            assert r["reason"], f"{r['project_id']} flagged but reason is empty"
            assert "lakhs" in r["reason"].lower(), "Reason should mention lakhs"

    def test_unflagged_have_no_reason(self, normal_df: pd.DataFrame):
        """Non-flagged projects must have an empty reason string."""
        results = detect(normal_df)
        for r in results:
            if not r["is_flagged"]:
                assert r["reason"] == "", f"{r['project_id']} unflagged but has reason"

    def test_severity_range(self, extreme_df: pd.DataFrame):
        """Severity must be between 0.0 and 1.0 inclusive."""
        results = detect(extreme_df)
        for r in results:
            assert 0.0 <= r["severity"] <= 1.0, (
                f"{r['project_id']} severity {r['severity']} out of range"
            )

    def test_direction_values(self, extreme_df: pd.DataFrame):
        """Direction must be 'above', 'below', or 'within'."""
        results = detect(extreme_df)
        valid_directions = {"above", "below", "within"}
        for r in results:
            assert r["direction"] in valid_directions

    def test_handles_full_dataset(self, sample_df: pd.DataFrame):
        """Detector must run without errors on the full 100-row dataset."""
        results = detect(sample_df)
        assert len(results) == 100, f"Expected 100 results, got {len(results)}"

        flagged = [r for r in results if r["is_flagged"]]
        # We planted 4 cost anomalies — should find at least those
        assert len(flagged) >= 4, f"Expected at least 4 flags, got {len(flagged)}"

    def test_missing_column_raises(self):
        """Detector must raise ValueError if required columns are missing."""
        bad_df = pd.DataFrame([{"project_id": "P-001", "sector": "Transport"}])
        with pytest.raises(ValueError, match="missing required columns"):
            detect(bad_df)

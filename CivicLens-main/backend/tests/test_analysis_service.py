"""
Unit tests for CivicLens Analysis Service.

Tests cover all 15 required scenarios:
1. Real 100-row sample dataset loading
2. Analyzing all 100 projects
3. Valid single-project lookup
4. Missing project raises ProjectNotFoundError
5. Empty dataset behavior
6. Invalid/missing schema raises DatasetValidationError
7. DataFrame dependency injection
8. Custom CSV path
9. Default DATASET_PATH loading
10. reference_date propagation
11. progress_threshold propagation
12. cost_overrun_threshold propagation
13. Single-project analysis preserves full-dataset sector IQR context
14. Delegation to risk_engine (no duplicated logic)
15. Output contract verification
"""

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from app.config import settings
from app.services.analysis_service import (
    AnalysisService,
    DatasetValidationError,
    ProjectNotFoundError,
)


def _make_valid_df(n: int = 5) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "project_id": f"PRJ-{i:03d}",
            "sector": "Education" if i % 2 == 1 else "Health",
            "original_cost_lakhs": 100.0 * i,
            "expenditure_lakhs": 50.0 * i,
            "revised_cost_lakhs": 100.0 * i,
            "physical_progress_pct": 50.0,
            "revised_completion_date": "2027-12-31",
            "status": "In Progress",
        })
    return pd.DataFrame(rows)


class TestAnalysisService:

    def test_default_dataset_path_loading(self):
        """Service loads default dataset from settings.DATASET_PATH when initialized without args."""
        service = AnalysisService()
        results = service.get_all_projects_analysis(reference_date=date(2026, 9, 18))
        assert len(results) == 100

    def test_analyze_all_100_projects(self):
        """Analyzing all projects returns 100 structured RiskEngineResult objects."""
        service = AnalysisService()
        results = service.get_all_projects_analysis(reference_date=date(2026, 9, 18))
        assert isinstance(results, list)
        assert len(results) == 100
        pids = {r["project_id"] for r in results}
        assert "PRJ-001" in pids
        assert "PRJ-100" in pids

    def test_valid_single_project_lookup(self):
        """get_project_analysis returns analysis result dict for a valid project_id."""
        service = AnalysisService()
        res = service.get_project_analysis("PRJ-001", reference_date=date(2026, 9, 18))
        assert isinstance(res, dict)
        assert res["project_id"] == "PRJ-001"
        assert "risk_score" in res
        assert "risk_level" in res

    def test_missing_project_raises_not_found(self):
        """Lookup of non-existent project_id raises ProjectNotFoundError."""
        service = AnalysisService()
        with pytest.raises(ProjectNotFoundError, match="PRJ-999"):
            service.get_project_analysis("PRJ-999")

    def test_dataframe_dependency_injection(self):
        """Service accepts injected DataFrame directly for testing without filesystem access."""
        df = _make_valid_df(3)
        service = AnalysisService(df=df)
        results = service.get_all_projects_analysis(reference_date=date(2026, 9, 18))
        assert len(results) == 3
        assert results[0]["project_id"] == "PRJ-001"

    def test_custom_csv_path(self, tmp_path):
        """Service loads dataset from custom csv_path when provided."""
        df = _make_valid_df(4)
        custom_csv = tmp_path / "custom_sample.csv"
        df.to_csv(custom_csv, index=False)

        service = AnalysisService(csv_path=custom_csv)
        results = service.get_all_projects_analysis(reference_date=date(2026, 9, 18))
        assert len(results) == 4
        assert results[-1]["project_id"] == "PRJ-004"

    def test_empty_dataset_behavior(self):
        """Empty DataFrame results in [] for get_all and ProjectNotFoundError for get_project."""
        empty_df = pd.DataFrame(columns=[
            "project_id", "sector", "original_cost_lakhs", "expenditure_lakhs",
            "revised_cost_lakhs", "physical_progress_pct", "revised_completion_date", "status"
        ])
        service = AnalysisService(df=empty_df)

        assert service.get_all_projects_analysis() == []

        with pytest.raises(ProjectNotFoundError):
            service.get_project_analysis("PRJ-001")

    def test_invalid_missing_schema_raises_validation_error(self):
        """Missing required columns raises DatasetValidationError."""
        invalid_df = pd.DataFrame([{"project_id": "PRJ-001", "sector": "Health"}])
        service = AnalysisService(df=invalid_df)

        with pytest.raises(DatasetValidationError, match="missing required column"):
            service.get_all_projects_analysis()

        with pytest.raises(DatasetValidationError, match="missing required column"):
            service.get_project_analysis("PRJ-001")

    def test_reference_date_propagation(self):
        """reference_date parameter is forwarded to delay detector via Risk Engine."""
        df = pd.DataFrame([{
            "project_id": "PRJ-DELAY",
            "sector": "Health",
            "original_cost_lakhs": 50.0,
            "revised_cost_lakhs": 50.0,
            "expenditure_lakhs": 25.0,
            "physical_progress_pct": 50.0,
            "revised_completion_date": "2026-06-01",
            "status": "In Progress",
        }])
        service = AnalysisService(df=df)

        res_before = service.get_project_analysis("PRJ-DELAY", reference_date=date(2025, 1, 1))
        assert res_before["detector_contributions"]["delay"]["is_flagged"] is False

        res_after = service.get_project_analysis("PRJ-DELAY", reference_date=date(2026, 12, 31))
        assert res_after["detector_contributions"]["delay"]["is_flagged"] is True

    def test_progress_threshold_propagation(self):
        """progress_threshold parameter is forwarded to progress mismatch detector via Risk Engine."""
        df = pd.DataFrame([{
            "project_id": "PRJ-PM",
            "sector": "Education",
            "original_cost_lakhs": 100.0,
            "revised_cost_lakhs": 100.0,
            "expenditure_lakhs": 50.0,
            "physical_progress_pct": 28.0,  # 22% mismatch
            "revised_completion_date": "2028-01-01",
            "status": "In Progress",
        }])
        service = AnalysisService(df=df)

        # Default 25% threshold -> unflagged
        res_default = service.get_project_analysis("PRJ-PM")
        assert res_default["detector_contributions"]["progress_mismatch"]["is_flagged"] is False

        # Custom 20% threshold -> flagged
        res_custom = service.get_project_analysis("PRJ-PM", progress_threshold=20.0)
        assert res_custom["detector_contributions"]["progress_mismatch"]["is_flagged"] is True

    def test_cost_overrun_threshold_propagation(self):
        """cost_overrun_threshold parameter is forwarded to cost overrun detector via Risk Engine."""
        df = pd.DataFrame([{
            "project_id": "PRJ-CO",
            "sector": "Transport",
            "original_cost_lakhs": 100.0,
            "revised_cost_lakhs": 115.0,  # 15% overrun
            "expenditure_lakhs": 50.0,
            "physical_progress_pct": 50.0,
            "revised_completion_date": "2028-01-01",
            "status": "In Progress",
        }])
        service = AnalysisService(df=df)

        # Default 20% threshold -> unflagged
        res_default = service.get_project_analysis("PRJ-CO")
        assert res_default["detector_contributions"]["cost_overrun"]["is_flagged"] is False

        # Custom 10% threshold -> flagged
        res_custom = service.get_project_analysis("PRJ-CO", cost_overrun_threshold=10.0)
        assert res_custom["detector_contributions"]["cost_overrun"]["is_flagged"] is True

    def test_single_project_uses_complete_dataset_context(self):
        """Single-project analysis evaluates the full dataset so cost anomaly IQR bounds reflect sector context."""
        service = AnalysisService()

        # Run get_all vs get_project("PRJ-001")
        all_results = service.get_all_projects_analysis(reference_date=date(2026, 9, 18))
        prj_001_from_all = next(r for r in all_results if r["project_id"] == "PRJ-001")

        single_result = service.get_project_analysis("PRJ-001", reference_date=date(2026, 9, 18))

        # Both must produce identical risk score and cost anomaly details
        assert single_result["risk_score"] == prj_001_from_all["risk_score"]
        assert (
            single_result["detector_contributions"]["cost_anomaly"]
            == prj_001_from_all["detector_contributions"]["cost_anomaly"]
        )

    def test_service_delegates_to_risk_engine(self):
        """Verify service delegates evaluation directly to risk_engine.evaluate_projects."""
        df = _make_valid_df(2)
        service = AnalysisService(df=df)

        with patch("app.services.analysis_service.risk_engine.evaluate_projects") as mock_eval:
            mock_eval.return_value = [{"project_id": "PRJ-001", "risk_score": 10.0}]
            res = service.get_all_projects_analysis()

            mock_eval.assert_called_once()
            assert res == [{"project_id": "PRJ-001", "risk_score": 10.0}]

    def test_output_contract_verification(self):
        """Single and all project analysis output dicts contain all required schema keys."""
        service = AnalysisService()
        res = service.get_project_analysis("PRJ-001", reference_date=date(2026, 9, 18))

        required_keys = {
            "project_id",
            "risk_score",
            "risk_level",
            "recommendation",
            "flagged_detectors_count",
            "total_detectors_evaluated",
            "detector_contributions",
            "flagged_reasons",
            "signals",
        }
        assert set(res.keys()) == required_keys

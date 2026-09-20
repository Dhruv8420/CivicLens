"""
Unit tests for CivicLens Risk Engine.

Tests cover all 13 required scenarios:
1. Clean project (score 0.0, LOW, LOW recommendation)
2. Each detector contributing independently
3. Maximum score (all detectors flagged at severity 1.0 -> score 100.0, CRITICAL)
4. All risk-band boundaries (0.0, 24.99, 25.00, 49.99, 50.00, 74.99, 75.00, 100.0)
5. Severity scaling (severity * max_points)
6. Missing/non-computable detector data
7. Output contract (schema validation)
8. Custom thresholds forwarded to detectors
9. Custom reference date forwarded to delay detector
10. Full 100-row sample dataset evaluation
11. Score clamping within 0-100 bounds
12. Flagged detector count accuracy
13. Preservation of raw detector evidence
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from app.engine.risk_engine import (
    DETECTOR_WEIGHTS,
    evaluate_project,
    evaluate_projects,
)


def _make_sample_detector_result(
    detector: str,
    is_flagged: bool = False,
    severity: float = 0.0,
    direction: str = "within",
    reason: str = "",
) -> dict:
    return {
        "project_id": "P-TEST",
        "detector": detector,
        "is_flagged": is_flagged,
        "severity": severity,
        "direction": direction,
        "reason": reason,
    }


class TestRiskEngine:

    def test_clean_project(self):
        """Clean project (no detectors flagged) should have score 0.0, LOW level, and LOW recommendation."""
        signals = [
            _make_sample_detector_result("cost_anomaly", False, 0.0),
            _make_sample_detector_result("progress_mismatch", False, 0.0),
            _make_sample_detector_result("delay", False, 0.0),
            _make_sample_detector_result("cost_overrun", False, 0.0),
        ]

        res = evaluate_project("P-CLEAN", signals)

        assert res["project_id"] == "P-CLEAN"
        assert res["risk_score"] == 0.0
        assert res["risk_level"] == "LOW"
        assert res["recommendation"] == "No immediate review indicated by the configured signals."
        assert res["flagged_detectors_count"] == 0
        assert res["total_detectors_evaluated"] == 4
        assert res["flagged_reasons"] == []

    def test_independent_detector_contributions(self):
        """Test each detector contributing independently with severity 1.0."""
        # 1. Cost anomaly only (weight 25)
        signals_ca = [
            _make_sample_detector_result("cost_anomaly", True, 1.0, "above", "Cost high"),
            _make_sample_detector_result("progress_mismatch", False, 0.0),
            _make_sample_detector_result("delay", False, 0.0),
            _make_sample_detector_result("cost_overrun", False, 0.0),
        ]
        res_ca = evaluate_project("P-CA", signals_ca)
        assert res_ca["risk_score"] == 25.0
        assert res_ca["risk_level"] == "MEDIUM"
        assert res_ca["detector_contributions"]["cost_anomaly"]["contribution"] == 25.0

        # 2. Progress mismatch only (weight 30)
        signals_pm = [
            _make_sample_detector_result("cost_anomaly", False, 0.0),
            _make_sample_detector_result("progress_mismatch", True, 1.0, "financial_ahead", "Mismatch high"),
            _make_sample_detector_result("delay", False, 0.0),
            _make_sample_detector_result("cost_overrun", False, 0.0),
        ]
        res_pm = evaluate_project("P-PM", signals_pm)
        assert res_pm["risk_score"] == 30.0
        assert res_pm["risk_level"] == "MEDIUM"
        assert res_pm["detector_contributions"]["progress_mismatch"]["contribution"] == 30.0

        # 3. Delay only (weight 20)
        signals_dl = [
            _make_sample_detector_result("cost_anomaly", False, 0.0),
            _make_sample_detector_result("progress_mismatch", False, 0.0),
            _make_sample_detector_result("delay", True, 1.0, "delayed", "Project delayed"),
            _make_sample_detector_result("cost_overrun", False, 0.0),
        ]
        res_dl = evaluate_project("P-DL", signals_dl)
        assert res_dl["risk_score"] == 20.0
        assert res_dl["risk_level"] == "LOW"
        assert res_dl["detector_contributions"]["delay"]["contribution"] == 20.0

        # 4. Cost overrun only (weight 25)
        signals_co = [
            _make_sample_detector_result("cost_anomaly", False, 0.0),
            _make_sample_detector_result("progress_mismatch", False, 0.0),
            _make_sample_detector_result("delay", False, 0.0),
            _make_sample_detector_result("cost_overrun", True, 1.0, "overrun", "Cost overrun high"),
        ]
        res_co = evaluate_project("P-CO", signals_co)
        assert res_co["risk_score"] == 25.0
        assert res_co["risk_level"] == "MEDIUM"
        assert res_co["detector_contributions"]["cost_overrun"]["contribution"] == 25.0

    def test_maximum_score(self):
        """All detectors flagged at severity 1.0 should produce score 100.0, CRITICAL level."""
        signals = [
            _make_sample_detector_result("cost_anomaly", True, 1.0, "above", "Cost anomaly"),
            _make_sample_detector_result("progress_mismatch", True, 1.0, "financial_ahead", "Progress mismatch"),
            _make_sample_detector_result("delay", True, 1.0, "delayed", "Delayed"),
            _make_sample_detector_result("cost_overrun", True, 1.0, "overrun", "Overrun"),
        ]

        res = evaluate_project("P-MAX", signals)
        assert res["risk_score"] == 100.0
        assert res["risk_level"] == "CRITICAL"
        assert res["recommendation"] == "Priority human verification of project records and supporting documents is recommended."
        assert res["flagged_detectors_count"] == 4
        assert len(res["flagged_reasons"]) == 4

    def test_risk_band_boundaries(self):
        """Verify exact boundary behavior for risk levels and recommendations."""
        # LOW: 0.0 - 24.99
        res_24_99 = evaluate_project("P1", [
            _make_sample_detector_result("progress_mismatch", True, 0.833, "financial_ahead", "Reason")
        ])
        assert res_24_99["risk_score"] == 24.99
        assert res_24_99["risk_level"] == "LOW"
        assert res_24_99["recommendation"] == "No immediate review indicated by the configured signals."

        # MEDIUM: 25.00 - 49.99
        res_25_00 = evaluate_project("P2", [
            _make_sample_detector_result("cost_anomaly", True, 1.0, "above", "Reason")
        ])
        assert res_25_00["risk_score"] == 25.00
        assert res_25_00["risk_level"] == "MEDIUM"
        assert res_25_00["recommendation"] == "Consider routine review of the flagged indicators."

        res_49_99 = evaluate_project("P3", [
            _make_sample_detector_result("cost_anomaly", True, 0.9996, "above", "Reason"),
            _make_sample_detector_result("cost_overrun", True, 1.0, "overrun", "Reason"),
        ])
        assert res_49_99["risk_score"] == 49.99
        assert res_49_99["risk_level"] == "MEDIUM"

        # HIGH: 50.00 - 74.99
        res_50_00 = evaluate_project("P4", [
            _make_sample_detector_result("cost_anomaly", True, 1.0, "above", "Reason"),
            _make_sample_detector_result("cost_overrun", True, 1.0, "overrun", "Reason"),
        ])
        assert res_50_00["risk_score"] == 50.00
        assert res_50_00["risk_level"] == "HIGH"
        assert res_50_00["recommendation"] == "Human verification of the flagged project records is recommended."

        res_74_99 = evaluate_project("P5", [
            _make_sample_detector_result("cost_anomaly", True, 1.0, "above", "Reason"),
            _make_sample_detector_result("progress_mismatch", True, 0.99966, "financial_ahead", "Reason"),
            _make_sample_detector_result("delay", True, 1.0, "delayed", "Reason"),
        ])
        assert res_74_99["risk_score"] == 74.99
        assert res_74_99["risk_level"] == "HIGH"

        # CRITICAL: 75.00 - 100.0
        res_75_00 = evaluate_project("P6", [
            _make_sample_detector_result("cost_anomaly", True, 1.0, "above", "Reason"),
            _make_sample_detector_result("progress_mismatch", True, 1.0, "financial_ahead", "Reason"),
            _make_sample_detector_result("delay", True, 1.0, "delayed", "Reason"),
        ])
        assert res_75_00["risk_score"] == 75.00
        assert res_75_00["risk_level"] == "CRITICAL"
        assert res_75_00["recommendation"] == "Priority human verification of project records and supporting documents is recommended."

    def test_severity_scaling(self):
        """Severity between 0.0 and 1.0 should scale contribution proportionally."""
        signals = [
            _make_sample_detector_result("cost_anomaly", True, 0.5, "above", "Cost severity 0.5"),
            _make_sample_detector_result("progress_mismatch", True, 0.4, "financial_ahead", "PM 0.4"),
            _make_sample_detector_result("delay", True, 0.25, "delayed", "Delay 0.25"),
            _make_sample_detector_result("cost_overrun", True, 0.8, "overrun", "Overrun 0.8"),
        ]

        res = evaluate_project("P-SCALE", signals)
        assert res["risk_score"] == 49.5
        assert res["risk_level"] == "MEDIUM"

    def test_missing_and_non_computable_detector_data(self):
        """Missing detector results get status 'missing_data'; non-computable unflagged results get status 'computed'."""
        signals = [
            _make_sample_detector_result("cost_anomaly", True, 1.0, "above", "Cost high"),
            {
                "project_id": "P-PARTIAL",
                "detector": "progress_mismatch",
                "is_flagged": False,
                "financial_progress_pct": 0.0,
                "physical_progress_pct": 50.0,
                "mismatch_pct": 0.0,
                "threshold": 25.0,
                "severity": 0.0,
                "direction": "invalid_cost",
                "reason": "Financial progress could not be computed: revised cost is zero or negative.",
            },
        ]

        res = evaluate_project("P-PARTIAL", signals)

        pm_contrib = res["detector_contributions"]["progress_mismatch"]
        assert pm_contrib["status"] == "computed"
        assert pm_contrib["is_flagged"] is False
        assert pm_contrib["contribution"] == 0.0
        assert pm_contrib["direction"] == "invalid_cost"

        dl_contrib = res["detector_contributions"]["delay"]
        assert dl_contrib["status"] == "missing_data"
        assert dl_contrib["is_flagged"] is False
        assert dl_contrib["contribution"] == 0.0
        assert dl_contrib["direction"] == "missing"

        co_contrib = res["detector_contributions"]["cost_overrun"]
        assert co_contrib["status"] == "missing_data"
        assert co_contrib["is_flagged"] is False
        assert co_contrib["contribution"] == 0.0

        assert res["risk_score"] == 25.0

    def test_output_contract(self):
        """Verify output dictionary keys and types match expected contract."""
        signals = [_make_sample_detector_result("cost_anomaly", False, 0.0)]
        res = evaluate_project("P-CONTRACT", signals)

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

        assert isinstance(res["project_id"], str)
        assert isinstance(res["risk_score"], float)
        assert isinstance(res["risk_level"], str)
        assert isinstance(res["recommendation"], str)
        assert isinstance(res["flagged_detectors_count"], int)
        assert isinstance(res["total_detectors_evaluated"], int)
        assert isinstance(res["detector_contributions"], dict)
        assert isinstance(res["flagged_reasons"], list)
        assert isinstance(res["signals"], list)

        for det_name, contrib in res["detector_contributions"].items():
            contrib_keys = {
                "detector", "is_flagged", "severity", "max_points",
                "contribution", "status", "direction", "reason",
            }
            assert set(contrib.keys()) == contrib_keys

    def test_custom_thresholds_forwarded(self):
        """Verify evaluate_projects correctly forwards custom thresholds to detectors."""
        df = pd.DataFrame([{
            "project_id": "P-THRESH",
            "sector": "Education",
            "original_cost_lakhs": 100.0,
            "revised_cost_lakhs": 115.0,
            "expenditure_lakhs": 50.0,
            "physical_progress_pct": 20.0,
            "revised_completion_date": "2028-01-01",
            "status": "In Progress",
        }])

        results_default = evaluate_projects(df)
        assert results_default[0]["risk_score"] == 0.0

        results_custom = evaluate_projects(
            df,
            progress_threshold=20.0,
            cost_overrun_threshold=10.0,
        )
        assert results_custom[0]["risk_score"] > 0.0
        contribs = results_custom[0]["detector_contributions"]
        assert contribs["cost_overrun"]["is_flagged"] is True
        assert contribs["progress_mismatch"]["is_flagged"] is True

    def test_custom_reference_date_forwarded(self):
        """Verify evaluate_projects forwards reference_date to delay detector."""
        df = pd.DataFrame([{
            "project_id": "P-DATE",
            "sector": "Health",
            "original_cost_lakhs": 50.0,
            "revised_cost_lakhs": 50.0,
            "expenditure_lakhs": 25.0,
            "physical_progress_pct": 50.0,
            "revised_completion_date": "2026-06-01",
            "status": "In Progress",
        }])

        res_past = evaluate_projects(df, reference_date=date(2025, 1, 1))
        assert res_past[0]["detector_contributions"]["delay"]["is_flagged"] is False

        res_future = evaluate_projects(df, reference_date=date(2026, 12, 31))
        assert res_future[0]["detector_contributions"]["delay"]["is_flagged"] is True

    def test_full_sample_dataset(self):
        """Evaluate full 100-project dataset and verify performance and score properties."""
        csv_path = Path(__file__).resolve().parents[1] / "data" / "sample_projects.csv"
        df = pd.read_csv(csv_path)

        results = evaluate_projects(df, reference_date=date(2026, 9, 18))

        assert len(results) == 100

        for r in results:
            assert 0.0 <= r["risk_score"] <= 100.0
            assert r["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
            assert r["total_detectors_evaluated"] == 4
            assert 0 <= r["flagged_detectors_count"] <= 4

    def test_score_clamping(self):
        """Score must never exceed 100.0 or fall below 0.0."""
        signals = [
            _make_sample_detector_result("cost_anomaly", True, 2.0, "above", "High"),
            _make_sample_detector_result("progress_mismatch", True, 2.0, "financial_ahead", "High"),
            _make_sample_detector_result("delay", True, 2.0, "delayed", "High"),
            _make_sample_detector_result("cost_overrun", True, 2.0, "overrun", "High"),
        ]
        res = evaluate_project("P-CLAMP", signals)
        assert res["risk_score"] == 100.0

    def test_flagged_detector_count(self):
        """Verify flagged_detectors_count accurately reflects number of flagged detectors."""
        signals = [
            _make_sample_detector_result("cost_anomaly", True, 0.5, "above", "Cost"),
            _make_sample_detector_result("progress_mismatch", False, 0.0),
            _make_sample_detector_result("delay", True, 0.5, "delayed", "Delay"),
            _make_sample_detector_result("cost_overrun", False, 0.0),
        ]
        res = evaluate_project("P-COUNT", signals)
        assert res["flagged_detectors_count"] == 2
        assert len(res["flagged_reasons"]) == 2

    def test_preservation_of_raw_detector_evidence(self):
        """Verify raw detector results are preserved untouched in signals field."""
        raw_signals = [
            {
                "project_id": "P-EVIDENCE",
                "detector": "cost_anomaly",
                "is_flagged": True,
                "original_cost_lakhs": 5000.0,
                "sector": "Transport",
                "lower_bound": 100.0,
                "upper_bound": 3000.0,
                "severity": 0.8,
                "direction": "above",
                "reason": "Original project cost is above upper bound.",
            }
        ]
        res = evaluate_project("P-EVIDENCE", raw_signals)
        assert res["signals"] == raw_signals
        assert res["signals"][0]["original_cost_lakhs"] == 5000.0

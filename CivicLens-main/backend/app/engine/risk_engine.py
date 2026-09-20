"""
CivicLens — Risk Engine
========================

PURPOSE:
    Combines signals from four detectors into a single project-level risk score
    from 0 to 100:
    1. Cost Anomaly detector (25 points max)
    2. Progress Mismatch detector (30 points max)
    3. Delay detector (20 points max)
    4. Cost Overrun detector (25 points max)

ETHICAL GUIDELINE:
    This Risk Engine identifies projects that merit human review based on
    statistical and objective project indicators. It does NOT claim fraud,
    corruption, or wrongdoing. All messaging remains neutral and evidence-based.

SCORING METHODOLOGY:
    For each detector:
        - If detector is_flagged is True:
              contribution = round(severity * max_points, 2)
        - If detector is_flagged is False or missing:
              contribution = 0.0

    Total Score:
        risk_score = round(clamp(sum(contributions), 0.0, 100.0), 2)

RISK BANDS & RECOMMENDATIONS:
    - 0.00 – 24.99 : LOW
      "No immediate review indicated by the configured signals."
    - 25.00 – 49.99 : MEDIUM
      "Consider routine review of the flagged indicators."
    - 50.00 – 74.99 : HIGH
      "Human verification of the flagged project records is recommended."
    - 75.00 – 100.00 : CRITICAL
      "Priority human verification of project records and supporting documents is recommended."
"""

from dataclasses import dataclass, asdict
from datetime import date
from typing import Any

import pandas as pd

from app.engine.detectors import cost_anomaly, progress_mismatch, delay, cost_overrun


# Centralized detector weights (sum = 100 points)
DETECTOR_WEIGHTS: dict[str, float] = {
    "cost_anomaly": 25.0,
    "progress_mismatch": 30.0,
    "delay": 20.0,
    "cost_overrun": 25.0,
}


@dataclass
class DetectorContribution:
    """Contribution details for a single detector signal within a project."""

    detector: str
    is_flagged: bool
    severity: float
    max_points: float
    contribution: float
    status: str  # "computed" | "missing_data"
    direction: str
    reason: str


@dataclass
class RiskEngineResult:
    """Project-level risk evaluation result combining all detector signals."""

    project_id: str
    risk_score: float
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    recommendation: str
    flagged_detectors_count: int
    total_detectors_evaluated: int
    detector_contributions: dict[str, dict]
    flagged_reasons: list[str]
    signals: list[dict]


def _get_risk_level_and_recommendation(score: float) -> tuple[str, str]:
    """Map a risk score (0-100) to its risk level band and recommendation."""
    if score < 25.0:
        return "LOW", "No immediate review indicated by the configured signals."
    elif score < 50.0:
        return "MEDIUM", "Consider routine review of the flagged indicators."
    elif score < 75.0:
        return "HIGH", "Human verification of the flagged project records is recommended."
    else:
        return (
            "CRITICAL",
            "Priority human verification of project records and supporting documents is recommended.",
        )


def evaluate_project(
    project_id: str,
    detector_results: list[dict],
    detector_availability: dict[str, dict[str, Any]] | None = None,
) -> dict:
    """
    Evaluate risk score and assemble explainable result for a single project.

    Parameters
    ----------
    project_id : str
        The identifier of the project.
    detector_results : list[dict]
        Detector output dicts for this project (from available detectors).
    detector_availability : dict[str, dict[str, Any]] | None
        Optional availability metadata per detector.

    Returns
    -------
    dict
        Asdict representation of ``RiskEngineResult``.
    """
    results_by_name: dict[str, dict] = {}
    for res in detector_results:
        det_name = res.get("detector")
        if det_name and det_name not in results_by_name:
            results_by_name[det_name] = res

    contributions_dict: dict[str, dict] = {}
    flagged_count = 0
    flagged_reasons: list[str] = []

    for det_name, max_points in DETECTOR_WEIGHTS.items():
        if det_name in results_by_name:
            res = results_by_name[det_name]
            is_flagged = bool(res.get("is_flagged", False))
            severity = float(res.get("severity", 0.0))
            direction = str(res.get("direction", ""))
            reason = str(res.get("reason", ""))
            status = "computed"

            if is_flagged:
                contribution = round(severity * max_points, 2)
                flagged_count += 1
                if reason:
                    flagged_reasons.append(reason)
            else:
                contribution = 0.0
        else:
            is_flagged = False
            severity = 0.0
            direction = "missing"
            avail_info = (detector_availability or {}).get(det_name, {})
            reason = avail_info.get(
                "reason", f"Detector '{det_name}' result is missing."
            )
            status = "missing_data"
            contribution = 0.0

        contrib = DetectorContribution(
            detector=det_name,
            is_flagged=is_flagged,
            severity=severity,
            max_points=max_points,
            contribution=contribution,
            status=status,
            direction=direction,
            reason=reason,
        )
        contributions_dict[det_name] = asdict(contrib)

    raw_score = sum(c["contribution"] for c in contributions_dict.values())
    risk_score = round(max(0.0, min(100.0, raw_score)), 2)
    risk_level, recommendation = _get_risk_level_and_recommendation(risk_score)

    result = RiskEngineResult(
        project_id=project_id,
        risk_score=risk_score,
        risk_level=risk_level,
        recommendation=recommendation,
        flagged_detectors_count=flagged_count,
        total_detectors_evaluated=len(DETECTOR_WEIGHTS),
        detector_contributions=contributions_dict,
        flagged_reasons=flagged_reasons,
        signals=list(detector_results),
    )

    return asdict(result)


def evaluate_projects(
    df: pd.DataFrame,
    reference_date: date | None = None,
    progress_threshold: float | None = None,
    cost_overrun_threshold: float | None = None,
    available_detectors: set[str] | list[str] | None = None,
    detector_availability: dict[str, dict[str, Any]] | None = None,
) -> list[dict]:
    """
    Run active detectors on *df* and compute project-level risk scores.

    Parameters
    ----------
    df : pd.DataFrame
        Input project dataset.
    reference_date : date | None
        Optional reference date forwarded to delay detector.
    progress_threshold : float | None
        Optional mismatch threshold percentage points forwarded to progress mismatch detector.
    cost_overrun_threshold : float | None
        Optional overrun threshold percentage forwarded to cost overrun detector.
    available_detectors : set[str] | list[str] | None
        Optional set of available detector names. If None, evaluates all detectors whose
        required columns are present in df.
    detector_availability : dict[str, dict[str, Any]] | None
        Optional detailed availability status dict per detector.

    Returns
    -------
    list[dict]
        One ``RiskEngineResult`` dict per project in *df*.
    """
    if "project_id" not in df.columns:
        raise ValueError("DataFrame missing required column: 'project_id'")

    if available_detectors is None:
        avail_set = {"cost_anomaly", "progress_mismatch", "delay", "cost_overrun"}
    else:
        avail_set = set(available_detectors)

    ca_results: list[dict] = []
    if "cost_anomaly" in avail_set and "original_cost_lakhs" in df.columns and "sector" in df.columns:
        ca_results = cost_anomaly.detect(df)

    pm_results: list[dict] = []
    if (
        "progress_mismatch" in avail_set
        and "expenditure_lakhs" in df.columns
        and "revised_cost_lakhs" in df.columns
        and "physical_progress_pct" in df.columns
    ):
        pm_kwargs: dict[str, Any] = {}
        if progress_threshold is not None:
            pm_kwargs["threshold"] = progress_threshold
        pm_results = progress_mismatch.detect(df, **pm_kwargs)

    delay_results: list[dict] = []
    if (
        "delay" in avail_set
        and "status" in df.columns
        and ("revised_completion_date" in df.columns or "target_completion_date" in df.columns)
    ):
        delay_kwargs: dict[str, Any] = {}
        if reference_date is not None:
            delay_kwargs["reference_date"] = reference_date
        delay_results = delay.detect(df, **delay_kwargs)

    co_results: list[dict] = []
    if (
        "cost_overrun" in avail_set
        and "original_cost_lakhs" in df.columns
        and "revised_cost_lakhs" in df.columns
    ):
        co_kwargs: dict[str, Any] = {}
        if cost_overrun_threshold is not None:
            co_kwargs["threshold"] = cost_overrun_threshold
        co_results = cost_overrun.detect(df, **co_kwargs)

    project_signals: dict[str, list[dict]] = {}
    for row_pid in df["project_id"].unique():
        project_signals[str(row_pid)] = []

    for res in ca_results + pm_results + delay_results + co_results:
        pid = str(res["project_id"])
        if pid in project_signals:
            project_signals[pid].append(res)

    results: list[dict] = []
    for pid in df["project_id"].unique():
        pid_str = str(pid)
        eval_res = evaluate_project(
            pid_str,
            project_signals[pid_str],
            detector_availability=detector_availability,
        )
        results.append(eval_res)

    return results

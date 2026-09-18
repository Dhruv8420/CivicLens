"""
CivicLens — Cost Anomaly Detector (IQR Method)
================================================

PURPOSE:
    Identifies projects whose ``original_cost_lakhs`` is statistically
    unusual compared with other projects in the SAME sector.

WHY SECTOR-WISE COMPARISON:
    Different sectors have fundamentally different cost profiles.
    A Transport highway project costing 4000 Lakhs is normal, but an
    Education school project at the same cost would be extreme.
    Comparing within sector ensures that outliers are relative to their
    peer group, not the entire dataset.

METHOD — Interquartile Range (IQR):
    For each sector independently:

        Q1  = 25th percentile of original_cost_lakhs
        Q3  = 75th percentile of original_cost_lakhs
        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

    A project is flagged as a cost anomaly if its original_cost_lakhs
    falls outside [lower_bound, upper_bound].

    IQR is a robust, non-parametric measure of spread that is resistant
    to extreme values — unlike standard deviation which can be inflated
    by the very outliers we are trying to detect.

OUTPUT:
    A list of ``CostAnomalyResult`` dicts — one per project — containing
    the flag, bounds, severity, and a human-readable explanation.
"""

from dataclasses import dataclass, asdict
from typing import Literal

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Result data structure
# ---------------------------------------------------------------------------
@dataclass
class CostAnomalyResult:
    """Detection result for a single project."""

    project_id: str
    detector: str  # always "cost_anomaly"
    is_flagged: bool
    original_cost_lakhs: float
    sector: str
    lower_bound: float
    upper_bound: float
    severity: float  # 0.0–1.0 normalised distance from fence
    direction: Literal["above", "below", "within"]
    reason: str


# ---------------------------------------------------------------------------
# Core detection logic
# ---------------------------------------------------------------------------
def _compute_sector_bounds(df: pd.DataFrame) -> dict[str, dict]:
    """
    Compute IQR fences for ``original_cost_lakhs`` within each sector.

    Returns a dict keyed by sector name::

        {
            "Transport": {"q1": ..., "q3": ..., "iqr": ...,
                          "lower": ..., "upper": ...},
            ...
        }
    """
    bounds: dict[str, dict] = {}

    for sector, group in df.groupby("sector"):
        costs = group["original_cost_lakhs"]
        q1 = float(np.percentile(costs, 25))
        q3 = float(np.percentile(costs, 75))
        iqr = q3 - q1

        bounds[sector] = {
            "q1": round(q1, 2),
            "q3": round(q3, 2),
            "iqr": round(iqr, 2),
            "lower": round(q1 - 1.5 * iqr, 2),
            "upper": round(q3 + 1.5 * iqr, 2),
        }

    return bounds


def _compute_severity(
    cost: float, lower: float, upper: float, iqr: float
) -> float:
    """
    Compute a normalised severity score (0.0–1.0).

    Severity is the distance from the nearest fence divided by ``iqr``,
    capped at 1.0.  A cost exactly on the fence has severity ~0; a cost
    several IQRs beyond it approaches 1.0.
    """
    if iqr == 0:
        return 0.0

    if cost > upper:
        raw = (cost - upper) / iqr
    elif cost < lower:
        raw = (lower - cost) / iqr
    else:
        return 0.0

    return round(min(raw / 3.0, 1.0), 4)  # scale: 3 IQRs → severity 1.0


def _build_reason(
    cost: float, lower: float, upper: float, sector: str, direction: str
) -> str:
    """Return a human-readable, non-accusatory explanation string."""
    if direction == "above":
        return (
            f"Original project cost of Rs. {cost:,.2f} lakhs is above the "
            f"{sector} sector's IQR upper bound of Rs. {upper:,.2f} lakhs."
        )
    if direction == "below":
        return (
            f"Original project cost of Rs. {cost:,.2f} lakhs is below the "
            f"{sector} sector's IQR lower bound of Rs. {lower:,.2f} lakhs."
        )
    return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def detect(df: pd.DataFrame) -> list[dict]:
    """
    Run cost-anomaly detection on every project in *df*.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain at least ``project_id``, ``original_cost_lakhs``,
        and ``sector`` columns.

    Returns
    -------
    list[dict]
        One ``CostAnomalyResult`` dict per project row.  Flagged entries
        have ``is_flagged=True`` with severity, direction, and reason
        populated.
    """
    required_cols = {"project_id", "original_cost_lakhs", "sector"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")

    sector_bounds = _compute_sector_bounds(df)
    results: list[dict] = []

    for _, row in df.iterrows():
        pid = row["project_id"]
        cost = float(row["original_cost_lakhs"])
        sector = row["sector"]
        bounds = sector_bounds[sector]
        lower = bounds["lower"]
        upper = bounds["upper"]
        iqr = bounds["iqr"]

        if cost > upper:
            flagged, direction = True, "above"
        elif cost < lower:
            flagged, direction = True, "below"
        else:
            flagged, direction = False, "within"

        severity = _compute_severity(cost, lower, upper, iqr) if flagged else 0.0
        reason = _build_reason(cost, lower, upper, sector, direction) if flagged else ""

        results.append(asdict(CostAnomalyResult(
            project_id=pid,
            detector="cost_anomaly",
            is_flagged=flagged,
            original_cost_lakhs=cost,
            sector=sector,
            lower_bound=lower,
            upper_bound=upper,
            severity=severity,
            direction=direction,
            reason=reason,
        )))

    return results


def detect_flagged(df: pd.DataFrame) -> list[dict]:
    """Convenience: return only the flagged results."""
    return [r for r in detect(df) if r["is_flagged"]]

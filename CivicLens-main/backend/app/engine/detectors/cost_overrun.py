"""
CivicLens - Cost Overrun Detector
===================================

PURPOSE:
    Identifies projects where the revised cost has increased significantly
    compared with the original cost.  A large cost overrun may indicate
    scope creep, procurement issues, or situations that merit human review.

    This detector identifies a *review signal* only.  It does NOT
    claim fraud or wrongdoing.

METHOD:
    cost_overrun_pct = ((revised_cost - original_cost) / original_cost) * 100

    A project is flagged when cost_overrun_pct > threshold.

    The default threshold (20%) is a prototype/hackathon rule sourced
    from ``config.COST_OVERRUN_THRESHOLD``, not an official government
    standard.

SEVERITY:
    Normalised 0.0-1.0:  severity = min(cost_overrun_pct / 100, 1.0)
    A 100% cost overrun (doubled cost) maps to severity 1.0.
"""

from dataclasses import dataclass, asdict

import pandas as pd

from app.config import settings


# ---------------------------------------------------------------------------
# Result data structure
# ---------------------------------------------------------------------------
@dataclass
class CostOverrunResult:
    """Detection result for a single project."""

    project_id: str
    detector: str  # always "cost_overrun"
    is_flagged: bool
    original_cost_lakhs: float
    revised_cost_lakhs: float
    cost_overrun_pct: float
    threshold: float
    severity: float  # 0.0-1.0
    direction: str  # "overrun" | "no_overrun" | "invalid_original_cost"
    reason: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _compute_overrun_pct(original: float, revised: float) -> float | None:
    """
    Compute cost overrun percentage.  Returns None if original cost
    is zero or negative (division not possible).
    """
    if original <= 0:
        return None
    return round(((revised - original) / original) * 100, 2)


def _compute_severity(overrun_pct: float) -> float:
    """Normalised severity: 100% overrun -> 1.0."""
    if overrun_pct <= 0:
        return 0.0
    return round(min(overrun_pct / 100.0, 1.0), 4)


def _build_reason(
    original: float, revised: float, overrun_pct: float,
) -> str:
    """Return a factual, non-accusatory explanation string."""
    return (
        f"Revised cost (Rs. {revised:,.2f} lakhs) is {overrun_pct:.1f}% "
        f"above the original cost (Rs. {original:,.2f} lakhs)."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def detect(
    df: pd.DataFrame,
    threshold: float | None = None,
) -> list[dict]:
    """
    Run cost-overrun detection on every project in *df*.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ``project_id``, ``original_cost_lakhs``, and
        ``revised_cost_lakhs`` columns.
    threshold : float | None
        Overrun threshold in percentage points.  Defaults to
        ``settings.COST_OVERRUN_THRESHOLD`` (currently 20.0).

    Returns
    -------
    list[dict]
        One ``CostOverrunResult`` dict per project row.
    """
    required_cols = {"project_id", "original_cost_lakhs", "revised_cost_lakhs"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")

    if threshold is None:
        threshold = settings.COST_OVERRUN_THRESHOLD

    results: list[dict] = []

    for _, row in df.iterrows():
        pid = row["project_id"]
        original = float(row["original_cost_lakhs"])
        revised = float(row["revised_cost_lakhs"])

        overrun_pct = _compute_overrun_pct(original, revised)

        # Handle invalid original cost
        if overrun_pct is None:
            results.append(asdict(CostOverrunResult(
                project_id=pid,
                detector="cost_overrun",
                is_flagged=False,
                original_cost_lakhs=original,
                revised_cost_lakhs=revised,
                cost_overrun_pct=0.0,
                threshold=threshold,
                severity=0.0,
                direction="invalid_original_cost",
                reason=(
                    f"Cost overrun cannot be calculated: "
                    f"original cost is zero or negative "
                    f"(Rs. {original:,.2f} lakhs)."
                ),
            )))
            continue

        if overrun_pct > threshold:
            flagged = True
            direction = "overrun"
            severity = _compute_severity(overrun_pct)
            reason = _build_reason(original, revised, overrun_pct)
        else:
            flagged = False
            direction = "overrun" if overrun_pct > 0 else "no_overrun"
            severity = 0.0
            reason = ""

        results.append(asdict(CostOverrunResult(
            project_id=pid,
            detector="cost_overrun",
            is_flagged=flagged,
            original_cost_lakhs=original,
            revised_cost_lakhs=revised,
            cost_overrun_pct=overrun_pct,
            threshold=threshold,
            severity=severity,
            direction=direction,
            reason=reason,
        )))

    return results


def detect_flagged(
    df: pd.DataFrame,
    threshold: float | None = None,
) -> list[dict]:
    """Convenience: return only the flagged results."""
    return [r for r in detect(df, threshold) if r["is_flagged"]]

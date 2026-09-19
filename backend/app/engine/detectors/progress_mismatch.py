"""
CivicLens - Expenditure vs Physical Progress Mismatch Detector
================================================================

PURPOSE:
    Identifies projects where financial progress (expenditure as a
    percentage of revised cost) significantly diverges from reported
    physical progress.  A large gap may indicate data-entry errors,
    stalled procurement, or situations that merit human review.

    This detector identifies a *review signal* only.  It does NOT
    claim fraud or wrongdoing.

METHOD:
    financial_progress_pct = (expenditure_lakhs / revised_cost_lakhs) * 100
    mismatch_pct = abs(financial_progress_pct - physical_progress_pct)

    A project is flagged when mismatch_pct > PROGRESS_MISMATCH_THRESHOLD.

    The threshold (default 25 percentage points) is a prototype/hackathon
    rule, not an official government standard.

DIRECTION:
    - "financial_ahead": money spent faster than physical work reported
    - "physical_ahead":  physical work reported faster than money spent
    - "aligned":         within threshold
"""

from dataclasses import dataclass, asdict

import pandas as pd


# ---------------------------------------------------------------------------
# Result data structure
# ---------------------------------------------------------------------------
@dataclass
class ProgressMismatchResult:
    """Detection result for a single project."""

    project_id: str
    detector: str  # always "progress_mismatch"
    is_flagged: bool
    financial_progress_pct: float
    physical_progress_pct: float
    mismatch_pct: float
    threshold: float
    severity: float  # 0.0-1.0 normalised
    direction: str  # "financial_ahead", "physical_ahead", or "aligned"
    reason: str


# ---------------------------------------------------------------------------
# Core detection logic
# ---------------------------------------------------------------------------
_DEFAULT_THRESHOLD = 25.0


def _safe_financial_progress(expenditure: float, revised_cost: float) -> float | None:
    """
    Compute financial progress percentage, returning None if the
    revised cost is zero or negative (invalid for division).
    """
    if revised_cost <= 0:
        return None
    return round((expenditure / revised_cost) * 100, 2)


def _compute_severity(mismatch: float, threshold: float) -> float:
    """
    Normalised severity: 0.0 at threshold, approaches 1.0 at 3x threshold.
    """
    if threshold <= 0 or mismatch <= threshold:
        return 0.0
    excess = mismatch - threshold
    return round(min(excess / (2.0 * threshold), 1.0), 4)


def _build_reason(
    financial_pct: float,
    physical_pct: float,
    mismatch: float,
    direction: str,
) -> str:
    """Return a human-readable, non-accusatory explanation string."""
    if direction == "financial_ahead":
        return (
            f"Financial progress ({financial_pct:.1f}%) is {mismatch:.1f} "
            f"percentage points ahead of reported physical progress "
            f"({physical_pct:.1f}%)."
        )
    if direction == "physical_ahead":
        return (
            f"Physical progress ({physical_pct:.1f}%) is {mismatch:.1f} "
            f"percentage points ahead of financial progress "
            f"({financial_pct:.1f}%)."
        )
    return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def detect(df: pd.DataFrame, threshold: float = _DEFAULT_THRESHOLD) -> list[dict]:
    """
    Run progress-mismatch detection on every project in *df*.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ``project_id``, ``expenditure_lakhs``,
        ``revised_cost_lakhs``, and ``physical_progress_pct`` columns.
    threshold : float
        Mismatch threshold in percentage points (default 25.0).

    Returns
    -------
    list[dict]
        One ``ProgressMismatchResult`` dict per project row.
    """
    required_cols = {
        "project_id", "expenditure_lakhs",
        "revised_cost_lakhs", "physical_progress_pct",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")

    results: list[dict] = []

    for _, row in df.iterrows():
        pid = row["project_id"]
        expenditure = float(row["expenditure_lakhs"])
        revised_cost = float(row["revised_cost_lakhs"])
        physical_pct = float(row["physical_progress_pct"])

        financial_pct = _safe_financial_progress(expenditure, revised_cost)

        # Handle invalid revised cost — not a mismatch, just non-computable
        if financial_pct is None:
            results.append(asdict(ProgressMismatchResult(
                project_id=pid,
                detector="progress_mismatch",
                is_flagged=False,
                financial_progress_pct=0.0,
                physical_progress_pct=physical_pct,
                mismatch_pct=0.0,
                threshold=threshold,
                severity=0.0,
                direction="invalid_cost",
                reason=(
                    f"Financial progress could not be computed: "
                    f"revised cost is zero or negative "
                    f"(Rs. {revised_cost:,.2f} lakhs)."
                ),
            )))
            continue

        mismatch = round(abs(financial_pct - physical_pct), 2)

        if mismatch > threshold:
            flagged = True
            if financial_pct > physical_pct:
                direction = "financial_ahead"
            else:
                direction = "physical_ahead"
        else:
            flagged = False
            direction = "aligned"

        severity = _compute_severity(mismatch, threshold) if flagged else 0.0
        reason = _build_reason(financial_pct, physical_pct, mismatch, direction) if flagged else ""

        results.append(asdict(ProgressMismatchResult(
            project_id=pid,
            detector="progress_mismatch",
            is_flagged=flagged,
            financial_progress_pct=financial_pct,
            physical_progress_pct=physical_pct,
            mismatch_pct=mismatch,
            threshold=threshold,
            severity=severity,
            direction=direction,
            reason=reason,
        )))

    return results


def detect_flagged(df: pd.DataFrame, threshold: float = _DEFAULT_THRESHOLD) -> list[dict]:
    """Convenience: return only the flagged results."""
    return [r for r in detect(df, threshold) if r["is_flagged"]]

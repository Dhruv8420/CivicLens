"""
CivicLens - Delay Detector
============================

PURPOSE:
    Identifies projects whose revised completion date has passed while
    the project remains incomplete.  A delayed project may indicate
    resource bottlenecks, scope changes, or situations that merit
    human review.

    This detector identifies a *review signal* only.  It does NOT
    claim fraud or wrongdoing.

RULES:
    A project is flagged as delayed when ALL of the following are true:

    1. revised_completion_date < reference_date  (deadline has passed)
    2. status is NOT "Completed"
    3. status is NOT "Planning"  (not eligible for delay detection)
    4. revised_completion_date is present and valid

    Completed projects are never delayed (they finished).
    Planning projects are excluded because they have not started
    execution, so a passed deadline is a scheduling issue rather
    than a project delay.

SEVERITY:
    Normalised 0.0-1.0 based on days delayed:
        severity = min(days_delayed / 730, 1.0)

    730 days (2 years) maps to severity 1.0.  This is a prototype
    hackathon heuristic, not an official government standard.
"""

from dataclasses import dataclass, asdict
from datetime import date, datetime

import pandas as pd


# ---------------------------------------------------------------------------
# Result data structure
# ---------------------------------------------------------------------------
@dataclass
class DelayResult:
    """Detection result for a single project."""

    project_id: str
    detector: str  # always "delay"
    is_flagged: bool
    revised_completion_date: str  # ISO string or ""
    reference_date: str  # ISO string
    days_delayed: int
    status: str
    severity: float  # 0.0-1.0
    reason: str


# Only these statuses are eligible for delay flagging
_DELAY_ELIGIBLE_STATUSES = {"In Progress", "Stalled"}

# Days at which severity reaches 1.0
_MAX_DELAY_DAYS = 730


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_date(value) -> date | None:
    """
    Safely parse a date value.  Accepts ``datetime.date``,
    ``datetime.datetime``, ISO-format strings, and pandas Timestamps.
    Returns None for missing / unparseable values.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, str):
        value = value.strip()
        if not value or value.lower() in ("", "nat", "none", "null"):
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _compute_severity(days_delayed: int) -> float:
    """Normalised severity: 0.0 at 0 days, 1.0 at 730+ days."""
    if days_delayed <= 0:
        return 0.0
    return round(min(days_delayed / _MAX_DELAY_DAYS, 1.0), 4)


def _build_reason(days: int, status: str) -> str:
    """Return a human-readable, non-accusatory explanation string."""
    return (
        f"Project is {days} days past its revised completion date "
        f"and is still {status}."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def detect(
    df: pd.DataFrame,
    reference_date: date | None = None,
) -> list[dict]:
    """
    Run delay detection on every project in *df*.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ``project_id``, ``revised_completion_date``,
        and ``status`` columns.
    reference_date : date | None
        The date to compare deadlines against.  Defaults to today
        if None.  Inject a fixed date for deterministic testing.

    Returns
    -------
    list[dict]
        One ``DelayResult`` dict per project row.
    """
    required_cols = {"project_id", "revised_completion_date", "status"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")

    if reference_date is None:
        reference_date = date.today()

    ref_str = reference_date.isoformat()
    results: list[dict] = []

    for _, row in df.iterrows():
        pid = row["project_id"]
        status = str(row["status"]).strip()
        raw_date = row["revised_completion_date"]
        revised = _parse_date(raw_date)

        # Cannot determine delay without a valid date
        if revised is None:
            results.append(asdict(DelayResult(
                project_id=pid,
                detector="delay",
                is_flagged=False,
                revised_completion_date="",
                reference_date=ref_str,
                days_delayed=0,
                status=status,
                severity=0.0,
                reason="Revised completion date is missing or invalid; "
                       "delay cannot be determined.",
            )))
            continue

        revised_str = revised.isoformat()
        days_past = (reference_date - revised).days

        # Determine if delayed
        deadline_passed = days_past > 0
        eligible = status in _DELAY_ELIGIBLE_STATUSES
        flagged = deadline_passed and eligible

        if flagged:
            severity = _compute_severity(days_past)
            reason = _build_reason(days_past, status)
        else:
            days_past = max(days_past, 0)
            severity = 0.0
            reason = ""

        results.append(asdict(DelayResult(
            project_id=pid,
            detector="delay",
            is_flagged=flagged,
            revised_completion_date=revised_str,
            reference_date=ref_str,
            days_delayed=days_past if flagged else 0,
            status=status,
            severity=severity,
            reason=reason,
        )))

    return results


def detect_flagged(
    df: pd.DataFrame,
    reference_date: date | None = None,
) -> list[dict]:
    """Convenience: return only the flagged results."""
    return [r for r in detect(df, reference_date) if r["is_flagged"]]

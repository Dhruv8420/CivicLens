"""
CivicLens — Dataset Adapter & Validation Module
=================================================

PURPOSE:
    Ingests raw uploaded CSV files, validates structure and contents,
    normalizes column headers to canonical schema names using flexible alias rules,
    sanitizes types, and determines which detectors have valid column inputs.
"""

from dataclasses import dataclass
import io
import re
from typing import Any
import pandas as pd


MAX_UPLOAD_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class DatasetIngestionError(Exception):
    """Raised when an uploaded file cannot be parsed or lacks mandatory fields."""

    pass


# Mapping canonical key -> list of common header aliases (lowercase, stripped)
CANONICAL_ALIASES: dict[str, list[str]] = {
    "project_id": [
        "project_id", "projectid", "prj_id", "id", "code", "project_code",
        "ref_no", "sl_no", "s_no", "project_no", "serial_no", "sl.no"
    ],
    "project_name": [
        "project_name", "name", "title", "project_title", "work_name", "scheme_name"
    ],
    "sector": [
        "sector", "category", "sub_sector", "domain", "department_sector", "sector_name"
    ],
    "original_cost_lakhs": [
        "original_cost_lakhs", "original_cost", "sanctioned_cost", "approved_cost",
        "original_cost_(rs_lakhs)", "sanctioned_cost_lakhs", "original_cost_rs_lakhs",
        "sanctioned_cost_in_lakhs", "approved_cost_lakhs", "original_cost_(lakhs)",
        "sanctioned_cost_rs_lakhs", "sanctioned_cost_(rs_lakhs)"
    ],
    "revised_cost_lakhs": [
        "revised_cost_lakhs", "revised_cost", "latest_cost", "latest_approved_cost",
        "revised_cost_(rs_lakhs)", "anticipated_cost", "revised_cost_rs_lakhs",
        "anticipated_cost_lakhs", "revised_cost_(lakhs)"
    ],
    "expenditure_lakhs": [
        "expenditure_lakhs", "expenditure", "cumulative_expenditure", "total_expenditure",
        "expenditure_(rs_lakhs)", "financial_progress_lakhs", "expenditure_rs_lakhs",
        "total_expenditure_lakhs", "expenditure_(lakhs)"
    ],
    "physical_progress_pct": [
        "physical_progress_pct", "physical_progress", "progress_pct", "completion_pct",
        "progress_%", "physical_progress_(%)", "physical_progress_percentage",
        "progress_percentage", "physical_progress_pct"
    ],
    "start_date": [
        "start_date", "date_of_start", "commencement_date", "sanction_date", "startdate"
    ],
    "target_completion_date": [
        "target_completion_date", "target_date", "original_completion_date", "doc",
        "target_date_of_completion"
    ],
    "revised_completion_date": [
        "revised_completion_date", "revised_doc", "anticipated_completion_date",
        "expected_doc", "revised_date_of_completion"
    ],
    "status": [
        "status", "project_status", "stage", "current_status"
    ],
    "department": [
        "department", "ministry", "agency", "dept"
    ],
    "state": [
        "state", "province", "region", "location"
    ],
}


@dataclass
class AdapterResult:
    """Output container for processed CSV datasets."""

    df: pd.DataFrame
    detector_availability: dict[str, dict[str, Any]]
    warnings: list[str]
    filename: str


def _normalize_header(header: str) -> str:
    """Clean and normalize header text for fuzzy matching."""
    s = header.strip().lower()
    s = re.sub(r"[\(\)\,\%]+", "", s)
    s = re.sub(r"[\s\-\.\/]+", "_", s)
    return s.strip("_")


def _map_columns_to_canonical(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Rename DataFrame columns to canonical names using alias dictionary."""
    renames: dict[str, str] = {}
    warnings: list[str] = []
    normalized_headers = {_normalize_header(col): col for col in df.columns}

    # Match canonical keys
    mapped_canonical: set[str] = set()
    for canonical_key, aliases in CANONICAL_ALIASES.items():
        for alias in aliases:
            norm_alias = _normalize_header(alias)
            if norm_alias in normalized_headers:
                orig_col = normalized_headers[norm_alias]
                if orig_col not in renames and canonical_key not in mapped_canonical:
                    renames[orig_col] = canonical_key
                    mapped_canonical.add(canonical_key)
                    break

    df = df.rename(columns=renames)
    return df, warnings


def _clean_numeric_series(series: pd.Series) -> pd.Series:
    """Sanitize currency and percentage strings and convert to float."""
    if series.dtype == object or isinstance(series.dtype, pd.StringDtype):
        cleaned = series.astype(str).str.replace(r"[Rs\$\,\%\s]", "", regex=True)
        return pd.to_numeric(cleaned, errors="coerce")
    return pd.to_numeric(series, errors="coerce")


def process_csv_bytes(file_bytes: bytes, filename: str) -> AdapterResult:
    """
    Parse, validate, map, and evaluate detector availability for uploaded CSV bytes.

    Parameters
    ----------
    file_bytes : bytes
        Raw CSV bytes.
    filename : str
        Name of uploaded file.

    Returns
    -------
    AdapterResult
        Contains normalized DataFrame, detector availability dict, and warnings.
    """
    if len(file_bytes) > MAX_UPLOAD_FILE_SIZE_BYTES:
        raise DatasetIngestionError(
            f"File '{filename}' exceeds maximum allowed size of 10 MB."
        )

    if not file_bytes or len(file_bytes.strip()) == 0:
        raise DatasetIngestionError(f"Uploaded CSV file '{filename}' is empty.")

    # Try UTF-8 first, fallback to latin-1
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("latin-1")
        except Exception:
            raise DatasetIngestionError(
                f"File '{filename}' has invalid encoding. Please save as UTF-8 CSV."
            )

    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception as e:
        raise DatasetIngestionError(f"Failed to parse CSV: {str(e)}")

    if len(df) == 0:
        raise DatasetIngestionError("CSV file contains no data rows.")

    df, warnings = _map_columns_to_canonical(df)

    if "project_id" not in df.columns:
        avail_cols = sorted(list(df.columns))
        raise DatasetIngestionError(
            f"CSV missing mandatory column 'project_id'. Detected headers: {avail_cols}"
        )

    # Clean project_id
    df["project_id"] = df["project_id"].astype(str).str.strip()

    # Handle duplicate project IDs
    if df["project_id"].duplicated().any():
        warnings.append(
            "Duplicate project_ids detected. Appended row suffixes to ensure unique identifiers."
        )
        df["project_id"] = (
            df["project_id"] + "_row" + (df.index + 1).astype(str)
        )

    # Default metadata if missing
    if "sector" not in df.columns:
        df["sector"] = "General"
        warnings.append("Column 'sector' missing; defaulted to 'General'.")
    else:
        df["sector"] = df["sector"].fillna("General").astype(str).str.strip()

    if "status" not in df.columns:
        df["status"] = "In Progress"
        warnings.append("Column 'status' missing; defaulted to 'In Progress'.")
    else:
        df["status"] = df["status"].fillna("In Progress").astype(str).str.strip()

    # Clean numeric columns
    numeric_cols = [
        "original_cost_lakhs",
        "revised_cost_lakhs",
        "expenditure_lakhs",
        "physical_progress_pct",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = _clean_numeric_series(df[col])

    # Clean revised_completion_date
    if "revised_completion_date" in df.columns:
        df["revised_completion_date"] = df["revised_completion_date"].astype(str).str.strip()

    # Evaluate Detector Availability
    detector_availability: dict[str, dict[str, Any]] = {}

    # 1. Cost Anomaly
    if "original_cost_lakhs" in df.columns and df["original_cost_lakhs"].notna().sum() > 0:
        detector_availability["cost_anomaly"] = {
            "available": True,
            "missing_columns": [],
            "reason": "Evaluated using 'original_cost_lakhs' and 'sector'.",
        }
    else:
        detector_availability["cost_anomaly"] = {
            "available": False,
            "missing_columns": ["original_cost_lakhs"],
            "reason": "Skipped: Missing required column 'original_cost_lakhs'.",
        }

    # 2. Progress Mismatch
    pm_required = ["expenditure_lakhs", "revised_cost_lakhs", "physical_progress_pct"]
    pm_missing = [c for c in pm_required if c not in df.columns or df[c].notna().sum() == 0]
    if not pm_missing:
        detector_availability["progress_mismatch"] = {
            "available": True,
            "missing_columns": [],
            "reason": "Evaluated using expenditure, revised cost, and physical progress.",
        }
    else:
        detector_availability["progress_mismatch"] = {
            "available": False,
            "missing_columns": pm_missing,
            "reason": f"Skipped: Missing required column(s): {', '.join(pm_missing)}.",
        }

    # 3. Delay
    delay_has_date = (
        ("revised_completion_date" in df.columns and df["revised_completion_date"].notna().sum() > 0)
        or ("target_completion_date" in df.columns and df["target_completion_date"].notna().sum() > 0)
    )
    if delay_has_date and "status" in df.columns:
        detector_availability["delay"] = {
            "available": True,
            "missing_columns": [],
            "reason": "Evaluated using completion date and status.",
        }
    else:
        missing_delay = []
        if not delay_has_date:
            missing_delay.append("revised_completion_date")
        if "status" not in df.columns:
            missing_delay.append("status")
        detector_availability["delay"] = {
            "available": False,
            "missing_columns": missing_delay,
            "reason": f"Skipped: Missing required column(s): {', '.join(missing_delay)}.",
        }

    # 4. Cost Overrun
    co_required = ["original_cost_lakhs", "revised_cost_lakhs"]
    co_missing = [c for c in co_required if c not in df.columns or df[c].notna().sum() == 0]
    if not co_missing:
        detector_availability["cost_overrun"] = {
            "available": True,
            "missing_columns": [],
            "reason": "Evaluated using original cost and revised cost.",
        }
    else:
        detector_availability["cost_overrun"] = {
            "available": False,
            "missing_columns": co_missing,
            "reason": f"Skipped: Missing required column(s): {', '.join(co_missing)}.",
        }

    return AdapterResult(
        df=df,
        detector_availability=detector_availability,
        warnings=warnings,
        filename=filename,
    )

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
        "project_name", "projectname", "name", "title", "project_title", "work_name", "scheme_name"
    ],
    "sector": [
        "sector", "sectorname", "sector_name", "category", "sub_sector", "domain", "department_sector"
    ],
    "original_cost_lakhs": [
        "original_cost_lakhs", "original_cost", "projectcost", "project_cost", "sanctioned_cost", "approved_cost",
        "original_cost_(rs_lakhs)", "sanctioned_cost_lakhs", "original_cost_rs_lakhs",
        "sanctioned_cost_in_lakhs", "approved_cost_lakhs", "original_cost_(lakhs)",
        "sanctioned_cost_rs_lakhs", "sanctioned_cost_(rs_lakhs)"
    ],
    "revised_cost_lakhs": [
        "revised_cost_lakhs", "revised_cost", "revisedcost", "latest_cost", "latest_approved_cost",
        "revised_cost_(rs_lakhs)", "anticipated_cost", "revised_cost_rs_lakhs",
        "anticipated_cost_lakhs", "revised_cost_(lakhs)"
    ],
    "expenditure_lakhs": [
        "expenditure_lakhs", "expenditure", "texpend", "t_expend", "cumulative_expenditure", "total_expenditure",
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
        "department", "ministry", "lineministry", "line_ministry", "agency", "dept"
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


def _is_mospi_paimana_dataset(df: pd.DataFrame) -> bool:
    """
    Check if the DataFrame positively matches the MoSPI PAIMANA official header schema.
    Requires presence of MoSPI-specific source column names.
    """
    normalized = {_normalize_header(col) for col in df.columns}
    mospi_required_headers = {
        "projectid",
        "projectname",
        "sectorname",
        "lineministry",
        "projectcost",
        "revisedcost",
        "texpend",
    }
    return mospi_required_headers.issubset(normalized)


def _map_columns_to_canonical(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], bool]:
    """Rename DataFrame columns to canonical names using alias dictionary and detect MoSPI fingerprint."""
    renames: dict[str, str] = {}
    warnings: list[str] = []
    normalized_headers = {_normalize_header(col): col for col in df.columns}
    
    is_mospi = _is_mospi_paimana_dataset(df)

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
    return df, warnings, is_mospi


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

    df, warnings, is_mospi = _map_columns_to_canonical(df)

    if "project_id" not in df.columns:
        avail_cols = sorted(list(df.columns))
        raise DatasetIngestionError(
            f"CSV missing mandatory column 'project_id'. Detected headers: {avail_cols}"
        )

    # Clean project_id
    df["project_id"] = df["project_id"].astype(str).str.strip()

    # Handle duplicate project IDs
    if is_mospi:
        raw_rows = len(df)
        dup_pid_mask = df.duplicated(subset=["project_id"], keep=False)
        if dup_pid_mask.any():
            relevant_cols = [
                c for c in [
                    "project_id", "project_name", "sector", "department",
                    "original_cost_lakhs", "revised_cost_lakhs", "expenditure_lakhs"
                ] if c in df.columns
            ]
            
            # Group by project_id and check for value conflicts
            conflicts = []
            grouped = df[dup_pid_mask].groupby("project_id")
            for pid, group in grouped:
                if group[relevant_cols].drop_duplicates().shape[0] > 1:
                    conflicts.append(str(pid))

            if conflicts:
                warnings.append(
                    f"MoSPI dataset contains {len(conflicts)} ProjectID(s) with conflicting data values: {conflicts[:5]}. Preserved all rows."
                )
            else:
                # Exact duplicates verified - safe to collapse
                df = df.drop_duplicates(subset=relevant_cols, keep="first").reset_index(drop=True)
                exact_removed = raw_rows - len(df)
                warnings.append(
                    f"MoSPI PAIMANA dataset: Identified and collapsed {exact_removed} exact duplicate project records ({len(df)} unique projects retained out of {raw_rows} raw rows)."
                )
    elif df["project_id"].duplicated().any():
        init_count = len(df)
        counts: dict[str, int] = {}
        new_pids: list[str] = []
        for pid in df["project_id"]:
            if pid in counts:
                counts[pid] += 1
                new_pids.append(f"{pid}_{counts[pid]}")
            else:
                counts[pid] = 1
                new_pids.append(pid)
        df["project_id"] = new_pids
        warnings.append(
            f"Duplicate project_ids detected ({init_count - len(counts)} duplicates). Appended unique suffixes to preserve all {init_count} rows."
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
            # Convert Crores to Lakhs ONLY when MoSPI fingerprint is positively matched
            if is_mospi and col in ["original_cost_lakhs", "revised_cost_lakhs", "expenditure_lakhs"]:
                df[col] = df[col] * 100.0

    if is_mospi:
        warnings.append("MoSPI PAIMANA dataset detected: Converted monetary values from Crores to Lakhs (multiplied by 100).")

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
            "reason": None,
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
            "reason": None,
        }
    else:
        pm_reason = (
            "Skipped: Physical progress % is not provided in the MoSPI PAIMANA upload."
            if is_mospi
            else f"Skipped: Missing required column(s): {', '.join(pm_missing)}."
        )
        detector_availability["progress_mismatch"] = {
            "available": False,
            "missing_columns": pm_missing,
            "reason": pm_reason,
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
            "reason": None,
        }
    else:
        missing_delay = []
        if not delay_has_date:
            missing_delay.append("revised_completion_date")
        if "status" not in df.columns:
            missing_delay.append("status")
        delay_reason = (
            "Skipped: Target and revised completion dates are not provided in the MoSPI PAIMANA upload."
            if is_mospi
            else f"Skipped: Missing required column(s): {', '.join(missing_delay)}."
        )
        detector_availability["delay"] = {
            "available": False,
            "missing_columns": missing_delay,
            "reason": delay_reason,
        }

    # 4. Cost Overrun
    co_required = ["original_cost_lakhs", "revised_cost_lakhs"]
    co_missing = [c for c in co_required if c not in df.columns or df[c].notna().sum() == 0]
    if not co_missing:
        detector_availability["cost_overrun"] = {
            "available": True,
            "missing_columns": [],
            "reason": None,
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

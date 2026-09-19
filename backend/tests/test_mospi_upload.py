"""
Tests for MoSPI PAIMANA Real Dataset Ingestion & Upload Analysis
================================================================
"""

import os
import io
import pytest
import pandas as pd
from app.services.dataset_adapter import process_csv_bytes, _is_mospi_paimana_dataset
from app.services.analysis_service import AnalysisService


MOSPI_CSV_PATH = os.path.join("scratch", "real_data", "mospi_paimana", "paimana_projects_full.csv")


def test_mospi_adapter_ingestion():
    """Test that MoSPI PAIMANA CSV is correctly recognized, mapped, deduplicated, and converted from Crores to Lakhs."""
    assert os.path.exists(MOSPI_CSV_PATH), f"MoSPI CSV file not found at {MOSPI_CSV_PATH}"
    
    with open(MOSPI_CSV_PATH, "rb") as f:
        file_bytes = f.read()

    # Read raw dataframe to verify fingerprinting directly
    df_raw = pd.read_csv(io.BytesIO(file_bytes))
    assert _is_mospi_paimana_dataset(df_raw) is True

    result = process_csv_bytes(file_bytes, "paimana_projects_full.csv")

    assert result.df is not None
    # 2201 raw rows -> 214 exact duplicate rows removed -> 1987 unique projects retained
    assert len(result.df) == 1987
    
    # Verify column mapping
    assert "project_id" in result.df.columns
    assert "project_name" in result.df.columns
    assert "original_cost_lakhs" in result.df.columns
    assert "revised_cost_lakhs" in result.df.columns
    assert "expenditure_lakhs" in result.df.columns
    assert "sector" in result.df.columns
    assert "department" in result.df.columns

    # Verify unit conversion (480.00 Cr -> 48000.00 Lakhs)
    leh_project = result.df[result.df["project_id"] == "400010"].iloc[0]
    assert leh_project["original_cost_lakhs"] == pytest.approx(48000.0)
    assert leh_project["revised_cost_lakhs"] == pytest.approx(64000.0)
    assert leh_project["expenditure_lakhs"] == pytest.approx(50613.0)

    # Verify absence of fabricated fields
    assert "physical_progress_pct" not in result.df.columns or result.df["physical_progress_pct"].isna().all()
    assert "revised_completion_date" not in result.df.columns or result.df["revised_completion_date"].isna().all()

    # Step 4.11 check: Verify status is NOT fabricated to 'In Progress' for MoSPI
    assert "status" not in result.df.columns or (result.df["status"] != "In Progress").all()
    status_warnings = [w for w in result.warnings if "status" in w.lower()]
    assert len(status_warnings) == 0, f"Unexpected status fabrication warning found: {status_warnings}"

    # Verify detector availability
    avail = result.detector_availability
    assert avail["cost_anomaly"]["available"] is True
    assert avail["cost_overrun"]["available"] is True
    assert avail["progress_mismatch"]["available"] is False
    assert "MoSPI PAIMANA upload" in avail["progress_mismatch"]["reason"]
    assert avail["delay"]["available"] is False
    assert "MoSPI PAIMANA upload" in avail["delay"]["reason"]


def test_mospi_analysis_service_integration():
    """Test that full analysis engine processes MoSPI dataset without error and handles partial detector coverage."""
    with open(MOSPI_CSV_PATH, "rb") as f:
        file_bytes = f.read()

    service = AnalysisService()
    result = service.analyze_uploaded_dataset(file_bytes, "paimana_projects_full.csv")

    assert result is not None
    assert result["total_projects"] == 1987
    assert "detector_availability" in result
    assert result["detector_availability"]["cost_anomaly"]["available"] is True
    assert result["detector_availability"]["cost_overrun"]["available"] is True
    assert result["detector_availability"]["progress_mismatch"]["available"] is False
    assert result["detector_availability"]["delay"]["available"] is False
    
    # Check evaluated project structure & partial coverage status
    assert len(result["projects"]) == 1987
    p0 = result["projects"][0]
    assert p0["project_id"] != ""
    assert p0["risk_score"] >= 0.0
    
    # Verify inactive detectors are marked as missing_data, NOT clean evaluated detectors
    contribs = p0["detector_contributions"]
    assert contribs["progress_mismatch"]["status"] == "missing_data"
    assert contribs["progress_mismatch"]["is_flagged"] is False
    assert contribs["delay"]["status"] == "missing_data"
    assert contribs["delay"]["is_flagged"] is False


def test_generic_csv_no_crores_scaling():
    """Test that generic non-MoSPI CSV with project_cost is NOT scaled by 100."""
    csv_data = (
        "project_id,project_name,project_cost,sector\n"
        "PRJ-GEN-01,Generic Road Project,480.0,Transport\n"
    )
    
    # Read raw to verify it does NOT trigger MoSPI fingerprint
    df_raw = pd.read_csv(io.StringIO(csv_data))
    assert _is_mospi_paimana_dataset(df_raw) is False

    result = process_csv_bytes(csv_data.encode("utf-8"), "generic_project.csv")
    assert result.df["original_cost_lakhs"].iloc[0] == pytest.approx(480.0)  # Must remain 480.0 Lakhs


def test_generic_csv_duplicate_suffixes():
    """Test that generic non-MoSPI CSV with duplicate project_ids uses suffix disambiguation."""
    csv_data = (
        "project_id,project_name,sector,original_cost_lakhs\n"
        "PRJ-DUP,School A,Education,300.0\n"
        "PRJ-DUP,School B,Education,400.0\n"
    )
    result = process_csv_bytes(csv_data.encode("utf-8"), "generic_dups.csv")
    assert len(result.df) == 2
    assert list(result.df["project_id"]) == ["PRJ-DUP", "PRJ-DUP_2"]


def test_generic_csv_status_fallback_preserved():
    """Test that generic non-MoSPI CSV without status still receives the 'In Progress' fallback and warning."""
    csv_data = (
        "project_id,project_name,sector,original_cost_lakhs\n"
        "PRJ-GEN-STAT,Road Work,Transport,500.0\n"
    )
    result = process_csv_bytes(csv_data.encode("utf-8"), "generic_no_status.csv")
    assert "status" in result.df.columns
    assert result.df["status"].iloc[0] == "In Progress"
    status_warns = [w for w in result.warnings if "status" in w.lower()]
    assert len(status_warns) == 1
    assert "defaulted to 'In Progress'" in status_warns[0]

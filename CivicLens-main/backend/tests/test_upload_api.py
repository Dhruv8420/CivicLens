"""
CivicLens — Dataset Upload API Test Suite
============================================

Tests for CSV dataset upload, canonical column mapping, detector availability evaluation,
and error handling via FastAPI TestClient.
"""

import io
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_upload_valid_full_csv():
    """Test uploading a valid CSV with all detector columns present."""
    csv_data = (
        "project_id,sector,original_cost_lakhs,revised_cost_lakhs,expenditure_lakhs,"
        "physical_progress_pct,revised_completion_date,status\n"
        "PRJ-U01,Transport,1000.0,1500.0,1200.0,30.0,2025-01-01,In Progress\n"
        "PRJ-U02,Energy,2000.0,2200.0,1000.0,50.0,2026-12-31,In Progress\n"
    )

    response = client.post(
        "/api/analyze/upload",
        files={"file": ("test_projects.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_projects.csv"
    assert data["total_projects"] == 2
    assert "detector_availability" in data
    assert data["detector_availability"]["cost_anomaly"]["available"] is True
    assert data["detector_availability"]["progress_mismatch"]["available"] is True
    assert data["detector_availability"]["delay"]["available"] is True
    assert data["detector_availability"]["cost_overrun"]["available"] is True

    # Check project structure
    p1 = data["projects"][0]
    assert p1["project_id"] in ["PRJ-U01", "PRJ-U02"]
    assert "risk_score" in p1
    assert "risk_level" in p1


def test_upload_partial_detector_availability():
    """Test uploading a dataset missing physical_progress_pct (progress_mismatch unavailable)."""
    csv_data = (
        "project_id,sector,original_cost_lakhs,revised_cost_lakhs,status,revised_completion_date\n"
        "PRJ-P01,Health,500.0,800.0,In Progress,2024-06-01\n"
    )

    response = client.post(
        "/api/analyze/upload",
        files={"file": ("partial.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    avail = data["detector_availability"]

    assert avail["cost_anomaly"]["available"] is True
    assert avail["cost_overrun"]["available"] is True
    assert avail["delay"]["available"] is True
    assert avail["progress_mismatch"]["available"] is False
    assert "physical_progress_pct" in avail["progress_mismatch"]["missing_columns"]

    # Check detector contribution status for progress mismatch
    p = data["projects"][0]
    pm_contrib = p["detector_contributions"]["progress_mismatch"]
    assert pm_contrib["status"] == "missing_data"
    assert pm_contrib["contribution"] == 0.0


def test_upload_missing_mandatory_project_id():
    """Test uploading CSV without project_id header fails with 400 Bad Request."""
    csv_data = "sector,original_cost_lakhs\nTransport,1000.0\n"

    response = client.post(
        "/api/analyze/upload",
        files={"file": ("invalid.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "project_id" in detail


def test_upload_invalid_file_extension():
    """Test uploading a non-CSV file extension fails with 400."""
    response = client.post(
        "/api/analyze/upload",
        files={"file": ("data.txt", io.BytesIO(b"some text data"), "text/plain")},
    )

    assert response.status_code == 400
    assert "CSV format" in response.json()["detail"]


def test_upload_empty_csv():
    """Test uploading empty file fails with 400."""
    response = client.post(
        "/api/analyze/upload",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_duplicate_project_ids():
    """Test that duplicate project_ids are made unique with row suffixes."""
    csv_data = (
        "project_id,sector,original_cost_lakhs\n"
        "PRJ-DUP,Education,300.0\n"
        "PRJ-DUP,Education,400.0\n"
    )

    response = client.post(
        "/api/analyze/upload",
        files={"file": ("dups.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    pids = [p["project_id"] for p in data["projects"]]
    assert len(pids) == 2
    assert pids[0] != pids[1]
    assert any("Duplicate project_ids" in w for w in data["warnings"])


def test_upload_fuzzy_column_alias_mapping():
    """Test that open dataset header aliases (e.g. data.gov.in format) map cleanly."""
    csv_data = (
        "Project Code,Department Sector,Sanctioned Cost (Rs Lakhs),Anticipated Cost,Project Status\n"
        "GOV-101,Water,1200.0,1800.0,In Progress\n"
    )

    response = client.post(
        "/api/analyze/upload",
        files={"file": ("gov_data.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_projects"] == 1
    p = data["projects"][0]
    assert p["project_id"] == "GOV-101"
    # cost overrun should be available
    assert data["detector_availability"]["cost_overrun"]["available"] is True


def test_upload_unsupported_schema():
    """Test upload with no detector-supported columns yields all missing_data detectors."""
    csv_data = (
        "project_id,random_text_field,notes\n"
        "PRJ-NO-SIG,hello world,some notes\n"
    )

    response = client.post(
        "/api/analyze/upload",
        files={"file": ("no_detectors.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    avail = data["detector_availability"]
    assert avail["cost_anomaly"]["available"] is False
    assert avail["progress_mismatch"]["available"] is False
    assert avail["cost_overrun"]["available"] is False
    assert avail["delay"]["available"] is False
    p = data["projects"][0]
    assert p["risk_score"] == 0.0
    assert p["risk_level"] == "LOW"

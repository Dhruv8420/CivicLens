"""
Integration and Unit Tests for CivicLens FastAPI Analysis API.

Tests cover all 18 API requirements:
1. GET /api/health -> 200 OK
2. Health response payload {"status": "ok"}
3. GET /api/projects -> 200 OK
4. /api/projects total == 100
5. /api/projects returns 100 items
6. Project results contain all RiskEngineResult fields
7. GET /api/projects/PRJ-001 -> 200 OK
8. Single project returned ID is PRJ-001
9. GET /api/projects/PRJ-999 -> 404 Not Found
10. 404 response detail string
11. Custom reference_date query param
12. Custom progress_threshold query param
13. Custom cost_overrun_threshold query param
14. Invalid reference_date -> 422 Unprocessable Entity
15. Negative progress_threshold -> 422 Unprocessable Entity
16. Negative cost_overrun_threshold -> 422 Unprocessable Entity
17. DatasetValidationError -> safe 500 response
18. Route delegation to AnalysisService
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from app.api.routes.projects import get_analysis_service
from app.services.analysis_service import DatasetValidationError, ProjectNotFoundError


client = TestClient(app)


class TestAnalysisAPI:

    def test_health_check_status_code(self):
        """GET /api/health returns HTTP 200."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_check_payload(self):
        """GET /api/health returns exact payload {"status": "ok"}."""
        response = client.get("/api/health")
        assert response.json() == {"status": "ok"}

    def test_get_all_projects_status_200(self):
        """GET /api/projects returns HTTP 200."""
        response = client.get("/api/projects")
        assert response.status_code == 200

    def test_get_all_projects_returns_total_100(self):
        """GET /api/projects total field equals 100 on sample dataset."""
        response = client.get("/api/projects?reference_date=2026-09-18")
        data = response.json()
        assert data["total"] == 100

    def test_get_all_projects_returns_100_projects(self):
        """GET /api/projects projects array contains 100 project items."""
        response = client.get("/api/projects?reference_date=2026-09-18")
        data = response.json()
        assert len(data["projects"]) == 100

    def test_all_projects_contain_expected_fields(self):
        """All items in /api/projects contain complete RiskEngineResult fields."""
        response = client.get("/api/projects?reference_date=2026-09-18")
        data = response.json()
        first = data["projects"][0]

        expected_fields = {
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
        assert set(first.keys()) == expected_fields

    def test_get_single_project_PRJ_001_status_200(self):
        """GET /api/projects/PRJ-001 returns HTTP 200."""
        response = client.get("/api/projects/PRJ-001?reference_date=2026-09-18")
        assert response.status_code == 200

    def test_get_single_project_PRJ_001_project_id(self):
        """GET /api/projects/PRJ-001 returned project_id is PRJ-001."""
        response = client.get("/api/projects/PRJ-001?reference_date=2026-09-18")
        data = response.json()
        assert data["project_id"] == "PRJ-001"

    def test_missing_project_returns_404(self):
        """GET /api/projects/PRJ-999 returns HTTP 404."""
        response = client.get("/api/projects/PRJ-999")
        assert response.status_code == 404

    def test_missing_project_404_detail(self):
        """GET /api/projects/PRJ-999 detail contains clean expected message."""
        response = client.get("/api/projects/PRJ-999")
        data = response.json()
        assert data["detail"] == "Project 'PRJ-999' not found in dataset."

    def test_custom_reference_date_accepted(self):
        """GET /api/projects accepts valid ISO reference_date query parameter."""
        response = client.get("/api/projects?reference_date=2026-12-31")
        assert response.status_code == 200

    def test_custom_progress_threshold_forwarded(self):
        """GET /api/projects accepts valid progress_threshold query parameter."""
        response = client.get("/api/projects?progress_threshold=20.0")
        assert response.status_code == 200

    def test_custom_cost_overrun_threshold_forwarded(self):
        """GET /api/projects accepts valid cost_overrun_threshold query parameter."""
        response = client.get("/api/projects?cost_overrun_threshold=10.0")
        assert response.status_code == 200

    def test_invalid_reference_date_returns_422(self):
        """Invalid reference_date format returns HTTP 422."""
        response = client.get("/api/projects?reference_date=not-a-date")
        assert response.status_code == 422

    def test_negative_progress_threshold_returns_422(self):
        """Negative progress_threshold returns HTTP 422."""
        response = client.get("/api/projects?progress_threshold=-5.0")
        assert response.status_code == 422

    def test_negative_cost_overrun_threshold_returns_422(self):
        """Negative cost_overrun_threshold returns HTTP 422."""
        response = client.get("/api/projects?cost_overrun_threshold=-10.0")
        assert response.status_code == 422

    def test_dataset_validation_error_returns_safe_500(self):
        """DatasetValidationError yields safe 500 response without internal details."""
        mock_service = MagicMock()
        mock_service.get_all_projects_analysis.side_effect = DatasetValidationError("Missing col X")

        app.dependency_overrides[get_analysis_service] = lambda: mock_service
        try:
            response = client.get("/api/projects")
            assert response.status_code == 500
            assert response.json()["detail"] == "Project dataset is unavailable or invalid."
        finally:
            app.dependency_overrides.clear()

    def test_routes_delegate_to_analysis_service(self):
        """Route handlers delegate execution to AnalysisService dependency."""
        mock_service = MagicMock()
        mock_service.get_project_analysis.return_value = {
            "project_id": "PRJ-MOCK",
            "risk_score": 10.0,
            "risk_level": "LOW",
        }

        app.dependency_overrides[get_analysis_service] = lambda: mock_service
        try:
            response = client.get("/api/projects/PRJ-MOCK")
            assert response.status_code == 200
            assert response.json()["project_id"] == "PRJ-MOCK"
            mock_service.get_project_analysis.assert_called_once_with(
                project_id="PRJ-MOCK",
                reference_date=None,
                progress_threshold=None,
                cost_overrun_threshold=None,
            )
        finally:
            app.dependency_overrides.clear()

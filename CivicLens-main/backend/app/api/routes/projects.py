"""
CivicLens — Projects API Router
=================================

FastAPI route handlers exposing project analysis data.
Delegates all dataset and risk analysis to AnalysisService.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.analysis_service import (
    AnalysisService,
    DatasetValidationError,
    ProjectNotFoundError,
)


def get_analysis_service() -> AnalysisService:
    """Dependency provider for AnalysisService."""
    return AnalysisService()


class ProjectsResponse(BaseModel):
    """Response model for all projects analysis endpoint."""

    total: int
    projects: list[dict]


router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=ProjectsResponse)
@router.get("/", response_model=ProjectsResponse, include_in_schema=False)
def get_all_projects(
    reference_date: Annotated[
        date | None,
        Query(description="Optional ISO reference date for delay calculation"),
    ] = None,
    progress_threshold: Annotated[
        float | None,
        Query(ge=0, description="Optional progress mismatch threshold percentage points"),
    ] = None,
    cost_overrun_threshold: Annotated[
        float | None,
        Query(ge=0, description="Optional cost overrun threshold percentage"),
    ] = None,
    service: AnalysisService = Depends(get_analysis_service),
) -> ProjectsResponse:
    """Analyze all projects and return project risk results."""
    try:
        results = service.get_all_projects_analysis(
            reference_date=reference_date,
            progress_threshold=progress_threshold,
            cost_overrun_threshold=cost_overrun_threshold,
        )
        return ProjectsResponse(total=len(results), projects=results)
    except DatasetValidationError:
        raise HTTPException(
            status_code=500,
            detail="Project dataset is unavailable or invalid.",
        )


@router.get("/{project_id}")
def get_project_by_id(
    project_id: str,
    reference_date: Annotated[
        date | None,
        Query(description="Optional ISO reference date for delay calculation"),
    ] = None,
    progress_threshold: Annotated[
        float | None,
        Query(ge=0, description="Optional progress mismatch threshold percentage points"),
    ] = None,
    cost_overrun_threshold: Annotated[
        float | None,
        Query(ge=0, description="Optional cost overrun threshold percentage"),
    ] = None,
    service: AnalysisService = Depends(get_analysis_service),
) -> dict:
    """Analyze a single project by project_id and return complete explainable risk result."""
    try:
        return service.get_project_analysis(
            project_id=project_id,
            reference_date=reference_date,
            progress_threshold=progress_threshold,
            cost_overrun_threshold=cost_overrun_threshold,
        )
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found in dataset.",
        )
    except DatasetValidationError:
        raise HTTPException(
            status_code=500,
            detail="Project dataset is unavailable or invalid.",
        )

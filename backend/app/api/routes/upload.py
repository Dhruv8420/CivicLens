"""
CivicLens — Dataset Upload API Router
========================================

FastAPI route handler for CSV dataset upload and dynamic risk analysis.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.services.analysis_service import AnalysisService
from app.services.dataset_adapter import DatasetIngestionError


def get_analysis_service() -> AnalysisService:
    """Dependency provider for AnalysisService."""
    return AnalysisService()


router = APIRouter(prefix="/api/analyze", tags=["Upload & Analysis"])


@router.post("/upload")
async def upload_and_analyze_dataset(
    file: Annotated[UploadFile, File(description="CSV dataset file to upload and analyze")],
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
    """
    Upload a CSV project dataset, validate structure, determine active detectors,
    and run CivicLens risk engine analysis.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be a CSV format (filename ending in .csv).",
        )

    try:
        file_bytes = await file.read()
        return service.analyze_uploaded_dataset(
            file_bytes=file_bytes,
            filename=file.filename,
            reference_date=reference_date,
            progress_threshold=progress_threshold,
            cost_overrun_threshold=cost_overrun_threshold,
        )
    except DatasetIngestionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while analyzing the dataset: {str(e)}",
        )

"""
CivicLens — Analysis Service
==============================

PURPOSE:
    Orchestration layer between API/application consumers and the Risk Engine.
    Loads and validates project datasets, executes the Risk Engine across all
    projects, and exposes project-level risk analysis.

KEY DESIGN RULES:
    1. Zero Anomaly/Risk Engine Logic: Delegates 100% of detection and scoring
       to `risk_engine.evaluate_projects()`.
    2. Whole Dataset Semantics: Single-project analysis runs the Risk Engine
       over the complete dataset so sector-wise IQR fences remain accurate.
    3. Clean Service Boundary: Contains no FastAPI dependencies. Raises domain
       exceptions (`ProjectNotFoundError`, `DatasetValidationError`).
"""

from datetime import date
from pathlib import Path

import pandas as pd

from app.config import settings
from app.engine import risk_engine


REQUIRED_COLUMNS: set[str] = {
    "project_id",
    "sector",
    "original_cost_lakhs",
    "expenditure_lakhs",
    "revised_cost_lakhs",
    "physical_progress_pct",
    "revised_completion_date",
    "status",
}


class ProjectNotFoundError(Exception):
    """Raised when a requested project_id is not present in the dataset."""

    pass


class DatasetValidationError(Exception):
    """Raised when the input dataset is missing required columns or invalid."""

    pass


class AnalysisService:
    """Service layer orchestrating project dataset analysis via Risk Engine."""

    def __init__(
        self,
        csv_path: str | Path | None = None,
        df: pd.DataFrame | None = None,
    ):
        """
        Initialize AnalysisService.

        Parameters
        ----------
        csv_path : str | Path | None
            Optional explicit path to CSV dataset.
        df : pd.DataFrame | None
            Optional pre-loaded DataFrame (for dependency injection in tests).
        """
        self._csv_path = Path(csv_path) if csv_path is not None else None
        self._df: pd.DataFrame | None = df.copy() if df is not None else None

    def _load_and_validate_dataset(self) -> pd.DataFrame:
        """Load and validate the dataset DataFrame."""
        if self._df is None:
            path_to_load = self._csv_path if self._csv_path is not None else settings.DATASET_PATH
            path_obj = Path(path_to_load)
            if not path_obj.exists():
                raise FileNotFoundError(f"Dataset file not found at: {path_obj}")
            self._df = pd.read_csv(path_obj)

        missing = REQUIRED_COLUMNS - set(self._df.columns)
        if missing:
            raise DatasetValidationError(
                f"Dataset missing required column(s): {sorted(list(missing))}"
            )

        return self._df

    def get_all_projects_analysis(
        self,
        reference_date: date | None = None,
        progress_threshold: float | None = None,
        cost_overrun_threshold: float | None = None,
    ) -> list[dict]:
        """
        Run Risk Engine on all projects in dataset.

        Returns
        -------
        list[dict]
            List of RiskEngineResult dicts. Empty list if dataset has 0 rows.
        """
        df = self._load_and_validate_dataset()

        if len(df) == 0:
            return []

        return risk_engine.evaluate_projects(
            df=df,
            reference_date=reference_date,
            progress_threshold=progress_threshold,
            cost_overrun_threshold=cost_overrun_threshold,
        )

    def get_project_analysis(
        self,
        project_id: str,
        reference_date: date | None = None,
        progress_threshold: float | None = None,
        cost_overrun_threshold: float | None = None,
    ) -> dict:
        """
        Analyze a single project by project_id.

        Runs Risk Engine over the full dataset to preserve sector-wise IQR fences
        and returns the result matching project_id.

        Raises
        ------
        ProjectNotFoundError
            If project_id is not in the dataset or if dataset has 0 rows.
        """
        df = self._load_and_validate_dataset()

        if len(df) == 0 or project_id not in df["project_id"].astype(str).values:
            raise ProjectNotFoundError(f"Project '{project_id}' not found in dataset.")

        all_results = risk_engine.evaluate_projects(
            df=df,
            reference_date=reference_date,
            progress_threshold=progress_threshold,
            cost_overrun_threshold=cost_overrun_threshold,
        )

        for res in all_results:
            if res["project_id"] == project_id:
                return res

        raise ProjectNotFoundError(f"Project '{project_id}' not found in dataset.")

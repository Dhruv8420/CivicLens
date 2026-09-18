"""
Application configuration via pydantic-settings.

Reads from environment variables and .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """CivicLens application settings."""

    APP_NAME: str = "CivicLens"
    APP_VERSION: str = "0.1.0"

    # CORS origins allowed (comma-separated in .env, defaults for local dev)
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
    ]

    # Anomaly detection thresholds (will be used by detectors later)
    PROGRESS_MISMATCH_THRESHOLD: float = 25.0  # percentage points
    COST_OVERRUN_THRESHOLD: float = 20.0  # percentage

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

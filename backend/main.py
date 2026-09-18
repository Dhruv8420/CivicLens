"""
CivicLens Backend — FastAPI Application

Explainable AI-powered risk intelligence system
for public development projects.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Explainable AI-powered risk intelligence system for public "
        "development projects. Identifies anomalies and recommends "
        "human verification."
    ),
    version=settings.APP_VERSION,
)

# CORS — allow frontend dev server during local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["System"])
def health_check():
    """Health check endpoint. Returns system status."""
    return {"status": "ok"}

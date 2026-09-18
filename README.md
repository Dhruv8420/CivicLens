# CivicLens

Explainable AI-powered risk intelligence system for public development projects.

CivicLens analyzes project records and identifies anomalous patterns such as cost anomalies, expenditure vs physical-progress mismatches, project delays, and cost overruns. It recommends human verification — it does **not** claim fraud.

## Status

🚧 Under development — Hackathon MVP (Sep 18–20, 2026)

## Quick Start

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Dataset

- **Location**: `backend/data/sample_projects.csv`
- **Records**: 100 synthetic public-development project records
- **Generator**: `scripts/generate_data.py` (deterministic, seed=42)

> **Disclaimer**: This is **synthetic data** created for hackathon demonstration and testing purposes only. It does NOT represent real government projects, real expenditures, or real departments.

To regenerate:
```bash
python scripts/generate_data.py
```

## Tech Stack

- **Backend**: Python, FastAPI, pandas, numpy
- **Frontend**: React + Vite (coming soon)
- **Deployment**: Docker, AWS EC2 (coming soon)

## Team

- **Developer 1**: Python / AI / Backend
- **Developer 2**: AWS / Cloud / Deployment

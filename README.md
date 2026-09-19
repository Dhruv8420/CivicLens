# CivicLens

CivicLens identifies unusual patterns in public development project data and produces explainable risk indicators for human verification.

> [!IMPORTANT]
> **Ethical Disclaimer & Prototype Notice**:
> - CivicLens does **NOT** prove fraud, corruption, or wrongdoing.
> - CivicLens does **NOT** accuse individuals, contractors, or organizations.
> - It identifies statistical outliers and pattern mismatches to prioritize projects for objective human review.
> - All risk scores (0–100) and risk bands are prototype review heuristics, **not** official government thresholds.

---

## Architecture

```
React + Vite (Frontend)
       ↓
FastAPI (Backend API)
       ↓
Analysis Service (Orchestration & Validation)
       ↓
Detector Engine (Cost Anomaly, Overrun, Progress Mismatch, Delay)
       ↓
Explainable Risk Engine (Scoring & Evidence Aggregation)
       ↓
Explainable Results & API Response
```

---

## Anomaly Detectors

1. **Cost Anomaly (IQR Method)**: Statistical outlier detection for `original_cost_lakhs` relative to peer group projects in the SAME sector.
2. **Progress Mismatch**: Identifies severe gaps between financial expenditure percentage (`expenditure / revised_cost`) and reported physical progress percentage.
3. **Delay Detector**: Identifies projects past their `revised_completion_date` that remain incomplete (`In Progress` or `Stalled`).
4. **Cost Overrun**: Evaluates percentage cost escalation between `original_cost_lakhs` and `revised_cost_lakhs`.

---

## Datasets & Real-Data Support

### 1. Synthetic Benchmark Dataset
- **Location**: `backend/data/sample_projects.csv` (100 project records, seed=42)
- **Purpose**: Testing and baseline demonstration. Synthetic data must **NOT** be interpreted as real government project findings.

### 2. MoSPI PAIMANA Real Government Dataset
- **Source**: Ministry of Statistics and Programme Implementation (MoSPI) Infrastructure & Project Monitoring Division (IPMD) PAIMANA / OCMS portal.
- **Location**: `scratch/real_data/mospi_paimana/paimana_projects_full.csv` (2,201 raw records, 1,987 unique projects).
- **Capability**: Supports **Cost Anomaly** and **Cost Overrun** detectors. Physical progress and completion target dates are omitted in the MoSPI REST feed; CivicLens transparently marks **Progress Mismatch** and **Delay** as unavailable without fabricating missing data.

---

## Quick Start & Setup

### Backend (FastAPI)
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows (or source venv/bin/activate on Linux/macOS)
pip install -r requirements.txt
python -m uvicorn main:app --port 8000 --reload
```
- **Frontend Dashboard**: `http://localhost:5173`
- **Interactive API Documentation**: `http://127.0.0.1:8000/docs`

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

---

## API Endpoints

- `GET /api/health` — System health check (`{"status": "ok"}`).
- `GET /api/projects` — Evaluates default project dataset and returns project-level risk analysis.
- `GET /api/projects/{project_id}` — Returns detailed risk explanation for a specific project.
- `POST /api/analyze/upload` — Ingests custom CSV uploads, auto-maps canonical columns, evaluates detector availability, and returns explainable risk analysis.

---

## Testing & Verification

```bash
# Run backend test suite (127+ tests)
python -m pytest backend/tests -q

# Run frontend build verification
cd frontend
npm run build
```

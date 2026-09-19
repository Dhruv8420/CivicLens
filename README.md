# CivicLens

**AI-Powered Risk Intelligence for Public Development Projects**

CivicLens identifies unusual patterns in public development project data and produces explainable risk indicators for human verification. Upload any government project CSV — the system auto-maps columns, evaluates detector availability, scores risk, and surfaces transparent evidence.

> [!IMPORTANT]
> **Ethical Disclaimer & Prototype Notice**:
> - CivicLens does **NOT** prove fraud, corruption, or wrongdoing.
> - CivicLens does **NOT** accuse individuals, contractors, or organizations.
> - It identifies statistical outliers and pattern mismatches to prioritize projects for objective human review.
> - All risk scores (0–100) and risk bands are prototype review heuristics, **not** official government thresholds.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  React 19 + Vite 8 (Dark-mode Dashboard)                    │
│  Components: Navbar, UploadSection, SummaryCards,            │
│              ProjectTable, ProjectDetailDrawer,              │
│              DetectorAvailabilityBanner, RiskBadge           │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP (JSON)
┌────────────────────────▼────────────────────────────────────┐
│  FastAPI Backend (Python 3.x)                                │
│  Routes: /api/health, /api/projects, /api/projects/{id},     │
│          /api/analyze/upload                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Dataset Adapter (Alias Resolution & Validation)             │
│  - Flexible canonical alias mapping (20+ synonyms/field)     │
│  - Auto-detects detector availability per upload             │
│  - Type sanitization & missing-data transparency             │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Anomaly Detection Engine                                    │
│  ├── Cost Anomaly (IQR per sector)                           │
│  ├── Cost Overrun (revised vs original cost)                 │
│  ├── Progress Mismatch (expenditure % vs physical %)         │
│  └── Delay (past deadline + incomplete status)               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Explainable Risk Engine                                     │
│  - Composite weighted score (0–100)                          │
│  - Risk bands: Low, Medium, High, Critical                   │
│  - Per-project evidence with detector contributions          │
└─────────────────────────────────────────────────────────────┘
```

---

## Anomaly Detectors

| Detector              | Method                                  | Key Fields                                      |
|-----------------------|-----------------------------------------|-------------------------------------------------|
| **Cost Anomaly**      | IQR-based outlier detection per sector  | `original_cost_lakhs`, `sector`                 |
| **Cost Overrun**      | % escalation between cost estimates     | `original_cost_lakhs`, `revised_cost_lakhs`     |
| **Progress Mismatch** | Financial expenditure % vs physical %   | `expenditure_lakhs`, `revised_cost_lakhs`, `physical_progress_pct` |
| **Delay**             | Past deadline with incomplete status    | `revised_completion_date`, `status`             |

Each detector is **independently availability-checked** against the uploaded dataset — unavailable detectors are transparently skipped without fabricating data.

---

## Dataset Support

### Synthetic Benchmark
- **Location**: `backend/data/sample_projects.csv` (100 records, seed=42)
- **Purpose**: Testing and baseline demonstration only.

### MoSPI PAIMANA (Real Government Data)
- **Source**: Ministry of Statistics & Programme Implementation (MoSPI) IPMD PAIMANA / OCMS portal.
- **Columns**: Supports `Original End Date`, `Revised Date`, `Project Cost`, `Anticipated Cost`, `Sector`, `Status`, and more.
- **Capability**: All 4 detectors are available when date and progress columns are present.

### Custom CSV Upload
Upload any CSV through the dashboard or `POST /api/analyze/upload`. The Dataset Adapter auto-maps headers using canonical alias rules (e.g., `Original End Date` → `target_completion_date`, `Revised Date` → `revised_completion_date`).

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### Backend (FastAPI)
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows (or source venv/bin/activate on Linux/macOS)
pip install -r requirements.txt
python -m uvicorn main:app --port 8000 --reload
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

- **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
- **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## API Endpoints

| Method | Endpoint                  | Description                                                      |
|--------|---------------------------|------------------------------------------------------------------|
| `GET`  | `/api/health`             | System health check (`{"status": "ok"}`)                         |
| `GET`  | `/api/projects`           | Evaluate default dataset and return project-level risk analysis  |
| `GET`  | `/api/projects/{id}`      | Detailed risk explanation for a specific project                 |
| `POST` | `/api/analyze/upload`     | Ingest custom CSV, auto-map columns, and return risk analysis    |

---

## Project Structure

```
CivicLens/
├── backend/
│   ├── main.py                          # FastAPI entry point
│   ├── app/
│   │   ├── api/routes/                  # API route handlers
│   │   ├── engine/
│   │   │   ├── risk_engine.py           # Composite risk scoring
│   │   │   └── detectors/              # Cost anomaly, overrun, delay, progress mismatch
│   │   ├── services/
│   │   │   ├── analysis_service.py      # Orchestration & validation
│   │   │   └── dataset_adapter.py       # Alias mapping & ingestion
│   │   └── data/                        # Sample datasets
│   ├── tests/                           # 128 tests (pytest)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/                  # Navbar, ProjectTable, UploadSection, etc.
│   │   ├── pages/DashboardPage.tsx      # Main dashboard
│   │   ├── services/                    # API client
│   │   ├── types/                       # TypeScript interfaces
│   │   └── index.css                    # Dark-mode design system
│   └── package.json
├── scripts/                             # Utility scripts
├── README.md
└── PROJECT.md
```

---

## Testing & Verification

```bash
# Run full backend test suite (128 tests)
cd backend
python -m pytest tests -q

# Frontend build verification
cd frontend
npm run build
```

All detectors, the dataset adapter, the risk engine, the API layer, and MoSPI-format ingestion are covered by automated tests.

---

## License

This project is a research prototype. All data analysis is for educational and transparency purposes only.

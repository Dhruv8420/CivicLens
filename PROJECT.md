# CivicLens — Project Document

## Vision

CivicLens is an explainable AI-powered risk intelligence system for public development projects. It ingests real government project data (CSV uploads from portals like MoSPI PAIMANA), auto-maps columns using flexible alias rules, detects anomalies across four independent detectors, and produces transparent, evidence-backed risk scores — all without fabricating missing data or accusing any individual or organization.

---

## Anomaly Detection Scope

| #  | Detector                 | Method                                      | Status       |
|----|--------------------------|---------------------------------------------|--------------|
| 1  | **Cost Anomaly**         | IQR-based outlier detection per sector      | ✅ Deployed   |
| 2  | **Cost Overrun**         | Revised cost vs. original cost escalation   | ✅ Deployed   |
| 3  | **Progress Mismatch**    | Financial expenditure % vs. physical % gap  | ✅ Deployed   |
| 4  | **Delay Detection**      | Past deadline with incomplete status        | ✅ Deployed   |
| 5  | *Duplicate Descriptions* | TF-IDF + cosine similarity *(stretch goal)* | ⏳ Planned    |

---

## Risk Scoring

- **Composite weighted score**: 0–100
- **Risk bands**: Low (0–25) · Medium (26–50) · High (51–75) · Critical (76–100)
- **Explainability**: Each project score includes per-detector contributions, evidence text, and flags

> [!IMPORTANT]
> The system identifies anomalies — it does **NOT** accuse projects of fraud.

---

## Architecture

```
CSV Upload → Dataset Adapter (Alias Resolution & Validation)
                ↓
          Anomaly Detection Engine (4 Independent Detectors)
                ↓
          Explainable Risk Engine (Weighted Scoring & Evidence)
                ↓
          FastAPI REST API (JSON Responses)
                ↓
          React 19 + Vite 8 Dark-Mode Dashboard
```

---

## Tech Stack

| Layer      | Technology                                                  |
|------------|-------------------------------------------------------------|
| Frontend   | React 19, TypeScript 6, Vite 8, dark-mode CSS design       |
| Backend    | Python 3.10+, FastAPI, Pandas, Uvicorn                      |
| Testing    | pytest (128 tests), Vite build verification                 |
| Data       | CSV ingestion with flexible canonical alias mapping         |

---

## Key Features

- **Flexible CSV Ingestion**: Auto-maps 20+ column name synonyms per canonical field — works with MoSPI, OCMS, and custom CSV formats out of the box
- **Detector Availability Transparency**: Each detector is independently checked against the uploaded data; unavailable detectors are clearly marked (never fabricated)
- **Dark-Mode Professional Dashboard**: Enterprise-grade UI with smooth animations, glassmorphism cards, interactive data table with sorting/filtering, and per-project detail drawers
- **Full Test Coverage**: 128 automated tests covering all detectors, the dataset adapter, risk engine, API layer, and MoSPI-format ingestion

---

## Timeline

| Day              | Milestone                                                                          |
|------------------|-------------------------------------------------------------------------------------|
| Day 1 (Sep 18)   | Data pipeline + detection engine scaffold                                          |
| Day 2 (Sep 19)   | All 4 detectors + API + frontend + dark-mode UI + dataset adapter + 128 tests      |
| Day 3 (Sep 20)   | Polish, deploy, demo                                                               |

---

## Current Status

✅ All 4 anomaly detectors implemented and tested  
✅ Dataset adapter with flexible canonical alias mapping  
✅ FastAPI backend with upload, analysis, and project detail endpoints  
✅ Dark-mode React dashboard with enterprise-grade UI  
✅ 128 automated tests passing  
✅ MoSPI PAIMANA real-data ingestion verified  

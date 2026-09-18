# CivicLens — Project Document

## Vision

CivicLens is an explainable AI-powered risk intelligence system for public development projects. It identifies anomalous patterns and recommends human verification.

## Anomaly Detection Scope

1. **Cost Anomaly** — IQR-based outlier detection per sector
2. **Expenditure vs Progress Mismatch** — Financial % vs Physical % gap
3. **Delay Detection** — Projects past deadline with incomplete status
4. **Cost Overrun** — Revised cost significantly exceeds original estimate
5. *(Stretch)* **Duplicate Descriptions** — TF-IDF + cosine similarity

## Risk Scoring

Composite weighted score (0–100) with four tiers: Low, Medium, High, Critical.

> **Important**: The system identifies anomalies — it does NOT accuse projects of fraud.

## Architecture

```
CSV Upload → Validation → Anomaly Detection → Risk Score → Explanation → Dashboard
```

## Timeline

- **Day 1 (Sep 18)**: Data + detection engine scaffold
- **Day 2 (Sep 19)**: Detectors + API + frontend shell
- **Day 3 (Sep 20)**: Polish + deploy + demo

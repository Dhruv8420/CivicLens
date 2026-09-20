☁️ CivicLens — AI-Powered Risk Intelligence for Public Projects

A production-style, explainability-first risk analysis platform for public development project data, demonstrating real-world CSV ingestion, anomaly detection, an explainable scoring engine, and cloud deployment on AWS.

![AWS](https://img.shields.io/badge/AWS-Cloud-FF9900?logo=amazon-aws&logoColor=white)
![Status](https://img.shields.io/badge/status-prototype-orange)
![IaC](https://img.shields.io/badge/IaC-CloudFormation-8A63D2)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Frontend](https://img.shields.io/badge/frontend-React%2019-149ECA?logo=react&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-2E9CF0)

---

## 📖 Table of Contents

- [🎯 Objective](#-objective)
- [💡 Problem Statement](#-problem-statement)
- [📌 System Architecture](#-system-architecture)
- [🔄 Application Workflow](#-application-workflow)
- [🕵️ Anomaly Detectors](#️-anomaly-detectors)
- [🔒 Security Features](#-security-features)
- [⚡ Scalability](#-scalability)
- [📊 AWS Services Explained](#-aws-services-explained)
- [🧩 Challenges Faced](#-challenges-faced)
- [📚 Key Learnings](#-key-learnings)
- [🎓 Suitable For](#-suitable-for)
- [🚀 Future Roadmap](#-future-roadmap)
- [👨‍💻 Author](#-author)

---

## 🎯 Objective

CivicLens identifies unusual patterns in public development project data and produces **explainable risk indicators for human verification**. Upload any government project CSV and the system auto-maps columns, evaluates which detectors the data can support, scores each project for review priority, and shows the evidence behind every score.

> [!IMPORTANT]
> **Ethical disclaimer & prototype notice**
> - CivicLens does **not** prove fraud, corruption, or wrongdoing.
> - CivicLens does **not** accuse individuals, contractors, or organizations.
> - It surfaces statistical outliers and pattern mismatches to prioritize projects for objective human review.
> - Risk scores (0–100) and risk bands are prototype review heuristics, **not** official government thresholds.

---

## 💡 Problem Statement

Public development project data — cost estimates, revised budgets, physical progress, deadlines — is published across many government portals in inconsistent formats, with no consistent way to flag projects that deserve a closer look. Reviewers are left to manually skim spreadsheets for cost blowouts, stalled progress, or missed deadlines, which doesn't scale across thousands of projects.

CivicLens addresses this by turning any project CSV — regardless of its exact column names — into a consistent, scored, evidence-backed shortlist for human reviewers, without ever making an accusation on its own.

---

## 📌 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  React 19 + Vite 8 (Dark-mode Dashboard)                    │
│  Navbar · UploadSection · SummaryCards · ProjectTable         │
│  ProjectDetailDrawer · DetectorAvailabilityBanner · RiskBadge │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP (JSON)
┌────────────────────────▼────────────────────────────────────┐
│  FastAPI Backend (Python 3.x)                                │
│  /api/health · /api/projects · /api/projects/{id}            │
│  /api/analyze/upload                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Dataset Adapter (Alias Resolution & Validation)             │
│  20+ synonym mappings per field · detector availability check │
│  type sanitization · missing-data transparency                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Anomaly Detection Engine                                    │
│  Cost Anomaly · Cost Overrun · Progress Mismatch · Delay      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  Explainable Risk Engine                                     │
│  Composite weighted score (0–100) · Low/Medium/High/Critical  │
│  Per-project evidence with detector contributions              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Application Workflow

1. **Upload** — a user drops a government project CSV into the dashboard, or calls `POST /api/analyze/upload` directly.
2. **Adapt** — the Dataset Adapter resolves header synonyms to a canonical schema and reports which fields are missing, without fabricating data.
3. **Detect** — each of the four anomaly detectors runs independently, only if the fields it needs are present.
4. **Score** — the Risk Engine combines detector outputs into a single composite score (0–100) and a Low → Critical band.
5. **Review** — the dashboard surfaces the score, band, and the specific evidence behind it, so a human makes the final call.

---

## 🕵️ Anomaly Detectors

| Detector | Method | Key Fields |
|---|---|---|
| **Cost Anomaly** | IQR-based outlier detection per sector | `original_cost_lakhs`, `sector` |
| **Cost Overrun** | % escalation between cost estimates | `original_cost_lakhs`, `revised_cost_lakhs` |
| **Progress Mismatch** | Financial expenditure % vs physical progress % | `expenditure_lakhs`, `revised_cost_lakhs`, `physical_progress_pct` |
| **Delay** | Past deadline with incomplete status | `revised_completion_date`, `status` |

Each detector is checked independently against the uploaded dataset — unavailable detectors are transparently skipped rather than faked.

---

## 🔒 Security Features

- No inbound SSH — administrative access to the EC2 host goes through **AWS Systems Manager Session Manager** only.
- IAM instance profile scoped to `AmazonSSMManagedInstanceCore`.
- EC2 security group exposes only **HTTP/80** and **HTTPS/443** publicly; everything else stays closed.
- The CloudFormation template (`civiclens-ec2-existing-vpc.yaml`) deliberately contains **no** AWS access keys, GitHub tokens, or private keys.
- Nothing committed to the repo: `.env` files with secrets, AWS access keys, GitHub personal access tokens, EC2 `.pem` private keys, passwords, or API keys. Secrets are handled through environment variables or AWS-managed identity instead.

---

## ⚡ Scalability

- Detectors are independent and availability-checked per upload, so adding a new detector doesn't require every dataset to support it.
- The Dataset Adapter's alias-mapping layer means new government data sources can be onboarded by extending the alias table, not by rewriting ingestion logic.
- The backend and frontend are decoupled over a JSON API, so the FastAPI service can be scaled or moved behind a load balancer independently of the static frontend build.
- Nginx serves the built frontend directly and only proxies `/api/` calls to FastAPI, keeping static asset delivery cheap at higher traffic.

---

## 📊 AWS Services Explained

| Service | Role in CivicLens |
|---|---|
| **Amazon EC2** (Amazon Linux 2023) | Hosts the built React frontend and the FastAPI backend on a single instance. |
| **Nginx** | Serves `frontend/dist` and reverse-proxies `/api/` to FastAPI on `127.0.0.1:8000`. |
| **AWS Systems Manager (Session Manager)** | Administrative access to the instance without an open inbound SSH port. |
| **IAM Instance Profile** | Grants the instance `AmazonSSMManagedInstanceCore` so Session Manager can connect. |
| **EC2 Security Group** | Publicly exposes only HTTP/80 and HTTPS/443. |
| **AWS CloudFormation** | `civiclens-ec2-existing-vpc.yaml` provisions the EC2 instance, security group, IAM role, and instance profile inside an existing VPC and public subnet. |

**Server layout**

| Path | Purpose |
|---|---|
| `/opt/CivicLens` | Application root |
| `/opt/CivicLens/backend` | FastAPI backend |
| `/opt/CivicLens/.venv` | Python virtual environment |
| `/opt/CivicLens/frontend/dist` | Frontend build |

```bash
# Install Nginx — Amazon Linux 2023
sudo dnf install -y nginx
sudo cp deployment/nginx/civiclens.conf /etc/nginx/conf.d/civiclens.conf
sudo nginx -t
sudo systemctl enable --now nginx
```

```bash
# Install the FastAPI service
sudo cp deployment/systemd/civiclens.service /etc/systemd/system/civiclens.service
sudo systemctl daemon-reload
sudo systemctl enable --now civiclens
sudo systemctl status civiclens
```

---

## 🧩 Challenges Faced

- **Inconsistent source data** — government CSVs name the same field a dozen different ways (`Original End Date` vs `target_completion_date`, for example), which is what pushed the Dataset Adapter toward a 20+ synonym alias-mapping system instead of a fixed schema.
- **Avoiding false confidence** — early detector logic risked implying certainty about wrongdoing. The response was to make every detector independently availability-checked and to always surface the underlying evidence rather than a bare score.
- **Partial datasets** — real government exports rarely have every field populated. The adapter had to fail gracefully per-detector instead of per-upload, so a dataset missing progress data can still be scored for cost anomalies.
- **Zero-trust deployment on a small footprint** — getting administrative access working through Session Manager only, with no inbound SSH, took care in the IAM instance profile and security group configuration.

---

## 📚 Key Learnings

- Designing for **explainability first** changes the shape of the whole pipeline — every detector has to carry its evidence forward, not just its verdict.
- Alias-based schema mapping is far more resilient to real-world government data than requiring an exact column format.
- Keeping infrastructure secrets out of source control (via CloudFormation params, environment variables, and IAM roles) is easiest when it's designed in from the CloudFormation template up, not retrofitted later.
- A single EC2 instance with Nginx as a reverse proxy is a simple, auditable way to run a small full-stack app in a VPC you don't fully control.

---

## 🎓 Suitable For

- Civic-tech and open-government developers exploring anomaly detection on public spending data.
- Students and researchers studying explainable ML/statistics applied to procurement or infrastructure data.
- Cloud/DevOps learners looking at a minimal, session-manager-only AWS deployment pattern.
- Government transparency and audit teams evaluating tools to prioritize manual review, not replace it.

---

## 🚀 Future Roadmap

- [ ] Expand detector library (e.g., vendor concentration, geographic clustering of risk).
- [ ] Support additional government data portals beyond MoSPI PAIMANA.
- [ ] Add authentication and role-based access for review teams.
- [ ] HTTPS termination and a custom domain in the CloudFormation template.
- [ ] Exportable review reports (PDF/CSV) per project.

---

## 👨‍💻 Authors

| | |
|---|---|
| **Arghya Roy** | **Dhruba Bauri** |
| 🎓 B.Tech, Information Technology | 🎓 B.Tech, CSE — AI/ML |
| ☁️ Cloud & DevOps Enthusiast | 🧠 MLOps Enthusiast |
| [![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white)](#) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/arghyaroy1/) | [![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white)](#) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/dhrubabaur) |

⭐ **If you found this project useful, consider giving it a star — it genuinely helps!**

---

## License

This project is a research prototype. All data analysis is for educational and transparency purposes only.

Licensed under the [MIT License](./LICENSE) — Copyright © 2026 CivicLens.

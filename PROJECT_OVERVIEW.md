# PlaneSense Demo Project — Overview

Three workstreams built for BD research and AI demo assets targeting PlaneSense (potential Calfus client).

---

## 1. Predictive Maintenance

**Purpose:** Demonstrate AI-driven aircraft component failure prediction for PlaneSense's fleet (46 PC-12 NGX + 16 PC-24 = 62 aircraft).

**Scripts:**
- `generate_synthetic_data.py` — generates 9 CSVs of synthetic fleet data
- `train_predictive_maintenance.py` — trains XGBoost classifiers + RUL regressor

**Data (`output/predictive_maintenance/data/`):**

| File | Rows | Description |
|---|---|---|
| aircraft_registry.csv | 62 | Tail numbers, bases, delivery dates, total hours |
| components_master.csv | 17 | Component types across 6 categories with life limits |
| component_installations.csv | 792 | One row per component per aircraft with wear % and status |
| flight_logs.csv | ~81,695 | 2-year simulation (2024-2025) with weather and route data |
| sensor_readings.csv | ~81,695 | Per-flight EGT, oil, vibration, fuel flow, anomaly scores |
| maintenance_records.csv | ~11,258 | Scheduled inspections + unscheduled events |
| failure_events.csv | ~17 | AOG/MAJOR events with cost and detection method |
| parts_inventory.csv | 28 | SKUs, suppliers, lead times, supply chain risk flags |
| ml_features.csv | 792 | Aggregated feature matrix for model training |

**Models (`output/predictive_maintenance/model/`):**
- `failure_50h_model.json` — CRITICAL alert classifier
- `failure_100h_model.json` — AT-RISK alert classifier
- `rul_model.json` — Remaining Useful Life regressor
- 6 plots (ROC, PR, feature importance, SHAP, confusion matrix, RUL scatter)
- `demo_predictions.csv` — alert levels: HEALTHY / WATCH / WARNING / CRITICAL

**Key Results:**

| Model | ROC-AUC | PR-AUC | CV-AUC |
|---|---|---|---|
| fail_50h (CRITICAL) | 0.993 | 0.939 | 0.989 ± 0.007 |
| fail_100h (AT-RISK) | 0.992 | 0.970 | 0.987 ± 0.004 |
| RUL regressor | R²=0.791 | MAE=483h | RMSE=913h |

**Top predictors:** wear_pct_max, unscheduled_events_12m, max_anomaly_score_30d, min_oil_pressure_30d, max_vibration_30d

---

## 2. Customer Churn

**Purpose:** Predict fractional-owner churn and identify upsell opportunities across PlaneSense's owner base.

**Scripts:**
- `generate_churn_data.py` — generates 5 CSVs for 350 synthetic fractional owners
- `train_churn_model.py` — trains XGBoost churn + upsell classifiers

**Data (`output/churn/data/`):**

| File | Rows | Description |
|---|---|---|
| owners.csv | 350 | Share types, aircraft pref, region, contract dates, AM |
| flight_activity.csv | ~26,919 | 2023-2024 flight history per owner |
| service_interactions.csv | ~3,313 | Phone/email/portal/in-person interactions |
| owner_engagement.csv | ~6,044 | Monthly app sessions, portal logins, email opens |
| churn_ml_features.csv | 350 | 32 features across 5 groups for model training |

**Models (`output/churn/model/`):**
- `churn_model.json` — churned_within_12m classifier
- `upsell_model.json` — upsell_ready classifier
- 7 plots (ROC/PR for both models, feature importance, SHAP, confusion matrices, risk segments)
- `demo_at_risk.csv` — all owners ranked by churn probability
- `demo_upsell_pipeline.csv` — upsell targets ranked by probability

**Key Results:**

| Model | ROC-AUC | PR-AUC | CV-AUC |
|---|---|---|---|
| Churn (churned_within_12m) | 0.953 | 0.667 | 0.969 ± 0.019 |
| Upsell (upsell_ready) | 0.978 | 0.948 | 0.979 ± 0.015 |

**Dataset:** 350 owners, 9.1% churn rate, 13.7% upsell rate. Upsell types: SHARE_UPGRADE, AIRCRAFT_UPGRADE_PC24, COBALTPASS_TO_FRACTIONAL, JETFLY_INTRO.

---

## 3. Research (Scraping + Reports)

**Purpose:** Scrape planesense.com comprehensively and produce BD intelligence for the CXO meeting with Mandar Pendse (CIO).

**Scripts:**
- `scraper.py` — full-site scraper (532 pages, 229 images, 0 errors)
- `split_data.py` — partitions into content (403), fleet (110), company overview (19)
- `split_fleet.py` — splits fleet into PC-24 (35), PC-12 (13), general (3)
- `split_content.py` — splits content into 7 thematic buckets (fractional ownership, comparisons/cost, aircraft, news, people/guides, destinations, general)

**Data (`output/research/`):**

| Directory | Contents |
|---|---|
| `company/` | company_overview.json — 19 pages (homepage, Why PlaneSense, programs) |
| `fleet/` | 3 JSONs — PC-24 (35 pages), PC-12 (13 pages), general (3 pages) |
| `content/` | 7 JSONs — fractional ownership (29), comparisons (13), aircraft (8), news (22), people (21), destinations (19), general (31) |

**Reports (`output/research/reports/`):**
- `EXECUTIVE_SUMMARY.md` — primary BD brief: who they are, 2025 changes, tech gap, top 3 opportunities
- `DECK_SLIDES.md` — 12-slide presentation script with speaker notes
- `DECK_VISUAL_PROMPTS.md` — AI image generation prompts per slide
- 5 research JSONs: company intelligence, pain points, opportunity matrix, hidden opportunities, conversation playbook

**Key Findings:**
- PlaneSense launched 4+ major programs in 2025 (Jetfly EU, CobaltPass jet card, Sourcing Solution, CaptainJet) with **no ERP or AI layer**
- Confirmed absent: Oracle/SAP/Workday, AI/automation, BI platform
- Top 3 opportunities: (1) IOC AI dispatch agents, (2) Oracle Cloud ERP for multi-entity financials, (3) Predictive maintenance at Atlas Aircraft Center
- Hidden opportunity: world-first PC-12 NGX Level D simulator — only used internally, every PC-12 operator globally needs access

---

## Also Built (not covered above)

**IOC Dispatch Agent** — Claude Sonnet tool-use agent simulating flight dispatch with 9 tools. Scripts: `generate_ioc_data.py`, `ioc_dispatch_agent.py`. Data: `output/ioc/`. Demo: 5 dispatched, 5 escalated from 10 requests.

See `DEMO_IDEAS.md` for full 5-idea reference with specs and build status.

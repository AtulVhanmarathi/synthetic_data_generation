# PlaneSense Pre-Sales — Output Register

**Client:** PlaneSense Inc. | **Project owner:** Calfus BD
**Last updated:** 2026-03-16
**Primary contact at client:** Mandar Pendse (CIO)

---

## Status Legend
| Symbol | Meaning |
|---|---|
| ✅ | Complete |
| 🔄 | In progress |
| 📋 | Spec complete, not yet built |
| ❌ | Not started |

---

## 1. Research & BD Intelligence

| Output | Location | Status | Notes |
|---|---|---|---|
| Full site scrape (532 pages, 229 images) | `output/research/company/`, `fleet/`, `content/` | ✅ | 7 thematic buckets + fleet + company overview |
| Company Intelligence JSON | `output/research/reports/01_company_intelligence.json` | ✅ | Structure, financials signals, tech maturity |
| Pain Points & Opportunities JSON | `output/research/reports/02_pain_points_opportunities.json` | ✅ | Operational friction, documented challenges |
| Opportunity Matrix JSON | `output/research/reports/03_opportunity_matrix.json` | ✅ | 3×3 strategic opportunity map |
| Hidden Opportunities JSON | `output/research/reports/04_hidden_opportunities.json` | ✅ | Non-obvious revenue/cost plays |
| Conversation Playbook JSON | `output/research/reports/05_conversation_playbook.json` | ✅ | Discovery questions, objection handling |
| Executive Summary (CXO brief) | `output/research/reports/EXECUTIVE_SUMMARY.md` | ✅ | Primary doc for first meeting with Mandar Pendse |
| 12-Slide Deck Script | `output/research/reports/DECK_SLIDES.md` | ✅ | Full speaker notes per slide |
| Deck Visual Prompts | `output/research/reports/DECK_VISUAL_PROMPTS.md` | ✅ | AI image prompts per slide |
| Demo Strategy Document | `output/research/PlaneSense_Demo_Strategy_Document.md` | ✅ | Deep problem statement + dataset audit |
| Client Research & Collaboration Strategy | `output/research/Client Research & Collaboration Strategy.pdf` | ✅ | PDF deliverable |

**Key findings from research:**
- PlaneSense launched 4 major programs in 2025 (Jetfly EU, CobaltPass, Sourcing Solution, CaptainJet) with **no ERP or AI layer**
- Confirmed absent: Oracle/SAP/Workday, BI platform, AI/automation of any kind
- Top 3 Calfus opportunities: **(1)** IOC AI dispatch agents, **(2)** Oracle Cloud ERP multi-entity financials, **(3)** Predictive maintenance at Atlas Aircraft Center
- Hidden opportunity: world-first PC-12 NGX Level D simulator — currently internal only, every PC-12 operator globally is a potential paying customer

---

## 2. Synthetic Analytics Dataset (Star Schema)

> Built to demonstrate what PlaneSense's data *could* look like under a modern BI platform. Calibrated against FAA GA Survey 2020–2024 and FAA SDRS data.

**Generator:** `generate_analytics_data_v2.py` (V2 — single-pass, all fixes baked in)
**Output location:** `output/analytics/data/`

### Dimension Tables

| File | Rows | Description |
|---|---|---|
| `dim_aircraft.csv` | 62 | Tail numbers, bases, types (46 PC-12 NGX + 16 PC-24) |
| `dim_owner.csv` | 350 | Share types, regions, contract dates, account manager |
| `dim_airport.csv` | 34 | Airports with lat/lon; KPSM (Portsmouth) as dominant hub |
| `dim_crew.csv` | — | Pilot roster |
| `dim_date.csv` | 2023–2025 | Calendar dimension with season, day_of_week |
| `dim_facility.csv` | 2 | Portsmouth NH, Boulder City NV maintenance facilities |
| `dim_component.csv` | — | 17 component types across 6 categories with life limits |

### Fact Tables

| File | Rows | Description |
|---|---|---|
| `fact_flight.csv` | ~142,841 | 3 years of flights; ~47,614/yr (target: 47,800 ✅) |
| `fact_booking.csv` | — | Multi-leg owner journey bookings |
| `fact_aircraft_daily_status.csv` | 63,080 | FLYING / AVAILABLE / IN_MAINTENANCE / AOG per aircraft per day |
| `fact_maintenance_job.csv` | 2,589 | Scheduled + unscheduled maintenance jobs |
| `fact_maintenance_detail.csv` | 6,893 | Line-item costs (parts + labor) per job |

### Data Quality Benchmarks (V2)

| Metric | Achieved | Benchmark | Pass |
|---|---|---|---|
| Annual flights | ~47,680 | ~47,800 (PlaneSense reported) | ✅ |
| PC-12 utilization | ~1,150 hrs/yr | FAA GA Survey | ✅ |
| PC-24 utilization | ~1,350 hrs/yr | FAA GA Survey | ✅ |
| FLYING % overall | 74.7% | 72–78% FAA fractional ops | ✅ |
| AVAILABLE % overall | 16.0% | 14–20% industry benchmark | ✅ |
| Holiday spike (Dec 20–Jan 5) | 82% FLYING | 82% target | ✅ |
| AOG months | Mar / May / Oct only | Inspection-cycle aligned | ✅ |
| Deadhead ratio | 14.8% | 15% industry norm | ✅ |
| Maint cost / flight-hr | ~$46 | ~$39 target | ⚠️ Slightly above (acceptable) |

---

## 3. ML Models

### 3a. Predictive Maintenance

**Scripts:** `generate_synthetic_data.py`, `train_predictive_maintenance.py`
**Output:** `output/predictive_maintenance/`

| Asset | Location | Description |
|---|---|---|
| Aircraft registry | `data/aircraft_registry.csv` | 62 aircraft, 46 PC-12 + 16 PC-24 |
| Component master | `data/components_master.csv` | 17 component types with life limits |
| Component installations | `data/component_installations.csv` | 792 rows (components per aircraft) |
| Flight logs | `data/flight_logs.csv` | ~81,695 rows, 2-year simulation |
| Sensor readings | `data/sensor_readings.csv` | Per-flight EGT, oil, vibration, fuel flow |
| Maintenance records | `data/maintenance_records.csv` | ~11,258 rows |
| Failure events | `data/failure_events.csv` | ~17 AOG/MAJOR events |
| Parts inventory | `data/parts_inventory.csv` | 28 SKUs with supply chain risk flags |
| ML feature matrix | `data/ml_features.csv` | 792 rows × engineered features |
| CRITICAL alert model | `model/failure_50h_model.json` | Failure within 50h classifier |
| AT-RISK alert model | `model/failure_100h_model.json` | Failure within 100h classifier |
| RUL regressor | `model/rul_model.json` | Remaining Useful Life |
| Demo predictions | `model/demo_predictions.csv` | HEALTHY / WATCH / WARNING / CRITICAL alerts |
| Model plots (6) | `model/plots/` | ROC, PR, SHAP, confusion matrix, RUL scatter |

**Model performance:**

| Model | ROC-AUC | PR-AUC | CV-AUC |
|---|---|---|---|
| fail_50h (CRITICAL alert) | **0.993** | 0.939 | 0.989 ± 0.007 |
| fail_100h (AT-RISK alert) | **0.992** | 0.970 | 0.987 ± 0.004 |
| RUL regressor | R²=**0.791** | MAE=483h | RMSE=913h |

**Top predictors:** `wear_pct_max`, `unscheduled_events_12m`, `max_anomaly_score_30d`, `min_oil_pressure_30d`, `max_vibration_30d`

---

### 3b. Customer Churn & Upsell

**Scripts:** `generate_churn_data.py`, `train_churn_model.py`
**Output:** `output/churn/`

| Asset | Location | Description |
|---|---|---|
| Owner profiles | `data/owners.csv` | 350 fractional owners, share types, regions |
| Flight activity | `data/flight_activity.csv` | ~26,919 rows (2023–2024) |
| Service interactions | `data/service_interactions.csv` | ~3,313 rows (phone/email/portal) |
| Owner engagement | `data/owner_engagement.csv` | ~6,044 rows (app sessions, email opens) |
| ML feature matrix | `data/churn_ml_features.csv` | 350 owners × 32 features |
| Churn model | `model/churn_model.json` | churned_within_12m classifier |
| Upsell model | `model/upsell_model.json` | upsell_ready classifier |
| At-risk list | `model/demo_at_risk.csv` | All owners ranked by churn probability |
| Upsell pipeline | `model/demo_upsell_pipeline.csv` | Upsell targets ranked by probability |
| Model plots (7) | `model/plots/` | ROC/PR, SHAP, confusion matrices, risk segments |

**Model performance:**

| Model | ROC-AUC | PR-AUC | CV-AUC |
|---|---|---|---|
| Churn (churned_within_12m) | **0.953** | 0.667 | 0.969 ± 0.019 |
| Upsell (upsell_ready) | **0.978** | 0.948 | 0.979 ± 0.015 |

**Dataset stats:** 350 owners | 9.1% churn rate (mirrors PlaneSense's 91% retention) | 13.7% upsell-ready
**Upsell types modeled:** SHARE_UPGRADE, AIRCRAFT_UPGRADE_PC24, COBALTPASS_TO_FRACTIONAL, JETFLY_INTRO

---

## 4. AI Agent Demo

### IOC Dispatch Agent

**Scripts:** `generate_ioc_data.py`, `ioc_dispatch_agent.py`
**Output:** `output/ioc/`

| Asset | Location | Description |
|---|---|---|
| Crew roster | `data/crew_roster.csv` | Pilot availability data |
| Owner profiles | `data/owner_profiles.csv` | Owner preferences and priorities |
| Flight requests | `data/flight_requests.csv` | Incoming dispatch requests |
| Weather events | `data/weather_events.csv` | SIGMET / IFR weather data |
| Demo dispatch log | `dispatch_log/dispatch_log_2025-12-20.json` | Full agent run output |

**Agent:** Claude Sonnet (claude-sonnet-4-6) with 9 tool-use tools
**Demo scenario:** Dec 20, 2025 (peak holiday demand)
**Result:** 5 dispatched ✅ | 5 escalated ⚠️ | 49 total tool calls

Key scenarios demonstrated:
- IFR weather delay (+90 min reroute)
- SIGMET delay (+2h hold)
- CRITICAL maintenance alert → substitute aircraft substitution
- Jetfly EU coordination (EGLL→LSZH cross-border dispatch)
- Crew shortage → escalation to human dispatcher

---

## 5. Power BI Dashboards

| Dashboard | Spec Doc | Build Status |
|---|---|---|
| Dashboard 1: Fleet Utilization | `DAX_DASHBOARD1_FLEET_UTILIZATION.md` | 🔄 V1 built (screenshot at `output/analytics/Power BI outputs/`), evaluation in `DASHBOARD1_EVALUATION_V1.md` |
| Dashboard 2: Maintenance Intelligence | `DAX_DASHBOARD2_MAINTENANCE.md` | 📋 Spec complete, not yet built |
| Dashboard 3: Route & Airport | `DASHBOARD_VISUALS.md` | 📋 Outlined, not fully specced |
| Dashboard 4: Safety & Reliability | `DASHBOARD_VISUALS.md` | 📋 Outlined, not fully specced |

**Reference data used for calibration** (`output/reference_data/`):
- FAA GA Survey 2020–2024
- FAA AIDS database
- NASR airport reference data
- NTSB accident reports

---

## 6. Supporting Documentation

| Document | Purpose |
|---|---|
| `PROJECT_OVERVIEW.md` | High-level summary of all 3 workstreams |
| `PROJECT_PROGRESSION.md` | Full changelog V1→V2, all data revision decisions |
| `DEMO_IDEAS.md` | 5 demo proposals with build status |
| `DASHBOARD_BRAINSTORM.md` | 4 dashboard concepts, public dataset inventory |
| `DASHBOARD_EVALUATION.md` | Gap analysis of client's Book1.xlsx (scored 4/10 and 5/10) |
| `DASHBOARD_VISUALS.md` | Visual specs and narrative arcs for all dashboards |
| `DATA_REVISION_V2_REASONING.md` | Detailed reasoning for route redesign and all data fixes |
| `output/reference_data/20260302_dashboards_ideas.xlsx` | Dashboard ideas reference spreadsheet |

---

## 7. What's NOT Yet Done

| Item | Priority | Notes |
|---|---|---|
| Dashboard 2 (Maintenance Intelligence) in Power BI | High | Spec in `DAX_DASHBOARD2_MAINTENANCE.md` — ready to build |
| Dashboard 3 (Route & Airport) | Medium | Needs full spec before build |
| Dashboard 4 (Safety & Reliability) | Medium | Needs full spec before build |
| Competitor scraping (NetJets, Flexjet, Wheels Up) | Medium | Would enable positioning matrix for CXO deck |
| Global PC-12/PC-24 operator enumeration | Medium | TAM model for Level D simulator opportunity |
| FAA SDR expansion (PC-12/PC-24 service difficulty records) | Low | Would improve maintenance model calibration |
| Financial ROI model for simulator opportunity | Low | Requires assumptions on training price, utilization |

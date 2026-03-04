# Calfus × PlaneSense — AI/ML Demo Ideas

> **Context:** Proposed before the CXO meeting pitch. Ranked by impact, demo-ability, and fit with PlaneSense's documented pain points. Top 3 were built as working demos. Ideas 4–5 are ready to build.

---

## Status Overview

| # | Demo | Type | Status | Audience |
|---|------|------|--------|----------|
| 1 | Predictive Maintenance Agent | ML + AI Agent | ✅ **BUILT** | CEO + CIO + Atlas leadership |
| 2 | Owner Churn + Upsell Scoring | ML (dual model) | ✅ **BUILT** | CEO + Account Services |
| 3 | IOC Dispatch Scheduling Agent | AI Agent (tool use) | ✅ **BUILT** | CIO + VP Flight Ops |
| 4 | Parts Procurement Intelligence Agent | AI Agent (Atlas-specific) | 🔲 **NOT BUILT** | Atlas Aircraft Center (Todd Smith) |
| 5 | CobaltPass Demand Forecasting | ML (time-series) | 🔲 **NOT BUILT** | CEO + CFO (Jim Citro) |

---

## Demo 1 — Predictive Maintenance Agent ✅

**Pain point addressed:** Atlas Aircraft Center manages 194,000+ parts, two facilities, documented supply chain delays ("parts availability and shipping delays are impacting return-to-service"). One grounded aircraft disrupts owner guarantees = direct churn risk.

**Why build this first:** Most documented pain point, standalone Atlas engagement, directly tied to revenue (91% retention depends on aircraft availability), visual and compelling to a non-technical audience.

### What was built
- **`generate_synthetic_data.py`** — 9 CSVs: aircraft_registry, components_master, component_installations, flight_logs, sensor_readings, maintenance_records, failure_events, parts_inventory, ml_features
- **`train_predictive_maintenance.py`** — 3 XGBoost models + 6 SHAP plots + demo_predictions.csv
- Synthetic fleet: 62 aircraft (46 PC-12 NGX + 16 PC-24), 792 components, 81K flight logs

### ML results
| Model | Metric | Score |
|-------|--------|-------|
| Failure within 50h (CRITICAL) | ROC-AUC | **0.993** |
| Failure within 50h | PR-AUC | 0.939 |
| Failure within 50h | CV-AUC | 0.989 ± 0.007 |
| Failure within 100h (AT-RISK) | ROC-AUC | **0.991** |
| RUL regressor | R² | 0.791 |
| RUL regressor | MAE | 483 hours |

### Key design choices
- **Rank-based target injection** (top 8% by hazard score = CRITICAL) — ensures strong feature correlations without unrealistic distributions
- **Deviation-based anomaly score** — measures deviation from age-expected baseline, not absolute sensor value
- `wear_pct_max` is the strongest predictor (r = 0.52)
- Final class balance: 8.1% CRITICAL, 20.1% AT-RISK

### Demo narrative (CXO moment)
> *"Aircraft N124AF is showing early bearing wear — recommend inspection before the Tampa-Nantucket flight on March 3rd. Here's the maintenance window that minimizes owner disruption."*

### Outputs
```
output/predictive_maintenance/
├── data/   — 9 CSVs (62 aircraft, 792 components, 81K flights)
└── model/  — 3 model .json files, 6 plots, demo_predictions.csv
```

### Agentic layer (spec — not yet wired as standalone agent)
The ML model outputs feed directly into an agent that could:
- Query the model for at-risk components fleet-wide
- Check parts inventory for required replacement components
- Check owner schedule for affected aircraft
- Propose maintenance window with minimum owner disruption
- Draft notification to account services team

---

## Demo 2 — Owner Churn + Upsell Scoring ✅

**Pain point addressed:** 91% retention is PlaneSense's proudest metric and core brand promise. The flip side — identifying the 9% who are at risk *before* they tell you — is a direct revenue protection play. The upsell angle (who's ready for a larger share, who should graduate from CobaltPass to fractional) adds revenue upside.

**Why build this second:** Emotional resonance with a CEO ("what if we could move that 91% to 95%?"), dual revenue angle (retention + growth), and the West Coast expansion + Jetfly partnership are bringing in new owner profiles who need proactive management.

### What was built
- **`generate_churn_data.py`** — 5 CSVs: owners, flight_activity, service_interactions, owner_engagement, churn_ml_features
- **`train_churn_model.py`** — 2 XGBoost classifiers + 7 plots + demo_at_risk.csv + demo_upsell_pipeline.csv
- 350 synthetic owners, PC-12 (75%) / PC-24 (25%), share types 1/32 through 1/4

### ML results
| Model | Metric | Score |
|-------|--------|-------|
| Churn (churned_within_12m) | ROC-AUC | **0.953** |
| Churn | PR-AUC | 0.667 |
| Churn | CV-AUC | 0.969 ± 0.019 |
| Upsell readiness | ROC-AUC | **0.978** |
| Upsell | PR-AUC | 0.948 |
| Upsell | CV-AUC | 0.979 ± 0.015 |

### Dataset
- 350 owners · 9.1% churn rate (mirrors 91% retention) · 13.7% upsell-ready
- Upsell types: `SHARE_UPGRADE`, `AIRCRAFT_UPGRADE_PC24`, `COBALTPASS_TO_FRACTIONAL`, `JETFLY_INTRO`

### Demo narrative (CXO moment — at-risk)
```
Steven Sanchez    West Coast  1/16  util 21%  3 complaints  → 99.9% churn risk
Jessica Gonzalez  Northeast   1/32  util 22%  0 complaints  → 99.6% churn risk
```
Pattern: **low utilization + any service friction = very high churn risk**

### Demo narrative (upsell pipeline)
```
Lisa Clark         West Coast  1/8   → SHARE_UPGRADE        (99.9%)
Elizabeth Thomas   Northeast   1/32  → JETFLY_INTRO         (99.7%)
Nancy Clark        West Coast  1/16  → COBALTPASS→FRAC      (99.9%)
```

### Outputs
```
output/churn/
├── data/   — 5 CSVs (350 owners, ~26K flight legs, ~3.3K service interactions)
└── model/  — churn_model.json, upsell_model.json, 7 plots, 2 demo CSVs
```

### Agentic layer (spec — not yet built)
An account intelligence agent that:
- Surfaces top 10 at-risk owners weekly to account services team
- Generates a personalized outreach brief per owner (what to say, what to offer, what to avoid)
- Flags upsell-ready owners with a suggested conversation starter
- Monitors Jetfly usage patterns for JETFLY_INTRO candidates

---

## Demo 3 — IOC Dispatch Scheduling Agent ✅

**Pain point addressed:** PlaneSense's 24/7 IOC handles reservations, crew scheduling, flight planning, weather monitoring, maintenance coordination, slot management, catering, and client preferences for 240+ pilots and 60+ aircraft — entirely by a human team. Three new programs in 2025 (Jetfly, CobaltPass, Sourcing Solution) are compounding coordination load without a proportional technology layer.

**Why build this third:** Most technically impressive, most differentiating for Calfus, most directly tied to the CIO conversation. This is the demo that makes the CIO sit up straight.

### What was built
- **`generate_ioc_data.py`** — 4 CSVs: crew_roster (52 pilots), flight_requests (10), weather_events (4 advisories), owner_profiles (10 owners)
- **`ioc_dispatch_agent.py`** — Claude claude-sonnet-4-6 + 9 tool-use functions, full agentic loop
- Demo date: December 20, 2025 (peak holiday demand)

### 9 tools defined
| Tool | Purpose |
|------|---------|
| `get_pending_flight_requests` | Load IOC queue for a given date |
| `get_aircraft_maintenance_status` | Query ML model output for a tail |
| `get_available_aircraft` | Find dispatch-safe aircraft at a base |
| `get_available_crew` | Find available, rated crew at a base |
| `check_weather` | Check SIGMETs/PIREPs/NOTAMs on a route |
| `check_jetfly_availability` | Query Jetfly EU partner slot availability |
| `dispatch_flight` | Confirm and record a dispatch |
| `escalate_to_human` | Escalate with reason + suggested resolution |
| `send_owner_notification` | Send owner app + SMS confirmation |

### 5 scenarios demonstrated
1. **Weather delay** — IFR at KPSM → +90 min delay, owner notified (RQ-001)
2. **SIGMET delay** — MODERATE SIGMET at KBOS → +2h, alternate filed (RQ-005)
3. **Maintenance check** — CRITICAL alert on N800AF detected → substitution (RQ-003/007)
4. **Jetfly EU coordination** — EGLL→LSZH slot confirmed for HB-FXX (RQ-009)
5. **Crew escalation** — No PC-24-rated FO available → human dispatch + suggested resolution

### Demo run results (Dec 20, 2025)
- **5 dispatched** / 5 escalated from 10 requests · **49 tool calls**
- Dispatch log → `output/ioc/dispatch_log/dispatch_log_2025-12-20.json`

### How to run
```bash
# Demo mode (no API key needed — scripted replay):
python3 ioc_dispatch_agent.py --demo

# Live mode (Claude API):
export ANTHROPIC_API_KEY=sk-ant-...
python3 ioc_dispatch_agent.py
```

### Outputs
```
output/ioc/
├── data/          — crew_roster.csv, flight_requests.csv, weather_events.csv, owner_profiles.csv
└── dispatch_log/  — dispatch_log_2025-12-20.json
```

---

## Demo 4 — Parts Procurement Intelligence Agent 🔲

**Pain point addressed:** PlaneSense explicitly documented this on their site: *"The availability of aircraft parts and shipping delays are impacting the ability to repair and return aircraft to service in a timely manner. Parts are increasingly more costly."* Atlas Aircraft Center manages 194,000+ parts across two facilities.

**Primary buyer:** Todd Smith (Director of Airworthiness) + Atlas Aircraft Center leadership

**Why this is compelling:** Atlas is a distinct legal entity — this can be a standalone engagement, completely separate from the main PlaneSense IOC/ERP conversation. Gives Calfus two entry points into the same company.

### Proposed scope
**Synthetic data to build:**
- Parts catalog: part number, description, category (engine/avionics/structural), unit cost, criticality tier
- Current inventory: quantity on hand, reorder point, warehouse location (PSM vs BVU), expiry dates
- Consumption history: part consumed, aircraft/component, maintenance event, date
- Supplier catalog: supplier, part number, lead time (days), reliability score, contracted price
- Maintenance schedule: upcoming scheduled events by tail, required parts list per event type

**ML layer:**
- Demand forecasting model per part per base (ARIMA or LightGBM with time features)
- Shortage risk score = P(stockout before arrival | current demand + lead time)
- Supplier reliability scoring from historical fulfillment patterns

**Agentic layer:**
An agent that:
1. Loads the next 90-day maintenance schedule (already built in predictive maintenance data)
2. Forecasts parts demand from the schedule + unscheduled failure rates
3. Checks current inventory vs. projected demand
4. Checks supplier lead times for at-risk parts
5. Flags shortages before they happen (with lead time to act)
6. Auto-generates a procurement recommendation list (part, quantity, supplier, urgency)
7. Optionally raises a purchase order draft for human approval

**Demo narrative:**
> *"You have 3 PC-24 scheduled overhauls in February. At current consumption rates, you'll hit zero stock on [part X] on January 28th. Your primary supplier has a 21-day lead time. You need to order today. Here's the PO."*

### Estimated build time
- Synthetic data generator: ~2 hours
- Demand forecasting model: ~3 hours
- Procurement agent (Claude + tools): ~4 hours
- Total: ~1 day of development

---

## Demo 5 — CobaltPass Demand Forecasting + Dynamic Inventory Model 🔲

**Pain point addressed:** CobaltPass jet card launched May 2025 and **sold out by February 2026** — approximately 9 months. PlaneSense had no demand forecasting model to predict this. They also launched a dedicated "Sourcing Solution" team in August 2025 specifically to handle overflow demand beyond their own fleet.

**Primary buyer:** Jim Citro (CFO) + George Antoniadis (CEO, for pricing/inventory decisions)

**Why this is compelling:** CobaltPass selling out is simultaneously a validation (product-market fit is strong) and a business failure (they left revenue on the table, and customers who couldn't get a slot may have gone to competitors). The question *"how did you arrive at the initial inventory size?"* opens the entire forecasting gap.

### Proposed scope
**Synthetic data to build:**
- Booking history: date booked, flight date, origin/destination, pax, program type (fractional/CobaltPass/charter)
- CobaltPass inventory: slots available by week, price tier, remaining inventory
- External signals: airline passenger volumes, holiday calendar, economic index (private aviation demand), weather (ski season, summer destinations)
- Cancellation and reschedule patterns

**ML / forecasting layer:**
- Time-series demand model: weekly CobaltPass booking velocity with seasonality decomposition
- Price elasticity model: what happens to booking rate at different price points
- Capacity optimization: how many slots to make available per quarter at what price to maximize revenue without stockouts

**Agentic / analytics layer:**
A dashboard + recommendation engine that:
1. Shows projected demand for the next 4 quarters with confidence intervals
2. Recommends optimal CobaltPass inventory by quarter (e.g., "increase Q4 allocation by 40%, reduce Q1 by 15%")
3. Flags periods where demand is likely to exceed own fleet capacity → triggers Sourcing Solution proactive procurement
4. Models revenue impact of dynamic pricing (peak season premium)
5. Alerts when booking velocity suggests a sellout risk 6-8 weeks in advance

**Demo narrative:**
> *"Based on booking velocity and the ski season signal, you're on track to sell out your Q4 CobaltPass inventory by October 15th — 10 weeks early. If you add 12 more slots now and price them at a 15% peak premium, you capture an additional $X in revenue before the sellout. Want me to update the inventory?"*

### Estimated build time
- Synthetic time-series booking data: ~2 hours
- Forecasting model (Prophet or LightGBM with time features): ~3 hours
- Dashboard + recommendation agent: ~4 hours
- Total: ~1 day of development

---

## Building Order Recommendation

For the CXO meeting, the 3 built demos are enough. If there's time before the meeting or a follow-up discovery session, build in this order:

1. **Demo 4 (Parts Procurement)** — Atlas is a separate buyer and a fast win. The pain is explicitly documented. Shows Calfus understands the Atlas side of the business, not just the PlaneSense side.

2. **Demo 5 (CobaltPass Forecasting)** — Directly tied to a recent, visible failure (selling out). Strong CFO + CEO angle. Opens a pricing conversation that can lead to a broader data intelligence engagement.

### Connecting the demos to the conversation playbook

| Demo | Opens the door to |
|------|------------------|
| Predictive Maintenance | Oracle Cloud ERP for Atlas (OPP-02, OPP-03 in opportunity matrix) |
| Churn + Upsell | Owner Digital Experience Platform (OPP-04) + HubSpot data layer |
| IOC Dispatch Agent | Full IOC AI automation engagement (OPP-01) + AssistIQ (OPP-06) |
| Parts Procurement | Atlas ERP engagement, independent of main PlaneSense relationship |
| CobaltPass Forecasting | Data Intelligence platform (OPP-05) + dynamic pricing capability |

---

## Technical Reference

### Python environment
```bash
# Python 3.12 at:
/Users/atulvhanmarathi/projects/agents/.venv/bin/python3

# Key packages installed:
xgboost==3.2.0, lightgbm==4.6.0, scikit-learn==1.8.0
shap==0.50.0, matplotlib==3.10.8, seaborn==0.13.2
anthropic==0.55.0, pandas, numpy

# macOS note: XGBoost requires OpenMP
brew install libomp
```

### Project structure
```
web_scrapping/
├── DEMO_IDEAS.md                     ← this file
├── generate_synthetic_data.py        ← Demo 1 data
├── train_predictive_maintenance.py   ← Demo 1 ML
├── generate_churn_data.py            ← Demo 2 data
├── train_churn_model.py              ← Demo 2 ML
├── generate_ioc_data.py              ← Demo 3 data
├── ioc_dispatch_agent.py             ← Demo 3 agent
└── output/
    ├── predictive_maintenance/       ← Demo 1 outputs
    ├── churn/                        ← Demo 2 outputs
    ├── ioc/                          ← Demo 3 outputs
    └── research/reports/             ← BD research (opportunity matrix, deck, etc.)
```

### Running the demos
```bash
# Demo 1 — generate data + train
python3 generate_synthetic_data.py
python3 train_predictive_maintenance.py

# Demo 2 — generate data + train
python3 generate_churn_data.py
python3 train_churn_model.py

# Demo 3 — generate data + run agent
python3 generate_ioc_data.py
python3 ioc_dispatch_agent.py --demo          # no API key
python3 ioc_dispatch_agent.py                 # with ANTHROPIC_API_KEY set
```

---

*Created: February 2026 | For Calfus × PlaneSense CXO meeting preparation*

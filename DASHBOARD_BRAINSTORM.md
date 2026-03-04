# Dashboard Brainstorm — PlaneSense Data Analytics Demos

> **Date**: 2026-03-02
> **Context**: BD demo for CXO meeting with PlaneSense (CIO: Mandar Pendse)
> **Direction from seniors**: No ML model training/simulation needed. Focus on data analytics and dashboards.
> **Tool**: Power BI (primary), Python prototypes acceptable for iteration

---

## Core Narrative

"We don't have access to your internal operational data — but we went deep into publicly available FAA, NTSB, and your own published information. Here's what the data already tells us about your fleet type, and here's what an operational analytics layer would look like with real data plugged in."

This demonstrates:
1. We understand the aviation domain
2. We know where the data lives
3. We have a concrete vision for what analytics can surface
4. The gap between "what's publicly known" and "what you could know" is the sales pitch

---

## Available Data Inventory

### Real Public Data (downloaded)

| Dataset | Location | Records | Key Fields |
|---------|----------|---------|------------|
| FAA GA Survey 2020-2024 | `reference_data/faa_ga_survey_*/Ch1-Ch7.xlsx` | 35 Excel files | Fleet counts, utilization hours, fuel consumption, airframe hours by aircraft type, 5-year trends |
| FAA SDRS (PC-12/PC-24) | `reference_data/faa_aids/*.xls` | ~615 SDR records | Difficulty date, JASC code, component, failure description, operator, aircraft model |
| NTSB Accident DB | `reference_data/ntsb/avall.zip` | 89 MB MDB | All US aviation accidents since 1982, ~73 PC-12 events with narratives |
| NASR Airport DB | `reference_data/nasr_airports/nasr_28day.zip` | ~33,700 airports | Runway surface, length, elevation, location, type |
| NASA CMAPSS | `reference_data/archive.zip` | 4 datasets | Turbofan RUL benchmark, 26 sensors, 708 engine trajectories |
| NASA N-CMAPSS | `reference_data/N-CMAPSS_DS01-005.h5` | 2.7 GB HDF5 | Full flight-cycle engine degradation |

### Synthetic Data (generated)

| Dataset | Location | Records | Purpose |
|---------|----------|---------|---------|
| Aircraft registry | `predictive_maintenance/data/aircraft_registry.csv` | 62 | Fleet composition |
| Flight logs | `predictive_maintenance/data/flight_logs.csv` | 81,695 | 2-year flight simulation |
| Sensor readings | `predictive_maintenance/data/sensor_readings.csv` | 81,695 | Per-flight sensor snapshots |
| Maintenance records | `predictive_maintenance/data/maintenance_records.csv` | 11,258 | Scheduled + unscheduled events |
| Component installations | `predictive_maintenance/data/component_installations.csv` | 792 | Component wear tracking |
| Parts inventory | `predictive_maintenance/data/parts_inventory.csv` | 28 | Supply chain status |
| Failure events | `predictive_maintenance/data/failure_events.csv` | 17 | AOG/MAJOR events |
| Owner profiles | `churn/data/owners.csv` | 350 | Fractional owner base |
| Owner flight activity | `churn/data/flight_activity.csv` | 26,919 | 2-year owner flight history |

### Scraped Intelligence

| Source | Location | Records |
|--------|----------|---------|
| PlaneSense website | `output/research/` | 532 pages, 229 images |
| Executive summary | `output/research/reports/EXECUTIVE_SUMMARY.md` | Verified facts |
| Research reports | `output/research/reports/*.json` | 5 structured intelligence files |

---

## Dashboard Ideas

### SELECTED FOR BUILD

#### Dashboard 1: Fleet Utilization Analytics
**Data sources**: FAA GA Survey Ch3 (utilization hours) + Ch6 (airframe hours) + synthetic flight_logs + scraped PlaneSense facts
**Key visuals**:
- Turboprop vs light jet national utilization trends 2020-2024 (real FAA data)
- PlaneSense's 47,800 flights/yr benchmarked against national fleet averages
- Per-aircraft utilization heatmap (synthetic — "with your data, this is what you'd see")
- Seasonal flight volume patterns (monthly, showing summer peaks and winter troughs)
- Base-level comparison: PSM vs BVU utilization rates
- Fleet age vs utilization correlation scatter
- PC-12 vs PC-24 utilization split
**Story**: "Your fleet flies more than the national average for this aircraft class. But do you know which individual aircraft are underutilized? Which routes drive the most hours?"

#### Dashboard 2: Maintenance Intelligence
**Data sources**: FAA SDRS (615 real PC-12/PC-24 records) + synthetic maintenance_records + component_installations + parts_inventory
**Key visuals**:
- Real SDR failure type distribution by JASC/ATA code for PC-12 and PC-24
- Maintenance event timeline (scheduled vs unscheduled, real SDR dates)
- Component wear tracking across fleet (synthetic — "this is the operational view")
- Top 10 most-reported difficulty items from SDR data
- Unscheduled maintenance rate trends
- Downtime hours by event severity
- Parts inventory status with supply chain risk flags
- Maintenance cost distribution
**Story**: "FAA data shows these are the real failure patterns for your aircraft type. An operational dashboard would let you see this for YOUR fleet in real-time, predict the next event, and pre-position parts."

#### Dashboard 3: Route Network & Airport Accessibility
**Data sources**: NASR airports + synthetic flight_logs + scraped PlaneSense base locations
**Key visuals**:
- Map of all US airports PC-12 can access (including unpaved/short-strip) vs PC-24
- Route network from PSM and BVU hubs
- Airport accessibility advantage: PC-12 reaches X airports that jets cannot
- Regional coverage heat map
- Top destination airports by frequency
**Story**: "PC-12's unpaved runway capability gives PlaneSense access to airports no jet-only operator can reach. Here's exactly how many — and where they are."

#### Dashboard 4: Safety & Reliability Profile
**Data sources**: NTSB avall.zip (PC-12 events) + FAA SDRS trends
**Key visuals**:
- PC-12 incident timeline (NTSB data, 1982-present)
- Incident rate per 100K flight hours (normalized)
- Root cause distribution from NTSB narratives
- SDR trend lines over time (are difficulty reports increasing/decreasing?)
- Comparison: PC-12 safety record vs turboprop class average
**Story**: "The PC-12 has one of the best safety records in single-engine turboprops. Here's the data."

### KEPT FOR LATER

#### Dashboard 5: Owner Analytics & Retention
- Owner utilization by share type, engagement scoring, churn risk indicators
- Deferred because seniors said no ML focus; pure descriptive analytics version possible later

#### Dashboard 6: CobaltPass & Demand Forecasting
- Jet card demand trends, capacity utilization, pricing analytics
- Deferred — Demo 5 from DEMO_IDEAS.md, not yet built

#### Dashboard 7: Parts Procurement & Supply Chain
- Inventory optimization, supplier reliability, demand forecasting
- Deferred — Demo 4 from DEMO_IDEAS.md, not yet built

---

## Synthetic Data Validation Plan

Before building dashboards, cross-check our synthetic assumptions against real FAA data:

| Assumption | Our Synthetic Value | Real Data Source | Status |
|------------|-------------------|------------------|--------|
| PC-12 annual flight hours | ~850 hrs/yr | FAA GA Survey Ch6 (airframe hours by type) | TO CHECK |
| PC-24 annual flight hours | ~900 hrs/yr | FAA GA Survey Ch6 | TO CHECK |
| Flights per aircraft per day | Poisson(2.1) | FAA GA Survey Ch3 (hours ÷ avg leg) | TO CHECK |
| Seasonal multipliers | Jul 1.25x, Feb 0.85x | FAA GA Survey Ch3 (monthly if available) | TO CHECK |
| Component failure distribution | 17 types, custom rates | FAA SDRS PC-12/PC-24 exports | TO CHECK |
| Unscheduled maintenance rate | ~4% per interval | FAA SDRS frequency analysis | TO CHECK |
| Fleet size (62 aircraft) | Verified on planesense.com | N/A — confirmed | DONE |
| Annual flights (47,800) | Verified on planesense.com | N/A — confirmed | DONE |

**If real data significantly diverges from synthetic, regenerate synthetic data with corrected parameters before building dashboards.**

---

## Technical Approach

### Option A: Power BI (Final Deliverable)
- Prepare clean CSV/Excel files as Power BI data sources
- Document data model and relationships
- Build .pbix files in Power BI Desktop
- Requires: manual Power BI work (not automatable from CLI)

### Option B: Python Prototype → Power BI Port
- Build interactive dashboards in Plotly Dash or Streamlit first
- Iterate quickly on layout and KPIs
- Port final design to Power BI for polished client deliverable
- Advantage: can build and iterate from CLI

### Option C: Hybrid
- Parse and prepare all data in Python (automated)
- Build quick Streamlit prototypes for internal review
- Final client-facing version in Power BI
- **This is the recommended approach**

---

## Next Steps

1. **Parse real data** — Extract NTSB PC-12 events from avall.mdb, parse SDRS HTML-table XLS files, extract NASR airport data
2. **Validate synthetic data** — Compare our assumptions against FAA GA Survey Ch3/Ch6 numbers
3. **Prepare Power BI-ready datasets** — Clean, joined, with consistent keys
4. **Build Dashboard 1 & 2 first** (utilization + maintenance — highest impact for the meeting)
5. **Add Dashboard 3 & 4** (route network + safety — strong "we understand your business" signals)

---

## Key Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-02 | Focus on data analytics dashboards, not ML models | Senior direction — demonstrate analytical thinking, not model accuracy |
| 2026-03-02 | Use real FAA/NTSB data as primary layer, synthetic as "operational view" layer | Shows we did real research; synthetic shows what's possible with actual data |
| 2026-03-02 | Selected Dashboards 1-4 for build, deferred 5-7 | Utilization + Maintenance are the highest-impact topics for CIO meeting |
| 2026-03-02 | Recommended hybrid approach (Python prototype → Power BI) | Fastest iteration + polished final output |

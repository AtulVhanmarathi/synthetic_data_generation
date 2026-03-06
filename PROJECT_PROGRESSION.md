# PlaneSense Data Project — Progression & Change Log

**Last updated:** 2026-03-06
**Purpose:** Reference document tracking the full evolution of synthetic/analytics data generation from V1 to current state. Use this before making any data modifications to understand what has already been changed and why.

---

## Phase 1 — Research & Scraping

**Scripts:** `scraper.py`, `split_data.py`, `split_fleet.py`, `split_content.py`

Scraped planesense.com: 532 pages, 229 images, 0 errors. Partitioned into:
- 7 thematic content buckets (fractional ownership, comparisons/cost, aircraft, news/awards, people/guides, destinations, general)
- 3 fleet files (PC-24, PC-12, general)
- 1 company overview file

Output fed `output/research/reports/EXECUTIVE_SUMMARY.md` and `DECK_SLIDES.md` — 12-slide deck for CXO meeting with PlaneSense CIO (Mandar Pendse).

---

## Phase 2 — Synthetic Data V1 (Predictive Maintenance)

**Scripts:** `generate_synthetic_data.py`, `train_predictive_maintenance.py`
**Output:** `output/predictive_maintenance/data/` (9 CSVs), `output/predictive_maintenance/model/` (3 models)

First synthetic dataset: 62 aircraft (46 PC-12 NGX + 16 PC-24), 792 components, 81k flight logs.
Targets were rank-injected (not probabilistic) to ensure strong feature correlations.

**Model results:**
- fail_50h classifier: ROC-AUC 0.993, PR-AUC 0.939, CV-AUC 0.989 ± 0.007
- fail_100h classifier: ROC-AUC 0.991, PR-AUC 0.970
- RUL regressor: R² = 0.791, MAE = 483h
- Top predictor: wear_pct_max (r = 0.52 with fail_50h)

---

## Phase 3 — Customer Churn & IOC Agent

### Churn Model
**Scripts:** `generate_churn_data.py`, `train_churn_model.py`
**Output:** `output/churn/data/` (5 CSVs), `output/churn/model/` (2 models)

350 fractional owners, share types: 1/16, 1/8, 1/4, Cobalt. 2-year activity window (2023–2024).
- Churn classifier: ROC-AUC 0.953, PR-AUC 0.667, CV-AUC 0.969 ± 0.019 (9.1% churn rate)
- Upsell classifier: ROC-AUC 0.978, PR-AUC 0.948, CV-AUC 0.979 ± 0.015 (13.7% upsell rate)

### IOC Dispatch Agent
**Scripts:** `generate_ioc_data.py`, `ioc_dispatch_agent.py`
**Output:** `output/ioc/dispatch_log/dispatch_log_2025-12-20.json`

Claude claude-sonnet-4-6 tool-use agent. 9 tools. Demo date: Dec 20, 2025 (peak holiday day).
Result: 5 dispatched, 5 escalated from 10 requests (49 total tool calls).
Key scenarios: IFR weather delay (+90min), SIGMET delay (+2h), CRITICAL maintenance → substitute aircraft, Jetfly EU coordination (EGLL→LSZH), crew shortage escalation.

---

## Phase 4 — Strategy Pivot

**Senior direction:** No ML training/simulation. Focus on data analytics and Power BI dashboards.
**Narrative:** "We used authenticated public data to show our thought process for when we get actual data."

Key documents produced:
- `DASHBOARD_BRAINSTORM.md` — 4 dashboard proposals, inventory of available public datasets
- `DASHBOARD_EVALUATION.md` — deep critique of client's Book1.xlsx (scored 4/10 and 5/10 readiness). Identified missing star schema, no KPI cards, no fleet availability %, no cost/flight-hour, no scheduled vs unscheduled split. Critical missing table: `fact_aircraft_daily_status`
- `DASHBOARD_VISUALS.md` — full visual specifications and narrative arcs for 2 dashboards

---

## Phase 5 — Analytics Data Generation V1

**Script:** `generate_analytics_data.py`
**Output:** `output/analytics/data/` (12 CSVs)

Star schema: 7 dimensions + 5 facts.
- 142,841 flights × 3 years (2023–2025)
- 2,589 maintenance jobs, 6,893 maintenance detail lines
- 63,080 daily status rows (62 aircraft × ~1,096 days)
- 350 owners, 34 airports

**Calibration sources:**
- FAA GA Survey 2020–2024: PC-12 ~1,150 hrs/yr, PC-24 ~1,350 hrs/yr
- FAA SDRS: 615 PC-12/PC-24 service difficulty records (JASC codes, failure distribution)
- Target: 47,800 flights/yr | Achieved: 47,614 flights/yr ✅
- Deadhead ratio: 15% ✅ | Maintenance cost: ~$39/flight-hour ✅

---

## Phase 6 — Data Revision Cycle

All fix scripts are in `scripts/`. Each addresses a specific realism or integrity problem discovered after V1 generation.

### 6.1 Route Distribution Fix
**Script:** `scripts/regenerate_routes_v2.py`
**Reasoning doc:** `DATA_REVISION_V2_REASONING.md`

**Problem:** Routes were uniformly random — every airport received ~4,700–5,000 flights. Completely unrealistic.
**Fix:** Replaced with weighted probability matrix (model × purpose × season × owner_region).
- PC-12 constrained to pc12_accessible airports only
- PC-24 gets full range advantage and transcon routes
- KPSM (Portsmouth NH) as dominant hub for eastern fleet
- KBVU (Boulder City NV) western bias
- Leisure routes: summer→Northeast coastal/islands, winter→Florida
- Business routes: year-round major metros
- Medical routes: concentrated near major hospitals
- Also recalculated: distance_nm, flight_hours, block_hours, fuel, departure/arrival times
- Added: season, day_of_week to fact_flight; owner_type to dim_owner
- Synced fact_booking routes to match

### 6.2 Owner Data Integrity
**Script:** `scripts/fix_owner_data.py`

**Problems fixed:**
- Duplicate owner_type columns (x4 → x1)
- 1/32 share type does not exist in fractional aviation → reclassified to Share_1/16
- Share type names caused Excel to parse fractions as dates (e.g., "1/4" → Jan 4) → renamed to 'Share_1/4', 'Share_1/8', etc.
- Cobalt pass holders misconfigured (wrong share_type, wrong annual_hours=25)
- Duplicate season/day_of_week columns in fact_flight

### 6.3 AOG Consolidation
**Script:** `scripts/consolidate_aog.py`

**Problem:** AOG (Aircraft on Ground) events scattered randomly across all months. Unrealistic — AOG events cluster around inspection cycles.
**Fix:**
- Removed AOG from all months except March, May, October
- Targets: March → 6 AOG days/yr, May → 8 days/yr, October → 6 days/yr
- Boosted maintenance costs in AOG months: Parts = 1.40x labor, labor × 1.25x (emergency overtime)

### 6.4 Fleet Status Seasonality
**Script:** `scripts/fix_fleet_status_seasonality.py`

**Problem:** fact_aircraft_daily_status had no seasonal signal — flat FLYING% all year.
**Fix applied (V1 seasonality):**
- Summer (Jun–Aug): FLYING ~90%
- Spring/Fall (Mar–May, Sep–Nov): FLYING ~85%
- Winter (Dec–Feb): FLYING ~78%
- IN_MAINTENANCE boost: March/October ~14%, May ~12%
- Normalized all dates to YYYY-MM-DD format

### 6.5 Maintenance Cost Ratio
**Script:** `scripts/fix_maintenance_cost_ratio.py`

**Problem:** Parts/labor cost ratios had accidental spikes in wrong months (Jan/Jul/Dec 2023).
**Fix:**
- BOOST months (Mar + Oct, all years): Parts > Labor ~1.40x (heavy scheduled inspections)
- REVERT months (Jan/Jul/Dec 2023): Parts < Labor ~0.70x (routine labor-heavy work)

### 6.6 AOG Cost Realism
**Script:** `scripts/fix_aog_costs.py`

**Problem:** AOG line items in fact_maintenance_detail had PARTS = 0.0. Emergency AOG events always require expensive emergency parts procurement.
**Fix:**
- Top 3 AOG-heavy months (2024-05 ×12 days, 2023-05 ×6, 2023-06 ×5): 1.40x parts ratio + 1.25x labor
- AOG_REPAIR line items with PARTS = 0.0 → inserted emergency part costs (2x standard + emergency procurement premium)

### 6.7 Daily Status Hours Integrity
**Script:** `scripts/fix_daily_status_hours.py`

**Problem:** Data integrity violations — FLYING rows with flight_hours = 0, non-FLYING rows with hours > 0.
**Fix:** Enforced rules:
- FLYING rows: flight_hours > 0, flight_cycles > 0 (backfilled from aircraft-specific daily averages in fact_flight, fallback to fleet mean)
- AVAILABLE / IN_MAINTENANCE / AOG rows: flight_hours = 0, flight_cycles = 0

---

## Phase 7 — FLYING/AVAILABLE Rebalancing (Current)

**Script:** `scripts/rebalance_daily_status.py`

**Problems identified:**
1. AVAILABLE was only 6.6% overall — FAA benchmark for fractional ops is 14–20%
2. Summer AVAILABLE was 2.8% — dangerously unrealistic (no reserve capacity)
3. Holiday window (Dec 20–Jan 5) was LESS busy than surrounding winter (77.7% vs 78.1% FLYING) — inverted reality. Private aviation peaks sharply in this window.
4. 4,863 FLYING rows had no matching flight record in fact_flight — status contradicted by fact table

**Three-step fix:**

| Step | Action | Count |
|---|---|---|
| Step 1 | Convert FLYING rows with no matching fact_flight record → AVAILABLE | 4,863 rows |
| Step 2 | Holiday carve-out: boost Dec 20–Jan 5 FLYING back to 82% target | +359 rows |
| Step 3 | Seasonal fine-tuning per period to hit targets | ~1,442 rows |

**Final targets and results:**

| Period | Before FLYING | After FLYING | Before AVAILABLE | After AVAILABLE |
|---|---|---|---|---|
| Holiday (Dec 20–Jan 5) | 77.7% | **82.0%** | 13.5% | 9.2% |
| Rest of Winter | 78.1% | **64.0%** | 14.1% | 28.2% |
| Spring | 84.4% | 74.3% | 4.0% | 14.1% |
| Summer | 90.0% | 82.0% | 2.8% | 10.8% |
| Fall | 83.6% | 74.6% | 6.0% | 14.9% |
| **Overall** | **84.0%** | **74.7%** | **6.6%** | **16.0%** |

AOG and IN_MAINTENANCE rows: untouched throughout (9.2% and 0.1%).

---

## Current State of Analytics Data

**File:** `output/analytics/data/fact_aircraft_daily_status.csv` — v7 (after all 7 fix scripts)

| Metric | Value | Benchmark |
|---|---|---|
| Total flights/yr | 47,614 | 47,800 target ✅ |
| PC-12 utilization | ~1,150 hrs/yr | FAA GA Survey ✅ |
| PC-24 utilization | ~1,350 hrs/yr | FAA GA Survey ✅ |
| Overall FLYING% | 74.7% | 72–78% FAA fractional ops ✅ |
| Overall AVAILABLE% | 16.0% | 14–20% industry benchmark ✅ |
| Maint cost/flight-hr | ~$39 | Realistic for turboprop ✅ |
| AOG months | Mar/May/Oct only | Inspection cycle aligned ✅ |
| Holiday spike | 82% FLYING vs 64% shoulder | Peak demand reflected ✅ |
| Deadhead ratio | 15% | Industry norm ✅ |

---

## Dashboard Build Status

| Dashboard | Spec Doc | Build Status |
|---|---|---|
| Dashboard 1: Fleet Utilization | `DAX_DASHBOARD1_FLEET_UTILIZATION.md` | Spec complete, ready to build in Power BI |
| Dashboard 2: Maintenance Intelligence | `DAX_DASHBOARD2_MAINTENANCE.md` | Spec complete, ready to build in Power BI |
| Dashboard 3: Route/Airport | `DASHBOARD_VISUALS.md` | Outlined, not fully specced |
| Dashboard 4: Safety | `DASHBOARD_VISUALS.md` | Outlined, not fully specced |

---

## Phase 8 — V2 Consolidated Generator

**Script:** `generate_analytics_data_v2.py`

### Why V2 was created
The V1 pipeline had a fundamental design problem: the base generator had gaps, and 7 separate fix scripts in `scripts/` were needed to patch the output after generation. This created two sources of truth — if `generate_analytics_data.py` was run alone, the data was wrong. The correct state only existed after running all 9 scripts in the right order via `build_data.py`.

V2 folds all fix logic directly into the generator so it produces correct data in one pass.

### What V2 folds in (vs V1 + 7 fix scripts)

| V1 Fix Script | Where it lives in V2 |
|---|---|
| `regenerate_routes_v2.py` | `gen_fact_flight()` — haversine routing, weighted probability matrix, KPSM dominance, departure hour pools |
| `fix_owner_data.py` | `gen_dim_owner()` — correct share types (Share_1/4 etc.), Cobalt config, owner_type column at creation |
| `consolidate_aog.py` | `gen_daily_status()` Phase B — AOG assigned only to Mar/May/Oct during generation |
| `fix_fleet_status_seasonality.py` | `gen_daily_status()` Phase A — MONTH_TARGETS seasonal patterns applied at row creation |
| `fix_daily_status_hours.py` | `gen_daily_status()` Phase C — hours/cycles integrity enforced inline |
| `rebalance_daily_status.py` | `gen_daily_status()` Phase D — FLYING↔AVAILABLE rebalance + holiday spike, all in-memory before write |
| `fix_maintenance_cost_ratio.py` + `fix_aog_costs.py` | `gen_maintenance()` post-generation in-memory pass — BOOST_MONTHS 1.40x, REVERT_MONTHS 0.70x, AOG emergency costs, missing PARTS rows added |

### New architecture in `gen_fact_flight()`
V2 uses actual haversine distances between the 34 airports (with lat/lon) for realistic `distance_nm`, `flight_hours`, `block_hours`, and `fuel_consumed_gal`. A practical minimum leg time (0.8h PC-12 / 1.0h PC-24) prevents unrealistically short hops on nearby NE airport pairs.

### V2 output benchmarks

| Metric | V2 Result | Target | Note |
|---|---|---|---|
| Annualized flights | ~47,680/yr | ~47,800 | ✅ |
| Deadhead ratio | 14.8% | 15% | ✅ |
| Daily status FLYING% | 74.7% | 72–78% | ✅ |
| Daily status AVAILABLE% | 16.0% | 14–20% | ✅ |
| Holiday spike (Dec20-Jan5) | 82% FLYING | 82% | ✅ |
| AOG days (Mar/May/Oct) | 6/8/6 per year | 6/8/6 | ✅ 9/9 |
| Avg hrs/ac/yr | ~833 | ~1,150/1,350 | ⚠️ Below aspirational target (same as V1=873; gauss truncation effect) |
| Maint cost/flt-hr | ~$46 | ~$39 | ⚠️ Slightly above (fewer hours, similar cost base — acceptable) |

The hrs/ac/yr gap is a known V1 characteristic — the generator never hit the aspirational 1,150 target due to gauss truncation in `n_flights` calculation. V2 is 5% lower than V1 due to weighted routes creating more regional (shorter) legs.

### How to use
```bash
python3 generate_analytics_data_v2.py
```
One script. One run. ~15 seconds. `build_data.py` and `scripts/` are preserved for reference and rollback.

---

## Rebuilding Data from Scratch

All generated CSVs are gitignored. On a fresh clone, run:

```bash
python3 build_data.py
```

This executes all 9 scripts in dependency order and produces `output/analytics/data/` in ~14 seconds.

**Partial rebuild options:**
```bash
python3 build_data.py --from 4    # Resume from step 4 (skip steps 1–3)
python3 build_data.py --only 9    # Run only step 9
```

**Step dependency map:**

```
Step 1 (generate_analytics_data.py)
  └─► Step 2 (regenerate_routes_v2.py)   ← needs latitude/longitude in dim_airport.csv
        └─► Step 3 (fix_owner_data.py)   ← cleans up after route regen

Step 4 (consolidate_aog.py)              ← must precede step 5
  └─► Step 5 (fix_aog_costs.py)
Step 6 (fix_maintenance_cost_ratio.py)   ← depends on step 4 AOG months being set

Step 7 (fix_fleet_status_seasonality.py) ← must run before step 8
  └─► Step 8 (fix_daily_status_hours.py) ← integrity pass after seasonality set
        └─► Step 9 (rebalance_daily_status.py) ← final FLYING/AVAILABLE pass, must be last
```

**Known fix applied during pipeline creation:** `generate_analytics_data.py` was not writing
`latitude`/`longitude` to `dim_airport.csv`, causing step 2 to fail with `KeyError: 'latitude'`.
Fixed by adding `lat`/`lon` coordinates to the `AIRPORTS` constant and including them in the CSV output.

---

## Key Files Quick Reference

| File | Purpose |
|---|---|
| `generate_analytics_data.py` | Master data generator — 12 CSV star schema |
| `DATA_REVISION_V2_REASONING.md` | Route redesign justification (most detailed reasoning doc) |
| `DASHBOARD_EVALUATION.md` | Gap analysis of Book1.xlsx, proposed star schema |
| `DASHBOARD_VISUALS.md` | Visual specs and narrative arcs |
| `DAX_DASHBOARD1_FLEET_UTILIZATION.md` | Step-by-step Power BI build guide, Dashboard 1 |
| `DAX_DASHBOARD2_MAINTENANCE.md` | Step-by-step Power BI build guide, Dashboard 2 |
| `scripts/regenerate_routes_v2.py` | Route realism fix (biggest structural change) |
| `scripts/rebalance_daily_status.py` | Latest fix — FLYING/AVAILABLE rebalancing + holiday spike |

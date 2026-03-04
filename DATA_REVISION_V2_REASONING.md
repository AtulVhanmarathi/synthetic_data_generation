# Data Revision V2 — Reasoning, Decisions & Change Log

**Date**: 2026-03-04
**Author**: Data / BI team (via AI-assisted review)
**Previous version**: `20260303_EDA_analytics_data.ipynb` / initial synthetic data generation
**Scope**: Route realism, aircraft model constraints, seasonality, new analytical columns

---

## 1. Why We Revised the Data

This dataset is synthetic but grounded in real PlaneSense operational context (FAA data, PlaneSense public information, OurAirports). After the initial generation, a review identified that while the **volume**, **flight purpose distribution**, and **aircraft specifications** were realistic, the **route (origin/destination) selection** was generated with uniform random airport sampling — producing a flat, unrealistic airport distribution that doesn't reflect how fractional aviation actually operates.

**Primary symptoms identified:**
- All airports outside KPSM had nearly identical flight counts (~4,700–5,000 each for both origin and destination)
- Business and Leisure flights were routed to the same airports in near-identical proportions
- No meaningful seasonality in destination choices (Leisure in July only ~29% higher than January — should be 2–3x)
- PC-12 and PC-24 drew from the same airport pool despite PC-12 having short-strip limitations
- KBVU-based (West) PC-24 aircraft were not routing toward western airports (KLAS, KSAN, KLAX, KSFO)
- Owner region was not influencing flight routing (Northeast owners flying to West coast as often as Southeast owners)

---

## 2. What Was NOT Changed (and Why)

| Component | Decision | Reasoning |
|-----------|----------|-----------|
| `flight_purpose` value counts | Kept unchanged | Confirmed realistic: 64,882 Business / 33,018 Leisure / 13,998 Mixed / 5,779 Medical / 20,811 Repositioning / 4,353 Maintenance Ferry |
| `fact_aircraft_daily_status` | Kept unchanged | Fleet status is independent of routing; daily status, maintenance state, fleet growth from 46→62 aircraft are all valid |
| `fact_maintenance_job` / `fact_maintenance_detail` | Kept unchanged | Maintenance is facility-driven (FAC-PSM / FAC-BVU), not route-driven |
| All dimension tables (except `dim_owner`) | Kept unchanged | `dim_aircraft`, `dim_airport`, `dim_crew`, `dim_date`, `dim_facility`, `dim_component` all remain as-is |
| `dim_airport` | Kept unchanged | Already has `pc12_accessible`, `pc24_accessible`, `latitude`, `longitude`, `city`, `state`, `region` — used as the reference for route weighting |
| PC-12 vs PC-24 distance separation | Kept (already good) | Pre-revision: PC-12 avg 263nm / max 632nm vs PC-24 avg 578nm / max 1,220nm — realistic against specs |
| Overall flight volume | Kept (142,841 rows) | Consistent with ~47,800 flights/year for PlaneSense scale |
| Journey structure (booking_id, leg sequences) | Preserved | Multi-leg journey coherence maintained |

---

## 3. What Was Changed

### 3.1 Route Selection Logic — `fact_flight` and `fact_booking`

**Columns affected**: `origin_icao`, `destination_icao` (and derived: `distance_nm`, `flight_hours`, `block_hours`, `fuel_consumed_gal`, `departure_time`, `arrival_time`)

**Old approach**: Uniform random sampling from the full 34-airport pool for all models, purposes, and seasons.

**New approach**: Weighted probability matrix driven by:

```
model  ×  flight_purpose  ×  season  ×  owner_region  →  airport_pair_weights
```

**Airport pool assignment by purpose:**

| Purpose | Airport pool logic |
|---------|-------------------|
| **Leisure** (Summer: Jun–Aug) | Heavy bias: KACK, KMVY, 2B2, K1B1, KPWM, KSFM (Northeast coastal/island). Florida airports drop significantly in summer |
| **Leisure** (Winter: Dec–Feb) | Shift toward: KMIA, KPBI, KFLL, KTPA (Florida snowbird pattern), KLAS, KSAN (West leisure destinations) |
| **Leisure** (Spring/Fall) | Transitional — mixed Northeast with moderate Florida |
| **Business** | Year-round bias toward metro business hubs: KTEB, KHPN, KEWR, KJFK, KBOS, KORD, KATL, KIAD, KPHL, KCLT. Moderate Q4/holiday dip |
| **Medical** | Concentrated around major medical center airports: KBOS (Mass General/Dana-Farber), KJFK/KEWR (Memorial Sloan Kettering), KPHL (Penn Medicine), KIAD (Johns Hopkins) |
| **Mixed** | Blend of Business and Leisure pools |
| **Repositioning** | Back-channel logic: typically returning to hub (KPSM) or repositioning to next pickup origin |
| **Maintenance Ferry** | Restricted to KPSM ↔ KBVU corridor, or aircraft base facility |

**Model constraints enforced:**

| Aircraft | Rule |
|----------|------|
| PC-12 NGX | Can only use airports where `pc12_accessible = 1` AND `pc24_accessible` can be 0 or 1. Max practical distance cap: 600nm. Biased toward Northeast short-strip airports |
| PC-24 | Can use all airports (`pc24_accessible = 1` only). Max practical distance: 1,200nm. KBVU-based PC-24 aircraft get additional West region bias (KLAS, KSAN, KLAX, KSFO, KAPC, KDEN) |

**Owner region influence:**

| Owner Region | Route bias |
|-------------|-----------|
| Northeast (102 owners) | Strongly biased toward Northeast airports; occasional Southeast leisure |
| Mid-Atlantic (72 owners) | Mid-Atlantic + Northeast mix; KIAD, KPHL as common bases |
| Southeast (69 owners) | Southeast airports (KMIA, KATL, KCLT) + Northeast business |
| West (55 owners) | Western airports for KBVU-based flights (KLAS, KSAN, KLAX, KSFO, KDEN); cross-country when PC-24 |
| Midwest (52 owners) | KORD, KMSP as hubs; Northeast/Southeast connections |

**KPSM dominance preserved**: As the primary PlaneSense base and maintenance facility, KPSM retains its status as the dominant origin airport (~7,000+ revenue departures vs ~2,000–4,000 for secondary hubs).

### 3.2 Derived Field Recalculation

When origin/destination changes, these fields are recalculated from scratch:

| Field | Recalculation method |
|-------|---------------------|
| `distance_nm` | Haversine formula from `dim_airport[latitude]` and `dim_airport[longitude]` |
| `flight_hours` | `distance_nm / cruise_speed_knots` where PC-12 NGX = 270 knots, PC-24 = 340 knots |
| `block_hours` | `flight_hours × 1.15` (standard 15% block time buffer for taxi, climb, descent) |
| `fuel_consumed_gal` | PC-12 NGX: `flight_hours × 68 gal/hr`; PC-24: `flight_hours × 95 gal/hr` (approximate typical burn rates) |
| `departure_time` | Day-of-week weighted: Business peaks Mon/Fri (0600–0900 departure), Leisure peaks Fri/Sun (0900–1200) |
| `arrival_time` | `departure_time + block_hours` |

### 3.3 New Column: `season` in `fact_flight`

**Why added**: Makes seasonality directly queryable in Power BI without requiring a DAX formula. Enables a Season slicer natively.

| Value | Months |
|-------|--------|
| Winter | Dec, Jan, Feb |
| Spring | Mar, Apr, May |
| Summer | Jun, Jul, Aug |
| Fall | Sep, Oct, Nov |

### 3.4 New Column: `day_of_week` in `fact_flight`

**Why added**: Enables Business Mon/Fri vs Leisure Fri/Sun day-of-week analysis as a direct slicer or visual axis, without needing `WEEKDAY()` DAX.

| Value | Range |
|-------|-------|
| Integer 1–7 | 1 = Monday, 7 = Sunday (ISO weekday convention) |

### 3.5 New Column: `owner_type` in `dim_owner`

**Why added**: The existing `share_type` column (e.g., 1/32, 1/16) indicates share size but doesn't directly convey behavioral archetype. `owner_type` provides a segmentation useful for analyzing Leisure vs Business routing patterns at owner level.

| Value | Description |
|-------|-------------|
| Corporate | Company-owned share; primarily Business purpose flights |
| Individual | Individual/HNW personal share; primarily Leisure/Mixed |
| Family | Family-owned share; Leisure dominant, seasonal patterns |

**Assignment logic**: Derived from existing `share_type` and inferred from `aircraft_preference` and historical flight purpose distribution per owner.

---

## 4. Tables Impact Summary

| Table | Changed | New Columns | Notes |
|-------|---------|-------------|-------|
| `fact_flight` | ✅ Yes | `season`, `day_of_week` | Routes, distances, times, fuel recalculated |
| `fact_booking` | ✅ Yes | None | `origin_icao`, `destination_icao` synced with fact_flight routes |
| `dim_owner` | ✅ Yes | `owner_type` | New classification column added |
| `fact_aircraft_daily_status` | No | None | Unchanged |
| `fact_maintenance_job` | No | None | Unchanged |
| `fact_maintenance_detail` | No | None | Unchanged |
| `dim_airport` | No | None | Already complete with lat/lon added 2026-03-03 |
| `dim_aircraft` | No | None | Unchanged |
| `dim_crew` | No | None | Unchanged |
| `dim_date` | No | None | Unchanged |
| `dim_facility` | No | None | Unchanged |
| `dim_component` | No | None | Unchanged |
| `dim_owner` | No | None | Unchanged |

---

## 5. Expected Validation Results After Revision

After running the regeneration script, the following should hold:

### Route Distribution
- KPSM should remain dominant origin (~7,000+ departures) — significantly above all others
- Top business destination cluster (KTEB, KHPN, KEWR, KJFK) should be clearly elevated above leisure destinations year-round
- Top leisure destinations (KACK, KMVY) should show a strong summer peak

### Seasonality
- Leisure flights to KACK/KMVY: Summer count should be 2–3x Winter count
- Leisure flights to KMIA/KPBI: Winter count should be 2–3x Summer count
- Business flights: relatively flat across months (~10–15% seasonal variance max)

### PC-12 vs PC-24 Separation
- PC-12 routes: all within `pc12_accessible = 1` airports; max distance ~600nm; zero western cross-country routes
- PC-24 routes: can reach all airports; KBVU-based aircraft show western airport cluster (KLAS, KSAN, KLAX)
- 2B2 (Plum Island) and K1B1 (Hudson): should appear only in PC-12 flights (both have `pc24_accessible = 0`)

### Day-of-Week Pattern
- Business flights: Monday and Friday should be the top 2 days
- Leisure flights: Friday and Sunday should be the top 2 days

### Owner Type vs Purpose
- Corporate owners: >70% Business purpose flights
- Individual/Family owners: >50% Leisure + Mixed purpose flights

---

## 6. Files Touched by the Revision Script

```
output/analytics/data/fact_flight.csv         ← routes, derived fields, + 2 new columns
output/analytics/data/fact_booking.csv        ← routes synced
output/analytics/data/dim_owner.csv           ← + owner_type column
```

**Script location**: `scripts/regenerate_routes_v2.py`

---

## 7. Additional Data Quality Fixes — dim_owner (post-revision audit)

Identified and fixed after the route revision:

### Issue 1 — `1/32` share type does not exist in PlaneSense's program
PlaneSense's minimum fractional ownership is **1/16 (50 hrs/year)**. The original generation incorrectly included `1/32` (73 owners).
- **Fix**: All 73 `1/32` owners reclassified to `Share_1/16`, `annual_hours_contracted = 50`

### Issue 2 — Cobalt pass holders had incorrect fractional ownership data
42 owners with `cobalt_pass_holder = 1` were incorrectly assigned fractional `share_type` values (1/8, 1/16, 1/4) and corresponding contracted hours (100–400). Cobalt is an entry access program — 25 hrs/year, no fractional share ownership.
- **Fix**: All 42 Cobalt holders set to `share_type = Cobalt`, `annual_hours_contracted = 25`

### Issue 3 — `share_type` string values parsed as dates by Excel / Power BI
Fraction strings like `"1/8"` are auto-detected as January 8th, `"1/16"` as January 16th, `"1/32"` as a parse error. This silently breaks any slicer or filter on this column.
- **Fix**: Values renamed to `"Share_1/4"`, `"Share_1/8"`, `"Share_1/16"`, `"Cobalt"` — unambiguous text categories

### Issue 4 — Duplicate columns from repeated script runs
Running `regenerate_routes_v2.py` multiple times appended new `owner_type` columns to `dim_owner.csv` and new `season`/`day_of_week` columns to `fact_flight.csv`.
- **dim_owner**: `owner_type` appeared 4× — deduplicated to 1
- **fact_flight**: `season` and `day_of_week` each appeared 4× — deduplicated to 1
- **Script fix**: Both scripts now check if columns already exist before appending (idempotent)

**Script used**: `scripts/fix_owner_data.py`

### Final dim_owner `share_type` distribution after all fixes
| share_type | Count | annual_hours |
|------------|-------|-------------|
| Share_1/16 | 169   | 50           |
| Share_1/8  | 86    | 200          |
| Share_1/4  | 53    | 400          |
| Cobalt     | 42    | 25           |

---

## 8. What This Does NOT Fix (Known Remaining Limitations)

- **Owner-specific preference persistence**: An individual owner's personal preferred destinations are not tracked across bookings. A true owner preference model would require a separate owner behavior profile table.
- **Multi-stop journey geographic coherence**: For journeys with 3+ legs, intermediate stops are logically consistent within a region but are not guaranteed to follow real-world flight path geography exactly.
- **Weather and ATC delays**: `weather_delay_min` values are not updated — they remain synthetically generated from the original pass.
- **Crew assignment to route**: Crew IDs remain unchanged. In reality, crew base assignments would constrain which crew fly which routes. Not revised in this pass.

---

*Document maintained by: Data / BI team*
*For Dashboard DAX context, refer to `DAX_DASHBOARD1_FLEET_UTILIZATION.md` and `DAX_DASHBOARD2_MAINTENANCE.md`*

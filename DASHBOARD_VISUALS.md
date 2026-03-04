# Power BI Dashboard — Visual Specifications

> **Data Source**: `output/analytics/data/` (12 CSVs, star schema)
> **Target**: 2 dashboards — Aircraft Utilization + Maintenance Intelligence
> **Audience**: CIO-level (Mandar Pendse, PlaneSense)

---

## Data Model — How Tables Connect in Power BI

```
dim_date ──────────┬──── fact_flight (date)
                   ├──── fact_booking (departure_date, booking_date)
                   ├──── fact_maintenance_job (date)
                   ├──── fact_maintenance_detail (date)
                   └──── fact_aircraft_daily_status (date)

dim_aircraft ──────┬──── fact_flight (aircraft_id)
                   ├──── fact_maintenance_job (aircraft_id)
                   ├──── fact_maintenance_detail (aircraft_id)
                   └──── fact_aircraft_daily_status (aircraft_id)

dim_airport ───────┬──── fact_flight (origin_icao, destination_icao)
                   └──── fact_booking (origin_icao, destination_icao)

dim_component ─────┬──── fact_maintenance_detail (jasc_ata_code)

dim_facility ──────┬──── fact_maintenance_job (facility_id)
                   ├──── fact_maintenance_detail (facility_id)
                   └──── dim_aircraft (base_facility_id)

dim_crew ──────────┬──── fact_flight (pilot_id)
                   └──── fact_maintenance_job (technician_id)

dim_owner ─────────┬──── fact_flight (owner_id)
                   └──── fact_booking (owner_id)
```

---

## Dashboard 1: Aircraft Utilization

### Page 1 — Fleet Utilization Overview

#### Slicers (Top Bar)
| Slicer | Source | Type |
|--------|--------|------|
| Date Range | dim_date.date | Date range picker |
| Year | dim_date.year | Dropdown |
| Aircraft Model | dim_aircraft.model | Buttons (PC-12 NGX / PC-24 / All) |
| Base Facility | dim_facility.facility_name | Dropdown |
| Flight Purpose | fact_flight.flight_purpose | Multi-select |

#### Row 1 — KPI Cards (6 cards across top)

| Card | DAX Measure | Format | Benchmark |
|------|-------------|--------|-----------|
| **Total Flight Hours** | `SUM(fact_flight[flight_hours])` | #,##0 | — |
| **Total Flights** | `COUNTROWS(fact_flight)` | #,##0 | ~47,800/yr |
| **Avg Hours/Aircraft/Day** | `DIVIDE(SUM(fact_flight[flight_hours]), DISTINCTCOUNT(dim_aircraft[aircraft_id]) * DISTINCTCOUNT(dim_date[date]))` | 0.0 | FAA avg: 8.7 hrs/day for turboprop |
| **Fleet Availability %** | `DIVIDE(CALCULATE(COUNTROWS(fact_aircraft_daily_status), fact_aircraft_daily_status[status] IN {"FLYING","AVAILABLE"}), COUNTROWS(fact_aircraft_daily_status))` | 0.0% | Target: >90% |
| **Deadhead Ratio** | `DIVIDE(CALCULATE(COUNTROWS(fact_flight), fact_flight[is_deadhead]=1), COUNTROWS(fact_flight))` | 0.0% | Industry: 10-20% |
| **Total Passengers** | `SUM(fact_flight[passenger_count])` | #,##0 | — |

#### Row 2 — Trends (2 visuals)

**Visual 2a: Monthly Flight Hours Trend** (Line chart)
- X: dim_date[month_name] + dim_date[year]
- Y: SUM(fact_flight[flight_hours])
- Legend: dim_aircraft[model]
- Add constant line: FAA GA Survey avg (267 hrs/mo for turboprop single-engine = 3,200/12)
- Tooltip: flight count, avg leg duration

**Visual 2b: Aircraft Utilization Heatmap** (Matrix)
- Rows: dim_aircraft[tail_number]
- Columns: dim_date[month_name]
- Values: SUM(fact_flight[flight_hours])
- Conditional formatting: Red (<50 hrs/mo) → Yellow (50-80) → Green (>80)
- This is the single most powerful visual for identifying underutilized aircraft

#### Row 3 — Operational Breakdowns (3 visuals)

**Visual 3a: Top 15 Routes by Frequency** (Horizontal bar chart)
- Y: CONCATENATE(fact_flight[origin_icao], " → ", fact_flight[destination_icao])
- X: COUNT(fact_flight[flight_id])
- Color: dim_aircraft[model]
- Drill-through: click route → see all flights on that route

**Visual 3b: Fleet Status Over Time** (Stacked area chart)
- X: dim_date[date]
- Y: COUNT(fact_aircraft_daily_status[aircraft_id])
- Legend: fact_aircraft_daily_status[status] — FLYING / AVAILABLE / IN_MAINTENANCE / AOG
- Color: FLYING=green, AVAILABLE=blue, IN_MAINTENANCE=amber, AOG=red
- This shows fleet availability trends — critical for capacity planning

**Visual 3c: Regional Utilization** (Filled map OR bar chart)
- Category: dim_airport[region]
- Values: SUM(fact_flight[flight_hours]) for departures
- Size: COUNT(fact_flight[flight_id])
- Shows Northeast dominance and West Coast growth

---

### Page 2 — Flight Operations Detail

#### Row 1 — Distribution Charts (3 visuals)

**Visual 4a: Flight Duration Distribution** (Histogram)
- Values: fact_flight[flight_hours]
- Bins: 0.5h increments
- Legend: dim_aircraft[model]
- Shows PC-12 peaks at ~1.0h, PC-24 peaks at ~1.4h

**Visual 4b: Hourly Departure Distribution** (Column chart)
- X: HOUR(fact_flight[departure_time])
- Y: COUNT(fact_flight[flight_id])
- Shows peak departure hours (9-11 AM typically)

**Visual 4c: Seasonal Pattern** (Line chart)
- X: dim_date[month_name]
- Y: COUNT(fact_flight[flight_id])
- Legend: dim_date[year]
- Shows summer peak, February trough — consistent across years

#### Row 2 — Deadhead & Efficiency (2 visuals)

**Visual 5a: Deadhead Analysis** (Donut + table)
- Donut: Revenue flights vs Deadhead vs Maintenance Ferry
- Table below: Top 10 deadhead routes by frequency

**Visual 5b: Fuel Consumption Trend** (Combo chart)
- Bars: SUM(fact_flight[fuel_consumed_gal]) by month
- Line: AVG(fact_flight[fuel_consumed_gal]) per flight
- Legend: dim_aircraft[model]

#### Row 3 — Booking Intelligence (2 visuals)

**Visual 6a: Booking Lead Time Distribution** (Histogram)
- Values: fact_booking[lead_time_days]
- Shows how far in advance owners book (avg ~7 days)

**Visual 6b: Booking Channel Mix** (Stacked bar by month)
- X: dim_date[month_name]
- Y: COUNT(fact_booking[booking_id])
- Legend: fact_booking[booking_channel] — Phone / Mobile App / Owner Portal / Account Manager
- Shows digital adoption trend (if App % is growing)

---

### Page 3 — Airport & Route Network

**Visual 7a: Airport Map** (ArcGIS or Filled Map)
- Locations: dim_airport lat/lon
- Size: flight count from that airport
- Color: dim_airport[pc24_accessible] — shows PC-12 can reach airports PC-24 cannot
- Bubble size shows traffic volume

**Visual 7b: PC-12 Advantage Airports** (Table)
- Filter: dim_airport[pc24_accessible] = 0
- Shows: airport name, city, runway length, flight count
- Story: "PC-12 accesses X airports that jets cannot reach"

**Visual 7c: Top 20 Airport Pairs** (Chord diagram or Sankey)
- If Power BI supports it; otherwise horizontal bar of origin→destination pairs

---

## Dashboard 2: Maintenance Intelligence

### Page 1 — Maintenance Overview

#### Slicers (Top Bar)
| Slicer | Source | Type |
|--------|--------|------|
| Date Range | dim_date.date | Date range picker |
| Facility | dim_facility.facility_name | Buttons (Portsmouth / Boulder City / All) |
| Aircraft Model | dim_aircraft.model | Buttons |
| Maintenance Type | fact_maintenance_job.maintenance_type | Multi-select |
| Severity | fact_maintenance_job.severity | Multi-select |
| Scheduled/Unscheduled | fact_maintenance_job.is_scheduled | Buttons (Scheduled / Unscheduled / All) |

#### Row 1 — KPI Cards (7 cards)

| Card | DAX Measure | Format | Benchmark |
|------|-------------|--------|-----------|
| **Total Maintenance Cost** | `SUM(fact_maintenance_detail[extended_cost])` | $#,##0 | — |
| **Cost / Flight Hour** | `DIVIDE(SUM(fact_maintenance_detail[extended_cost]), SUM(fact_flight[flight_hours]))` | $#,##0 | Industry: $200-$400 for turboprop |
| **MTBF (hours)** | `DIVIDE(SUM(fact_flight[flight_hours]), CALCULATE(COUNTROWS(fact_maintenance_job), fact_maintenance_job[is_scheduled]=0))` | #,##0 | Higher = better |
| **MTTR (hours)** | `AVERAGE(fact_maintenance_job[total_elapsed_hours])` | 0.0 | Lower = better |
| **Downtime %** | `DIVIDE(CALCULATE(COUNTROWS(fact_aircraft_daily_status), fact_aircraft_daily_status[status] IN {"IN_MAINTENANCE","AOG"}), COUNTROWS(fact_aircraft_daily_status))` | 0.0% | Target: <5% |
| **Scheduled / Unscheduled Ratio** | `DIVIDE(CALCULATE(COUNTROWS(fact_maintenance_job), fact_maintenance_job[is_scheduled]=1), COUNTROWS(fact_maintenance_job))` | 0.0% | Target: >85% scheduled |
| **AOG Events** | `CALCULATE(COUNTROWS(fact_maintenance_job), fact_maintenance_job[severity]="AOG")` | #,##0 | Target: 0 |

#### Row 2 — Trends & Splits (3 visuals)

**Visual 8a: Maintenance Cost Trend** (Stacked area chart)
- X: dim_date[month_name] + dim_date[year]
- Y: SUM(fact_maintenance_detail[extended_cost])
- Legend: fact_maintenance_detail[cost_category] — LABOR / PARTS / FUEL / CERTIFICATION
- Shows cost composition and whether parts or labor is driving increases

**Visual 8b: Scheduled vs Unscheduled Events** (Combo chart)
- Bars: COUNT of scheduled events (green) and unscheduled events (red) by month
- Line: Unscheduled rate % (= unscheduled / total)
- Rising unscheduled rate = fleet health declining

**Visual 8c: Maintenance by Facility** (Clustered bar)
- X: dim_facility[facility_name]
- Y: COUNT(fact_maintenance_job[maintenance_job_id])
- Legend: maintenance_type
- Shows workload distribution between Portsmouth and Boulder City

#### Row 3 — Component & Cost Analysis (3 visuals)

**Visual 9a: Top 10 Components by Cost** (Horizontal bar)
- Y: dim_component[component_name] (via JASC code join)
- X: SUM(fact_maintenance_detail[extended_cost])
- Filtered to cost_category = PARTS
- Shows which systems drive the most parts spend

**Visual 9b: Top 5 Aircraft by Maintenance Cost** (Bar chart)
- Y: dim_aircraft[tail_number]
- X: SUM(fact_maintenance_detail[extended_cost])
- Color: dim_aircraft[model]
- Action: "Which individual aircraft are costing us the most?"

**Visual 9c: JASC System Failure Distribution** (Treemap)
- Category: dim_component[system_name]
- Sub-category: dim_component[component_name]
- Values: COUNT of unscheduled maintenance events
- Calibrated from real SDRS data: Flight Controls > Engine > Landing Gear > Instruments

---

### Page 2 — Maintenance Detail & Reliability

#### Row 1 — Reliability Metrics (2 visuals)

**Visual 10a: MTBF by Aircraft** (Bar chart sorted ascending)
- Y: dim_aircraft[tail_number]
- X: Aircraft-level MTBF (flight hours / unscheduled events)
- Color: Red if MTBF < fleet average, Green if above
- Shows which aircraft are least reliable

**Visual 10b: MTTR by Maintenance Type** (Box plot or bar chart)
- Category: fact_maintenance_job[maintenance_type]
- Values: AVG(total_elapsed_hours)
- Shows which types take longest — AOG should dominate

#### Row 2 — Work Order Details (1 visual)

**Visual 11: Maintenance Job Table** (Paginated table with drill-through)
- Columns: Job ID | Date | Aircraft | Facility | Type | Severity | Trigger | Status | Duration | Cost
- Sortable by any column
- Filter by: open jobs, AOG only, specific facility
- Drill-through to detail lines (labor, parts, fuel breakdown)

#### Row 3 — Trigger Source Analysis (2 visuals)

**Visual 12a: How Defects Are Found** (Donut chart)
- Values: COUNT by fact_maintenance_job[trigger_source]
- SCHEDULED / PILOT_REPORT / SENSOR_ALERT / INSPECTION_FINDING / GROUND_CREW
- Story: "What % of issues are caught proactively vs reactively?"

**Visual 12b: Finding Code Distribution** (Bar chart)
- For scheduled maintenance: NO_FINDING / WEAR_WITHIN_LIMITS / MINOR_DEFECT / REPLACEMENT_REQUIRED
- Shows inspection effectiveness — high NO_FINDING rate may mean over-inspection

---

## Key DAX Measures Reference

```dax
// === UTILIZATION MEASURES ===

Fleet Utilization Rate =
DIVIDE(
    SUM(fact_flight[flight_hours]),
    DISTINCTCOUNT(dim_aircraft[aircraft_id]) * 8 * DISTINCTCOUNT(dim_date[date])
)

Avg Leg Duration =
AVERAGE(fact_flight[flight_hours])

Revenue Flight Pct =
DIVIDE(
    CALCULATE(COUNTROWS(fact_flight),
        fact_flight[flight_purpose] IN {"Business","Leisure","Medical","Mixed"}),
    COUNTROWS(fact_flight)
)

YoY Flight Hours Growth =
VAR CurrentYear = SUM(fact_flight[flight_hours])
VAR PriorYear = CALCULATE(SUM(fact_flight[flight_hours]), SAMEPERIODLASTYEAR(dim_date[date]))
RETURN DIVIDE(CurrentYear - PriorYear, PriorYear)

// === MAINTENANCE MEASURES ===

Cost Per Flight Hour =
DIVIDE(
    SUM(fact_maintenance_detail[extended_cost]),
    SUM(fact_flight[flight_hours])
)

MTBF Hours =
DIVIDE(
    SUM(fact_flight[flight_hours]),
    CALCULATE(COUNTROWS(fact_maintenance_job), fact_maintenance_job[is_scheduled] = 0)
)

MTTR Hours =
AVERAGE(fact_maintenance_job[total_elapsed_hours])

Unscheduled Rate =
DIVIDE(
    CALCULATE(COUNTROWS(fact_maintenance_job), fact_maintenance_job[is_scheduled] = 0),
    COUNTROWS(fact_maintenance_job)
)

Parts Cost Pct =
DIVIDE(
    CALCULATE(SUM(fact_maintenance_detail[extended_cost]),
        fact_maintenance_detail[cost_category] = "PARTS"),
    SUM(fact_maintenance_detail[extended_cost])
)
```

---

## Narrative Strategy — What Each Dashboard "Says"

### Utilization Dashboard Story Arc
1. **Open with KPIs**: "47,600 flights, 162K flight hours across 62 aircraft"
2. **Seasonal pattern**: "Summer peak is 40% above February — do you staff for peak or average?"
3. **Heatmap reveals**: "3 aircraft flew <40 hrs in October — were they in maintenance or underutilized?"
4. **Deadhead insight**: "15% of flights carry zero passengers — that's 7,100 empty flights/year. Where's the repositioning waste?"
5. **PC-12 advantage**: "PC-12 accesses 2 airports PC-24 cannot — that's your competitive moat with short-strip capability"
6. **Close with question**: "With your actual data, we could show utilization by owner, by share type, by contract tier — and predict demand 30 days out"

### Maintenance Dashboard Story Arc
1. **Open with headline**: "$6.4M total maintenance, $39/flight hour cost"
2. **Scheduled dominance**: "91% of maintenance is scheduled — that's a sign of a mature maintenance program"
3. **SDRS validation**: "We cross-referenced FAA Service Difficulty Reports — your top failure systems match real PC-12 patterns: flight controls, engine, brakes"
4. **Cost drivers**: "Landing gear and engine systems drive 45% of parts cost"
5. **Facility comparison**: "Portsmouth handles 70% of work orders — is Boulder City underutilized or is that by design?"
6. **Close with vision**: "With real data, we'd add predictive maintenance alerts — 'N105AF brake assembly at 87% wear, schedule replacement in next 200 flight hours'"

---

## Files Generated in output/analytics/data/

| File | Rows | Description | Power BI Role |
|------|------|-------------|---------------|
| dim_date.csv | 1,096 | 2023-01-01 to 2025-12-31 | Time intelligence dimension |
| dim_aircraft.csv | 62 | 46 PC-12 + 16 PC-24 | Central dimension |
| dim_airport.csv | 34 | NE + SE + West + Midwest airports | Geography dimension |
| dim_component.csv | 20 | JASC-based, SDRS-calibrated | Maintenance dimension |
| dim_crew.csv | 120 | 80 pilots + 40 technicians | People dimension |
| dim_facility.csv | 2 | Portsmouth + Boulder City | Facility dimension |
| dim_owner.csv | 350 | Fractional owners | Owner dimension |
| fact_flight.csv | 142,841 | Every flight leg over 3 years | Core utilization fact |
| fact_booking.csv | 123,560 | Bookings including ~5% cancellations | Demand fact |
| fact_maintenance_job.csv | 2,589 | Work orders (scheduled + unscheduled) | Maintenance header fact |
| fact_maintenance_detail.csv | 6,893 | Line items (labor, parts, fuel, cert) | Maintenance cost fact |
| fact_aircraft_daily_status.csv | 63,080 | Per-aircraft-per-day status | Bridge: utilization ↔ maintenance |

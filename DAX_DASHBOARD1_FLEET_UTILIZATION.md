# Dashboard 1 — Fleet Utilization Overview: DAX & Build Guide

> **Scope**: This file covers Dashboard 1 only — Fleet Utilization Overview (Page 1).
> **Data Source**: `output/analytics/data/` — 12 CSV files loaded as tables in Power BI
> **Last Updated**: 2026-03-03
> **Status**: Slicers ✅ | KPI Cards ✅ | Visualizations ✅ (all 5)
>
> **Dashboard 2 — Maintenance Overview** is documented in a separate file.
> → Refer to **`DAX_DASHBOARD2_MAINTENANCE.md`** for all Dashboard 2 slicers, KPI cards, and visuals.

---

## How to Read This Document

Each entry follows this structure:
- **What it is** — plain English description
- **Where the data comes from** — exact table and column
- **Power BI setup** — step-by-step instructions
- **DAX** — the exact query to paste into Power BI
- **Why this DAX** — simple explanation of what each line does
- **Expected result** — what you should see when it works

---

## Table of Contents

1. [Power BI Setup — Before You Write Any DAX](#1-power-bi-setup--before-you-write-any-dax)
2. [Dashboard 1 — Fleet Utilization Overview](#2-dashboard-1--fleet-utilization-overview)
   - [Slicers](#slicers)
   - [KPI Cards](#kpi-cards)
   - [Prerequisite Steps Before Building Visuals](#prerequisite-steps-before-building-visuals)
   - [Visual 2a — Monthly Flight Hours Trend](#visual-2a--monthly-flight-hours-trend)
   - [Visual 2b — Aircraft Utilization Heatmap](#visual-2b--aircraft-utilization-heatmap)
   - [Visual 3a — Top 15 Routes by Frequency](#visual-3a--top-15-routes-by-frequency)
   - [Visual 3b — Fleet Status Over Time](#visual-3b--fleet-status-over-time)
   - [Visual 3c — Regional Utilization Map](#visual-3c--regional-utilization-map)
3. [Dashboard 2 — Reference](#3-dashboard-2--reference)
4. [Shared / Reusable Measures](#4-shared--reusable-measures)

---

## 1. Power BI Setup — Before You Write Any DAX

### 1.1 Table Names in Power BI

When you import the CSVs, Power BI will name tables after the file names. Use these **exact table names** in all DAX — rename them in Power BI if they come in differently:

| CSV File | Power BI Table Name |
|----------|---------------------|
| `fact_flight.csv` | `fact_flight` |
| `fact_aircraft_daily_status.csv` | `fact_aircraft_daily_status` |
| `fact_booking.csv` | `fact_booking` |
| `fact_maintenance_job.csv` | `fact_maintenance_job` |
| `fact_maintenance_detail.csv` | `fact_maintenance_detail` |
| `dim_aircraft.csv` | `dim_aircraft` |
| `dim_airport.csv` | `dim_airport` |
| `dim_date.csv` | `dim_date` |
| `dim_facility.csv` | `dim_facility` |
| `dim_crew.csv` | `dim_crew` |
| `dim_owner.csv` | `dim_owner` |
| `dim_component.csv` | `dim_component` |

---

### 1.2 Relationships to Define in Power BI Model View

These relationships must exist before any DAX will filter correctly. Go to **Model View → Manage Relationships** and create:

| From Table (Many side) | Column | To Table (One side) | Column | Cardinality |
|------------------------|--------|---------------------|--------|-------------|
| `fact_flight` | `date` | `dim_date` | `date` | Many-to-One |
| `fact_flight` | `aircraft_id` | `dim_aircraft` | `aircraft_id` | Many-to-One |
| `fact_flight` | `origin_icao` | `dim_airport` | `airport_icao` | Many-to-One |
| `fact_flight` | `pilot_id` | `dim_crew` | `crew_id` | Many-to-One |
| `fact_flight` | `owner_id` | `dim_owner` | `owner_id` | Many-to-One |
| `fact_aircraft_daily_status` | `date` | `dim_date` | `date` | Many-to-One |
| `fact_aircraft_daily_status` | `aircraft_id` | `dim_aircraft` | `aircraft_id` | Many-to-One |
| `fact_booking` | `departure_date` | `dim_date` | `date` | Many-to-One |
| `fact_booking` | `owner_id` | `dim_owner` | `owner_id` | Many-to-One |
| `fact_maintenance_job` | `date` | `dim_date` | `date` | Many-to-One |
| `fact_maintenance_job` | `aircraft_id` | `dim_aircraft` | `aircraft_id` | Many-to-One |
| `fact_maintenance_job` | `facility_id` | `dim_facility` | `facility_id` | Many-to-One |
| `fact_maintenance_detail` | `aircraft_id` | `dim_aircraft` | `aircraft_id` | Many-to-One |
| `fact_maintenance_detail` | `facility_id` | `dim_facility` | `facility_id` | Many-to-One |
| `dim_aircraft` | `base_facility_id` | `dim_facility` | `facility_id` | Many-to-One |

> **Note on `dim_date` as the central date table**: Mark `dim_date` as the **Date Table** in Power BI
> (right-click table → Mark as date table → select `date` column).
> This enables Power BI's built-in time intelligence (YoY, MTD, etc.).

---

### 1.3 Where to Write DAX Measures

All measures go into a dedicated measures table:
1. **Home → Enter Data** → name it `_Measures` → Load
2. Right-click `_Measures` table → **New Measure**
3. Paste each DAX block below

Keeping all measures in `_Measures` keeps the model clean and makes them easy to find.

---

## 2. Dashboard 1 — Fleet Utilization Overview

---

## Slicers

Slicers are not DAX — they are visual elements in Power BI that use raw columns from dimension tables. Here is the exact setup for each one.

---

### Slicer 1 — Date Range

**What it does**: Lets the user pick a start and end date. Every visual on the page filters to only show data within that window.

**Setup**:
1. Add a **Slicer** visual to the canvas
2. Drag `dim_date[date]` into the **Field** well
3. In the **Format pane → Slicer settings → Options → Style** → select **Between**
4. This gives you a From/To date picker

**Why `dim_date[date]` and not `fact_flight[date]`?**
Because `dim_date` is the central date table with the relationship to all fact tables. When you filter `dim_date[date]`, Power BI automatically propagates that filter through every connected fact table (flights, bookings, maintenance, daily status) in one go. If you used `fact_flight[date]` directly, only the flight table would filter — the other tables would not respond.

**Expected result**: Two calendar pickers showing 2023-01-01 (earliest) to 2025-12-31 (latest).

---

### Slicer 2 — Year

**What it does**: Lets the user quickly jump to a full year — 2023, 2024, or 2025.

**Setup**:
1. Add a **Slicer** visual
2. Drag `dim_date[year]` into the **Field** well
3. Format pane → Style → **Dropdown** (keeps the page clean vs. showing 3 large buttons)

**Why year from `dim_date` and not a separate column?**
Same reason as above — `dim_date` is already connected to all fact tables. One filter, everything responds. The `year` column is already in `dim_date` so no DAX needed.

**Expected result**: Dropdown with options 2023, 2024, 2025.

---

### Slicer 3 — Aircraft Model

**What it does**: Filters the entire page to show data for PC-12 NGX only, PC-24 only, or both.

**Setup**:
1. Add a **Slicer** visual
2. Drag `dim_aircraft[model]` into the **Field** well
3. Format pane → Style → **Tile** (shows as buttons: PC-12 NGX | PC-24)
4. Enable **Multi-select with Ctrl** → OFF (single-select is cleaner for model)

**Why from `dim_aircraft` and not `fact_flight[model]`?**
`dim_aircraft` is the authoritative source for model information. `fact_flight` also has a `model` column (denormalized for convenience) but using the dimension ensures the filter correctly flows to all fact tables — including `fact_aircraft_daily_status` and maintenance tables that join through `aircraft_id`, not through a `model` column.

**Expected result**: Two tile buttons — **PC-12 NGX** and **PC-24**.

---

### Slicer 4 — Base Facility

**What it does**: Filters everything to either the Portsmouth NH (Pease) facility or Boulder City NV facility.

**Setup**:
1. Add a **Slicer** visual
2. Drag `dim_facility[facility_name]` into the **Field** well
3. Format pane → Style → **Tile**

**Why `facility_name` and not `facility_id`?**
`facility_id` shows codes like FAC-PSM which mean nothing to a CIO. `facility_name` shows "Portsmouth NH (Pease)" — readable and self-explanatory.

**How this filter travels to flight data**:
`dim_facility` → `dim_aircraft[base_facility_id]` → `fact_flight[aircraft_id]`
The aircraft registered at a facility drives which flights appear. This is correct — you're asking "show me flights from aircraft based at Portsmouth."

**Expected result**: Two tile buttons — **Portsmouth NH (Pease)** and **Boulder City NV**.

---

### Slicer 5 — Flight Purpose

**What it does**: Lets the user pick which type of flight to include. Useful for isolating revenue flights from repositioning/ferry flights.

**Setup**:
1. Add a **Slicer** visual
2. Drag `fact_flight[flight_purpose]` into the **Field** well
3. Format pane → Style → **List** with checkboxes (multi-select is useful here)
4. Enable **Select All** option

**Distinct values in the data**:
| Value | Count | Meaning |
|-------|-------|---------|
| Business | 64,882 | Revenue — owner flying for work |
| Leisure | 33,018 | Revenue — owner personal travel |
| Medical | 5,779 | Revenue — medical transport |
| Mixed | 13,998 | Revenue — combination purpose |
| Repositioning | 20,811 | Non-revenue — moving aircraft between locations |
| Maintenance Ferry | 4,353 | Non-revenue — flying to/from maintenance |

**Why this is important**: When the CIO asks "what's our real revenue utilization?", they can uncheck Repositioning and Maintenance Ferry to see only owner-serving flights.

**Expected result**: Checklist with all 6 values. Default = all selected.

---

## KPI Cards

All 6 KPI cards require DAX measures. Create each one in the `_Measures` table as described in Section 1.3.

To display as a Card visual:
1. Add a **Card** visual to the canvas
2. Drag the measure into the **Fields** well
3. Format pane → **Callout value** → set font size (36–48 is good for CIO dashboards)
4. Add a **Title** in the Format pane with the KPI name

---

### KPI Card 1 — Total Flight Hours

**What it shows**: The sum of all flight hours flown across the filtered period, model, facility, and purpose. This is the single most fundamental utilization number.

**DAX**:
```dax
Total Flight Hours =
SUM ( fact_flight[flight_hours] )
```

**Why this DAX**:
`SUM` adds up every value in the `flight_hours` column. Because of the relationships set up in Section 1.2, this automatically respects all active slicer filters — if you select only PC-12 NGX, it sums only PC-12 flight hours; if you pick 2024 only, it sums only 2024 hours. You don't need to write `WHERE` conditions — the relationship model handles it.

**Format string**: `#,##0` (shows as 162,450 not 162450.23)

**How to set format**: Measure properties → Format → Custom → paste `#,##0`

**Expected result**: ~162,000 hours across the full 3-year dataset.

---

### KPI Card 2 — Total Flights

**What it shows**: The count of individual flight legs flown. Paired with Total Flight Hours, this gives the average leg duration indirectly.

**DAX**:
```dax
Total Flights =
COUNTROWS ( fact_flight )
```

**Why this DAX**:
`COUNTROWS` counts every row in the `fact_flight` table that passes through the current filter context. One row = one flight leg. No column needed — you're counting the rows themselves, not summing a value. This is more reliable than `COUNT(fact_flight[flight_id])` because COUNT skips blank values; COUNTROWS never does.

**Format string**: `#,##0`

**Benchmark**: ~47,800 per year (verified against PlaneSense published figures). Over 3 years expect ~142,800 total.

**Expected result**: 142,841

---

### KPI Card 3 — Average Hours per Aircraft per Day

**What it shows**: On average, how many hours is each aircraft flying per day? This is the core efficiency metric — it tells you whether the fleet is being worked hard or sitting idle.

**DAX**:
```dax
Avg Hours per Aircraft per Day =
DIVIDE (
    SUM ( fact_flight[flight_hours] ),
    COUNTROWS ( fact_aircraft_daily_status ),
    0
)
```

**Why this DAX**:
- `SUM(fact_flight[flight_hours])` — total hours flown in the current filter window
- `COUNTROWS(fact_aircraft_daily_status)` — counts the actual "aircraft-days" available in the fleet. This table tracks exactly which aircraft existed on which day.
- **Critical logic note**: We use `fact_aircraft_daily_status` for the denominator instead of `DISTINCTCOUNT(date) * DISTINCTCOUNT(aircraft)` because the fleet size changes over time (new deliveries). The daily status table accurately reflects the exact number of aircraft in the fleet on any given day.
- `DIVIDE(numerator, denominator, 0)` — safe division.

**Format string**: `0.0` (one decimal place — e.g., 2.3 hrs/aircraft/day)

**Industry benchmark**: FAA GA Survey average for turboprop single-engine = 8.7 hrs/day. PlaneSense will likely show 2–3 hrs/day because fractional aircraft don't fly 8+ hours every day — that's a commercial airline metric. The story here is trend, not absolute value.

> **Important**: This measure uses `dim_aircraft[aircraft_id]` not `fact_flight[aircraft_id]`. If a slicer filters to PC-12 only, `dim_aircraft` will only show PC-12 aircraft_ids, so the denominator correctly uses only PC-12 count.

**Expected result**: ~2.3 hrs/aircraft/day across the full dataset.

---

### KPI Card 4 — Fleet Availability %

**What it shows**: What percentage of aircraft-days were the aircraft available to fly (either actively flying or sitting ready)? The inverse is downtime. This is the most important operational health metric.

**DAX — Step 1: Create a supporting measure first**:
```dax
Available Aircraft Days =
CALCULATE (
    COUNTROWS ( fact_aircraft_daily_status ),
    fact_aircraft_daily_status[status] IN { "FLYING", "AVAILABLE" }
)
```

**Why**: We first count only the rows where the aircraft was FLYING or AVAILABLE. The `IN {}` syntax is a clean way to check membership against a list of values — equivalent to `status = "FLYING" OR status = "AVAILABLE"` but more readable. `CALCULATE` applies this condition as a filter on top of whatever slicers are already active.

**DAX — Step 2: The KPI measure**:
```dax
Fleet Availability % =
DIVIDE (
    [Available Aircraft Days],
    COUNTROWS ( fact_aircraft_daily_status ),
    0
)
```

**Why**: We divide available days by total aircraft-days. `COUNTROWS(fact_aircraft_daily_status)` gives the total rows after all slicer filters apply. The result is a proportion (0.928 = 92.8%).

**Format string**: `0.0%` — Power BI will multiply by 100 automatically when the format is `%`

**Benchmark**: Target >90%. Our data shows 92.8% — above target. ✅

**Display tip**: In the Card visual, add a subtitle "Target: >90%" using the Format pane → Additional header text.

**Expected result**: 92.8%

---

### KPI Card 5 — Deadhead Ratio

**What it shows**: What percentage of flights carried zero passengers (empty legs)? This includes repositioning flights and maintenance ferry flights. A high deadhead ratio means the fleet is burning fuel and hours without serving owners — it's the single most actionable inefficiency metric.

**DAX — Step 1: Supporting measure**:
```dax
Deadhead Flights =
CALCULATE (
    COUNTROWS ( fact_flight ),
    fact_flight[is_deadhead] = 1
)
```

**Why**: `is_deadhead` is a 0/1 flag already in the data. We filter to only rows where this equals 1 and count them.

**DAX — Step 2: The KPI measure**:
```dax
Deadhead Ratio =
DIVIDE (
    [Deadhead Flights],
    [Total Flights],
    0
)
```

**Why**: We reuse the `Total Flights` measure from KPI Card 2. This is why building base measures first is important — they compose cleanly. Deadhead Flights ÷ Total Flights = percentage of empty legs.

**Format string**: `0.0%`

**Benchmark**: Industry norm = 10–20% for fractional operators. Our data shows 15% (21,446 out of 142,841 flights).

**Breakdown of what drives deadhead** (useful for tooltip or annotation):
| Deadhead type | Count |
|---------------|-------|
| Repositioning | 20,811 |
| Maintenance Ferry | 635 |

**Expected result**: ~15.0%

---

### KPI Card 6 — Total Passengers

**What it shows**: Total number of passengers carried across all flights in the selected period. Paired with Total Flights, this gives average load per flight. Useful for showing the human scale of the operation.

**DAX**:
```dax
Total Passengers =
SUM ( fact_flight[passenger_count] )
```

**Why this DAX**: Straightforward sum. `passenger_count` has zero nulls in the data so no null handling is needed. Because of the relationship model, this automatically filters by model, facility, date, and flight purpose slicers.

**Format string**: `#,##0`

**Bonus measure — Average Passengers per Flight** (optional, useful for tooltips):
```dax
Avg Passengers per Flight =
DIVIDE (
    SUM ( fact_flight[passenger_count] ),
    COUNTROWS ( fact_flight ),
    0
)
```

**Why**: This tells you on average how full the aircraft are on revenue flights. If you add the Flight Purpose slicer and select only Business + Leisure + Medical + Mixed, this gives meaningful load factor context.

**Format string**: `0.0`

**Expected result**: Total Passengers ~490,000+ across 3 years. Avg ~3.4 passengers per flight (will be lower because deadhead flights have 0 passengers pulling the average down).

---

---

## Dashboard 1 — Visualizations

---

### Prerequisite Steps Before Building Visuals

Two one-time setup tasks must be completed in Power BI before any of the 4 visuals below will work correctly. Do these first.

---

#### Step A — Fix Month Sort Order in `dim_date`

**Why this matters**: Power BI sorts text columns alphabetically by default. Without this fix, `month_name` will display as April, August, December... instead of January, February, March...

**One-time fix in Power BI**:
1. Go to **Data View** → click the `dim_date` table
2. Click the `month_name` column header to select it
3. In the top ribbon → **Column Tools** → **Sort by Column** → select `month`
4. Done — `month_name` will now always sort as Jan → Dec

> This fix applies globally to all visuals that use `dim_date[month_name]`.

---

#### Step B — Create Calculated Column: `Month Year Label` in `dim_date`

**Why this matters**: Using just `month_name` on an X-axis will merge all Januaries across 2023, 2024, 2025 into a single "January" point. You need a "Jan 2023", "Feb 2023"... label for multi-year trend charts.

**DAX — Calculated Column** (go to Data View → dim_date table → New Column):
```dax
Month Year Label =
FORMAT ( dim_date[date], "MMM YYYY" )
```

**Why**: `FORMAT` converts a date to a string using the pattern you specify. "MMM YYYY" produces "Jan 2023", "Feb 2023" etc. This becomes the X-axis label for Visual 2a.

**Sort this column**: After creating it, with `Month Year Label` column selected → Column Tools → Sort by Column → select `month_year_sort_key` (create that next).

**DAX — Sort Key Column** (New Column in dim_date):
```dax
Month Year Sort Key =
dim_date[year] * 100 + dim_date[month]
```

**Why**: Multiplying year by 100 and adding month creates a numeric sort key: Jan 2023 = 202301, Feb 2023 = 202302, Jan 2024 = 202401. Numbers always sort correctly even when displayed as text labels.

Then: select `Month Year Label` → Column Tools → Sort by Column → `Month Year Sort Key`.

**Expected result**: 36 labels in the correct chronological order: Jan 2023, Feb 2023... Dec 2025.

---

#### Step C — Create Calculated Column: `Route` in `fact_flight`

**Why this matters**: Visual 3a needs a single "KPSM → KPWM" text value per row to use as a bar chart category. This doesn't exist in the raw data — we need to build it.

**DAX — Calculated Column** (Data View → fact_flight table → New Column):
```dax
Route =
fact_flight[origin_icao] & " → " & fact_flight[destination_icao]
```

**Why**: The `&` operator in DAX concatenates text. We join `origin_icao`, the literal arrow string, and `destination_icao` to produce the route label.

**Data note — filter out same-origin-destination flights**: The data contains 355 flights where `origin_icao = destination_icao` (test/circuit flights). These should be excluded from the route visual using a report-level filter (see Visual 3a setup for details).

**Expected result**: 142,841 rows with values like "KPSM → KPWM", "KPSM → KBDL" etc.

---

### New Measures for Visuals

Create these in the `_Measures` table before building the visuals.

---

#### Measure: Avg Leg Duration

**Used in**: Visual 2a tooltip

```dax
Avg Leg Duration =
AVERAGE ( fact_flight[flight_hours] )
```

**Why**: `AVERAGE` divides the sum of `flight_hours` by the count of rows. In a monthly chart context, it gives the average flight duration for that month. Shown in tooltip on the trend line.

**Format string**: `0.0 "hrs"`

**Expected result**: ~1.1 hrs for PC-12, ~1.5 hrs for PC-24

---

#### Measure: Avg Monthly Hours per Aircraft

**Used in**: Visual 2a Y-axis (for benchmark comparison)

```dax
Avg Monthly Hours per Aircraft =
DIVIDE (
    SUM ( fact_flight[flight_hours] ),
    DISTINCTCOUNT ( fact_flight[aircraft_id] ),
    0
)
```

**Why**: When this measure is placed on a monthly chart, Power BI evaluates it once per month. For each month:
- `SUM(flight_hours)` = total hours flown that month
- `DISTINCTCOUNT(fact_flight[aircraft_id])` = number of unique aircraft that flew that month (not the full fleet of 62 — only those with flights)
- The result is average hours per active aircraft per month

We use `fact_flight[aircraft_id]` (not `dim_aircraft[aircraft_id]`) because we want only aircraft that actually flew, giving an honest "active aircraft" average.

**Format string**: `0.0`

**Expected result**: ~75 hrs/month for PC-12, ~85 hrs/month for PC-24

> **Important narrative note**: The FAA benchmark is 267 hrs/month (~3,200 hrs/year) for commercial turboprop operators. PlaneSense averages ~75–85 hrs/month per aircraft because fractional aviation operates on owner demand, not scheduled commercial routes. The benchmark line is a comparison reference, NOT a performance target. Label it "FAA Commercial Turboprop Avg" in the visual to avoid misinterpretation.

---

#### Measures: Individual Fleet Status Counts

**Used in**: Visual 3b (stacked area chart) and tooltips

```dax
Aircraft FLYING =
CALCULATE (
    COUNTROWS ( fact_aircraft_daily_status ),
    fact_aircraft_daily_status[status] = "FLYING"
)
```

```dax
Aircraft AVAILABLE =
CALCULATE (
    COUNTROWS ( fact_aircraft_daily_status ),
    fact_aircraft_daily_status[status] = "AVAILABLE"
)
```

```dax
Aircraft IN_MAINTENANCE =
CALCULATE (
    COUNTROWS ( fact_aircraft_daily_status ),
    fact_aircraft_daily_status[status] = "IN_MAINTENANCE"
)
```

```dax
Aircraft AOG =
CALCULATE (
    COUNTROWS ( fact_aircraft_daily_status ),
    fact_aircraft_daily_status[status] = "AOG"
)
```

**Why four separate measures instead of one with a legend**: Power BI stacked area charts accept either (a) one measure + legend field, or (b) multiple measures stacked. Separate measures give you full control over the color assignment for each status — critical because AOG must always be red and FLYING must always be green regardless of sort order.

**Format string for all**: `#,##0`

---

### Visual 2a — Monthly Flight Hours Trend

**What it shows**: How total flight hours trend month by month across 3 years, split by aircraft model. Includes the FAA commercial benchmark as a reference line.

**Visual type**: Line Chart

**Data verified**: ✅ All columns available, no nulls. 36 months × 2 models = 72 data points.

---

#### Setup Steps

1. Add a **Line Chart** visual to the canvas

2. **Fields**:
   | Field well | Value |
   |------------|-------|
   | X axis | `dim_date[Month Year Label]` *(calculated column from Step B above)* |
   | Y axis | `[Avg Monthly Hours per Aircraft]` *(measure created above)* |
   | Legend | `dim_aircraft[model]` |
   | Tooltips | `[Total Flights]`, `[Avg Leg Duration]` |

3. **Sort the X axis**: Click the "..." on the visual → Sort axis → `Month Year Label` → Ascending. This uses the sort key you set in Step B.

4. **Add the FAA Benchmark line**:
   - Click the visual to select it
   - In the right panel → **Analytics pane** (magnifying glass icon)
   - Expand **Constant Line** → Add
   - Value: `267`
   - Color: Gray (#808080)
   - Style: Dashed
   - Label: ON → Type "FAA Commercial Turboprop Avg (267 hrs)"

   > Why 267? FAA GA Survey reports ~3,200 flight hours/year per commercial turboprop aircraft (3,200 ÷ 12 = 267/month). PlaneSense aircraft average ~75–85 hrs/month because this is fractional aviation on owner demand, not scheduled commercial service.

5. **Format the lines**:
   - PC-12 NGX line: Blue (#0070C0), stroke width 2.5px
   - PC-24 line: Orange (#E36C09), stroke width 2.5px

6. **Titles and labels**:
   - Title: "Monthly Flight Hours by Aircraft Model"
   - Y axis title: "Avg Flight Hours per Aircraft"
   - X axis: turn off title, keep labels

7. **Interaction with slicers**: This visual correctly responds to all 5 slicers. When a user selects "2024" in the Year slicer, only 12 data points show.

---

**Expected result**: Two lines — PC-12 NGX trending ~3,000–3,800 hrs/month total (fleet total), PC-24 trending ~800–1,200 hrs/month total, with a clear summer peak (Jun–Aug) and winter trough (Jan–Feb). Dashed gray benchmark line at 267.

---

### Visual 2b — Aircraft Utilization Heatmap

**What it shows**: A grid of every aircraft (rows) × every month (columns), colored by how many hours each aircraft flew. Instantly reveals which aircraft are underutilized, and which months are slow across the fleet.

**Visual type**: Matrix

**Data verified**: ✅ 62 aircraft × 36 months = 2,232 cells. Range: 15.7 to 123.2 hrs/month. Only 37 cells fall below 50 hrs (well-utilized fleet overall).

---

#### Setup Steps

1. Add a **Matrix** visual to the canvas

2. **Fields**:
   | Field well | Value |
   |------------|-------|
   | Rows | `dim_aircraft[tail_number]` |
   | Columns | `dim_date[year]` → then drag `dim_date[month_name]` under it (creates a hierarchy) |
   | Values | `[Total Flight Hours]` |

   > Why `year → month_name` hierarchy in columns? This keeps years as outer groupings (2023 | 2024 | 2025) with months underneath, so January 2023 and January 2024 are separate columns. If you only put `month_name`, all Januaries collapse into one column showing 3-year totals.

3. **Conditional Formatting — The color coding**:
   - Click the Values field in the matrix → **Conditional Formatting** → **Background color**
   - Select **Rules**
   - Add 3 rules:

   | Rule | Condition | Color |
   |------|-----------|-------|
   | Rule 1 | Value is less than `50` | Red `#FF0000` |
   | Rule 2 | Value is greater than or equal to `50` AND less than `80` | Yellow `#FFFF00` |
   | Rule 3 | Value is greater than or equal to `80` | Green `#00B050` |

   > **Threshold rationale**: With ~75 avg hrs/month and max 123 hrs/month:
   > - Red (<50): Only 37 of 2,232 cells — genuinely underperforming months
   > - Yellow (50–80): ~1,128 cells — normal operating range
   > - Green (>80): ~913 cells — high utilization months

4. **Sort rows**: Right-click any row → Sort → by `[Total Flight Hours]` descending. This puts the most-utilized aircraft at the top.

5. **Format**:
   - Turn off row/column totals unless specifically needed (Format pane → Row subtotals → OFF; Column subtotals → OFF). Totals add clutter to a heatmap.
   - Set cell font size to 8–9pt to fit all 62 aircraft on one page

6. **Slicer interaction note**: When the Aircraft Model slicer filters to "PC-12 NGX", only PC-12 tail numbers appear in the rows. When the Year slicer selects "2024", only 12 month columns show. Both work correctly.

---

**Expected result**: A 62-row × 36-column grid (or 62 × 12 when filtered to one year), mostly yellow and green, with occasional red cells visible in low-utilization months for specific aircraft.

---

### Visual 3a — Top 15 Routes by Frequency

**What it shows**: Which origin–destination pairs are flown most often, and how the traffic splits between PC-12 and PC-24 on each route. Useful for seeing whether PC-12 and PC-24 serve different or overlapping routes.

**Visual type**: Clustered Bar Chart (horizontal)

**Data verified**: ✅ All 15 top routes are served by BOTH models — the stacked bar will be meaningful. KPSM (Portsmouth) dominates as expected. 355 same-origin-destination flights must be excluded.

---

#### Setup Steps

1. Add a **Clustered Bar Chart** visual *(horizontal — Y axis has categories, X axis has values)*

2. **Fields**:
   | Field well | Value |
   |------------|-------|
   | Y axis | `fact_flight[Route]` *(calculated column from Step C above)* |
   | X axis | `[Total Flights]` |
   | Legend | `dim_aircraft[model]` |
   | Tooltips | `[Total Flight Hours]`, `[Avg Leg Duration]` |

3. **Exclude same-origin-destination routes** (the 355 data quality rows):
   - In the **Filters pane** on this visual → drag `fact_flight[origin_icao]`
   - Set filter: **does not equal** `fact_flight[destination_icao]`
   - **NOTE**: Power BI filters pane does not support cross-column comparisons directly. Use this workaround:
     - Create a calculated column in `fact_flight`: `Is Valid Route = IF ( fact_flight[origin_icao] = fact_flight[destination_icao], "Exclude", "Include" )`
     - Then in the visual's Filters pane → drag `Is Valid Route` → filter to show only **"Include"**

4. **TopN Filter — Show only Top 15 routes**:
   - In the **Filters pane** on this visual → drag `fact_flight[Route]`
   - Change filter type to **Top N**
   - Show: **Top** `15` By value: `[Total Flights]`

5. **Sort the bars**: Click "..." on the visual → Sort axis → `[Total Flights]` → Descending. Longest bar at top.

6. **Colors**:
   - PC-12 NGX: Blue (#0070C0)
   - PC-24: Orange (#E36C09)

7. **Data labels**: Format pane → Data labels → ON. Shows the flight count on each bar segment.

8. **Title**: "Top 15 Routes by Flight Frequency"

---

**Expected result**: 15 horizontal bars, each split into blue (PC-12) and orange (PC-24) segments. KPSM appears as origin or destination in nearly all top routes — visually confirming Portsmouth as the hub. Longest bar: KPSM → KPWM with 434 flights.

---

### Visual 3b — Fleet Status Over Time

**What it shows**: How many aircraft were flying, available, in maintenance, or grounded (AOG) each month across 3 years. Shows fleet expansion over time and lets you spot maintenance surges.

**Visual type**: Stacked Area Chart

**Data verified**: ✅ 1,096 days × up to 62 aircraft = 63,080 rows in `fact_aircraft_daily_status`. Fleet count grows from ~46 aircraft in early 2023 to 62 by end of dataset. Monthly aggregation is used — daily granularity (1,096 points) is too dense for a 3-year view.

---

#### Setup Steps

1. Add a **Stacked Area Chart** visual to the canvas

2. **Fields**:
   | Field well | Value |
   |------------|-------|
   | X axis | `dim_date[Month Year Label]` *(calculated column from Step B)* |
   | Y axis | Drag all 4 status measures: `[Aircraft FLYING]`, `[Aircraft AVAILABLE]`, `[Aircraft IN_MAINTENANCE]`, `[Aircraft AOG]` |
   | Legend | *(leave empty — the 4 measures become the legend automatically)* |

   > Why 4 separate measures instead of using `status` as a legend field? Using separate measures gives you precise control over the color assignment for each status. With a legend field, Power BI assigns colors based on sort order which may change. For AOG (which must always be visually distinct as red), separate measures are safer.

3. **Assign colors to each series** (Format pane → Lines → Colors):
   | Status | Color | Hex |
   |--------|-------|-----|
   | Aircraft FLYING | Green | #00B050 |
   | Aircraft AVAILABLE | Blue | #0070C0 |
   | Aircraft IN_MAINTENANCE | Amber | #ED7D31 |
   | Aircraft AOG | Red | #FF0000 |

4. **Sort the X axis**: Click "..." → Sort axis → `Month Year Label` → Ascending

5. **Y axis**: Format pane → Y axis → Title → "Number of Aircraft"

6. **Data labels**: OFF (too cluttered on a stacked area)

7. **Tooltip**: Enable — shows exact count per status on hover

8. **Title**: "Fleet Status Distribution Over Time"

9. **Slicer interaction notes**:
   - Date Range and Year slicers: ✅ Work correctly — filter the X axis
   - Aircraft Model slicer: ✅ Works — filters to only PC-12 or PC-24 aircraft in `dim_aircraft`, propagates to `fact_aircraft_daily_status` through the aircraft_id relationship
   - Base Facility slicer: ✅ Works — facility → aircraft → daily status
   - **Flight Purpose slicer**: Does NOT affect this visual (one-directional relationship design). This is intentional — fleet availability is a fleet-level metric independent of what type of flights are being flown.

---

**Expected result**: A stacked area chart with the green FLYING band dominant (~83–84% of the stack), blue AVAILABLE band as a thin secondary band, amber IN_MAINTENANCE as a thin periodic band, and a tiny red AOG band barely visible at the top. The total height of the stack grows from ~46 aircraft in early 2023 to ~62 by late 2024, showing fleet expansion visually.

---

---

### Visual 3c — Regional Utilization Map

**What it shows**: A bubble map of the United States with one bubble per airport. Bubble size shows how much departure traffic each airport generates. Bubble color shows whether the airport is accessible to both PC-12 and PC-24, or PC-12 only — directly illustrating the short-strip competitive advantage of the PC-12.

**Visual type**: Map (Power BI built-in bubble map using latitude/longitude)

**Data verified**: ✅ `dim_airport.csv` now has `latitude` and `longitude` for all 34 airports (added from public OurAirports dataset). Two airports are PC-12 exclusive: `2B2` (Plum Island, MA) and `K1B1` (Hudson, NY) — together receiving **8,788 flights** that no PC-24 operator could serve.

> **Data update note**: `latitude` and `longitude` columns were added to `dim_airport.csv` on 2026-03-03. If re-importing to Power BI, refresh the `dim_airport` table to pick up these new columns.

---

#### Prerequisite: Add One Calculated Column in `dim_airport`

The `pc24_accessible` column contains 0 or 1 integers. For a readable map legend, create a label column:

**DAX — Calculated Column** (Data View → `dim_airport` table → New Column):
```dax
Aircraft Access =
IF ( dim_airport[pc24_accessible] = 1, "PC-12 & PC-24", "PC-12 Only" )
```

**Why**: The map legend will show "PC-12 Only" and "PC-12 & PC-24" instead of "0" and "1". This makes the insight immediately readable for a CIO audience without needing a tooltip explanation.

**Expected values**:
| Value | Count | Airports |
|-------|-------|---------|
| PC-12 Only | 2 | 2B2 (Plum Island MA), K1B1 (Hudson NY) |
| PC-12 & PC-24 | 32 | All other airports |

---

#### New Measure: Airport Departure Count

**Used in**: Map bubble size

```dax
Airport Departures =
CALCULATE (
    COUNTROWS ( fact_flight ),
    USERELATIONSHIP ( fact_flight[origin_icao], dim_airport[airport_icao] )
)
```

**Why `USERELATIONSHIP`**: The relationship between `fact_flight` and `dim_airport` is on `origin_icao → airport_icao`. In the context of a map visual where each row is an airport from `dim_airport`, we explicitly activate this relationship so the measure counts only **departing** flights from each airport. Without this, Power BI may not know which relationship to use.

**Format string**: `#,##0`

**Expected result**: KPSM = 8,608 departures (highest — Portsmouth is the primary hub), followed by KHPN, KACK, KPWM, KMVY each with ~5,700–5,900.

---

#### New Measure: Airport Departure Hours

**Used in**: Map tooltip

```dax
Airport Departure Hours =
CALCULATE (
    SUM ( fact_flight[flight_hours] ),
    USERELATIONSHIP ( fact_flight[origin_icao], dim_airport[airport_icao] )
)
```

**Why**: Same logic as Airport Departures — explicitly uses the origin relationship. Gives total flight hours originating from each airport, useful for tooltip context.

**Format string**: `#,##0`

---

#### Setup Steps

1. Add a **Map** visual to the canvas
   > Use the standard built-in **Map** visual (globe icon in the Visualizations pane), NOT the Filled Map or ArcGIS Map

2. **Fields**:
   | Field well | Value |
   |------------|-------|
   | Latitude | `dim_airport[latitude]` |
   | Longitude | `dim_airport[longitude]` |
   | Size | `[Airport Departures]` |
   | Legend | `dim_airport[Aircraft Access]` *(calculated column created above)* |
   | Tooltips | `dim_airport[airport_name]`, `dim_airport[city]`, `dim_airport[state]`, `[Airport Departures]`, `[Airport Departure Hours]`, `dim_airport[runway_length_ft]` |

3. **Assign colors to the Legend**:
   - Format pane → Colors
   - **PC-12 Only**: Red (#FF0000) — makes the 2 exclusive airports immediately visible
   - **PC-12 & PC-24**: Blue (#0070C0)

4. **Bubble size scaling**: Format pane → Bubbles → Min size: 5, Max size: 30. This ensures even small airports (like 2B2 and K1B1 with fewer flights) are visible on the map while KPSM's dominance is clear.

5. **Map style**: Format pane → Map styles → Theme → **Road** (clean background, best for business presentations)

6. **Title**: "Airport Departure Activity & PC-12 Accessibility Advantage"

7. **Annotation** (text box next to the map):
   > Add a text box on the canvas: *"PC-12 serves 2 airports PC-24 cannot reach — 8,788 flights to short-strip destinations inaccessible to jets."*
   > This delivers the competitive narrative directly on the visual.

---

#### Slicer Interactions

| Slicer | Behavior |
|--------|----------|
| Date Range / Year | ✅ Filters departure counts to the selected period — bubbles resize dynamically |
| Aircraft Model | ✅ Filters to PC-12 or PC-24 flights only — useful to show: "Select PC-12 only → 2B2 and K1B1 bubbles appear. Select PC-24 only → they disappear." This is a powerful live demo moment. |
| Base Facility | ✅ Filters to aircraft based at Portsmouth or Boulder City |
| Flight Purpose | ✅ Filters by flight type (e.g., uncheck Repositioning to show only revenue departure activity) |

> **Demo tip**: During the CIO presentation, use the Aircraft Model slicer live — switch from "All" to "PC-24 only" and the 2B2 and K1B1 bubbles vanish from the map in real time. Then switch to "PC-12 NGX only" and they reappear. This single interaction tells the entire short-strip competitive story in 10 seconds without saying a word.

---

**Expected result**: A US map with ~32 blue bubbles clustered in the Northeast (Portsmouth hub dominance), 2 red bubbles in Massachusetts and New York (PC-12 exclusive airports), and smaller clusters in Florida, the West Coast, and the Midwest. KPSM bubble is visibly the largest.

---

## 3. Dashboard 2 — Reference

Dashboard 2 (Maintenance Intelligence Overview) is documented in its own dedicated file to keep each guide focused and easy to hand off independently.

**→ File**: `DAX_DASHBOARD2_MAINTENANCE.md`

That file will cover:
- All 6 slicers for the Maintenance Overview page
- All 7 KPI cards (Total Cost, Cost/Flight Hour, MTBF, MTTR, Downtime %, Scheduled Ratio, AOG Events)
- All 6 visuals (Cost Trend, Scheduled vs Unscheduled, Facility Workload, Top Components, Top Aircraft by Cost, JASC Treemap)
- Any additional calculated columns and measures specific to maintenance data

> **Note**: The Power BI model setup in Section 1 of this file (table names and relationships) applies to both dashboards — do not repeat it in the Dashboard 2 file. Reference this file for those steps.

---

## 4. Shared / Reusable Measures

These are base measures that multiple KPI cards and visuals reference. Build these first.

### Total Flight Hours
*(already defined above in KPI Card 1 — listed here for reference)*
```dax
Total Flight Hours =
SUM ( fact_flight[flight_hours] )
```

### Total Flights
*(already defined above in KPI Card 2)*
```dax
Total Flights =
COUNTROWS ( fact_flight )
```

### Available Aircraft Days
*(already defined above in KPI Card 4)*
```dax
Available Aircraft Days =
CALCULATE (
    COUNTROWS ( fact_aircraft_daily_status ),
    fact_aircraft_daily_status[status] IN { "FLYING", "AVAILABLE" }
)
```

### Deadhead Flights
*(already defined above in KPI Card 5)*
```dax
Deadhead Flights =
CALCULATE (
    COUNTROWS ( fact_flight ),
    fact_flight[is_deadhead] = 1
)
```

### FAA Benchmark Measures
*Hardcoded benchmarks from FAA GA Survey (2022) for comparison visuals*

```dax
Benchmark FAA Turboprop Hours = 267
```

```dax
Benchmark FAA Jet Hours = 300
```

### Avg Leg Duration
*(defined in Visual 2a section)*
```dax
Avg Leg Duration =
AVERAGE ( fact_flight[flight_hours] )
```

### Avg Monthly Hours per Aircraft
*(defined in Visual 2a section)*
```dax
Avg Monthly Hours per Aircraft =
DIVIDE (
    SUM ( fact_flight[flight_hours] ),
    DISTINCTCOUNT ( fact_flight[aircraft_id] ),
    0
)
```

### Aircraft FLYING / AVAILABLE / IN_MAINTENANCE / AOG
*(defined in Visual 3b section)*
```dax
Aircraft FLYING =
CALCULATE ( COUNTROWS ( fact_aircraft_daily_status ), fact_aircraft_daily_status[status] = "FLYING" )

Aircraft AVAILABLE =
CALCULATE ( COUNTROWS ( fact_aircraft_daily_status ), fact_aircraft_daily_status[status] = "AVAILABLE" )

Aircraft IN_MAINTENANCE =
CALCULATE ( COUNTROWS ( fact_aircraft_daily_status ), fact_aircraft_daily_status[status] = "IN_MAINTENANCE" )

Aircraft AOG =
CALCULATE ( COUNTROWS ( fact_aircraft_daily_status ), fact_aircraft_daily_status[status] = "AOG" )
```

### Airport Departures
*(defined in Visual 3c section)*
```dax
Airport Departures =
CALCULATE (
    COUNTROWS ( fact_flight ),
    USERELATIONSHIP ( fact_flight[origin_icao], dim_airport[airport_icao] )
)
```

### Airport Departure Hours
*(defined in Visual 3c section)*
```dax
Airport Departure Hours =
CALCULATE (
    SUM ( fact_flight[flight_hours] ),
    USERELATIONSHIP ( fact_flight[origin_icao], dim_airport[airport_icao] )
)
```

### Calculated Columns (not measures — go in Data View)

```dax
-- In dim_date table:
Month Year Label = FORMAT ( dim_date[date], "MMM YYYY" )
Month Year Sort Key = dim_date[year] * 100 + dim_date[month]

-- In fact_flight table:
Route = fact_flight[origin_icao] & " → " & fact_flight[destination_icao]
Is Valid Route = IF ( fact_flight[origin_icao] = fact_flight[destination_icao], "Exclude", "Include" )

-- In dim_airport table:
Aircraft Access = IF ( dim_airport[pc24_accessible] = 1, "PC-12 & PC-24", "PC-12 Only" )
```

---

## Appendix — Data Quick Reference

### Column Names Used in This Document

| Table | Column | Data Type | Notes |
|-------|--------|-----------|-------|
| `fact_flight` | `flight_hours` | Float | No nulls. 142,841 rows |
| `fact_flight` | `passenger_count` | Integer | No nulls |
| `fact_flight` | `is_deadhead` | Integer (0/1) | 21,446 rows = 1 |
| `fact_flight` | `flight_purpose` | String | 6 distinct values |
| `fact_flight` | `flight_status` | String | All rows = COMPLETED |
| `fact_flight` | `fuel_consumed_gal` | Float | No nulls |
| `fact_flight` | `distance_nm` | Float | No nulls |
| `fact_aircraft_daily_status` | `status` | String | FLYING / AVAILABLE / IN_MAINTENANCE / AOG |
| `dim_aircraft` | `aircraft_id` | String | 62 unique aircraft |
| `dim_aircraft` | `model` | String | PC-12 NGX (46) / PC-24 (16) |
| `dim_date` | `date` | Date | 2023-01-01 to 2025-12-31 |
| `dim_date` | `year` | Integer | 2023, 2024, 2025 |
| `dim_facility` | `facility_name` | String | Portsmouth NH / Boulder City NV |

### Known Data Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| All `flight_status` = COMPLETED | No cancelled/diverted flight rate | Use `fact_booking[booking_status]` for cancellation rate instead |
| All `job_status` = COMPLETED | Open Work Orders KPI = 0 always | Flag last 15 recent jobs as OPEN in data prep |
| `dim_airport` lat/lon | ✅ Resolved 2026-03-03 | `latitude` and `longitude` added to `dim_airport.csv` from OurAirports public dataset — map visual now fully buildable |
| `copilot_id` is 55% null | Limited co-pilot analysis | PC-12 is single-pilot certified — acceptable for most flights |
| 355 flights where origin = destination | Pollutes route analysis in Visual 3a | Use `Is Valid Route` calculated column filter to exclude these |
| FAA benchmark 267 hrs/mo vs our ~75–85 | May seem like underperformance | Label benchmark as "FAA Commercial Avg" — fractional model is a different operating context |
| Fleet count grows from 46 → 62 over 3 years | Daily status chart shows expanding total stack | This is a feature — shows fleet expansion over time |

---

*Document maintained by: Data / BI team*
*This file is complete for Dashboard 1. For Dashboard 2, refer to `DAX_DASHBOARD2_MAINTENANCE.md`.*

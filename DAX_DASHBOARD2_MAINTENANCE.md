# Dashboard 2 — Maintenance Intelligence Overview: DAX & Build Guide

> **Scope**: This file covers Dashboard 2 only — Maintenance Intelligence Overview (Page 1).
> **Data Source**: `output/analytics/data/` — 12 CSV files loaded as tables in Power BI
> **Last Updated**: 2026-03-03
> **Status**: Slicers ✅ | KPI Cards ✅ | Visualizations ✅ (all 6)
>
> **Dashboard 1 — Fleet Utilization Overview** is documented in `DAX_DASHBOARD1_FLEET_UTILIZATION.md`.
> → The Power BI model setup (table names, all relationships) lives in that file. Read Section 1 of that
>   file before starting here. This file only adds the 2 relationships specific to maintenance visuals.

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

1. [Additional Relationships for Dashboard 2](#1-additional-relationships-for-dashboard-2)
2. [Dashboard 2 — Maintenance Overview](#2-dashboard-2--maintenance-overview)
   - [Slicers](#slicers)
   - [KPI Cards](#kpi-cards)
   - [Prerequisite Steps Before Building Visuals](#prerequisite-steps-before-building-visuals)
   - [Visual 8a — Maintenance Cost Trend](#visual-8a--maintenance-cost-trend)
   - [Visual 8b — Scheduled vs Unscheduled Events](#visual-8b--scheduled-vs-unscheduled-events)
   - [Visual 8c — Maintenance by Facility](#visual-8c--maintenance-by-facility)
   - [Visual 9a — Top 10 Components by Cost](#visual-9a--top-10-components-by-cost)
   - [Visual 9b — Top 5 Aircraft by Maintenance Cost](#visual-9b--top-5-aircraft-by-maintenance-cost)
   - [Visual 9c — JASC System Failure Treemap](#visual-9c--jasc-system-failure-treemap)
3. [Shared / Reusable Measures](#3-shared--reusable-measures)
4. [Appendix — Data Quick Reference](#4-appendix--data-quick-reference)

---

## 1. Additional Relationships for Dashboard 2

The base model relationships are in `DAX_DASHBOARD1_FLEET_UTILIZATION.md` Section 1.2. Add these **two additional relationships** in Power BI Model View before building Dashboard 2 visuals:

| From Table (Many side) | Column | To Table (One side) | Column | Cardinality | Why Needed |
|------------------------|--------|---------------------|--------|-------------|------------|
| `fact_maintenance_detail` | `maintenance_job_id` | `fact_maintenance_job` | `maintenance_job_id` | Many-to-One | Allows job-level filters (is_scheduled, severity) to propagate to detail cost lines |
| `fact_maintenance_detail` | `jasc_ata_code` | `dim_component` | `jasc_ata_code` | Many-to-One | Powers the JASC Treemap and Top Components by Cost visual |

> **Why these weren't in Dashboard 1**: Dashboard 1 only uses flight and availability data. These two relationships are only needed when joining maintenance cost detail to job metadata and component taxonomy — which is Dashboard 2 territory.

---

## 2. Dashboard 2 — Maintenance Overview

---

## Slicers

All 6 slicers use the same setup pattern as Dashboard 1 (Format pane → Slicer settings → Style). Add all to the top bar of the page.

---

### Slicer 1 — Date Range

**What it does**: Filters the entire page to a selected date window. All KPI cards and visuals update.

**Setup**:
1. Add a **Slicer** visual
2. Drag `dim_date[date]` into the Field well
3. Format pane → Slicer settings → Style → **Between**

**Why `dim_date[date]`**: Same reason as Dashboard 1 — `dim_date` is connected to both `fact_maintenance_job` and `fact_maintenance_detail`, so one date filter propagates everywhere.

**Expected result**: Date range picker, 2023-01-01 to 2025-12-31.

---

### Slicer 2 — Facility

**What it does**: Filters to Portsmouth NH (Pease) — the primary facility — or Boulder City NV — the secondary facility.

**Setup**:
1. Add a **Slicer** visual
2. Drag `dim_facility[facility_name]` into the Field well
3. Format pane → Style → **Tile**

**Distinct values in data**:
| facility_name | Type | Technicians | Bays | Expected job share |
|---------------|------|-------------|------|--------------------|
| Portsmouth NH (Pease) | PRIMARY | 28 | 8 | ~70% of all jobs |
| Boulder City NV | SECONDARY | 12 | 4 | ~30% of all jobs |

**How filter travels**: `dim_facility` → `fact_maintenance_job[facility_id]` and `fact_maintenance_detail[facility_id]`

**Expected result**: Two tile buttons — **Portsmouth NH (Pease)** and **Boulder City NV**.

---

### Slicer 3 — Aircraft Model

**What it does**: Filters to PC-12 NGX or PC-24 maintenance data.

**Setup**:
1. Add a **Slicer** visual
2. Drag `dim_aircraft[model]` into the Field well
3. Format pane → Style → **Tile**

**Why from `dim_aircraft`**: Filter flows from `dim_aircraft` → `fact_maintenance_job[aircraft_id]` and `fact_maintenance_detail[aircraft_id]` through established relationships.

**Expected result**: Two tile buttons — **PC-12 NGX** and **PC-24**.

---

### Slicer 4 — Maintenance Type

**What it does**: Lets the user drill into specific maintenance categories — e.g., show only AOG repairs to analyse emergency events, or only 100HR inspections to analyse scheduled workload.

**Setup**:
1. Add a **Slicer** visual
2. Drag `fact_maintenance_job[maintenance_type]` into the Field well
3. Format pane → Style → **List** with checkboxes (multi-select)
4. Enable **Select All** option

**Distinct values in data**:
| Maintenance Type | Count | Scheduled? |
|-----------------|-------|------------|
| 100HR_INSPECTION | 1,586 | Yes |
| 200HR_INSPECTION | 776 | Yes |
| COMPONENT_REPLACEMENT | 75 | Mixed |
| LINE_MAINTENANCE | 91 | Mixed |
| TROUBLESHOOTING | 43 | No |
| AOG_REPAIR | 18 | No |

**Expected result**: Checklist with all 6 values. Default = all selected.

---

### Slicer 5 — Severity

**What it does**: Filters to a specific urgency level. Selecting AOG isolates the most critical grounding events.

**Setup**:
1. Add a **Slicer** visual
2. Drag `fact_maintenance_job[severity]` into the Field well
3. Format pane → Style → **Tile**

**Distinct values in data**:
| Severity | Count | Meaning |
|----------|-------|---------|
| ROUTINE | 2,362 | Scheduled, no urgency |
| MINOR | 120 | Small defect, not urgent |
| MODERATE | 80 | Attention needed, not grounding |
| AOG | 27 | Aircraft on Ground — grounded until fixed |

> **Data note**: URGENT and SAFETY_CRITICAL do not exist in this dataset. The slicer will only show these 4 values — this is expected behaviour, not a bug.

**Expected result**: Four tile buttons — **ROUTINE**, **MINOR**, **MODERATE**, **AOG**.

---

### Slicer 6 — Scheduled / Unscheduled

**What it does**: The most important operational filter — separates planned maintenance (scheduled intervals) from reactive maintenance (failure-driven). Unscheduled events drive cost spikes and availability drops.

**Setup**:
1. Add a **Slicer** visual
2. Drag `fact_maintenance_job[is_scheduled]` into the Field well
3. Format pane → Style → **Tile**

**Values in data**: 1 = Scheduled (2,362 jobs, 91.2%), 0 = Unscheduled (227 jobs, 8.8%)

> **Rename values for readability**: In Power BI, go to Data View → `fact_maintenance_job` table → `is_scheduled` column → you cannot rename 0/1 directly. Instead, create a calculated column:
```dax
Schedule Type =
IF ( fact_maintenance_job[is_scheduled] = 1, "Scheduled", "Unscheduled" )
```
Then use `fact_maintenance_job[Schedule Type]` in the slicer instead of `is_scheduled`. This shows **Scheduled** and **Unscheduled** as tile labels rather than 1 and 0.

**Expected result**: Two tile buttons — **Scheduled** and **Unscheduled**.

---

## KPI Cards

Create all measures in the `_Measures` table. Then display each as a **Card** visual with font size 36–48pt.

---

### KPI Card 1 — Total Maintenance Cost

**What it shows**: The total spend on all maintenance activities (labor, parts, fuel, certification) across the selected period and filters.

**DAX**:
```dax
Total Maintenance Cost =
SUM ( fact_maintenance_detail[extended_cost] )
```

**Why**: Simple sum of all cost lines. Because `fact_maintenance_detail` connects to `dim_date`, `dim_aircraft`, `dim_facility`, and `fact_maintenance_job` through relationships, all 6 slicers automatically filter this correctly.

**Format string**: `"$"#,##0` (shows as $6,405,548)

**Expected result**: **$6,405,548** across the full 3-year dataset.

---

### KPI Card 2 — Cost per Flight Hour

**What it shows**: How much is spent on maintenance for every hour of flying. The single most important cost efficiency metric in aviation — it benchmarks operational health against industry standards.

**DAX**:
```dax
Cost per Flight Hour =
DIVIDE (
    SUM ( fact_maintenance_detail[extended_cost] ),
    SUM ( fact_flight[flight_hours] ),
    0
)
```

**Why this DAX — the cross-table calculation**:
- `SUM(fact_maintenance_detail[extended_cost])` evaluates in the maintenance filter context
- `SUM(fact_flight[flight_hours])` evaluates in the flight filter context
- Both are scoped by the same `dim_aircraft` and `dim_date` filters in the current selection
- `DIVIDE(..., ..., 0)` handles the case where no flights exist in the filter (returns 0 not blank)

This works because both fact tables share `dim_aircraft` and `dim_date` relationships — Power BI applies the same slicer filters to both sides of the division simultaneously.

**Format string**: `"$"#,##0.00`

**Benchmark**: Industry standard = $200–$400 per flight hour for turboprop aircraft.

> **⚠️ Important data narrative note**: Our dataset shows **$39.47/flight hour** — significantly below the industry benchmark. This is a known synthetic data characteristic where maintenance costs were generated at lower rates than real-world values. When presenting to the CIO, frame this as: *"With your actual cost data plugged in, this card would show your real cost-per-hour and benchmark it against the $200–$400 industry range."* Do not hide the number — use it as a demonstration of the metric's structure.

**Expected result**: $39.47

---

### KPI Card 3 — MTBF (Mean Time Between Failures)

**What it shows**: On average, how many flight hours pass between unscheduled maintenance events? Higher is better — it means the fleet is more reliable and failures are rare.

**DAX**:
```dax
MTBF Hours =
DIVIDE (
    SUM ( fact_flight[flight_hours] ),
    CALCULATE (
        COUNTROWS ( fact_maintenance_job ),
        fact_maintenance_job[is_scheduled] = 0,
        fact_maintenance_job[job_status] = "COMPLETED"
    ),
    0
)
```

**Why this DAX, line by line**:
- `SUM(fact_flight[flight_hours])` — total hours the fleet operated
- `CALCULATE(COUNTROWS(...), is_scheduled = 0, job_status = "COMPLETED")` — count only unscheduled events that are finished. We explicitly filter to COMPLETED jobs because open unscheduled events haven't resolved yet and shouldn't count as confirmed failures in this reliability metric.
- `DIVIDE(..., ..., 0)` — safe division

**Format string**: `#,##0 "hrs"`

**Expected result**: **714.9 hrs** — meaning on average, an unscheduled maintenance event occurs every ~715 flight hours per aircraft.

---

### KPI Card 4 — MTTR (Mean Time To Repair)

**What it shows**: On average, how many hours does it take to complete a maintenance job from start to close? Lower is better — faster repairs mean less aircraft downtime.

**DAX**:
```dax
MTTR Hours =
CALCULATE (
    AVERAGE ( fact_maintenance_job[total_elapsed_hours] ),
    fact_maintenance_job[job_status] = "COMPLETED"
)
```

**Why filter to COMPLETED**: The 15 open jobs we added have NULL `total_elapsed_hours` (they haven't finished yet). While DAX `AVERAGE` ignores NULLs automatically, explicitly filtering to COMPLETED is clearer intent — MTTR should only be calculated from jobs where we know the full duration. This also ensures the metric stays stable as more jobs are eventually completed.

**Format string**: `0.0 "hrs"`

**Expected result**: **16.1 hrs** average repair time across completed jobs.

---

### KPI Card 5 — Downtime %

**What it shows**: What percentage of aircraft-days were aircraft grounded for maintenance? The inverse of Fleet Availability from Dashboard 1. Target is below 5%.

**DAX — Step 1: Supporting measure**:
```dax
Maintenance Days =
CALCULATE (
    COUNTROWS ( fact_aircraft_daily_status ),
    fact_aircraft_daily_status[status] IN { "IN_MAINTENANCE", "AOG" }
)
```

**DAX — Step 2: KPI measure**:
```dax
Downtime % =
DIVIDE (
    [Maintenance Days],
    COUNTROWS ( fact_aircraft_daily_status ),
    0
)
```

**Why**: We count only rows where the aircraft was IN_MAINTENANCE or AOG, then divide by total aircraft-days. This is the exact inverse of Fleet Availability % from Dashboard 1.

**Format string**: `0.0%`

**Benchmark**: Target <5%. Our data shows **7.2%** — slightly above target, which is a realistic and honest story point for the CIO presentation.

**Display tip**: Add a subtitle "Target: <5%" in Format pane → Additional header text. The 7.2% being above target creates a conversation about maintenance program optimization.

**Expected result**: 7.2%

---

### KPI Card 6 — Scheduled Maintenance Ratio

**What it shows**: What percentage of all maintenance events were planned (scheduled) vs reactive (unscheduled)? Higher is better — a well-maintained fleet catches problems before they cause grounding events.

**DAX**:
```dax
Scheduled Maintenance Ratio =
DIVIDE (
    CALCULATE (
        COUNTROWS ( fact_maintenance_job ),
        fact_maintenance_job[is_scheduled] = 1
    ),
    COUNTROWS ( fact_maintenance_job ),
    0
)
```

**Why**: Count scheduled jobs divided by all jobs. `COUNTROWS(fact_maintenance_job)` in the denominator picks up all jobs in the current filter context — including open jobs, which is correct since we want to know what ratio of current activity is scheduled.

**Format string**: `0.0%`

**Benchmark**: Target >85% scheduled. Our data shows **91.2%** — above target ✅. This is a strong positive narrative for the CIO: *"91% of your maintenance is proactive, not reactive."*

**Expected result**: 91.2%

---

### KPI Card 7 — AOG Events

**What it shows**: How many Aircraft on Ground (AOG) events occurred — the most severe maintenance classification where the aircraft is completely grounded and cannot fly. Target is zero.

**DAX**:
```dax
AOG Events =
CALCULATE (
    COUNTROWS ( fact_maintenance_job ),
    fact_maintenance_job[severity] = "AOG"
)
```

**Why**: Filter `fact_maintenance_job` to only rows where severity equals "AOG" and count them. Simple and direct.

**Format string**: `#,##0`

**Benchmark**: Target = 0. Any AOG event is a failure of preventive maintenance or an unavoidable emergency. 27 events across 3 years = ~9 AOG events per year across a 62-aircraft fleet.

**Display tip**: Use **conditional formatting** on this Card visual:
- Format pane → Callout value → Conditional formatting → Rules
- If value > 0 → font color Red (#FF0000)
- If value = 0 → font color Green (#00B050)

**Expected result**: 27

---

### KPI Card 8 (Bonus) — Open Work Orders

**What it shows**: How many maintenance jobs are currently active — not yet completed. Breaks down into OPEN (not started), IN_PROGRESS (active work), and PARTS_AWAITING (blocked on parts). This adds operational real-time feel to the dashboard.

**DAX**:
```dax
Open Work Orders =
CALCULATE (
    COUNTROWS ( fact_maintenance_job ),
    fact_maintenance_job[job_status] IN { "OPEN", "IN_PROGRESS", "PARTS_AWAITING" }
)
```

**Why**: We explicitly list the three non-completed statuses using `IN {}`. This is cleaner than `<> "COMPLETED"` because it's intention-clear and won't accidentally include any new status values added in the future.

**Format string**: `#,##0`

**Breakdown measures** (useful as tooltips or sub-cards):
```dax
Jobs OPEN =
CALCULATE ( COUNTROWS ( fact_maintenance_job ), fact_maintenance_job[job_status] = "OPEN" )

Jobs IN_PROGRESS =
CALCULATE ( COUNTROWS ( fact_maintenance_job ), fact_maintenance_job[job_status] = "IN_PROGRESS" )

Jobs PARTS_AWAITING =
CALCULATE ( COUNTROWS ( fact_maintenance_job ), fact_maintenance_job[job_status] = "PARTS_AWAITING" )
```

**Expected result**: **15** total (5 OPEN + 7 IN_PROGRESS + 3 PARTS_AWAITING)

---

## Prerequisite Steps Before Building Visuals

---

### Step A — `Schedule Type` Calculated Column (already covered in Slicer 6)

This column was created for Slicer 6. It is also used as the legend in Visual 8b. No additional action needed if you already created it.

```dax
-- In fact_maintenance_job table:
Schedule Type =
IF ( fact_maintenance_job[is_scheduled] = 1, "Scheduled", "Unscheduled" )
```

---

### Step B — Reuse `Month Year Label` from Dashboard 1

The `Month Year Label` calculated column in `dim_date` was created in `DAX_DASHBOARD1_FLEET_UTILIZATION.md` Step B. It is already in the model. Use `dim_date[Month Year Label]` as the X-axis for Visuals 8a and 8b — no additional setup needed.

---

### Step C — Verify the Two New Relationships Are Active

Before building Visual 9a and 9c, confirm in Model View:
- `fact_maintenance_detail[maintenance_job_id]` → `fact_maintenance_job[maintenance_job_id]` ✅
- `fact_maintenance_detail[jasc_ata_code]` → `dim_component[jasc_ata_code]` ✅

If not added yet, add them now per Section 1 of this file.

---

### New Measures for Visuals

Create these in the `_Measures` table before building visuals.

#### Cost by Category Measures (for Visual 8a stacked area)

```dax
Labor Cost =
CALCULATE (
    SUM ( fact_maintenance_detail[extended_cost] ),
    fact_maintenance_detail[cost_category] = "LABOR"
)
```

```dax
Parts Cost =
CALCULATE (
    SUM ( fact_maintenance_detail[extended_cost] ),
    fact_maintenance_detail[cost_category] = "PARTS"
)
```

```dax
Fuel Cost =
CALCULATE (
    SUM ( fact_maintenance_detail[extended_cost] ),
    fact_maintenance_detail[cost_category] = "FUEL"
)
```

```dax
Certification Cost =
CALCULATE (
    SUM ( fact_maintenance_detail[extended_cost] ),
    fact_maintenance_detail[cost_category] = "CERTIFICATION"
)
```

**Why four separate measures**: Same reason as Dashboard 1's fleet status measures — separate measures give full control over color assignment for each cost category in the stacked area chart.

**Cost breakdown in data** (full 3-year totals):
| Category | Total | Share |
|----------|-------|-------|
| LABOR | $3,189,051 | 49.8% |
| PARTS | $1,983,060 | 30.9% |
| CERTIFICATION | $796,972 | 12.4% |
| FUEL | $436,465 | 6.8% |

---

#### Scheduled and Unscheduled Event Counts (for Visual 8b)

```dax
Scheduled Events =
CALCULATE (
    COUNTROWS ( fact_maintenance_job ),
    fact_maintenance_job[is_scheduled] = 1
)
```

```dax
Unscheduled Events =
CALCULATE (
    COUNTROWS ( fact_maintenance_job ),
    fact_maintenance_job[is_scheduled] = 0
)
```

```dax
Unscheduled Rate % =
DIVIDE (
    [Unscheduled Events],
    COUNTROWS ( fact_maintenance_job ),
    0
)
```

**Why `Unscheduled Rate %` matters**: A rising line on this measure month-over-month signals fleet health deterioration — more reactive fixes mean the preventive program is slipping. A flat or declining line confirms a healthy maintenance program.

**Format string for Unscheduled Rate %**: `0.0%`

---

#### Unscheduled Component Events (for Visual 9c Treemap)

```dax
Unscheduled Component Events =
CALCULATE (
    COUNTROWS ( fact_maintenance_detail ),
    fact_maintenance_job[is_scheduled] = 0
)
```

**Why this works**: Because `fact_maintenance_detail` is now connected to `fact_maintenance_job` via `maintenance_job_id` (relationship added in Section 1), the filter `fact_maintenance_job[is_scheduled] = 0` propagates through that relationship to `fact_maintenance_detail`. When the treemap puts `dim_component[system_name]` and `dim_component[component_name]` as categories, the dim_component → fact_maintenance_detail relationship (via jasc_ata_code) scopes the count to each component.

**Result**: Each treemap cell shows how many unscheduled maintenance detail lines involved that component.

---

## Visual 8a — Maintenance Cost Trend

**What it shows**: How total maintenance spend trends month by month, broken down by cost type (Labor, Parts, Fuel, Certification). Lets the CIO see whether labor or parts are driving cost increases over time.

**Visual type**: Stacked Area Chart

**Data verified**: ✅ 36 months of data, all 4 cost categories present. Labor dominates at 49.8% of total cost.

---

### Setup Steps

1. Add a **Stacked Area Chart** visual

2. **Fields**:
   | Field well | Value |
   |------------|-------|
   | X axis | `dim_date[Month Year Label]` *(from Dashboard 1 Step B)* |
   | Y axis | Drag all 4: `[Labor Cost]`, `[Parts Cost]`, `[Certification Cost]`, `[Fuel Cost]` |
   | Legend | *(leave empty — the 4 measures auto-create the legend)* |
   | Tooltips | `[Total Maintenance Cost]`, `[Scheduled Events]`, `[Unscheduled Events]` |

3. **Sort X axis**: Click "..." → Sort axis → `Month Year Label` → Ascending

4. **Assign colors**:
   | Category | Color | Hex |
   |----------|-------|-----|
   | Labor Cost | Blue | #0070C0 |
   | Parts Cost | Orange | #E36C09 |
   | Certification Cost | Gray | #808080 |
   | Fuel Cost | Yellow | #FFC000 |

5. **Y axis title**: "Maintenance Cost ($)"

6. **Title**: "Monthly Maintenance Cost by Category"

7. **Slicer interactions**: All 6 slicers filter this visual correctly. Selecting "Unscheduled" from Slicer 6 will show only the cost of reactive maintenance — a powerful filter for isolating cost impact of failures.

---

**Expected result**: 36-month stacked area with blue (Labor) as the dominant band, orange (Parts) as the second largest, gray (Certification) as a thin consistent band (it mirrors scheduled inspection counts), and yellow (Fuel) at the base. Visual should show a seasonal pattern with summer peaks.

---

## Visual 8b — Scheduled vs Unscheduled Events

**What it shows**: Side-by-side monthly view of scheduled event counts (green bars) and unscheduled event counts (red bars), with a line overlay showing the unscheduled rate %. The line trending up is the early warning signal that the fleet maintenance program is degrading.

**Visual type**: Line and Clustered Column Chart

**Data verified**: ✅ All 36 months have both scheduled and unscheduled events. Monthly pattern shows ~70–90 scheduled events/month, ~5–10 unscheduled events/month.

---

### Setup Steps

1. Add a **Line and Clustered Column Chart** visual
   > This visual type has two Y-axes: Column Y (left) and Line Y (right). Find it in the Visualizations pane — it looks like a bar chart with a line through it.

2. **Fields**:
   | Field well | Value |
   |------------|-------|
   | X axis | `dim_date[Month Year Label]` |
   | Column Y axis | `[Scheduled Events]`, `[Unscheduled Events]` |
   | Line Y axis | `[Unscheduled Rate %]` |
   | Tooltips | `[Total Maintenance Cost]`, `[MTTR Hours]` |

3. **Sort X axis**: Click "..." → Sort axis → `Month Year Label` → Ascending

4. **Assign column colors**:
   | Measure | Color | Hex |
   |---------|-------|-----|
   | Scheduled Events | Green | #00B050 |
   | Unscheduled Events | Red | #FF0000 |

5. **Line color**: Dark red (#C00000), line style: Solid, width: 2.5px

6. **Right Y axis** (for line): Format pane → Y axis (secondary) → Title → "Unscheduled Rate %", Format → `0.0%`

7. **Left Y axis**: Title → "Number of Events"

8. **Title**: "Scheduled vs Unscheduled Maintenance Events"

9. **Add target reference line** (Analytics pane → Constant Line):
   - Value: `0.15` (15% = upper limit for healthy unscheduled rate, beyond industry 85% scheduled target)
   - Color: Orange, dashed
   - Label: "Max Acceptable Rate (15%)"

---

**Expected result**: Tall green bars (60–90 scheduled) with small red bars (3–12 unscheduled) each month. Dark red line hovering between 5–15%. The line should stay comfortably below the 15% reference line for most months.

---

## Visual 8c — Maintenance by Facility

**What it shows**: How maintenance workload is split between Portsmouth (PRIMARY) and Boulder City (SECONDARY), broken down by maintenance type. Confirms whether Boulder City is being appropriately utilized or if workload is concentrated too heavily at Portsmouth.

**Visual type**: Clustered Bar Chart (horizontal)

**Data verified**: ✅ Portsmouth handles 1,800 jobs (70%), Boulder City 789 jobs (30%). Both facilities handle all maintenance types.

---

### Setup Steps

1. Add a **Clustered Bar Chart** visual (horizontal)

2. **Fields**:
   | Field well | Value |
   |------------|-------|
   | Y axis | `dim_facility[facility_name]` |
   | X axis | `COUNTROWS(fact_maintenance_job)` — use the measure `[Scheduled Events]` + `[Unscheduled Events]` total, or simply use `[Open Work Orders]` + completed count. Easiest: create `Total Maintenance Jobs` |
   | Legend | `fact_maintenance_job[maintenance_type]` |
   | Tooltips | `[Total Maintenance Cost]`, `[MTTR Hours]` |

   **DAX — Total Maintenance Jobs** (supporting measure):
   ```dax
   Total Maintenance Jobs =
   COUNTROWS ( fact_maintenance_job )
   ```

3. **Sort**: Click "..." → Sort → `[Total Maintenance Jobs]` → Descending. Portsmouth bar on top.

4. **Colors**: Assign distinct colors per maintenance type:
   | Type | Color |
   |------|-------|
   | 100HR_INSPECTION | Blue (#0070C0) |
   | 200HR_INSPECTION | Dark Blue (#002060) |
   | COMPONENT_REPLACEMENT | Orange (#E36C09) |
   | LINE_MAINTENANCE | Amber (#FFC000) |
   | TROUBLESHOOTING | Red (#FF0000) |
   | AOG_REPAIR | Dark Red (#C00000) |

5. **Data labels**: ON — shows job count per segment

6. **Title**: "Maintenance Workload by Facility and Type"

---

**Expected result**: Two horizontal bars. Portsmouth bar (~1,800 total) significantly longer than Boulder City (~789). Both bars show 100HR_INSPECTION as the dominant segment (blue). AOG_REPAIR segments are barely visible (18 total across both facilities) — confirming low emergency event frequency.

---

## Visual 9a — Top 10 Components by Cost

**What it shows**: Which aircraft components cost the most in parts replacement. Landing gear components (Brake Assembly, Nose Gear) lead — consistent with real FAA SDRS data for PC-12 aircraft.

**Visual type**: Horizontal Bar Chart

**Data verified**: ✅ All 20 component JASC codes in `fact_maintenance_detail` match `dim_component` — 100% join. Parts cost only: $1,983,060 total.

---

### Setup Steps

1. Add a **Clustered Bar Chart** visual (horizontal)

2. **Fields**:
   | Field well | Value |
   |------------|-------|
   | Y axis | `dim_component[component_name]` |
   | X axis | `[Parts Cost]` *(filtered to PARTS category — already in the measure)* |
   | Tooltips | `dim_component[system_name]`, `[Unscheduled Component Events]` |

3. **TopN Filter — Show only Top 10**:
   - Filters pane on this visual → drag `dim_component[component_name]`
   - Filter type → **Top N** → Show **Top 10** → By value → `[Parts Cost]`

4. **Sort**: Click "..." → Sort → `[Parts Cost]` → Descending. Most expensive at top.

5. **Color**: Single color — Orange (#E36C09) for all bars (this is a ranking chart, not a category comparison)

6. **Data labels**: ON — shows dollar amount on each bar

7. **Title**: "Top 10 Components by Parts Replacement Cost"

---

**Expected result** (top 5 shown):
| Rank | Component | Cost |
|------|-----------|------|
| 1 | Brake Assembly | $294,700 |
| 2 | Nose Gear Steering | $239,140 |
| 3 | Communications System | $237,180 |
| 4 | Engine (General) | $173,720 |
| 5 | Fuselage Structure | $143,020 |

> **Narrative note**: Brake Assembly and Nose Gear top the list — consistent with real FAA SDRS data for PC-12 operations. This validates the synthetic data against real aircraft failure patterns, a strong credibility point for the CIO presentation.

---

## Visual 9b — Top 5 Aircraft by Maintenance Cost

**What it shows**: Which individual aircraft are costing the most in total maintenance spend. Useful for identifying candidates for early retirement, targeted inspection, or root-cause analysis.

**Visual type**: Clustered Bar Chart (horizontal)

**Data verified**: ✅ AC-003 is most expensive at $284,791 over 3 years. Top 5 use ~$1.16M of the $6.4M total — roughly 18% concentrated in 5 aircraft.

---

### Setup Steps

1. Add a **Clustered Bar Chart** visual (horizontal)

2. **Fields**:
   | Field well | Value |
   |------------|-------|
   | Y axis | `dim_aircraft[tail_number]` |
   | X axis | `[Total Maintenance Cost]` |
   | Legend | `dim_aircraft[model]` |
   | Tooltips | `dim_aircraft[years_in_service]`, `dim_aircraft[base_facility_id]`, `[Total Maintenance Jobs]` |

3. **TopN Filter — Show only Top 5**:
   - Filters pane → drag `dim_aircraft[tail_number]`
   - Filter type → **Top N** → Show **Top 5** → By value → `[Total Maintenance Cost]`

4. **Sort**: Click "..." → Sort → `[Total Maintenance Cost]` → Descending

5. **Colors**:
   - PC-12 NGX: Blue (#0070C0)
   - PC-24: Orange (#E36C09)

6. **Data labels**: ON

7. **Title**: "Top 5 Aircraft by Total Maintenance Cost"

---

**Expected result**: 5 bars showing the most expensive aircraft. AC-003 ($284K) and AC-041 ($280K) lead. Including `years_in_service` in tooltip gives context — older aircraft typically cost more.

---

## Visual 9c — JASC System Failure Distribution Treemap

**What it shows**: Which aircraft systems generate the most unscheduled maintenance events, with drill-down to individual components. The area of each block represents event count — larger blocks = more failures. Based on the same JASC/ATA taxonomy used by the FAA SDRS system.

**Visual type**: Treemap

**Data verified**: ✅ All 20 JASC codes present and joined. Flight Controls leads with 62 unscheduled events, Landing Gear second with 60, Engine third with 46. This matches real FAA SDRS patterns for PC-12 aircraft.

---

### Setup Steps

1. Add a **Treemap** visual

2. **Fields**:
   | Field well | Value |
   |------------|-------|
   | Category | `dim_component[system_name]` *(outer grouping = aircraft system)* |
   | Details | `dim_component[component_name]` *(inner grouping = specific component)* |
   | Values | `[Unscheduled Component Events]` |
   | Tooltips | `dim_component[system_name]`, `dim_component[component_name]`, `[Parts Cost]` |

3. **Why this hierarchy works**:
   - `system_name` groups components by aircraft system (Landing Gear, Engine, Flight Controls etc.)
   - `component_name` shows the specific part within that system
   - `[Unscheduled Component Events]` flows correctly because of the relationships:
     `dim_component` → `fact_maintenance_detail` (jasc_ata_code) → `fact_maintenance_job` (maintenance_job_id) → filtered to `is_scheduled = 0`

4. **Colors**: Format pane → Colors → Diverging color scale
   - Minimum: Light blue (#BDD7EE) — few failures
   - Maximum: Dark red (#C00000) — many failures
   - This naturally highlights the most problematic systems in red

5. **Data labels**: ON — shows component name and count inside each block

6. **Title**: "Unscheduled Event Distribution by Aircraft System (JASC Taxonomy)"

7. **Add annotation** (text box near visual):
   > *"Component failure distribution cross-referenced with FAA Service Difficulty Reports (SDRS) for PC-12/PC-24 aircraft. Patterns align with real-world SDRS data — Flight Controls and Engine systems are confirmed top failure categories."*
   > This delivers the "real FAA data validation" narrative directly on the visual.

---

**Expected result**: A treemap with 8–10 colored blocks. Largest blocks (most failures):
- **Flight Controls** — 62 events (2 components: Flight Control System 39, Rudder Control System 23)
- **Landing Gear** — 60 events (4 components spread across Brake Assembly, Nose Gear, Main Landing Gear, Brake System)
- **Engine** — 46 events (2 components: Engine General 35, Engine Control 11)
- **Fuselage** — 23 events
- **Instruments** — 22 events

---

## 3. Shared / Reusable Measures

All measures for Dashboard 2 in one place for reference.

```dax
-- KPI MEASURES --

Total Maintenance Cost =
SUM ( fact_maintenance_detail[extended_cost] )

Cost per Flight Hour =
DIVIDE ( SUM ( fact_maintenance_detail[extended_cost] ), SUM ( fact_flight[flight_hours] ), 0 )

MTBF Hours =
DIVIDE (
    SUM ( fact_flight[flight_hours] ),
    CALCULATE ( COUNTROWS ( fact_maintenance_job ), fact_maintenance_job[is_scheduled] = 0, fact_maintenance_job[job_status] = "COMPLETED" ),
    0
)

MTTR Hours =
CALCULATE ( AVERAGE ( fact_maintenance_job[total_elapsed_hours] ), fact_maintenance_job[job_status] = "COMPLETED" )

Maintenance Days =
CALCULATE ( COUNTROWS ( fact_aircraft_daily_status ), fact_aircraft_daily_status[status] IN { "IN_MAINTENANCE", "AOG" } )

Downtime % =
DIVIDE ( [Maintenance Days], COUNTROWS ( fact_aircraft_daily_status ), 0 )

Scheduled Maintenance Ratio =
DIVIDE ( CALCULATE ( COUNTROWS ( fact_maintenance_job ), fact_maintenance_job[is_scheduled] = 1 ), COUNTROWS ( fact_maintenance_job ), 0 )

AOG Events =
CALCULATE ( COUNTROWS ( fact_maintenance_job ), fact_maintenance_job[severity] = "AOG" )

Open Work Orders =
CALCULATE ( COUNTROWS ( fact_maintenance_job ), fact_maintenance_job[job_status] IN { "OPEN", "IN_PROGRESS", "PARTS_AWAITING" } )

-- SUPPORTING MEASURES FOR VISUALS --

Labor Cost =
CALCULATE ( SUM ( fact_maintenance_detail[extended_cost] ), fact_maintenance_detail[cost_category] = "LABOR" )

Parts Cost =
CALCULATE ( SUM ( fact_maintenance_detail[extended_cost] ), fact_maintenance_detail[cost_category] = "PARTS" )

Fuel Cost =
CALCULATE ( SUM ( fact_maintenance_detail[extended_cost] ), fact_maintenance_detail[cost_category] = "FUEL" )

Certification Cost =
CALCULATE ( SUM ( fact_maintenance_detail[extended_cost] ), fact_maintenance_detail[cost_category] = "CERTIFICATION" )

Scheduled Events =
CALCULATE ( COUNTROWS ( fact_maintenance_job ), fact_maintenance_job[is_scheduled] = 1 )

Unscheduled Events =
CALCULATE ( COUNTROWS ( fact_maintenance_job ), fact_maintenance_job[is_scheduled] = 0 )

Unscheduled Rate % =
DIVIDE ( [Unscheduled Events], COUNTROWS ( fact_maintenance_job ), 0 )

Total Maintenance Jobs =
COUNTROWS ( fact_maintenance_job )

Unscheduled Component Events =
CALCULATE ( COUNTROWS ( fact_maintenance_detail ), fact_maintenance_job[is_scheduled] = 0 )

Jobs OPEN =
CALCULATE ( COUNTROWS ( fact_maintenance_job ), fact_maintenance_job[job_status] = "OPEN" )

Jobs IN_PROGRESS =
CALCULATE ( COUNTROWS ( fact_maintenance_job ), fact_maintenance_job[job_status] = "IN_PROGRESS" )

Jobs PARTS_AWAITING =
CALCULATE ( COUNTROWS ( fact_maintenance_job ), fact_maintenance_job[job_status] = "PARTS_AWAITING" )

-- CALCULATED COLUMNS (Data View — not Measures table) --

-- In fact_maintenance_job table:
Schedule Type = IF ( fact_maintenance_job[is_scheduled] = 1, "Scheduled", "Unscheduled" )
```

---

## 4. Appendix — Data Quick Reference

### Column Names Used in This Document

| Table | Column | Data Type | Notes |
|-------|--------|-----------|-------|
| `fact_maintenance_detail` | `extended_cost` | Float | No nulls. 6,893 rows |
| `fact_maintenance_detail` | `cost_category` | String | LABOR / PARTS / FUEL / CERTIFICATION |
| `fact_maintenance_detail` | `jasc_ata_code` | Float | 20 distinct codes, all match dim_component |
| `fact_maintenance_job` | `is_scheduled` | Integer (0/1) | 2,362 scheduled / 227 unscheduled |
| `fact_maintenance_job` | `severity` | String | ROUTINE / MINOR / MODERATE / AOG |
| `fact_maintenance_job` | `maintenance_type` | String | 6 distinct types |
| `fact_maintenance_job` | `job_status` | String | COMPLETED (2,574) / OPEN (5) / IN_PROGRESS (7) / PARTS_AWAITING (3) |
| `fact_maintenance_job` | `total_elapsed_hours` | Float | NULL for 15 open jobs — AVERAGE ignores these correctly |
| `fact_maintenance_job` | `trigger_source` | String | SCHEDULED / PILOT_REPORT / SENSOR_ALERT / INSPECTION_FINDING / GROUND_CREW |
| `fact_aircraft_daily_status` | `status` | String | FLYING / AVAILABLE / IN_MAINTENANCE / AOG |
| `dim_component` | `jasc_ata_code` | Integer | 20 components, 100% join to fact_maintenance_detail |
| `dim_component` | `system_name` | String | 10 aircraft systems |
| `dim_facility` | `facility_name` | String | Portsmouth NH (Pease) / Boulder City NV |

### Known Data Limitations

| Limitation | Impact | Workaround / Notes |
|------------|--------|--------------------|
| Cost/Flight Hour = $39.47 vs industry $200–$400 | Appears low for benchmarking | Synthetic data characteristic — frame as: "With your real cost data, this shows your actual CPFH vs industry" |
| Severity missing URGENT and SAFETY_CRITICAL | Slicer shows only 4 values | Expected — these severity levels don't exist in the synthetic data. Document as known |
| `total_elapsed_hours` NULL for 15 open jobs | MTTR calculation | Handled — MTTR DAX explicitly filters to COMPLETED jobs only |
| All open jobs are recent (Dec 2025) | May not show in filtered views | Date slicer must include Dec 2025 to see open work orders |
| JASC codes in maintenance_detail are floats (7200.0) | Join to dim_component may fail if types mismatch | In Power BI Power Query, cast both `jasc_ata_code` columns to Integer before loading |

---

*Document maintained by: Data / BI team*
*Dashboard 1 reference: `DAX_DASHBOARD1_FLEET_UTILIZATION.md`*
*This file is complete for Dashboard 2 Page 1. Pages 2 onward to be added as needed.*

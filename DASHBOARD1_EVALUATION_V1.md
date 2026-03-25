# Dashboard 1 — Fleet Utilization: Evaluation Report

**Evaluation Date**: 2026-03-06
**Iteration**: V1 (Baseline)
**Current Build**: `output/analytics/Power BI outputs/Aircraft_utilization_dashboard.png`
**Reference Design**: `output/analytics/dashboard visualization ideas/Aircraft utilization - overview.png`
**Specification Source**: `DAX_DASHBOARD1_FLEET_UTILIZATION.md`

---

## Scoring Matrix

| Score | Label | Meaning |
|-------|-------|---------|
| 5 | ✅ Complete | Matches reference exactly — no action needed |
| 4 | 🟡 Minor Gap | Implemented but minor deviation (label, format, color) |
| 3 | 🟠 Partial | Feature exists but significant differences from spec |
| 2 | 🔴 Major Gap | Component present but incorrect or materially wrong |
| 1 | ⛔ Missing | Not implemented at all |

---

## Section 1 — Header / Title

| Item | Reference | Current | Score | Gap Description |
|------|-----------|---------|-------|----------------|
| Dashboard title | "AIRCRAFT UTILIZATION – Fleet Overview" | "PlaneSense - AVIATION UTILIZATION ANALYTICS" | 4 | Title is client-branded which is acceptable; format differs slightly from reference |
| Airplane icon/logo | ✅ Present top-left | ✅ Present | 5 | Matches |
| Power BI branding | Top-right corner | Not visible (cropped) | — | N/A |

**Section Score: 4.5 / 5**

---

## Section 2 — Slicers

| Slicer | Reference Spec | Current Status | Score | Gap |
|--------|---------------|----------------|-------|-----|
| **Date Range** (From/To picker) | `dim_date[date]`, Between style, full range 2023–2025 | ✅ Present, showing 1/1/2025–12/31/2025 | 4 | Showing only 2025 — default should be full range 2023-01-01 to 2025-12-31 |
| **Year** (dropdown) | `dim_date[year]`, Dropdown style | ⛔ Not visible in current build | 1 | Missing — was partially visible in earlier screenshot but not in current |
| **Aircraft Model** (tile buttons) | `dim_aircraft[model]`, Tile style, PC-12 NGX \| PC-24 \| All | 🟠 Present but unclear tile formatting | 3 | Currently visible but All/PC-12/PC-24 split unclear; reference shows 3 clear tile buttons |
| **Base Facility** (dropdown) | `dim_facility[facility_name]`, Tile style | ⛔ Not visible | 1 | Missing entirely from current layout |
| **Flight Purpose** (multi-select list) | `fact_flight[flight_purpose]`, Checklist | 🟡 Present as "Travel Purpose" dropdown | 4 | Label says "Travel Purpose" instead of "Flight Purpose"; should be list/checklist not dropdown |
| **Tail Number** (extra slicer) | Not in reference design | ✅ Present as dropdown | 3 | Extra slicer not in reference spec — may be useful but creates layout crowding |

**Section Score: 2.7 / 5**
**Priority gaps**: Year slicer missing, Base Facility slicer missing, Flight Purpose label incorrect, Date range default too narrow

---

## Section 3 — KPI Cards (Row 1)

| KPI Card | Reference | DAX Spec | Current Value | Score | Gap |
|----------|-----------|----------|---------------|-------|-----|
| **Total Flight Hours** | ✅ Required | `SUM(fact_flight[flight_hours])` | 38,814 ✅ | 5 | Correctly implemented; value is for 2025 only due to date filter |
| **Total Flights** | ✅ Required (card 2) | `COUNTROWS(fact_flight)` | ⛔ Replaced by "Total Miles Flown" (13.31M) | 1 | Reference card 2 = Total Flights; current shows Total Miles Flown instead. Miles card may be added but should not replace Total Flights |
| **Avg Hours per Aircraft per Day** | ✅ Required (card 3) | `DIVIDE(SUM flight_hours, COUNTROWS daily_status)` | 1.72 🟠 | 3 | Present but labelled "Daily Aircraft hours"; reference shows 4.26 — value difference likely because ref uses a different denominator. Check if dividing by flying days only vs all days |
| **Fleet Availability %** | ✅ Required (card 4) | `DIVIDE(Available Aircraft Days, total days)` | ⛔ Missing | 1 | Not present in current build — critical KPI for a CIO dashboard |
| **Deadhead Ratio %** | ✅ Required (card 5) | `DIVIDE(Deadhead Flights, Total Flights)` | 14.95% ✅ | 5 | Correctly implemented and labelled |
| **Total Passengers** | ✅ Required (card 6) | `SUM(fact_flight[passenger_count])` | 138,458 ✅ | 5 | Correctly implemented |
| **Total Miles Flown** | Not in reference | `SUMX(fact_flight, distance_nm * 1.15078)` | 13.31M | 4 | Good addition for PlaneSense story (client claims 15.9M/year) but should be a 7th card, not replace Total Flights |

**Section Score: 3.3 / 5**
**Priority gaps**: Fleet Availability % missing (highest priority), Total Flights replaced by Miles Flown, Avg hours value discrepancy needs investigation

---

## Section 4 — Row 2 Visuals

### Visual 2a — Monthly Flight Hours Trend

| Item | Reference | Current | Score | Gap |
|------|-----------|---------|-------|-----|
| Visual type | Line chart | ✅ Line chart | 5 | Correct |
| PC-12 NGX line | ✅ Separate line with label | ✅ Present | 5 | Correct |
| PC-24 line | ✅ Separate line | ✅ Present | 5 | Correct |
| **Y-axis measure** | `[Avg Monthly Hours per Aircraft]` per spec | 🔴 Appears to use `[Total Flight Hours]` (SUM) | 2 | **Critical**: MD file specifies `DIVIDE(SUM(flight_hours), DISTINCTCOUNT(aircraft_id))` — per-aircraft average. Current Y-axis label reads "Total flight hours" suggesting developer used SUM instead. Reference image Y-axis caps at ~300, consistent only with per-aircraft average (~75–85 hrs/month), not fleet totals (which would be thousands). Must switch measure. |
| **Y-axis title** | "Avg Flight Hours per Aircraft" | "Total flight hours" | 1 | Wrong label — must change to "Avg Flight Hours per Aircraft" |
| FAA Benchmark line | ✅ Dashed gray horizontal line at 267 hrs | ❌ Not visible | 1 | Missing — must add via Analytics pane → Constant Line → value `267`, dashed gray, label "FAA Commercial Turboprop Avg (267 hrs/month)". **Important caveat**: this benchmark applies ONLY to commercial turboprop (Part 135) operators — it is NOT applicable to the PC-24 line (which is a twin-engine business jet). Label must clarify scope. |
| Tooltips | Flights count + Flight hours on hover | Not verifiable from screenshot | — | N/A |
| X axis | Month + Year (`dim_date[Month Year Label]`) | ✅ Present | 5 | Correct |
| Legend | PC-12 NGX + PC-24 labels | ✅ Present top-left | 5 | Correct |
| Line shapes | Smooth curves showing seasonal variation | Current appears nearly flat | 3 | Lines appear flat — once Y-axis measure is corrected to per-aircraft average, seasonal variation (summer peak Jun–Aug, winter trough Jan–Feb) should become visible |

**Visual 2a Score: 2.9 / 5** *(revised down from 3.6 — Y-axis measure issue is a critical implementation error)*

**Priority gaps**:
1. Switch Y-axis field from `[Total Flight Hours]` → `[Avg Monthly Hours per Aircraft]`
2. Rename Y-axis title to "Avg Flight Hours per Aircraft"
3. Add FAA Benchmark Constant Line at 267 with label scoped to turboprop only
4. Verify seasonal variation becomes visible after measure fix

> **MD file internal inconsistency (for developer awareness)**: The MD file spec (line 587) correctly defines the Y-axis as `[Avg Monthly Hours per Aircraft]`, but the "Expected result" note on line 617 contradicts this by saying "~3,000–3,800 hrs/month total (fleet total)." Per-aircraft average of 75–85 hrs can never produce fleet totals of 3,000–3,800. The measure definition is correct — the expected result note is wrong. Developer should follow the measure definition, not the expected result note.

---

### Visual 2b — Aircraft Utilization Heatmap (Matrix)

| Item | Reference | Current | Score | Gap |
|------|-----------|---------|-------|-----|
| Visual type | Matrix (heatmap) | ✅ Matrix | 5 | Correct |
| Rows | `dim_aircraft[tail_number]` | ✅ Tail_Number shown | 5 | Correct |
| Columns | `dim_date[year]` → `month_name` hierarchy | ✅ Jan–Aug visible (scrollable) | 5 | Correct |
| Values | `[Total Flight Hours]` | ✅ Numeric values showing | 5 | Correct |
| Conditional formatting | Red(<50) → Yellow(50–80) → Green(>80) | ✅ Red/Yellow/Green visible | 5 | Applied — gradient working |
| Custom gradient thresholds | Max set to 75 to push more green | Appears applied based on color distribution | 4 | Mostly green with some red/amber — looks realistic |
| Row totals | Should be OFF per spec | ✅ "Total" row visible at bottom | 2 | Total row is ON — spec says turn it OFF to reduce clutter |
| Legend | "Low → High" with color bar | ✅ Present top-right | 5 | Matches reference |

**Visual 2b Score: 4.5 / 5**
**Priority gap**: Turn OFF row/column totals (Format pane → Row subtotals → OFF)

---

## Section 5 — Row 3 Visuals

### Visual 3a — Top Routes by Frequency

| Item | Reference | Current | Score | Gap |
|------|-----------|---------|-------|-----|
| Visual type | Horizontal bar chart | ✅ Horizontal bar | 5 | Correct |
| Number of routes | Top **15** routes | Top **5** routes only | 2 | Showing only 5 — TopN filter must be changed to 15 |
| Y axis | Route label (origin → destination) | ✅ Route labels showing | 5 | Correct format |
| X axis | `[Total Flights]` (count) | ✅ Route Frequency | 5 | Correct |
| Legend/color split | `dim_aircraft[model]` — PC-12 blue, PC-24 orange | 🟠 Single color visible | 2 | PC-12 vs PC-24 color split not visible — Legend field may not be set |
| Same-origin filter | Exclude `Is Valid Route = "Include"` | Not verifiable | — | N/A |
| Sort | Descending by `[Total Flights]` | ✅ Sorted longest bar top | 5 | Correct |

**Visual 3a Score: 3.2 / 5**
**Priority gaps**: Change TopN from 5 → 15; Add `dim_aircraft[model]` to Legend field for PC-12/PC-24 color split

---

### Visual 3b — Fleet Performance Trend (Fleet Status Over Time)

| Item | Reference | Current | Score | Gap |
|------|-----------|---------|-------|-----|
| Visual type | 100% Stacked Area | ✅ Stacked Area | 5 | Correct |
| FLYING band | ✅ Green, dominant | 🟠 "Flying" present but teal/blue | 3 | Color should be Green #00B050 per spec |
| AVAILABLE band | ✅ Blue | ✅ "Available" present | 4 | Present |
| IN_MAINTENANCE band | ✅ Amber | 🔴 Not visible as distinct band | 2 | In Maintenance not visible — may be missing from Values field or color too similar |
| AOG band | ✅ Red (thin) | 🟠 "AOG" present | 4 | Present but very thin (correct) |
| Y axis | 0–100% | ✅ 0–100% "Available %" | 4 | Showing percentage correctly |
| X axis | Month Year | ✅ Month Year labels | 5 | Correct |
| Legend | 4 status labels | ✅ Available / Flying / AOG | 3 | Missing "In Maintenance" from legend |
| Seasonal pattern | Summer FLYING peak, Winter dip | 🟠 Some variation visible | 3 | Pattern exists but subtle — will improve after AVAILABLE rebalancing |

**Visual 3b Score: 3.7 / 5**
**Priority gaps**: IN_MAINTENANCE band missing or invisible; FLYING color should be Green (#00B050); confirm all 4 measures are in Values field

---

### Visual 3c — Regional Utilization Map (Departure Density)

| Item | Reference | Current | Score | Gap |
|------|-----------|---------|-------|-----|
| Visual type | Bubble map (USA) | ✅ Bubble map | 5 | Correct |
| Bubble size | `[Airport Departures]` | ✅ Varying bubble sizes visible | 5 | Correct |
| Bubble color | PC-12 & PC-24 = blue, PC-12 Only = red | 🟠 Single color (teal) | 2 | PC-12-only airports (2B2, K1B1) should show red — `dim_airport[Aircraft Access]` not on Legend |
| Coverage | Mostly Northeast with some Southeast/West | ✅ Correct geographic distribution | 5 | Matches expected airport coverage |
| Tooltips | airport_name, city, state, departures, hours, runway | Not verifiable | — | N/A |
| Title | "Regional Utilization Map" | "Departure Density" | 4 | Different title but acceptable |

**Visual 3c Score: 3.8 / 5**
**Priority gap**: Add `dim_airport[Aircraft Access]` to Legend field to show PC-12-only airports in red

---

## Overall Dashboard Score — V1 Baseline

| Section | Max Score | Current Score | % |
|---------|-----------|---------------|---|
| Header / Title | 5 | 4.5 | 90% |
| Slicers (5 required) | 5 | 2.7 | 54% |
| KPI Cards (6 required) | 5 | 3.3 | 66% |
| Visual 2a — Monthly Trend | 5 | 2.9 | 58% *(revised — Y-axis measure wrong)* |
| Visual 2b — Heatmap | 5 | 4.5 | 90% |
| Visual 3a — Routes | 5 | 3.2 | 64% |
| Visual 3b — Fleet Status | 5 | 3.7 | 74% |
| Visual 3c — Map | 5 | 3.8 | 76% |
| **TOTAL** | **40** | **28.6** | **71.5%** |

---

## Prioritized Gap List

### P1 — Critical (affects core narrative or is completely missing)

| # | Gap | Component | Action Required |
|---|-----|-----------|----------------|
| 1 | Fleet Availability % KPI missing | KPI Card 4 | Add two measures: `Available Aircraft Days = CALCULATE(COUNTROWS(fact_aircraft_daily_status), fact_aircraft_daily_status[status] IN {"FLYING","AVAILABLE"})` then `Fleet Availability % = DIVIDE([Available Aircraft Days], COUNTROWS(fact_aircraft_daily_status), 0)`. Display as Card with format `0.0%`. |
| 2 | Total Flights KPI missing (replaced by Miles Flown) | KPI Card 2 | Add `Total Flights = COUNTROWS(fact_flight)` card. Keep "Total Miles Flown" as an additional 7th card — do not remove it. |
| 3 | **Y-axis measure wrong on Monthly Trend** | Visual 2a | Replace Y-axis field with `[Avg Monthly Hours per Aircraft]` = `DIVIDE(SUM(fact_flight[flight_hours]), DISTINCTCOUNT(fact_flight[aircraft_id]), 0)`. This will shift Y-axis scale from thousands down to ~75–167 range. Also rename Y-axis title from "Total flight hours" to "Avg Flight Hours per Aircraft". |
| 4 | FAA Benchmark line missing on Monthly Trend | Visual 2a | After fixing measure (gap #3): Analytics pane → Constant Line → value `267` → dashed gray → label "FAA Commercial Turboprop Avg (PC-12 only)". **Note**: 267 hrs/month = ~3,200 hrs/year is the Part 135 commercial turboprop benchmark. This benchmark does NOT apply to the PC-24 line — PC-24 is a twin-engine business jet (Super Light Jet class, Williams FJ44-4A turbofan engines), not a turboprop. The label must reflect this limitation. |
| 5 | IN_MAINTENANCE band missing/invisible on Fleet Status | Visual 3b | Confirm `[Aircraft IN_MAINTENANCE]` measure is in Values well; set color to Amber #ED7D31 |
| 6 | Base Facility slicer missing | Slicers | Add slicer from `dim_facility[facility_name]`, Tile style |
| 7 | Year slicer missing | Slicers | Add slicer from `dim_date[year]`, Dropdown style |

### P2 — High (materially affects usability or visual accuracy)

| # | Gap | Component | Action Required |
|---|-----|-----------|----------------|
| 7 | Top Routes shows 5 instead of 15 | Visual 3a | Change TopN filter from 5 to 15 |
| 8 | No PC-12/PC-24 color split on Routes chart | Visual 3a | Add `dim_aircraft[model]` to Legend field; set PC-12=Blue, PC-24=Orange |
| 9 | PC-12-only airport highlighting missing on Map | Visual 3c | Add `dim_airport[Aircraft Access]` to Legend; PC-12 Only = Red |
| 10 | FLYING band color is teal, not green | Visual 3b | Change Aircraft FLYING series color to Green #00B050 |
| 11 | Date range default showing 2025 only | Slicers | Reset default to show full 2023–2025 range |

### P3 — Low (polish and minor deviations)

| # | Gap | Component | Action Required |
|---|-----|-----------|----------------|
| 12 | "Travel Purpose" label should be "Flight Purpose" | Slicers | Rename slicer header |
| 13 | Flight Purpose should be checklist not dropdown | Slicers | Change slicer style to List |
| 14 | Heatmap Total row should be OFF | Visual 2b | Format pane → Row subtotals → OFF |
| 15 | Avg Hours per Aircraft value (1.72 vs expected ~2.3) | KPI Card 3 | Investigate denominator — may need to verify `fact_aircraft_daily_status` row count after data refresh |
| 16 | Tail Number extra slicer not in reference | Slicers | Consider removing or relocating to reduce clutter |

---

## Next Steps for V2 Iteration

Work through gaps in P1 → P2 → P3 order. After each fix batch, share a new screenshot for re-scoring. Target score for V2: **≥ 85% (34/40)**.

---

## Analysis Notes & Clarifications

These are conceptual clarifications established during review sessions — intended to prevent misinterpretation during implementation.

---

### Note 1 — Fleet Availability % and Deadhead Ratio are independent metrics (do NOT add to 100%)

**Question raised**: Do Fleet Availability % (88.7% in reference) and Deadhead Ratio % (2.9% in reference) together sum to 100%?

**Answer**: No. They are completely independent and measure different things across different tables:

| KPI | Source Table | Unit of Measure | What it answers |
|-----|-------------|-----------------|----------------|
| Fleet Availability % | `fact_aircraft_daily_status` | Aircraft-days | "What % of days was each aircraft ready to fly (FLYING or AVAILABLE)?" |
| Deadhead Ratio % | `fact_flight` | Individual flight legs | "What % of flights carried zero passengers (empty legs)?" |

An aircraft can sit on the ground all day as AVAILABLE — that day contributes to Fleet Availability but produces no flight record at all, so it does not factor into Deadhead Ratio. The two metrics operate on different denominators across different tables and have no mathematical relationship to each other.

**Why the reference values differ from current build**: Reference shows 2.9% Deadhead vs current 14.95% — this is because the reference may be filtered to a different time window with fewer repositioning flights, or was built on different input data. The DAX implementation is structurally correct in the current build.

---

### Note 2 — PC-24 is a twin-engine business jet, NOT a turboprop

**Classification**: Pilatus PC-24 — Super Light Business Jet, powered by two Williams FJ44-4A **turbofan** engines. FAA survey category: **Turbojet**. It is in the same class as Cessna Citation CJ4 and Embraer Phenom 300.

**Why this matters for Visual 2a**: The FAA benchmark constant line at 267 hrs/month is explicitly for **commercial turboprop operators** (Part 135 scheduled/air taxi). It is relevant only to the PC-12 NGX line. Applying it visually to the same chart as the PC-24 line is misleading unless clearly labelled.

**Correct benchmark context by aircraft type**:

| Aircraft | FAA Category | Benchmark Type | Benchmark Value |
|----------|-------------|----------------|-----------------|
| PC-12 NGX | Turboprop single-engine | FAA Part 135 commercial turboprop | ~267 hrs/month (~3,200 hrs/year) |
| PC-24 | Turbojet (Super Light Jet) | High-utilization fractional light jet industry avg | ~40–50 hrs/month (~500–600 hrs/year) |
| PlaneSense PC-12 (our data) | — | Actual per MD file expected | ~75–85 hrs/month per aircraft |
| PlaneSense PC-24 (our data) | — | Actual per user-confirmed data | ~92–100 hrs/month per aircraft |

PlaneSense PC-24s at ~100 hrs/month are operating at 2–3× the typical fractional light jet industry average (40–50 hrs/month), which reflects the intensity of their fractional ownership program.

**Developer instruction**: When adding the benchmark line at 267, set the label to "FAA Commercial Turboprop Avg (PC-12 only)" — not a generic label — so CIO-level readers understand it applies only to the turboprop line.

---

### Note 3 — MD file internal inconsistency in Visual 2a Expected Result

The MD file contradicts itself on Visual 2a:
- **Line 587 (Field well spec)**: Y-axis = `[Avg Monthly Hours per Aircraft]` — correct, produces values ~75–167
- **Line 617 (Expected result)**: *"PC-12 NGX trending ~3,000–3,800 hrs/month total (fleet total)"* — incorrect; describes fleet totals, not per-aircraft averages

**Resolution**: Follow the field well spec (line 587), not the expected result note (line 617). Per-aircraft average is the correct measure, consistent with the reference image Y-axis scale (~300 max) and with the benchmark line at 267 being meaningful.

---

*Evaluation conducted by: AI-assisted review*
*Reference files: `DAX_DASHBOARD1_FLEET_UTILIZATION.md`, `Aircraft utilization - overview.png`*
*Next iteration: `DASHBOARD1_EVALUATION_V2.md` (to be created after gap fixes)*

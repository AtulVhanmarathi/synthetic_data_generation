# Dashboard Deep Evaluation & Data Model Design

> **Date**: 2026-03-02
> **Input**: `output/Book1.xlsx` (7 sheets)
> **Evaluator Perspective**: Aviation Domain Expert + CIO Strategist + BI Architect + Data Modeler

---

# STEP 1 — Sheet-by-Sheet Evaluation

---

## Sheet 1: Aircraft Dim

### A. Summary of Intent
Master dimension table for the aircraft fleet. Attempts to capture aircraft identity, model, age, flight hours, cycles, region, certification, and status. This is the central dimension for both dashboards.

### B. Strengths
- Correct separation of PC-12 and PC-24 as distinct model types
- Includes "Years in Service" (derived from Year of Make) — useful for age-based analysis
- "Current Status" enables active/in-maintenance filtering
- "Last Flight Worthy Certification date" shows domain awareness (airworthiness is a real aviation concept)
- "Owning Region" enables geographic slicing
- Sample has 10 PC-12 + 5 PC-24 = 15 aircraft (smaller demo set; production would be 46 + 16 = 62)

### C. Gaps & Missing Components

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| **No engine type column** | PC-12 (PT6A-67P turboprop) and PC-24 (2× FJ44-4A turbofan) have fundamentally different maintenance profiles | Add `engine_type` and `engine_count` |
| **No serial number** | Cannot link to FAA registry, SDRS, or NTSB data | Add `serial_number` |
| **No tail/registration number** | "Aircraft No" is an internal ID (PC12-001), not an FAA N-number | Add `registration_number` (e.g., N100AF) or clarify that Aircraft No IS the tail number |
| **No base facility** | Cannot determine which maintenance facility services this aircraft | Add `base_facility` (Portsmouth NH / Boulder City NV) |
| **No delivery date** | "Year of Make" is coarse — delivery date enables precise age calculations | Replace with or add `delivery_date` |
| **"Total Flight Hours" and "# flight cycles" are static** | These are point-in-time snapshots that become stale | These should be **calculated measures** from Trip Fact Table, not stored in the dimension. Keep `hours_at_delivery` if needed for baseline |
| **No MTOW / max range / seat capacity** | Limits operational comparison between PC-12 (10 pax, 1,845 nm) and PC-24 (11 pax, 2,000 nm) | Add aircraft specification columns or a separate Aircraft Specs dimension |
| **No maintenance program type** | PlaneSense may use MSG-3, phase inspection, or progressive inspection programs | Add `maintenance_program` column |
| **Missing sample data** | Most rows have only Aircraft No and Model populated — Year of Make only for first 5 PC-12s and all PC-24s | Fill all rows for evaluation completeness |
| **Year of Make values are unrealistic** | PC12-001 = 1995, but PlaneSense's fleet avg age is 4.5 years (so oldest ~2017). A 1995 PC-12 is 30 years old | Align with real fleet profile: PC-12s 2017-2024, PC-24s 2018-2025 |

### D. Improvements Suggested

**Rename and restructure:**
```
Aircraft_ID (PK) | Tail_Number | Model | Engine_Type | Engine_Count |
Serial_Number | Delivery_Date | Years_In_Service (calculated) |
Base_Facility | Owning_Region | Seat_Capacity | Max_Range_NM |
MTOW_KG | Airworthiness_Cert_Date | Current_Status |
Maintenance_Program | Insurance_Group
```

**Remove from dimension (move to calculated measures):**
- Total Flight Hours → SUM from Trip Fact
- Total Flight Cycles → COUNT from Trip Fact
- These MUST be calculated dynamically, otherwise every dashboard filter (date range, region) shows stale numbers

### E. CIO-Level Considerations

- **"Why is your oldest PC-12 from 1995?"** PlaneSense cycles out aircraft at 10-12 years. A 30-year-old PC-12 in the fleet would raise immediate credibility questions. Fix the year range.
- **"Where's the tail number?"** Any aviation CIO expects to see N-numbers — internal IDs alone look like a toy dataset.
- **"How does this connect to FAA records?"** Without serial_number or registration_number, there's no bridge to SDRS, NTSB, or FAA registry — which is the entire "authenticated public data" narrative.

---

## Sheet 2: Trip Fact Table

### A. Summary of Intent
Captures individual flight legs — the core utilization fact table. Links to aircraft, crew, booking, and airports. Includes a "Maintenance Related?" flag to distinguish revenue vs. ferry/repositioning flights.

### B. Strengths
- **Journey Leg concept** (JL-001, JL-002 under one Booking No) — correctly models multi-leg trips
- **Maintenance Related flag** — smart: ferry flights to/from maintenance facilities are non-revenue but real utilization
- **Crew columns** (Pilot, Copilot, Crew1-3) — enables crew utilization analysis
- **Start/Destination Airport** — enables route network analysis
- **Links to Booking No** — enables revenue attribution
- **Date + Aircraft No as compound key context** — proper fact table structure

### C. Gaps & Missing Components

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| **No Flight Duration populated** | This is THE core utilization metric — empty makes the sheet non-functional | Must populate; use hours (decimal) not HH:MM |
| **No departure/arrival time** | Cannot calculate block time, turnaround time, or daily utilization curves | Add `departure_time`, `arrival_time` |
| **No distance/miles** | Cannot calculate miles flown, deadhead ratio, or route efficiency | Add `distance_nm` (nautical miles) |
| **No passenger count** | "Client Onboard" is Y/N binary — doesn't capture how many | Replace with `passenger_count` (integer); keep Y/N as derived |
| **No deadhead flag** | Repositioning flights (empty legs) are a major utilization metric; "Maintenance Related?" only catches one type | Add `is_deadhead` (Y/N) — flight with zero passengers and not maintenance |
| **No fuel consumed** | Key cost metric; enables cost-per-flight-hour and fuel efficiency analysis | Add `fuel_gallons` or `fuel_kg` |
| **No flight phase data** | Cannot distinguish between block time (gate-to-gate) and flight time (wheels-up to wheels-down) | Add `block_hours` vs `flight_hours` if data permits |
| **Airport codes are city names** | "Chicago" and "Minneapolis" are not airport identifiers — multiple airports per city | Use ICAO codes (KORD, KMSP) or IATA codes (ORD, MSP); links to NASR airport dimension |
| **No weather conditions** | Cannot analyze weather impact on utilization (delays, cancellations) | Add `weather_delay_min` or link to weather dimension |
| **No flight status** | Was this flight completed, diverted, cancelled? | Add `flight_status` (COMPLETED / DIVERTED / CANCELLED) |
| **No revenue/cost flag beyond maintenance** | Charter, owner, demo, training flights all have different utilization implications | Add `flight_purpose` (OWNER / CHARTER / MAINTENANCE_FERRY / TRAINING / DEMO / REPOSITIONING) |
| **Crew names are placeholders (X, Y, A, B)** | Need proper crew IDs to link to a Crew Dimension | Use structured IDs (CREW-001) |

### D. Improvements Suggested

**Revised schema:**
```
Trip_ID (PK) | Date | Aircraft_ID (FK) | Booking_ID (FK) |
Journey_Leg_Seq | Origin_ICAO (FK) | Destination_ICAO (FK) |
Departure_Time | Arrival_Time | Block_Hours | Flight_Hours |
Distance_NM | Passenger_Count | Flight_Purpose |
Is_Deadhead | Is_Maintenance_Ferry | Flight_Status |
Fuel_Consumed_Gal | Pilot_ID (FK) | Copilot_ID (FK) |
Weather_Delay_Min | Cancellation_Reason
```

**Critical calculated measures this fact enables:**
- `Utilization Rate` = SUM(Flight_Hours) / (Aircraft_Count × Available_Hours_Per_Day × Days_In_Period)
- `Deadhead Ratio` = SUM(Deadhead_Miles) / SUM(Total_Miles)
- `Revenue Hours Ratio` = SUM(Revenue_Flight_Hours) / SUM(Total_Flight_Hours)
- `Average Leg Duration` = AVG(Flight_Hours)
- `Cycles Per Day` = COUNT(Trip_ID) / DISTINCTCOUNT(Date)

### E. CIO-Level Considerations

- **"What's your deadhead ratio?"** This is THE first question any aviation operations CIO asks. Without it, the dashboard misses the single most actionable utilization metric.
- **"What's utilization vs. availability?"** Aircraft can be available but unused (demand gap) or unavailable (maintenance). The current schema can't distinguish these states.
- **"How does weather impact your operation?"** PlaneSense operates in the Northeast (heavy winter weather). Without weather correlation, the utilization story is incomplete.

---

## Sheet 3: Booking Fact Table

### A. Summary of Intent
Captures booking/reservation data — the demand side of the equation. Links owners to trips and enables demand analysis.

### B. Strengths
- Separates booking from trip execution (correct: a booking may result in 0, 1, or many flights)
- Includes "Purpose" (Leisure/Business) — enables demand segmentation
- "No of Pets" — domain-specific detail that shows industry awareness (PlaneSense explicitly markets pet-friendly flying)
- "Preferred Plane" — captures aircraft preference which affects fleet allocation

### C. Gaps & Missing Components

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| **No Booking Status** | Can't distinguish confirmed / pending / cancelled bookings | Add `booking_status` (REQUESTED / CONFIRMED / COMPLETED / CANCELLED / NO-SHOW) |
| **No lead time** | Booking Date → Departure Date gap is key demand forecasting metric | Derive from Booking_Date and Departure_Date; but both must be populated |
| **No owner/share information** | "Client Name" alone doesn't capture share type (1/32, 1/16, 1/8, 1/4) which determines entitlement hours | Add `owner_id` (FK to Owner Dimension), or embed `share_type` |
| **No aircraft assigned** | Only "Preferred Plane" (which is a request, not assignment) — no link to which aircraft actually flew | The Booking No FK in Trip Fact handles this, but should be explicit here too |
| **No return leg / round-trip flag** | One-way vs round-trip bookings have different utilization implications | Add `trip_type` (ONE_WAY / ROUND_TRIP / MULTI_LEG) |
| **No booking channel** | Phone, app, portal — important for digital transformation narrative | Add `booking_channel` |
| **No pricing/revenue** | Can't calculate revenue per flight hour, revenue per booking | Add `estimated_cost` or `hours_charged` |
| **Missing data** | Only 2 sample rows, most fields empty | Needs population |

### D. Improvements Suggested

**Revised schema:**
```
Booking_ID (PK) | Booking_Date | Owner_ID (FK) | Client_Name |
Passenger_Count | Pet_Count | Preferred_Aircraft_Model |
Departure_Date | Departure_Time | Origin_ICAO (FK) |
Destination_ICAO (FK) | Trip_Type | Trip_Purpose |
Booking_Status | Booking_Channel | Hours_Charged |
Lead_Time_Days (derived) | Assigned_Aircraft_ID (FK)
```

### E. CIO-Level Considerations

- **"What's our booking-to-flight conversion rate?"** Without booking status, can't calculate how many bookings become flights vs cancellations.
- **"What's the lead time distribution?"** Fractional operators live and die by how far in advance owners book. Short lead times create scheduling nightmares.
- **Booking is the DEMAND signal; Trip is the SUPPLY execution.** The gap between them is where operational intelligence lives.

---

## Sheet 4: Utilization Visuals

### A. Summary of Intent
Dashboard layout mockup for the Aircraft Utilization Dashboard. Proposes filters (Date, Aircraft Model, Aircraft, Trip Purpose) and 6 visual elements.

### B. Strengths
- **Date range filter (From/To)** — essential
- **Aircraft Model + Aircraft double-filter** — enables fleet-level then drill-to-individual
- **Trip Purpose filter** — distinguishes business vs leisure utilization
- **Deadhead Miles as a separate metric** — shows awareness of empty-leg problem
- **Top 10 Destinations** — good operational insight
- **Top 10 Customers** — good for identifying key accounts

### C. Gaps & Missing Components

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| **No core utilization KPI cards** | No headline numbers: Fleet Utilization %, Total Flight Hours, Total Cycles, Average Hours/Aircraft/Day | Add KPI card row at top: Utilization Rate, Total Flight Hours, Total Cycles, Avg Daily Hours, Fleet Availability % |
| **No time-series granularity control** | "Flight Trends" and "Deadhead Trends" — by day? week? month? quarter? | Add time granularity toggle (Daily / Weekly / Monthly / Quarterly) |
| **No benchmark line** | Trends without context are meaningless — need industry benchmark or prior year comparison | Add FAA GA Survey average as benchmark overlay |
| **No fleet availability visual** | How many aircraft are flyable vs in maintenance on any given day? | Add stacked area chart: Available / In Maintenance / AOG over time |
| **No heatmap** | Aircraft × Month utilization heatmap is the single most powerful utilization visual | Add utilization heatmap matrix |
| **No regional breakdown** | "Owning Region" is in the dimension but no visual uses it | Add regional utilization map or bar chart |
| **Missing slicer: Base Facility** | Portsmouth vs Boulder City utilization comparison is critical | Add Base Facility slicer |
| **Missing slicer: Flight Purpose** | Beyond Trip Purpose (business/leisure), need Maintenance Ferry / Revenue / Repositioning | Expand flight categorization |
| **No daily utilization curve** | What hours of the day are aircraft flying? Peak hour analysis | Add hourly distribution histogram |
| **# Passengers Flown metric** | Good, but should be segmented (per flight, per aircraft, per route) | Add Average Load Factor = Passengers / Seat Capacity |
| **# Pets Flown** | Novel but may seem trivial in a CIO dashboard | Keep as small KPI card, not a major visual — it's a differentiator talking point |

### D. Improvements Suggested

**Proposed Utilization Dashboard Layout (3-row):**

**Row 1 — KPI Cards:**
| Fleet Utilization % | Total Flight Hours | Total Cycles | Avg Hours/Aircraft/Day | Deadhead Ratio | Fleet Availability % |

**Row 2 — Trends + Heatmap:**
| Flight Hours Trend (monthly, with FAA benchmark line) | Aircraft × Month Utilization Heatmap |

**Row 3 — Operational Breakdowns:**
| Top 10 Routes by Frequency | Top 10 Airports by Hours | Regional Utilization Map |

**Slicers:** Date Range | Aircraft Model | Individual Aircraft | Base Facility | Flight Purpose | Region

### E. CIO-Level Considerations

- **"What's our utilization rate vs industry?"** Without the FAA benchmark overlay, trends are just lines — they don't answer "are we good or bad?"
- **"Which aircraft are sitting idle?"** The heatmap instantly answers this — currently missing
- **"What's the revenue impact of deadhead flights?"** Deadhead Miles is shown, but no cost association

---

## Sheet 5: Maintenance Jobs Fact

### A. Summary of Intent
Captures maintenance work orders at the job level — the header record for each maintenance event. Links to aircraft, facility, and time.

### B. Strengths
- **Maintenance Type differentiation** (Preventive / AOG) — correct: scheduled vs unscheduled is THE fundamental maintenance split
- **Facility column** — Portsmouth vs Boulder City tracking
- **Service Owner** — implies technician/team assignment tracking
- **Start/Close Date+Time** — enables TAT (Turnaround Time) and MTTR calculation

### C. Gaps & Missing Components

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| **Only 2 maintenance types** | Preventive and AOG are extremes — missing: Line Maintenance, Heavy Check (A/B/C/D), Component Replacement, Inspection, Modification/SB compliance, Troubleshooting | Expand `maintenance_type` to: PREVENTIVE / LINE / A_CHECK / B_CHECK / C_CHECK / D_CHECK / COMPONENT_REPLACEMENT / AOG / MODIFICATION / INSPECTION |
| **No priority/severity** | AOG implies critical, but no severity scale for other types | Add `severity` (ROUTINE / URGENT / AOG / SAFETY_CRITICAL) |
| **No trigger/source** | What initiated this maintenance? Scheduled interval? Pilot report? Sensor alert? SDR? | Add `trigger_source` (SCHEDULED / PILOT_REPORT / SENSOR_ALERT / INSPECTION_FINDING / AD_COMPLIANCE / SDR) |
| **No associated flight** | If maintenance was triggered by in-flight event, which flight? | Add `triggering_flight_id` (FK to Trip Fact, nullable) |
| **No downtime hours** | Close - Start gives wall-clock time, but not all of it is active downtime (parts waiting, shift gaps) | Add `active_repair_hours` vs `total_elapsed_hours` |
| **No status** | Is this job open, in progress, completed, deferred? | Add `job_status` (OPEN / IN_PROGRESS / PARTS_AWAITING / COMPLETED / DEFERRED) |
| **No component link at header level** | Can't aggregate by component type at the job level | Add `primary_component_id` (FK) |
| **"Service Owner" is undefined** | Technician? Team? Shift? | Rename to `assigned_technician_id` (FK to Crew/Technician Dimension) |
| **No regulatory reference** | Was this maintenance triggered by an AD (Airworthiness Directive) or SB (Service Bulletin)? | Add `ad_sb_reference` (nullable) |
| **No deferral/MEL tracking** | Deferred maintenance via MEL (Minimum Equipment List) is a major operational reality | Add `mel_reference` and `deferral_expiry_date` |

### D. Improvements Suggested

**Revised schema:**
```
Maintenance_Job_ID (PK) | Date_Opened | Aircraft_ID (FK) |
Facility (FK) | Maintenance_Type | Severity | Trigger_Source |
Assigned_Technician_ID (FK) | Primary_Component_ID (FK) |
Job_Status | Start_DateTime | Close_DateTime |
Total_Elapsed_Hours | Active_Repair_Hours |
Triggering_Flight_ID (FK) | AD_SB_Reference |
MEL_Reference | Deferral_Expiry_Date |
Is_AOG | Is_Scheduled
```

### E. CIO-Level Considerations

- **"What's our planned vs unplanned maintenance ratio?"** The current schema barely supports this (only Preventive vs AOG). Real answer needs the full maintenance type taxonomy.
- **"How long are aircraft grounded?"** Start/Close time is there, but no concept of parts-waiting time, which is often 60-80% of total TAT.
- **"Are we compliant with all ADs?"** Without AD/SB tracking, there's no regulatory compliance view — a CIO's nightmare scenario.

---

## Sheet 6: Maintenance Details Fact Table

### A. Summary of Intent
Line-item detail for each maintenance job — labor, parts, fuel, certification. This is the cost and resource consumption fact table.

### B. Strengths
- **Multi-type detail rows** (Repair, Replace, Labor, Fuel, Certification) — correctly models that one job has many cost lines
- **UOM + Quantity + Unit Cost + Extended Cost** — proper cost accounting structure
- **Component identification** ("Back tyre", "Front tyre", "Reading Light", "Seat Strap") — shows real part-level granularity
- **Facility linkage** — cost by facility is important
- **Fuel as a maintenance line item** — smart: aircraft must be fueled after maintenance before return to service

### C. Gaps & Missing Components

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| **No Part Number** | "Back tyre" is a description, not an inventory identifier | Add `part_number` (FK to Parts Inventory dimension) — enables parts consumption tracking |
| **No component category / JASC-ATA code** | Can't aggregate by system (propulsion, landing gear, avionics, etc.) | Add `jasc_ata_code` — links to FAA SDRS taxonomy |
| **"type" column overloaded** | Repair, Replace, Checkup are maintenance actions; Labor, Fuel, Certification are cost categories — these are two different dimensions | Split into: `action_type` (REPAIR / REPLACE / INSPECT / OVERHAUL / SERVICE) and `cost_category` (LABOR / PARTS / FUEL / CERTIFICATION / TOOLING / EXTERNAL) |
| **No warranty flag** | Parts under warranty have zero cost but still represent a maintenance event | Add `is_warranty` (Y/N) |
| **Unit costs missing for components** | Tyre, Reading Light, Seat Strap — no unit cost populated | Must populate; our synthetic data has part costs |
| **No supplier** | Which vendor supplied the replacement part? | Add `supplier_id` (FK to Supplier Dimension) |
| **No condition code** | Was the removed part scrapped, repairable, or sent for overhaul? | Add `removed_part_condition` (SCRAP / REPAIRABLE / OVERHAUL / SERVICEABLE) |
| **No serial number tracking** | Serialized parts (engines, props, landing gear) need on/off serial tracking | Add `serial_number_installed` and `serial_number_removed` for serialized parts |
| **"Cost Head" terminology** | Unconventional — standard terms are "Cost Category" or "Cost Element" | Rename to `cost_category` |

### D. Improvements Suggested

**Revised schema:**
```
Detail_Line_ID (PK) | Maintenance_Job_ID (FK) | Date |
Aircraft_ID (FK) | Facility (FK) |
Action_Type | Cost_Category | JASC_ATA_Code |
Part_Number (FK) | Part_Description | UOM |
Quantity | Unit_Cost | Extended_Cost |
Supplier_ID (FK) | Is_Warranty |
Serial_Removed | Serial_Installed | Removed_Part_Condition |
Technician_ID (FK) | Labor_Hours
```

### E. CIO-Level Considerations

- **"What's our cost per flight hour?"** This is the #1 maintenance KPI. It requires: Total Maintenance Cost (from this table) ÷ Total Flight Hours (from Trip Fact). The tables don't currently have a clean join path.
- **"What's our top cost driver?"** Without JASC codes, you can say "tyres cost the most" but not "landing gear system costs the most" — the latter is what a CIO wants.
- **"Are we seeing cost escalation?"** Need cost trend over time by category — the schema supports this but needs populated data across a meaningful time range.

---

## Sheet 7: Maintenance Visuals

### A. Summary of Intent
Dashboard layout mockup for the Maintenance Dashboard. Proposes filters and 6 visual elements.

### B. Strengths
- **MTTR and MTBF as explicit metrics** — these are THE two foundational reliability KPIs
- **Facility slicer** — Portsmouth vs Boulder City comparison
- **Aircraft Model + Individual Aircraft filters** — fleet-level and drill-down
- **"5 Aircraft Needing Most Maintenance"** — action-oriented visual
- **"Top 5 Maintenance Heads" and "Top 10 Components"** — cost driver identification

### C. Gaps & Missing Components

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| **No KPI cards** | No headline numbers at the top | Add: Total Maintenance Cost, Avg Cost/Flight Hour, Fleet MTBF, Fleet MTTR, Maintenance Downtime %, Open Work Orders |
| **No scheduled vs unscheduled split** | THE most important maintenance management metric | Add donut/pie chart: Scheduled vs Unscheduled event count and cost |
| **No maintenance backlog visual** | How many open/deferred work orders exist? | Add backlog trend chart with aging bands (0-7d, 7-30d, 30-90d, 90d+) |
| **No component lifecycle view** | Wear progression over time by component type | Add component wear trend or Weibull reliability curve |
| **No parts-waiting-time analysis** | Biggest TAT driver in real maintenance operations | Add: Parts Lead Time vs Repair Time stacked bar |
| **No regulatory compliance tracker** | AD/SB compliance status | Add compliance status table (compliant / due / overdue) |
| **Missing slicer: Maintenance Type** | Can't filter to see only AOG events, or only preventive | Add Maintenance Type slicer |
| **Missing slicer: Severity** | Can't filter by urgency | Add Severity slicer |
| **No cost trend breakdown** | "Cost of Maintenance" single number — needs time-series by category | Add cost trend stacked area: Labor / Parts / Fuel / External |
| **"Hours Grounded for Maintenance"** | Good metric but should be normalized: Grounded Hours / Total Available Hours = Downtime % | Show both absolute and percentage |

### D. Improvements Suggested

**Proposed Maintenance Dashboard Layout (3-row):**

**Row 1 — KPI Cards:**
| Total Maint Cost | Cost/Flight Hour | MTBF (hours) | MTTR (hours) | Downtime % | Open Work Orders | Scheduled vs Unscheduled Ratio |

**Row 2 — Trends + Distributions:**
| Maintenance Cost Trend (monthly, by cost category) | Scheduled vs Unscheduled Split (donut) | Component Failure Distribution (by JASC system) |

**Row 3 — Action-Oriented:**
| Top 5 Aircraft by Maintenance Cost | Top 10 Components by Replacement Frequency | Maintenance Backlog Aging | Parts Lead Time Analysis |

**Slicers:** Date Range | Facility | Aircraft Model | Individual Aircraft | Maintenance Type | Severity

### E. CIO-Level Considerations

- **"What's our maintenance cost per flight hour trend?"** This single metric benchmarks against industry ($200-$400/hr for turboprops). Without it, all other cost data lacks context.
- **"What's our unscheduled maintenance rate trend?"** Rising unscheduled rate = fleet aging or inspection quality issues. Flat/declining = good maintenance program.
- **"Do we have any overdue ADs?"** Every CIO fears this question from the FAA. Need regulatory compliance visibility.

---

# STEP 2 — Dashboard Strategy Evaluation

---

## Dashboard 1: Aircraft Utilization Dashboard

### Core KPIs Assessment

| KPI | In Current Design? | Priority | Formula |
|-----|-------------------|----------|---------|
| Fleet Utilization Rate | NO — CRITICAL MISS | P0 | SUM(Flight_Hours) / (Aircraft_Count × Max_Daily_Hours × Days) |
| Total Flight Hours | Implied (no card) | P0 | SUM(Flight_Hours) from Trip Fact |
| Total Cycles | NO | P0 | COUNT(Trip_ID) where Flight_Status = COMPLETED |
| Avg Hours / Aircraft / Day | NO | P0 | SUM(Flight_Hours) / DISTINCTCOUNT(Aircraft) / DISTINCTCOUNT(Date) |
| Deadhead Ratio | Partially (Miles shown, no ratio) | P1 | SUM(Deadhead_Miles) / SUM(Total_Miles) |
| Fleet Availability % | NO — CRITICAL MISS | P0 | COUNT(Available_Aircraft) / COUNT(Total_Aircraft) per day |
| Revenue Hours % | NO | P1 | SUM(Revenue_Flight_Hours) / SUM(Total_Flight_Hours) |
| Average Passengers/Flight | NO | P2 | AVG(Passenger_Count) |
| Load Factor | NO | P2 | AVG(Passenger_Count / Seat_Capacity) |
| Cancellation Rate | NO | P1 | COUNT(Cancelled) / COUNT(Total_Bookings) |

### Missing Drill-Down Paths
1. **Fleet → Aircraft Model → Individual Aircraft → Individual Flight** (currently stops at Individual Aircraft)
2. **Time → Year → Quarter → Month → Week → Day → Hour** (no hierarchy defined)
3. **Geography → Region → State → Airport** (no geography hierarchy)
4. **Purpose → Revenue/Non-Revenue → Business/Leisure/Training/Ferry** (flat, no hierarchy)

### What Would Make It Predictive Instead of Descriptive
- **Demand forecasting overlay**: expected bookings vs capacity (from booking lead time patterns)
- **Seasonal utilization prediction**: "Next month, based on 5-year FAA trends, expect X% utilization"
- **Aircraft rotation optimization**: "Aircraft N105AF has been idle 3 of last 7 days — suggest repositioning to BVU"
- **Weather impact prediction**: "Northeast winter storm forecast — expect 15% utilization drop this week"

### Executive Readiness Score: 4/10
**Why**: Good directional ideas but missing the headline KPIs (utilization rate, availability), no benchmarks, no time hierarchy, and incomplete data. A CIO would see this and ask "where are the numbers?"

---

## Dashboard 2: Maintenance Dashboard

### Core KPIs Assessment

| KPI | In Current Design? | Priority | Formula |
|-----|-------------------|----------|---------|
| MTBF (Mean Time Between Failures) | YES | P0 | Total_Operating_Hours / Count(Unscheduled_Events) |
| MTTR (Mean Time To Repair) | YES | P0 | AVG(Close_DateTime - Start_DateTime) for completed jobs |
| Cost Per Flight Hour | NO — CRITICAL MISS | P0 | SUM(Maintenance_Cost) / SUM(Flight_Hours) |
| Maintenance Downtime % | Partial ("Hours Grounded") | P0 | SUM(Grounded_Hours) / SUM(Available_Hours) |
| Scheduled vs Unscheduled Ratio | NO — CRITICAL MISS | P0 | COUNT(Scheduled) / COUNT(All_Events) |
| Total Maintenance Cost | YES (single number) | P0 | SUM(Extended_Cost) from Details Fact |
| Open Work Orders | NO | P1 | COUNT where Job_Status ≠ COMPLETED |
| Parts Availability Rate | NO | P1 | Parts_In_Stock / Parts_Required for open jobs |
| Repeat Defect Rate | NO | P1 | COUNT(Same_Component_Same_Aircraft within 30d) / COUNT(All_Events) |
| AD/SB Compliance % | NO | P1 | COUNT(Compliant_ADs) / COUNT(Total_Applicable_ADs) |
| Deferred Maintenance Items | NO | P1 | COUNT where Job_Status = DEFERRED |
| Labor Efficiency | NO | P2 | Actual_Labor_Hours / Estimated_Labor_Hours |

### Predictive vs Reactive Assessment
- **Current design**: 100% reactive/historical — "what happened"
- **Missing predictive indicators**:
  - Component remaining useful life trending
  - Failure probability scores from sensor data
  - Parts demand forecast (will we have stock when the next check is due?)
  - Maintenance cost projection for next quarter
- **Missing root cause analytics**:
  - No Pareto analysis (80/20 rule — which 20% of components cause 80% of cost)
  - No repeat failure tracking
  - No fleet-wide failure pattern detection

### Executive Readiness Score: 5/10
**Why**: MTBF and MTTR show domain knowledge. Cost structure is partially there. But missing the cost-per-flight-hour headline, no scheduled/unscheduled split, no backlog view, and no regulatory compliance.

---

# STEP 3 — Data Model & Table Design

---

## Entity Identification

From all 7 sheets plus domain requirements, the following entities are needed:

### Dimension Tables

| Dimension | Purpose | Key Fields |
|-----------|---------|------------|
| **Dim_Aircraft** | Fleet master | Aircraft_ID, Tail_Number, Model, Engine_Type, Delivery_Date, Base_Facility, Region, Status, Seat_Capacity, Max_Range_NM |
| **Dim_Date** | Time intelligence | Date_Key, Date, Day, Week, Month, Quarter, Year, Day_of_Week, Is_Weekend, Is_Holiday, Season |
| **Dim_Airport** | Location master (from NASR) | Airport_ICAO, Airport_Name, City, State, Region, Latitude, Longitude, Elevation_Ft, Runway_Length_Ft, Runway_Surface, Has_Instrument_Approach |
| **Dim_Component** | Part/component master | Component_ID, Component_Name, JASC_ATA_Code, Category, Aircraft_Compatibility, Life_Limit_Hours, Inspection_Interval_Hours |
| **Dim_Crew** | Pilot/technician master | Crew_ID, Name, Role (Pilot/Copilot/Technician), Base, Type_Ratings, Certifications |
| **Dim_Owner** | Fractional owner master | Owner_ID, Name, Region, Share_Type, Annual_Hours, Join_Date, Status |
| **Dim_Facility** | Maintenance facility | Facility_ID, Facility_Name, Location, Type (PRIMARY/SECONDARY), Capacity |
| **Dim_Supplier** | Parts suppliers | Supplier_ID, Supplier_Name, Lead_Time_Days, Reliability_Rating |
| **Dim_Part** | Parts inventory | Part_Number, Part_Name, Component_ID (FK), Unit_Cost, Reorder_Point, Supplier_ID (FK) |

### Fact Tables

| Fact Table | Grain | Purpose | Key Measures |
|------------|-------|---------|--------------|
| **Fact_Flight** | One row per flight leg | Utilization tracking | Flight_Hours, Distance_NM, Passenger_Count, Fuel_Consumed, Is_Deadhead |
| **Fact_Booking** | One row per booking | Demand tracking | Lead_Time_Days, Passenger_Count, Booking_Status |
| **Fact_Maintenance_Job** | One row per work order | Maintenance event tracking | Elapsed_Hours, Is_Scheduled, Severity, Job_Status |
| **Fact_Maintenance_Detail** | One row per line item | Cost tracking | Quantity, Unit_Cost, Extended_Cost, Labor_Hours |
| **Fact_Sensor_Reading** | One row per flight per component | Condition monitoring | EGT, Oil_Pressure, Vibration, Anomaly_Score |
| **Fact_Aircraft_Daily_Status** | One row per aircraft per day | Availability tracking | Status (AVAILABLE/IN_MAINTENANCE/AOG/SCHEDULED_OUT), Hours_Flown, Cycles |

### Star Schema Relationships

```
                        Dim_Date
                           |
                    +-------+-------+
                    |       |       |
              Fact_Flight  Fact_Maint_Job  Fact_Booking
                    |       |       |
              +-----+-----+ +------+
              |     |     |  |     |
        Dim_Aircraft |  Dim_Facility |
              |     |              |
        Dim_Airport Dim_Crew    Dim_Owner
                    |
            Fact_Maint_Detail
                    |
              +-----+-----+
              |     |     |
        Dim_Component Dim_Part Dim_Supplier
```

**Key relationship: Fact_Aircraft_Daily_Status**
This is the BRIDGE between utilization and maintenance. It captures:
- Was this aircraft flying, in maintenance, or idle on this day?
- This enables: `Fleet Availability %` = COUNT(AVAILABLE) / COUNT(ALL) per day

### Power BI Calculated Measures (DAX)

```
// Core Utilization Measures
Fleet Utilization Rate =
    DIVIDE(
        SUM(Fact_Flight[Flight_Hours]),
        COUNTROWS(Dim_Aircraft) * [Max_Daily_Hours] * DISTINCTCOUNT(Dim_Date[Date])
    )

Deadhead Ratio =
    DIVIDE(
        CALCULATE(SUM(Fact_Flight[Distance_NM]), Fact_Flight[Is_Deadhead] = TRUE),
        SUM(Fact_Flight[Distance_NM])
    )

Revenue Hours Pct =
    DIVIDE(
        CALCULATE(SUM(Fact_Flight[Flight_Hours]), Fact_Flight[Flight_Purpose] = "OWNER"),
        SUM(Fact_Flight[Flight_Hours])
    )

Fleet Availability Pct =
    DIVIDE(
        CALCULATE(COUNTROWS(Fact_Aircraft_Daily_Status),
            Fact_Aircraft_Daily_Status[Status] = "AVAILABLE"),
        COUNTROWS(Fact_Aircraft_Daily_Status)
    )

// Core Maintenance Measures
Cost Per Flight Hour =
    DIVIDE(
        SUM(Fact_Maintenance_Detail[Extended_Cost]),
        SUM(Fact_Flight[Flight_Hours])
    )

MTBF =
    DIVIDE(
        SUM(Fact_Flight[Flight_Hours]),
        CALCULATE(COUNTROWS(Fact_Maintenance_Job),
            Fact_Maintenance_Job[Is_Scheduled] = FALSE)
    )

MTTR =
    AVERAGE(Fact_Maintenance_Job[Total_Elapsed_Hours])

Downtime Pct =
    DIVIDE(
        SUM(Fact_Maintenance_Job[Total_Elapsed_Hours]),
        COUNTROWS(Dim_Aircraft) * 24 * DISTINCTCOUNT(Dim_Date[Date])
    )

Scheduled Maint Ratio =
    DIVIDE(
        CALCULATE(COUNTROWS(Fact_Maintenance_Job),
            Fact_Maintenance_Job[Is_Scheduled] = TRUE),
        COUNTROWS(Fact_Maintenance_Job)
    )

// Derived Columns (in Power Query / data prep)
// Fact_Flight: Is_Deadhead = IF(Passenger_Count = 0 AND Flight_Purpose <> "MAINTENANCE_FERRY", TRUE, FALSE)
// Fact_Maintenance_Job: Total_Elapsed_Hours = DATEDIFF(Start_DateTime, Close_DateTime, HOUR)
// Fact_Booking: Lead_Time_Days = DATEDIFF(Booking_Date, Departure_Date, DAY)
// Dim_Aircraft: Years_In_Service = DATEDIFF(Delivery_Date, TODAY(), YEAR)
```

---

# STEP 4 — Synthetic Data Strategy Evaluation

---

## Current Synthetic Data Assessment

### What's Realistic

| Element | Assessment | Confidence |
|---------|-----------|------------|
| Fleet size (62 aircraft) | Verified against planesense.com | HIGH |
| Fleet mix (46 PC-12 + 16 PC-24) | Verified | HIGH |
| Annual flights (~47,800) | Verified against planesense.com | HIGH |
| 2 facilities (Portsmouth + Boulder City) | Verified | HIGH |
| Component types (17) | Reasonable for demo; real fleet has hundreds | MEDIUM |
| Seasonal patterns (summer peak) | Directionally correct, needs FAA validation | MEDIUM |

### What Needs Validation Against Real Data

| Assumption | Synthetic Value | Validation Source | Action Required |
|-----------|----------------|-------------------|-----------------|
| PC-12 annual hours | ~850 hrs/yr | FAA GA Survey Ch6 (airframe hours for turboprop single-engine) | PARSE Ch6 across 2020-2024 and extract turboprop hours |
| PC-24 annual hours | ~900 hrs/yr | FAA GA Survey Ch6 (airframe hours for light jet) | PARSE Ch6 for jet category |
| Flights per day | Poisson(2.1) | Derived: 47,800 total flights / 62 aircraft / 365 days = 2.11/day | VALIDATED — matches published figure |
| Average leg duration PC-12 | Normal(1.1h, 0.35h) | FAA GA Survey Ch3 (hours by use type) / total flights | CHECK against real data |
| Average leg duration PC-24 | Normal(1.5h, 0.4h) | FAA GA Survey Ch3 | CHECK against real data |
| Unscheduled maintenance rate | ~4% per inspection interval | FAA SDRS — count PC-12 SDRs per year / fleet size | PARSE SDRS exports and calculate |
| Component failure distribution | Custom 17-type | FAA SDRS JASC code distribution for PC-12 | COMPARE SDRS JASC codes vs our categories |
| Maintenance downtime (AOG) | 72h × Uniform(0.5-1.8) | Industry benchmark: AOG averages 48-120h | REASONABLE |

### What's Missing From Synthetic Data

| Missing Element | Why It Matters | How to Add |
|----------------|----------------|------------|
| **Aircraft Daily Status table** | Cannot calculate fleet availability without knowing each aircraft's status each day | Generate from flight_logs + maintenance_records: flying → AVAILABLE, maintenance window → IN_MAINTENANCE, else → IDLE |
| **Booking/demand data** | No booking table exists in synthetic data (churn data has flight_activity but no booking layer) | Generate bookings that precede flights by 1-30 days, with some cancellations |
| **Deadhead/empty leg flights** | Current flight_logs don't flag deadhead vs revenue flights | Add passenger_count=0 flights (~15-20% of total) for repositioning |
| **Crew assignment** | No crew data linked to flights | Generate from IOC crew_roster data; assign pilot + copilot per flight |
| **Airport dimension with NASR data** | Current airports are random ICAO codes — no runway/surface data | Parse NASR zip and build proper airport dimension |
| **Cost data in maintenance records** | maintenance_records.csv has labor_hours but no costs; parts_inventory has unit_cost but no consumption linkage | Generate maintenance detail lines with labor ($100-$150/hr) + parts costs + fuel |

### Cross-Dependencies That Should Exist

1. **Utilization → Maintenance**: Higher flight hours should increase wear_pct and trigger more maintenance events. Currently these are generated independently.
2. **Maintenance → Utilization**: Aircraft in maintenance should have zero flights during maintenance window. Currently not enforced — need to block out flight dates during maintenance events.
3. **Seasonality alignment**: Flight seasonal peaks should align with slightly lagged maintenance seasonal peaks (post-summer busy season = fall maintenance surge). Currently independent.
4. **Owner churn ↔ Utilization**: Low-utilization owners should correlate with churn risk. This IS implemented in churn model but not cross-linked to the fleet utilization data.

---

# STEP 5 — Advanced Enhancements

---

## Predictive KPIs

| KPI | Description | Data Required | Differentiation Value |
|-----|-------------|---------------|----------------------|
| **Predicted Next Maintenance Date** | Per aircraft, based on hours/cycles accumulation rate vs next inspection interval | Flight hours trend + component inspection intervals | HIGH — shifts from reactive to proactive |
| **Parts Demand Forecast** | Expected parts consumption next 30/60/90 days based on fleet utilization projection | Historical parts consumption + maintenance schedule + utilization trend | HIGH — directly addresses PlaneSense's 194K parts pain point |
| **Fleet Availability Forecast** | Expected available aircraft next 7 days considering scheduled maintenance | Maintenance schedule + avg TAT by maintenance type | HIGH — IOC dispatch directly uses this |
| **Cost Per Flight Hour Trend with Projection** | Current CPFH + linear/seasonal projection for next quarter | Maintenance cost + flight hours, 12+ months history | MEDIUM — budget planning metric |
| **Component Reliability Score** | Fleet-wide health index per component type based on age, hours, and sensor trends | Sensor readings + component age + maintenance history | HIGH — unique differentiator |

## Early Warning Indicators

| Indicator | Trigger Logic | Dashboard Action |
|-----------|---------------|------------------|
| **Aircraft exceeding utilization threshold** | Hours/day > 8 for 5+ consecutive days | Amber alert on utilization heatmap |
| **Component approaching life limit** | wear_pct > 80% | Red flag on component table |
| **Rising unscheduled maintenance rate** | 30-day rolling unscheduled rate > historical avg + 1σ | Trend line turns red |
| **Parts below reorder point** | Quantity < Reorder_Point | Parts availability card turns amber/red |
| **Aircraft idle > 5 days** | No flights for 5+ days, not in maintenance | Idle flag on fleet status |
| **Maintenance TAT exceeding target** | Elapsed hours > target by maintenance type | Open job highlighted in backlog |

## Scenario Simulation Capabilities

1. **"What if we add 5 aircraft?"**: Show utilization impact, maintenance cost projection, facility capacity check
2. **"What if utilization increases 15%?"**: Show maintenance frequency increase, parts demand increase, cost projection
3. **"What if we move 3 aircraft from PSM to BVU?"**: Show regional utilization rebalancing, maintenance facility load shift

## What Differentiates This From a Standard Dashboard

1. **Real FAA data as calibration layer** — not just synthetic; show actual SDRS failure patterns, GA Survey benchmarks, NTSB safety data alongside operational metrics
2. **Cross-domain linking** — utilization drives maintenance drives cost drives availability drives utilization (circular dependency modeled)
3. **Dual-layer storytelling** — "Here's what we know from public data" (layer 1) + "Here's what YOU would see with your data" (layer 2)
4. **Actionable intelligence, not just metrics** — every KPI has a "so what" action: which aircraft to reposition, which part to reorder, which owner is at risk

---

# Summary Scorecard

| Dimension | Current State | Target State | Gap |
|-----------|--------------|--------------|-----|
| Aircraft Dimension | Basic (6/15 fields populated) | Complete (15+ fields, linked to FAA) | LARGE |
| Trip Fact | Structure OK, data empty, missing key fields | Full schema with deadhead, fuel, crew, weather | LARGE |
| Booking Fact | Skeleton only | Complete demand tracking | LARGE |
| Maintenance Job Fact | Minimal (2 types only) | Full maintenance taxonomy with regulatory tracking | MEDIUM-LARGE |
| Maintenance Detail Fact | Good structure, incomplete data | Full cost accounting with JASC codes and parts linkage | MEDIUM |
| Utilization Dashboard | 4/10 readiness | 9/10 with KPI cards, benchmarks, heatmap, availability | LARGE |
| Maintenance Dashboard | 5/10 readiness | 9/10 with CPFH, scheduled/unscheduled split, backlog, compliance | MEDIUM-LARGE |
| Data Model | No star schema defined | Full star schema with 9 dimensions + 6 facts | NOT STARTED |
| Synthetic Data Quality | Good foundation, missing cross-dependencies | Validated against FAA, with availability and booking layers | MEDIUM |

---

# Recommended Next Steps (Priority Order)

1. **Validate synthetic data** against FAA GA Survey Ch3/Ch6 — fix utilization rates if off
2. **Parse FAA SDRS exports** — extract JASC codes and failure distribution for PC-12/PC-24
3. **Generate missing tables**: Aircraft_Daily_Status, Booking, enhanced Trip with deadhead/fuel/crew
4. **Build Dim_Airport** from NASR data (filtered to PlaneSense-relevant airports)
5. **Build Dim_Date** with full time intelligence hierarchy
6. **Regenerate maintenance data** with proper cost detail lines (labor + parts + fuel per job)
7. **Build utilization dashboard prototype** (Python/Streamlit for iteration speed)
8. **Build maintenance dashboard prototype**
9. **Port to Power BI** with proper star schema and DAX measures

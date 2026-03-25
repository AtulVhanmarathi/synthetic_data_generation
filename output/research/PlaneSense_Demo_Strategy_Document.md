# PlaneSense Demo Strategy Document
### Predictive Maintenance & Proactive Flight Scheduling Optimization
**Prepared for internal use | February 2026**

---

## Document Purpose

This document serves as the internal blueprint for building a data science and machine learning demo targeting PlaneSense, Inc. as a prospective client. It is structured in three parts:

1. **Problem Statement Definitions** — Precise framing of the two ML opportunity areas, grounded in the client research report
2. **Public Dataset Audit** — A detailed, fact-checked inventory of every publicly available dataset identified for use in the demo, covering access method, data volume, format, cost, limitations, and fitness for purpose
3. **Synthetic Data Specification & Business Impact Methodology** — How to construct proxy data where real data is unavailable, and how to translate model outputs into client-relevant financial metrics

The overall guiding principle: **we are not pretending to have PlaneSense's data. We are demonstrating the methodology and the business value calculation with publicly available aviation data and calibrated synthetic data, then showing exactly what the model becomes with their actual data.**

---

## Part 1: Problem Statement Definitions

### Track 1 — Predictive Maintenance for Atlas Aircraft Center

#### Business Context
Atlas Aircraft Center (AAC) is PlaneSense's wholly owned FAA Part 145 repair station. It is the exclusive MRO (Maintenance, Repair, and Overhaul) provider for the entire PlaneSense fleet of ~64 Pilatus aircraft (PC-12 turboprops and PC-24 light jets), operating 7 days a week. AAC also holds Pilatus-authorized fleet service and support center status.

The core maintenance challenge PlaneSense faces is the **AOG (Aircraft on Ground) event cascade**. When a component fails unexpectedly:
- A backup aircraft must be repositioned to serve the affected client (generating an uncompensated deadhead flight)
- A technician may need to be dispatched to a remote location
- The specific Pilatus OEM part may not be in stock at AAC, requiring emergency procurement
- The scheduling optimization engine must absorb a sudden, unplanned asset loss in its routing matrix

The client research report explicitly notes that PlaneSense's current parts procurement is "reactive versus predictive" — meaning Atlas monitors inventory thresholds manually and responds to failures rather than anticipating them.

#### The ML Problem
**Remaining Useful Life (RUL) Prediction for high-criticality PC-12/PC-24 components**

Given continuous operational telemetry from a fleet of aircraft (engine cycles, sensor readings, flight hours, environmental conditions), predict the probability distribution of each component's remaining serviceable life with sufficient lead time (target: 30–60 days) to:
1. Pre-order the replacement part to arrive at the exact Atlas hangar during the aircraft's next scheduled downtime window
2. Avoid AOG events through proactive maintenance scheduling
3. Shift MRO from a cost center to a strategic, predictable operational asset

#### Specific Components to Model (Pilatus PC-12)
The Pilatus PC-12 uses a Pratt & Whitney Canada PT6A-67P turboprop engine. High-turnover components include:
- **Starter-generator**: High failure frequency in turboprops, well-documented in FAA SDRS
- **Propeller governor**: Critical for power management, subject to wear
- **Fuel control unit (FCU)**: Complex, precision component, expensive to replace on AOG basis
- **Hot section components** (turbine blades, combustion liner): Managed by cycle limits but subject to accelerated wear
- **Avionics LRUs** (Line Replaceable Units): Increasing failure source as avionics age

#### Success Metrics for the Demo
| Metric | Current State (Reactive) | Target State (Predictive) |
|---|---|---|
| AOG events per quarter | Baseline (unknown without data) | 30–50% reduction |
| Emergency part procurement cost | ~2.5–4x standard price | Near elimination |
| Average AOG resolution time | 4–24 hours | Planned scheduled downtime only |
| Deadhead flights triggered by AOG | Included in baseline deadhead rate | Isolated and quantified |

---

### Track 2 — Proactive Flight Scheduling Optimization

#### Business Context
PlaneSense's scheduling operation is described in the client research report as a "3D scheduling problem" — simultaneously assigning the right aircraft (from a fleet distributed across ~50+ airports at any moment), the right pilots (from 200+ pilots with FAA duty time limits and type-specific currency), and the right routing (to satisfy the 8–12 hour availability guarantee) in response to demand that arrives with extremely short notice.

The financial vulnerability is the **deadhead flight** (also called empty-leg or repositioning flight). Fractional owners pay only an "occupied hourly rate" — they are not billed when the aircraft flies empty to their departure airport. PlaneSense absorbs that cost entirely. With a fleet flying approximately 15 million miles per year, and assuming a typical deadhead ratio of 20–35% (industry average for fractional operators), this represents tens of thousands of deadhead hours annually.

The current scheduling engine is **reactive** — it receives a request and solves the assignment problem backward from that request. The ML upgrade is **proactive** — predicting where clients are likely to request flights before they call, and pre-positioning aircraft overnight to minimize tomorrow's deadhead exposure.

#### The ML Problem (Two-Layer)

**Layer A — Demand Forecasting**: 
Given historical flight request patterns (origin airport, destination airport, date/time, client segment, aircraft type requested), forecast the demand distribution for the next 24–72 hours by geographic zone and time window. Output: a probability heatmap of flight request origins and destinations.

**Layer B — Pre-Positioning Optimization**:
Given the demand forecast from Layer A, the current positions of all 64 aircraft, pilot locations and duty-time availability, and scheduled maintenance windows, solve the overnight pre-positioning problem: where should each aircraft be parked tonight to minimize total expected deadhead miles for tomorrow's flights?

This is a form of the **Stochastic Vehicle Pre-Positioning Problem** — a well-studied problem in operations research with direct ML augmentation possible.

#### Key Constraints that Must Be Modeled
- 8–12 hour SLA guarantee: every flight request must be satisfied within this window
- FAA Part 135 pilot duty time limits: pilots cannot exceed prescribed flight and duty hour limits
- PC-12 vs PC-24 differentiation: not all runways can accept a jet; PC-12 can access ~5,000 airports, PC-24 fewer
- Maintenance windows: aircraft scheduled for Atlas downtime cannot be repositioned
- European interchange: hours may originate from Jetfly/CaptainJet owners (adds demand uncertainty)

#### Success Metrics for the Demo
| Metric | Baseline | Projected Improvement |
|---|---|---|
| Deadhead ratio | ~20–35% of total flight hours | 3–8% reduction (industry benchmark for proactive scheduling) |
| Deadhead hours per year | Estimated 2,000–5,000 hrs | 60–400 hours reduction |
| Cost per deadhead hour (PC-12) | ~$900–$1,100 (fuel + crew + cycles) | Direct dollar savings |
| SLA compliance rate | Currently 100% (guaranteed) | Maintained at 100% |

A 5% reduction in deadhead hours on a fleet of 64 aircraft flying ~250 hours/aircraft/year translates to approximately **$720,000–$1,400,000 in annual savings** at current fuel and operational costs — conservative enough to be credible, material enough to warrant investment.

---

## Part 2: Public Dataset Audit

### Dataset 1 — NASA CMAPSS (Classic)
**Turbofan Engine Simulated Data**

| Attribute | Details |
|---|---|
| **Full Name** | CMAPSS: Commercial Modular Aero-Propulsion System Simulation |
| **Publisher** | NASA Prognostics Center of Excellence (PCoE), Ames Research Center |
| **Primary URL** | https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data |
| **Direct Download** | https://data.nasa.gov/docs/legacy/CMAPSSData.zip |
| **License** | Public Domain (U.S. Government Work) |
| **Cost** | Free |
| **Last Updated** | May 29, 2025 (dataset page); original data published 2008 |
| **Registration Required** | No — direct download, no account needed |

**Data Volume & Format**
| Sub-Dataset | Training Trajectories | Test Trajectories | Operating Conditions | Fault Modes |
|---|---|---|---|---|
| FD001 | 100 engines | 100 engines | 1 (Sea Level) | 1 (HPC Degradation) |
| FD002 | 260 engines | 259 engines | 6 conditions | 1 (HPC Degradation) |
| FD003 | 100 engines | 100 engines | 1 (Sea Level) | 2 (HPC + Fan) |
| FD004 | 248 engines | 249 engines | 6 conditions | 2 (HPC + Fan) |

- **Format**: ZIP-compressed plain text (.txt), space-separated values
- **Schema**: 26 columns per row — unit number, time in cycles, 3 operational settings, 21 sensor measurements
- **Total compressed size**: ~2.1 MB (uncompressed: ~15 MB)
- **Total rows**: ~61,000 training rows + ~13,096 test rows across all four sub-datasets
- **Label**: RUL (Remaining Useful Life) in cycles, provided as a separate ground truth file for test sets

**What the Data Represents**
Each row is one operational cycle of one engine. The engine starts healthy and degrades until failure. Training set goes all the way to failure; test set is truncated before failure (simulating the real-world scenario where you don't know when failure will occur). The 21 sensor channels simulate readings analogous to: EGT (exhaust gas temperature), N1/N2 (fan/core shaft speeds), Ps30 (static pressure), fuel flow, temperature at various stages, vibration proxies.

**Fitness for PlaneSense Demo**
- **Strength**: Gold standard in predictive maintenance research; extensively peer-reviewed; clean, well-labeled data; directly models the RUL prediction problem
- **Limitation**: Models large commercial turbofans (analogous to CFM56 class), NOT the Pratt & Whitney Canada PT6A turboprop on the Pilatus PC-12. The physics differ. However, the degradation patterns and sensor correlation structures are directly analogous — a demo using this data with proper framing ("same methodology, different engine model") is professionally credible
- **How to Use**: Train LSTM or Temporal Fusion Transformer on FD001/FD003 for single-condition scenarios, FD002/FD004 for multi-condition (more realistic). Use as the methodological backbone

---

### Dataset 2 — NASA N-CMAPSS (New CMAPSS)
**Aircraft Engine Run-to-Failure Under Real Flight Conditions**

| Attribute | Details |
|---|---|
| **Full Name** | N-CMAPSS: New Commercial Modular Aero-Propulsion System Simulation |
| **Publisher** | ETH Zürich + NASA Ames Research Center (Arias Chao et al., 2021) |
| **Primary URL** | https://ti.arc.nasa.gov/tech/dash/groups/pcoe/prognostic-data-repository/ |
| **Mirror** | https://data.phmsociety.org/nasa/ |
| **Paper DOI** | https://doi.org/10.3390/data6010005 |
| **License** | CC0 1.0 (Public Domain Dedication) |
| **Cost** | Free |
| **Registration Required** | No |

**Data Volume & Format**
- **Format**: HDF5 (.h5) — structured binary format, readable with Python (h5py, pandas)
- **Number of sub-datasets**: 9 (DS01 through DS08b, with DS08a and DS08b being variants)
- **Approximate total size**: ~4–6 GB across all sub-datasets
- **Structure per file**: Each HDF5 file contains arrays: `W` (4 scenario descriptors), `X_s` (14 measured sensor outputs), `X_v` (14 virtual/unmeasured properties), `T` (14 health parameters / degradation modes), `A` (5 auxiliary variables), `Y` (RUL label), `hs` (health state: healthy/faulty binary), `fc` (fault class)

**Key Improvement Over Classic CMAPSS**
N-CMAPSS simulates **complete realistic flights** (climb + cruise + descent), not just snapshots of cruise phase. The degradation onset is tied to the engine's operational history, not randomly assigned. This makes it significantly more realistic and more closely mirrors what PlaneSense would see in actual PC-12 HUMS (Health and Usage Monitoring System) data.

The 4 scenario descriptors (W): altitude (ft), Mach number, throttle resolver angle (TRA), temperature delta at sea level. These map directly to real flight parameters recorded by the Pilatus PC-12's avionics.

**Fault Modes Included**
- High Pressure Compressor (HPC) efficiency degradation
- Fan efficiency degradation
- High Pressure Turbine (HPT) degradation
- Low Pressure Turbine (LPT) degradation
- Fan blade erosion (DS04+)

**Fitness for PlaneSense Demo**
- **Strength**: Most realistic publicly available engine degradation dataset; models full flight profiles including climb/cruise/descent exactly as a Pilatus aircraft would experience; CC0 license means zero restriction on commercial demo use
- **Limitation**: Still models a large commercial turbofan, not the PT6A turboprop. However, the flight condition modeling and RUL prediction framework are directly transferable
- **How to Use**: Preferred over classic CMAPSS for the demo — the realistic flight condition simulation allows you to show PlaneSense that the model can be retrained with their HUMS data mapped to the same schema. Use DS01 for a clean single-fault demo, DS04+ for multi-fault diagnostic capability

---

### Dataset 3 — FAA Service Difficulty Reporting System (SDRS)
**Real-World Aircraft Component Failure Reports**

| Attribute | Details |
|---|---|
| **Full Name** | FAA Service Difficulty Reporting System |
| **Publisher** | Federal Aviation Administration |
| **Query Portal** | https://sdrs.faa.gov/Query.aspx |
| **Bulk Download** | https://av-info.faa.gov/dd_sublevel.asp?Folder=%5CSDRS |
| **License** | U.S. Government public domain |
| **Cost** | Free |
| **Registration Required** | No |

**Data Volume & Format**
- **Format**: Fixed-width text files (.dat / .txt), organized by year and operator type
- **Operator types**: `a` = Air Carrier, `g` = General Aviation (Part 135 / fractional fits here)
- **File sizes**: 658 KB – 8,048 KB per file (compressed ZIP). Approximately 800 MB total uncompressed across all years
- **Year coverage**: Data available from ~1974 to 2024 (latest update June 2024 for the bulk download files)
- **Online query**: Near real-time (recently submitted SDRs available after FAA quality control approval)
- **Schema**: 50+ fields including: aircraft make, aircraft model, aircraft registration, engine make/model, propeller make/model, ATA/JASC component code, part name, part number, difficulty description, date of occurrence, repair description, operator, precautionary procedure, whether failure was in-flight

**How to Query for Pilatus PC-12 Specifically**
The online query at `sdrs.faa.gov/Query.aspx` supports filtering by:
- **Aircraft Make**: "PILATUS" (dropdown)
- **Aircraft Model**: "PC-12" (dropdown — includes all PC-12 variants: PC-12/45, PC-12/47, PC-12/47E, PC-12 NG, PC-12 NGX)
- **JASC/ATA Code**: Can filter by system (e.g., Code 7300 = Engine Fuel, Code 7800 = Engine, Code 6100 = Propeller)
- **Date range**: Any period from database inception to present

Based on public Aviation Safety Network data, there are approximately **73 recorded events** for Pilatus PC-12 in the US in the ASN database. The SDRS, which captures all difficulty reports (not just accidents), will contain significantly more records — estimated 500–2,000 PC-12 specific reports spanning the fleet's operational life in the US.

**Fitness for PlaneSense Demo**
- **Strength**: Real operational failure data for the actual aircraft type (PC-12); provides empirical failure mode distribution (which components fail most frequently); directly usable to calibrate synthetic failure probability distributions; JASC codes map to industry-standard ATA chapter structure that PlaneSense's Atlas CMMS would also use
- **Limitation**: Reports are narrative/descriptive; not time-series sensor data. Useful for failure mode analysis and base rate estimation, not for training a sequential degradation model
- **How to Use**: Analyze PC-12 SDRS records to produce a **failure mode frequency table** (which components fail most often, at what flight hours). Use this as the prior distribution when generating synthetic maintenance event data calibrated to the PlaneSense fleet

---

### Dataset 4 — OpenSky Network (ADS-B Historical Flight Data)
**Real Flight Tracking Data for Pilatus Aircraft**

| Attribute | Details |
|---|---|
| **Full Name** | OpenSky Network Historical ADS-B Dataset |
| **Publisher** | OpenSky Network (non-profit, University of Kaiserslautern + EUROCONTROL) |
| **Website** | https://opensky-network.org |
| **Historical Database** | https://opensky-network.org/data/trino (Trino SQL interface) |
| **Scientific Datasets** | https://opensky-network.org/data/scientific |
| **Aircraft Database** | https://opensky-network.org/data/aircraft |
| **License** | Free for research (university-affiliated, governmental, non-profit); commercial entities require a license |
| **Cost** | Free for qualifying research use |

**Access Eligibility Assessment for Demo Use**
This is the most important nuance: OpenSky's full Trino historical database is restricted to:
- University-affiliated researchers
- Governmental organizations
- Aviation authorities

A commercial consultancy building a client demo does not natively qualify. **However**, there are two viable paths:
1. **Partner or collaborate with a university researcher** for the data pull — this is common practice and straightforward
2. **Use OpenSky's public Scientific Datasets** — pre-curated datasets that are freely downloadable without restriction, including the Aircraft Metadata Database and weekly 24-hour state vector snapshots

**Data Volume (Trino Database)**
- Coverage: ~2014 to present
- Aircraft tracked: 50,000–100,000+ unique aircraft per day globally
- State vectors: Updated every 1–10 seconds per aircraft
- Estimated total data volume: Multi-petabyte (entire database); practical queries are bounded by time window
- For a Pilatus PC-12 specific query (filter by aircraft type via ICAO24 codes cross-referenced with OpenSky's aircraft metadata database): estimated **several hundred to low thousands of unique PC-12 aircraft** in the US registry, generating millions of position records over a multi-year window
- Data retention: `state_vectors_data4` has unlimited retention; some other tables retain ~1 year

**Data Format (Trino)**
- Access via SQL query interface (Trino), Python libraries (`pyopensky`, `traffic`)
- `state_vectors_data4` columns: ICAO24 hex code, callsign, lat, lon, baro altitude, geo altitude, velocity (m/s), heading (degrees), vertical rate (m/s), on_ground (boolean), squawk, timestamp, last contact
- `flights_data4` columns: ICAO24, callsign, first seen (unix timestamp), last seen, estimated departure airport, estimated arrival airport, day partition key

**How to Query Pilatus PC-12 Data Specifically**
1. Download OpenSky's Aircraft Metadata Database (CSV, ~54-57 MB per monthly snapshot) from `opensky-network.org/data/aircraft`
2. Filter by `typecode = "PC12"` to get all ICAO24 hex codes registered to Pilatus PC-12 aircraft (primarily N-registered US aircraft)
3. Use these ICAO24 codes to query `flights_data4` for a 12–24 month period to get actual origin-destination pairs and flight timing
4. Use `state_vectors_data4` for trajectory data (position at each minute during flight)

**Fitness for PlaneSense Demo**
- **Strength**: Real flight data for the actual aircraft type operating in the actual US airspace; provides empirical origin-destination distributions, ground time patterns, and flight duration baselines; the `on_ground` boolean combined with position data lets you reconstruct fleet positional distributions at any point in time
- **Limitation**: ADS-B coverage is not 100% at low altitude and in remote areas (exactly the areas where PC-12 excels); coverage improves significantly above 5,000 feet. Some rural/uncontrolled airfields in the PlaneSense service area may have data gaps. Also note data outages in 2023 (see retention period notes)
- **How to Use**: Extract ~12 months of PC-12 flight data to build the demand forecasting training dataset (origin ICAO code, destination ICAO code, day of week, month, time of day). Use flight departure/arrival times to model ground dwell distributions. Combine with FAA NASR airport data to add runway characteristics

**Data Gaps to Know**
OpenSky has documented data loss periods:
- 2024-05-20 10:00 UTC → 2024-05-21 05:00 UTC
- 2023-12-02 → 2023-12-05 (3 days)
- 2023-11-15 → 2023-11-16
- 2023-01-18 → 2023-01-23 (5 days)

Avoid these windows in the training dataset.

---

### Dataset 5 — FAA General Aviation and Part 135 Activity Survey (GA Survey)
**Annual Flight Hours and Utilization by Aircraft Type**

| Attribute | Details |
|---|---|
| **Full Name** | FAA General Aviation and Part 135 Activity Survey |
| **Publisher** | Federal Aviation Administration |
| **Primary URL** | https://www.faa.gov/data_research/aviation_data_statistics/general_aviation/cy2024 |
| **Format** | Excel (.xlsx) and PDF tables |
| **License** | U.S. Government public domain |
| **Cost** | Free |
| **Registration Required** | No |
| **Update Frequency** | Annual; CY2024 data published February 6, 2026 |

**Data Volume & Coverage**
- Historical tables go back to 2013 (some to 1978) for trend analysis
- Aircraft type granularity: Fixed-wing single engine, fixed-wing multi-engine, rotorcraft, experimental, turboprop (separate category), jet, etc.
- CY2024 survey released February 6, 2026 — current as of this document

**Key Tables Relevant to PlaneSense Demo**

| Table | Content | Relevance |
|---|---|---|
| Table 1.3 | Total hours flown by aircraft type, 2013–2024 | Baseline utilization rates for turboprop fleet |
| Table 2.1 | Active aircraft + total hours by aircraft type, 2024 | Hours per aircraft per year (calibration for synthetic data) |
| Table 3.1 | Active aircraft by primary use (including **Fractional Ownership** as separate category) | Direct relevance — fractional hours as its own category |
| Table 3.3 | **Fractional ownership hours flown by aircraft type** | Most directly relevant — shows turboprop fractional utilization |
| Table 5.1 | Fuel consumption and average fuel consumption rate by aircraft type | Directly usable for deadhead cost calculation |
| Table 6.1 | Total and average airframe hours for active aircraft by aircraft type | Fleet age and cycle modeling |
| Table 4.1 | IFR vs VFR hours by aircraft type | Relevant for scheduling constraint modeling |

**Key Data Points to Extract for Demo Calibration**
- Average annual hours per active turboprop: Used to set synthetic fleet utilization rate
- Fractional ownership hours for turboprops: Ground truth for fleet size × hours calculation
- Fuel consumption per hour for turboprop: Input to deadhead cost model (combined with published PC-12 fuel burn ~65 gal/hr at cruise)

**Fitness for PlaneSense Demo**
- **Strength**: Official government statistics; directly covers fractional ownership as a distinct category (Table 3.3); contains the exact turboprop utilization data needed to calibrate the synthetic PlaneSense fleet
- **Limitation**: Aggregate statistics at aircraft type level — no individual flight records, no origin-destination data
- **How to Use**: Use Table 3.3 and Table 2.1 to calibrate synthetic fleet parameters (hours per aircraft per year, average flight duration). Use Table 5.1 for fuel cost inputs to the business impact calculator

---

### Dataset 6 — NTSB Aviation Accident Database
**Civil Aviation Accidents and Incidents: 1962–Present**

| Attribute | Details |
|---|---|
| **Full Name** | NTSB Aviation Accident and Incident Database |
| **Publisher** | National Transportation Safety Board |
| **Primary URL** | https://data.ntsb.gov/Pages/home.aspx |
| **Bulk Download** | https://data.ntsb.gov/avdata |
| **Query Interface** | https://www.ntsb.gov/Pages/AviationQueryHelp.aspx |
| **License** | U.S. Government public domain |
| **Cost** | Free |
| **Registration Required** | No |

**Data Volume & Format**
- **Full database download**: `avall.zip` — 89.3 MB compressed (updated April 1, 2025)
- **Historical archive**: `Pre2008.zip` — 154.5 MB compressed (pre-2008 records)
- **Format**: Microsoft Access (.MDB) format — converted to CSV/SQLite for analysis using tools like `mdb-tools` or Python's `pyodbc`
- **Monthly updates**: Individual ZIP files, ~400–840 KB each
- **Coverage**: 1962 to present, all US civil aviation accidents + incidents + some international waters
- **Record count (full database)**: Estimated 80,000–100,000+ events
- **Tables**: Events, Aircraft, Crew, Engines, Findings, Occurrences, Flight Crew Information, Narrative

**Filtering for Pilatus PC-12**
Query fields available:
- `acft_make`: "PILATUS"
- `acft_model`: "PC-12" (will return all variants)
- `ev_type`: ACC (accident) or INC (incident)
- `far_part`: 135 (Part 135 operations, which includes fractional)

Based on Aviation Safety Network data, approximately **73 Pilatus PC-12 events** are recorded in US databases. The full NTSB database will contain more, including incidents that did not rise to accident level.

**Fitness for PlaneSense Demo**
- **Strength**: Real failure and incident narratives with detailed probable cause analysis; includes maintenance-related incidents (e.g., "propeller governor failure during climbout") that directly inform the failure mode library for the predictive maintenance model; covers PC-12 specific component failures across the entire US operational history of the type
- **Limitation**: Accidents and incidents are rare events — the sample size is small (~73–150 PC-12 records). The NTSB database is not a substitute for ongoing health monitoring data; it's a failure mode catalog, not a degradation time series
- **How to Use**: Extract all PC-12 and PC-24 records. Analyze the "Findings" and "Narrative" fields to build a **Pilatus-specific failure mode taxonomy** — categorized by ATA chapter, component, failure mode, and operational phase when failure occurred. This taxonomy informs which components to prioritize in the predictive maintenance model and validates the SDRS-based failure frequency analysis

---

### Dataset 7 — FAA NASR (National Airspace System Resources) Airport Database
**All US Airports Including Private and Unimproved Airstrips**

| Attribute | Details |
|---|---|
| **Full Name** | FAA National Airspace System Resources (NASR) Subscription |
| **Publisher** | Federal Aviation Administration |
| **Primary URL** | https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/ |
| **Direct Download (current)** | Available at the above URL; updated every 28 days |
| **eNASR Query Portal** | https://enasr.faa.gov/eNASR/nasr/Current/Airport |
| **GitHub Mirror** | https://github.com/tlarsendataguy/us_airspace_data |
| **License** | U.S. Government public domain |
| **Cost** | Free |
| **Registration Required** | No |
| **Update Frequency** | Every 28 days (FAA aeronautical cycle) |

**Data Volume & Format**
- **Full NASR ZIP file**: ~50–150 MB (varies by format)
- **Formats available**: Legacy fixed-width TXT (with CSV mapping documentation), AIXM 5.0, AIXM 5.1
- **Airport records**: ~19,700 public-use airports + ~14,000+ private-use airports = ~33,700+ total US landing facilities
- **Key airport fields**: Airport ID (ICAO / FAA LID), name, city, state, latitude, longitude, elevation (MSL), runway count, runway length (ft), runway width (ft), runway surface type (HARD/TURF/GRAVEL/DIRT/CORAL/etc.), airport ownership (public/private), control tower (Y/N), CTAF frequency, available services

**Why Surface Type Matters for PlaneSense**
The PC-12's defining operational advantage is access to unimproved runways (grass, dirt, crushed coral). The NASR database contains the `surface_type` field for every runway, allowing the demo to:
1. Classify the ~5,000 airports accessible to the PC-12 vs the ~1,500 accessible to the PC-24 jet
2. Build the geographic accessibility matrix used in the scheduling optimization
3. Visualize the PlaneSense operational advantage versus competitors limited to hard-surface runways

**Fitness for PlaneSense Demo**
- **Strength**: Complete and authoritative; updated every 28 days; contains exactly the runway surface and dimension data needed to replicate PlaneSense's aircraft-airport compatibility matrix; free with no restrictions
- **Limitation**: Does not include private airstrips that are not registered with FAA (some ultra-high-net-worth client destinations may be unregistered). Does not include real-time airport operational status (NOTAMs are a separate system)
- **How to Use**: Download the current 28-day subscription. Parse the APT (Airport) and RWY (Runway) data files. Filter to airports with at least one runway accessible to PC-12 (length ≥ 2,500 ft, surface type includes TURF/GRVL/DIRT). Use this as the airport node set for the scheduling optimization graph. Overlay with demand data from OpenSky to identify high-demand PC-12 accessible airports for the heatmap visualization

---

### Dataset Readiness Summary

| Dataset | Cost | Registration | Access Complexity | Data Volume | Demo Role | Ready to Use? |
|---|---|---|---|---|---|---|
| NASA CMAPSS (Classic) | Free | None | Direct download | ~15 MB | PM model backbone | ✅ Immediate |
| NASA N-CMAPSS | Free | None | Direct download (HDF5) | ~4–6 GB | PM model backbone (preferred) | ✅ Immediate |
| FAA SDRS | Free | None | Web query + bulk download | ~800 MB | Failure mode calibration | ✅ Immediate |
| OpenSky Network (Trino) | Free (research) | Account + application | SQL query interface | Petabytes (query-bounded) | Demand forecasting training | ⚠️ Apply first (1–3 days) |
| OpenSky Scientific Datasets | Free | None | Direct download | ~54–57 MB (metadata CSV) | Aircraft ICAO lookup | ✅ Immediate |
| FAA GA Survey CY2024 | Free | None | Direct download (Excel) | <10 MB | Fleet calibration | ✅ Immediate |
| NTSB Accident Database | Free | None | Direct download (MDB) | ~89 MB compressed | Failure mode taxonomy | ✅ Immediate |
| FAA NASR Airport DB | Free | None | Direct download (ZIP/TXT) | ~50–150 MB | Airport graph (scheduling) | ✅ Immediate |

**Recommended first action**: Apply for OpenSky Trino access immediately (it takes 1–3 business days for approval) while the rest of the demo build proceeds using the immediately available datasets.

---

## Part 3: Synthetic Data Specification & Business Impact Methodology

### 3A — Synthetic Data Specification: Predictive Maintenance Track

The goal is to construct a synthetic maintenance dataset that mirrors what PlaneSense's Atlas Aircraft Center would realistically possess in their CMMS (Computerized Maintenance Management System).

#### Synthetic Dataset: "Atlas Fleet Maintenance Logs"

**Fleet Parameters (calibrated from FAA GA Survey and client research)**
- Fleet size: 64 aircraft (45 PC-12, 19 PC-24)
- Simulation period: 5 years of operational history (2019–2024)
- Average annual hours per aircraft: 300 hours/year (turboprop fractional average per FAA GA Survey Table 2.1, conservative for a heavily utilized fractional fleet)
- Average flight duration: 1.8 hours (consistent with short-field, regional PC-12 operations)
- Implied annual flights per aircraft: ~167 flights/aircraft/year
- Total fleet flight cycles over 5 years: 64 × 167 × 5 = ~53,440 flight events

**Synthetic Variables to Generate**

*Per-flight record (53,440 rows):*
| Column | Type | Distribution / Logic |
|---|---|---|
| `flight_id` | String | Unique identifier |
| `tail_number` | String | 64 aircraft, N-prefix registrations |
| `aircraft_type` | Categorical | PC-12 (45) or PC-24 (19) |
| `flight_date` | Date | 2019-01-01 to 2024-12-31 |
| `departure_icao` | String | Sampled from NASR airport list (weighted by OpenSky demand data) |
| `arrival_icao` | String | Same |
| `flight_hours` | Float | Lognormal(μ=1.8, σ=0.6), capped at 5.5 hrs |
| `cycle_count` | Integer | Cumulative per tail number |
| `total_airframe_hours` | Float | Cumulative |
| `fuel_consumed_gal` | Float | flight_hours × N(65, 5) for PC-12 |
| `egt_max_degC` | Float | Multivariate normal, correlated with age and degradation state |
| `n1_max_pct` | Float | Same |
| `oil_pressure_psi` | Float | Same |
| `vibration_ips` | Float | Gamma distribution, increases with wear |
| `engine_health_index` | Float | 1.0 (healthy) → 0 (failure), degrading trajectory with noise |

*Per-maintenance-event record (generated from failure model):*
| Column | Type | Source |
|---|---|---|
| `tail_number` | String | From flight log |
| `event_date` | Date | Triggered by degradation model |
| `ata_chapter` | String | From SDRS failure mode distribution (e.g., 73 = fuel, 61 = propeller) |
| `component_name` | String | From SDRS/NTSB failure taxonomy |
| `event_type` | Categorical | Scheduled / Unscheduled (AOG) |
| `part_number` | String | Pilatus IPC (Illustrated Parts Catalog) reference |
| `labor_hours` | Float | From historical MRO benchmark data |
| `parts_cost_usd` | Float | Modeled from Pilatus spare parts pricing (publicly quoted) |
| `aog_flag` | Boolean | True if event was unscheduled/forced |
| `downtime_hours` | Float | Hours aircraft was grounded |

**Failure Rate Calibration**
Using FAA SDRS data for PC-12 failures, assign annual failure probabilities per component category. Example calibration targets:
- Starter-generator: ~0.15 events/aircraft/year
- Propeller governor: ~0.08 events/aircraft/year
- Fuel control unit: ~0.04 events/aircraft/year
- Avionics LRU: ~0.12 events/aircraft/year
- Hot section inspection trigger: every 3,500–4,000 cycles (Pratt & Whitney PT6A TBO)

These rates produce a dataset with a realistic mixture of scheduled maintenance, proactive replacements, and AOG events — enabling the model to learn the difference.

---

### 3B — Synthetic Data Specification: Scheduling Optimization Track

#### Synthetic Dataset: "PlaneSense Flight Demand and Fleet Position Log"

The data-generating process:
1. Use real PC-12 ADS-B data from OpenSky to identify empirical origin-destination pairs and demand patterns
2. Scale these patterns to PlaneSense's fleet size and guaranteed-availability service model
3. Add the scheduling constraints (SLA window, pilot duty time, maintenance) as metadata

**Demand Data (calibrated from OpenSky ADS-B)**

*Per-flight-request record (~53,440 over 5 years):*
| Column | Type | Source/Distribution |
|---|---|---|
| `request_id` | String | Unique |
| `request_datetime` | Datetime | Derived from OpenSky PC-12 flight departure times (empirical) |
| `client_segment` | Categorical | Fractional owner / CobaltPass / Sourcing Solutions |
| `departure_icao` | String | From OpenSky PC-12 origin airports |
| `arrival_icao` | String | From OpenSky PC-12 destination airports |
| `pax_count` | Integer | Uniform(1, 8) for PC-12; Uniform(1, 8) for PC-24 |
| `preferred_aircraft_type` | Categorical | PC-12 / PC-24 / No preference |
| `arrival_latest` | Datetime | request_datetime + U(8, 12) hours (SLA window) |
| `booked_lead_time_hours` | Float | Exponential(λ=0.15), most bookings 8–48 hours ahead |

**Fleet State Data (per 1-hour snapshot, 5 years × 8,760 hrs = 560,640 snapshots):**
| Column | Type | Distribution / Logic |
|---|---|---|
| `snapshot_datetime` | Datetime | Hourly |
| `tail_number` | String | 64 rows per snapshot |
| `current_icao` | String | Airport where aircraft is located |
| `status` | Categorical | Available / Airborne / Maintenance / Repositioning |
| `pilot_id_assigned` | String | From pilot roster (200+ pilots) |
| `duty_hours_used` | Float | Cumulative per 24hr period, FAA Part 135 limits |
| `next_maintenance_due_hours` | Float | Time to next scheduled maintenance |
| `fuel_state_gal` | Float | Available fuel |

**Feature Engineering for Demand Forecasting Layer**
From the above raw data, engineer:
- `day_of_week` (0–6)
- `month` (1–12)
- `is_holiday` (US federal + major vacation holidays)
- `week_of_year` (1–52)
- `departure_state_region` (Northeast / Southeast / Midwest / Southwest / Mountain / Pacific)
- `destination_state_region` (same)
- `avg_demand_same_weekday_last_4_weeks` (rolling feature)
- `local_events_flag` (major golf tournaments, sporting events near destination — optionally augmented with public event data)

---

### 3C — Business Impact Calculation Methodology

This section defines the exact formulas to use when translating model outputs into dollar figures for the PlaneSense C-suite.

#### Predictive Maintenance Impact Model

**Cost of an AOG Event (per occurrence)**

| Cost Component | Formula | Approximate Value (PC-12) |
|---|---|---|
| Emergency part procurement premium | Standard part cost × 2.5 (emergency sourcing multiplier) | $2,000–$15,000 depending on component |
| Technician dispatch to remote location | Travel + labor hours × $85/hr (A&P rate) + per diem | $800–$4,000 |
| Backup aircraft deadhead to cover client | Deadhead_miles ÷ cruise_speed × ($900–$1,100/hr) | $450–$3,300 per deadhead flight |
| Revenue impact from unplanned downtime | Grounded_hours × avg_occupied_hourly_rate | $1,200–$2,000/hr grounded |
| Client service impact | Qualitative (brand risk on 91% retention model) | Not quantified in demo |

**Conservative per-AOG-event cost: $5,000–$25,000**

**Predictive Maintenance ROI Calculation:**
```
Annual AOG events (baseline) = Fleet_size × AOG_rate_per_aircraft_per_year
                              = 64 × 0.8 = ~51 AOG events/year (estimated)

Model_reduction_rate = 35% (conservative; literature shows 30–50% for comparable applications)

AOG_events_prevented = 51 × 0.35 = ~18 events/year

Annual_savings = 18 × avg_AOG_cost
               = 18 × $12,500 (mid-range estimate)
               = $225,000/year
```

**Additionally quantify:**
- Reduction in emergency parts premium: Proactive orders at standard price vs. AOG emergency price
- Reduction in excess inventory capital: Leaner safety stock because demand is predictable
- Increased fleet utilization: Hours of grounded time recovered

#### Scheduling Optimization Impact Model

**Cost of a Deadhead Hour (PC-12)**
| Cost Component | Value |
|---|---|
| Jet-A fuel (PC-12 burns ~65 gal/hr at cruise) | 65 × $5.50/gal = ~$357/hr |
| Crew cost (pro-rated, pilot salary + benefits) | ~$200–$280/hr |
| Engine cycle reserve (PT6A overhaul reserve) | ~$150–$200/hr |
| Aircraft maintenance reserve | ~$50–$80/hr |
| **Total cost per deadhead hour (PC-12)** | **~$757–$917/hr** |
| **Total cost per deadhead hour (PC-24)** | **~$1,100–$1,500/hr** (jet fuel, higher cycle cost) |

**Deadhead Reduction ROI Calculation:**
```
Total fleet annual flight hours = 64 aircraft × 300 hrs/year = 19,200 hrs/year
Deadhead ratio (industry benchmark for fractional) = 25%
Current annual deadhead hours = 19,200 × 0.25 = 4,800 hrs/year

Model_reduction = 5% (conservative; proactive pre-positioning literature: 4–8%)
Deadhead_hours_saved = 4,800 × 0.05 = 240 hrs/year

Cost_saved = 240 × $837 (blended PC-12/PC-24 average)
           = $200,880/year

At 8% reduction = $384,000/year
At 10% reduction = $480,000/year
```

**For context to PlaneSense:** The client research document references 15 million miles flown annually. At ~270 knots average cruise = ~55,555 flight hours. The 19,200 hours above likely undercounts if this includes repositioning. Scaling to 55,555 hours total (including deadheads):
```
Deadhead hours (25% of total) = 13,889 hrs/year
5% reduction = 694 hrs saved × $837 = $581,000/year
10% reduction = 1,389 hrs × $837 = $1,162,000/year
```

This is the more credible range to present. Even the lower bound ($580K/year) represents a 3–5× return on a reasonable technology investment within Year 1.

---

### 3D — "What Becomes Possible With Your Real Data" Narrative

This is the closing argument for each demo section — making explicit what the proxy demo cannot capture, and why PlaneSense's proprietary data is the unlock.

**For Predictive Maintenance:**
> "Everything you've seen today was built on publicly available turbofan engine simulation data. The model architecture, the RUL prediction framework, and the business impact calculation are all valid and proven. What you have that we don't is 30 years of PT6A engine telemetry from 64 Pilatus aircraft, Atlas work order records with actual failure-to-prevention ratios, and HUMS data from the PC-12's digital engine monitoring system. The moment that data feeds this model, the RUL curves stop being generic turbofan curves and start being specific to your exact aircraft, your specific operational profiles — flying into crushed coral runways in the Bahamas versus 3,000-foot grass strips in Vermont. That's where generic predictive maintenance becomes PlaneSense-specific competitive advantage."

**For Scheduling Optimization:**
> "The demand forecasting layer you saw today was trained on public ADS-B data from Pilatus PC-12 aircraft across the US — real planes, real routes, real patterns. But it's not your data. Your Gözen Operator platform has recorded every flight request, every 12-hour notice booking, every seasonal surge around golf season in the Southeast and foliage season in New England, every time a corporate client's board meeting pattern drove a cluster of Thursday evening departures. That pattern library is worth more to this model than anything we can build from public data. The optimization layer improves by an order of magnitude when it learns from your clients' actual behavior, not aggregate US PC-12 patterns. What you're seeing today is a lower bound on what this system becomes."

---

## Appendix: Immediate Action Items

| Action | Owner | Timeline | Notes |
|---|---|---|---|
| Apply for OpenSky Trino access | Data Engineer | Day 1 | Account registration at opensky-network.org/my-opensky/request-data |
| Download NASA N-CMAPSS datasets (DS01, DS03, DS04) | Data Engineer | Day 1 | From ti.arc.nasa.gov/tech/dash/groups/pcoe/prognostic-data-repository/ |
| Download FAA SDRS bulk files (General Aviation) | Data Engineer | Day 1 | From av-info.faa.gov/dd_sublevel.asp?Folder=%5CSDRS |
| Download NTSB full database (avall.zip) | Data Engineer | Day 1 | From data.ntsb.gov/avdata |
| Download FAA NASR current 28-day subscription | Data Engineer | Day 1 | From faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/ |
| Download FAA GA Survey CY2024 Excel files | Data Analyst | Day 1 | From faa.gov/data_research/aviation_data_statistics/general_aviation/cy2024 |
| Query SDRS for Pilatus PC-12 records | Data Analyst | Day 2 | Use sdrs.faa.gov/Query.aspx; filter Aircraft Make = PILATUS, Model = PC-12 |
| Build failure mode taxonomy from SDRS + NTSB | Data Scientist | Day 3–5 | Categorize by ATA chapter; produce frequency table |
| Pull PC-12 ICAO24 list from OpenSky aircraft metadata | Data Engineer | Day 3 (post-access) | Filter typecode = "PC12" from aircraft metadata CSV |
| Pull 12-month PC-12 flight history from OpenSky Trino | Data Engineer | Day 4 (post-access) | Join flights_data4 with PC-12 ICAO24 list |
| Generate synthetic Atlas maintenance dataset | Data Scientist | Week 2 | Using calibration from FAA GA Survey + SDRS failure rates |
| Begin N-CMAPSS RUL model development | Data Scientist | Week 2 | Start with DS01 for clean baseline, then DS04 for multi-fault |
| Build airport accessibility matrix (NASR + PC-12 specs) | Data Engineer | Week 2 | Filter runways ≥ 2,500 ft, include non-paved surface types |

---

*Document version: 1.1 | Prepared February 2026 | Internal use only — do not share with client prior to demo*

---

## Part 4: Strategic Intelligence Log
### Key Signals from Research & Internal Discussion

This section records only high-signal findings, decisions, and strategic conclusions distilled from the research process and internal discussion. It is a living record — update as new insights emerge.

---

### Signal 1 — Source of Client Intelligence
**Context:** All client knowledge originates from a single Gemini deep research output generated by pointing the model at PlaneSense's and the consultancy's public websites. There is no proprietary data, no NDA, no direct client conversation yet.

**Implication:** Every claim made in this document is inference from public sources, not confirmed ground truth. Present the demo as "built from public data to demonstrate methodology" — this is a strength (shows initiative) not a weakness.

---

### Signal 2 — Number Validation: 15M Miles and 47,800 Flights
**What the report states:** 15 million miles flown annually; fleet of ~64 aircraft.

**47,800 flights/year cross-check:**
- 47,800 ÷ 64 aircraft = ~747 flights/aircraft/year
- 15,000,000 miles ÷ 47,800 flights = ~314 miles/flight average (~1 hour at PC-12 cruise of 311 mph)
- 747 flights × ~1 hr = ~750 hours/aircraft/year — significantly above FAA GA Survey average of 300–500 hrs for fractional turboprops

**Verdict:** Numbers are self-consistent but on the high end. Most likely explanation: the 15M miles includes deadhead repositioning flights (not just client-occupied miles), and may include Sourcing Solutions / Jetfly interchange activity — not just the 64-aircraft core fleet. **Do not present as precise facts in the demo.** If challenged, frame it as a public figure to be validated against their actual dispatch data.

---

### Signal 3 — Predictive Maintenance: What They Already Do vs. the Gap
**What they almost certainly do today:**
- TBO (Time Between Overhaul) based scheduled replacement — PT6A TBO is ~3,600 cycles; replace at the clock, not at the signal
- CAMP or equivalent CMMS for compliance-driven component life tracking
- PC-12 NGX HUMS (Health Usage Monitoring System) streams basic engine parameters — used for compliance tracking, not ML anomaly detection

**What they almost certainly do NOT do:**
- ML-based degradation modeling that detects components trending toward failure *before* TBO threshold
- Per-tail-number condition scoring that accounts for each aircraft's specific operational profile (remote runways, altitude cycling, dust environments)
- Probabilistic RUL prediction with confidence intervals driving parts procurement timing

**Key evidence from the report:** The discovery question "How much of your current parts procurement is reactive versus predictive?" is listed as something the consultancy needs to *ask* — if they were doing it well, the report would have called it out as a current capability. Language like "manual inventory thresholds" and "reactive purchasing" further confirms the gap.

**The correct demo framing:** Not "we'll build you predictive maintenance." Instead: "Condition-based prognostics using your HUMS sensor streams — not replacing your TBO schedule, but catching the 15% of failures that happen *before* TBO triggers, and safely extending the 20% of components that are healthy beyond TBO."

---

### Signal 4 — Scheduling Optimization: What They Already Do vs. the Gap
**What they already have (important — do not pitch as new):**
- A custom mathematical scheduling engine co-developed with university mathematicians
- Gözen's Operator platform for dispatch and flight planning
- Dynamic scheduling within a 12–48 hour reactive window

**This is a sophisticated system.** Pitching "scheduling optimization" generically will kill credibility in the room.

**What they do NOT have:**
- A demand forecasting layer that extends the planning horizon beyond 12–48 hours
- Probabilistic prediction of where/when clients will request flights based on historical seasonality, local events, corporate travel patterns
- An overnight pre-positioning model that answers "where should each of the 64 aircraft park tonight to minimize tomorrow's deadhead exposure before requests arrive"

**The correct demo framing:** Not "scheduling optimization." Instead: "Demand forecasting to extend your scheduling horizon from 12–48 hours to 5–7 days — not replacing Gözen, but giving dispatchers a forward-looking demand map that Gözen doesn't have today." Gözen optimizes given current inputs; this improves the *inputs* to Gözen.

---

### Signal 5 — The Correct Wedge for Both Tracks
**Single unifying message:** Both ML opportunities are about **time horizon extension and data depth**, not about replacing existing systems.

| Track | Current State | ML Extension |
|---|---|---|
| Maintenance | Replace at TBO clock (rules-based) | Detect anomalous degradation before the clock triggers (signal-based) |
| Scheduling | Optimize given today's requests (reactive) | Pre-position based on predicted demand 5–7 days ahead (proactive) |

Both tracks position the consultancy as additive to Atlas Aircraft Center's current investments and Gözen Operator — which is explicitly the correct posture per the client engagement strategy in the research report. Never suggest replacing these systems.

---

### Signal 6 — CIO Profile and the Right Hook
**CIO:** Mandar Pendse

**Publicly stated priorities (from the report):**
- "Data is everything" — direct quote
- Cloud ERP migration and finance automation actively underway
- Mobile app for shareowners in development
- Explicitly wants to shift from descriptive reporting to predictive analytics

**What will NOT interest him:** Generic AI/ML pitch, "supply chain optimization" as a broad concept, anything that sounds like a standard IT project.

**What WILL interest him:** Showing that data PlaneSense already generates and owns (HUMS telemetry, dispatch logs, maintenance work orders) is currently producing zero intelligence beyond compliance reporting — and that a specific, narrow ML layer on top of existing systems produces a quantified dollar outcome. The hook is: *you already have the data; you're just not yet using it to see 5 days ahead.*

---

### Signal 7 — Dataset Access Priority Matrix
| Dataset | Access Status | First Action |
|---|---|---|
| NASA N-CMAPSS | Free, immediate | Download DS01, DS03, DS04 from ti.arc.nasa.gov |
| FAA SDRS | Free, immediate | Query sdrs.faa.gov for Pilatus PC-12 records; also download bulk GA files |
| NTSB Database | Free, immediate | Download avall.zip from data.ntsb.gov/avdata |
| FAA GA Survey CY2024 | Free, immediate | Download Tables 2.1, 3.3, 5.1 from faa.gov GA survey page |
| FAA NASR Airport DB | Free, immediate | Download current 28-day subscription ZIP |
| OpenSky Aircraft Metadata | Free, immediate | Download monthly CSV snapshot (~55 MB); filter typecode = "PC12" for ICAO24 list |
| OpenSky Trino (flight history) | Free for research — apply first | Apply at opensky-network.org/my-opensky/request-data; approval 1–3 days |

**Critical note on OpenSky:** The full historical flight tracking database (the data needed for origin-destination demand modeling) requires an account application. Apply on Day 1. All other datasets are unblocked immediately.

---

### Signal 8 — What to Avoid in the Demo Presentation
1. **Do not claim the scheduling model replaces Gözen Operator.** They have recently invested heavily in it. Frame as a demand intelligence input layer that feeds Gözen better data.
2. **Do not use airline (Part 121) datasets** and claim they represent fractional Part 135/91K operations. The scheduling physics are fundamentally different — no fixed routes, 12-hour demand horizon, remote runways.
3. **Do not present the 15M miles / 47,800 flights as hard facts.** They are likely inclusive of deadheads and ancillary operations. Use them as order-of-magnitude calibration only.
4. **Do not pitch generic supply chain or predictive maintenance.** Anchor every claim to the Pilatus PC-12 / PT6A turboprop specifically — failure modes, runway profiles, component names. Generic pitches immediately signal lack of domain depth.
5. **Do not call it "AI."** Per the report's engagement strategy, sell business outcomes: "Autonomous Parts Procurement Agent," "Forward Demand Map," "Fleet Health Score by Tail Number." These are the language patterns that resonate with operations-focused aviation executives.

---

### Signal 9 — The Closing Argument Structure (for Demo Day)
Each demo track should close with the same three-beat structure:

**Beat 1 — What we built (the methodology):**
"Here is the model, trained on publicly available Pilatus operational data and NASA engine simulation datasets."

**Beat 2 — What it produces (the business outcome):**
"At conservative assumptions, this produces [X dollars saved per year / Y AOG events prevented] for a fleet of your size."

**Beat 3 — What your data unlocks (the ask):**
"Everything you've seen today is a lower bound. Your Gözen dispatch logs, your Atlas work order history, your HUMS telemetry — that data makes this model specific to your fleet, your clients, your routes. We would like to show you what it looks like with your data."

Beat 3 is the bridge from demo to engagement. It is not a sales pitch — it is a logical extension of what was just demonstrated.

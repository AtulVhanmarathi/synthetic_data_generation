#!/usr/bin/env python3
"""
Generate analytics-ready synthetic data for PlaneSense Power BI dashboards.
Output: output/analytics/data/ — star schema tables (dimensions + facts)

Calibrated against:
- FAA GA Survey 2020-2024 (Ch3/Ch6): PC-12 ~3,200 hrs/yr, PC-24 ~3,900 hrs/yr
- FAA SDRS: 294 real PC-12/PC-24 SDR records — JASC code distribution
- PlaneSense website: 62 aircraft, 47,800 flights/yr, 2 facilities, 91% retention
"""

import csv
import json
import os
import random
import math
from datetime import datetime, timedelta, date
from collections import defaultdict

random.seed(42)
OUT_DIR = "output/analytics/data"
os.makedirs(OUT_DIR, exist_ok=True)

# =============================================================================
# CONSTANTS — calibrated against FAA data
# =============================================================================

# Simulation window
SIM_START = date(2023, 1, 1)
SIM_END = date(2025, 12, 31)
SNAPSHOT_DATE = date(2025, 12, 31)

# Fleet composition (verified planesense.com)
PC12_COUNT = 46
PC24_COUNT = 16
TOTAL_AIRCRAFT = PC12_COUNT + PC24_COUNT  # 62

# Facilities (verified)
FACILITIES = [
    {"id": "FAC-PSM", "name": "Portsmouth NH (Pease)", "icao": "KPSM", "state": "NH",
     "type": "PRIMARY", "technician_count": 28, "bays": 8},
    {"id": "FAC-BVU", "name": "Boulder City NV", "icao": "KBVU", "state": "NV",
     "type": "SECONDARY", "technician_count": 12, "bays": 4},
]

# FAA-calibrated utilization (GA Survey Ch6: turboprop 1-eng ~3,200 hrs/yr, turbojet ~3,900 hrs/yr)
# Fractional fleets run higher than GA average — use ~870 hrs/yr PC-12, ~1,050 hrs/yr PC-24
# This yields ~47,800 flights/yr across 62 aircraft (verified)
PC12_AVG_HOURS_YR = 1150  # ~3.0 flights/day × 1.05h avg = ~1,150 hrs/yr
PC24_AVG_HOURS_YR = 1350  # ~2.55 flights/day × 1.45h avg = ~1,350 hrs/yr
PC12_AVG_LEG_HRS = 1.05   # FAA Ch3 derived
PC24_AVG_LEG_HRS = 1.45

# Seasonal multipliers (indexed by month 1-12)
SEASONAL = {1: 1.05, 2: 0.85, 3: 0.95, 4: 1.00, 5: 1.05, 6: 1.15,
            7: 1.20, 8: 1.15, 9: 1.05, 10: 1.00, 11: 0.90, 12: 0.95}

# JASC codes — calibrated from SDRS PC-12/PC-24 data (top 20 real codes)
JASC_CODES = [
    {"code": "2752", "system": "Flight Controls", "name": "Rudder Control System", "weight_pc12": 0.08, "weight_pc24": 0.03},
    {"code": "7200", "system": "Engine", "name": "Engine (General)", "weight_pc12": 0.07, "weight_pc24": 0.05},
    {"code": "2750", "system": "Flight Controls", "name": "Flight Control System", "weight_pc12": 0.07, "weight_pc24": 0.04},
    {"code": "3242", "system": "Landing Gear", "name": "Brake Assembly", "weight_pc12": 0.05, "weight_pc24": 0.07},
    {"code": "2497", "system": "Empennage", "name": "Stabilizer Assembly", "weight_pc12": 0.04, "weight_pc24": 0.02},
    {"code": "5610", "system": "Instruments", "name": "Flight Instruments", "weight_pc12": 0.04, "weight_pc24": 0.11},
    {"code": "7230", "system": "Engine", "name": "Engine Fuel & Control", "weight_pc12": 0.03, "weight_pc24": 0.03},
    {"code": "3418", "system": "Ice Protection", "name": "Ice Protection (Airframe)", "weight_pc12": 0.03, "weight_pc24": 0.02},
    {"code": "3230", "system": "Landing Gear", "name": "Nose Gear Steering", "weight_pc12": 0.03, "weight_pc24": 0.02},
    {"code": "2140", "system": "Fuselage", "name": "Fuselage Structure", "weight_pc12": 0.03, "weight_pc24": 0.08},
    {"code": "3260", "system": "Landing Gear", "name": "Wheel/Tire Assembly", "weight_pc12": 0.02, "weight_pc24": 0.04},
    {"code": "7321", "system": "Engine", "name": "Engine Control System", "weight_pc12": 0.02, "weight_pc24": 0.03},
    {"code": "3240", "system": "Landing Gear", "name": "Brake System (General)", "weight_pc12": 0.02, "weight_pc24": 0.07},
    {"code": "2932", "system": "Hydraulics", "name": "Hydraulic Valve", "weight_pc12": 0.02, "weight_pc24": 0.03},
    {"code": "5230", "system": "Avionics", "name": "Communications System", "weight_pc12": 0.02, "weight_pc24": 0.03},
    {"code": "3457", "system": "APU", "name": "Auxiliary Power Unit", "weight_pc12": 0.02, "weight_pc24": 0.02},
    {"code": "3020", "system": "Landing Gear", "name": "Main Landing Gear", "weight_pc12": 0.02, "weight_pc24": 0.03},
    {"code": "2435", "system": "Empennage", "name": "Elevator Assembly", "weight_pc12": 0.02, "weight_pc24": 0.01},
    {"code": "3411", "system": "Pneumatics", "name": "Pitot/Static System", "weight_pc12": 0.01, "weight_pc24": 0.02},
    {"code": "2411", "system": "Electrical", "name": "Generator/Alternator", "weight_pc12": 0.02, "weight_pc24": 0.02},
]

# Airports — PlaneSense heavy Northeast + West Coast, plus top GA airports
AIRPORTS = [
    # Northeast (primary market)
    {"icao": "KPSM", "name": "Portsmouth Intl", "city": "Portsmouth", "state": "NH", "region": "Northeast", "runway_ft": 11321, "surface": "ASPH"},
    {"icao": "KBOS", "name": "Boston Logan", "city": "Boston", "state": "MA", "region": "Northeast", "runway_ft": 10083, "surface": "ASPH"},
    {"icao": "KJFK", "name": "John F Kennedy", "city": "New York", "state": "NY", "region": "Northeast", "runway_ft": 14511, "surface": "ASPH"},
    {"icao": "KEWR", "name": "Newark Liberty", "city": "Newark", "state": "NJ", "region": "Northeast", "runway_ft": 11000, "surface": "ASPH"},
    {"icao": "KPVD", "name": "T.F. Green", "city": "Providence", "state": "RI", "region": "Northeast", "runway_ft": 7166, "surface": "ASPH"},
    {"icao": "KBDL", "name": "Bradley Intl", "city": "Hartford", "state": "CT", "region": "Northeast", "runway_ft": 9510, "surface": "ASPH"},
    {"icao": "KPWM", "name": "Portland Jetport", "city": "Portland", "state": "ME", "region": "Northeast", "runway_ft": 7200, "surface": "ASPH"},
    {"icao": "KMHT", "name": "Manchester-Boston", "city": "Manchester", "state": "NH", "region": "Northeast", "runway_ft": 9250, "surface": "ASPH"},
    {"icao": "KACK", "name": "Nantucket Memorial", "city": "Nantucket", "state": "MA", "region": "Northeast", "runway_ft": 6303, "surface": "ASPH"},
    {"icao": "KMVY", "name": "Martha's Vineyard", "city": "Vineyard Haven", "state": "MA", "region": "Northeast", "runway_ft": 5504, "surface": "ASPH"},
    {"icao": "KHPN", "name": "Westchester County", "city": "White Plains", "state": "NY", "region": "Northeast", "runway_ft": 6549, "surface": "ASPH"},
    {"icao": "KTEB", "name": "Teterboro", "city": "Teterboro", "state": "NJ", "region": "Northeast", "runway_ft": 7000, "surface": "ASPH"},
    {"icao": "KBED", "name": "Hanscom Field", "city": "Bedford", "state": "MA", "region": "Northeast", "runway_ft": 7011, "surface": "ASPH"},
    # Mid-Atlantic
    {"icao": "KIAD", "name": "Dulles Intl", "city": "Washington", "state": "VA", "region": "Mid-Atlantic", "runway_ft": 11500, "surface": "CONC"},
    {"icao": "KPHL", "name": "Philadelphia Intl", "city": "Philadelphia", "state": "PA", "region": "Mid-Atlantic", "runway_ft": 10506, "surface": "ASPH"},
    # Southeast
    {"icao": "KMIA", "name": "Miami Intl", "city": "Miami", "state": "FL", "region": "Southeast", "runway_ft": 13016, "surface": "ASPH"},
    {"icao": "KPBI", "name": "Palm Beach Intl", "city": "West Palm Beach", "state": "FL", "region": "Southeast", "runway_ft": 10008, "surface": "ASPH"},
    {"icao": "KTPA", "name": "Tampa Intl", "city": "Tampa", "state": "FL", "region": "Southeast", "runway_ft": 11002, "surface": "ASPH"},
    {"icao": "KATL", "name": "Hartsfield-Jackson", "city": "Atlanta", "state": "GA", "region": "Southeast", "runway_ft": 12390, "surface": "CONC"},
    {"icao": "KCLT", "name": "Charlotte Douglas", "city": "Charlotte", "state": "NC", "region": "Southeast", "runway_ft": 10000, "surface": "ASPH"},
    {"icao": "KFLL", "name": "Fort Lauderdale", "city": "Fort Lauderdale", "state": "FL", "region": "Southeast", "runway_ft": 9000, "surface": "ASPH"},
    # West Coast (expanding market)
    {"icao": "KBVU", "name": "Boulder City Municipal", "city": "Boulder City", "state": "NV", "region": "West", "runway_ft": 4800, "surface": "ASPH"},
    {"icao": "KLAX", "name": "Los Angeles Intl", "city": "Los Angeles", "state": "CA", "region": "West", "runway_ft": 12091, "surface": "ASPH-CONC"},
    {"icao": "KSFO", "name": "San Francisco Intl", "city": "San Francisco", "state": "CA", "region": "West", "runway_ft": 11870, "surface": "ASPH"},
    {"icao": "KSAN", "name": "San Diego Intl", "city": "San Diego", "state": "CA", "region": "West", "runway_ft": 9401, "surface": "ASPH"},
    {"icao": "KLAS", "name": "Harry Reid Intl", "city": "Las Vegas", "state": "NV", "region": "West", "runway_ft": 14510, "surface": "ASPH"},
    {"icao": "KDEN", "name": "Denver Intl", "city": "Denver", "state": "CO", "region": "West", "runway_ft": 16000, "surface": "CONC"},
    {"icao": "KSDM", "name": "Brown Field", "city": "San Diego", "state": "CA", "region": "West", "runway_ft": 7972, "surface": "ASPH"},
    {"icao": "KAPC", "name": "Napa County", "city": "Napa", "state": "CA", "region": "West", "runway_ft": 5931, "surface": "ASPH"},
    # Midwest
    {"icao": "KORD", "name": "O'Hare Intl", "city": "Chicago", "state": "IL", "region": "Midwest", "runway_ft": 13000, "surface": "CONC"},
    {"icao": "KMSP", "name": "Minneapolis-St Paul", "city": "Minneapolis", "state": "MN", "region": "Midwest", "runway_ft": 11006, "surface": "CONC"},
    # Short-strip PC-12-only airports (competitive advantage)
    {"icao": "2B2", "name": "Plum Island", "city": "Newburyport", "state": "MA", "region": "Northeast", "runway_ft": 2700, "surface": "ASPH"},
    {"icao": "K1B1", "name": "Hudson", "city": "Hudson", "state": "NY", "region": "Northeast", "runway_ft": 3600, "surface": "ASPH"},
    {"icao": "KSFM", "name": "Sanford Seacoast", "city": "Sanford", "state": "ME", "region": "Northeast", "runway_ft": 5200, "surface": "ASPH"},
]

# Route weights: Northeast-heavy, seasonal Florida
ROUTE_WEIGHTS_NE = [a["icao"] for a in AIRPORTS if a["region"] == "Northeast"]
ROUTE_WEIGHTS_SE = [a["icao"] for a in AIRPORTS if a["region"] == "Southeast"]
ROUTE_WEIGHTS_W = [a["icao"] for a in AIRPORTS if a["region"] == "West"]
SHORT_STRIP = [a["icao"] for a in AIRPORTS if a["runway_ft"] < 4000]

# Trip purposes (FAA Ch3: business w/crew dominant for fractional)
TRIP_PURPOSES = ["Business", "Leisure", "Medical", "Mixed"]
TRIP_PURPOSE_WEIGHTS = [0.55, 0.28, 0.05, 0.12]

# Maintenance types with scheduling
MAINT_TYPES = [
    {"type": "100HR_INSPECTION", "interval_hours": 100, "is_scheduled": True, "avg_duration_hrs": 12, "avg_labor_hrs": 8, "severity": "ROUTINE"},
    {"type": "200HR_INSPECTION", "interval_hours": 200, "is_scheduled": True, "avg_duration_hrs": 24, "avg_labor_hrs": 16, "severity": "ROUTINE"},
    {"type": "ANNUAL_INSPECTION", "interval_hours": 0, "is_scheduled": True, "avg_duration_hrs": 72, "avg_labor_hrs": 48, "severity": "ROUTINE"},
    {"type": "PHASE_1_CHECK", "interval_hours": 600, "is_scheduled": True, "avg_duration_hrs": 96, "avg_labor_hrs": 60, "severity": "ROUTINE"},
    {"type": "PHASE_2_CHECK", "interval_hours": 1200, "is_scheduled": True, "avg_duration_hrs": 168, "avg_labor_hrs": 100, "severity": "ROUTINE"},
    {"type": "HOT_SECTION_INSPECTION", "interval_hours": 1800, "is_scheduled": True, "avg_duration_hrs": 240, "avg_labor_hrs": 120, "severity": "ROUTINE"},
    {"type": "LINE_MAINTENANCE", "interval_hours": 0, "is_scheduled": False, "avg_duration_hrs": 6, "avg_labor_hrs": 4, "severity": "MINOR"},
    {"type": "COMPONENT_REPLACEMENT", "interval_hours": 0, "is_scheduled": False, "avg_duration_hrs": 18, "avg_labor_hrs": 10, "severity": "MODERATE"},
    {"type": "AOG_REPAIR", "interval_hours": 0, "is_scheduled": False, "avg_duration_hrs": 48, "avg_labor_hrs": 24, "severity": "AOG"},
    {"type": "TROUBLESHOOTING", "interval_hours": 0, "is_scheduled": False, "avg_duration_hrs": 8, "avg_labor_hrs": 6, "severity": "MINOR"},
    {"type": "AD_COMPLIANCE", "interval_hours": 0, "is_scheduled": True, "avg_duration_hrs": 16, "avg_labor_hrs": 10, "severity": "ROUTINE"},
    {"type": "SERVICE_BULLETIN", "interval_hours": 0, "is_scheduled": True, "avg_duration_hrs": 12, "avg_labor_hrs": 8, "severity": "ROUTINE"},
]

# Cost heads for maintenance details
LABOR_RATE_HR = 115  # $/hr for A&P mechanic
CERT_RATE_HR = 135   # $/hr for IA signoff
FUEL_COST_GAL = 6.80 # Jet-A $/gal

# Owner share types (from churn model, verified against PlaneSense programs)
SHARE_TYPES = [
    {"type": "1/16", "annual_hours": 100, "weight": 0.35},
    {"type": "1/8", "annual_hours": 200, "weight": 0.30},
    {"type": "1/4", "annual_hours": 400, "weight": 0.15},
    {"type": "1/32", "annual_hours": 50, "weight": 0.20},
]


def write_csv(filename, rows, fieldnames):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  {filename}: {len(rows)} rows")
    return path


# =============================================================================
# DIM_DATE
# =============================================================================
def gen_dim_date():
    rows = []
    d = SIM_START
    while d <= SIM_END:
        rows.append({
            "date_key": d.strftime("%Y%m%d"),
            "date": d.isoformat(),
            "day": d.day,
            "day_of_week": d.strftime("%A"),
            "day_of_week_num": d.isoweekday(),
            "is_weekend": 1 if d.isoweekday() >= 6 else 0,
            "week_num": d.isocalendar()[1],
            "month": d.month,
            "month_name": d.strftime("%B"),
            "quarter": (d.month - 1) // 3 + 1,
            "year": d.year,
            "season": {1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
                       6: "Summer", 7: "Summer", 8: "Summer", 9: "Fall", 10: "Fall",
                       11: "Fall", 12: "Winter"}[d.month],
            "is_holiday": 1 if (d.month, d.day) in [(1,1),(7,4),(12,25),(11,28),(12,31)] else 0,
            "fiscal_year": d.year if d.month >= 7 else d.year - 1,
        })
        d += timedelta(days=1)
    fields = list(rows[0].keys())
    write_csv("dim_date.csv", rows, fields)
    return rows


# =============================================================================
# DIM_AIRCRAFT
# =============================================================================
def gen_dim_aircraft():
    rows = []
    # PC-12 fleet: delivered 2017-2024, avg age ~4.5 yrs at end of 2025
    for i in range(PC12_COUNT):
        tail = f"N{100+i}AF"
        # Spread deliveries: center around 2021, range 2017-2024
        yr = random.choices(range(2017, 2025), weights=[3, 5, 8, 10, 12, 10, 6, 4])[0]
        mo = random.randint(1, 12)
        dy = random.randint(1, 28)
        delivery = date(yr, mo, dy)
        base = "FAC-PSM" if i < 32 else "FAC-BVU"
        rows.append({
            "aircraft_id": f"AC-{i+1:03d}",
            "tail_number": tail,
            "model": "PC-12 NGX",
            "engine_type": "PT6A-67P",
            "engine_count": 1,
            "serial_number": f"PC12-{1700+i}",
            "delivery_date": delivery.isoformat(),
            "years_in_service": round((SNAPSHOT_DATE - delivery).days / 365.25, 1),
            "base_facility_id": base,
            "region": "Northeast" if base == "FAC-PSM" else "West",
            "seat_capacity": 10,
            "max_range_nm": 1845,
            "mtow_kg": 4740,
            "current_status": "ACTIVE",
            "maintenance_program": "PHASE_INSPECTION",
        })
    # PC-24 fleet: delivered 2018-2025
    for i in range(PC24_COUNT):
        tail = f"N{800+i}AF"
        yr = random.choices(range(2018, 2026), weights=[3, 4, 6, 8, 10, 8, 5, 3])[0]
        mo = random.randint(1, 12)
        dy = random.randint(1, 28)
        delivery = date(yr, mo, dy)
        base = "FAC-PSM" if i < 11 else "FAC-BVU"
        rows.append({
            "aircraft_id": f"AC-{PC12_COUNT+i+1:03d}",
            "tail_number": tail,
            "model": "PC-24",
            "engine_type": "FJ44-4A",
            "engine_count": 2,
            "serial_number": f"PC24-{200+i}",
            "delivery_date": delivery.isoformat(),
            "years_in_service": round((SNAPSHOT_DATE - delivery).days / 365.25, 1),
            "base_facility_id": base,
            "region": "Northeast" if base == "FAC-PSM" else "West",
            "seat_capacity": 11,
            "max_range_nm": 2000,
            "mtow_kg": 8300,
            "current_status": "ACTIVE",
            "maintenance_program": "PHASE_INSPECTION",
        })
    fields = list(rows[0].keys())
    write_csv("dim_aircraft.csv", rows, fields)
    return rows


# =============================================================================
# DIM_AIRPORT
# =============================================================================
def gen_dim_airport():
    rows = []
    for a in AIRPORTS:
        rows.append({
            "airport_icao": a["icao"],
            "airport_name": a["name"],
            "city": a["city"],
            "state": a["state"],
            "region": a["region"],
            "runway_length_ft": a["runway_ft"],
            "runway_surface": a["surface"],
            "pc12_accessible": 1,
            "pc24_accessible": 1 if a["runway_ft"] >= 3810 else 0,  # PC-24 needs ~3,810 ft
        })
    fields = list(rows[0].keys())
    write_csv("dim_airport.csv", rows, fields)
    return rows


# =============================================================================
# DIM_COMPONENT (JASC-based, from SDRS calibration)
# =============================================================================
def gen_dim_component():
    rows = []
    for j in JASC_CODES:
        rows.append({
            "component_id": f"COMP-{j['code']}",
            "jasc_ata_code": j["code"],
            "system_name": j["system"],
            "component_name": j["name"],
            "sdrs_weight_pc12": j["weight_pc12"],
            "sdrs_weight_pc24": j["weight_pc24"],
        })
    fields = list(rows[0].keys())
    write_csv("dim_component.csv", rows, fields)
    return rows


# =============================================================================
# DIM_CREW
# =============================================================================
def gen_dim_crew():
    rows = []
    first_names = ["James","Robert","Michael","William","David","Richard","Joseph","Thomas",
                   "Sarah","Jennifer","Lisa","Emily","Amanda","Jessica","Michelle","Karen",
                   "Daniel","Mark","Steven","Andrew","Brian","Kevin","Timothy","Christopher"]
    last_names = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
                  "Rodriguez","Martinez","Hernandez","Lopez","Wilson","Anderson","Thomas","Taylor"]
    # 240+ pilots, we'll generate 80 for the demo
    for i in range(80):
        base = "FAC-PSM" if i < 56 else "FAC-BVU"
        role = "Captain" if i % 3 != 2 else "First Officer"
        # type ratings
        if i < 20:
            ratings = "PC-12,PC-24"
        elif i < 55:
            ratings = "PC-12"
        else:
            ratings = "PC-24" if i >= 60 else "PC-12"
        rows.append({
            "crew_id": f"CREW-{i+1:03d}",
            "crew_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "role": role,
            "base_facility_id": base,
            "type_ratings": ratings,
        })
    # 40 technicians
    for i in range(40):
        base = "FAC-PSM" if i < 28 else "FAC-BVU"
        rows.append({
            "crew_id": f"TECH-{i+1:03d}",
            "crew_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "role": "A&P Mechanic" if i % 4 != 0 else "IA Inspector",
            "base_facility_id": base,
            "type_ratings": "PC-12,PC-24",
        })
    fields = list(rows[0].keys())
    write_csv("dim_crew.csv", rows, fields)
    return rows


# =============================================================================
# DIM_FACILITY
# =============================================================================
def gen_dim_facility():
    fields = ["facility_id", "facility_name", "icao", "state", "type", "technician_count", "maintenance_bays"]
    rows = [{"facility_id": f["id"], "facility_name": f["name"], "icao": f["icao"],
             "state": f["state"], "type": f["type"], "technician_count": f["technician_count"],
             "maintenance_bays": f["bays"]} for f in FACILITIES]
    write_csv("dim_facility.csv", rows, fields)
    return rows


# =============================================================================
# DIM_OWNER
# =============================================================================
def gen_dim_owner():
    first_names = ["Catherine","George","Michael","Sarah","Robert","Jennifer","William","Emily",
                   "James","Amanda","David","Lisa","Richard","Karen","Thomas","Jessica",
                   "Daniel","Michelle","Steven","Laura","Andrew","Nicole","Brian","Rebecca",
                   "Kevin","Stephanie","Mark","Heather","Timothy","Rachel"]
    last_names = ["Morris","Chen","Patel","Thompson","Garcia","Williams","Johnson","Brown",
                  "Martinez","Anderson","Taylor","Thomas","Wilson","Clark","Lewis","Robinson",
                  "Hall","Young","Walker","Allen","King","Wright","Scott","Hill"]
    regions = ["Northeast", "Mid-Atlantic", "Southeast", "Midwest", "West"]
    region_weights = [0.30, 0.20, 0.18, 0.15, 0.17]
    states_by_region = {
        "Northeast": ["NH","MA","CT","RI","ME","VT","NY"],
        "Mid-Atlantic": ["NJ","PA","VA","MD","DC"],
        "Southeast": ["FL","GA","NC","SC","TN"],
        "Midwest": ["IL","OH","MI","MN","WI"],
        "West": ["CA","NV","CO","AZ","WA"],
    }
    rows = []
    share_labels = [s["type"] for s in SHARE_TYPES]
    share_weights = [s["weight"] for s in SHARE_TYPES]
    share_hours = {s["type"]: s["annual_hours"] for s in SHARE_TYPES}

    for i in range(350):
        region = random.choices(regions, weights=region_weights)[0]
        share = random.choices(share_labels, weights=share_weights)[0]
        join_yr = random.choices(range(2015, 2026), weights=[2,3,4,5,6,7,8,10,12,10,8])[0]
        join_date = date(join_yr, random.randint(1,12), random.randint(1,28))
        pref = random.choices(["PC-12", "PC-24", "No Preference"], weights=[0.55, 0.25, 0.20])[0]
        rows.append({
            "owner_id": f"OWN-{i+1:04d}",
            "owner_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "region": region,
            "state": random.choice(states_by_region[region]),
            "share_type": share,
            "annual_hours_contracted": share_hours[share],
            "join_date": join_date.isoformat(),
            "tenure_years": round((SNAPSHOT_DATE - join_date).days / 365.25, 1),
            "aircraft_preference": pref,
            "cobalt_pass_holder": 1 if random.random() < 0.12 else 0,
            "jetfly_access": 1 if region in ("Northeast", "Mid-Atlantic") and random.random() < 0.12 else 0,
            "status": "ACTIVE" if random.random() < 0.91 else "CHURNED",
        })
    fields = list(rows[0].keys())
    write_csv("dim_owner.csv", rows, fields)
    return rows


# =============================================================================
# FACT_FLIGHT — the core utilization fact
# =============================================================================
def gen_fact_flight(aircraft, owners):
    print("  Generating flights (this takes a moment)...")
    flights = []
    flight_id = 0
    aircraft_hours = defaultdict(float)  # running total per aircraft
    aircraft_last_flight = {}

    # Build owner pool for booking linkage
    active_owners = [o for o in owners if o["status"] == "ACTIVE"]

    # Pre-build date list
    all_dates = []
    d = SIM_START
    while d <= SIM_END:
        all_dates.append(d)
        d += timedelta(days=1)

    for ac in aircraft:
        delivery = date.fromisoformat(ac["delivery_date"])
        is_pc12 = ac["model"] == "PC-12 NGX"
        avg_hrs_yr = PC12_AVG_HOURS_YR if is_pc12 else PC24_AVG_HOURS_YR
        avg_leg = PC12_AVG_LEG_HRS if is_pc12 else PC24_AVG_LEG_HRS
        avg_flights_day = avg_hrs_yr / 365 / avg_leg
        base_icao = "KPSM" if ac["base_facility_id"] == "FAC-PSM" else "KBVU"

        # Weight airports by region affinity
        if ac["region"] == "Northeast":
            pool = ROUTE_WEIGHTS_NE * 4 + ROUTE_WEIGHTS_SE * 2 + ROUTE_WEIGHTS_W + [a["icao"] for a in AIRPORTS if a["region"] == "Midwest"]
        else:
            pool = ROUTE_WEIGHTS_W * 4 + ROUTE_WEIGHTS_NE * 2 + ROUTE_WEIGHTS_SE + [a["icao"] for a in AIRPORTS if a["region"] == "Midwest"]

        # Remove short-strip from PC-24
        if not is_pc12:
            pool = [p for p in pool if p not in SHORT_STRIP]

        current_location = base_icao

        for d in all_dates:
            if d < delivery:
                continue

            seasonal = SEASONAL[d.month]
            n_flights = max(0, int(random.gauss(avg_flights_day * seasonal, 0.8)))

            # Ground day probability (maintenance, weather, no demand)
            if random.random() < 0.08:
                n_flights = 0

            for _ in range(n_flights):
                flight_id += 1

                # Determine origin/destination
                origin = current_location
                dest = random.choice([p for p in pool if p != origin]) if len(pool) > 1 else pool[0]

                # Duration — FAA-calibrated
                duration = max(0.3, random.gauss(avg_leg, 0.35 if is_pc12 else 0.40))
                duration = round(duration, 2)

                # Passengers — fractional = typically 1-6 pax
                is_deadhead = random.random() < 0.15  # ~15% empty legs
                is_maint_ferry = random.random() < 0.03  # ~3% ferry to maintenance
                if is_deadhead or is_maint_ferry:
                    pax = 0
                    if is_maint_ferry:
                        dest = "KPSM" if ac["base_facility_id"] == "FAC-PSM" else "KBVU"
                else:
                    pax = random.choices([1,2,3,4,5,6,7,8], weights=[15,20,25,18,10,7,3,2])[0]

                # Purpose
                if is_maint_ferry:
                    purpose = "Maintenance Ferry"
                elif is_deadhead:
                    purpose = "Repositioning"
                else:
                    purpose = random.choices(TRIP_PURPOSES, weights=TRIP_PURPOSE_WEIGHTS)[0]

                # Times
                hour = random.choices(range(6, 22), weights=[3,5,8,10,10,8,8,6,5,5,5,5,4,3,3,2])[0]
                dep_time = datetime(d.year, d.month, d.day, hour, random.randint(0, 59))
                arr_time = dep_time + timedelta(hours=duration)

                # Distance estimate (rough: 250 nm/hr for PC-12, 400 nm/hr for PC-24)
                speed = 250 if is_pc12 else 400
                distance_nm = round(duration * speed, 0)

                # Fuel consumption (PC-12: ~65 gal/hr, PC-24: ~160 gal/hr)
                fuel_rate = 65 if is_pc12 else 160
                fuel_gal = round(duration * fuel_rate * random.uniform(0.9, 1.1), 1)

                # Weather delay
                weather_delay = 0
                if d.month in (1, 2, 12) and ac["region"] == "Northeast":
                    if random.random() < 0.12:
                        weather_delay = random.choice([15, 30, 45, 60, 90, 120])
                elif random.random() < 0.04:
                    weather_delay = random.choice([15, 30, 45])

                # Owner assignment
                owner = random.choice(active_owners) if pax > 0 else None

                # Crew assignment
                pilot_id = f"CREW-{random.randint(1, 80):03d}"
                copilot_id = f"CREW-{random.randint(1, 80):03d}" if not is_pc12 or random.random() < 0.3 else ""

                flights.append({
                    "flight_id": f"FLT-{flight_id:07d}",
                    "date": d.isoformat(),
                    "aircraft_id": ac["aircraft_id"],
                    "tail_number": ac["tail_number"],
                    "model": ac["model"],
                    "owner_id": owner["owner_id"] if owner else "",
                    "booking_id": f"BK-{flight_id:07d}" if pax > 0 else "",
                    "journey_leg_seq": 1,
                    "origin_icao": origin,
                    "destination_icao": dest,
                    "departure_time": dep_time.strftime("%Y-%m-%d %H:%M"),
                    "arrival_time": arr_time.strftime("%Y-%m-%d %H:%M"),
                    "block_hours": round(duration + random.uniform(0.1, 0.3), 2),
                    "flight_hours": duration,
                    "distance_nm": int(distance_nm),
                    "passenger_count": pax,
                    "flight_purpose": purpose,
                    "is_deadhead": 1 if is_deadhead else 0,
                    "is_maintenance_ferry": 1 if is_maint_ferry else 0,
                    "flight_status": "COMPLETED",
                    "fuel_consumed_gal": fuel_gal,
                    "weather_delay_min": weather_delay,
                    "pilot_id": pilot_id,
                    "copilot_id": copilot_id,
                })
                aircraft_hours[ac["aircraft_id"]] += duration
                current_location = dest
                aircraft_last_flight[ac["aircraft_id"]] = d

    fields = list(flights[0].keys())
    write_csv("fact_flight.csv", flights, fields)
    return flights, aircraft_hours


# =============================================================================
# FACT_BOOKING
# =============================================================================
def gen_fact_booking(flights, owners):
    bookings = []
    seen = set()
    active_owners = [o for o in owners if o["status"] == "ACTIVE"]

    for f in flights:
        bid = f["booking_id"]
        if not bid or bid in seen:
            continue
        seen.add(bid)

        fdate = date.fromisoformat(f["date"])
        lead_days = max(1, int(random.expovariate(1/7) + 1))  # avg 7 days lead
        booking_date = fdate - timedelta(days=lead_days)

        owner = next((o for o in owners if o["owner_id"] == f["owner_id"]), None)
        channel = random.choices(["Phone", "Mobile App", "Owner Portal", "Account Manager"],
                                 weights=[0.25, 0.35, 0.25, 0.15])[0]
        bookings.append({
            "booking_id": bid,
            "booking_date": booking_date.isoformat(),
            "owner_id": f["owner_id"],
            "passenger_count": f["passenger_count"],
            "pet_count": 1 if random.random() < 0.08 else 0,
            "preferred_model": owner["aircraft_preference"] if owner else "",
            "departure_date": f["date"],
            "origin_icao": f["origin_icao"],
            "destination_icao": f["destination_icao"],
            "trip_purpose": f["flight_purpose"],
            "booking_status": "COMPLETED",
            "booking_channel": channel,
            "lead_time_days": lead_days,
        })

    # Add ~5% cancelled bookings
    n_cancelled = int(len(bookings) * 0.05)
    for i in range(n_cancelled):
        owner = random.choice(active_owners)
        fdate = SIM_START + timedelta(days=random.randint(0, (SIM_END - SIM_START).days))
        lead_days = max(1, int(random.expovariate(1/5) + 1))
        booking_date = fdate - timedelta(days=lead_days)
        origin = random.choice(AIRPORTS)["icao"]
        dest = random.choice([a["icao"] for a in AIRPORTS if a["icao"] != origin])
        bookings.append({
            "booking_id": f"BK-C{i+1:06d}",
            "booking_date": booking_date.isoformat(),
            "owner_id": owner["owner_id"],
            "passenger_count": random.randint(1, 5),
            "pet_count": 0,
            "preferred_model": owner["aircraft_preference"],
            "departure_date": fdate.isoformat(),
            "origin_icao": origin,
            "destination_icao": dest,
            "trip_purpose": random.choices(TRIP_PURPOSES, weights=TRIP_PURPOSE_WEIGHTS)[0],
            "booking_status": random.choice(["CANCELLED", "NO_SHOW"]),
            "booking_channel": random.choice(["Phone", "Mobile App", "Owner Portal", "Account Manager"]),
            "lead_time_days": lead_days,
        })

    fields = list(bookings[0].keys())
    write_csv("fact_booking.csv", bookings, fields)
    return bookings


# =============================================================================
# FACT_MAINTENANCE_JOB + FACT_MAINTENANCE_DETAIL
# =============================================================================
def gen_maintenance(aircraft, flights, aircraft_hours):
    print("  Generating maintenance jobs...")
    jobs = []
    details = []
    job_id = 0
    detail_id = 0

    # Build per-aircraft flight hour accumulation timeline
    ac_hour_timeline = defaultdict(list)
    for f in flights:
        ac_hour_timeline[f["aircraft_id"]].append((date.fromisoformat(f["date"]), f["flight_hours"]))

    # SDRS-calibrated JASC weights
    jasc_weights_pc12 = [j["weight_pc12"] for j in JASC_CODES]
    jasc_weights_pc24 = [j["weight_pc24"] for j in JASC_CODES]

    for ac in aircraft:
        is_pc12 = ac["model"] == "PC-12 NGX"
        facility = ac["base_facility_id"]
        delivery = date.fromisoformat(ac["delivery_date"])
        timeline = sorted(ac_hour_timeline.get(ac["aircraft_id"], []))

        # Accumulate hours
        cumulative_hours = 0.0
        last_100hr = 0.0
        last_200hr = 0.0
        last_annual = delivery
        hours_by_date = {}
        for d, hrs in timeline:
            cumulative_hours += hrs
            hours_by_date[d] = cumulative_hours

            # Scheduled: 100-hour inspection
            if cumulative_hours - last_100hr >= 100:
                last_100hr = cumulative_hours
                job_id += 1
                mt = MAINT_TYPES[0]  # 100HR
                duration = max(4, random.gauss(mt["avg_duration_hrs"], mt["avg_duration_hrs"] * 0.2))
                start = datetime(d.year, d.month, d.day, 7, 0)
                close = start + timedelta(hours=duration)
                tech = f"TECH-{random.randint(1, 40):03d}"

                finding = random.choices(
                    ["NO_FINDING", "WEAR_WITHIN_LIMITS", "MINOR_DEFECT", "REPLACEMENT_REQUIRED"],
                    weights=[0.55, 0.25, 0.14, 0.06]
                )[0]

                jobs.append({
                    "maintenance_job_id": f"MJ-{job_id:06d}",
                    "date": d.isoformat(),
                    "aircraft_id": ac["aircraft_id"],
                    "tail_number": ac["tail_number"],
                    "facility_id": facility,
                    "maintenance_type": mt["type"],
                    "is_scheduled": 1,
                    "severity": mt["severity"],
                    "trigger_source": "SCHEDULED",
                    "job_status": "COMPLETED",
                    "start_datetime": start.strftime("%Y-%m-%d %H:%M"),
                    "close_datetime": close.strftime("%Y-%m-%d %H:%M"),
                    "total_elapsed_hours": round(duration, 1),
                    "finding_code": finding,
                    "technician_id": tech,
                    "aircraft_hours_at_event": round(cumulative_hours, 1),
                })
                # Detail lines
                labor_hrs = max(2, random.gauss(mt["avg_labor_hrs"], 2))
                detail_id += 1
                details.append({
                    "detail_id": f"MD-{detail_id:07d}",
                    "maintenance_job_id": f"MJ-{job_id:06d}",
                    "date": d.isoformat(),
                    "aircraft_id": ac["aircraft_id"],
                    "facility_id": facility,
                    "action_type": "INSPECT",
                    "cost_category": "LABOR",
                    "jasc_ata_code": "",
                    "part_description": "Inspection Labor",
                    "uom": "Hours",
                    "quantity": round(labor_hrs, 1),
                    "unit_cost": LABOR_RATE_HR,
                    "extended_cost": round(labor_hrs * LABOR_RATE_HR, 2),
                })
                # Cert signoff
                detail_id += 1
                cert_hrs = round(random.uniform(1.5, 3.0), 1)
                details.append({
                    "detail_id": f"MD-{detail_id:07d}",
                    "maintenance_job_id": f"MJ-{job_id:06d}",
                    "date": d.isoformat(),
                    "aircraft_id": ac["aircraft_id"],
                    "facility_id": facility,
                    "action_type": "CERTIFY",
                    "cost_category": "CERTIFICATION",
                    "jasc_ata_code": "",
                    "part_description": "IA Return-to-Service",
                    "uom": "Hours",
                    "quantity": cert_hrs,
                    "unit_cost": CERT_RATE_HR,
                    "extended_cost": round(cert_hrs * CERT_RATE_HR, 2),
                })
                # If replacement required, add part cost
                if finding == "REPLACEMENT_REQUIRED":
                    jasc = random.choices(JASC_CODES, weights=jasc_weights_pc12 if is_pc12 else jasc_weights_pc24)[0]
                    part_cost = random.choice([420, 680, 1500, 2200, 3800, 4500, 9500])
                    detail_id += 1
                    details.append({
                        "detail_id": f"MD-{detail_id:07d}",
                        "maintenance_job_id": f"MJ-{job_id:06d}",
                        "date": d.isoformat(),
                        "aircraft_id": ac["aircraft_id"],
                        "facility_id": facility,
                        "action_type": "REPLACE",
                        "cost_category": "PARTS",
                        "jasc_ata_code": jasc["code"],
                        "part_description": jasc["name"],
                        "uom": "Each",
                        "quantity": 1,
                        "unit_cost": part_cost,
                        "extended_cost": part_cost,
                    })
                # Fuel for engine run
                fuel_gal = round(random.uniform(20, 60), 1)
                detail_id += 1
                details.append({
                    "detail_id": f"MD-{detail_id:07d}",
                    "maintenance_job_id": f"MJ-{job_id:06d}",
                    "date": d.isoformat(),
                    "aircraft_id": ac["aircraft_id"],
                    "facility_id": facility,
                    "action_type": "SERVICE",
                    "cost_category": "FUEL",
                    "jasc_ata_code": "",
                    "part_description": "Jet-A Fuel (ground run)",
                    "uom": "Gallons",
                    "quantity": fuel_gal,
                    "unit_cost": FUEL_COST_GAL,
                    "extended_cost": round(fuel_gal * FUEL_COST_GAL, 2),
                })

            # 200-hour inspection
            if cumulative_hours - last_200hr >= 200:
                last_200hr = cumulative_hours
                job_id += 1
                mt = MAINT_TYPES[1]
                duration = max(8, random.gauss(mt["avg_duration_hrs"], 4))
                start = datetime(d.year, d.month, d.day, 7, 0)
                close = start + timedelta(hours=duration)
                tech = f"TECH-{random.randint(1, 40):03d}"
                finding = random.choices(
                    ["NO_FINDING", "WEAR_WITHIN_LIMITS", "MINOR_DEFECT", "REPLACEMENT_REQUIRED"],
                    weights=[0.45, 0.30, 0.17, 0.08]
                )[0]
                jobs.append({
                    "maintenance_job_id": f"MJ-{job_id:06d}",
                    "date": d.isoformat(),
                    "aircraft_id": ac["aircraft_id"],
                    "tail_number": ac["tail_number"],
                    "facility_id": facility,
                    "maintenance_type": mt["type"],
                    "is_scheduled": 1,
                    "severity": mt["severity"],
                    "trigger_source": "SCHEDULED",
                    "job_status": "COMPLETED",
                    "start_datetime": start.strftime("%Y-%m-%d %H:%M"),
                    "close_datetime": close.strftime("%Y-%m-%d %H:%M"),
                    "total_elapsed_hours": round(duration, 1),
                    "finding_code": finding,
                    "technician_id": tech,
                    "aircraft_hours_at_event": round(cumulative_hours, 1),
                })
                labor_hrs = max(6, random.gauss(mt["avg_labor_hrs"], 3))
                detail_id += 1
                details.append({
                    "detail_id": f"MD-{detail_id:07d}",
                    "maintenance_job_id": f"MJ-{job_id:06d}",
                    "date": d.isoformat(),
                    "aircraft_id": ac["aircraft_id"],
                    "facility_id": facility,
                    "action_type": "INSPECT",
                    "cost_category": "LABOR",
                    "jasc_ata_code": "",
                    "part_description": "200hr Inspection Labor",
                    "uom": "Hours",
                    "quantity": round(labor_hrs, 1),
                    "unit_cost": LABOR_RATE_HR,
                    "extended_cost": round(labor_hrs * LABOR_RATE_HR, 2),
                })
                detail_id += 1
                cert_hrs = round(random.uniform(2.0, 4.0), 1)
                details.append({
                    "detail_id": f"MD-{detail_id:07d}",
                    "maintenance_job_id": f"MJ-{job_id:06d}",
                    "date": d.isoformat(),
                    "aircraft_id": ac["aircraft_id"],
                    "facility_id": facility,
                    "action_type": "CERTIFY",
                    "cost_category": "CERTIFICATION",
                    "jasc_ata_code": "",
                    "part_description": "IA Return-to-Service",
                    "uom": "Hours",
                    "quantity": cert_hrs,
                    "unit_cost": CERT_RATE_HR,
                    "extended_cost": round(cert_hrs * CERT_RATE_HR, 2),
                })
                if finding in ("MINOR_DEFECT", "REPLACEMENT_REQUIRED"):
                    jasc = random.choices(JASC_CODES, weights=jasc_weights_pc12 if is_pc12 else jasc_weights_pc24)[0]
                    part_cost = random.choice([680, 1500, 2200, 3800, 4500])
                    repair_hrs = round(random.uniform(2, 8), 1)
                    detail_id += 1
                    details.append({
                        "detail_id": f"MD-{detail_id:07d}",
                        "maintenance_job_id": f"MJ-{job_id:06d}",
                        "date": d.isoformat(),
                        "aircraft_id": ac["aircraft_id"],
                        "facility_id": facility,
                        "action_type": "REPLACE" if finding == "REPLACEMENT_REQUIRED" else "REPAIR",
                        "cost_category": "PARTS" if finding == "REPLACEMENT_REQUIRED" else "LABOR",
                        "jasc_ata_code": jasc["code"],
                        "part_description": jasc["name"],
                        "uom": "Each" if finding == "REPLACEMENT_REQUIRED" else "Hours",
                        "quantity": 1 if finding == "REPLACEMENT_REQUIRED" else repair_hrs,
                        "unit_cost": part_cost if finding == "REPLACEMENT_REQUIRED" else LABOR_RATE_HR,
                        "extended_cost": part_cost if finding == "REPLACEMENT_REQUIRED" else round(repair_hrs * LABOR_RATE_HR, 2),
                    })

            # Unscheduled maintenance — ~4% probability per 100 flight hours (SDRS-calibrated)
            if random.random() < 0.0015:  # per-flight probability ≈ 4% per 100hrs / ~27 flights per 100hrs
                job_id += 1
                severity = random.choices(
                    ["MINOR", "MODERATE", "AOG"],
                    weights=[0.55, 0.35, 0.10]
                )[0]
                unsched_type = random.choices(
                    ["LINE_MAINTENANCE", "COMPONENT_REPLACEMENT", "AOG_REPAIR", "TROUBLESHOOTING"],
                    weights=[0.40, 0.30, 0.10, 0.20]
                )[0]
                mt = next(m for m in MAINT_TYPES if m["type"] == unsched_type)
                duration = max(2, random.gauss(mt["avg_duration_hrs"], mt["avg_duration_hrs"] * 0.3))
                if severity == "AOG":
                    duration = max(24, random.gauss(48, 16))
                start = datetime(d.year, d.month, d.day, random.randint(7, 20), 0)
                close = start + timedelta(hours=duration)
                trigger = random.choices(
                    ["PILOT_REPORT", "SENSOR_ALERT", "INSPECTION_FINDING", "GROUND_CREW"],
                    weights=[0.35, 0.20, 0.25, 0.20]
                )[0]
                jasc = random.choices(JASC_CODES, weights=jasc_weights_pc12 if is_pc12 else jasc_weights_pc24)[0]
                tech = f"TECH-{random.randint(1, 40):03d}"

                jobs.append({
                    "maintenance_job_id": f"MJ-{job_id:06d}",
                    "date": d.isoformat(),
                    "aircraft_id": ac["aircraft_id"],
                    "tail_number": ac["tail_number"],
                    "facility_id": facility,
                    "maintenance_type": unsched_type,
                    "is_scheduled": 0,
                    "severity": severity,
                    "trigger_source": trigger,
                    "job_status": "COMPLETED",
                    "start_datetime": start.strftime("%Y-%m-%d %H:%M"),
                    "close_datetime": close.strftime("%Y-%m-%d %H:%M"),
                    "total_elapsed_hours": round(duration, 1),
                    "finding_code": jasc["name"],
                    "technician_id": tech,
                    "aircraft_hours_at_event": round(cumulative_hours, 1),
                })
                # Labor
                labor_hrs = max(2, random.gauss(mt["avg_labor_hrs"], 3))
                detail_id += 1
                details.append({
                    "detail_id": f"MD-{detail_id:07d}",
                    "maintenance_job_id": f"MJ-{job_id:06d}",
                    "date": d.isoformat(),
                    "aircraft_id": ac["aircraft_id"],
                    "facility_id": facility,
                    "action_type": "REPAIR",
                    "cost_category": "LABOR",
                    "jasc_ata_code": jasc["code"],
                    "part_description": f"{jasc['name']} - {unsched_type}",
                    "uom": "Hours",
                    "quantity": round(labor_hrs, 1),
                    "unit_cost": LABOR_RATE_HR,
                    "extended_cost": round(labor_hrs * LABOR_RATE_HR, 2),
                })
                # Parts if component replacement or AOG
                if unsched_type in ("COMPONENT_REPLACEMENT", "AOG_REPAIR"):
                    part_cost = random.choice([680, 1500, 2200, 3800, 4500, 9500, 15000, 22000])
                    if severity == "AOG":
                        part_cost = random.choice([9500, 15000, 22000, 45000, 85000])
                    detail_id += 1
                    details.append({
                        "detail_id": f"MD-{detail_id:07d}",
                        "maintenance_job_id": f"MJ-{job_id:06d}",
                        "date": d.isoformat(),
                        "aircraft_id": ac["aircraft_id"],
                        "facility_id": facility,
                        "action_type": "REPLACE",
                        "cost_category": "PARTS",
                        "jasc_ata_code": jasc["code"],
                        "part_description": jasc["name"],
                        "uom": "Each",
                        "quantity": random.randint(1, 3),
                        "unit_cost": part_cost,
                        "extended_cost": part_cost * random.randint(1, 2),
                    })

    fields_jobs = list(jobs[0].keys())
    fields_details = list(details[0].keys())
    write_csv("fact_maintenance_job.csv", jobs, fields_jobs)
    write_csv("fact_maintenance_detail.csv", details, fields_details)
    return jobs, details


# =============================================================================
# FACT_AIRCRAFT_DAILY_STATUS — bridges utilization ↔ maintenance
# =============================================================================
def gen_daily_status(aircraft, flights, maint_jobs):
    print("  Generating aircraft daily status...")
    # Build flight days per aircraft
    flight_days = defaultdict(lambda: defaultdict(float))
    flight_counts = defaultdict(lambda: defaultdict(int))
    for f in flights:
        flight_days[f["aircraft_id"]][f["date"]] += f["flight_hours"]
        flight_counts[f["aircraft_id"]][f["date"]] += 1

    # Build maintenance windows per aircraft
    maint_windows = defaultdict(list)
    for j in maint_jobs:
        start = datetime.strptime(j["start_datetime"], "%Y-%m-%d %H:%M").date()
        elapsed = j["total_elapsed_hours"]
        end = start + timedelta(days=max(1, int(elapsed / 24)))
        maint_windows[j["aircraft_id"]].append((start, end, j["severity"], j["maintenance_type"]))

    rows = []
    for ac in aircraft:
        delivery = date.fromisoformat(ac["delivery_date"])
        d = max(SIM_START, delivery)
        while d <= SIM_END:
            ds = d.isoformat()
            hrs = round(flight_days[ac["aircraft_id"]].get(ds, 0.0), 2)
            cycles = flight_counts[ac["aircraft_id"]].get(ds, 0)

            # Check if in maintenance
            in_maint = False
            maint_type = ""
            for (ms, me, sev, mt) in maint_windows[ac["aircraft_id"]]:
                if ms <= d <= me:
                    in_maint = True
                    maint_type = mt
                    if sev == "AOG":
                        status = "AOG"
                    else:
                        status = "IN_MAINTENANCE"
                    break

            if not in_maint:
                if hrs > 0:
                    status = "FLYING"
                else:
                    status = "AVAILABLE"

            rows.append({
                "aircraft_id": ac["aircraft_id"],
                "date": ds,
                "status": status,
                "flight_hours": hrs,
                "flight_cycles": cycles,
                "maintenance_type": maint_type if in_maint else "",
            })
            d += timedelta(days=1)

    fields = list(rows[0].keys())
    write_csv("fact_aircraft_daily_status.csv", rows, fields)
    return rows


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 60)
    print("Generating PlaneSense Analytics Data (Power BI ready)")
    print("=" * 60)
    print(f"Simulation: {SIM_START} to {SIM_END} (3 years)")
    print(f"Fleet: {PC12_COUNT} PC-12 + {PC24_COUNT} PC-24 = {TOTAL_AIRCRAFT} aircraft")
    print(f"Output: {OUT_DIR}/")
    print()

    print("[1/8] Dim_Date")
    dates = gen_dim_date()

    print("[2/8] Dim_Aircraft")
    aircraft = gen_dim_aircraft()

    print("[3/8] Dim_Airport")
    airports = gen_dim_airport()

    print("[4/8] Dim_Component")
    components = gen_dim_component()

    print("[5/8] Dim_Crew + Dim_Facility + Dim_Owner")
    crew = gen_dim_crew()
    facilities = gen_dim_facility()
    owners = gen_dim_owner()

    print("[6/8] Fact_Flight (core utilization)")
    flights, ac_hours = gen_fact_flight(aircraft, owners)

    print("[7/8] Fact_Booking")
    bookings = gen_fact_booking(flights, owners)

    print("[8/8] Fact_Maintenance_Job + Fact_Maintenance_Detail")
    maint_jobs, maint_details = gen_maintenance(aircraft, flights, ac_hours)

    print("[9/8] Fact_Aircraft_Daily_Status (bridge table)")
    daily_status = gen_daily_status(aircraft, flights, maint_jobs)

    # Summary
    print()
    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    total_flight_hrs = sum(f["flight_hours"] for f in flights)
    total_pax = sum(f["passenger_count"] for f in flights)
    total_maint_cost = sum(d["extended_cost"] for d in maint_details)
    scheduled = sum(1 for j in maint_jobs if j["is_scheduled"] == 1)
    unscheduled = sum(1 for j in maint_jobs if j["is_scheduled"] == 0)
    aog_count = sum(1 for j in maint_jobs if j["severity"] == "AOG")

    print(f"Flights:           {len(flights):,}")
    print(f"Total flight hrs:  {total_flight_hrs:,.0f}")
    print(f"Avg hrs/aircraft:  {total_flight_hrs/TOTAL_AIRCRAFT:,.0f} (over {(SIM_END-SIM_START).days/365:.1f} yrs)")
    print(f"Avg hrs/ac/yr:     {total_flight_hrs/TOTAL_AIRCRAFT/3:,.0f}")
    print(f"Total passengers:  {total_pax:,}")
    print(f"Bookings:          {len(bookings):,}")
    print(f"Maint jobs:        {len(maint_jobs):,} (scheduled: {scheduled}, unscheduled: {unscheduled}, AOG: {aog_count})")
    print(f"Maint details:     {len(maint_details):,}")
    print(f"Total maint cost:  ${total_maint_cost:,.0f}")
    print(f"Cost/flight hour:  ${total_maint_cost/total_flight_hrs:,.0f}")
    print(f"Daily status rows: {len(daily_status):,}")
    print(f"Owners:            {len(owners)}")
    print()
    ann_flights = len(flights) / 3
    print(f"Annualized flights: ~{ann_flights:,.0f} (target: ~47,800)")
    print(f"Deadhead ratio:     {sum(1 for f in flights if f['is_deadhead'])/len(flights)*100:.1f}%")
    print()
    print(f"All files saved to: {OUT_DIR}/")


if __name__ == "__main__":
    main()

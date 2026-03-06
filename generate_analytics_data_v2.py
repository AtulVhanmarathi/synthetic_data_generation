#!/usr/bin/env python3
"""
generate_analytics_data_v2.py
==============================
Single-pass consolidated generator for PlaneSense Power BI analytics data.

Produces all 12 CSVs (star schema) in one run with correct data from the start.
Folds in all logic previously spread across 7 fix scripts in scripts/:
  - Weighted route distribution (regenerate_routes_v2.py)
  - Correct share types + Cobalt config (fix_owner_data.py)
  - AOG consolidated to Mar/May/Oct (consolidate_aog.py)
  - Maintenance cost ratios: BOOST months 1.40x, REVERT months 0.70x (fix_maintenance_cost_ratio.py)
  - Emergency AOG costs for heavy AOG months (fix_aog_costs.py)
  - Seasonal FLYING% patterns (fix_fleet_status_seasonality.py)
  - Hours/cycles integrity (fix_daily_status_hours.py)
  - FLYING<->AVAILABLE rebalance + holiday spike (rebalance_daily_status.py)

Calibrated against:
  - FAA GA Survey 2020–2024 (Ch3/Ch6): PC-12 ~1,150 hrs/yr, PC-24 ~1,350 hrs/yr
  - FAA SDRS: 615 real PC-12/PC-24 SDR records (JASC code distribution)
  - PlaneSense: 62 aircraft, ~47,800 flights/yr, 2 facilities, 91% retention

Usage:  python3 generate_analytics_data_v2.py
Output: output/analytics/data/  (12 CSVs — gitignored, regenerate from this script)

Preserved (reference/rollback):
  generate_analytics_data.py  — V1 base generator
  scripts/*.py                — individual fix scripts
  build_data.py               — V1 pipeline wrapper
"""

import csv
import math
import os
import random
from collections import defaultdict
from datetime import date, datetime, timedelta

random.seed(42)
OUT_DIR = "output/analytics/data"
os.makedirs(OUT_DIR, exist_ok=True)

# =============================================================================
# SIMULATION WINDOW
# =============================================================================
SIM_START    = date(2023, 1, 1)
SIM_END      = date(2025, 12, 31)
SNAPSHOT     = date(2025, 12, 31)

# =============================================================================
# FLEET
# =============================================================================
PC12_COUNT     = 46
PC24_COUNT     = 16
TOTAL_AIRCRAFT = PC12_COUNT + PC24_COUNT   # 62

# Aircraft performance (from regenerate_routes_v2)
PERF = {
    "PC-12 NGX": {"cruise_kts": 270, "fuel_gph": 68, "block_factor": 1.15, "max_nm": 600},
    "PC-24":     {"cruise_kts": 340, "fuel_gph": 95, "block_factor": 1.15, "max_nm": 1200},
}

# =============================================================================
# FACILITIES
# =============================================================================
FACILITIES = [
    {"id": "FAC-PSM", "name": "Portsmouth NH (Pease)", "icao": "KPSM", "state": "NH",
     "type": "PRIMARY",   "technician_count": 28, "bays": 8},
    {"id": "FAC-BVU", "name": "Boulder City NV",       "icao": "KBVU", "state": "NV",
     "type": "SECONDARY", "technician_count": 12, "bays": 4},
]

# =============================================================================
# AIRPORTS — all 34 with lat/lon (required for haversine route calculation)
# =============================================================================
AIRPORTS = [
    # Northeast
    {"icao": "KPSM", "name": "Portsmouth Intl",       "city": "Portsmouth",      "state": "NH", "region": "Northeast",    "runway_ft": 11321, "surface": "ASPH",      "lat": 43.0779, "lon":  -70.8233},
    {"icao": "KBOS", "name": "Boston Logan",           "city": "Boston",          "state": "MA", "region": "Northeast",    "runway_ft": 10083, "surface": "ASPH",      "lat": 42.3643, "lon":  -71.0052},
    {"icao": "KJFK", "name": "John F Kennedy",         "city": "New York",        "state": "NY", "region": "Northeast",    "runway_ft": 14511, "surface": "ASPH",      "lat": 40.6413, "lon":  -73.7781},
    {"icao": "KEWR", "name": "Newark Liberty",         "city": "Newark",          "state": "NJ", "region": "Northeast",    "runway_ft": 11000, "surface": "ASPH",      "lat": 40.6895, "lon":  -74.1745},
    {"icao": "KPVD", "name": "T.F. Green",             "city": "Providence",      "state": "RI", "region": "Northeast",    "runway_ft":  7166, "surface": "ASPH",      "lat": 41.7243, "lon":  -71.4282},
    {"icao": "KBDL", "name": "Bradley Intl",           "city": "Hartford",        "state": "CT", "region": "Northeast",    "runway_ft":  9510, "surface": "ASPH",      "lat": 41.9388, "lon":  -72.6832},
    {"icao": "KPWM", "name": "Portland Jetport",       "city": "Portland",        "state": "ME", "region": "Northeast",    "runway_ft":  7200, "surface": "ASPH",      "lat": 43.6462, "lon":  -70.3093},
    {"icao": "KMHT", "name": "Manchester-Boston",      "city": "Manchester",      "state": "NH", "region": "Northeast",    "runway_ft":  9250, "surface": "ASPH",      "lat": 42.9326, "lon":  -71.4357},
    {"icao": "KACK", "name": "Nantucket Memorial",     "city": "Nantucket",       "state": "MA", "region": "Northeast",    "runway_ft":  6303, "surface": "ASPH",      "lat": 41.2531, "lon":  -70.0602},
    {"icao": "KMVY", "name": "Martha's Vineyard",      "city": "Vineyard Haven",  "state": "MA", "region": "Northeast",    "runway_ft":  5504, "surface": "ASPH",      "lat": 41.3931, "lon":  -70.6154},
    {"icao": "KHPN", "name": "Westchester County",     "city": "White Plains",    "state": "NY", "region": "Northeast",    "runway_ft":  6549, "surface": "ASPH",      "lat": 41.0670, "lon":  -73.7076},
    {"icao": "KTEB", "name": "Teterboro",              "city": "Teterboro",       "state": "NJ", "region": "Northeast",    "runway_ft":  7000, "surface": "ASPH",      "lat": 40.8501, "lon":  -74.0608},
    {"icao": "KBED", "name": "Hanscom Field",          "city": "Bedford",         "state": "MA", "region": "Northeast",    "runway_ft":  7011, "surface": "ASPH",      "lat": 42.4700, "lon":  -71.2890},
    # Mid-Atlantic
    {"icao": "KIAD", "name": "Dulles Intl",            "city": "Washington",      "state": "VA", "region": "Mid-Atlantic", "runway_ft": 11500, "surface": "CONC",      "lat": 38.9531, "lon":  -77.4565},
    {"icao": "KPHL", "name": "Philadelphia Intl",      "city": "Philadelphia",    "state": "PA", "region": "Mid-Atlantic", "runway_ft": 10506, "surface": "ASPH",      "lat": 39.8721, "lon":  -75.2411},
    # Southeast
    {"icao": "KMIA", "name": "Miami Intl",             "city": "Miami",           "state": "FL", "region": "Southeast",    "runway_ft": 13016, "surface": "ASPH",      "lat": 25.7959, "lon":  -80.2870},
    {"icao": "KPBI", "name": "Palm Beach Intl",        "city": "West Palm Beach", "state": "FL", "region": "Southeast",    "runway_ft": 10008, "surface": "ASPH",      "lat": 26.6832, "lon":  -80.0956},
    {"icao": "KTPA", "name": "Tampa Intl",             "city": "Tampa",           "state": "FL", "region": "Southeast",    "runway_ft": 11002, "surface": "ASPH",      "lat": 27.9755, "lon":  -82.5332},
    {"icao": "KATL", "name": "Hartsfield-Jackson",     "city": "Atlanta",         "state": "GA", "region": "Southeast",    "runway_ft": 12390, "surface": "CONC",      "lat": 33.6407, "lon":  -84.4277},
    {"icao": "KCLT", "name": "Charlotte Douglas",      "city": "Charlotte",       "state": "NC", "region": "Southeast",    "runway_ft": 10000, "surface": "ASPH",      "lat": 35.2140, "lon":  -80.9431},
    {"icao": "KFLL", "name": "Fort Lauderdale",        "city": "Fort Lauderdale", "state": "FL", "region": "Southeast",    "runway_ft":  9000, "surface": "ASPH",      "lat": 26.0726, "lon":  -80.1527},
    # West
    {"icao": "KBVU", "name": "Boulder City Municipal", "city": "Boulder City",    "state": "NV", "region": "West",         "runway_ft":  4800, "surface": "ASPH",      "lat": 35.9474, "lon": -114.8609},
    {"icao": "KLAX", "name": "Los Angeles Intl",       "city": "Los Angeles",     "state": "CA", "region": "West",         "runway_ft": 12091, "surface": "ASPH-CONC", "lat": 33.9425, "lon": -118.4081},
    {"icao": "KSFO", "name": "San Francisco Intl",     "city": "San Francisco",   "state": "CA", "region": "West",         "runway_ft": 11870, "surface": "ASPH",      "lat": 37.6213, "lon": -122.3790},
    {"icao": "KSAN", "name": "San Diego Intl",         "city": "San Diego",       "state": "CA", "region": "West",         "runway_ft":  9401, "surface": "ASPH",      "lat": 32.7338, "lon": -117.1933},
    {"icao": "KLAS", "name": "Harry Reid Intl",        "city": "Las Vegas",       "state": "NV", "region": "West",         "runway_ft": 14510, "surface": "ASPH",      "lat": 36.0840, "lon": -115.1537},
    {"icao": "KDEN", "name": "Denver Intl",            "city": "Denver",          "state": "CO", "region": "West",         "runway_ft": 16000, "surface": "CONC",      "lat": 39.8561, "lon": -104.6737},
    {"icao": "KSDM", "name": "Brown Field",            "city": "San Diego",       "state": "CA", "region": "West",         "runway_ft":  7972, "surface": "ASPH",      "lat": 32.5723, "lon": -116.9800},
    {"icao": "KAPC", "name": "Napa County",            "city": "Napa",            "state": "CA", "region": "West",         "runway_ft":  5931, "surface": "ASPH",      "lat": 38.2132, "lon": -122.2807},
    # Midwest
    {"icao": "KORD", "name": "O'Hare Intl",            "city": "Chicago",         "state": "IL", "region": "Midwest",      "runway_ft": 13000, "surface": "CONC",      "lat": 41.9742, "lon":  -87.9073},
    {"icao": "KMSP", "name": "Minneapolis-St Paul",    "city": "Minneapolis",     "state": "MN", "region": "Midwest",      "runway_ft": 11006, "surface": "CONC",      "lat": 44.8820, "lon":  -93.2218},
    # Short-strip PC-12-only (competitive advantage)
    {"icao": "2B2",  "name": "Plum Island",            "city": "Newburyport",     "state": "MA", "region": "Northeast",    "runway_ft":  2700, "surface": "ASPH",      "lat": 42.7608, "lon":  -70.8394},
    {"icao": "K1B1", "name": "Hudson",                 "city": "Hudson",          "state": "NY", "region": "Northeast",    "runway_ft":  3600, "surface": "ASPH",      "lat": 42.2973, "lon":  -73.7120},
    {"icao": "KSFM", "name": "Sanford Seacoast",       "city": "Sanford",         "state": "ME", "region": "Northeast",    "runway_ft":  5200, "surface": "ASPH",      "lat": 43.3938, "lon":  -70.7080},
]
AIRPORT_MAP = {a["icao"]: a for a in AIRPORTS}

# Airport groups for route weighting (from regenerate_routes_v2)
BIZ_NE       = ["KTEB","KHPN","KEWR","KJFK","KBOS","KBDL","KPVD","KBED","KIAD","KPHL"]
BIZ_SE       = ["KATL","KCLT","KMIA","KTPA","KFLL"]
BIZ_MW       = ["KORD","KMSP"]
BIZ_WE       = ["KLAX","KSFO","KLAS","KDEN","KSAN"]
LEIS_SUM_NE  = ["KACK","KMVY","2B2","K1B1","KPWM","KSFM","KBDL","KPVD"]
LEIS_WIN_FL  = ["KMIA","KPBI","KFLL","KTPA"]
LEIS_WE      = ["KLAS","KSAN","KAPC","KLAX","KSFO"]
MEDICAL_HUBS = ["KBOS","KJFK","KEWR","KPHL","KIAD","KATL","KBDL"]
PC12_FAVS    = ["KACK","KMVY","2B2","K1B1","KSFM","KPWM","KBED","KMHT"]

# =============================================================================
# OWNER SHARE TYPES — correct format from day 1 (no Excel date-parsing issue)
# =============================================================================
SHARE_TYPES = [
    {"type": "Share_1/16", "annual_hours": 100, "weight": 0.35},
    {"type": "Share_1/8",  "annual_hours": 200, "weight": 0.30},
    {"type": "Share_1/4",  "annual_hours": 400, "weight": 0.15},
    # Cobalt pass holders handled separately (12% of owners, 25 hrs/yr)
]
COBALT_FRAC = 0.12   # 12% of owners are Cobalt pass holders

# =============================================================================
# JASC CODES — calibrated from SDRS PC-12/PC-24 data
# =============================================================================
JASC_CODES = [
    {"code": "2752", "system": "Flight Controls", "name": "Rudder Control System",    "w12": 0.08, "w24": 0.03},
    {"code": "7200", "system": "Engine",           "name": "Engine (General)",         "w12": 0.07, "w24": 0.05},
    {"code": "2750", "system": "Flight Controls", "name": "Flight Control System",    "w12": 0.07, "w24": 0.04},
    {"code": "3242", "system": "Landing Gear",    "name": "Brake Assembly",           "w12": 0.05, "w24": 0.07},
    {"code": "2497", "system": "Empennage",       "name": "Stabilizer Assembly",      "w12": 0.04, "w24": 0.02},
    {"code": "5610", "system": "Instruments",     "name": "Flight Instruments",       "w12": 0.04, "w24": 0.11},
    {"code": "7230", "system": "Engine",           "name": "Engine Fuel & Control",    "w12": 0.03, "w24": 0.03},
    {"code": "3418", "system": "Ice Protection",  "name": "Ice Protection (Airframe)","w12": 0.03, "w24": 0.02},
    {"code": "3230", "system": "Landing Gear",    "name": "Nose Gear Steering",       "w12": 0.03, "w24": 0.02},
    {"code": "2140", "system": "Fuselage",        "name": "Fuselage Structure",       "w12": 0.03, "w24": 0.08},
    {"code": "3260", "system": "Landing Gear",    "name": "Wheel/Tire Assembly",      "w12": 0.02, "w24": 0.04},
    {"code": "7321", "system": "Engine",           "name": "Engine Control System",    "w12": 0.02, "w24": 0.03},
    {"code": "3240", "system": "Landing Gear",    "name": "Brake System (General)",   "w12": 0.02, "w24": 0.07},
    {"code": "2932", "system": "Hydraulics",      "name": "Hydraulic Valve",          "w12": 0.02, "w24": 0.03},
    {"code": "5230", "system": "Avionics",        "name": "Communications System",    "w12": 0.02, "w24": 0.03},
    {"code": "3457", "system": "APU",             "name": "Auxiliary Power Unit",     "w12": 0.02, "w24": 0.02},
    {"code": "3020", "system": "Landing Gear",    "name": "Main Landing Gear",        "w12": 0.02, "w24": 0.03},
    {"code": "2435", "system": "Empennage",       "name": "Elevator Assembly",        "w12": 0.02, "w24": 0.01},
    {"code": "3411", "system": "Pneumatics",      "name": "Pitot/Static System",      "w12": 0.01, "w24": 0.02},
    {"code": "2411", "system": "Electrical",      "name": "Generator/Alternator",     "w12": 0.02, "w24": 0.02},
]

# =============================================================================
# MAINTENANCE COST TARGETS
# (applied in-memory to fact_maintenance_detail before writing CSV)
# =============================================================================
# BOOST months: heavy scheduled inspections → parts > labor, ratio 1.40x
BOOST_MONTHS   = {"2023-03","2024-03","2025-03","2023-10","2024-10","2025-10"}
# REVERT months: accidental outlier spikes reverted → parts < labor, ratio 0.70x
REVERT_MONTHS  = {"2023-01","2023-07","2023-12"}
# AOG-heavy months: emergency labor uplift + parts raised to 1.40x
AOG_BOOST_MONTHS = {"2023-05": 6, "2023-06": 5, "2024-05": 12}   # value = AOG days
COST_BOOST_RATIO  = 1.40
COST_REVERT_RATIO = 0.70
LABOR_MULT        = 1.25   # emergency overtime in AOG months

# AOG emergency part costs (from fix_aog_costs — used if PARTS row is missing)
AOG_PART_COSTS = {
    "2700": ("Brake Assembly - Emergency Replace",       4800,  1),
    "7200": ("Engine Fuel Control Unit - AOG Replace",  28500,  1),
    "2900": ("Hydraulic Actuator - AOG Replace",         6200,  1),
    "2400": ("Electrical Relay Pack - AOG Replace",      3400,  2),
    "3200": ("Main Gear Strut Seal Kit - AOG Replace",   2100,  1),
    "7100": ("Turbine Inlet Temp Sensor - AOG Replace",  5600,  1),
    "2500": ("Avionics LRU - AOG Replace",              12800,  1),
    "2800": ("Fuel Boost Pump - AOG Replace",            3900,  1),
}
DEFAULT_AOG_PART = ("Unscheduled Component Replace - AOG", 4500, 1)

# =============================================================================
# DAILY STATUS TARGETS
# =============================================================================
# Phase A: initial seasonal FLYING%/MAINT% distribution
MONTH_TARGETS = {
    1:  (0.78, 0.080),   # Winter
    2:  (0.78, 0.080),
    3:  (0.84, 0.140),   # Spring + heavy inspection
    4:  (0.85, 0.080),
    5:  (0.85, 0.120),   # Spring + AOG month
    6:  (0.90, 0.070),   # Summer peak
    7:  (0.90, 0.070),
    8:  (0.90, 0.075),
    9:  (0.85, 0.080),   # Fall
    10: (0.84, 0.140),   # Fall + heavy inspection
    11: (0.82, 0.090),
    12: (0.78, 0.080),   # Winter
}
MAINT_TYPE_BY_MONTH = {
    3:  ["INSPECTION","INSPECTION","INSPECTION","COMPONENT_REPLACEMENT","LINE_MAINTENANCE"],
    10: ["INSPECTION","INSPECTION","INSPECTION","COMPONENT_REPLACEMENT","LINE_MAINTENANCE"],
    5:  ["INSPECTION","LINE_MAINTENANCE","COMPONENT_REPLACEMENT","TROUBLESHOOTING"],
}
DEFAULT_MAINT_TYPES = ["INSPECTION","LINE_MAINTENANCE","TROUBLESHOOTING"]

# Phase B: AOG exactly per year
AOG_TARGETS = {3: 6, 5: 8, 10: 6}   # month → days per year

# Phase D: FLYING/AVAILABLE rebalance per date window
PERIOD_TARGETS = {
    "holiday":     0.82,   # Dec 20–Jan 5 (peak demand)
    "dec_non_hol": 0.64,   # Dec 1–19
    "jan_non_hol": 0.64,   # Jan 6–31
    "winter_rest": 0.64,   # Feb
    "march":       0.72,
    "april":       0.76,
    "may":         0.75,
    "summer":      0.82,   # Jun–Aug
    "fall":        0.76,   # Sep, Nov
    "october":     0.72,
}

# =============================================================================
# RATES
# =============================================================================
LABOR_RATE_HR = 115   # $/hr A&P
CERT_RATE_HR  = 135   # $/hr IA signoff
FUEL_COST_GAL = 6.80  # Jet-A $/gal

SEASONAL = {1: 1.05, 2: 0.85, 3: 0.95, 4: 1.00, 5: 1.05, 6: 1.15,
            7: 1.20, 8: 1.15, 9: 1.05, 10: 1.00, 11: 0.90, 12: 0.95}

# =============================================================================
# HELPERS
# =============================================================================
def write_csv(filename, rows, fieldnames):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  {filename}: {len(rows)} rows")
    return path


def haversine_nm(lat1, lon1, lat2, lon2):
    R = 3440.065   # Earth radius in nautical miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def get_season(month):
    return {12:"Winter",1:"Winter",2:"Winter",
            3:"Spring",4:"Spring",5:"Spring",
            6:"Summer",7:"Summer",8:"Summer",
            9:"Fall",10:"Fall",11:"Fall"}[month]


def build_dest_weights(model, purpose, season, owner_region, base_facility, origin_icao):
    """Return dict {icao: weight} for destination selection."""
    is_pc12 = model == "PC-12 NGX"
    max_nm  = PERF[model]["max_nm"]
    origin  = AIRPORT_MAP.get(origin_icao)

    weights = {}
    for ap in AIRPORTS:
        icao = ap["icao"]
        if icao == origin_icao:
            continue
        # Accessibility constraint
        if is_pc12 and ap["runway_ft"] < 2500:
            continue
        if not is_pc12 and ap["runway_ft"] < 3810:
            continue
        # Range constraint
        if origin:
            dist = haversine_nm(origin["lat"], origin["lon"], ap["lat"], ap["lon"])
            if dist > max_nm:
                continue
        w = 1.0
        region = ap["region"]

        if purpose == "Business":
            if icao in BIZ_NE: w += 8.0
            if icao in BIZ_SE: w += 4.0
            if icao in BIZ_MW: w += 3.0
            if icao in BIZ_WE: w += 2.0
            if is_pc12 and icao in PC12_FAVS: w += 0.5

        elif purpose == "Leisure":
            if season == "Summer":
                if icao in LEIS_SUM_NE: w += 10.0
                if icao in LEIS_WIN_FL: w += 1.0
                if icao in LEIS_WE:     w += 2.0
                if is_pc12 and icao in PC12_FAVS: w += 0.3
            elif season == "Winter":
                if icao in LEIS_WIN_FL: w += 10.0
                if icao in LEIS_SUM_NE: w += 2.0
                if icao in LEIS_WE:     w += 4.0
                if is_pc12 and icao in PC12_FAVS: w += 0.5
            else:   # Spring/Fall
                if icao in LEIS_SUM_NE: w += 5.0
                if icao in LEIS_WIN_FL: w += 4.0
                if icao in LEIS_WE:     w += 3.0
                if is_pc12 and icao in PC12_FAVS: w += 0.5

        elif purpose == "Medical":
            if icao in MEDICAL_HUBS: w += 12.0

        elif purpose in ("Mixed", "Repositioning"):
            if icao in BIZ_NE: w += 4.0
            if season == "Summer" and icao in LEIS_SUM_NE: w += 4.0
            if season == "Winter" and icao in LEIS_WIN_FL: w += 4.0

        # Owner region bias
        owner_bias = {
            "Northeast":   {"Northeast": 2.5, "Mid-Atlantic": 1.5},
            "Mid-Atlantic":{"Northeast": 2.0, "Mid-Atlantic": 2.0, "Southeast": 1.3},
            "Southeast":   {"Southeast": 2.5, "Northeast": 1.3, "Mid-Atlantic": 1.3},
            "West":        {"West": 3.0, "Midwest": 1.2},
            "Midwest":     {"Midwest": 2.0, "Northeast": 1.3, "Southeast": 1.3},
        }
        w *= owner_bias.get(owner_region, {}).get(region, 1.0)

        # Base facility bias (KBVU-based → West)
        if base_facility == "FAC-BVU":
            if region == "West":    w *= 3.0
            if region == "Midwest": w *= 1.5

        weights[icao] = max(0.01, w)
    return weights


def pick_weighted(weights, exclude=None):
    pool = [(icao, w) for icao, w in weights.items() if icao != exclude]
    if not pool:
        return list(weights.keys())[0]
    total = sum(w for _, w in pool)
    r = random.random() * total
    cum = 0.0
    for icao, w in pool:
        cum += w
        if r <= cum:
            return icao
    return pool[-1][0]


def calc_flight_fields(origin_icao, dest_icao, model, dep_dt):
    """Calculate distance_nm, flight_hours, block_hours, fuel_consumed_gal, arrival_time.

    Applies a practical minimum flight time (0.8h PC-12 / 1.0h PC-24) reflecting
    fractional aviation operations where short hops still incur climb/descent/taxi time
    and operators rarely book legs under ~30-45 minutes airborne.
    """
    o = AIRPORT_MAP.get(origin_icao)
    d = AIRPORT_MAP.get(dest_icao)
    perf   = PERF[model]
    min_fh = 0.8 if model == "PC-12 NGX" else 1.0   # practical minimum leg
    if o and d:
        raw_dist = haversine_nm(o["lat"], o["lon"], d["lat"], d["lon"])
        # Blend actual distance with a minimum effective range to avoid unrealistically
        # short legs on nearby airports (e.g. KPSM→KBOS = 56nm)
        eff_dist = max(raw_dist, min_fh * perf["cruise_kts"])
        dist = round(eff_dist, 0)
    else:
        dist = round(perf["cruise_kts"] * 1.5, 0)
    flight_hrs = round(max(min_fh, dist / perf["cruise_kts"]), 2)
    block_hrs  = round(flight_hrs * perf["block_factor"], 2)
    fuel_gal   = round(flight_hrs * perf["fuel_gph"] * random.uniform(0.95, 1.05), 1)
    arr_dt     = dep_dt + timedelta(hours=block_hrs)
    return int(dist), flight_hrs, block_hrs, fuel_gal, arr_dt


def owner_type(share_type, aircraft_preference):
    """Derive owner_type from share type and aircraft preference."""
    if share_type in ("Share_1/4", "Share_1/8"):
        return "Corporate"
    if share_type == "Cobalt":
        return "Individual"
    # Share_1/16
    if aircraft_preference == "PC-24":
        return "Corporate"
    return "Individual"


# =============================================================================
# GENERATORS
# =============================================================================

def gen_dim_date():
    rows = []
    d = SIM_START
    while d <= SIM_END:
        rows.append({
            "date_key":        d.strftime("%Y%m%d"),
            "date":            d.isoformat(),
            "day":             d.day,
            "day_of_week":     d.strftime("%A"),
            "day_of_week_num": d.isoweekday(),
            "is_weekend":      1 if d.isoweekday() >= 6 else 0,
            "week_num":        d.isocalendar()[1],
            "month":           d.month,
            "month_name":      d.strftime("%B"),
            "quarter":         (d.month - 1) // 3 + 1,
            "year":            d.year,
            "season":          get_season(d.month),
            "is_holiday":      1 if (d.month, d.day) in [(1,1),(7,4),(12,25),(11,28),(12,31)] else 0,
            "fiscal_year":     d.year if d.month >= 7 else d.year - 1,
        })
        d += timedelta(days=1)
    write_csv("dim_date.csv", rows, list(rows[0].keys()))
    return rows


def gen_dim_aircraft():
    rows = []
    for i in range(PC12_COUNT):
        yr = random.choices(range(2017, 2025), weights=[3,5,8,10,12,10,6,4])[0]
        delivery = date(yr, random.randint(1,12), random.randint(1,28))
        base = "FAC-PSM" if i < 32 else "FAC-BVU"
        rows.append({
            "aircraft_id":        f"AC-{i+1:03d}",
            "tail_number":        f"N{100+i}AF",
            "model":              "PC-12 NGX",
            "engine_type":        "PT6A-67P",
            "engine_count":       1,
            "serial_number":      f"PC12-{1700+i}",
            "delivery_date":      delivery.isoformat(),
            "years_in_service":   round((SNAPSHOT - delivery).days / 365.25, 1),
            "base_facility_id":   base,
            "region":             "Northeast" if base == "FAC-PSM" else "West",
            "seat_capacity":      10,
            "max_range_nm":       1845,
            "current_status":     "ACTIVE",
            "maintenance_program":"PHASE_INSPECTION",
        })
    for i in range(PC24_COUNT):
        yr = random.choices(range(2018, 2026), weights=[3,4,6,8,10,8,5,3])[0]
        delivery = date(yr, random.randint(1,12), random.randint(1,28))
        base = "FAC-PSM" if i < 11 else "FAC-BVU"
        rows.append({
            "aircraft_id":        f"AC-{PC12_COUNT+i+1:03d}",
            "tail_number":        f"N{800+i}AF",
            "model":              "PC-24",
            "engine_type":        "FJ44-4A",
            "engine_count":       2,
            "serial_number":      f"PC24-{200+i}",
            "delivery_date":      delivery.isoformat(),
            "years_in_service":   round((SNAPSHOT - delivery).days / 365.25, 1),
            "base_facility_id":   base,
            "region":             "Northeast" if base == "FAC-PSM" else "West",
            "seat_capacity":      11,
            "max_range_nm":       2000,
            "current_status":     "ACTIVE",
            "maintenance_program":"PHASE_INSPECTION",
        })
    write_csv("dim_aircraft.csv", rows, list(rows[0].keys()))
    return rows


def gen_dim_airport():
    rows = []
    for a in AIRPORTS:
        rows.append({
            "airport_icao":     a["icao"],
            "airport_name":     a["name"],
            "city":             a["city"],
            "state":            a["state"],
            "region":           a["region"],
            "runway_length_ft": a["runway_ft"],
            "runway_surface":   a["surface"],
            "pc12_accessible":  1,
            "pc24_accessible":  1 if a["runway_ft"] >= 3810 else 0,
            "latitude":         a["lat"],
            "longitude":        a["lon"],
        })
    write_csv("dim_airport.csv", rows, list(rows[0].keys()))
    return rows


def gen_dim_component():
    rows = [{
        "component_id":      f"COMP-{j['code']}",
        "jasc_ata_code":     j["code"],
        "system_name":       j["system"],
        "component_name":    j["name"],
        "sdrs_weight_pc12":  j["w12"],
        "sdrs_weight_pc24":  j["w24"],
    } for j in JASC_CODES]
    write_csv("dim_component.csv", rows, list(rows[0].keys()))
    return rows


def gen_dim_crew():
    fnames = ["James","Robert","Michael","William","David","Richard","Joseph","Thomas",
              "Sarah","Jennifer","Lisa","Emily","Amanda","Jessica","Michelle","Karen",
              "Daniel","Mark","Steven","Andrew","Brian","Kevin","Timothy","Christopher"]
    lnames = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
              "Rodriguez","Martinez","Hernandez","Lopez","Wilson","Anderson","Thomas","Taylor"]
    rows = []
    for i in range(80):
        base = "FAC-PSM" if i < 56 else "FAC-BVU"
        if i < 20:   ratings = "PC-12,PC-24"
        elif i < 55: ratings = "PC-12"
        else:        ratings = "PC-24" if i >= 60 else "PC-12"
        rows.append({
            "crew_id":          f"CREW-{i+1:03d}",
            "crew_name":        f"{random.choice(fnames)} {random.choice(lnames)}",
            "role":             "Captain" if i % 3 != 2 else "First Officer",
            "base_facility_id": base,
            "type_ratings":     ratings,
        })
    for i in range(40):
        base = "FAC-PSM" if i < 28 else "FAC-BVU"
        rows.append({
            "crew_id":          f"TECH-{i+1:03d}",
            "crew_name":        f"{random.choice(fnames)} {random.choice(lnames)}",
            "role":             "A&P Mechanic" if i % 4 != 0 else "IA Inspector",
            "base_facility_id": base,
            "type_ratings":     "PC-12,PC-24",
        })
    write_csv("dim_crew.csv", rows, list(rows[0].keys()))
    return rows


def gen_dim_facility():
    rows = [{"facility_id": f["id"], "facility_name": f["name"], "icao": f["icao"],
             "state": f["state"], "type": f["type"],
             "technician_count": f["technician_count"], "maintenance_bays": f["bays"]}
            for f in FACILITIES]
    write_csv("dim_facility.csv", rows, list(rows[0].keys()))
    return rows


def gen_dim_owner():
    fnames = ["Catherine","George","Michael","Sarah","Robert","Jennifer","William","Emily",
              "James","Amanda","David","Lisa","Richard","Karen","Thomas","Jessica",
              "Daniel","Michelle","Steven","Laura","Andrew","Nicole","Brian","Rebecca",
              "Kevin","Stephanie","Mark","Heather","Timothy","Rachel"]
    lnames = ["Morris","Chen","Patel","Thompson","Garcia","Williams","Johnson","Brown",
              "Martinez","Anderson","Taylor","Thomas","Wilson","Clark","Lewis","Robinson",
              "Hall","Young","Walker","Allen","King","Wright","Scott","Hill"]
    regions = ["Northeast","Mid-Atlantic","Southeast","Midwest","West"]
    rweights = [0.30, 0.20, 0.18, 0.15, 0.17]
    states = {"Northeast": ["NH","MA","CT","RI","ME","VT","NY"],
              "Mid-Atlantic": ["NJ","PA","VA","MD","DC"],
              "Southeast": ["FL","GA","NC","SC","TN"],
              "Midwest": ["IL","OH","MI","MN","WI"],
              "West": ["CA","NV","CO","AZ","WA"]}

    share_labels  = [s["type"] for s in SHARE_TYPES]
    share_weights = [s["weight"] for s in SHARE_TYPES]
    share_hours   = {s["type"]: s["annual_hours"] for s in SHARE_TYPES}

    rows = []
    for i in range(350):
        region = random.choices(regions, weights=rweights)[0]
        is_cobalt = random.random() < COBALT_FRAC
        if is_cobalt:
            share = "Cobalt"
            hours = 25
        else:
            share = random.choices(share_labels, weights=share_weights)[0]
            hours = share_hours[share]
        join_yr   = random.choices(range(2015,2026), weights=[2,3,4,5,6,7,8,10,12,10,8])[0]
        join_date = date(join_yr, random.randint(1,12), random.randint(1,28))
        pref      = random.choices(["PC-12","PC-24","No Preference"], weights=[0.55,0.25,0.20])[0]
        rows.append({
            "owner_id":                 f"OWN-{i+1:04d}",
            "owner_name":               f"{random.choice(fnames)} {random.choice(lnames)}",
            "region":                   region,
            "state":                    random.choice(states[region]),
            "share_type":               share,
            "annual_hours_contracted":  hours,
            "join_date":                join_date.isoformat(),
            "tenure_years":             round((SNAPSHOT - join_date).days / 365.25, 1),
            "aircraft_preference":      pref,
            "cobalt_pass_holder":       1 if is_cobalt else 0,
            "jetfly_access":            1 if region in ("Northeast","Mid-Atlantic") and random.random() < 0.12 else 0,
            "status":                   "ACTIVE" if random.random() < 0.91 else "CHURNED",
            "owner_type":               "Individual" if is_cobalt else owner_type(share, pref),
        })
    write_csv("dim_owner.csv", rows, list(rows[0].keys()))
    return rows


def gen_fact_flight(aircraft, owners):
    print("  Generating flights (this takes a moment)...")
    flights    = []
    flight_id  = 0
    active_owners = [o for o in owners if o["status"] == "ACTIVE"]

    # Departure hour pools by purpose
    dep_hours = {
        "Business":          [6,6,7,7,7,8,8,9,10,11,13,14,15,16,17],
        "Leisure":           [8,9,9,10,10,10,11,11,12,13,14,15,16],
        "Medical":           [6,7,7,8,8,9,9,10,11],
        "Maintenance Ferry": [6,7,8,9,10],
        "Repositioning":     [7,8,9,10,11,12,13,14,15],
        "Mixed":             [7,8,9,10,11,12,13,14,15],
    }

    all_dates = []
    d = SIM_START
    while d <= SIM_END:
        all_dates.append(d)
        d += timedelta(days=1)

    for ac in aircraft:
        delivery    = date.fromisoformat(ac["delivery_date"])
        model       = ac["model"]
        is_pc12     = model == "PC-12 NGX"
        base_fac    = ac["base_facility_id"]
        base_icao   = "KPSM" if base_fac == "FAC-PSM" else "KBVU"
        ac_region   = ac["region"]
        avg_leg     = 1.05 if is_pc12 else 1.45
        avg_hrs_yr  = 1150 if is_pc12 else 1350
        avg_flt_day = avg_hrs_yr / 365 / avg_leg

        current_loc = base_icao

        for d in all_dates:
            if d < delivery:
                continue

            n_flights = max(0, int(random.gauss(avg_flt_day * SEASONAL[d.month], 0.8)))
            if random.random() < 0.08:
                n_flights = 0

            season = get_season(d.month)
            dow    = d.isoweekday()   # 1=Mon … 7=Sun

            for _ in range(n_flights):
                flight_id += 1

                is_deadhead   = random.random() < 0.15
                is_maint_fry  = random.random() < 0.03
                owner         = None
                dest          = base_icao   # default; overridden below
                if is_maint_fry:
                    purpose = "Maintenance Ferry"
                    pax     = 0
                elif is_deadhead:
                    purpose = "Repositioning"
                    pax     = 0
                else:
                    purpose = random.choices(
                        ["Business","Leisure","Medical","Mixed"],
                        weights=[0.55,0.28,0.05,0.12]
                    )[0]
                    pax = random.choices([1,2,3,4,5,6,7,8], weights=[15,20,25,18,10,7,3,2])[0]

                origin = current_loc

                # KPSM hub dominance for NE/Mid-Atlantic owners at FAC-PSM
                if (base_fac == "FAC-PSM" and ac_region == "Northeast"
                        and purpose not in ("Maintenance Ferry","Repositioning")
                        and random.random() < 0.40):
                    origin = "KPSM"

                if not is_maint_fry:
                    owner    = random.choice(active_owners) if pax > 0 else None
                    o_region = owner["region"] if owner else ac_region
                    wts  = build_dest_weights(model, purpose, season, o_region, base_fac, origin)
                    dest = pick_weighted(wts, exclude=origin)

                # Departure time
                hour    = random.choice(dep_hours.get(purpose, dep_hours["Mixed"]))
                dep_dt  = datetime(d.year, d.month, d.day, hour, random.randint(0,59))
                dist, fh, bh, fuel, arr_dt = calc_flight_fields(origin, dest, model, dep_dt)

                # Weather delay (winter NE)
                weather_delay = 0
                if d.month in (1,2,12) and ac_region == "Northeast":
                    if random.random() < 0.12:
                        weather_delay = random.choice([15,30,45,60,90,120])
                elif random.random() < 0.04:
                    weather_delay = random.choice([15,30,45])

                pilot_id   = f"CREW-{random.randint(1,80):03d}"
                copilot_id = f"CREW-{random.randint(1,80):03d}" if not is_pc12 or random.random() < 0.3 else ""

                flights.append({
                    "flight_id":           f"FLT-{flight_id:07d}",
                    "date":                d.isoformat(),
                    "aircraft_id":         ac["aircraft_id"],
                    "tail_number":         ac["tail_number"],
                    "model":               model,
                    "owner_id":            owner["owner_id"] if owner else "",
                    "booking_id":          f"BK-{flight_id:07d}" if pax > 0 else "",
                    "journey_leg_seq":     1,
                    "origin_icao":         origin,
                    "destination_icao":    dest,
                    "departure_time":      dep_dt.strftime("%Y-%m-%d %H:%M"),
                    "arrival_time":        arr_dt.strftime("%Y-%m-%d %H:%M"),
                    "block_hours":         bh,
                    "flight_hours":        fh,
                    "distance_nm":         dist,
                    "passenger_count":     pax,
                    "flight_purpose":      purpose,
                    "is_deadhead":         1 if is_deadhead else 0,
                    "is_maintenance_ferry":1 if is_maint_fry else 0,
                    "flight_status":       "COMPLETED",
                    "fuel_consumed_gal":   fuel,
                    "weather_delay_min":   weather_delay,
                    "pilot_id":            pilot_id,
                    "copilot_id":          copilot_id,
                    "season":              season,
                    "day_of_week":         dow,
                })
                current_loc = dest

    write_csv("fact_flight.csv", flights, list(flights[0].keys()))
    return flights


def gen_fact_booking(flights, owners):
    bookings   = []
    seen       = set()
    active_owners = [o for o in owners if o["status"] == "ACTIVE"]
    purposes   = ["Business","Leisure","Medical","Mixed"]
    pw         = [0.55,0.28,0.05,0.12]

    for f in flights:
        bid = f["booking_id"]
        if not bid or bid in seen:
            continue
        seen.add(bid)
        fdate     = date.fromisoformat(f["date"])
        lead_days = max(1, int(random.expovariate(1/7) + 1))
        owner     = next((o for o in owners if o["owner_id"] == f["owner_id"]), None)
        bookings.append({
            "booking_id":       bid,
            "booking_date":     (fdate - timedelta(days=lead_days)).isoformat(),
            "owner_id":         f["owner_id"],
            "passenger_count":  f["passenger_count"],
            "pet_count":        1 if random.random() < 0.08 else 0,
            "preferred_model":  owner["aircraft_preference"] if owner else "",
            "departure_date":   f["date"],
            "origin_icao":      f["origin_icao"],
            "destination_icao": f["destination_icao"],
            "trip_purpose":     f["flight_purpose"],
            "booking_status":   "COMPLETED",
            "booking_channel":  random.choices(["Phone","Mobile App","Owner Portal","Account Manager"],
                                               weights=[0.25,0.35,0.25,0.15])[0],
            "lead_time_days":   lead_days,
        })

    # ~5% cancelled bookings
    for i in range(int(len(bookings) * 0.05)):
        owner   = random.choice(active_owners)
        fdate   = SIM_START + timedelta(days=random.randint(0,(SIM_END-SIM_START).days))
        ld      = max(1, int(random.expovariate(1/5) + 1))
        origin  = random.choice(AIRPORTS)["icao"]
        dest    = random.choice([a["icao"] for a in AIRPORTS if a["icao"] != origin])
        bookings.append({
            "booking_id":       f"BK-C{i+1:06d}",
            "booking_date":     (fdate - timedelta(days=ld)).isoformat(),
            "owner_id":         owner["owner_id"],
            "passenger_count":  random.randint(1,5),
            "pet_count":        0,
            "preferred_model":  owner["aircraft_preference"],
            "departure_date":   fdate.isoformat(),
            "origin_icao":      origin,
            "destination_icao": dest,
            "trip_purpose":     random.choices(purposes, weights=pw)[0],
            "booking_status":   random.choice(["CANCELLED","NO_SHOW"]),
            "booking_channel":  random.choice(["Phone","Mobile App","Owner Portal","Account Manager"]),
            "lead_time_days":   ld,
        })

    write_csv("fact_booking.csv", bookings, list(bookings[0].keys()))
    return bookings


def gen_maintenance(aircraft, flights):
    print("  Generating maintenance jobs...")
    jobs    = []
    details = []
    job_id  = 0
    det_id  = 0

    ac_timeline = defaultdict(list)
    for f in flights:
        ac_timeline[f["aircraft_id"]].append((date.fromisoformat(f["date"]), f["flight_hours"]))

    jw12 = [j["w12"] for j in JASC_CODES]
    jw24 = [j["w24"] for j in JASC_CODES]

    MAINT_TYPES = [
        {"type": "100HR_INSPECTION", "is_scheduled": True,  "severity": "ROUTINE",  "avg_dur": 12, "avg_lab": 8},
        {"type": "200HR_INSPECTION", "is_scheduled": True,  "severity": "ROUTINE",  "avg_dur": 24, "avg_lab": 16},
        {"type": "LINE_MAINTENANCE", "is_scheduled": False, "severity": "MINOR",    "avg_dur":  6, "avg_lab":  4},
        {"type": "COMPONENT_REPLACEMENT","is_scheduled": False,"severity": "MODERATE","avg_dur": 18,"avg_lab": 10},
        {"type": "AOG_REPAIR",       "is_scheduled": False, "severity": "AOG",      "avg_dur": 48, "avg_lab": 24},
        {"type": "TROUBLESHOOTING",  "is_scheduled": False, "severity": "MINOR",    "avg_dur":  8, "avg_lab":  6},
    ]

    def add_labor(job_mid, d_str, ac_id, fac, desc, hours, rate=LABOR_RATE_HR, action="INSPECT", jasc=""):
        nonlocal det_id
        det_id += 1
        details.append({
            "detail_id":         f"MD-{det_id:07d}",
            "maintenance_job_id": job_mid,
            "date":              d_str,
            "aircraft_id":       ac_id,
            "facility_id":       fac,
            "action_type":       action,
            "cost_category":     "LABOR",
            "jasc_ata_code":     jasc,
            "part_description":  desc,
            "uom":               "Hours",
            "quantity":          round(hours, 1),
            "unit_cost":         rate,
            "extended_cost":     round(hours * rate, 2),
        })

    def add_parts(job_mid, d_str, ac_id, fac, jasc, desc, qty, unit_cost, action="REPLACE"):
        nonlocal det_id
        det_id += 1
        details.append({
            "detail_id":         f"MD-{det_id:07d}",
            "maintenance_job_id": job_mid,
            "date":              d_str,
            "aircraft_id":       ac_id,
            "facility_id":       fac,
            "action_type":       action,
            "cost_category":     "PARTS",
            "jasc_ata_code":     jasc,
            "part_description":  desc,
            "uom":               "Each",
            "quantity":          qty,
            "unit_cost":         unit_cost,
            "extended_cost":     round(unit_cost * qty, 2),
        })

    def add_cert(job_mid, d_str, ac_id, fac):
        nonlocal det_id
        det_id += 1
        hrs = round(random.uniform(1.5, 4.0), 1)
        details.append({
            "detail_id":         f"MD-{det_id:07d}",
            "maintenance_job_id": job_mid,
            "date":              d_str,
            "aircraft_id":       ac_id,
            "facility_id":       fac,
            "action_type":       "CERTIFY",
            "cost_category":     "CERTIFICATION",
            "jasc_ata_code":     "",
            "part_description":  "IA Return-to-Service",
            "uom":               "Hours",
            "quantity":          hrs,
            "unit_cost":         CERT_RATE_HR,
            "extended_cost":     round(hrs * CERT_RATE_HR, 2),
        })

    for ac in aircraft:
        is_pc12  = ac["model"] == "PC-12 NGX"
        fac      = ac["base_facility_id"]
        jw       = jw12 if is_pc12 else jw24
        timeline = sorted(ac_timeline.get(ac["aircraft_id"], []))

        cum_hrs   = 0.0
        last_100  = 0.0
        last_200  = 0.0

        for d, hrs in timeline:
            cum_hrs += hrs
            ds = d.isoformat()

            # 100-hour inspection
            if cum_hrs - last_100 >= 100:
                last_100 = cum_hrs
                job_id += 1
                mid = f"MJ-{job_id:06d}"
                dur = max(4, random.gauss(12, 2.4))
                start = datetime(d.year, d.month, d.day, 7, 0)
                finding = random.choices(
                    ["NO_FINDING","WEAR_WITHIN_LIMITS","MINOR_DEFECT","REPLACEMENT_REQUIRED"],
                    weights=[0.55, 0.25, 0.14, 0.06])[0]
                jobs.append({
                    "maintenance_job_id":   mid,
                    "date":                 ds,
                    "aircraft_id":          ac["aircraft_id"],
                    "tail_number":          ac["tail_number"],
                    "facility_id":          fac,
                    "maintenance_type":     "100HR_INSPECTION",
                    "is_scheduled":         1,
                    "severity":             "ROUTINE",
                    "trigger_source":       "SCHEDULED",
                    "job_status":           "COMPLETED",
                    "start_datetime":       start.strftime("%Y-%m-%d %H:%M"),
                    "close_datetime":       (start + timedelta(hours=dur)).strftime("%Y-%m-%d %H:%M"),
                    "total_elapsed_hours":  round(dur, 1),
                    "finding_code":         finding,
                    "technician_id":        f"TECH-{random.randint(1,40):03d}",
                    "aircraft_hours_at_event": round(cum_hrs, 1),
                })
                add_labor(mid, ds, ac["aircraft_id"], fac, "Inspection Labor",
                          max(2, random.gauss(8, 2)))
                add_cert(mid, ds, ac["aircraft_id"], fac)
                fuel_gal = round(random.uniform(20, 60), 1)
                det_id += 1
                details.append({
                    "detail_id": f"MD-{det_id:07d}", "maintenance_job_id": mid,
                    "date": ds, "aircraft_id": ac["aircraft_id"], "facility_id": fac,
                    "action_type": "SERVICE", "cost_category": "FUEL",
                    "jasc_ata_code": "", "part_description": "Jet-A Fuel (ground run)",
                    "uom": "Gallons", "quantity": fuel_gal,
                    "unit_cost": FUEL_COST_GAL, "extended_cost": round(fuel_gal * FUEL_COST_GAL, 2),
                })
                if finding == "REPLACEMENT_REQUIRED":
                    jasc = random.choices(JASC_CODES, weights=jw)[0]
                    add_parts(mid, ds, ac["aircraft_id"], fac, jasc["code"], jasc["name"],
                              1, random.choice([420,680,1500,2200,3800,4500,9500]))

            # 200-hour inspection
            if cum_hrs - last_200 >= 200:
                last_200 = cum_hrs
                job_id += 1
                mid = f"MJ-{job_id:06d}"
                dur = max(8, random.gauss(24, 4))
                start = datetime(d.year, d.month, d.day, 7, 0)
                finding = random.choices(
                    ["NO_FINDING","WEAR_WITHIN_LIMITS","MINOR_DEFECT","REPLACEMENT_REQUIRED"],
                    weights=[0.45, 0.30, 0.17, 0.08])[0]
                jobs.append({
                    "maintenance_job_id":   mid,
                    "date":                 ds,
                    "aircraft_id":          ac["aircraft_id"],
                    "tail_number":          ac["tail_number"],
                    "facility_id":          fac,
                    "maintenance_type":     "200HR_INSPECTION",
                    "is_scheduled":         1,
                    "severity":             "ROUTINE",
                    "trigger_source":       "SCHEDULED",
                    "job_status":           "COMPLETED",
                    "start_datetime":       start.strftime("%Y-%m-%d %H:%M"),
                    "close_datetime":       (start + timedelta(hours=dur)).strftime("%Y-%m-%d %H:%M"),
                    "total_elapsed_hours":  round(dur, 1),
                    "finding_code":         finding,
                    "technician_id":        f"TECH-{random.randint(1,40):03d}",
                    "aircraft_hours_at_event": round(cum_hrs, 1),
                })
                add_labor(mid, ds, ac["aircraft_id"], fac, "200hr Inspection Labor",
                          max(6, random.gauss(16, 3)))
                add_cert(mid, ds, ac["aircraft_id"], fac)
                if finding in ("MINOR_DEFECT","REPLACEMENT_REQUIRED"):
                    jasc = random.choices(JASC_CODES, weights=jw)[0]
                    repair_hrs = round(random.uniform(2, 8), 1)
                    if finding == "REPLACEMENT_REQUIRED":
                        add_parts(mid, ds, ac["aircraft_id"], fac, jasc["code"], jasc["name"],
                                  1, random.choice([680,1500,2200,3800,4500]))
                    else:
                        add_labor(mid, ds, ac["aircraft_id"], fac, jasc["name"],
                                  repair_hrs, action="REPAIR", jasc=jasc["code"])

            # Unscheduled ~0.15% per flight
            if random.random() < 0.0015:
                job_id += 1
                mid = f"MJ-{job_id:06d}"
                severity = random.choices(["MINOR","MODERATE","AOG"], weights=[0.55,0.35,0.10])[0]
                utype = random.choices(
                    ["LINE_MAINTENANCE","COMPONENT_REPLACEMENT","AOG_REPAIR","TROUBLESHOOTING"],
                    weights=[0.40,0.30,0.10,0.20])[0]
                mt_info = next(m for m in MAINT_TYPES if m["type"] == utype)
                dur = max(2, random.gauss(mt_info["avg_dur"], mt_info["avg_dur"]*0.3))
                if severity == "AOG":
                    dur = max(24, random.gauss(48, 16))
                start = datetime(d.year, d.month, d.day, random.randint(7,20), 0)
                jasc = random.choices(JASC_CODES, weights=jw)[0]
                jobs.append({
                    "maintenance_job_id":   mid,
                    "date":                 ds,
                    "aircraft_id":          ac["aircraft_id"],
                    "tail_number":          ac["tail_number"],
                    "facility_id":          fac,
                    "maintenance_type":     utype,
                    "is_scheduled":         0,
                    "severity":             severity,
                    "trigger_source":       random.choices(
                        ["PILOT_REPORT","SENSOR_ALERT","INSPECTION_FINDING","GROUND_CREW"],
                        weights=[0.35,0.20,0.25,0.20])[0],
                    "job_status":           "COMPLETED",
                    "start_datetime":       start.strftime("%Y-%m-%d %H:%M"),
                    "close_datetime":       (start + timedelta(hours=dur)).strftime("%Y-%m-%d %H:%M"),
                    "total_elapsed_hours":  round(dur, 1),
                    "finding_code":         jasc["name"],
                    "technician_id":        f"TECH-{random.randint(1,40):03d}",
                    "aircraft_hours_at_event": round(cum_hrs, 1),
                })
                lab_hrs = max(2, random.gauss(mt_info["avg_lab"], 3))
                add_labor(mid, ds, ac["aircraft_id"], fac, f"{jasc['name']} - {utype}",
                          lab_hrs, action="REPAIR", jasc=jasc["code"])
                if utype in ("COMPONENT_REPLACEMENT","AOG_REPAIR"):
                    base_cost = random.choice([680,1500,2200,3800,4500,9500,15000,22000])
                    if severity == "AOG":
                        base_cost = random.choice([9500,15000,22000,45000,85000])
                    qty = random.randint(1,3)
                    add_parts(mid, ds, ac["aircraft_id"], fac, jasc["code"], jasc["name"],
                              qty, base_cost)

    # -------------------------------------------------------------------------
    # POST-GENERATION: apply cost ratio targets in-memory before writing
    # -------------------------------------------------------------------------
    # Group LABOR and PARTS totals by month
    def month_key(row): return row["date"][:7]

    def apply_ratio(details, target_months, ratio, labor_mult=1.0):
        """Scale PARTS rows so parts_total = labor_total × ratio.
           Optionally also scale LABOR rows by labor_mult first (AOG months)."""
        month_labor = defaultdict(float)
        month_parts = defaultdict(float)
        for row in details:
            mk = month_key(row)
            if mk in target_months:
                if row["cost_category"] == "LABOR":
                    month_labor[mk] += row["extended_cost"]
                elif row["cost_category"] == "PARTS":
                    month_parts[mk] += row["extended_cost"]

        # Step 1: scale labor if needed
        if labor_mult != 1.0:
            for row in details:
                mk = month_key(row)
                if mk in target_months and row["cost_category"] == "LABOR":
                    row["extended_cost"] = round(row["extended_cost"] * labor_mult, 2)
                    row["unit_cost"]     = round(row["unit_cost"] * labor_mult, 2)
            # Recalculate labor totals after scaling
            month_labor = defaultdict(float)
            for row in details:
                mk = month_key(row)
                if mk in target_months and row["cost_category"] == "LABOR":
                    month_labor[mk] += row["extended_cost"]

        # Step 2: scale parts
        for mk in target_months:
            lt = month_labor.get(mk, 0)
            pt = month_parts.get(mk, 0)
            if lt > 0 and pt > 0:
                mult = (lt * ratio) / pt
                for row in details:
                    if month_key(row) == mk and row["cost_category"] == "PARTS":
                        row["extended_cost"] = round(row["extended_cost"] * mult, 2)
                        row["unit_cost"]     = round(row["unit_cost"] * mult, 2)
        return details

    # BOOST months (Mar/Oct all years → 1.40x)
    details = apply_ratio(details, BOOST_MONTHS, COST_BOOST_RATIO)
    # REVERT months (Jan/Jul/Dec 2023 → 0.70x)
    details = apply_ratio(details, REVERT_MONTHS, COST_REVERT_RATIO)
    # AOG-heavy months: labor × 1.25 first, then parts = labor × 1.40
    details = apply_ratio(details, set(AOG_BOOST_MONTHS.keys()), COST_BOOST_RATIO, labor_mult=LABOR_MULT)

    # Ensure AOG_REPAIR jobs have a PARTS row
    jobs_with_parts = {r["maintenance_job_id"] for r in details if r["cost_category"] == "PARTS"}
    jobs_aog_labor  = {r["maintenance_job_id"]: r for r in details
                       if "AOG_REPAIR" in r["part_description"] and r["cost_category"] == "LABOR"}
    for mid, labor_row in jobs_aog_labor.items():
        if mid not in jobs_with_parts:
            jasc_key = str(labor_row["jasc_ata_code"]).split(".")[0]
            desc, unit, qty = AOG_PART_COSTS.get(jasc_key, DEFAULT_AOG_PART)
            premium = round(unit * random.uniform(1.8, 2.4), 2)
            det_id += 1
            details.append({
                "detail_id":         f"MD-{det_id:07d}",
                "maintenance_job_id": mid,
                "date":              labor_row["date"],
                "aircraft_id":       labor_row["aircraft_id"],
                "facility_id":       labor_row["facility_id"],
                "action_type":       "REPLACE",
                "cost_category":     "PARTS",
                "jasc_ata_code":     labor_row["jasc_ata_code"],
                "part_description":  desc,
                "uom":               "Each",
                "quantity":          qty,
                "unit_cost":         premium,
                "extended_cost":     round(premium * qty, 2),
            })

    write_csv("fact_maintenance_job.csv",    jobs,    list(jobs[0].keys()))
    write_csv("fact_maintenance_detail.csv", details, list(details[0].keys()))
    return jobs, details


def gen_daily_status(aircraft, flights):
    """
    Four-phase generation — one CSV write at the end.

    Phase A: assign base rows with MONTH_TARGETS seasonal %s
    Phase B: enforce AOG exactly to Mar=6, May=8, Oct=6 per year
    Phase C: backfill flight_hours/cycles from fact_flight; zero non-FLYING
    Phase D: FLYING<->AVAILABLE rebalance per PERIOD_TARGETS + holiday spike
    """
    print("  Generating aircraft daily status (4 phases)...")

    # ── Phase A: base seasonal generation ────────────────────────────────────
    # Build flight lookup for Phase C + D
    flight_day_hrs    = defaultdict(float)   # (ac_id, date_str) → total hours
    flight_day_cycles = defaultdict(int)     # (ac_id, date_str) → flight count
    flight_lookup     = set()               # (date, ac_id) pairs with actual flight
    for f in flights:
        key = (f["date"], f["aircraft_id"])
        flight_day_hrs[(f["aircraft_id"], f["date"])]    += f["flight_hours"]
        flight_day_cycles[(f["aircraft_id"], f["date"])] += 1
        flight_lookup.add(key)

    # Per-aircraft daily averages for backfill
    ac_daily_avg = defaultdict(list)
    for (ac_id, _), h in flight_day_hrs.items():
        ac_daily_avg[ac_id].append(h)
    ac_mean = {ac: sum(v)/len(v) for ac, v in ac_daily_avg.items()}
    fleet_mean = sum(h for v in ac_daily_avg.values() for h in v) / max(1, sum(len(v) for v in ac_daily_avg.values()))

    rows = []
    for ac in aircraft:
        delivery = date.fromisoformat(ac["delivery_date"])
        d = max(SIM_START, delivery)
        while d <= SIM_END:
            ds = d.isoformat()
            fly_t, maint_t = MONTH_TARGETS[d.month]
            maint_types = MAINT_TYPE_BY_MONTH.get(d.month, DEFAULT_MAINT_TYPES)
            r = random.random()
            if r < fly_t:
                status = "FLYING"
            elif r < fly_t + maint_t:
                status = "IN_MAINTENANCE"
            else:
                status = "AVAILABLE"
            rows.append({
                "aircraft_id":    ac["aircraft_id"],
                "date":           ds,
                "status":         status,
                "flight_hours":   0.0,
                "flight_cycles":  0,
                "maintenance_type": random.choice(maint_types) if status == "IN_MAINTENANCE" else "",
            })
            d += timedelta(days=1)

    # ── Phase B: enforce AOG to Mar/May/Oct only ──────────────────────────────
    # Index rows by (year, month) for manipulation
    by_ym = defaultdict(list)
    for i, row in enumerate(rows):
        d = date.fromisoformat(row["date"])
        by_ym[(d.year, d.month)].append(i)

    for yr in [2023, 2024, 2025]:
        for mo, target in AOG_TARGETS.items():
            bucket = by_ym[(yr, mo)]
            aog_idxs  = [i for i in bucket if rows[i]["status"] == "AOG"]
            avail_idxs = [i for i in bucket if rows[i]["status"] == "AVAILABLE"]
            cur = len(aog_idxs)
            if cur < target:
                # Convert AVAILABLE → AOG
                to_flip = min(target - cur, len(avail_idxs))
                for i in random.sample(avail_idxs, to_flip):
                    rows[i]["status"]           = "AOG"
                    rows[i]["maintenance_type"] = "AOG_REPAIR"
            elif cur > target:
                # Trim excess AOG → AVAILABLE
                for i in random.sample(aog_idxs, cur - target):
                    rows[i]["status"]           = "AVAILABLE"
                    rows[i]["maintenance_type"] = ""

    # Remove AOG from non-target months
    for i, row in enumerate(rows):
        d = date.fromisoformat(row["date"])
        if row["status"] == "AOG" and d.month not in AOG_TARGETS:
            rows[i]["status"]           = "AVAILABLE"
            rows[i]["maintenance_type"] = ""

    # ── Phase C: hours/cycles integrity ──────────────────────────────────────
    for row in rows:
        ac_id = row["aircraft_id"]
        ds    = row["date"]
        if row["status"] == "FLYING":
            actual = flight_day_hrs.get((ac_id, ds))
            if actual and actual > 0:
                fh = round(actual, 2)
            else:
                mean = ac_mean.get(ac_id, fleet_mean)
                fh = round(max(0.3, random.gauss(mean, mean * 0.15)), 2)
            row["flight_hours"]  = fh
            row["flight_cycles"] = max(1, round(fh / 1.5))
        else:
            row["flight_hours"]  = 0.0
            row["flight_cycles"] = 0

    # ── Phase D: FLYING<->AVAILABLE rebalance per period ─────────────────────
    def period_for(d_obj):
        m, dy = d_obj.month, d_obj.day
        if (m == 12 and dy >= 20) or (m == 1 and dy <= 5): return "holiday"
        if m == 12: return "dec_non_hol"
        if m == 1:  return "jan_non_hol"
        if m == 2:  return "winter_rest"
        if m == 3:  return "march"
        if m == 4:  return "april"
        if m == 5:  return "may"
        if m in (6,7,8): return "summer"
        if m in (9,11):  return "fall"
        if m == 10: return "october"
        return None

    # Step D1: unmatched FLYING → AVAILABLE
    for row in rows:
        if row["status"] == "FLYING":
            if (row["date"], row["aircraft_id"]) not in flight_lookup:
                row["status"]        = "AVAILABLE"
                row["flight_hours"]  = 0.0
                row["flight_cycles"] = 0

    # Build period index
    by_period = defaultdict(list)
    for i, row in enumerate(rows):
        p = period_for(date.fromisoformat(row["date"]))
        if p:
            by_period[p].append(i)

    flying_median = sorted(r["flight_hours"] for r in rows if r["status"] == "FLYING")
    flying_median = flying_median[len(flying_median)//2] if flying_median else 2.7

    # Process holiday first (needs to push FLYING up), then the rest
    ordered_periods = ["holiday","dec_non_hol","jan_non_hol","winter_rest",
                       "march","april","may","summer","fall","october"]

    for period in ordered_periods:
        target = PERIOD_TARGETS[period]
        idxs   = by_period[period]
        total  = len(idxs)
        if total == 0:
            continue
        cur_flying = sum(1 for i in idxs if rows[i]["status"] == "FLYING")
        t_flying   = int(round(target * total))
        delta      = t_flying - cur_flying

        if delta < 0:
            # Demote FLYING: prefer no-flight-record rows, then lowest flight_hours
            flying_idxs = [i for i in idxs if rows[i]["status"] == "FLYING"]
            flying_idxs.sort(key=lambda i: (
                1 if (rows[i]["date"], rows[i]["aircraft_id"]) in flight_lookup else 0,
                rows[i]["flight_hours"]
            ))
            for i in flying_idxs[:abs(delta)]:
                rows[i]["status"]        = "AVAILABLE"
                rows[i]["flight_hours"]  = 0.0
                rows[i]["flight_cycles"] = 0
        elif delta > 0:
            # Promote AVAILABLE: only rows with flight records
            avail_idxs = [i for i in idxs
                          if rows[i]["status"] == "AVAILABLE"
                          and (rows[i]["date"], rows[i]["aircraft_id"]) in flight_lookup]
            for i in avail_idxs[:delta]:
                rows[i]["status"]        = "FLYING"
                rows[i]["flight_hours"]  = flying_median
                rows[i]["flight_cycles"] = 2

    write_csv("fact_aircraft_daily_status.csv", rows, list(rows[0].keys()))
    return rows


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 60)
    print("  PlaneSense Analytics Data — V2 Consolidated Generator")
    print("=" * 60)
    print(f"  Simulation: {SIM_START} → {SIM_END}  (3 years)")
    print(f"  Fleet:      {PC12_COUNT} PC-12 + {PC24_COUNT} PC-24 = {TOTAL_AIRCRAFT} aircraft")
    print(f"  Output:     {OUT_DIR}/")
    print()

    print("[1/9] dim_date");           gen_dim_date()
    print("[2/9] dim_aircraft");       aircraft = gen_dim_aircraft()
    print("[3/9] dim_airport");        gen_dim_airport()
    print("[4/9] dim_component");      gen_dim_component()
    print("[5/9] dim_crew");           gen_dim_crew()
    print("[6/9] dim_facility");       gen_dim_facility()
    print("[7/9] dim_owner");          owners = gen_dim_owner()
    print("[8/9] fact_flight");        flights = gen_fact_flight(aircraft, owners)
    print("[8b]  fact_booking");       gen_fact_booking(flights, owners)
    print("[8c]  fact_maintenance");   maint_jobs, maint_details = gen_maintenance(aircraft, flights)
    print("[9/9] fact_daily_status");  daily = gen_daily_status(aircraft, flights)

    # ── Validation summary ──────────────────────────────────────────────────
    total_fh    = sum(f["flight_hours"]   for f in flights)
    total_pax   = sum(f["passenger_count"] for f in flights)
    total_cost  = sum(d["extended_cost"]   for d in maint_details)
    n_sched     = sum(1 for j in maint_jobs if j["is_scheduled"] == 1)
    n_unsched   = sum(1 for j in maint_jobs if j["is_scheduled"] == 0)
    n_aog       = sum(1 for j in maint_jobs if j["severity"] == "AOG")

    print()
    print("=" * 60)
    print("  GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Flights          : {len(flights):,}")
    print(f"  Total flight hrs : {total_fh:,.0f}")
    print(f"  Annualized/yr    : ~{len(flights)/3:,.0f}  (target ~47,800)")
    print(f"  Avg hrs/ac/yr    : {total_fh/TOTAL_AIRCRAFT/3:,.0f}  (PC-12 target ~1,150, PC-24 ~1,350)")
    print(f"  Total passengers : {total_pax:,}")
    print(f"  Deadhead ratio   : {sum(1 for f in flights if f['is_deadhead'])/len(flights)*100:.1f}%")
    print(f"  Maint jobs       : {len(maint_jobs):,}  (sched:{n_sched}, unsched:{n_unsched}, AOG:{n_aog})")
    print(f"  Maint cost/flt-h : ${total_cost/total_fh:,.0f}  (target ~$39)")
    print(f"  Daily status rows: {len(daily):,}")

    # Seasonal FLYING/AVAILABLE breakdown
    from collections import Counter
    season_status = defaultdict(Counter)
    for row in daily:
        m = date.fromisoformat(row["date"]).month
        s = get_season(m)
        season_status[s][row["status"]] += 1

    print()
    print("  Daily Status by Season:")
    for s in ["Winter","Spring","Summer","Fall"]:
        c = season_status[s]
        tot = sum(c.values())
        print(f"    {s}: FLYING={c['FLYING']/tot:.1%}  AVAILABLE={c['AVAILABLE']/tot:.1%}  "
              f"MAINT={c['IN_MAINTENANCE']/tot:.1%}  AOG={c['AOG']/tot:.1%}")

    hw = [r for r in daily if
          (date.fromisoformat(r["date"]).month == 12 and date.fromisoformat(r["date"]).day >= 20) or
          (date.fromisoformat(r["date"]).month == 1  and date.fromisoformat(r["date"]).day <= 5)]
    if hw:
        hwc = Counter(r["status"] for r in hw)
        hwt = sum(hwc.values())
        print(f"    Holiday(Dec20-Jan5): FLYING={hwc['FLYING']/hwt:.1%}  AVAILABLE={hwc['AVAILABLE']/hwt:.1%}")

    # AOG validation
    aog_by_ym = defaultdict(int)
    for row in daily:
        if row["status"] == "AOG":
            aog_by_ym[row["date"][:7]] += 1
    print()
    print("  AOG days (target Mar=6, May=8, Oct=6 per year):")
    for yr in [2023,2024,2025]:
        for mo,tgt in AOG_TARGETS.items():
            mk  = f"{yr}-{mo:02d}"
            got = aog_by_ym.get(mk, 0)
            ok  = "✓" if got == tgt else "✗"
            print(f"    {mk}: {got}  (expected {tgt}) {ok}")

    print()
    print(f"  All files saved to: {OUT_DIR}/")


if __name__ == "__main__":
    main()

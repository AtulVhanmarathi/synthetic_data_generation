"""
PlaneSense IOC — Synthetic Operational Data Generator
=====================================================
Generates the live-day data fed into the IOC Dispatch Agent:

  1. crew_roster.csv        — 52 pilots (ratings, bases, availability)
  2. flight_requests.csv    — 10 inbound requests for Dec 20 2025
  3. weather_events.csv     — 4 active weather advisories
  4. owner_profiles.csv     — Minimal owner reference (name, tier, preferences)

Reuses aircraft_registry.csv and ml_features.csv from the
predictive maintenance dataset.
"""

import os
import random
import json
from datetime import date, time, datetime

import numpy as np
import pandas as pd

random.seed(99)
np.random.seed(99)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR  = os.path.join(BASE_DIR, "output", "ioc", "data")
os.makedirs(OUT_DIR, exist_ok=True)

AIRCRAFT_CSV    = os.path.join(BASE_DIR, "output", "predictive_maintenance", "data", "aircraft_registry.csv")
MAINTENANCE_CSV = os.path.join(BASE_DIR, "output", "predictive_maintenance", "data", "ml_features.csv")

DEMO_DATE = "2025-12-20"   # Peak holiday period — high demand day

# ── Pilot roster ──────────────────────────────────────────────────────────────

PILOT_FIRST = ["James","Maria","Robert","Linda","David","Patricia","Michael",
               "Susan","William","Jessica","Richard","Sandra","Charles","Ashley",
               "Joseph","Dorothy","Thomas","Lisa","Kevin","Nancy","Brian","Betty",
               "Mark","Ruth","Paul","Sharon","Steven","Helen","Andrew","Donna",
               "Kenneth","Carol","Joshua","Amanda","Eric","Melissa","Ryan","Deborah",
               "Jacob","Stephanie","Gary","Rebecca","Tyler","Laura","Frank","Rachel",
               "Henry","Anna","Aaron","Diane"]
PILOT_LAST  = ["Martinez","Chen","Williams","Johnson","Davis","Garcia","Wilson",
               "Anderson","Taylor","Thomas","Moore","Jackson","Martin","Lee",
               "Thompson","White","Harris","Clark","Lewis","Robinson","Walker",
               "Hall","Allen","Young","Scott","Adams","Baker","Nelson","Carter",
               "Mitchell","Roberts","Turner","Phillips","Campbell","Parker",
               "Evans","Edwards","Collins","Stewart","Flores","Morris","Rogers",
               "Reed","Cook","Morgan","Bell","Murphy","Bailey","Rivera","Cooper"]

BASES = ["PSM", "BVU"]   # Portsmouth NH | Boulder City NV

def build_crew_roster() -> pd.DataFrame:
    rows = []
    used = set()
    emp_id = 10001

    # 34 at PSM, 18 at BVU — approx fleet ratio
    base_assignments = ["PSM"] * 34 + ["BVU"] * 18
    random.shuffle(base_assignments)

    for i, base in enumerate(base_assignments):
        # Build a unique name by incrementing first/last indices until we find a free slot
        first_i, last_i = i % len(PILOT_FIRST), i % len(PILOT_LAST)
        for attempt in range(len(PILOT_FIRST) * len(PILOT_LAST)):
            name = f"{PILOT_FIRST[(first_i + attempt) % len(PILOT_FIRST)]} {PILOT_LAST[(last_i + attempt) % len(PILOT_LAST)]}"
            if name not in used:
                used.add(name)
                break

        # Senior captains can fly both types; junior → PC-12 only
        seniority = random.choice(["Captain", "Captain", "Captain", "First Officer"])
        can_pc24  = (seniority == "Captain") and (random.random() < 0.45)
        ratings   = "PC-12,PC-24" if can_pc24 else "PC-12"

        # Duty status on demo day
        duty_options = ["AVAILABLE", "AVAILABLE", "AVAILABLE", "ON_REST",
                        "ON_TRIP", "VACATION"]
        duty_status = random.choice(duty_options)
        avail_time  = None
        if duty_status == "AVAILABLE":
            # Some available from early morning, some later
            h = random.choice([5, 5, 6, 6, 6, 7, 8, 9, 10, 11])
            avail_time = f"{h:02d}:00"
        elif duty_status == "ON_REST":
            h = random.choice([12, 14, 16, 18])
            avail_time = f"{h:02d}:00"

        rows.append(dict(
            employee_id    = f"EMP-{emp_id}",
            pilot_name     = name,
            role           = seniority,
            base           = base,
            type_ratings   = ratings,
            duty_status    = duty_status,
            available_from = avail_time,
            rest_hours_remaining = (random.randint(0, 8) if duty_status == "ON_REST" else 0),
            trips_ytd      = random.randint(80, 420),
            currency_pc12  = "CURRENT",
            currency_pc24  = ("CURRENT" if can_pc24 else "N/A"),
        ))
        emp_id += 1

    return pd.DataFrame(rows)


# ── Flight requests ───────────────────────────────────────────────────────────

REQUESTS = [
    # id, owner_id, owner_name, dep, arr, req_time, pax, aircraft_pref, notes
    ("RQ-001", "PL-0042", "Catherine Morris",   "KPSM", "KMIA", "09:00", 3, "PC-12",  ""),
    ("RQ-002", "PL-0117", "Thomas Nelson",       "KBVU", "KSFO", "10:30", 2, "PC-12",  ""),
    ("RQ-003", "PL-0089", "Sophia Ramirez",      "KPSM", "KATL", "08:00", 4, "PC-24",  "Owner prefers window seat, quiet cabin"),
    ("RQ-004", "PL-0205", "Marcus Johnson",      "KBVU", "KLAS", "11:00", 1, "PC-12",  ""),
    ("RQ-005", "PL-0033", "Eleanor Brooks",      "KPSM", "KBOS", "13:00", 2, "PC-12",  ""),
    ("RQ-006", "PL-0178", "Phillip Chen",        "KBVU", "KPHX", "09:30", 3, "PC-12",  "Medical equipment in cargo"),
    ("RQ-007", "PL-0061", "Margaret Walsh",      "KPSM", "KTEB", "07:30", 5, "PC-24",  "Holiday travel, 5 pax + luggage"),
    ("RQ-008", "PL-0290", "Samuel Edwards",      "KBVU", "KDEN", "14:00", 2, "PC-12",  ""),
    ("RQ-009", "PL-0014", "Richard Thornton",    "KPSM", "EGLL", "16:00", 2, "PC-24",  "Jetfly segment: KPSM → EGLL → LSZH"),
    ("RQ-010", "PL-0155", "Grace Patterson",     "KBVU", "KSEA", "12:00", 3, "PC-24",  "West Coast owner, new to fleet"),
]

def build_flight_requests() -> pd.DataFrame:
    rows = []
    for (rid, oid, owner, dep, arr, req_time, pax, ac_pref, notes) in REQUESTS:
        rows.append(dict(
            request_id        = rid,
            owner_id          = oid,
            owner_name        = owner,
            departure_icao    = dep,
            arrival_icao      = arr,
            requested_dep_time= f"{DEMO_DATE} {req_time}",
            pax_count         = pax,
            aircraft_preference = ac_pref,
            special_notes     = notes,
            status            = "PENDING",
            created_at        = f"{DEMO_DATE} 06:00",
            priority          = ("HIGH" if pax >= 4 or "EGLL" in arr else "NORMAL"),
        ))
    return pd.DataFrame(rows)


# ── Weather events ─────────────────────────────────────────────────────────────

WEATHER = [
    dict(
        event_id    = "WX-001",
        type        = "SIGMET",
        severity    = "MODERATE",
        affected_area = "Northeast corridor KBOS-KEWR-KPHL",
        valid_from  = f"{DEMO_DATE} 07:00",
        valid_to    = f"{DEMO_DATE} 15:00",
        description = "Moderate icing FL080-FL180 along northeast corridor; "
                      "IMC conditions at KBOS, KEWR. Expect delays 30-60 min.",
        affects_airports = "KBOS,KEWR,KPHL,KBWI,KLGA",
        recommended_action = "File alternate, carry extra fuel, consider 2h delay",
    ),
    dict(
        event_id    = "WX-002",
        type        = "PIREP",
        severity    = "LIGHT",
        affected_area = "KBVU departure corridor FL120-FL200",
        valid_from  = f"{DEMO_DATE} 08:00",
        valid_to    = f"{DEMO_DATE} 12:00",
        description = "Light turbulence FL120-FL200 west of BVU departures. "
                      "Smooth above FL200.",
        affects_airports = "KBVU,KLAS",
        recommended_action = "Plan cruise above FL200 or accept light chop",
    ),
    dict(
        event_id    = "WX-003",
        type        = "METAR",
        severity    = "LOW_VIS",
        affected_area = "KPSM ground operations",
        valid_from  = f"{DEMO_DATE} 06:00",
        valid_to    = f"{DEMO_DATE} 10:00",
        description = "KPSM: BKN003 OVC006 BR, visibility 1/2SM. "
                      "IFR conditions. Expect Cat I ILS approaches.",
        affects_airports = "KPSM",
        recommended_action = "Delay departures by 90 min or file IFR with Cat I alternate",
    ),
    dict(
        event_id    = "WX-004",
        type        = "NOTAM",
        severity    = "INFO",
        affected_area = "KATL ground delay program",
        valid_from  = f"{DEMO_DATE} 10:00",
        valid_to    = f"{DEMO_DATE} 18:00",
        description = "KATL GDP in effect due to holiday volume. "
                      "Avg ground delay 45 min for arrivals.",
        affects_airports = "KATL",
        recommended_action = "Request EDCT, advise owner of potential delay",
    ),
]

def build_weather_events() -> pd.DataFrame:
    return pd.DataFrame(WEATHER)


# ── Owner profiles (minimal, for agent context) ────────────────────────────────

def build_owner_profiles(requests_df: pd.DataFrame) -> pd.DataFrame:
    TIERS = {"PL-0042": "1/8",  "PL-0117": "1/16", "PL-0089": "1/4",
             "PL-0205": "1/32", "PL-0033": "1/16", "PL-0178": "1/8",
             "PL-0061": "1/4",  "PL-0290": "1/16", "PL-0014": "1/8",
             "PL-0155": "1/16"}
    TENURE = {"PL-0042": 7.2,  "PL-0117": 3.1,  "PL-0089": 12.4,
              "PL-0205": 1.2,  "PL-0033": 5.8,  "PL-0178": 2.9,
              "PL-0061": 9.1,  "PL-0290": 0.8,  "PL-0014": 15.6,
              "PL-0155": 1.5}
    UTIL   = {"PL-0042": 0.74, "PL-0117": 0.88, "PL-0089": 0.96,
              "PL-0205": 0.41, "PL-0033": 0.72, "PL-0178": 0.68,
              "PL-0061": 0.83, "PL-0290": 0.55, "PL-0014": 0.91,
              "PL-0155": 0.63}

    rows = []
    for _, req in requests_df.iterrows():
        oid = req["owner_id"]
        rows.append(dict(
            owner_id          = oid,
            owner_name        = req["owner_name"],
            share_type        = TIERS.get(oid, "1/16"),
            tenure_years      = TENURE.get(oid, 3.0),
            utilization_rate  = UTIL.get(oid, 0.70),
            churn_risk        = ("HIGH" if UTIL.get(oid, 0.70) < 0.50 else
                                 "MEDIUM" if UTIL.get(oid, 0.70) < 0.75 else "LOW"),
            jetfly_access     = int(oid in ["PL-0014"]),
            cobalt_pass       = int(oid in ["PL-0290"]),
            vip_flag          = int(TENURE.get(oid, 0) > 10),
            preferred_aircraft= req["aircraft_preference"],
        ))
    return pd.DataFrame(rows)


# ── Main ──────────────────────────────────────────────────────────────────────

def save(df, name):
    path = os.path.join(OUT_DIR, name)
    df.to_csv(path, index=False)
    print(f"  ✓  {name:<35} {len(df):>6} rows   "
          f"{os.path.getsize(path)/1024:>6.1f} KB")


def main():
    bar = "=" * 65
    print(f"\n{bar}")
    print("  PlaneSense IOC — Operational Data Generator")
    print(f"  Demo date: {DEMO_DATE} | Peak holiday period")
    print(bar)

    crew = build_crew_roster()
    save(crew, "crew_roster.csv")

    requests = build_flight_requests()
    save(requests, "flight_requests.csv")

    weather = build_weather_events()
    save(weather, "weather_events.csv")

    owners = build_owner_profiles(requests)
    save(owners, "owner_profiles.csv")

    print(f"\n  Crew available (AVAILABLE status): "
          f"{(crew['duty_status']=='AVAILABLE').sum()}")
    print(f"  Crew on rest (returning today):    "
          f"{(crew['duty_status']=='ON_REST').sum()}")
    print(f"  Flight requests:                   {len(requests)}")
    print(f"  Active weather advisories:         {len(weather)}")
    print(f"\n  Output: {os.path.relpath(OUT_DIR)}")
    print(bar)


if __name__ == "__main__":
    main()

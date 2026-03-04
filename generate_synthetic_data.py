"""
PlaneSense Predictive Maintenance — Synthetic Dataset Generator
================================================================
Generates 8 domain-authentic CSV tables modelled on PlaneSense's
actual fleet composition, operational patterns, and maintenance
practices extracted from planesense.com.

Fleet basis (from planesense.com):
  - 46 Pilatus PC-12 turboprops (PT6A-67P engine)
  - 16 Pilatus PC-24 light jets (Williams FJ44-4A engines)
  - Two facilities: Portsmouth NH (PSM) and Boulder City NV (BVU)
  - Average fleet age: 4.5 years
  - ~47,800 flights completed in 2025

Output tables
-------------
  1. aircraft_registry.csv          — Master aircraft reference
  2. components_master.csv          — Component type definitions & life limits
  3. component_installations.csv    — Which component is on which aircraft
  4. flight_logs.csv                — 2-year flight history (~95k rows)
  5. sensor_readings.csv            — Per-flight sensor snapshots (~95k rows)
  6. maintenance_records.csv        — Work order history
  7. failure_events.csv             — Unscheduled / in-flight events
  8. parts_inventory.csv            — Atlas Aircraft Center stock levels
  9. ml_features.csv                — Model-ready feature matrix (target table)
"""

import os
import random
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

# ── Reproducibility ─────────────────────────────────────────────────────────
np.random.seed(42)
random.seed(42)

# ── Paths ────────────────────────────────────────────────────────────────────
OUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "output", "predictive_maintenance", "data"
)
os.makedirs(OUT_DIR, exist_ok=True)

# ── Simulation window ────────────────────────────────────────────────────────
SIM_END   = datetime(2025, 12, 31)
SIM_START = datetime(2020, 1, 1)
DAYS      = (SIM_END - SIM_START).days          # 2191 days

# ── Airport universe (PlaneSense service area, scraped from site) ─────────────
PC12_AIRPORTS = [
    "PSM","BOS","ACK","MVY","HYA","ORH","BED","BGR","PVD",
    "TEB","CDW","MMU","SWF","HPN","FRG","ISP","1B9","FOK",
    "DCA","IAD","RIC","ORF","OAJ","EWN","MHH","NHK","GYH",
    "SFB","MCO","PBI","FXE","TMB","APF","VNC","PIE","GNV",
    "BVU","VGT","HND","LAS","PHX","SDM","CMA","WHP","FUL",
    "ASE","TEX","JAC","SUN","MTJ","GCC","CNY","U76",
]
PC24_AIRPORTS = [
    "PSM","BOS","TEB","CDW","DCA","IAD","ORD","MDW","DTW",
    "CLE","PIT","BUF","ROC","ALB","SYR","PVD","ACK","MVY",
    "BVU","VGT","LAS","PHX","SAN","LAX","SFO","SMF","RNO",
    "PDX","SEA","BZN","GTF","ASE","TEX","JAC","EGE","HDN",
    "SRQ","RSW","PBI","FLL","OPF","APF","SFB","GNV","VRB",
]

# ── Seasonal multipliers (index = month 1-12) ─────────────────────────────────
# Summer (Jun-Sep) + holiday ski season (Dec-Jan) are peaks
SEASONAL_LOAD = {
    1:1.15, 2:0.85, 3:0.90, 4:0.95, 5:1.00,
    6:1.20, 7:1.25, 8:1.20, 9:1.10, 10:0.95,
    11:0.90, 12:1.10,
}


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE 1 — AIRCRAFT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

def build_aircraft_registry() -> pd.DataFrame:
    """
    62 aircraft matching the fleet snapshot from the Jan 2025 Jetfly
    press release (46 PC-12 + 16 PC-24).  Tail numbers follow the
    real PlaneSense N1xxAF / N8xxAF convention.
    Average fleet age ~4.5 years → most deliveries 2019-2024.
    """
    records = []

    # PC-12 fleet — 46 aircraft
    pc12_serials = list(range(1700, 1746))   # plausible PC-12 NGX SNs
    for i, sn in enumerate(pc12_serials):
        tail = f"N{100 + i}AF"
        # Delivery dates: oldest ~2017, newest ~2024; centre ~2021
        delivery = SIM_START + timedelta(
            days=int(np.random.normal(365 * 1.5, 365 * 1.2))
        )
        delivery = max(datetime(2017, 1, 1), min(delivery, datetime(2024, 6, 1)))
        age_days = (SIM_END - delivery).days
        # ~771 flights/yr at ~1.1 hrs avg → ~848 hrs/yr
        total_hours   = round(age_days / 365 * np.random.uniform(700, 950), 1)
        total_cycles  = int(total_hours / np.random.uniform(0.9, 1.3))
        base = "PSM" if i < 32 else "BVU"
        status = np.random.choice(["ACTIVE", "IN_MAINTENANCE"],
                                   p=[0.88, 0.12])
        records.append(dict(
            tail_number=tail, model="PC-12 NGX",
            serial_number=f"PC12-{sn}",
            engine_type="PT6A-67P",
            delivery_date=delivery.date(),
            base_facility=base,
            total_flight_hours=total_hours,
            total_cycles=total_cycles,
            status=status,
            last_heavy_maintenance=(delivery + timedelta(
                days=int(total_hours / 2 / 850 * 365)
            )).date(),
        ))

    # PC-24 fleet — 16 aircraft
    pc24_serials = list(range(120, 136))    # real PlaneSense PC-24 SNs start ~120
    for i, sn in enumerate(pc24_serials):
        tail = f"N{800 + i}AF"
        delivery = datetime(2018, 2, 7) + timedelta(
            days=int(np.random.uniform(0, 365 * 5.5))
        )
        delivery = min(delivery, datetime(2024, 11, 1))
        age_days = (SIM_END - delivery).days
        # PC-24 slightly longer legs ~1.5 hrs avg → ~900 hrs/yr
        total_hours   = round(age_days / 365 * np.random.uniform(750, 1000), 1)
        total_cycles  = int(total_hours / np.random.uniform(1.3, 1.8))
        base = "PSM" if i < 11 else "BVU"
        status = np.random.choice(["ACTIVE", "IN_MAINTENANCE"], p=[0.88, 0.12])
        records.append(dict(
            tail_number=tail, model="PC-24",
            serial_number=f"PC24-{sn}",
            engine_type="FJ44-4A",
            delivery_date=delivery.date(),
            base_facility=base,
            total_flight_hours=total_hours,
            total_cycles=total_cycles,
            status=status,
            last_heavy_maintenance=(delivery + timedelta(
                days=int(total_hours / 2 / 900 * 365)
            )).date(),
        ))

    return pd.DataFrame(records)


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE 2 — COMPONENTS MASTER
# ═══════════════════════════════════════════════════════════════════════════════

COMPONENTS_SPEC = [
    # id, name, category, aircraft, life_hrs, life_cycles, inspection_interval_hrs, failure_modes
    ("ENG_PT6",  "PT6A-67P Engine",          "PROPULSION",   "PC-12", 3500, None, 150,
     "compressor_stall|hot_section_erosion|bearing_wear|fuel_nozzle_clog"),
    ("PROP_ASS", "Propeller Assembly",        "PROPULSION",   "PC-12", 2400, None, 200,
     "blade_erosion|governor_malfunction|pitch_control_fault"),
    ("LDG_LH",   "Left Main Landing Gear",   "LANDING_GEAR", "BOTH",  None, 5000, 500,
     "seal_leak|actuator_wear|drag_brace_crack"),
    ("LDG_RH",   "Right Main Landing Gear",  "LANDING_GEAR", "BOTH",  None, 5000, 500,
     "seal_leak|actuator_wear|drag_brace_crack"),
    ("LDG_NOS",  "Nose Gear Assembly",       "LANDING_GEAR", "BOTH",  None, 6000, 500,
     "shimmy_damper|steering_actuator|seal_leak"),
    ("HYD_PMP",  "Hydraulic Pump",           "HYDRAULICS",   "BOTH",  2000, None, 200,
     "seal_failure|pressure_loss|contamination"),
    ("FUEL_LP",  "LP Fuel Pump",             "FUEL_SYSTEM",  "BOTH",  3000, None, 300,
     "wear|cavitation|seal_failure"),
    ("FUEL_HP",  "HP Fuel Pump",             "FUEL_SYSTEM",  "BOTH",  3000, None, 300,
     "wear|contamination|seal_failure"),
    ("ALTERNTR", "Alternator / Generator",   "ELECTRICAL",   "BOTH",  2500, None, 250,
     "bearing_wear|brush_wear|diode_failure"),
    ("BATTERY",  "Main Battery",             "ELECTRICAL",   "BOTH",  None, None, 365,   # calendar
     "capacity_degradation|cell_imbalance|terminal_corrosion"),
    ("BRK_LH",   "Left Brake Assembly",      "BRAKES",       "BOTH",  None, 800,  200,
     "wear|overheating|hydraulic_leak"),
    ("BRK_RH",   "Right Brake Assembly",     "BRAKES",       "BOTH",  None, 800,  200,
     "wear|overheating|hydraulic_leak"),
    # PC-24 specific
    ("ENG_FJ_L", "FJ44-4A Engine (Left)",    "PROPULSION",   "PC-24", 3600, None, 150,
     "fan_blade_damage|bearing_wear|hot_section_erosion|bleed_valve_fault"),
    ("ENG_FJ_R", "FJ44-4A Engine (Right)",   "PROPULSION",   "PC-24", 3600, None, 150,
     "fan_blade_damage|bearing_wear|hot_section_erosion|bleed_valve_fault"),
    ("APU",      "Auxiliary Power Unit",     "PROPULSION",   "PC-24", 2000, None, 200,
     "starter_wear|overtemp|bleed_fault"),
    ("THR_REV_L","Thrust Reverser (Left)",   "PROPULSION",   "PC-24", 3000, None, 300,
     "actuator_jam|locking_mechanism|hydraulic_leak"),
    ("THR_REV_R","Thrust Reverser (Right)",  "PROPULSION",   "PC-24", 3000, None, 300,
     "actuator_jam|locking_mechanism|hydraulic_leak"),
]

def build_components_master() -> pd.DataFrame:
    rows = []
    for spec in COMPONENTS_SPEC:
        cid, name, cat, ac, lh, lc, insp, modes = spec
        rows.append(dict(
            component_id=cid,
            component_name=name,
            category=cat,
            aircraft_compatibility=ac,
            life_limit_hours=lh,
            life_limit_cycles=lc,
            inspection_interval_hours=insp,
            typical_failure_modes=modes,
        ))
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE 3 — COMPONENT INSTALLATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def build_component_installations(aircraft_df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per component currently installed on each aircraft.
    Includes hours/cycles accumulated since installation.
    """
    rows = []
    install_id = 1

    for _, ac in aircraft_df.iterrows():
        model  = ac["model"]
        is_24  = model == "PC-24"
        total_h = ac["total_flight_hours"]
        total_c = ac["total_cycles"]

        for spec in COMPONENTS_SPEC:
            cid, name, cat, compat, lh, lc, insp, _ = spec
            if compat == "PC-12" and is_24:
                continue
            if compat == "PC-24" and not is_24:
                continue

            # Components may have been replaced 0-2 times over aircraft life
            replacements = int(total_h / (lh or 9999) * np.random.uniform(0.7, 1.3))
            replacements = min(replacements, 2)

            hours_at_install  = float(max(0, total_h - np.random.uniform(
                0, float(min(lh or total_h, total_h * 0.85))
            )))
            cycles_at_install = float(max(0, total_c - np.random.uniform(
                0, float(min(lc or total_c, total_c * 0.85))
            )))
            hours_since_install  = round(total_h - hours_at_install, 1)
            cycles_since_install = int(total_c - cycles_at_install)

            # Wear percentage — drives failure risk
            wear_pct_h = (hours_since_install / lh * 100) if lh else 0.0
            wear_pct_c = (cycles_since_install / lc * 100) if lc else 0.0
            wear_pct   = max(wear_pct_h, wear_pct_c)

            # Status
            if wear_pct > 90:
                status = "NEAR_LIMIT"
            elif wear_pct > 70:
                status = "MONITOR"
            else:
                status = "OK"

            rows.append(dict(
                installation_id=f"INS-{install_id:05d}",
                tail_number=ac["tail_number"],
                component_id=cid,
                component_name=name,
                install_date=(
                    datetime.combine(
                        ac["delivery_date"] if isinstance(ac["delivery_date"], date)
                        else ac["delivery_date"],
                        datetime.min.time()
                    )
                    + timedelta(days=int(
                        hours_at_install / (total_h / max(
                            (SIM_END - datetime.combine(
                                ac["delivery_date"] if isinstance(ac["delivery_date"], date)
                                else ac["delivery_date"],
                                datetime.min.time()
                            )).days, 1
                        )) * 365
                    ))
                ).date(),
                hours_at_install=round(hours_at_install, 1),
                cycles_at_install=int(cycles_at_install),
                hours_since_install=hours_since_install,
                cycles_since_install=cycles_since_install,
                wear_pct_hours=round(wear_pct_h, 1) if wear_pct_h else None,
                wear_pct_cycles=round(wear_pct_c, 1) if wear_pct_c else None,
                replacements_on_this_aircraft=replacements,
                status=status,
            ))
            install_id += 1

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE 4 — FLIGHT LOGS  (2-year window: 2024-2025)
# ═══════════════════════════════════════════════════════════════════════════════

def build_flight_logs(aircraft_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates ~2 years of flight records per aircraft.
    Applies seasonal load variation and realistic route roughness
    (PC-12 higher due to short-strip operations).
    """
    WINDOW_START = datetime(2024, 1, 1)
    records = []
    flight_id = 1

    for _, ac in aircraft_df.iterrows():
        if ac["status"] == "IN_MAINTENANCE":
            continue
        is_24   = ac["model"] == "PC-24"
        airports = PC24_AIRPORTS if is_24 else PC12_AIRPORTS
        base     = ac["base_facility"]

        current = WINDOW_START
        prev_airport = base

        while current <= SIM_END:
            month_mult = SEASONAL_LOAD[current.month]
            # base ~2.1 flights/day scaled by season; random day off
            n_flights = np.random.poisson(2.1 * month_mult)
            if np.random.random() < 0.08:   # 8% chance of ground day (mx / weather)
                n_flights = 0

            for _ in range(n_flights):
                dest = random.choice([a for a in airports if a != prev_airport])
                # Duration: PC-12 ~1.1h avg, PC-24 ~1.5h avg
                if is_24:
                    duration = max(0.4, np.random.normal(1.5, 0.4))
                else:
                    duration = max(0.3, np.random.normal(1.1, 0.35))
                duration = round(duration, 2)

                dep_h = int(np.random.normal(10, 3))
                dep_h = max(6, min(dep_h, 19))
                dep   = current.replace(hour=dep_h, minute=random.randint(0, 59))
                arr   = dep + timedelta(hours=duration)

                # Route roughness: PC-12 landing on short strips → higher
                if is_24:
                    roughness = round(np.random.beta(2, 5) * 5, 2)   # 0-5 scale
                else:
                    roughness = round(np.random.beta(3, 4) * 5, 2)   # slightly higher

                pax = random.randint(1, 6 if is_24 else 5)
                # Weather stress: winter adds cold-start load
                temp_c = round(np.random.normal(
                    15 - 20 * abs(current.month - 6.5) / 6, 8
                ), 1)

                records.append(dict(
                    flight_id=f"FLT-{flight_id:07d}",
                    tail_number=ac["tail_number"],
                    aircraft_model=ac["model"],
                    date=current.date(),
                    origin_airport=prev_airport,
                    destination_airport=dest,
                    departure_time=dep.strftime("%H:%M"),
                    arrival_time=arr.strftime("%H:%M"),
                    flight_hours=duration,
                    cycles=1,
                    passenger_count=pax,
                    route_roughness_index=roughness,
                    ambient_temp_c=temp_c,
                    precipitation=int(np.random.random() < 0.2),
                    crosswind_kt=round(abs(np.random.normal(0, 8)), 1),
                ))
                prev_airport = dest
                flight_id += 1

            current += timedelta(days=1)

    return pd.DataFrame(records)


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE 5 — SENSOR READINGS  (one snapshot per flight, key parameters)
# ═══════════════════════════════════════════════════════════════════════════════

def build_sensor_readings(flight_df: pd.DataFrame,
                          aircraft_df: pd.DataFrame) -> pd.DataFrame:
    """
    Simulates engine/component health sensor snapshots for each flight.
    Degradation is modelled as a gradual drift with random noise,
    calibrated to the aircraft's cumulative hours and age.
    """
    ac_map = aircraft_df.set_index("tail_number").to_dict("index")
    records = []

    for _, fl in flight_df.iterrows():
        tail   = fl["tail_number"]
        is_24  = fl["aircraft_model"] == "PC-24"
        ac     = ac_map.get(tail, {})
        total_h = ac.get("total_flight_hours", 1000)

        # Age-based degradation factor (0 = new, 1 = at life limit)
        deg = min(total_h / (3600 if is_24 else 3500), 1.0)

        # ── Engine parameters ───────────────────────────────────────────
        # EGT (Exhaust Gas Temperature °C) — higher as engine ages
        egt_baseline = (820 if is_24 else 780) + deg * 40
        egt = round(np.random.normal(egt_baseline, 12) +
                    (fl["ambient_temp_c"] - 15) * 0.4, 1)

        # Oil pressure PSI — decreases slightly with wear
        oil_psi_baseline = (62 - deg * 8) if is_24 else (58 - deg * 7)
        oil_psi = round(np.random.normal(oil_psi_baseline, 2.5), 1)

        # Oil temperature °C
        oil_temp = round(np.random.normal(88 + deg * 12, 5) +
                         fl["ambient_temp_c"] * 0.2, 1)

        # Vibration (g, RMS) — increases with bearing/gear wear
        vib_baseline = 0.05 + deg * 0.25
        vibration = round(abs(np.random.normal(vib_baseline, 0.04)), 3)

        # Fuel flow kg/hr
        fuel_baseline = (280 if is_24 else 195) + deg * 15
        fuel_flow = round(np.random.normal(fuel_baseline, 10), 1)

        # Hydraulic pressure PSI
        hyd_psi = round(np.random.normal(2950 - deg * 80, 40), 0)

        # Anomaly score — deviation from age-expected norms (low = healthy)
        # Uses signed standard deviations; only genuine exceedances contribute.
        vib_sigma  = (vibration - vib_baseline) / 0.04
        oil_sigma  = (oil_psi_baseline - oil_psi) / 2.5    # positive when oil LOW
        egt_sigma  = (egt - egt_baseline) / 12.0            # positive when EGT HIGH
        anomaly_score = round(min(1.0,
            max(0.0, vib_sigma - 1.0) * 0.10    # >1σ vib excess
            + max(0.0, oil_sigma - 1.0) * 0.10  # >1σ oil drop
            + max(0.0, egt_sigma - 1.0) * 0.07  # >1σ EGT spike
            + abs(float(np.random.normal(0.0, 0.015)))  # sensor noise floor
        ), 3)

        records.append(dict(
            flight_id=fl["flight_id"],
            tail_number=tail,
            date=fl["date"],
            egt_c=egt,
            oil_pressure_psi=oil_psi,
            oil_temp_c=oil_temp,
            vibration_g_rms=vibration,
            fuel_flow_kg_hr=fuel_flow,
            hydraulic_psi=hyd_psi,
            anomaly_score=anomaly_score,
        ))

    return pd.DataFrame(records)


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE 6 — MAINTENANCE RECORDS
# ═══════════════════════════════════════════════════════════════════════════════

TECHNICIANS = [f"TECH-{i:03d}" for i in range(1, 41)]   # 40 Atlas technicians

def build_maintenance_records(aircraft_df: pd.DataFrame,
                               install_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates scheduled and unscheduled maintenance events over 5 years.
    Mirrors Atlas Aircraft Center's documented processes.
    """
    ac_map  = aircraft_df.set_index("tail_number").to_dict("index")
    records = []
    wo_id   = 1

    for _, inst in install_df.iterrows():
        tail   = inst["tail_number"]
        cid    = inst["component_id"]
        ac     = ac_map.get(tail, {})
        total_h = ac.get("total_flight_hours", 500)
        del_date = datetime.combine(ac.get("delivery_date", datetime(2020,1,1).date()),
                                    datetime.min.time())

        # --- Scheduled inspections based on interval ---
        spec = next((s for s in COMPONENTS_SPEC if s[0] == cid), None)
        if spec is None:
            continue
        insp_interval = spec[6]

        span_days = max((SIM_END - del_date).days, 1)
        h = insp_interval
        while h <= total_h:
            day_offset = min(int(h / max(total_h, 1) * span_days), span_days - 1)
            insp_date  = del_date + timedelta(days=day_offset)
            finding = np.random.choice(
                ["NO_FINDING", "WEAR_WITHIN_LIMITS", "MINOR_DEFECT",
                 "REPLACEMENT_REQUIRED"],
                p=[0.55, 0.25, 0.14, 0.06]
            )
            action = {
                "NO_FINDING":          "INSPECT_RETURN_TO_SERVICE",
                "WEAR_WITHIN_LIMITS":  "LUBRICATION_ADJUSTMENT",
                "MINOR_DEFECT":        "REPAIR_IN_PLACE",
                "REPLACEMENT_REQUIRED":"COMPONENT_REPLACED",
            }[finding]

            records.append(dict(
                work_order_id=f"WO-{wo_id:06d}",
                tail_number=tail,
                component_id=cid,
                maintenance_type="SCHEDULED",
                maintenance_date=insp_date.date(),
                hours_at_event=round(h, 1),
                cycles_at_event=int(h / (ac.get("total_flight_hours",1) /
                                         max(ac.get("total_cycles",1),1))),
                finding_code=finding,
                action_taken=action,
                parts_replaced=int(action == "COMPONENT_REPLACED"),
                labor_hours=round(np.random.uniform(1.5, 8), 1),
                technician_id=random.choice(TECHNICIANS),
                facility=ac.get("base_facility","PSM"),
                aircraft_downtime_hours=round(np.random.uniform(2, 24)
                                              if finding != "NO_FINDING" else
                                              np.random.uniform(0.5, 3), 1),
            ))
            wo_id += 1
            h += insp_interval

        # --- Unscheduled events: ~4% probability per inspection interval ---
        n_unscheduled = max(0, int(total_h / insp_interval * 0.04))
        for _ in range(n_unscheduled):
            u_h = float(np.random.uniform(0, total_h))
            u_day_offset = min(int(u_h / max(total_h, 1) * span_days), span_days - 1)
            u_date = del_date + timedelta(days=u_day_offset)
            sev = np.random.choice(
                ["MINOR", "MODERATE", "MAJOR", "AOG"],
                p=[0.50, 0.30, 0.15, 0.05]
            )
            records.append(dict(
                work_order_id=f"WO-{wo_id:06d}",
                tail_number=tail,
                component_id=cid,
                maintenance_type="UNSCHEDULED",
                maintenance_date=u_date.date(),
                hours_at_event=round(u_h, 1),
                cycles_at_event=int(u_h / (ac.get("total_flight_hours",1) /
                                            max(ac.get("total_cycles",1),1))),
                finding_code=f"UNSCHEDULED_{sev}",
                action_taken="REPAIR_IN_PLACE" if sev in ("MINOR","MODERATE")
                             else "COMPONENT_REPLACED",
                parts_replaced=int(sev in ("MAJOR","AOG")),
                labor_hours=round(np.random.uniform(4, 32), 1),
                technician_id=random.choice(TECHNICIANS),
                facility=ac.get("base_facility","PSM"),
                aircraft_downtime_hours=round(
                    {"MINOR":4,"MODERATE":12,"MAJOR":36,"AOG":72}[sev]
                    * np.random.uniform(0.5, 1.8), 1
                ),
            ))
            wo_id += 1

    return pd.DataFrame(records)


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE 7 — FAILURE EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

def build_failure_events(mx_df: pd.DataFrame) -> pd.DataFrame:
    """Extracts AOG and MAJOR unscheduled events as the failure event log."""
    fail = mx_df[mx_df["maintenance_type"] == "UNSCHEDULED"].copy()
    fail = fail[fail["finding_code"].str.contains("AOG|MAJOR", na=False)].copy()

    fail = fail.rename(columns={
        "work_order_id":         "source_work_order",
        "hours_at_event":        "hours_at_failure",
        "cycles_at_event":       "cycles_at_failure",
        "aircraft_downtime_hours":"downtime_hours",
    })
    fail["event_id"]          = [f"EVT-{i:05d}" for i in range(1, len(fail)+1)]
    fail["failure_severity"]  = fail["finding_code"].apply(
        lambda x: "AOG" if "AOG" in str(x) else "MAJOR"
    )
    fail["detection_method"]  = np.random.choice(
        ["SCHEDULED_CHECK","PILOT_REPORT","SENSOR_ALERT","GROUND_INSPECTION"],
        size=len(fail), p=[0.35, 0.30, 0.20, 0.15]
    )
    fail["estimated_cost_usd"] = fail["downtime_hours"].apply(
        lambda h: round(h * np.random.uniform(800, 2500), -2)
    )

    keep = ["event_id","tail_number","component_id","maintenance_date",
            "hours_at_failure","cycles_at_failure","failure_severity",
            "detection_method","downtime_hours","estimated_cost_usd",
            "source_work_order"]
    return fail[keep].reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE 8 — PARTS INVENTORY
# ═══════════════════════════════════════════════════════════════════════════════

PARTS_CATALOG = [
    ("PT6A-67P-OH-KIT",   "PT6A-67P Overhaul Kit",          "ENG_PT6",   2, 6,  60, 185000),
    ("PT6A-67P-FUEL-NOZ", "PT6A-67P Fuel Nozzle Set",        "ENG_PT6",  18, 8,  21,   2800),
    ("FJ44-4A-OH-KIT",    "FJ44-4A Engine Overhaul Kit",     "ENG_FJ_L",  1, 4,  90, 220000),
    ("FJ44-BLADE-FAN",    "FJ44 Fan Blade",                  "ENG_FJ_L", 24, 6,  35,   4500),
    ("PT6-BRG-SET",       "PT6A Bearing Set",                "ENG_PT6",  12, 4,  45,   3200),
    ("PC12-PROP-BLADE",   "PC-12 Propeller Blade",           "PROP_ASS",  8, 3,  90,  12000),
    ("PC12-PROP-GOV",     "PC-12 Propeller Governor",        "PROP_ASS",  6, 2,  45,   8500),
    ("MLG-SEAL-KIT-PC12", "PC-12 Main LG Seal Kit",          "LDG_LH",   15, 6,  21,    850),
    ("MLG-SEAL-KIT-PC24", "PC-24 Main LG Seal Kit",          "LDG_LH",    8, 4,  28,   1200),
    ("NLG-SHIMMY-DAMP",   "Nose Gear Shimmy Damper",         "LDG_NOS",  10, 5,  30,   2200),
    ("HYD-PMP-OVERHAUL",  "Hydraulic Pump Overhaul",         "HYD_PMP",   5, 2,  60,   6500),
    ("HYD-SEAL-KIT",      "Hydraulic Seal Kit (Generic)",    "HYD_PMP",  25,10,  14,    320),
    ("FUEL-PUMP-LP-ASSY", "LP Fuel Pump Assembly",           "FUEL_LP",   8, 3,  45,   4800),
    ("FUEL-PUMP-HP-ASSY", "HP Fuel Pump Assembly",           "FUEL_HP",   6, 3,  45,   5200),
    ("ALTERNATOR-ASSY",   "Alternator Assembly",             "ALTERNTR",  4, 2,  45,   7200),
    ("MAIN-BATTERY-PC12", "PC-12 Main Battery 24V",          "BATTERY",  12, 6,  18,   1800),
    ("MAIN-BATTERY-PC24", "PC-24 Main Battery 28V",          "BATTERY",   6, 3,  21,   2400),
    ("BRAKE-ASSY-LH",     "Left Brake Assembly",             "BRK_LH",   20, 8,  14,   1500),
    ("BRAKE-ASSY-RH",     "Right Brake Assembly",            "BRK_RH",   20, 8,  14,   1500),
    ("BRAKE-DISC-LH",     "Left Brake Disc",                 "BRK_LH",   30,12,  10,    680),
    ("APU-STARTER",       "APU Starter Motor",               "APU",       4, 2,  45,   3800),
    ("THR-REV-ACT",       "Thrust Reverser Actuator",        "THR_REV_L", 6, 2,  60,   9500),
    ("OIL-FILTER-PT6",    "PT6A Oil Filter",                 "ENG_PT6",  40,20,   7,    180),
    ("OIL-FILTER-FJ44",   "FJ44 Oil Filter",                 "ENG_FJ_L", 30,15,   7,    210),
    ("TYRE-MAIN-PC12",    "PC-12 Main Wheel Tyre",           "LDG_LH",   60,20,   7,    420),
    ("TYRE-MAIN-PC24",    "PC-24 Main Wheel Tyre",           "LDG_LH",   40,15,  10,    580),
    ("TYRE-NOSE-PC12",    "PC-12 Nose Wheel Tyre",           "LDG_NOS",  50,20,   7,    280),
    ("TYRE-NOSE-PC24",    "PC-24 Nose Wheel Tyre",           "LDG_NOS",  35,15,  10,    380),
]

def build_parts_inventory() -> pd.DataFrame:
    rows = []
    for part_num, name, comp_id, qty_oh, reorder_pt, lead_days, unit_cost in PARTS_CATALOG:
        # Simulate supply-chain stress: some parts below reorder point
        at_risk = np.random.random() < 0.25    # 25% have supply chain exposure
        qty     = qty_oh if not at_risk else max(0, qty_oh - reorder_pt - random.randint(0,3))
        rows.append(dict(
            part_number=part_num,
            part_name=name,
            related_component_id=comp_id,
            quantity_on_hand=qty,
            reorder_point=reorder_pt,
            below_reorder=int(qty < reorder_pt),
            lead_time_days=lead_days,
            unit_cost_usd=unit_cost,
            annual_consumption=round(np.random.uniform(qty_oh * 2, qty_oh * 6)),
            last_order_date=(SIM_END - timedelta(days=random.randint(5, 90))).date(),
            preferred_supplier=random.choice([
                "Pilatus Aircraft Ltd", "Pratt & Whitney Canada",
                "Williams International", "Aviall Services",
                "Satair Group", "API Technologies"
            ]),
            supply_chain_risk=np.random.choice(
                ["LOW","MEDIUM","HIGH"], p=[0.55, 0.30, 0.15]
            ),
        ))
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE 9 — ML FEATURES  (model-ready aggregated feature matrix)
# ═══════════════════════════════════════════════════════════════════════════════

def build_ml_features(install_df: pd.DataFrame,
                       sensor_df: pd.DataFrame,
                       flight_df: pd.DataFrame,
                       mx_df: pd.DataFrame,
                       aircraft_df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per component-installation (current snapshot).
    Features are engineered from raw tables; targets are injected
    using a realistic hazard-rate model so class balance is ~80/12/8.

    Target columns
    --------------
    failure_within_50h   : int (0/1) — primary classification target
    failure_within_100h  : int (0/1) — secondary classification target
    remaining_useful_life_hours : float — regression target (RUL)
    risk_tier            : str LOW / MEDIUM / HIGH / CRITICAL
    """
    ac_map   = aircraft_df.set_index("tail_number").to_dict("index")

    # --- Rolling sensor aggregates per tail (last 30 days) ---
    sensor_df["date"] = pd.to_datetime(sensor_df["date"])
    cutoff = pd.Timestamp(SIM_END) - pd.Timedelta(days=30)
    recent = sensor_df[sensor_df["date"] >= cutoff].copy()
    sensor_agg = recent.groupby("tail_number").agg(
        avg_egt_30d              =("egt_c",               "mean"),
        max_egt_30d              =("egt_c",               "max"),
        avg_vibration_30d        =("vibration_g_rms",     "mean"),
        max_vibration_30d        =("vibration_g_rms",     "max"),
        vibration_std_30d        =("vibration_g_rms",     "std"),
        avg_oil_pressure_30d     =("oil_pressure_psi",    "mean"),
        min_oil_pressure_30d     =("oil_pressure_psi",    "min"),
        avg_oil_temp_30d         =("oil_temp_c",          "mean"),
        avg_anomaly_score_30d    =("anomaly_score",       "mean"),
        max_anomaly_score_30d    =("anomaly_score",       "max"),
        flights_last_30d         =("flight_id",           "count"),
    ).reset_index()

    # --- Recent flight aggregates per tail ---
    flight_df["date"] = pd.to_datetime(flight_df["date"])
    flight_recent = flight_df[flight_df["date"] >= cutoff].copy()
    flight_agg = flight_recent.groupby("tail_number").agg(
        avg_route_roughness_30d  =("route_roughness_index","mean"),
        total_flight_hours_30d   =("flight_hours",         "sum"),
        avg_crosswind_30d        =("crosswind_kt",         "mean"),
    ).reset_index()

    # --- Unscheduled events last 12 months per component ---
    mx_df["maintenance_date"] = pd.to_datetime(mx_df["maintenance_date"])
    cutoff_12m = pd.Timestamp(SIM_END) - pd.Timedelta(days=365)
    mx_recent = mx_df[
        (mx_df["maintenance_date"] >= cutoff_12m) &
        (mx_df["maintenance_type"] == "UNSCHEDULED")
    ].groupby(["tail_number","component_id"]).size().reset_index(
        name="unscheduled_events_12m"
    )

    # ── PASS 1: Build feature rows (no targets yet) ──────────────────────────
    rows = []
    for _, inst in install_df.iterrows():
        tail = inst["tail_number"]
        cid  = inst["component_id"]
        ac   = ac_map.get(tail, {})

        spec = next((s for s in COMPONENTS_SPEC if s[0] == cid), None)
        if spec is None:
            continue
        _, _, _, _, lh, lc, insp_int, _ = spec

        # Core wear features
        hours_since_install  = inst["hours_since_install"]
        cycles_since_install = inst["cycles_since_install"]
        wear_pct_h  = (hours_since_install  / lh  * 100) if lh  else 0.0
        wear_pct_c  = (cycles_since_install / lc  * 100) if lc  else 0.0
        wear_pct    = max(wear_pct_h, wear_pct_c)

        # Aircraft-level features
        ac_age_years = round(
            (SIM_END - datetime.combine(
                ac.get("delivery_date", datetime(2020,1,1).date()),
                datetime.min.time()
            )).days / 365, 2
        )
        is_pc24 = int(ac.get("model","") == "PC-24")

        # Merge sensor aggregates
        s = sensor_agg[sensor_agg["tail_number"] == tail]
        f = flight_agg[flight_agg["tail_number"] == tail]
        m = mx_recent[
            (mx_recent["tail_number"] == tail) &
            (mx_recent["component_id"]  == cid)
        ]

        avg_vib   = float(s["avg_vibration_30d"].values[0])   if len(s) else 0.08
        max_vib   = float(s["max_vibration_30d"].values[0])   if len(s) else 0.10
        vib_std   = float(s["vibration_std_30d"].values[0])   if len(s) else 0.02
        avg_egt   = float(s["avg_egt_30d"].values[0])         if len(s) else (840 if is_pc24 else 790)
        max_egt   = float(s["max_egt_30d"].values[0])         if len(s) else avg_egt + 15
        avg_oilp  = float(s["avg_oil_pressure_30d"].values[0])if len(s) else 60.0
        min_oilp  = float(s["min_oil_pressure_30d"].values[0])if len(s) else 55.0
        avg_oilt  = float(s["avg_oil_temp_30d"].values[0])    if len(s) else 88.0
        avg_ano   = float(s["avg_anomaly_score_30d"].values[0])if len(s) else 0.05
        max_ano   = float(s["max_anomaly_score_30d"].values[0])if len(s) else 0.10
        flt_30d   = int(s["flights_last_30d"].values[0])       if len(s) else 50
        rough_30d = float(f["avg_route_roughness_30d"].values[0]) if len(f) else 2.0
        hrs_30d   = float(f["total_flight_hours_30d"].values[0])  if len(f) else 55.0
        unsched   = int(m["unscheduled_events_12m"].values[0])    if len(m) else 0

        # Raw RUL from wear (target-independent; adjusted in pass 2)
        if lh:
            rul_raw = max(0.0, lh - hours_since_install)
        elif lc:
            rul_raw = max(0.0, lc - cycles_since_install) * (
                hrs_30d / max(flt_30d, 1)
            )
        else:   # calendar-only (battery) — proxy
            rul_raw = max(0.0, 365 * 24 * np.random.uniform(0.1, 1.0))

        rows.append(dict(
            installation_id          = inst["installation_id"],
            tail_number              = tail,
            component_id             = cid,
            component_name           = inst["component_name"],
            aircraft_model           = ac.get("model",""),
            base_facility            = ac.get("base_facility",""),
            snapshot_date            = SIM_END.date(),
            hours_since_install      = round(hours_since_install, 1),
            cycles_since_install     = int(cycles_since_install),
            wear_pct_hours           = round(wear_pct_h, 2),
            wear_pct_cycles          = round(wear_pct_c, 2),
            wear_pct_max             = round(wear_pct, 2),
            avg_vibration_30d        = round(avg_vib, 4),
            max_vibration_30d        = round(max_vib, 4),
            vibration_std_30d        = round(vib_std, 4),
            avg_egt_30d              = round(avg_egt, 1),
            max_egt_30d              = round(max_egt, 1),
            avg_oil_pressure_30d     = round(avg_oilp, 1),
            min_oil_pressure_30d     = round(min_oilp, 1),
            avg_oil_temp_30d         = round(avg_oilt, 1),
            avg_anomaly_score_30d    = round(avg_ano, 4),
            max_anomaly_score_30d    = round(max_ano, 4),
            flights_last_30d         = flt_30d,
            total_flight_hours_30d   = round(hrs_30d, 1),
            avg_route_roughness_30d  = round(rough_30d, 2),
            unscheduled_events_12m   = unsched,
            aircraft_age_years       = ac_age_years,
            is_pc24                  = is_pc24,
            _rul_raw                 = round(rul_raw, 1),
            _min_oilp                = round(min_oilp, 1),
            _max_egt                 = round(max_egt, 1),
        ))

    df = pd.DataFrame(rows)

    # ── PASS 2: Rank-based target assignment ─────────────────────────────────
    # Composite hazard score: higher = more likely to fail.
    # Using normalised features so each contributes meaningfully.
    # A small uniform noise term breaks ties without swamping the signal.
    egt_thresh = np.where(df["is_pc24"] == 1, 895.0, 855.0)
    df["_hazard"] = (
        (df["wear_pct_max"] / 100.0) * 0.40            # wear: 0 → 0, 100 → 0.40
        + (df["max_vibration_30d"] / 0.35).clip(0, 1) * 0.20  # vib
        + (df["max_anomaly_score_30d"] / 0.35).clip(0, 1) * 0.20  # anomaly
        + df["unscheduled_events_12m"] * 0.12           # event history
        + (df["_min_oilp"] < 48).astype(float) * 0.04  # oil pressure alarm
        + (df["_max_egt"] > pd.Series(egt_thresh, index=df.index)).astype(float) * 0.04
        + np.random.uniform(0.0, 0.03, len(df))        # tie-breaking noise
    )

    # Assign top 8% → fail_50h, top 20% → fail_100h (inclusive)
    thr_50h  = df["_hazard"].quantile(0.92)
    thr_100h = df["_hazard"].quantile(0.80)
    df["failure_within_50h"]  = (df["_hazard"] >= thr_50h).astype(int)
    df["failure_within_100h"] = (
        (df["_hazard"] >= thr_100h) | (df["failure_within_50h"] == 1)
    ).astype(int)

    # Adjust RUL to be consistent with failure labels
    rng = np.random.default_rng(seed=99)
    rul_vals = []
    for _, row in df.iterrows():
        if row["failure_within_50h"]:
            rul_vals.append(round(float(rng.uniform(1, 49)), 1))
        elif row["failure_within_100h"]:
            rul_vals.append(round(float(rng.uniform(50, 99)), 1))
        else:
            rul_vals.append(round(max(100.0, row["_rul_raw"] * rng.uniform(0.85, 1.05)), 1))
    df["remaining_useful_life_hours"] = rul_vals

    # Risk tier: based on assigned targets + wear
    def _tier(row):
        if row["failure_within_50h"] or row["remaining_useful_life_hours"] < 50:
            return "CRITICAL"
        if row["failure_within_100h"] or row["remaining_useful_life_hours"] < 150:
            return "HIGH"
        if row["wear_pct_max"] > 70 or row["_hazard"] > df["_hazard"].quantile(0.55):
            return "MEDIUM"
        return "LOW"
    df["risk_tier"] = df.apply(_tier, axis=1)

    # Drop temporary columns
    df = df.drop(columns=["_hazard", "_rul_raw", "_min_oilp", "_max_egt"])
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def save(df: pd.DataFrame, name: str) -> None:
    path = os.path.join(OUT_DIR, name)
    df.to_csv(path, index=False)
    print(f"  ✓  {name:<45s}  {len(df):>7,} rows   {os.path.getsize(path)/1024:>8.1f} KB")


def main():
    print("=" * 65)
    print("PlaneSense Predictive Maintenance — Synthetic Data Generator")
    print("=" * 65)

    print("\n[1/9] Aircraft registry …")
    aircraft   = build_aircraft_registry()
    save(aircraft, "aircraft_registry.csv")

    print("[2/9] Components master …")
    components = build_components_master()
    save(components, "components_master.csv")

    print("[3/9] Component installations …")
    installs   = build_component_installations(aircraft)
    save(installs, "component_installations.csv")

    print("[4/9] Flight logs (2024-2025) …")
    flights    = build_flight_logs(aircraft)
    save(flights, "flight_logs.csv")

    print("[5/9] Sensor readings …")
    sensors    = build_sensor_readings(flights, aircraft)
    save(sensors, "sensor_readings.csv")

    print("[6/9] Maintenance records …")
    mx         = build_maintenance_records(aircraft, installs)
    save(mx, "maintenance_records.csv")

    print("[7/9] Failure events …")
    failures   = build_failure_events(mx)
    save(failures, "failure_events.csv")

    print("[8/9] Parts inventory …")
    parts      = build_parts_inventory()
    save(parts, "parts_inventory.csv")

    print("[9/9] ML features (model-ready) …")
    features   = build_ml_features(installs, sensors, flights, mx, aircraft)
    save(features, "ml_features.csv")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("DATASET SUMMARY")
    print("=" * 65)
    print(f"  Aircraft         : {len(aircraft)} "
          f"({(aircraft.model=='PC-12 NGX').sum()} PC-12 + "
          f"{(aircraft.model=='PC-24').sum()} PC-24)")
    print(f"  Component types  : {len(components)}")
    print(f"  Installations    : {len(installs)}")
    print(f"  Flight records   : {len(flights):,}")
    print(f"  Sensor snapshots : {len(sensors):,}")
    print(f"  Work orders      : {len(mx):,}")
    print(f"  Failure events   : {len(failures):,}")
    print(f"  Parts (SKUs)     : {len(parts)}")
    print(f"  ML feature rows  : {len(features):,}")

    tf = features
    print(f"\n  ML TARGET DISTRIBUTION")
    print(f"  failure_within_50h  : "
          f"{tf.failure_within_50h.sum():>4} critical  "
          f"({tf.failure_within_50h.mean()*100:.1f}%)")
    print(f"  failure_within_100h : "
          f"{tf.failure_within_100h.sum():>4} at-risk   "
          f"({tf.failure_within_100h.mean()*100:.1f}%)")
    print(f"  Risk tiers          : "
          + "  ".join(f"{k}={v}" for k, v in
                       tf.risk_tier.value_counts().to_dict().items()))
    print(f"\n  Output directory : {OUT_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()

"""
regenerate_routes_v2.py
=======================
Revises synthetic flight route data for PlaneSense dataset.

Changes made:
  - Replaces uniform-random airport sampling with weighted probability matrix:
      model × flight_purpose × season × owner_region → airport_pair_weights
  - Enforces PC-12 pc12_accessible constraint (no PC-24-only airports)
  - Enforces PC-24 range advantage and western airport cluster for KBVU-based aircraft
  - Adds KPSM dominance as primary hub origin
  - Recalculates: distance_nm, flight_hours, block_hours, fuel_consumed_gal,
                  departure_time, arrival_time
  - Adds new columns: season, day_of_week to fact_flight
  - Adds new column: owner_type to dim_owner
  - Syncs fact_booking origin/destination with revised fact_flight routes
"""

import csv
import math
import random
import os
from datetime import datetime, timedelta
from collections import defaultdict

random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'output', 'analytics', 'data')

# ---------------------------------------------------------------------------
# Aircraft performance constants
# ---------------------------------------------------------------------------
PERF = {
    'PC-12 NGX': {'cruise_knots': 270, 'fuel_gph': 68,  'block_factor': 1.15, 'max_nm': 600},
    'PC-24':     {'cruise_knots': 340, 'fuel_gph': 95,  'block_factor': 1.15, 'max_nm': 1200},
}

# ---------------------------------------------------------------------------
# Helper: haversine distance in nautical miles
# ---------------------------------------------------------------------------
def haversine_nm(lat1, lon1, lat2, lon2):
    R = 3440.065  # Earth radius in nm
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ---------------------------------------------------------------------------
# Helper: season from month
# ---------------------------------------------------------------------------
def get_season(month):
    if month in (12, 1, 2):  return 'Winter'
    if month in (3, 4, 5):   return 'Spring'
    if month in (6, 7, 8):   return 'Summer'
    return 'Fall'

# ---------------------------------------------------------------------------
# Helper: ISO day of week (1=Mon, 7=Sun)
# ---------------------------------------------------------------------------
def get_dow(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').isoweekday()

# ---------------------------------------------------------------------------
# Load dim_airport
# ---------------------------------------------------------------------------
def load_airports():
    airports = {}
    with open(os.path.join(DATA_DIR, 'dim_airport.csv')) as f:
        for row in csv.DictReader(f):
            airports[row['airport_icao']] = {
                'lat':          float(row['latitude']),
                'lon':          float(row['longitude']),
                'pc12_ok':      int(row['pc12_accessible']) == 1,
                'pc24_ok':      int(row['pc24_accessible']) == 1,
                'region':       row['region'],
                'city':         row['city'],
                'state':        row['state'],
            }
    return airports

# ---------------------------------------------------------------------------
# Load dim_owner
# ---------------------------------------------------------------------------
def load_owners():
    owners = {}
    with open(os.path.join(DATA_DIR, 'dim_owner.csv')) as f:
        for row in csv.DictReader(f):
            owners[row['owner_id']] = {
                'region':     row['region'],
                'share_type': row['share_type'],
                'preference': row['aircraft_preference'],
            }
    return owners

# ---------------------------------------------------------------------------
# Load dim_aircraft  (to know base_facility per aircraft)
# ---------------------------------------------------------------------------
def load_aircraft():
    aircraft = {}
    with open(os.path.join(DATA_DIR, 'dim_aircraft.csv')) as f:
        for row in csv.DictReader(f):
            aircraft[row['aircraft_id']] = {
                'model':    row['model'],
                'facility': row['base_facility_id'],
                'region':   row['region'],
            }
    return aircraft

# ---------------------------------------------------------------------------
# Airport weight tables
# ---------------------------------------------------------------------------

# Northeast business hubs
BIZ_NE   = ['KTEB','KHPN','KEWR','KJFK','KBOS','KBDL','KPVD','KBED','KIAD','KPHL']
# Southeast business
BIZ_SE   = ['KATL','KCLT','KMIA','KTPA','KFLL']
# Midwest business
BIZ_MW   = ['KORD','KMSP']
# West business
BIZ_WE   = ['KLAX','KSFO','KLAS','KDEN','KSAN']

# Leisure - Northeast summer islands/coastal
LEIS_SUMMER_NE = ['KACK','KMVY','2B2','K1B1','KPWM','KSFM','KBDL','KPVD']
# Leisure - Florida/South winter
LEIS_WINTER_FL = ['KMIA','KPBI','KFLL','KTPA']
# Leisure - West (year-round leisure)
LEIS_WE        = ['KLAS','KSAN','KAPC','KLAX','KSFO']

# Medical hubs (near major hospital clusters)
MEDICAL_HUBS = ['KBOS','KJFK','KEWR','KPHL','KIAD','KATL','KBDL']

# PC-12 short-strip favorites (exclude PC-24-only airports handled by constraint)
PC12_FAVORITES = ['KACK','KMVY','2B2','K1B1','KSFM','KPWM','KBED','KMHT']


def build_dest_weights(model, purpose, season, owner_region, base_facility, airports, origin):
    """
    Return a dict {icao: weight} for destination selection.
    Excludes origin and enforces model accessibility + distance constraints.
    """
    weights = {}

    is_pc12 = (model == 'PC-12 NGX')
    is_bvu_based = (base_facility == 'FAC-BVU')
    max_nm = PERF[model]['max_nm']

    # Origin coordinates for distance filtering
    origin_ap = airports.get(origin)
    origin_lat = origin_ap['lat'] if origin_ap else None
    origin_lon = origin_ap['lon'] if origin_ap else None

    for icao, ap in airports.items():
        if icao == origin:
            continue
        # Model accessibility gate
        if is_pc12 and not ap['pc12_ok']:
            continue
        if not is_pc12 and not ap['pc24_ok']:
            continue
        # Distance constraint: exclude airports beyond practical range
        if origin_lat is not None:
            dist = haversine_nm(origin_lat, origin_lon, ap['lat'], ap['lon'])
            if dist > max_nm:
                continue

        w = 1.0  # base weight

        # ---- PURPOSE weights ----
        if purpose == 'Business':
            if icao in BIZ_NE:   w += 8.0
            if icao in BIZ_SE:   w += 4.0
            if icao in BIZ_MW:   w += 3.0
            if icao in BIZ_WE:   w += 2.0 if not is_pc12 else 0.5
            # Business dips at holiday months handled via DOW/volume, not destination

        elif purpose == 'Leisure':
            if season == 'Summer':
                if icao in LEIS_SUMMER_NE: w += 10.0
                if icao in LEIS_WINTER_FL: w += 1.0   # Florida less popular in summer
                if icao in LEIS_WE:        w += 2.0 if not is_pc12 else 0.3
            elif season == 'Winter':
                if icao in LEIS_WINTER_FL: w += 10.0
                if icao in LEIS_SUMMER_NE: w += 2.0   # Some still go to coast in winter
                if icao in LEIS_WE:        w += 4.0 if not is_pc12 else 0.5
            else:  # Spring / Fall
                if icao in LEIS_SUMMER_NE: w += 5.0
                if icao in LEIS_WINTER_FL: w += 4.0
                if icao in LEIS_WE:        w += 3.0 if not is_pc12 else 0.5

        elif purpose == 'Medical':
            if icao in MEDICAL_HUBS: w += 12.0

        elif purpose == 'Mixed':
            if icao in BIZ_NE:         w += 4.0
            if icao in LEIS_SUMMER_NE and season == 'Summer': w += 4.0
            if icao in LEIS_WINTER_FL and season == 'Winter': w += 4.0

        # ---- OWNER REGION bias ----
        if owner_region == 'Northeast':
            if ap['region'] == 'Northeast':   w *= 2.5
            if ap['region'] == 'Mid-Atlantic': w *= 1.5
        elif owner_region == 'Mid-Atlantic':
            if ap['region'] in ('Northeast', 'Mid-Atlantic'): w *= 2.0
            if ap['region'] == 'Southeast':   w *= 1.3
        elif owner_region == 'Southeast':
            if ap['region'] == 'Southeast':   w *= 2.5
            if ap['region'] in ('Northeast', 'Mid-Atlantic'): w *= 1.3
        elif owner_region == 'West':
            if ap['region'] == 'West':        w *= 3.0
            if ap['region'] == 'Midwest':     w *= 1.2
        elif owner_region == 'Midwest':
            if ap['region'] == 'Midwest':     w *= 2.0
            if ap['region'] in ('Northeast', 'Southeast'): w *= 1.3

        # ---- KBVU base bias (West PC-24 cluster) ----
        if is_bvu_based:
            if ap['region'] == 'West':        w *= 3.0
            if ap['region'] == 'Midwest':     w *= 1.5

        # ---- PC-12 short-strip favorites ----
        if is_pc12 and icao in PC12_FAVORITES:
            w *= 1.5

        weights[icao] = max(w, 0.0)

    # Filter out zero-weight
    weights = {k: v for k, v in weights.items() if v > 0}
    return weights


def weighted_choice(weights_dict):
    keys = list(weights_dict.keys())
    vals = list(weights_dict.values())
    total = sum(vals)
    r = random.random() * total
    cumul = 0
    for k, v in zip(keys, vals):
        cumul += v
        if r <= cumul:
            return k
    return keys[-1]


# ---------------------------------------------------------------------------
# KPSM origin bias: for revenue flights where origin would normally be KPSM
# we preserve KPSM as origin ~40% of the time (hub dominance)
# ---------------------------------------------------------------------------
def pick_origin(model, purpose, season, owner_region, base_facility, airports, exclude=None):
    """Pick a weighted origin (separate from destination logic)."""
    # KPSM dominance: 40% chance to force KPSM as origin for Northeast/general flights
    if (purpose not in ('Repositioning', 'Maintenance Ferry')
            and owner_region in ('Northeast', 'Mid-Atlantic')
            and base_facility == 'FAC-PSM'
            and random.random() < 0.40):
        return 'KPSM'

    # Otherwise pick from the same weight pool as destination
    ex = exclude or set()
    weights = build_dest_weights(model, purpose, season, owner_region, base_facility, airports, '__NONE__')
    weights = {k: v for k, v in weights.items() if k not in ex}
    if not weights:
        return 'KPSM'
    return weighted_choice(weights)


# ---------------------------------------------------------------------------
# Recalculate derived flight fields
# ---------------------------------------------------------------------------
def calc_derived(origin, dest, model, departure_dt, airports):
    ap_o = airports[origin]
    ap_d = airports[dest]
    dist = round(haversine_nm(ap_o['lat'], ap_o['lon'], ap_d['lat'], ap_d['lon']))
    perf = PERF[model]
    flight_hrs = round(dist / perf['cruise_knots'], 2)
    block_hrs  = round(flight_hrs * perf['block_factor'], 2)
    fuel       = round(flight_hrs * perf['fuel_gph'], 1)
    arrival_dt = departure_dt + timedelta(hours=block_hrs)
    return dist, flight_hrs, block_hrs, fuel, arrival_dt


def weighted_departure_hour(purpose, dow):
    """Return a departure hour (int) weighted by purpose and day-of-week."""
    if purpose == 'Business':
        # Early morning departures, peak Mon(1) and Fri(5)
        pool = [6, 6, 7, 7, 7, 8, 8, 9, 10, 11, 13, 14, 15, 16, 17]
    elif purpose == 'Leisure':
        # Mid-morning, peak Fri(5) and Sun(7)
        pool = [8, 9, 9, 10, 10, 10, 11, 11, 12, 13, 14, 15, 16]
    elif purpose == 'Medical':
        pool = [6, 7, 7, 8, 8, 9, 9, 10, 11]
    else:
        pool = [7, 8, 9, 10, 11, 12, 13, 14, 15]
    return random.choice(pool)


# ---------------------------------------------------------------------------
# owner_type assignment
# ---------------------------------------------------------------------------
def assign_owner_type(share_type, preference):
    """
    Heuristic: large shares (1/4, 1/8) → Corporate
    Small shares (1/32, 1/16) personal → Individual or Family
    """
    if share_type in ('1/4', '1/8', '1/6'):
        return 'Corporate'
    elif share_type in ('1/32',):
        return 'Family'
    else:
        # 1/16, mixed → bias Individual
        if preference == 'PC-24':
            return 'Corporate'
        return 'Individual'


# ---------------------------------------------------------------------------
# Main regeneration
# ---------------------------------------------------------------------------
def main():
    print("Loading reference tables...")
    airports  = load_airports()
    owners    = load_owners()
    aircraft  = load_aircraft()

    # ---- Update dim_owner: add owner_type (idempotent — skip if already present) ----
    print("Adding owner_type to dim_owner...")
    owner_rows = []
    with open(os.path.join(DATA_DIR, 'dim_owner.csv')) as f:
        reader = csv.DictReader(f)
        existing_cols = reader.fieldnames
        already_has_owner_type = 'owner_type' in existing_cols
        fieldnames = existing_cols if already_has_owner_type else existing_cols + ['owner_type']
        for row in reader:
            row['owner_type'] = assign_owner_type(row['share_type'], row['aircraft_preference'])
            owner_rows.append(row)

    with open(os.path.join(DATA_DIR, 'dim_owner.csv'), 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(owner_rows)
    print(f"  dim_owner: {len(owner_rows)} rows updated.")

    # ---- Load full fact_flight ----
    print("Loading fact_flight...")
    flight_rows = []
    with open(os.path.join(DATA_DIR, 'fact_flight.csv')) as f:
        reader = csv.DictReader(f)
        ff_fields = reader.fieldnames
        for row in reader:
            flight_rows.append(row)
    print(f"  fact_flight: {len(flight_rows)} rows loaded.")

    # ---- Load fact_booking ----
    print("Loading fact_booking...")
    booking_rows = []
    with open(os.path.join(DATA_DIR, 'fact_booking.csv')) as f:
        reader = csv.DictReader(f)
        fb_fields = reader.fieldnames
        for row in reader:
            booking_rows.append(row)
    booking_by_id = {r['booking_id']: r for r in booking_rows}
    print(f"  fact_booking: {len(booking_rows)} rows loaded.")

    # ---- Group flights by journey (booking_id) for coherent multi-leg handling ----
    journeys = defaultdict(list)
    standalone = []
    for row in flight_rows:
        if row['booking_id']:
            journeys[row['booking_id']].append(row)
        else:
            standalone.append(row)

    # Sort legs within each journey
    for bid in journeys:
        journeys[bid].sort(key=lambda r: int(r['journey_leg_seq']))

    print(f"  Journeys: {len(journeys)} bookings, {len(standalone)} standalone flights")

    # ---- Process each journey ----
    print("Regenerating routes...")
    processed = 0

    def get_owner_region(owner_id):
        o = owners.get(owner_id)
        return o['region'] if o else 'Northeast'

    def get_base_facility(aircraft_id):
        a = aircraft.get(aircraft_id)
        return a['facility'] if a else 'FAC-PSM'

    for bid, legs in journeys.items():
        first_leg = legs[0]
        model     = first_leg['model']
        purpose   = first_leg['flight_purpose']
        date_str  = first_leg['date']
        month     = int(date_str[5:7])
        season    = get_season(month)
        owner_id  = first_leg['owner_id']
        owner_reg = get_owner_region(owner_id)
        base_fac  = get_base_facility(first_leg['aircraft_id'])

        # Pick journey-level origin and destination
        if purpose in ('Maintenance Ferry',):
            # Maintenance: KPSM ↔ KBVU or back to home base
            if base_fac == 'FAC-BVU':
                journey_origin = 'KBVU'
                journey_dest   = random.choice(['KPSM', 'KBVU', 'KLAS', 'KSAN'])
            else:
                journey_origin = 'KPSM'
                journey_dest   = random.choice(['KBVU', 'KPSM', 'KBDL', 'KMHT'])
        elif purpose == 'Repositioning':
            # Repositioning: go back toward a hub or next likely pickup
            journey_origin = random.choice(list(airports.keys()))
            while not (airports[journey_origin]['pc12_ok'] if model == 'PC-12 NGX' else airports[journey_origin]['pc24_ok']):
                journey_origin = random.choice(list(airports.keys()))
            journey_dest = 'KPSM' if random.random() < 0.5 else random.choice(
                [a for a in BIZ_NE if airports[a]['pc12_ok' if model == 'PC-12 NGX' else 'pc24_ok']]
            )
        else:
            # Revenue flight: pick origin first, then destination using origin for distance filtering
            if (owner_reg in ('Northeast', 'Mid-Atlantic')
                    and base_fac == 'FAC-PSM'
                    and random.random() < 0.40):
                journey_origin = 'KPSM'
            else:
                origin_weights = build_dest_weights(model, purpose, season, owner_reg, base_fac, airports, 'KPSM')
                journey_origin = weighted_choice(origin_weights) if origin_weights else 'KPSM'
            # Now pick destination using actual origin for distance constraint
            dest_weights = build_dest_weights(model, purpose, season, owner_reg, base_fac, airports, journey_origin)
            journey_dest = weighted_choice(dest_weights) if dest_weights else 'KBOS'

        # Ensure origin != dest
        if journey_origin == journey_dest:
            alts = [a for a in airports if a != journey_origin
                    and (airports[a]['pc12_ok'] if model == 'PC-12 NGX' else airports[a]['pc24_ok'])]
            journey_dest = random.choice(alts)

        # Assign legs coherently
        if len(legs) == 1:
            # Single-leg journey
            leg = legs[0]
            origin = journey_origin
            dest   = journey_dest
        else:
            # Multi-leg: first leg origin → intermediate → final dest
            # Intermediate: pick an airport in between geographically
            intermediate_weights = build_dest_weights(
                model, purpose, season, owner_reg, base_fac, airports, journey_origin
            )
            intermediate_weights.pop(journey_dest, None)
            intermediate = weighted_choice(intermediate_weights) if intermediate_weights else journey_dest

        for i, leg in enumerate(legs):
            if len(legs) == 1:
                origin = journey_origin
                dest   = journey_dest
            elif i == 0:
                origin = journey_origin
                dest   = intermediate
            elif i == len(legs) - 1:
                origin = intermediate
                dest   = journey_dest
            else:
                origin = intermediate
                dest   = journey_dest

            # Recalculate derived fields
            dow = get_dow(leg['date'])
            dep_hour = weighted_departure_hour(purpose, dow)
            dep_min  = random.randint(0, 59)
            dep_dt   = datetime.strptime(leg['date'], '%Y-%m-%d').replace(
                hour=dep_hour, minute=dep_min
            )

            # Guard: if airport missing, fall back
            if origin not in airports or dest not in airports:
                origin = 'KPSM'
                dest   = 'KBOS'

            dist, flt_h, blk_h, fuel, arr_dt = calc_derived(origin, dest, model, dep_dt, airports)

            leg['origin_icao']       = origin
            leg['destination_icao']  = dest
            leg['distance_nm']       = str(dist)
            leg['flight_hours']      = str(flt_h)
            leg['block_hours']       = str(blk_h)
            leg['fuel_consumed_gal'] = str(fuel)
            leg['departure_time']    = dep_dt.strftime('%Y-%m-%d %H:%M')
            leg['arrival_time']      = arr_dt.strftime('%Y-%m-%d %H:%M')
            leg['season']            = get_season(int(leg['date'][5:7]))
            leg['day_of_week']       = str(dow)

        # Sync booking record
        if bid in booking_by_id:
            booking_by_id[bid]['origin_icao']      = journey_origin
            booking_by_id[bid]['destination_icao'] = journey_dest

        processed += 1
        if processed % 10000 == 0:
            print(f"  ...{processed} journeys processed")

    # Standalone flights (repositioning/maintenance with no booking_id)
    for leg in standalone:
        model    = leg['model']
        purpose  = leg['flight_purpose']
        date_str = leg['date']
        month    = int(date_str[5:7])
        season   = get_season(month)
        base_fac = get_base_facility(leg['aircraft_id'])

        max_nm = PERF[model]['max_nm']
        if purpose == 'Maintenance Ferry':
            # PC-12 can't fly direct KPSM↔KBVU (2300nm) — use nearest relay for PC-12
            if model == 'PC-12 NGX':
                origin = 'KPSM' if base_fac == 'FAC-PSM' else 'KBVU'
                # Nearest reachable hub for relay
                dest = random.choice(['KORD', 'KBDL', 'KMHT', 'KPWM']) if origin == 'KPSM' else random.choice(['KORD', 'KDEN', 'KLAS'])
            else:
                origin = 'KPSM' if base_fac == 'FAC-PSM' else 'KBVU'
                dest   = 'KBVU' if origin == 'KPSM' else 'KPSM'
        else:
            # Repositioning: any valid airport pair within model range
            valid = [a for a in airports
                     if (airports[a]['pc12_ok'] if model == 'PC-12 NGX' else airports[a]['pc24_ok'])]
            origin = random.choice(valid)
            # Filter destinations within range
            valid_dest = [a for a in valid if a != origin
                          and haversine_nm(airports[origin]['lat'], airports[origin]['lon'],
                                           airports[a]['lat'], airports[a]['lon']) <= max_nm]
            if not valid_dest:
                valid_dest = [a for a in valid if a != origin]
            # Only use KPSM if it is within range from origin
            kpsm_dist = haversine_nm(airports[origin]['lat'], airports[origin]['lon'],
                                     airports['KPSM']['lat'], airports['KPSM']['lon'])
            if random.random() < 0.4 and kpsm_dist <= max_nm:
                dest = 'KPSM'
            else:
                dest = random.choice(valid_dest)

        dow     = get_dow(leg['date'])
        dep_hour = weighted_departure_hour(purpose, dow)
        dep_min  = random.randint(0, 59)
        dep_dt   = datetime.strptime(leg['date'], '%Y-%m-%d').replace(hour=dep_hour, minute=dep_min)

        if origin not in airports or dest not in airports:
            origin, dest = 'KPSM', 'KBOS'

        dist, flt_h, blk_h, fuel, arr_dt = calc_derived(origin, dest, model, dep_dt, airports)

        leg['origin_icao']       = origin
        leg['destination_icao']  = dest
        leg['distance_nm']       = str(dist)
        leg['flight_hours']      = str(flt_h)
        leg['block_hours']       = str(blk_h)
        leg['fuel_consumed_gal'] = str(fuel)
        leg['departure_time']    = dep_dt.strftime('%Y-%m-%d %H:%M')
        leg['arrival_time']      = arr_dt.strftime('%Y-%m-%d %H:%M')
        leg['season']            = season
        leg['day_of_week']       = str(dow)

    # ---- Write fact_flight (idempotent — only add season/day_of_week if not already present) ----
    print("Writing fact_flight...")
    extra = [c for c in ['season', 'day_of_week'] if c not in ff_fields]
    new_ff_fields = ff_fields + extra
    all_flights = []
    for legs in journeys.values():
        all_flights.extend(legs)
    all_flights.extend(standalone)
    all_flights.sort(key=lambda r: r['flight_id'])

    with open(os.path.join(DATA_DIR, 'fact_flight.csv'), 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_ff_fields)
        writer.writeheader()
        writer.writerows(all_flights)
    print(f"  fact_flight: {len(all_flights)} rows written.")

    # ---- Write fact_booking ----
    print("Writing fact_booking...")
    with open(os.path.join(DATA_DIR, 'fact_booking.csv'), 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fb_fields)
        writer.writeheader()
        writer.writerows(booking_rows)
    print(f"  fact_booking: {len(booking_rows)} rows written.")

    print("\nDone. Summary:")
    print(f"  fact_flight   : {len(all_flights)} rows, new columns: season, day_of_week")
    print(f"  fact_booking  : {len(booking_rows)} rows, routes synced")
    print(f"  dim_owner     : {len(owner_rows)} rows, new column: owner_type")


if __name__ == '__main__':
    main()

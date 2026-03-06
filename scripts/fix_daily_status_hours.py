"""
fix_daily_status_hours.py
==========================
Fixes data integrity violations in fact_aircraft_daily_status.csv:

Rule:
  - FLYING rows     : flight_hours > 0, flight_cycles > 0 (must have valid values)
  - AVAILABLE rows  : flight_hours = 0, flight_cycles = 0
  - IN_MAINTENANCE  : flight_hours = 0, flight_cycles = 0
  - AOG             : flight_hours = 0, flight_cycles = 0

Fixes applied:
  1. Non-FLYING rows with hours/cycles > 0  → set both to 0
  2. FLYING rows with hours = 0 or cycles = 0 → assign realistic values
     sourced from the same aircraft's average daily hours from fact_flight,
     or fleet average if no match found.
"""

import csv
import os
import random
from collections import defaultdict

random.seed(55)

DATA_DIR    = os.path.join(os.path.dirname(__file__), '..', 'output', 'analytics', 'data')
STATUS_FILE = os.path.join(DATA_DIR, 'fact_aircraft_daily_status.csv')
FLIGHT_FILE = os.path.join(DATA_DIR, 'fact_flight.csv')


def main():
    # -----------------------------------------------------------------------
    # Build per-aircraft average daily flight hours from fact_flight
    # -----------------------------------------------------------------------
    print("Loading fact_flight to compute aircraft daily hour averages...")
    ac_day_hours = defaultdict(list)
    with open(FLIGHT_FILE) as f:
        for row in csv.DictReader(f):
            ac  = row['aircraft_id']
            dt  = row['date']
            try:
                hrs = float(row['flight_hours'] or 0)
                if hrs > 0:
                    ac_day_hours[(ac, dt)].append(hrs)
            except:
                pass

    # Sum hours per aircraft per day (multiple flights in one day)
    ac_daily_totals = {}
    for (ac, dt), hrs_list in ac_day_hours.items():
        ac_daily_totals[(ac, dt)] = sum(hrs_list)

    # Average daily hours per aircraft (only flying days)
    ac_avg = defaultdict(list)
    for (ac, dt), total in ac_daily_totals.items():
        ac_avg[ac].append(total)
    ac_mean = {ac: sum(vals) / len(vals) for ac, vals in ac_avg.items()}

    # Fleet-wide average for fallback
    all_vals = [v for vals in ac_avg.values() for v in vals]
    fleet_mean = sum(all_vals) / len(all_vals) if all_vals else 2.5
    print(f"  Fleet mean daily flight hours (flying days only): {fleet_mean:.2f}")

    # -----------------------------------------------------------------------
    # Load and fix fact_aircraft_daily_status
    # -----------------------------------------------------------------------
    print("\nLoading fact_aircraft_daily_status...")
    rows = []
    fieldnames = None
    with open(STATUS_FILE) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    print(f"  {len(rows)} rows loaded.")

    fixed_zero   = 0   # non-FLYING rows zeroed out
    fixed_flying = 0   # FLYING rows given realistic hours

    for row in rows:
        status = row['status']
        hrs    = float(row['flight_hours'] or 0)
        cyc    = int(float(row['flight_cycles'] or 0))

        if status != 'FLYING':
            # Rule: must be 0
            if hrs != 0 or cyc != 0:
                row['flight_hours']  = '0.0'
                row['flight_cycles'] = '0'
                fixed_zero += 1

        else:
            # Rule: FLYING must have hours > 0 and cycles > 0
            if hrs == 0 or cyc == 0:
                ac  = row['aircraft_id']
                dt  = row['date']
                # Try exact match from fact_flight for this aircraft+date
                actual = ac_daily_totals.get((ac, dt))
                if actual and actual > 0:
                    assigned_hrs = round(actual, 2)
                else:
                    # Use aircraft average ± small jitter, fallback to fleet mean
                    mean = ac_mean.get(ac, fleet_mean)
                    assigned_hrs = round(max(0.3, random.gauss(mean, mean * 0.15)), 2)

                # Cycles: typically 1 per ~1.5 hrs of flight, min 1
                assigned_cyc = max(1, round(assigned_hrs / 1.5))

                row['flight_hours']  = str(assigned_hrs)
                row['flight_cycles'] = str(assigned_cyc)
                fixed_flying += 1

    print(f"\nFixes applied:")
    print(f"  Non-FLYING rows zeroed out  : {fixed_zero}")
    print(f"  FLYING rows assigned hours  : {fixed_flying}")
    print(f"  Total rows fixed            : {fixed_zero + fixed_flying}")

    # -----------------------------------------------------------------------
    # Write output
    # -----------------------------------------------------------------------
    with open(STATUS_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nfact_aircraft_daily_status written: {len(rows)} rows")

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------
    print("\n=== VALIDATION ===")
    violations = 0
    flying_zero = 0
    non_flying_nonzero = 0
    for row in rows:
        hrs = float(row['flight_hours'] or 0)
        cyc = int(float(row['flight_cycles'] or 0))
        s   = row['status']
        if s == 'FLYING' and (hrs == 0 or cyc == 0):
            flying_zero += 1
            violations += 1
        elif s != 'FLYING' and (hrs > 0 or cyc > 0):
            non_flying_nonzero += 1
            violations += 1

    print(f"  FLYING rows with 0 hours/cycles      : {flying_zero}  (must be 0)")
    print(f"  Non-FLYING rows with hours/cycles > 0: {non_flying_nonzero}  (must be 0)")
    print(f"  Total violations remaining           : {violations}")
    if violations == 0:
        print("  ✓ All rows pass data integrity check")


if __name__ == '__main__':
    main()

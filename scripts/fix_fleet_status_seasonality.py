"""
fix_fleet_status_seasonality.py
================================
Fixes fact_aircraft_daily_status to show realistic seasonal patterns:

1. FLYING/AVAILABLE seasonality:
     Summer  (Jun–Aug) : FLYING ~90%,  AVAILABLE ~5%
     Spring  (Mar–May) : FLYING ~85%,  AVAILABLE ~8%
     Fall    (Sep–Nov) : FLYING ~84%,  AVAILABLE ~8%
     Winter  (Dec–Feb) : FLYING ~78%,  AVAILABLE ~14%

2. IN_MAINTENANCE boost in March, May, October:
     March/October (heavy inspection): ~14% IN_MAINTENANCE
     May (AOG-heavy month):            ~12% IN_MAINTENANCE

3. Normalize all dates to YYYY-MM-DD format.

Rules preserved throughout:
  - AOG days in March(6), May(8), October(6) per year — never touched
  - Fleet growth (46→62 aircraft) naturally reflected in row counts
  - Total rows unchanged (63,080)
"""

import csv
import os
import random
from datetime import datetime
from collections import defaultdict

random.seed(42)

DATA_DIR    = os.path.join(os.path.dirname(__file__), '..', 'output', 'analytics', 'data')
STATUS_FILE = os.path.join(DATA_DIR, 'fact_aircraft_daily_status.csv')

# -----------------------------------------------------------------------
# Seasonal FLYING % targets  (IN_MAINTENANCE and AOG absorb the rest)
# AVAILABLE = 100% - FLYING% - MAINT% - AOG%
# -----------------------------------------------------------------------
# month → (target_flying_pct, target_maint_pct)
MONTH_TARGETS = {
    1:  (0.78, 0.080),   # Winter
    2:  (0.78, 0.080),   # Winter
    3:  (0.84, 0.140),   # Spring + heavy inspection
    4:  (0.85, 0.080),   # Spring
    5:  (0.85, 0.120),   # Spring + AOG month
    6:  (0.90, 0.070),   # Summer peak
    7:  (0.90, 0.070),   # Summer peak
    8:  (0.90, 0.075),   # Summer peak
    9:  (0.85, 0.080),   # Fall
    10: (0.84, 0.140),   # Fall + heavy inspection
    11: (0.82, 0.090),   # Fall into Winter
    12: (0.78, 0.080),   # Winter
}


def parse_date(s):
    for fmt in ('%m/%d/%y', '%Y-%m-%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(s, fmt)
        except:
            pass
    return None


def main():
    print("Loading fact_aircraft_daily_status...")
    rows = []
    fieldnames = None
    with open(STATUS_FILE) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    print(f"  {len(rows)} rows loaded.")

    # -----------------------------------------------------------------------
    # Step 1: Normalize all dates to YYYY-MM-DD
    # -----------------------------------------------------------------------
    print("\nStep 1 — Normalizing date format to YYYY-MM-DD...")
    date_fixed = 0
    for row in rows:
        d = parse_date(row['date'])
        if d:
            norm = d.strftime('%Y-%m-%d')
            if norm != row['date']:
                row['date'] = norm
                date_fixed += 1
    print(f"  {date_fixed} dates reformatted.")

    # -----------------------------------------------------------------------
    # Build monthly index after date normalization
    # -----------------------------------------------------------------------
    # month_rows[(year, month)] = list of row indices grouped by current status
    month_idx = defaultdict(lambda: defaultdict(list))  # (yr,mo) → status → [indices]

    for i, row in enumerate(rows):
        d = parse_date(row['date'])
        if not d:
            continue
        month_idx[(d.year, d.month)][row['status']].append(i)

    # -----------------------------------------------------------------------
    # Step 2 & 3: Apply seasonal FLYING/AVAILABLE/MAINTENANCE targets
    # Preserve ALL AOG rows exactly as-is
    # -----------------------------------------------------------------------
    print("\nStep 2 — Applying seasonal status targets...")

    for (yr, mo), status_map in sorted(month_idx.items()):
        fly_target, maint_target = MONTH_TARGETS[mo]

        aog_rows   = status_map.get('AOG', [])
        fly_rows   = status_map.get('FLYING', [])
        avail_rows = status_map.get('AVAILABLE', [])
        maint_rows = status_map.get('IN_MAINTENANCE', [])

        total = len(aog_rows) + len(fly_rows) + len(avail_rows) + len(maint_rows)
        if total == 0:
            continue

        aog_count   = len(aog_rows)
        fly_target_n  = round((total - aog_count) * fly_target / (fly_target + (1 - fly_target)))
        maint_target_n = round((total - aog_count) * maint_target)
        # clamp so we don't exceed non-AOG rows
        non_aog = total - aog_count
        maint_target_n = min(maint_target_n, non_aog)
        fly_target_n   = min(fly_target_n, non_aog - maint_target_n)
        avail_target_n = non_aog - fly_target_n - maint_target_n

        # Pool of non-AOG rows (can be freely reassigned)
        non_aog_pool = fly_rows + avail_rows + maint_rows
        random.shuffle(non_aog_pool)

        # Assign in order: FLYING, IN_MAINTENANCE, AVAILABLE
        for i, idx in enumerate(non_aog_pool):
            if i < fly_target_n:
                rows[idx]['status'] = 'FLYING'
                rows[idx]['maintenance_type'] = ''
            elif i < fly_target_n + maint_target_n:
                rows[idx]['status'] = 'IN_MAINTENANCE'
                # Assign maintenance_type based on month
                if mo in (3, 10):
                    rows[idx]['maintenance_type'] = random.choice(
                        ['INSPECTION', 'INSPECTION', 'INSPECTION', 'COMPONENT_REPLACEMENT', 'LINE_MAINTENANCE']
                    )
                elif mo == 5:
                    rows[idx]['maintenance_type'] = random.choice(
                        ['INSPECTION', 'LINE_MAINTENANCE', 'COMPONENT_REPLACEMENT', 'TROUBLESHOOTING']
                    )
                else:
                    rows[idx]['maintenance_type'] = random.choice(
                        ['INSPECTION', 'LINE_MAINTENANCE', 'TROUBLESHOOTING']
                    )
            else:
                rows[idx]['status'] = 'AVAILABLE'
                rows[idx]['maintenance_type'] = ''

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
    monthly = defaultdict(lambda: defaultdict(int))
    for row in rows:
        d = parse_date(row['date'])
        if d:
            m = f"{d.year}-{d.month:02d}"
            monthly[m][row['status']] += 1
            monthly[m]['TOTAL'] += 1

    print(f"\n{'Month':<10} {'FLY%':>7} {'AVAIL%':>8} {'MAINT%':>8} {'AOG%':>7} {'Total':>7}")
    for yr in [2023, 2024, 2025]:
        print(f"--- {yr} ---")
        for mo in range(1, 13):
            m = f"{yr}-{mo:02d}"
            d = monthly[m]
            if d['TOTAL'] == 0:
                continue
            t = d['TOTAL']
            fly   = d['FLYING'] / t * 100
            av    = d['AVAILABLE'] / t * 100
            mn    = d['IN_MAINTENANCE'] / t * 100
            aog   = d['AOG'] / t * 100
            # Flag if seasonality looks right
            season_ok = ''
            if mo in (6, 7, 8) and fly >= 88:    season_ok = '← summer ✓'
            if mo in (12, 1, 2) and fly <= 80:   season_ok = '← winter ✓'
            if mo in (3, 10) and mn >= 12:        season_ok = '← heavy maint ✓'
            print(f"{m:<10} {fly:>6.1f}% {av:>7.1f}% {mn:>7.1f}% {aog:>6.2f}% {t:>7}  {season_ok}")

    # AOG check
    print("\nAOG days per target month (must be 6/8/6):")
    for yr in [2023, 2024, 2025]:
        for mo_s, exp in [('03', 6), ('05', 8), ('10', 6)]:
            m = f"{yr}-{mo_s}"
            print(f"  {m}: {monthly[m]['AOG']} AOG days (expected {exp}) {'✓' if monthly[m]['AOG'] == exp else '← CHECK'}")

    # Date format check
    sample_dates = [rows[0]['date'], rows[1000]['date'], rows[50000]['date']]
    print(f"\nSample dates (must be YYYY-MM-DD): {sample_dates}")


if __name__ == '__main__':
    main()

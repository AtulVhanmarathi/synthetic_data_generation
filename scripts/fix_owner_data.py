"""
fix_owner_data.py
=================
Fixes the following issues in dim_owner.csv and fact_flight.csv:

1. dim_owner — duplicate owner_type columns (x4) → deduplicate to single column
2. dim_owner — share_type '1/32' does not exist in PlaneSense program → reclassify to 'Share_1/16'
3. dim_owner — share_type strings ('1/4','1/8','1/16') parsed as dates by Excel/Power BI
               → rename to 'Share_1/4', 'Share_1/8', 'Share_1/16', 'Cobalt'
4. dim_owner — Cobalt pass holders incorrectly have fractional share_type and hours
               → set share_type='Cobalt', annual_hours_contracted=25
5. fact_flight — duplicate season and day_of_week columns (x4) → deduplicate to single each
"""

import csv
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'output', 'analytics', 'data')

SHARE_TYPE_MAP = {
    '1/4':  'Share_1/4',
    '1/8':  'Share_1/8',
    '1/16': 'Share_1/16',
    '1/32': 'Share_1/16',   # 1/32 doesn't exist → reclassify to minimum fractional
}

# ---------------------------------------------------------------------------
# Fix dim_owner.csv
# ---------------------------------------------------------------------------
def fix_dim_owner():
    path = os.path.join(DATA_DIR, 'dim_owner.csv')
    rows = []
    raw_fieldnames = None

    with open(path) as f:
        reader = csv.DictReader(f)
        raw_fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    # Deduplicate column names — keep first occurrence only
    seen = []
    for col in raw_fieldnames:
        if col not in seen:
            seen.append(col)
    clean_fieldnames = seen
    print(f"dim_owner: removed {len(raw_fieldnames) - len(clean_fieldnames)} duplicate column(s)")

    # Add 'owner_type' if not present (should already be there from regeneration script)
    if 'owner_type' not in clean_fieldnames:
        clean_fieldnames.append('owner_type')

    fixed = 0
    cobalt_fixed = 0
    share_reclassified = 0

    for row in rows:
        is_cobalt = row.get('cobalt_pass_holder', '0') == '1'

        if is_cobalt:
            # Cobalt is entry program — no fractional ownership
            row['share_type']               = 'Cobalt'
            row['annual_hours_contracted']   = '25'
            cobalt_fixed += 1
        else:
            old = row.get('share_type', '')
            new = SHARE_TYPE_MAP.get(old, old)
            if new != old:
                share_reclassified += 1
            row['share_type'] = new

        fixed += 1

    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=clean_fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    print(f"dim_owner: {cobalt_fixed} Cobalt holders fixed (share_type=Cobalt, hours=25)")
    print(f"dim_owner: {share_reclassified} share_type values reclassified/renamed")
    print(f"dim_owner: {fixed} rows written to {path}")
    print(f"dim_owner: final columns: {clean_fieldnames}")


# ---------------------------------------------------------------------------
# Fix fact_flight.csv — deduplicate season and day_of_week columns
# ---------------------------------------------------------------------------
def fix_fact_flight():
    path = os.path.join(DATA_DIR, 'fact_flight.csv')
    rows = []
    raw_fieldnames = None

    print("\nLoading fact_flight (this may take a moment)...")
    with open(path) as f:
        reader = csv.DictReader(f)
        raw_fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    # Deduplicate columns
    seen = []
    for col in raw_fieldnames:
        if col not in seen:
            seen.append(col)
    clean_fieldnames = seen
    removed = len(raw_fieldnames) - len(clean_fieldnames)
    print(f"fact_flight: removed {removed} duplicate column(s)")
    print(f"fact_flight: final columns: {clean_fieldnames}")

    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=clean_fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    print(f"fact_flight: {len(rows)} rows written to {path}")


# ---------------------------------------------------------------------------
# Validate results
# ---------------------------------------------------------------------------
def validate():
    print("\n=== Validation ===")

    # dim_owner
    with open(os.path.join(DATA_DIR, 'dim_owner.csv')) as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        rows = list(reader)

    from collections import Counter
    print(f"\ndim_owner columns ({len(cols)}): {cols}")
    print("share_type distribution:", dict(Counter(r['share_type'] for r in rows)))
    print("annual_hours distribution:", dict(Counter(r['annual_hours_contracted'] for r in rows)))

    cobalt_hrs = Counter(r['annual_hours_contracted'] for r in rows if r['cobalt_pass_holder'] == '1')
    cobalt_share = Counter(r['share_type'] for r in rows if r['cobalt_pass_holder'] == '1')
    print(f"Cobalt holders hours: {dict(cobalt_hrs)} (all must be 25)")
    print(f"Cobalt holders share_type: {dict(cobalt_share)} (all must be 'Cobalt')")

    invalid_share = [r for r in rows if r['share_type'] in ('1/4','1/8','1/16','1/32')]
    print(f"Rows with old share_type format (must be 0): {len(invalid_share)}")

    owner_type_col_count = cols.count('owner_type')
    print(f"owner_type column count (must be 1): {owner_type_col_count}")

    # fact_flight
    with open(os.path.join(DATA_DIR, 'fact_flight.csv')) as f:
        ff_cols = csv.DictReader(f).fieldnames
    season_count   = ff_cols.count('season')
    dow_count      = ff_cols.count('day_of_week')
    print(f"\nfact_flight season column count (must be 1): {season_count}")
    print(f"fact_flight day_of_week column count (must be 1): {dow_count}")
    print(f"fact_flight total columns: {len(ff_cols)}")


if __name__ == '__main__':
    fix_dim_owner()
    fix_fact_flight()
    validate()

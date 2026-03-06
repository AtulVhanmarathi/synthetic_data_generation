"""
fix_aog_costs.py
================
Fixes AOG-related cost realism in fact_maintenance_detail.csv:

1. BOOST top 3 AOG-heavy months (2024-05 x12 days, 2023-05 x6 days, 2023-06 x5 days):
   - Parts → 1.40x labor (same as March/October seasonal boosts)
   - Labor → 1.25x (AOG events require emergency overtime / expedited work)
   - Combined effect: both cost lines elevated, reflecting emergency urgency

2. FIX AOG_REPAIR line items that have PARTS = 0.0:
   - Every AOG_REPAIR action should have a corresponding parts replacement entry
   - New PARTS rows are inserted using realistic emergency part costs
   - Part descriptions reference the JASC/ATA system being repaired
   - unit_cost reflects emergency procurement premium (~2x standard part price)

3. March/October seasonal boosts from fix_maintenance_cost_ratio.py are preserved.
"""

import csv
import os
import random

random.seed(99)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'output', 'analytics', 'data')
FILE     = os.path.join(DATA_DIR, 'fact_maintenance_detail.csv')

# Top 3 AOG-heavy months to boost
AOG_BOOST_MONTHS = {
    '2024-05': 12,   # 12 AOG days — worst month
    '2023-05':  6,   # 6 AOG days
    '2023-06':  5,   # 5 AOG days
}

# Parts/labor targets for AOG boost months
PARTS_TO_LABOR_TARGET = 1.40
LABOR_MULTIPLIER      = 1.25   # emergency overtime uplift

# Realistic AOG emergency part costs by JASC system (emergency procurement premium)
AOG_PART_COSTS = {
    '2700.0': ('Brake Assembly - Emergency Replace',      4800,  1),
    '7200.0': ('Engine Fuel Control Unit - AOG Replace',  28500, 1),
    '2900.0': ('Hydraulic Actuator - AOG Replace',        6200,  1),
    '2400.0': ('Electrical Relay Pack - AOG Replace',     3400,  2),
    '3200.0': ('Main Gear Strut Seal Kit - AOG Replace',  2100,  1),
    '7100.0': ('Turbine Inlet Temp Sensor - AOG Replace', 5600,  1),
    '2500.0': ('Avionics LRU - AOG Replace',              12800, 1),
    '2800.0': ('Fuel Boost Pump - AOG Replace',           3900,  1),
}

DEFAULT_AOG_PART = ('Unscheduled Component Replace - AOG', 4500, 1)


def compute_monthly(rows):
    from collections import defaultdict
    monthly = defaultdict(lambda: {'LABOR': 0.0, 'PARTS': 0.0})
    for row in rows:
        m = row['date'][:7]
        try:
            monthly[m][row['cost_category']] += float(row['extended_cost'] or 0)
        except:
            pass
    return monthly


def apply_labor_multiplier(rows, months, multiplier):
    changed = 0
    for row in rows:
        if row['date'][:7] in months and row['cost_category'] == 'LABOR':
            try:
                uc = float(row['unit_cost'] or 0)
                ec = float(row['extended_cost'] or 0)
                row['unit_cost']     = f"{uc * multiplier:.1f}"
                row['extended_cost'] = f"{ec * multiplier:.1f}"
                changed += 1
            except:
                pass
    return changed


def apply_parts_multiplier(rows, month, target_ratio):
    """Scale PARTS rows in a single month to hit target_ratio × labor."""
    labor = sum(float(r['extended_cost'] or 0) for r in rows
                if r['date'][:7] == month and r['cost_category'] == 'LABOR')
    parts = sum(float(r['extended_cost'] or 0) for r in rows
                if r['date'][:7] == month and r['cost_category'] == 'PARTS')
    target = labor * target_ratio
    mult = target / parts if parts else 1.0
    changed = 0
    for row in rows:
        if row['date'][:7] == month and row['cost_category'] == 'PARTS':
            try:
                uc = float(row['unit_cost'] or 0)
                ec = float(row['extended_cost'] or 0)
                row['unit_cost']     = f"{uc * mult:.1f}"
                row['extended_cost'] = f"{ec * mult:.1f}"
                changed += 1
            except:
                pass
    return changed, mult, labor, parts, labor * target_ratio


def main():
    print("Loading fact_maintenance_detail...")
    rows = []
    fieldnames = None
    with open(FILE) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    print(f"  {len(rows)} rows loaded.")

    # -----------------------------------------------------------------------
    # Step 1: Boost labor in AOG-heavy months (emergency overtime)
    # -----------------------------------------------------------------------
    print("\nStep 1 — Boosting LABOR in AOG-heavy months (x1.25):")
    for month in sorted(AOG_BOOST_MONTHS):
        changed = apply_labor_multiplier(rows, {month}, LABOR_MULTIPLIER)
        labor = sum(float(r['extended_cost'] or 0) for r in rows
                    if r['date'][:7] == month and r['cost_category'] == 'LABOR')
        print(f"  {month} ({AOG_BOOST_MONTHS[month]} AOG days): {changed} LABOR rows updated → labor total now {labor:,.0f}")

    # -----------------------------------------------------------------------
    # Step 2: Boost parts in AOG-heavy months to 1.40x of (boosted) labor
    # -----------------------------------------------------------------------
    print("\nStep 2 — Boosting PARTS in AOG-heavy months to 1.40x labor:")
    for month in sorted(AOG_BOOST_MONTHS):
        changed, mult, labor, parts_before, parts_target = apply_parts_multiplier(
            rows, month, PARTS_TO_LABOR_TARGET
        )
        parts_after = sum(float(r['extended_cost'] or 0) for r in rows
                          if r['date'][:7] == month and r['cost_category'] == 'PARTS')
        print(f"  {month}: parts {parts_before:,.0f} → {parts_after:,.0f}  "
              f"labor {labor:,.0f}  ratio {parts_after/labor:.2f}x  (mult {mult:.3f}x, {changed} rows)")

    # -----------------------------------------------------------------------
    # Step 3: Fix AOG_REPAIR rows with PARTS = 0 — add emergency parts entries
    # -----------------------------------------------------------------------
    print("\nStep 3 — Adding PARTS entries for AOG_REPAIR line items:")

    # Find all AOG_REPAIR LABOR rows that have no corresponding PARTS row
    # Group by maintenance_job_id to find jobs missing parts
    from collections import defaultdict
    job_categories = defaultdict(set)
    job_meta = {}
    for row in rows:
        jid = row['maintenance_job_id']
        job_categories[jid].add(row['cost_category'])
        if row['cost_category'] == 'LABOR' and 'AOG_REPAIR' in row.get('part_description', '').upper():
            job_meta[jid] = row  # store reference row for this job

    # Find highest existing detail_id to continue numbering
    max_id = 0
    for row in rows:
        try:
            n = int(row['detail_id'].replace('MD-', ''))
            if n > max_id:
                max_id = n
        except:
            pass

    new_rows = []
    aog_jobs_fixed = 0

    for jid, ref_row in job_meta.items():
        if 'PARTS' not in job_categories[jid]:
            # This AOG job has no parts — add one
            jasc = ref_row.get('jasc_ata_code', '').strip()
            if jasc in AOG_PART_COSTS:
                desc, unit_price, qty = AOG_PART_COSTS[jasc]
            else:
                desc, unit_price, qty = DEFAULT_AOG_PART
                # Pick a random realistic AOG system
                desc, unit_price, qty = random.choice(list(AOG_PART_COSTS.values()))

            # Add emergency procurement premium (1.8x–2.4x standard price)
            premium = round(random.uniform(1.8, 2.4), 2)
            emergency_unit_cost = round(unit_price * premium, 1)
            extended = round(emergency_unit_cost * qty, 1)

            max_id += 1
            new_row = {
                'detail_id':           f'MD-{max_id:07d}',
                'maintenance_job_id':  jid,
                'date':                ref_row['date'],
                'aircraft_id':         ref_row['aircraft_id'],
                'facility_id':         ref_row['facility_id'],
                'action_type':         'REPLACE',
                'cost_category':       'PARTS',
                'jasc_ata_code':       ref_row.get('jasc_ata_code', ''),
                'part_description':    desc,
                'uom':                 'Each',
                'quantity':            str(qty),
                'unit_cost':           str(emergency_unit_cost),
                'extended_cost':       str(extended),
            }
            new_rows.append(new_row)
            aog_jobs_fixed += 1

    rows.extend(new_rows)
    print(f"  Added {len(new_rows)} PARTS rows for {aog_jobs_fixed} AOG_REPAIR jobs")
    print(f"  Total rows now: {len(rows)}")

    # -----------------------------------------------------------------------
    # Write updated file
    # -----------------------------------------------------------------------
    rows.sort(key=lambda r: r['detail_id'])
    with open(FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWritten: {len(rows)} rows to {FILE}")

    # -----------------------------------------------------------------------
    # Final validation
    # -----------------------------------------------------------------------
    monthly = compute_monthly(rows)
    all_months = sorted(monthly.keys())

    print(f"\n{'Month':<10} {'AOG days':>9} {'Labor':>12} {'Parts':>12} {'Ratio':>8} {'Flag':>14}")

    aog_days_map = {
        '2023-01':2,'2023-04':4,'2023-05':6,'2023-06':5,'2023-08':2,'2023-10':3,
        '2024-04':5,'2024-05':12,'2024-09':3,'2024-10':2,'2024-11':3,
        '2025-01':2,'2025-02':2,'2025-03':3,'2025-04':1,'2025-05':1,
        '2025-08':2,'2025-10':3,'2025-11':2
    }
    boost_months = {'2023-03','2024-03','2025-03','2023-10','2024-10','2025-10'}
    aog_boost    = set(AOG_BOOST_MONTHS.keys())

    for m in all_months:
        l = monthly[m]['LABOR']; p = monthly[m]['PARTS']
        ratio = p/l if l else 0
        flag = 'parts>labor ✓' if p > l else ''
        tag  = ''
        if m in boost_months: tag = ' [SEASONAL BOOST]'
        if m in aog_boost:    tag = ' [AOG BOOST]'
        aog_d = aog_days_map.get(m, 0)
        print(f"{m:<10} {aog_d:>9} {l:>12,.0f} {p:>12,.0f} {ratio:>7.2f}x {flag:>14}{tag}")


if __name__ == '__main__':
    main()

"""
consolidate_aog.py
==================
Consolidates AOG events across all years to only March, May, and October.

Changes to fact_aircraft_daily_status:
  1. Remove AOG from non-target months → change to AVAILABLE
  2. Boost AOG days in target months to consistent levels:
       March  → 6 AOG days per year
       May    → 8 AOG days per year
       October→ 6 AOG days per year

Changes to fact_maintenance_detail:
  3. Boost 2025-05 costs to match 2023-05 and 2024-05 pattern
     (Parts = 1.40x of boosted labor, labor × 1.25)
"""

import csv
import os
import random
from datetime import datetime
from collections import defaultdict

random.seed(77)

DATA_DIR  = os.path.join(os.path.dirname(__file__), '..', 'output', 'analytics', 'data')
STATUS_FILE = os.path.join(DATA_DIR, 'fact_aircraft_daily_status.csv')
DETAIL_FILE = os.path.join(DATA_DIR, 'fact_maintenance_detail.csv')

# Target AOG days per month per year
AOG_TARGETS = {3: 6, 5: 8, 10: 6}   # month_number → target days


def parse_date(s):
    for fmt in ('%m/%d/%y', '%Y-%m-%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(s, fmt)
        except:
            pass
    return None


def main():
    # -----------------------------------------------------------------------
    # Load fact_aircraft_daily_status
    # -----------------------------------------------------------------------
    print("Loading fact_aircraft_daily_status...")
    rows = []
    fieldnames = None
    with open(STATUS_FILE) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    print(f"  {len(rows)} rows loaded.")

    # Index rows by (year, month, status)
    month_status_idx = defaultdict(list)   # (year, month, status) → [row indices]
    month_aog_idx    = defaultdict(list)   # (year, month) → [row indices of AOG]
    for i, row in enumerate(rows):
        d = parse_date(row['date'])
        if not d:
            continue
        key     = (d.year, d.month)
        key_sta = (d.year, d.month, row['status'])
        month_status_idx[key_sta].append(i)
        if row['status'] == 'AOG':
            month_aog_idx[key].append(i)

    years = [2023, 2024, 2025]
    target_months = set(AOG_TARGETS.keys())

    removed = 0
    added   = 0

    # -----------------------------------------------------------------------
    # Step 1: Remove AOG from non-target months → AVAILABLE
    # -----------------------------------------------------------------------
    print("\nStep 1 — Removing AOG from non-target months:")
    for (yr, mo), idxs in sorted(month_aog_idx.items()):
        if mo not in target_months:
            for i in idxs:
                rows[i]['status'] = 'AVAILABLE'
                rows[i]['maintenance_type'] = ''
                removed += len(idxs)
            print(f"  {yr}-{mo:02d}: {len(idxs)} AOG → AVAILABLE")

    # -----------------------------------------------------------------------
    # Step 2: Boost AOG days in target months to desired levels
    # -----------------------------------------------------------------------
    print("\nStep 2 — Setting AOG days in March / May / October:")
    for yr in years:
        for mo, target in sorted(AOG_TARGETS.items()):
            key = (yr, mo)
            current_aog = [i for i in month_aog_idx[key]
                           if rows[i]['status'] == 'AOG']   # may have been modified above
            current_count = len(current_aog)
            need = target - current_count

            if need > 0:
                # Pick AVAILABLE rows to convert to AOG
                avail_pool = [i for i in month_status_idx[(yr, mo, 'AVAILABLE')]
                              if rows[i]['status'] == 'AVAILABLE']
                random.shuffle(avail_pool)
                to_convert = avail_pool[:need]
                for i in to_convert:
                    rows[i]['status'] = 'AOG'
                    rows[i]['maintenance_type'] = 'AOG_REPAIR'
                    added += 1
                actual = current_count + len(to_convert)
                print(f"  {yr}-{mo:02d}: {current_count} → {actual} AOG days (+{len(to_convert)} converted from AVAILABLE)")
            elif need < 0:
                # Too many AOG days — trim back to target, convert excess to AVAILABLE
                trim = current_aog[target:]   # keep first `target` rows as AOG
                for i in trim:
                    rows[i]['status'] = 'AVAILABLE'
                    rows[i]['maintenance_type'] = ''
                print(f"  {yr}-{mo:02d}: {current_count} → {target} AOG days (-{len(trim)} trimmed to AVAILABLE)")
            else:
                print(f"  {yr}-{mo:02d}: {current_count} AOG days — already at target, no change")

    # -----------------------------------------------------------------------
    # Write fact_aircraft_daily_status
    # -----------------------------------------------------------------------
    with open(STATUS_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nfact_aircraft_daily_status written: {len(rows)} rows")
    print(f"  Removed {removed} non-target AOG entries, added {added} new AOG entries")

    # -----------------------------------------------------------------------
    # Step 3: Boost 2025-05 maintenance costs (new AOG month, currently flat)
    # -----------------------------------------------------------------------
    print("\nStep 3 — Boosting 2025-05 maintenance costs:")
    detail_rows = []
    detail_fields = None
    with open(DETAIL_FILE) as f:
        reader = csv.DictReader(f)
        detail_fields = reader.fieldnames
        for row in reader:
            detail_rows.append(row)

    LABOR_MULT      = 1.25
    PARTS_TO_LABOR  = 1.40

    # Boost labor first
    labor_changed = 0
    for row in detail_rows:
        if row['date'][:7] == '2025-05' and row['cost_category'] == 'LABOR':
            try:
                row['unit_cost']     = f"{float(row['unit_cost'] or 0) * LABOR_MULT:.1f}"
                row['extended_cost'] = f"{float(row['extended_cost'] or 0) * LABOR_MULT:.1f}"
                labor_changed += 1
            except: pass

    labor_total = sum(float(r['extended_cost'] or 0) for r in detail_rows
                      if r['date'][:7] == '2025-05' and r['cost_category'] == 'LABOR')
    parts_total = sum(float(r['extended_cost'] or 0) for r in detail_rows
                      if r['date'][:7] == '2025-05' and r['cost_category'] == 'PARTS')
    target_parts = labor_total * PARTS_TO_LABOR
    parts_mult   = target_parts / parts_total if parts_total else 1.0

    parts_changed = 0
    for row in detail_rows:
        if row['date'][:7] == '2025-05' and row['cost_category'] == 'PARTS':
            try:
                row['unit_cost']     = f"{float(row['unit_cost'] or 0) * parts_mult:.1f}"
                row['extended_cost'] = f"{float(row['extended_cost'] or 0) * parts_mult:.1f}"
                parts_changed += 1
            except: pass

    parts_after = sum(float(r['extended_cost'] or 0) for r in detail_rows
                      if r['date'][:7] == '2025-05' and r['cost_category'] == 'PARTS')
    print(f"  Labor: {labor_changed} rows × {LABOR_MULT}x → {labor_total:,.0f}")
    print(f"  Parts: {parts_changed} rows × {parts_mult:.3f}x → {parts_after:,.0f}")
    print(f"  Ratio: {parts_after/labor_total:.2f}x (target 1.40x)")

    with open(DETAIL_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(detail_rows)
    print(f"\nfact_maintenance_detail written: {len(detail_rows)} rows")

    # -----------------------------------------------------------------------
    # Final validation
    # -----------------------------------------------------------------------
    print("\n=== VALIDATION ===")
    final_aog = defaultdict(int)
    for row in rows:
        if row['status'] == 'AOG':
            d = parse_date(row['date'])
            if d:
                final_aog[f"{d.year}-{d.month:02d}"] += 1

    print(f"\n{'Month':<10} {'AOG days':>9} {'Expected':>9} {'OK':>4}")
    for yr in years:
        for mo in range(1, 13):
            m = f"{yr}-{mo:02d}"
            aog_d = final_aog.get(m, 0)
            exp = AOG_TARGETS.get(mo, 0)
            ok = '✓' if aog_d == exp else f'← got {aog_d}'
            if aog_d > 0 or mo in AOG_TARGETS:
                print(f"  {m:<10} {aog_d:>9} {exp:>9} {ok:>4}")

    # Cost validation for AOG months
    print("\nMaintenance cost ratios — AOG months:")
    monthly_cost = defaultdict(lambda: {'LABOR': 0.0, 'PARTS': 0.0})
    for row in detail_rows:
        m = row['date'][:7]
        try: monthly_cost[m][row['cost_category']] += float(row['extended_cost'] or 0)
        except: pass

    aog_months_check = [f"{yr}-{mo:02d}" for yr in years for mo in sorted(AOG_TARGETS.keys())]
    for m in sorted(set(aog_months_check)):
        l = monthly_cost[m]['LABOR']; p = monthly_cost[m]['PARTS']
        ratio = p/l if l else 0
        flag = 'parts>labor ✓' if p > l else '← NEEDS FIX'
        print(f"  {m}: Labor={l:,.0f}  Parts={p:,.0f}  ratio={ratio:.2f}x  {flag}")


if __name__ == '__main__':
    main()

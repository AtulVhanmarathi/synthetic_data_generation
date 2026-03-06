"""
fix_maintenance_cost_ratio.py
==============================
Adjusts parts vs labor cost ratios in fact_maintenance_detail.csv so that:

  BOOST months (March + October, all 3 years):
    Parts cost > Labor cost (~1.4x) — reflects heavy pre-season inspection,
    component replacements (engine, landing gear, avionics) driving parts spend

  REVERT months (Jan-2023, Jul-2023, Dec-2023):
    Parts cost < Labor cost (~0.70x) — removes the 3 accidental outlier months
    so only March and October show the parts-dominant pattern consistently

Only fact_maintenance_detail[unit_cost] and [extended_cost] are modified.
quantity, action_type, jasc_ata_code, part_description all remain unchanged.
"""

import csv
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'output', 'analytics', 'data')
FILE     = os.path.join(DATA_DIR, 'fact_maintenance_detail.csv')

BOOST_MONTHS  = {'2023-03', '2024-03', '2025-03', '2023-10', '2024-10', '2025-10'}
REVERT_MONTHS = {'2023-01', '2023-07', '2023-12'}

# Target ratios: parts_total / labor_total after adjustment
BOOST_TARGET_RATIO  = 1.40   # parts should be 1.4x labor
REVERT_TARGET_RATIO = 0.70   # parts should be 0.7x labor


def compute_totals(rows, months):
    parts = sum(float(r['extended_cost'] or 0) for r in rows
                if r['date'][:7] in months and r['cost_category'] == 'PARTS')
    labor = sum(float(r['extended_cost'] or 0) for r in rows
                if r['date'][:7] in months and r['cost_category'] == 'LABOR')
    return parts, labor


def apply_multiplier(rows, months, multiplier):
    """Scale unit_cost and extended_cost for all PARTS rows in given months."""
    changed = 0
    for row in rows:
        if row['date'][:7] in months and row['cost_category'] == 'PARTS':
            try:
                uc = float(row['unit_cost'] or 0)
                ec = float(row['extended_cost'] or 0)
                row['unit_cost']    = f"{uc * multiplier:.1f}"
                row['extended_cost']= f"{ec * multiplier:.1f}"
                changed += 1
            except ValueError:
                pass
    return changed


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

    # ---- Boost: March + October — per-month multipliers ----
    print(f"\nBOOST (March + October all years) — per-month:")
    total_changed = 0
    for month in sorted(BOOST_MONTHS):
        p, l = compute_totals(rows, {month})
        target_p = l * BOOST_TARGET_RATIO
        mult = target_p / p if p else 1.0
        changed = apply_multiplier(rows, {month}, mult)
        p_after, _ = compute_totals(rows, {month})
        total_changed += changed
        print(f"  {month}: parts {p:,.0f} → {p_after:,.0f}  labor {l:,.0f}  ratio {p_after/l:.2f}x  (mult {mult:.3f}x, {changed} rows)")
    print(f"  Total PARTS rows changed: {total_changed}")

    # ---- Revert: Jan-2023, Jul-2023, Dec-2023 — per-month multipliers ----
    print(f"\nREVERT (Jan/Jul/Dec 2023) — per-month:")
    total_changed_r = 0
    for month in sorted(REVERT_MONTHS):
        p, l = compute_totals(rows, {month})
        target_p = l * REVERT_TARGET_RATIO
        mult = target_p / p if p else 1.0
        changed_r = apply_multiplier(rows, {month}, mult)
        p_after, _ = compute_totals(rows, {month})
        total_changed_r += changed_r
        print(f"  {month}: parts {p:,.0f} → {p_after:,.0f}  labor {l:,.0f}  ratio {p_after/l:.2f}x  (mult {mult:.3f}x, {changed_r} rows)")
    print(f"  Total PARTS rows changed: {total_changed_r}")

    # ---- Write updated file ----
    with open(FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWritten: {len(rows)} rows to {FILE}")

    # ---- Final validation: print all 36 months ----
    from collections import defaultdict
    monthly = defaultdict(lambda: {'LABOR': 0.0, 'PARTS': 0.0})
    for row in rows:
        m = row['date'][:7]
        try: monthly[m][row['cost_category']] += float(row['extended_cost'] or 0)
        except: pass

    print(f"\n{'Month':<10} {'Labor':>12} {'Parts':>12} {'Ratio':>8} {'Parts>Labor':>12}")
    for m in sorted(monthly.keys()):
        l = monthly[m]['LABOR']; p = monthly[m]['PARTS']
        ratio = p/l if l else 0
        flag = 'YES ✓' if p > l else ''
        marker = ' ← BOOST' if m[5:7] in ('03','10') else (' ← REVERTED' if m in REVERT_MONTHS else '')
        print(f"{m:<10} {l:>12,.0f} {p:>12,.0f} {ratio:>7.2f}x {flag:>12}{marker}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
build_data.py
=============
Single entry point to regenerate all PlaneSense analytics data from scratch.

Runs 9 scripts in the correct dependency order:

  Stage 1 — Base generation
    1. generate_analytics_data.py          Base 12-CSV star schema

  Stage 2 — Route & owner fixes (coupled pair)
    2. scripts/regenerate_routes_v2.py     Weighted route distribution
    3. scripts/fix_owner_data.py           Owner data cleanup after route regen

  Stage 3 — Maintenance fixes (AOG must precede cost fixes)
    4. scripts/consolidate_aog.py          AOG to Mar/May/Oct only
    5. scripts/fix_aog_costs.py            Emergency AOG part costs
    6. scripts/fix_maintenance_cost_ratio.py  Parts/labor ratio corrections

  Stage 4 — Daily status (strictly ordered, each builds on previous)
    7. scripts/fix_fleet_status_seasonality.py  Initial seasonal FLYING% pass
    8. scripts/fix_daily_status_hours.py        Hours/cycles integrity
    9. scripts/rebalance_daily_status.py        FLYING<->AVAILABLE rebalance + holiday spike

Output: output/analytics/data/  (12 CSVs, gitignored — regenerate from this script)

Usage:
    python3 build_data.py              Full rebuild from scratch
    python3 build_data.py --from 4     Resume from step 4 (skip steps 1-3)
    python3 build_data.py --only 9     Run only step 9
"""

import subprocess
import sys
import time
from pathlib import Path

PYTHON = sys.executable
ROOT   = Path(__file__).parent

STEPS = [
    (1, "generate_analytics_data.py",                  "Base 12-CSV star schema"),
    (2, "scripts/regenerate_routes_v2.py",             "Weighted route distribution"),
    (3, "scripts/fix_owner_data.py",                   "Owner data cleanup"),
    (4, "scripts/consolidate_aog.py",                  "AOG consolidation to Mar/May/Oct"),
    (5, "scripts/fix_aog_costs.py",                    "Emergency AOG part costs"),
    (6, "scripts/fix_maintenance_cost_ratio.py",       "Parts/labor ratio corrections"),
    (7, "scripts/fix_fleet_status_seasonality.py",     "Initial seasonal FLYING% pass"),
    (8, "scripts/fix_daily_status_hours.py",           "Hours/cycles integrity"),
    (9, "scripts/rebalance_daily_status.py",           "FLYING<->AVAILABLE rebalance + holiday spike"),
]


def parse_args():
    from_step = 1
    only_step = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--from" and i + 1 < len(args):
            from_step = int(args[i + 1]); i += 2
        elif args[i] == "--only" and i + 1 < len(args):
            only_step = int(args[i + 1]); i += 2
        else:
            print(f"Unknown argument: {args[i]}")
            print(__doc__)
            sys.exit(1)
    return from_step, only_step


def run_step(num, script, description):
    path = ROOT / script
    if not path.exists():
        print(f"\n  [ERROR] Script not found: {path}")
        sys.exit(1)

    print(f"\n{'─' * 60}")
    print(f"  Step {num}/9 — {description}")
    print(f"  Script : {script}")
    print(f"{'─' * 60}")

    start = time.time()
    result = subprocess.run(
        [PYTHON, str(path)],
        cwd=str(ROOT),
        capture_output=False,   # stream output live to terminal
    )
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"\n  [FAILED] Step {num} exited with code {result.returncode}")
        print(f"  Stopping build. Fix the issue in {script} then re-run:")
        print(f"    python3 build_data.py --from {num}")
        sys.exit(result.returncode)

    print(f"\n  [OK] Step {num} completed in {elapsed:.1f}s")


def check_output_dir():
    out = ROOT / "output" / "analytics" / "data"
    out.mkdir(parents=True, exist_ok=True)


def main():
    from_step, only_step = parse_args()

    steps_to_run = [s for s in STEPS if
                    (only_step is None and s[0] >= from_step) or
                    (only_step is not None and s[0] == only_step)]

    if not steps_to_run:
        print("No matching steps to run.")
        sys.exit(0)

    if only_step and only_step > 1:
        print(f"[WARNING] Running only step {only_step}. "
              f"Ensure steps 1–{only_step - 1} have already been run.")

    print("=" * 60)
    print("  PlaneSense Analytics Data Build")
    print(f"  Steps to run: {[s[0] for s in steps_to_run]}")
    print("=" * 60)

    check_output_dir()
    total_start = time.time()

    for num, script, description in steps_to_run:
        run_step(num, script, description)

    total = time.time() - total_start
    print(f"\n{'=' * 60}")
    print(f"  BUILD COMPLETE — all {len(steps_to_run)} step(s) finished in {total:.1f}s")
    print(f"  Output: output/analytics/data/")
    print("=" * 60)


if __name__ == "__main__":
    main()

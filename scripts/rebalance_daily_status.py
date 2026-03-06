"""
rebalance_daily_status.py
--------------------------
Rebalances fact_aircraft_daily_status FLYING <-> AVAILABLE distribution
to match realistic fractional aviation seasonality.

Three-step plan:
  Step 1 — Convert FLYING rows with no matching fact_flight record -> AVAILABLE
  Step 2 — Holiday carve-out: restore Dec 20–Jan 5 FLYING to ~82% target
  Step 3 — Seasonal fine-tuning per month/period targets

AOG and IN_MAINTENANCE rows are never touched.
"""

import pandas as pd
import numpy as np

RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

DS_PATH  = "output/analytics/data/fact_aircraft_daily_status.csv"
FF_PATH  = "output/analytics/data/fact_flight.csv"
OUT_PATH = DS_PATH

# Target FLYING fraction of ALL rows in each period window
PERIOD_TARGETS = {
    "holiday":     0.82,   # Dec 20–Jan 5: peak demand
    "dec_non_hol": 0.64,   # Dec 1–19
    "jan_non_hol": 0.64,   # Jan 6–31
    "winter_rest": 0.64,   # Feb
    "march":       0.72,   # heavy inspection
    "april":       0.76,
    "may":         0.75,   # AOG + inspection
    "summer":      0.82,   # Jun–Aug peak flying
    "fall":        0.76,   # Sep, Nov
    "october":     0.72,   # heavy inspection
}


def period_mask(ds, period):
    m = ds["date"].dt.month
    d = ds["date"].dt.day
    masks = {
        "holiday":     ((m == 12) & (d >= 20)) | ((m == 1) & (d <= 5)),
        "dec_non_hol": (m == 12) & (d < 20),
        "jan_non_hol": (m == 1) & (d > 5),
        "winter_rest": m == 2,
        "march":       m == 3,
        "april":       m == 4,
        "may":         m == 5,
        "summer":      m.isin([6, 7, 8]),
        "fall":        m.isin([9, 11]),
        "october":     m == 10,
    }
    return masks[period]


def build_flight_lookup(ff):
    """Set of (date, aircraft_id) with an actual revenue/ferry flight."""
    return set(zip(ff["date"].dt.date, ff["aircraft_id"]))


def step1_convert_unmatched(ds, flight_lookup):
    flying_mask = ds["status"] == "FLYING"
    flying_idx  = ds.index[flying_mask]
    keys = list(zip(ds.loc[flying_idx, "date"].dt.date,
                    ds.loc[flying_idx, "aircraft_id"]))
    unmatched = [idx for idx, key in zip(flying_idx, keys) if key not in flight_lookup]
    ds.loc[unmatched, "status"]        = "AVAILABLE"
    ds.loc[unmatched, "flight_hours"]  = 0.0
    ds.loc[unmatched, "flight_cycles"] = 0
    print(f"Step 1: {len(unmatched):,} unmatched FLYING → AVAILABLE")
    return ds


def adjust_period(ds, mask, target_frac, period_name, flight_lookup, flying_median_fh):
    sub   = ds[mask]
    total = len(sub)
    if total == 0:
        return ds

    current_flying = (sub["status"] == "FLYING").sum()
    target_flying  = int(round(target_frac * total))
    delta = target_flying - current_flying

    if delta == 0:
        return ds

    if delta < 0:
        # Reduce FLYING: prefer rows with no flight record, then lowest flight_hours
        n = abs(delta)
        flying_sub = sub[sub["status"] == "FLYING"].copy()
        flying_sub["has_flight"] = flying_sub.apply(
            lambda r: (r["date"].date(), r["aircraft_id"]) in flight_lookup, axis=1
        )
        flying_sub_sorted = flying_sub.sort_values(["has_flight", "flight_hours"])
        chosen = flying_sub_sorted.index[:n]
        ds.loc[chosen, "status"]        = "AVAILABLE"
        ds.loc[chosen, "flight_hours"]  = 0.0
        ds.loc[chosen, "flight_cycles"] = 0
        actual_after = current_flying - len(chosen)
        print(f"  {period_name:15s}: FLYING {current_flying/total:.1%} → "
              f"{actual_after/total:.1%}  (target {target_frac:.1%}, "
              f"flipped {len(chosen):,} F→A)")
    else:
        # Increase FLYING: promote AVAILABLE rows that have a flight record
        n = delta
        avail_sub = sub[sub["status"] == "AVAILABLE"].copy()
        avail_sub["has_flight"] = avail_sub.apply(
            lambda r: (r["date"].date(), r["aircraft_id"]) in flight_lookup, axis=1
        )
        candidates = avail_sub[avail_sub["has_flight"]]
        n = min(n, len(candidates))
        chosen = candidates.index[:n]
        ds.loc[chosen, "status"]        = "FLYING"
        ds.loc[chosen, "flight_hours"]  = flying_median_fh
        ds.loc[chosen, "flight_cycles"] = 2
        actual_after = current_flying + len(chosen)
        print(f"  {period_name:15s}: FLYING {current_flying/total:.1%} → "
              f"{actual_after/total:.1%}  (target {target_frac:.1%}, "
              f"promoted {len(chosen):,} A→F)")

    return ds


def print_summary(ds, label):
    ds2 = ds.copy()
    ds2["month"] = ds2["date"].dt.month
    ds2["day"]   = ds2["date"].dt.day
    season_map = {12:"Winter",1:"Winter",2:"Winter",
                  3:"Spring",4:"Spring",5:"Spring",
                  6:"Summer",7:"Summer",8:"Summer",
                  9:"Fall",10:"Fall",11:"Fall"}
    ds2["season"] = ds2["month"].map(season_map)

    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    print(f"Overall:  FLYING={(ds2['status']=='FLYING').mean():.1%}  "
          f"AVAILABLE={(ds2['status']=='AVAILABLE').mean():.1%}  "
          f"MAINT={(ds2['status']=='IN_MAINTENANCE').mean():.1%}  "
          f"AOG={(ds2['status']=='AOG').mean():.1%}")

    for season in ["Winter","Spring","Summer","Fall"]:
        s = ds2[ds2["season"] == season]
        print(f"  {season}: FLYING={(s['status']=='FLYING').mean():.1%}  "
              f"AVAILABLE={(s['status']=='AVAILABLE').mean():.1%}")

    hw = ds2[((ds2["month"]==12)&(ds2["day"]>=20))|((ds2["month"]==1)&(ds2["day"]<=5))]
    rest_w = ds2[~(((ds2["month"]==12)&(ds2["day"]>=20))|((ds2["month"]==1)&(ds2["day"]<=5))) &
                  ds2["season"].eq("Winter")]
    print(f"  Holiday(Dec20-Jan5): FLYING={(hw['status']=='FLYING').mean():.1%}  "
          f"AVAILABLE={(hw['status']=='AVAILABLE').mean():.1%}")
    print(f"  Rest of Winter:      FLYING={(rest_w['status']=='FLYING').mean():.1%}  "
          f"AVAILABLE={(rest_w['status']=='AVAILABLE').mean():.1%}")


def main():
    print("Loading data...")
    ds = pd.read_csv(DS_PATH)
    ff = pd.read_csv(FF_PATH)
    ds["date"] = pd.to_datetime(ds["date"])
    ff["date"] = pd.to_datetime(ff["date"])

    flight_lookup    = build_flight_lookup(ff)
    flying_median_fh = float(ds.loc[ds["status"]=="FLYING","flight_hours"].median())

    print_summary(ds, "BEFORE")

    # Step 1
    print(f"\n{'─'*60}")
    ds = step1_convert_unmatched(ds, flight_lookup)

    # Step 2 — Holiday first (needs to push FLYING UP inside winter)
    print(f"\nStep 2: Holiday carve-out")
    ds = adjust_period(ds, period_mask(ds,"holiday"), PERIOD_TARGETS["holiday"],
                       "holiday", flight_lookup, flying_median_fh)

    # Step 3 — All other periods
    print(f"\nStep 3: Seasonal fine-tuning")
    for period in ["dec_non_hol","jan_non_hol","winter_rest",
                   "march","april","may","summer","fall","october"]:
        ds = adjust_period(ds, period_mask(ds, period), PERIOD_TARGETS[period],
                           period, flight_lookup, flying_median_fh)

    print_summary(ds, "AFTER")

    # Save
    ds["date"] = ds["date"].dt.strftime("%Y-%m-%d")
    ds.to_csv(OUT_PATH, index=False)
    print(f"\nSaved → {OUT_PATH}")


if __name__ == "__main__":
    main()

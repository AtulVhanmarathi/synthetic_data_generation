"""
PlaneSense Owner Churn — Synthetic Dataset Generator
=====================================================
Generates 5 domain-authentic CSV tables modelled on PlaneSense's
fractional ownership business, extracted from planesense.com.

Fleet basis:
  - ~350 fractional owners (US-based, West Coast expansion in 2024)
  - Share types: 1/32 (50h/yr)  1/16 (100h/yr)  1/8 (200h/yr)  1/4 (400h/yr)
  - Aircraft: PC-12 turboprop (75%)  PC-24 jet (25%)
  - 91% historic retention rate → ~9% annual churn
  - CobaltPass jet card launched May 2025 (sold out)
  - Jetfly EU partnership operational April 2025
  - West Coast hub expanded (Boulder City NV)

Output tables
-------------
  1. owners.csv                  — Master owner registry (350 rows)
  2. flight_activity.csv         — Individual flight legs 2023–2024 (~22k rows)
  3. service_interactions.csv    — Support / service touchpoints (~3.5k rows)
  4. owner_engagement.csv        — Monthly digital engagement (~8.4k rows)
  5. churn_ml_features.csv       — Model-ready feature matrix (350 rows)
                                   Targets: churned_within_12m, upsell_ready, upsell_type
"""

import os
import random
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

# ── Reproducibility ───────────────────────────────────────────────────────────
np.random.seed(7)
random.seed(7)
rng = np.random.default_rng(7)

# ── Paths ──────────────────────────────────────────────────────────────────────
OUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "output", "churn", "data"
)
os.makedirs(OUT_DIR, exist_ok=True)

SIM_START = date(2023, 1, 1)
SIM_END   = date(2024, 12, 31)
SNAPSHOT  = date(2024, 12, 31)       # ML feature snapshot date

# ── Domain constants ──────────────────────────────────────────────────────────
SHARE_CONFIGS = {
    "1/32": {"annual_hours": 50,  "weight": 0.30},
    "1/16": {"annual_hours": 100, "weight": 0.35},
    "1/8":  {"annual_hours": 200, "weight": 0.25},
    "1/4":  {"annual_hours": 400, "weight": 0.10},
}

REGIONS = {
    "Northeast":   {"states": ["MA","CT","RI","NH","VT","ME","NY"], "weight": 0.30},
    "Mid-Atlantic": {"states": ["NJ","PA","DE","MD","VA","DC"],     "weight": 0.20},
    "Southeast":   {"states": ["FL","GA","NC","SC","TN","AL"],      "weight": 0.18},
    "Midwest":     {"states": ["OH","MI","IL","IN","WI","MN"],      "weight": 0.15},
    "West_Coast":  {"states": ["CA","OR","WA","NV","AZ"],           "weight": 0.17},
}

# ~110 airports PlaneSense serves (using representative codes)
AIRPORTS = [
    "KPSM","KBOS","KJFK","KEWR","KPHL","KBWI","KDCA","KIAD",
    "KATL","KMIA","KTPA","KORL","KPBI","KJAX","KRDU","KCLT",
    "KORD","KMDW","KDET","KCLE","KPIT","KCMH","KCIN","KIND",
    "KLAX","KSFO","KSJC","KOAK","KSAN","KBUR","KSMF","KPDX",
    "KSEA","KPHX","KLAS","KBVU","KDEN","KSLC","KDAL","KHOU",
    "KIAH","KMSY","KSTL","KMEM","KLIT","KNMM","KSAV","KFLL",
    "KBHM","KCAE","KGSP","KCHA","KJAN","KMOB","KHSV","KPNS",
    "KABQ","KELP","KTUS","KFAR","KFSD","KOMK","KBIS","KRAP",
    "KBTM","KBZN","KGJT","KGUC","KASN","KEGE","KHCD","KFLY",
]

ACCOUNT_MANAGERS = [f"AM-{i:03d}" for i in range(1, 9)]   # 8 account managers

# ─ First/last name pools (anonymized) ─────────────────────────────────────────
FIRST_NAMES = [
    "James","John","Robert","Michael","William","David","Richard","Joseph",
    "Thomas","Charles","Patricia","Jennifer","Linda","Barbara","Susan",
    "Jessica","Sarah","Karen","Nancy","Lisa","Andrew","Mark","Paul","Steven",
    "Kenneth","George","Brian","Edward","Ronald","Anthony","Kevin","Scott",
    "Elizabeth","Helen","Donna","Carol","Ruth","Sharon","Michelle","Laura",
]
LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
    "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson",
    "Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson",
    "White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker",
    "Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores",
]


# ══════════════════════════════════════════════════════════════════════════════
# TABLE 1 — OWNERS
# ══════════════════════════════════════════════════════════════════════════════

def build_owners(n: int = 350) -> pd.DataFrame:
    rows = []
    used_names = set()

    share_choices = list(SHARE_CONFIGS.keys())
    share_weights = [SHARE_CONFIGS[s]["weight"] for s in share_choices]

    region_choices = list(REGIONS.keys())
    region_weights = [REGIONS[r]["weight"] for r in region_choices]

    for i in range(1, n + 1):
        # Unique name
        while True:
            first = random.choice(FIRST_NAMES)
            last  = random.choice(LAST_NAMES)
            name  = f"{first} {last}"
            if name not in used_names:
                used_names.add(name)
                break

        # Join date: right-skewed toward recent (more new owners)
        join_days_ago = int(np.random.exponential(scale=600) + 180)
        join_days_ago = min(join_days_ago, 7300)   # cap at 20 years
        join_date = SNAPSHOT - timedelta(days=join_days_ago)

        region = rng.choice(region_choices, p=region_weights)
        state  = random.choice(REGIONS[region]["states"])
        share  = rng.choice(share_choices, p=share_weights)
        aircraft_pref = rng.choice(["PC-12", "PC-24", "No Preference"],
                                    p=[0.55, 0.25, 0.20])
        annual_hours  = SHARE_CONFIGS[share]["annual_hours"]

        # Contract structure
        contract_start = join_date
        # 3-year contracts; renewal cycles
        years_since_join = (SNAPSHOT - join_date).days / 365
        renewals_done = int(years_since_join / 3)
        current_contract_start = join_date + timedelta(days=renewals_done * 365 * 3)
        current_contract_end   = current_contract_start + timedelta(days=365 * 3)
        days_until_renewal = (current_contract_end - SNAPSHOT).days
        days_until_renewal = max(1, days_until_renewal % (365 * 3))

        # Product eligibility
        is_cobaltpass = rng.random() < 0.12          # 12% have CobaltPass
        has_jetfly    = (region == "Northeast" or
                         region == "Mid-Atlantic") and rng.random() < 0.12

        # Account manager (stable, rarely changes)
        am = random.choice(ACCOUNT_MANAGERS)
        am_changes = int(rng.choice([0, 1, 2], p=[0.75, 0.20, 0.05]))

        rows.append(dict(
            owner_id             = f"PL-{i:04d}",
            owner_name           = name,
            region               = region,
            state                = state,
            join_date            = join_date,
            tenure_years         = round(years_since_join, 2),
            share_type           = share,
            annual_hours_contracted = annual_hours,
            aircraft_preference  = aircraft_pref,
            cobalt_pass_holder   = int(is_cobaltpass),
            jetfly_access        = int(has_jetfly),
            account_manager_id   = am,
            account_manager_changes = am_changes,
            contract_start       = current_contract_start,
            contract_end         = current_contract_end,
            days_until_renewal   = days_until_renewal,
            contract_renewals_done = renewals_done,
        ))

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# TABLE 2 — FLIGHT ACTIVITY
# ══════════════════════════════════════════════════════════════════════════════

def build_flight_activity(owners_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    flight_counter = 0

    for _, owner in owners_df.iterrows():
        oid          = owner["owner_id"]
        ann_hrs      = owner["annual_hours_contracted"]
        ac_pref      = owner["aircraft_preference"]
        region       = owner["region"]
        join_date    = pd.to_datetime(owner["join_date"]).date()

        # Utilization profile (determines how many flights)
        # Will be adjusted during rank-based target assignment
        base_util = float(rng.beta(5, 2))       # centered ~0.71

        # Monthly flights ≈ (annual_hours * util) / avg_trip_duration / 12
        avg_trip_hrs = float(rng.uniform(1.2, 2.8))
        annual_flights = (ann_hrs * base_util) / avg_trip_hrs
        monthly_flights = max(0.5, annual_flights / 12)

        # Trip purpose mix
        biz_pct = float(rng.beta(3, 2))     # ~0.6 business

        # Seasonal weights (higher summer + holidays)
        month_weights = [0.07, 0.07, 0.08, 0.08, 0.09, 0.10,
                         0.10, 0.09, 0.08, 0.08, 0.08, 0.09]
        month_weights = np.array(month_weights) / sum(month_weights)

        for year in [2023, 2024]:
            for month in range(1, 13):
                dt = date(year, month, 1)
                if dt < join_date:
                    continue
                if dt > SIM_END:
                    break

                n_flights = max(0, int(rng.poisson(monthly_flights * month_weights[month-1] * 12)))
                for _ in range(n_flights):
                    flight_counter += 1
                    day = rng.integers(1, 28)
                    fdate = date(year, month, day)
                    dep   = random.choice(AIRPORTS)
                    arr   = random.choice([a for a in AIRPORTS if a != dep])
                    dur   = round(float(rng.uniform(0.8, avg_trip_hrs * 1.4)), 2)
                    ac    = (ac_pref if ac_pref != "No Preference"
                             else rng.choice(["PC-12","PC-24"], p=[0.70, 0.30]))
                    pax   = int(rng.integers(1, 7))
                    purpose = ("Business" if rng.random() < biz_pct
                               else rng.choice(["Leisure","Medical","Mixed"],
                                                p=[0.60, 0.05, 0.35]))
                    on_time = rng.random() < 0.88

                    rows.append(dict(
                        flight_id          = f"FLT-{flight_counter:06d}",
                        owner_id           = oid,
                        flight_date        = fdate,
                        departure_airport  = dep,
                        arrival_airport    = arr,
                        flight_duration_hrs= dur,
                        aircraft_type      = ac,
                        pax_count          = pax,
                        trip_purpose       = purpose,
                        on_time_departure  = int(on_time),
                    ))

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# TABLE 3 — SERVICE INTERACTIONS
# ══════════════════════════════════════════════════════════════════════════════

INTERACTION_TYPES = ["Scheduling Request","Billing Inquiry","Complaint",
                     "Compliment","General Inquiry","Trip Amendment"]
CHANNELS          = ["Phone","Email","Portal","In-Person"]

def build_service_interactions(owners_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    event_counter = 0

    for _, owner in owners_df.iterrows():
        oid       = owner["owner_id"]
        join_date = pd.to_datetime(owner["join_date"]).date()
        tenure    = owner["tenure_years"]

        # Number of interactions: newer owners contact more, happy owners less
        base_monthly = float(rng.uniform(0.3, 0.8))

        for year in [2023, 2024]:
            for month in range(1, 13):
                dt = date(year, month, 1)
                if dt < join_date:
                    continue
                n = int(rng.poisson(base_monthly))
                for _ in range(n):
                    event_counter += 1
                    day  = rng.integers(1, 28)
                    edate = date(year, month, day)

                    itype = rng.choice(INTERACTION_TYPES,
                                       p=[0.30, 0.20, 0.15, 0.10, 0.15, 0.10])
                    chan  = rng.choice(CHANNELS, p=[0.40, 0.35, 0.15, 0.10])
                    is_complaint = (itype == "Complaint")
                    resolved  = rng.random() < (0.72 if is_complaint else 0.95)
                    res_days  = round(float(rng.exponential(2.5 if is_complaint else 0.8)), 1)
                    escalated = is_complaint and rng.random() < 0.12
                    surveyed  = rng.random() < 0.40
                    if surveyed:
                        # Satisfaction: complaints skew low
                        if is_complaint:
                            sat = round(float(rng.beta(2, 4) * 4 + 1), 1)
                        else:
                            sat = round(float(rng.beta(4, 2) * 4 + 1), 1)
                        sat = round(min(5.0, max(1.0, sat)), 1)
                    else:
                        sat = None

                    rows.append(dict(
                        interaction_id    = f"SVC-{event_counter:06d}",
                        owner_id          = oid,
                        interaction_date  = edate,
                        channel           = chan,
                        interaction_type  = itype,
                        resolved          = int(resolved),
                        resolution_days   = res_days,
                        satisfaction_score= sat,
                        escalated         = int(escalated),
                    ))

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# TABLE 4 — OWNER ENGAGEMENT (monthly digital)
# ══════════════════════════════════════════════════════════════════════════════

def build_owner_engagement(owners_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, owner in owners_df.iterrows():
        oid       = owner["owner_id"]
        join_date = pd.to_datetime(owner["join_date"]).date()

        # Base engagement level (varies by owner)
        base_sessions = float(rng.uniform(3, 18))
        base_logins   = float(rng.uniform(2, 12))

        for year in [2023, 2024]:
            for month in range(1, 13):
                dt = date(year, month, 1)
                if dt < join_date:
                    continue
                sessions   = max(0, int(rng.poisson(base_sessions)))
                logins     = max(0, int(rng.poisson(base_logins)))
                email_opens= max(0, int(rng.poisson(2.5)))
                event_att  = int(rng.random() < 0.05)    # ~5% attend an event/month
                nl_clicks  = max(0, int(rng.poisson(0.8)))
                am_calls   = max(0, int(rng.poisson(0.4)))

                rows.append(dict(
                    owner_id          = oid,
                    year              = year,
                    month             = month,
                    app_sessions      = sessions,
                    portal_logins     = logins,
                    emails_opened     = email_opens,
                    event_attended    = event_att,
                    newsletter_clicks = nl_clicks,
                    account_manager_calls = am_calls,
                ))

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# TABLE 5 — CHURN ML FEATURES (rank-based target injection)
# ══════════════════════════════════════════════════════════════════════════════

def build_churn_features(
    owners_df: pd.DataFrame,
    flights_df: pd.DataFrame,
    service_df: pd.DataFrame,
    engagement_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    One row per owner. Features engineered from the four raw tables.
    Targets assigned via rank-based hazard scoring for strong correlations.
    """
    # ── Pre-index data ────────────────────────────────────────────────────────
    flights_df["flight_date"] = pd.to_datetime(flights_df["flight_date"])
    service_df["interaction_date"] = pd.to_datetime(service_df["interaction_date"])

    cutoff_12m = pd.Timestamp(SNAPSHOT) - pd.Timedelta(days=365)
    cutoff_24m = pd.Timestamp(SNAPSHOT) - pd.Timedelta(days=730)
    cutoff_90d = pd.Timestamp(SNAPSHOT) - pd.Timedelta(days=90)
    cutoff_180d = pd.Timestamp(SNAPSHOT) - pd.Timedelta(days=180)

    fl_12m = flights_df[flights_df["flight_date"] >= cutoff_12m]
    fl_24m = flights_df[flights_df["flight_date"] >= cutoff_24m]
    fl_prev = flights_df[
        (flights_df["flight_date"] >= cutoff_24m) &
        (flights_df["flight_date"] < cutoff_12m)
    ]

    sv_12m = service_df[service_df["interaction_date"] >= cutoff_12m]

    eng_12m = engagement_df[
        (engagement_df["year"] == 2024) |
        ((engagement_df["year"] == 2023) & (engagement_df["month"] >= 1))
    ]

    rows = []
    for _, owner in owners_df.iterrows():
        oid        = owner["owner_id"]
        ann_hrs    = owner["annual_hours_contracted"]

        # ── Flight utilization ────────────────────────────────────────────
        ofl_12m  = fl_12m[fl_12m["owner_id"] == oid]
        ofl_prev = fl_prev[fl_prev["owner_id"] == oid]
        ofl_90d  = flights_df[
            (flights_df["owner_id"] == oid) &
            (flights_df["flight_date"] >= cutoff_90d)
        ]
        ofl_all  = fl_24m[fl_24m["owner_id"] == oid]

        hours_12m   = float(ofl_12m["flight_duration_hrs"].sum())
        hours_prev  = float(ofl_prev["flight_duration_hrs"].sum())
        flights_12m = len(ofl_12m)
        flights_prev = len(ofl_prev)
        flights_90d = len(ofl_90d)

        util_12m  = round(hours_12m / max(ann_hrs, 1), 4)
        util_prev = round(hours_prev / max(ann_hrs, 1), 4)
        util_delta = round(util_12m - util_prev, 4)

        # Days since last flight
        if len(ofl_all) > 0:
            last_flight = ofl_all["flight_date"].max()
            days_since_last = (pd.Timestamp(SNAPSHOT) - last_flight).days
        else:
            days_since_last = 730

        # Longest gap between flights in last 12m
        if len(ofl_12m) >= 2:
            sorted_dates = ofl_12m["flight_date"].sort_values()
            gaps = sorted_dates.diff().dt.days.dropna()
            max_gap = int(gaps.max()) if len(gaps) > 0 else 365
        elif len(ofl_12m) == 1:
            max_gap = days_since_last
        else:
            max_gap = 365

        # Trip purpose
        if len(ofl_12m) > 0:
            biz_pct = float((ofl_12m["trip_purpose"] == "Business").mean())
            avg_dur = float(ofl_12m["flight_duration_hrs"].mean())
            unique_airports = int(
                ofl_12m["departure_airport"].nunique() +
                ofl_12m["arrival_airport"].nunique()
            )
            on_time_rate = float(ofl_12m["on_time_departure"].mean())
        else:
            biz_pct = 0.5
            avg_dur = 1.5
            unique_airports = 0
            on_time_rate = 0.85

        # ── Service interactions ──────────────────────────────────────────
        osv = sv_12m[sv_12m["owner_id"] == oid]
        complaints_12m    = int((osv["interaction_type"] == "Complaint").sum())
        escalations_12m   = int(osv["escalated"].sum())
        unresolved        = int((osv["resolved"] == 0).sum())
        all_sat = osv["satisfaction_score"].dropna()
        avg_satisfaction  = float(all_sat.mean()) if len(all_sat) > 0 else 3.8
        pct_complaints    = float(
            (osv["interaction_type"] == "Complaint").mean()
        ) if len(osv) > 0 else 0.0

        if len(osv) > 0:
            days_since_last_interaction = (
                pd.Timestamp(SNAPSHOT) - osv["interaction_date"].max()
            ).days
        else:
            days_since_last_interaction = 180

        # ── Engagement ────────────────────────────────────────────────────
        oeng = eng_12m[eng_12m["owner_id"] == oid]
        avg_sessions_month = float(oeng["app_sessions"].mean()) if len(oeng) > 0 else 5.0
        total_email_opens  = int(oeng["emails_opened"].sum())
        events_attended    = int(oeng["event_attended"].sum())
        total_am_calls     = int(oeng["account_manager_calls"].sum())

        # ── Owner attributes ──────────────────────────────────────────────
        tenure_yrs = float(owner["tenure_years"])
        share_tier = {"1/32": 1, "1/16": 2, "1/8": 3, "1/4": 4}[owner["share_type"]]
        region_enc = {"Northeast": 0, "Mid-Atlantic": 1, "Southeast": 2,
                      "Midwest": 3, "West_Coast": 4}[owner["region"]]
        ac_enc     = {"PC-12": 0, "No Preference": 1, "PC-24": 2}[
            owner["aircraft_preference"]
        ]

        rows.append(dict(
            owner_id                    = oid,
            owner_name                  = owner["owner_name"],
            region                      = owner["region"],
            state                       = owner["state"],
            snapshot_date               = SNAPSHOT,
            # Tenure
            tenure_years                = round(tenure_yrs, 2),
            days_until_renewal          = int(owner["days_until_renewal"]),
            contract_renewals_done      = int(owner["contract_renewals_done"]),
            account_manager_changes     = int(owner["account_manager_changes"]),
            # Product
            share_tier                  = share_tier,
            annual_hours_contracted     = int(ann_hrs),
            cobalt_pass_holder          = int(owner["cobalt_pass_holder"]),
            jetfly_access               = int(owner["jetfly_access"]),
            aircraft_pref_encoded       = ac_enc,
            region_encoded              = region_enc,
            # Utilization
            hours_flown_12m             = round(hours_12m, 1),
            utilization_rate_12m        = round(min(util_12m, 1.50), 4),
            utilization_rate_prior_12m  = round(min(util_prev, 1.50), 4),
            utilization_rate_delta      = round(util_delta, 4),
            flights_12m                 = flights_12m,
            flights_prior_12m           = flights_prev,
            flights_90d                 = flights_90d,
            days_since_last_flight      = int(min(days_since_last, 730)),
            longest_gap_days            = int(max_gap),
            avg_flight_duration_hrs     = round(avg_dur, 2),
            trip_purpose_biz_pct        = round(biz_pct, 4),
            unique_airports_12m         = unique_airports,
            on_time_departure_rate      = round(on_time_rate, 4),
            # Service
            complaints_12m              = complaints_12m,
            escalations_12m             = escalations_12m,
            unresolved_issues           = unresolved,
            avg_satisfaction_score      = round(avg_satisfaction, 2),
            pct_interactions_complaints = round(pct_complaints, 4),
            days_since_last_interaction = int(days_since_last_interaction),
            # Engagement
            avg_app_sessions_month      = round(avg_sessions_month, 2),
            total_email_opens_12m       = total_email_opens,
            events_attended_12m         = events_attended,
            am_calls_12m                = total_am_calls,
        ))

    df = pd.DataFrame(rows)

    # ── RANK-BASED CHURN TARGET ASSIGNMENT ───────────────────────────────────
    # Composite churn hazard score (higher = more likely to churn)
    df["_churn_hazard"] = (
        # Low utilization: strongest signal (inverted — low util = high churn risk)
        (1.0 - df["utilization_rate_12m"].clip(0, 1)) * 0.35

        # Declining trend: delta < 0 means dropping usage
        + (-df["utilization_rate_delta"].clip(-1, 1) * 0.5 + 0.5) * 0.15

        # Days dormant: longer gap → higher risk
        + (df["days_since_last_flight"] / 365).clip(0, 1) * 0.15

        # Service issues
        + (df["complaints_12m"] / 5).clip(0, 1) * 0.10
        + (df["escalations_12m"] / 2).clip(0, 1) * 0.05
        + (df["unresolved_issues"] / 3).clip(0, 1) * 0.05

        # Low engagement
        + (1.0 - (df["avg_app_sessions_month"] / 20).clip(0, 1)) * 0.07

        # Renewal proximity: <60 days = nervous window
        + ((df["days_until_renewal"] < 60).astype(float)) * 0.05

        # Longer tenure = more stable (inverted)
        + (1.0 - (df["tenure_years"] / 15).clip(0, 1)) * 0.03

        # Small share: easier to walk away
        + (1.0 - (df["share_tier"] / 4)) * 0.05

        # Tie-breaking noise
        + rng.uniform(0, 0.02, len(df))
    )

    # Assign top 9% → churned (matching PlaneSense's ~91% retention)
    thr_churn = df["_churn_hazard"].quantile(0.91)
    df["churned_within_12m"] = (df["_churn_hazard"] >= thr_churn).astype(int)

    # ── RANK-BASED UPSELL TARGET ASSIGNMENT ──────────────────────────────────
    # Only non-churning owners can be upsell targets
    active = df[df["churned_within_12m"] == 0].copy()

    active["_upsell_score"] = (
        # High utilization: strongest upsell signal
        active["utilization_rate_12m"].clip(0, 1.5) * 0.40

        # Growing usage
        + (active["utilization_rate_delta"].clip(-1, 1) * 0.5 + 0.5) * 0.15

        # Business traveler: higher ROI = open to upsell
        + active["trip_purpose_biz_pct"].clip(0, 1) * 0.12

        # Long tenure = trusted relationship
        + (active["tenure_years"] / 15).clip(0, 1) * 0.10

        # High satisfaction
        + (active["avg_satisfaction_score"] / 5) * 0.10

        # Frequent flyer (more flights 90d vs prior)
        + (active["flights_90d"] / max(float(active["flights_90d"].max()), 1)) * 0.08

        # Long haul preference: PC-24 upgrade signal
        + (active["avg_flight_duration_hrs"] / 4).clip(0, 1) * 0.05

        # Tie-breaking noise
        + rng.uniform(0, 0.02, len(active))
    )

    # Top 15% of active owners are upsell-ready
    thr_upsell = active["_upsell_score"].quantile(0.85)
    df["upsell_ready"] = 0
    upsell_mask = (df["churned_within_12m"] == 0) & (
        df.index.isin(active[active["_upsell_score"] >= thr_upsell].index)
    )
    df.loc[upsell_mask, "upsell_ready"] = 1

    # ── UPSELL TYPE ───────────────────────────────────────────────────────────
    def _upsell_type(row):
        if row["upsell_ready"] == 0:
            return "NONE"
        # Overshoot on hours → share upgrade
        if row["utilization_rate_12m"] > 0.90:
            return "SHARE_UPGRADE"
        # Long haul on PC-12 → aircraft upgrade
        if row["avg_flight_duration_hrs"] > 2.3 and row["aircraft_pref_encoded"] == 0:
            return "AIRCRAFT_UPGRADE_PC24"
        # CobaltPass holder flying a lot → fractional
        if row["cobalt_pass_holder"] and row["flights_12m"] > 20:
            return "COBALTPASS_TO_FRACTIONAL"
        # Northeast/Mid-Atlantic with no Jetfly → Jetfly intro
        if row["region_encoded"] <= 1 and row["jetfly_access"] == 0:
            return "JETFLY_INTRO"
        return "SHARE_UPGRADE"    # default upsell

    df["upsell_type"] = df.apply(_upsell_type, axis=1)

    # ── Clean up temp columns ─────────────────────────────────────────────────
    df = df.drop(columns=["_churn_hazard"])
    # Keep _upsell_score only for active owners (for inspection); drop from output
    if "_upsell_score" in df.columns:
        df = df.drop(columns=["_upsell_score"])

    return df


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def save(df: pd.DataFrame, name: str) -> None:
    path = os.path.join(OUT_DIR, name)
    df.to_csv(path, index=False)
    kb = os.path.getsize(path) / 1024
    print(f"  ✓  {name:<45} {len(df):>7,} rows   {kb:>7.1f} KB")


def main():
    bar = "=" * 65
    print(f"\n{bar}")
    print("  PlaneSense Owner Churn — Synthetic Data Generator")
    print(bar)

    print("\n[1/5] Owner registry …")
    owners = build_owners(350)
    save(owners, "owners.csv")

    print("[2/5] Flight activity (2023–2024) …")
    flights = build_flight_activity(owners)
    save(flights, "flight_activity.csv")

    print("[3/5] Service interactions …")
    service = build_service_interactions(owners)
    save(service, "service_interactions.csv")

    print("[4/5] Owner engagement (monthly) …")
    engagement = build_owner_engagement(owners)
    save(engagement, "owner_engagement.csv")

    print("[5/5] Churn ML features (model-ready) …")
    features = build_churn_features(owners, flights, service, engagement)
    save(features, "churn_ml_features.csv")

    # Summary
    print(f"\n{bar}")
    print("  DATASET SUMMARY")
    print(bar)
    print(f"  Owners              : {len(owners)}")
    print(f"  Flight legs         : {len(flights):,}")
    print(f"  Service events      : {len(service):,}")
    print(f"  Engagement rows     : {len(engagement):,}")
    print(f"  ML feature rows     : {len(features)}")
    print()
    print(f"  CHURN TARGET DISTRIBUTION")
    print(f"  churned_within_12m  : {features.churned_within_12m.sum()} "
          f"({features.churned_within_12m.mean():.1%})")
    print(f"  upsell_ready        : {features.upsell_ready.sum()} "
          f"({features.upsell_ready.mean():.1%})")
    print(f"  upsell_type counts  :")
    for k, v in features.upsell_type.value_counts().items():
        print(f"    {k:<35} {v}")
    print(f"\n  Output directory    : {os.path.relpath(OUT_DIR)}")
    print(bar)


if __name__ == "__main__":
    main()

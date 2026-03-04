"""
PlaneSense Owner Churn — ML Model Training
==========================================
Trains and evaluates two XGBoost models:

  1. Churn classifier   → churned_within_12m  (~9% positive)
  2. Upsell classifier  → upsell_ready         (~14% positive)

Outputs (output/churn/model/):
  - churn_model.json          XGBoost churn classifier
  - upsell_model.json         XGBoost upsell classifier
  - metrics.json              Full evaluation metrics
  - feature_list.txt          Ordered features for inference
  - plots/
      01_roc_pr_churn.png
      02_roc_pr_upsell.png
      03_feature_importance.png
      04_shap_churn.png
      05_shap_upsell.png
      06_confusion_matrices.png
      07_churn_risk_segments.png
  - demo_at_risk.csv          Owners sorted by churn probability
  - demo_upsell_pipeline.csv  Owners ready for upsell conversation
"""

import json
import os
import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
import seaborn as sns
import shap
import xgboost as xgb
from sklearn.metrics import (
    auc, average_precision_score, classification_report,
    confusion_matrix, precision_recall_curve, roc_auc_score, roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "output", "churn", "data", "churn_ml_features.csv")
MODEL_DIR = os.path.join(BASE_DIR, "output", "churn", "model")
PLOT_DIR  = os.path.join(MODEL_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

# ── Style ──────────────────────────────────────────────────────────────────────
NAVY  = "#0A1628"
BLUE  = "#0A84FF"
AMBER = "#F5A623"
RED   = "#E63946"
GREEN = "#52B788"
LGRAY = "#E8EDF4"
plt.rcParams.update({
    "figure.facecolor": NAVY, "axes.facecolor": "#0D1F3C",
    "axes.edgecolor": "#1E3A5F", "axes.labelcolor": LGRAY,
    "xtick.color": LGRAY, "ytick.color": LGRAY, "text.color": LGRAY,
    "grid.color": "#1E3A5F", "grid.linestyle": "--", "grid.linewidth": 0.5,
    "legend.facecolor": "#0D1F3C", "legend.edgecolor": "#1E3A5F",
    "font.family": "DejaVu Sans", "font.size": 11,
})

# ── Features ───────────────────────────────────────────────────────────────────
FEATURE_COLS = [
    # Tenure
    "tenure_years", "days_until_renewal", "contract_renewals_done",
    "account_manager_changes",
    # Product
    "share_tier", "annual_hours_contracted",
    "cobalt_pass_holder", "jetfly_access",
    "aircraft_pref_encoded", "region_encoded",
    # Utilization
    "utilization_rate_12m", "utilization_rate_prior_12m",
    "utilization_rate_delta",
    "flights_12m", "flights_prior_12m", "flights_90d",
    "days_since_last_flight", "longest_gap_days",
    "avg_flight_duration_hrs", "trip_purpose_biz_pct",
    "unique_airports_12m", "on_time_departure_rate",
    # Service
    "complaints_12m", "escalations_12m", "unresolved_issues",
    "avg_satisfaction_score", "pct_interactions_complaints",
    "days_since_last_interaction",
    # Engagement
    "avg_app_sessions_month", "total_email_opens_12m",
    "events_attended_12m", "am_calls_12m",
]

FRIENDLY = {
    "utilization_rate_12m":       "Utilization rate (12m)",
    "utilization_rate_delta":     "Utilization trend (delta)",
    "days_since_last_flight":     "Days since last flight",
    "complaints_12m":             "Complaints (12m)",
    "escalations_12m":            "Escalations (12m)",
    "days_until_renewal":         "Days until renewal",
    "avg_satisfaction_score":     "Avg satisfaction score",
    "avg_app_sessions_month":     "Avg app sessions / month",
    "tenure_years":               "Tenure (years)",
    "longest_gap_days":           "Longest flight gap (days)",
    "utilization_rate_prior_12m": "Utilization rate (prior 12m)",
    "share_tier":                 "Share tier (1=1/32 … 4=1/4)",
    "unresolved_issues":          "Unresolved service issues",
    "flights_12m":                "Flights last 12m",
    "account_manager_changes":    "Account manager changes",
    "pct_interactions_complaints":"% interactions = complaints",
    "annual_hours_contracted":    "Annual hours contracted",
    "contract_renewals_done":     "Renewals completed",
    "cobalt_pass_holder":         "CobaltPass holder",
    "jetfly_access":              "Jetfly (EU) access",
    "aircraft_pref_encoded":      "Aircraft pref (0=PC-12, 2=PC-24)",
    "region_encoded":             "Region encoded",
    "flights_prior_12m":          "Flights prior 12m",
    "flights_90d":                "Flights last 90d",
    "avg_flight_duration_hrs":    "Avg flight duration (hrs)",
    "trip_purpose_biz_pct":       "% business trips",
    "unique_airports_12m":        "Unique airports (12m)",
    "on_time_departure_rate":     "On-time departure rate",
    "days_since_last_interaction":"Days since last service contact",
    "total_email_opens_12m":      "Email opens (12m)",
    "events_attended_12m":        "Events attended (12m)",
    "am_calls_12m":               "Account manager calls (12m)",
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def savefig(name):
    path = os.path.join(PLOT_DIR, name)
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=NAVY)
    plt.close()
    print(f"    saved → {os.path.relpath(path, BASE_DIR)}")


def section(title):
    print(f"\n{'─'*65}\n  {title}\n{'─'*65}")


def plot_roc_pr(y_true, prob, label, color, filename):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    fig.suptitle(f"Model Performance — {label}",
                 color="white", fontsize=14, fontweight="bold", y=1.01)

    # ROC
    fpr, tpr, _ = roc_curve(y_true, prob)
    roc_val = auc(fpr, tpr)
    axes[0].plot(fpr, tpr, color=color, lw=2.5, label=f"ROC AUC = {roc_val:.3f}")
    axes[0].plot([0,1],[0,1],"--",color="#3A5A80",lw=1)
    axes[0].set_xlabel("False Positive Rate")
    axes[0].set_ylabel("True Positive Rate")
    axes[0].set_title("ROC Curve", color="white", pad=8)
    axes[0].legend(loc="lower right")
    axes[0].grid(True, alpha=0.3)

    # PR
    prec, rec, _ = precision_recall_curve(y_true, prob)
    ap_val = average_precision_score(y_true, prob)
    baseline = float(y_true.mean())
    axes[1].plot(rec, prec, color=color, lw=2.5, label=f"AP = {ap_val:.3f}")
    axes[1].axhline(baseline, linestyle="--", color="#3A5A80", lw=1,
                    label=f"Baseline = {baseline:.2f}")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].set_title("Precision-Recall Curve", color="white", pad=8)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    savefig(filename)
    return roc_val, ap_val


# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════════
section("1 / 6  Loading Data")

df = pd.read_csv(DATA_PATH)
print(f"  Dataset         : {len(df):,} owners × {len(df.columns)} cols")
print(f"  Churned (12m)   : {df.churned_within_12m.sum()} ({df.churned_within_12m.mean():.1%})")
print(f"  Upsell-ready    : {df.upsell_ready.sum()} ({df.upsell_ready.mean():.1%})")

X = df[FEATURE_COLS].copy()
y_churn  = df["churned_within_12m"]
y_upsell = df["upsell_ready"]

# Impute any NaNs (avg_satisfaction_score can be NaN for owners with no surveys)
X["avg_satisfaction_score"] = X["avg_satisfaction_score"].fillna(3.8)

# Stratified splits
(X_tr, X_te, yc_tr, yc_te,
 yu_tr, yu_te) = train_test_split(
    X, y_churn, y_upsell,
    test_size=0.20, random_state=42, stratify=y_churn
)
print(f"  Train / Test    : {len(X_tr)} / {len(X_te)}")
print(f"  Test churned    : {yc_te.sum()} / {len(yc_te)}")

with open(os.path.join(MODEL_DIR, "feature_list.txt"), "w") as f:
    f.write("\n".join(FEATURE_COLS))


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CHURN CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════════
section("2 / 6  Training Churn Classifier")

pos_c  = yc_tr.sum()
neg_c  = len(yc_tr) - pos_c
spw_c  = neg_c / pos_c

XGB_PARAMS = dict(
    n_estimators=500, max_depth=4, learning_rate=0.04,
    subsample=0.80, colsample_bytree=0.75,
    min_child_weight=3, reg_alpha=0.2, reg_lambda=1.0,
    eval_metric="aucpr", random_state=42, n_jobs=-1, verbosity=0,
)

clf_churn = xgb.XGBClassifier(scale_pos_weight=spw_c, **XGB_PARAMS)
clf_churn.fit(X_tr, yc_tr, eval_set=[(X_te, yc_te)], verbose=False)

cv_churn = cross_val_score(
    xgb.XGBClassifier(scale_pos_weight=spw_c, **XGB_PARAMS),
    X, y_churn,
    cv=StratifiedKFold(5, shuffle=True, random_state=42),
    scoring="roc_auc", n_jobs=-1,
)
print(f"  Churn CV AUC    : {cv_churn.mean():.3f} ± {cv_churn.std():.3f}")

clf_churn.save_model(os.path.join(MODEL_DIR, "churn_model.json"))


# ═══════════════════════════════════════════════════════════════════════════════
# 3. UPSELL CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════════
section("3 / 6  Training Upsell Classifier")

pos_u = yu_tr.sum()
neg_u = len(yu_tr) - pos_u
spw_u = neg_u / pos_u

clf_upsell = xgb.XGBClassifier(scale_pos_weight=spw_u, **XGB_PARAMS)
clf_upsell.fit(X_tr, yu_tr, eval_set=[(X_te, yu_te)], verbose=False)

cv_upsell = cross_val_score(
    xgb.XGBClassifier(scale_pos_weight=spw_u, **XGB_PARAMS),
    X, y_upsell,
    cv=StratifiedKFold(5, shuffle=True, random_state=42),
    scoring="roc_auc", n_jobs=-1,
)
print(f"  Upsell CV AUC   : {cv_upsell.mean():.3f} ± {cv_upsell.std():.3f}")

clf_upsell.save_model(os.path.join(MODEL_DIR, "upsell_model.json"))


# ═══════════════════════════════════════════════════════════════════════════════
# 4. EVALUATE
# ═══════════════════════════════════════════════════════════════════════════════
section("4 / 6  Evaluating Models")

prob_churn  = clf_churn.predict_proba(X_te)[:, 1]
prob_upsell = clf_upsell.predict_proba(X_te)[:, 1]
pred_churn  = clf_churn.predict(X_te)

auc_c  = roc_auc_score(yc_te, prob_churn)
ap_c   = average_precision_score(yc_te, prob_churn)
auc_u  = roc_auc_score(yu_te, prob_upsell)
ap_u   = average_precision_score(yu_te, prob_upsell)

print(f"  Churn   ROC-AUC={auc_c:.3f}   PR-AUC={ap_c:.3f}")
print(f"  Upsell  ROC-AUC={auc_u:.3f}   PR-AUC={ap_u:.3f}")
print()
print("  Churn classification report:")
print(classification_report(yc_te, pred_churn,
                             target_names=["Retained", "Churned"], digits=3))

metrics = {
    "churn":  {"roc_auc": round(auc_c, 4), "pr_auc": round(ap_c, 4),
               "cv_auc_mean": round(float(cv_churn.mean()), 4),
               "cv_auc_std": round(float(cv_churn.std()), 4)},
    "upsell": {"roc_auc": round(auc_u, 4), "pr_auc": round(ap_u, 4),
               "cv_auc_mean": round(float(cv_upsell.mean()), 4),
               "cv_auc_std": round(float(cv_upsell.std()), 4)},
    "dataset": {"n_owners": len(df),
                "churn_rate": round(float(y_churn.mean()), 4),
                "upsell_rate": round(float(y_upsell.mean()), 4)},
}
with open(os.path.join(MODEL_DIR, "metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PLOTS
# ═══════════════════════════════════════════════════════════════════════════════
section("5 / 6  Generating Plots")

# ROC/PR
plot_roc_pr(yc_te, prob_churn,  "Churn Prediction",  RED,  "01_roc_pr_churn.png")
plot_roc_pr(yu_te, prob_upsell, "Upsell Scoring",    BLUE, "02_roc_pr_upsell.png")

# ─ Feature importance (churn) ─────────────────────────────────────────────────
fi = pd.Series(clf_churn.feature_importances_, index=FEATURE_COLS)
fi.index = [FRIENDLY.get(c, c) for c in fi.index]
fi = fi.sort_values(ascending=True).tail(15)

fig, ax = plt.subplots(figsize=(11, 7))
colors = [RED if v >= fi.quantile(0.6) else BLUE for v in fi.values]
bars = ax.barh(fi.index, fi.values, color=colors, height=0.65)
ax.set_xlabel("Feature Importance (gain)")
ax.set_title("Top 15 Features — Churn Classifier", color="white",
             fontsize=13, pad=12)
for bar, val in zip(bars, fi.values):
    ax.text(val + 0.001, bar.get_y() + bar.get_height()/2,
            f"{val:.3f}", va="center", fontsize=9, color=LGRAY)
ax.grid(True, axis="x", alpha=0.3)
plt.tight_layout()
savefig("03_feature_importance.png")

# ─ SHAP beeswarm (churn) ──────────────────────────────────────────────────────
explainer_c = shap.TreeExplainer(clf_churn)
shap_c = explainer_c.shap_values(X_te)

fig, ax = plt.subplots(figsize=(11, 8))
X_te_named = X_te.rename(columns=FRIENDLY)
shap.summary_plot(shap_c, X_te_named, show=False, plot_size=None)
ax = plt.gca()
ax.set_facecolor("#0D1F3C")
ax.figure.set_facecolor(NAVY)
ax.tick_params(colors=LGRAY)
ax.xaxis.label.set_color(LGRAY)
for sp in ax.spines.values():
    sp.set_edgecolor("#1E3A5F")
plt.title("SHAP Values — Churn Classifier", color="white", fontsize=13, pad=12)
plt.tight_layout()
savefig("04_shap_churn.png")

# ─ SHAP beeswarm (upsell) ─────────────────────────────────────────────────────
explainer_u = shap.TreeExplainer(clf_upsell)
shap_u = explainer_u.shap_values(X_te)

fig, ax = plt.subplots(figsize=(11, 8))
shap.summary_plot(shap_u, X_te_named, show=False, plot_size=None)
ax = plt.gca()
ax.set_facecolor("#0D1F3C")
ax.figure.set_facecolor(NAVY)
ax.tick_params(colors=LGRAY)
ax.xaxis.label.set_color(LGRAY)
for sp in ax.spines.values():
    sp.set_edgecolor("#1E3A5F")
plt.title("SHAP Values — Upsell Classifier", color="white", fontsize=13, pad=12)
plt.tight_layout()
savefig("05_shap_upsell.png")

# ─ Confusion matrix ───────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Confusion Matrices", color="white", fontsize=13,
             fontweight="bold", y=1.02)

for ax, (y_t, y_p, ttl) in zip(axes, [
    (yc_te, pred_churn, "Churn Classifier"),
    (yu_te, clf_upsell.predict(X_te), "Upsell Classifier"),
]):
    cm = confusion_matrix(y_t, y_p)
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
                xticklabels=["Predicted 0","Predicted 1"],
                yticklabels=["Actual 0","Actual 1"],
                linewidths=0.5, cbar=False,
                annot_kws={"size": 13, "weight": "bold", "color": "white"})
    ax.set_title(ttl, color="white", pad=8)

plt.tight_layout()
savefig("06_confusion_matrices.png")

# ─ Churn risk segmentation ────────────────────────────────────────────────────
# Score the full dataset and show the risk distribution
prob_all = clf_churn.predict_proba(X)[:, 1]
upsell_all = clf_upsell.predict_proba(X)[:, 1]

tier_map = {1: "1/32", 2: "1/16", 3: "1/8", 4: "1/4"}
df["share_type"] = df["share_tier"].map(tier_map)
df_score = df[["owner_id","owner_name","region","share_type",
               "utilization_rate_12m","complaints_12m",
               "churned_within_12m","upsell_ready","upsell_type"]].copy()
df_score["churn_prob"]  = prob_all.round(4)
df_score["upsell_prob"] = upsell_all.round(4)
df_score["risk_band"] = pd.cut(
    prob_all,
    bins=[-0.001, 0.15, 0.40, 0.70, 1.001],
    labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"]
)

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
fig.suptitle("Owner Risk & Upsell Distribution", color="white",
             fontsize=14, fontweight="bold", y=1.01)

# Churn probability histogram
ax = axes[0]
ax.hist(prob_all[y_churn == 0], bins=30, color=BLUE, alpha=0.8,
        label="Retained", density=True)
ax.hist(prob_all[y_churn == 1], bins=20, color=RED, alpha=0.75,
        label="Churned", density=True)
ax.axvline(0.40, color=AMBER, linestyle="--", lw=1.5, label="Alert threshold")
ax.set_xlabel("Predicted Churn Probability")
ax.set_ylabel("Density")
ax.set_title("Churn Score Distribution", color="white", pad=8)
ax.legend()
ax.grid(True, alpha=0.3)

# Risk band pie
ax = axes[1]
counts = df_score["risk_band"].value_counts().reindex(["LOW","MEDIUM","HIGH","CRITICAL"])
colors_pie = [GREEN, AMBER, "#FF8C42", RED]
wedges, texts, autotexts = ax.pie(
    counts.values, labels=counts.index,
    colors=colors_pie, autopct="%1.0f%%",
    startangle=90, pctdistance=0.75,
    wedgeprops={"edgecolor": NAVY, "linewidth": 2},
)
for t in texts:
    t.set_color(LGRAY)
for at in autotexts:
    at.set_color(NAVY)
    at.set_fontweight("bold")
ax.set_title("Fleet Risk Band Distribution", color="white", pad=8)

plt.tight_layout()
savefig("07_churn_risk_segments.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. DEMO OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════════
section("6 / 6  Generating Demo Outputs")

# ─ At-risk list ───────────────────────────────────────────────────────────────
at_risk = df_score.copy()
at_risk["utilization_rate_12m"] = df["utilization_rate_12m"].round(3)
at_risk["days_since_last_flight"] = df["days_since_last_flight"]
at_risk["tenure_years"] = df["tenure_years"].round(1)
at_risk["avg_satisfaction_score"] = df["avg_satisfaction_score"].round(2)
at_risk["days_until_renewal"] = df["days_until_renewal"]

at_risk_cols = [
    "owner_id", "owner_name", "region", "share_type",
    "tenure_years", "days_until_renewal",
    "utilization_rate_12m", "complaints_12m",
    "days_since_last_flight", "avg_satisfaction_score",
    "churn_prob", "risk_band",
    "churned_within_12m",
]
at_risk_out = at_risk[at_risk_cols].sort_values("churn_prob", ascending=False)
at_risk_out.to_csv(os.path.join(MODEL_DIR, "demo_at_risk.csv"), index=False)

# ─ Upsell pipeline ────────────────────────────────────────────────────────────
upsell_cols = [
    "owner_id", "owner_name", "region", "share_type",
    "upsell_prob", "upsell_type",
    "upsell_ready",
]
upsell_out = at_risk[upsell_cols].sort_values("upsell_prob", ascending=False)
upsell_out.to_csv(os.path.join(MODEL_DIR, "demo_upsell_pipeline.csv"), index=False)

# ─ Console summary ────────────────────────────────────────────────────────────
high_risk = at_risk_out[at_risk_out["risk_band"].isin(["HIGH","CRITICAL"])]
print(f"\n  AT-RISK OWNERS (HIGH + CRITICAL) — top 12:")
print(f"  {'Owner':<22} {'Region':<14} {'Share':<6} "
      f"{'Util%':>6} {'Cmpl':>5} {'Days':>6} {'Churn%':>7} {'Band'}")
print(f"  {'─'*22} {'─'*14} {'─'*6} {'─'*6} {'─'*5} {'─'*6} {'─'*7} {'─'*8}")
for _, r in high_risk.head(12).iterrows():
    print(f"  {r.owner_name:<22} {r.region:<14} {r.share_type:<6} "
          f"{r.utilization_rate_12m*100:>5.0f}% "
          f"{r.complaints_12m:>5} "
          f"{r.days_since_last_flight:>6}d "
          f"{r.churn_prob*100:>6.1f}% "
          f"{str(r.risk_band)}")

print(f"\n  UPSELL PIPELINE — top 10:")
top_up = upsell_out[upsell_out["upsell_prob"] > 0.3].head(10)
print(f"  {'Owner':<22} {'Region':<14} {'Share':<6} "
      f"{'UpsellProb':>10}  {'Type'}")
print(f"  {'─'*22} {'─'*14} {'─'*6} {'─'*10}  {'─'*30}")
for _, r in top_up.iterrows():
    print(f"  {r.owner_name:<22} {r.region:<14} {r.share_type:<6} "
          f"{r.upsell_prob*100:>9.1f}%  {r.upsell_type}")

# Risk band summary
print(f"\n  Risk band distribution ({len(df)} owners):")
for band in ["CRITICAL","HIGH","MEDIUM","LOW"]:
    n = int((df_score["risk_band"] == band).sum())
    bar = "█" * max(1, int(n / len(df) * 50))
    print(f"    {band:<10} {n:>3}  {bar}")


# ── Final summary ──────────────────────────────────────────────────────────────
bar = "═" * 65
print(f"\n{bar}")
print("  TRAINING COMPLETE")
print(bar)
print(f"  Churn  ROC-AUC : {auc_c:.3f}   PR-AUC : {ap_c:.3f}   CV-AUC : {cv_churn.mean():.3f}")
print(f"  Upsell ROC-AUC : {auc_u:.3f}   PR-AUC : {ap_u:.3f}   CV-AUC : {cv_upsell.mean():.3f}")
print(f"\n  Models  → output/churn/model/")
print(f"  Plots   → output/churn/model/plots/")
print(bar)

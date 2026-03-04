"""
PlaneSense Predictive Maintenance — ML Model Training
======================================================
Trains and evaluates three models on the synthetic Atlas Aircraft Center dataset:

  1. XGBoost binary classifier  → failure_within_50h  (CRITICAL alert)
  2. XGBoost binary classifier  → failure_within_100h (AT-RISK alert)
  3. XGBoost regressor          → remaining_useful_life_hours

Outputs (to output/predictive_maintenance/model/):
  - failure_50h_model.json       trained model (XGBoost native format)
  - rul_model.json               trained regressor
  - feature_list.txt             ordered feature list for inference
  - metrics.json                 full evaluation metrics
  - plots/01_roc_pr_curves.png   ROC + Precision-Recall curves
  - plots/02_feature_importance.png
  - plots/03_shap_beeswarm.png
  - plots/04_confusion_matrix.png
  - plots/05_rul_prediction.png
  - demo_predictions.csv         sample predictions on held-out test set
"""

import json
import os
import warnings
warnings.filterwarnings("ignore")

import joblib
import matplotlib
matplotlib.use("Agg")          # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
import seaborn as sns
import shap
import xgboost as xgb
from sklearn.metrics import (
    auc, average_precision_score, classification_report,
    confusion_matrix, mean_absolute_error, mean_squared_error,
    precision_recall_curve, r2_score, roc_auc_score, roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "output", "predictive_maintenance", "data", "ml_features.csv")
MODEL_DIR = os.path.join(BASE_DIR, "output", "predictive_maintenance", "model")
PLOT_DIR  = os.path.join(MODEL_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

# ── Style ─────────────────────────────────────────────────────────────────────
NAVY    = "#0A1628"
BLUE    = "#0A84FF"
AMBER   = "#F5A623"
RED     = "#E63946"
GREEN   = "#52B788"
LGRAY   = "#E8EDF4"
plt.rcParams.update({
    "figure.facecolor":  NAVY,
    "axes.facecolor":    "#0D1F3C",
    "axes.edgecolor":    "#1E3A5F",
    "axes.labelcolor":   LGRAY,
    "xtick.color":       LGRAY,
    "ytick.color":       LGRAY,
    "text.color":        LGRAY,
    "grid.color":        "#1E3A5F",
    "grid.linestyle":    "--",
    "grid.linewidth":    0.5,
    "legend.facecolor":  "#0D1F3C",
    "legend.edgecolor":  "#1E3A5F",
    "font.family":       "DejaVu Sans",
    "font.size":         11,
})

# ── Feature definition ────────────────────────────────────────────────────────
FEATURE_COLS = [
    # Wear
    "hours_since_install", "cycles_since_install",
    "wear_pct_hours", "wear_pct_cycles", "wear_pct_max",
    # Sensor – 30-day aggregates
    "avg_vibration_30d", "max_vibration_30d", "vibration_std_30d",
    "avg_egt_30d", "max_egt_30d",
    "avg_oil_pressure_30d", "min_oil_pressure_30d",
    "avg_oil_temp_30d",
    "avg_anomaly_score_30d", "max_anomaly_score_30d",
    # Operational
    "flights_last_30d", "total_flight_hours_30d",
    "avg_route_roughness_30d", "unscheduled_events_12m",
    # Aircraft context
    "aircraft_age_years", "is_pc24",
]

FRIENDLY_NAMES = {
    "wear_pct_max":             "Wear % (max)",
    "unscheduled_events_12m":   "Unscheduled events (12m)",
    "max_anomaly_score_30d":    "Max anomaly score (30d)",
    "min_oil_pressure_30d":     "Min oil pressure (30d)",
    "max_vibration_30d":        "Max vibration (30d)",
    "avg_vibration_30d":        "Avg vibration (30d)",
    "wear_pct_hours":           "Wear % by hours",
    "wear_pct_cycles":          "Wear % by cycles",
    "hours_since_install":      "Hours since install",
    "cycles_since_install":     "Cycles since install",
    "avg_anomaly_score_30d":    "Avg anomaly score (30d)",
    "avg_egt_30d":              "Avg EGT °C (30d)",
    "max_egt_30d":              "Max EGT °C (30d)",
    "avg_oil_pressure_30d":     "Avg oil pressure (30d)",
    "avg_oil_temp_30d":         "Avg oil temp (30d)",
    "vibration_std_30d":        "Vibration std dev (30d)",
    "flights_last_30d":         "Flights last 30d",
    "total_flight_hours_30d":   "Flight hours last 30d",
    "avg_route_roughness_30d":  "Avg route roughness (30d)",
    "aircraft_age_years":       "Aircraft age (years)",
    "is_pc24":                  "PC-24 (vs PC-12)",
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def savefig(name: str):
    path = os.path.join(PLOT_DIR, name)
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=NAVY)
    plt.close()
    print(f"    saved → {os.path.relpath(path, BASE_DIR)}")


def section(title: str):
    bar = "─" * 65
    print(f"\n{bar}\n  {title}\n{bar}")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOAD & PREPARE DATA
# ═══════════════════════════════════════════════════════════════════════════════
section("1 / 6  Loading & Preparing Data")

df = pd.read_csv(DATA_PATH)
print(f"  Dataset: {len(df):,} rows × {len(df.columns)} cols")
print(f"  fail_50h  positive rate : {df.failure_within_50h.mean():.1%}")
print(f"  fail_100h positive rate : {df.failure_within_100h.mean():.1%}")
print(f"  RUL range               : {df.remaining_useful_life_hours.min():.0f} – "
      f"{df.remaining_useful_life_hours.max():.0f} h")

X = df[FEATURE_COLS].copy()
y50  = df["failure_within_50h"]
y100 = df["failure_within_100h"]
y_rul = df["remaining_useful_life_hours"]

# 80/20 stratified split (stratify on primary target)
X_train, X_test, y50_train, y50_test, y100_train, y100_test, yrul_train, yrul_test = \
    train_test_split(X, y50, y100, y_rul, test_size=0.20,
                     random_state=42, stratify=y50)

print(f"  Train: {len(X_train):,}  |  Test: {len(X_test):,}")
print(f"  Test positives (50h): {y50_test.sum()} / {len(y50_test)}")

# Save feature list for inference
with open(os.path.join(MODEL_DIR, "feature_list.txt"), "w") as f:
    f.write("\n".join(FEATURE_COLS))


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TRAIN CLASSIFIERS
# ═══════════════════════════════════════════════════════════════════════════════
section("2 / 6  Training XGBoost Classifiers")

# Class imbalance weight for fail_50h
pos50  = y50_train.sum()
neg50  = len(y50_train) - pos50
spw50  = neg50 / pos50
pos100 = y100_train.sum()
neg100 = len(y100_train) - pos100
spw100 = neg100 / pos100

XGB_CLF_PARAMS = dict(
    n_estimators      = 400,
    max_depth         = 5,
    learning_rate     = 0.05,
    subsample         = 0.85,
    colsample_bytree  = 0.80,
    min_child_weight  = 3,
    reg_alpha         = 0.1,
    reg_lambda        = 1.0,
    eval_metric       = "aucpr",
    random_state      = 42,
    n_jobs            = -1,
    verbosity         = 0,
)

# --- Classifier 1: failure_within_50h ---
clf50 = xgb.XGBClassifier(scale_pos_weight=spw50, **XGB_CLF_PARAMS)
clf50.fit(X_train, y50_train,
          eval_set=[(X_test, y50_test)], verbose=False)

# 5-fold cross-validation AUC (on full dataset)
cv_auc50 = cross_val_score(
    xgb.XGBClassifier(scale_pos_weight=spw50, **XGB_CLF_PARAMS),
    X, y50, cv=StratifiedKFold(5, shuffle=True, random_state=42),
    scoring="roc_auc", n_jobs=-1
)
print(f"  fail_50h  CV AUC : {cv_auc50.mean():.3f} ± {cv_auc50.std():.3f}")

# --- Classifier 2: failure_within_100h ---
clf100 = xgb.XGBClassifier(scale_pos_weight=spw100, **XGB_CLF_PARAMS)
clf100.fit(X_train, y100_train,
           eval_set=[(X_test, y100_test)], verbose=False)

cv_auc100 = cross_val_score(
    xgb.XGBClassifier(scale_pos_weight=spw100, **XGB_CLF_PARAMS),
    X, y100, cv=StratifiedKFold(5, shuffle=True, random_state=42),
    scoring="roc_auc", n_jobs=-1
)
print(f"  fail_100h CV AUC : {cv_auc100.mean():.3f} ± {cv_auc100.std():.3f}")

# ─ Save models ────────────────────────────────────────────────────────────────
clf50.save_model(os.path.join(MODEL_DIR, "failure_50h_model.json"))
clf100.save_model(os.path.join(MODEL_DIR, "failure_100h_model.json"))


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TRAIN RUL REGRESSOR
# ═══════════════════════════════════════════════════════════════════════════════
section("3 / 6  Training RUL Regressor")

XGB_REG_PARAMS = dict(
    n_estimators     = 400,
    max_depth        = 5,
    learning_rate    = 0.05,
    subsample        = 0.85,
    colsample_bytree = 0.80,
    min_child_weight = 3,
    reg_alpha        = 0.1,
    reg_lambda       = 1.0,
    objective        = "reg:squarederror",
    random_state     = 42,
    n_jobs           = -1,
    verbosity        = 0,
)

# Log-transform RUL to handle skew (add 1 to avoid log(0))
yrul_train_log = np.log1p(yrul_train)
yrul_test_log  = np.log1p(yrul_test)

reg_rul = xgb.XGBRegressor(**XGB_REG_PARAMS)
reg_rul.fit(X_train, yrul_train_log,
            eval_set=[(X_test, yrul_test_log)], verbose=False)

rul_pred_log = reg_rul.predict(X_test)
rul_pred     = np.expm1(rul_pred_log)          # back to original scale

mae  = mean_absolute_error(yrul_test, rul_pred)
rmse = mean_squared_error(yrul_test, rul_pred) ** 0.5
r2   = r2_score(yrul_test, rul_pred)
print(f"  RUL MAE  : {mae:.1f} h")
print(f"  RUL RMSE : {rmse:.1f} h")
print(f"  RUL R²   : {r2:.3f}")

reg_rul.save_model(os.path.join(MODEL_DIR, "rul_model.json"))


# ═══════════════════════════════════════════════════════════════════════════════
# 4. EVALUATE CLASSIFIERS
# ═══════════════════════════════════════════════════════════════════════════════
section("4 / 6  Evaluating Models")

prob50  = clf50.predict_proba(X_test)[:, 1]
prob100 = clf100.predict_proba(X_test)[:, 1]
pred50  = clf50.predict(X_test)
pred100 = clf100.predict(X_test)

# AUC metrics
auc50  = roc_auc_score(y50_test,  prob50)
auc100 = roc_auc_score(y100_test, prob100)
ap50   = average_precision_score(y50_test,  prob50)
ap100  = average_precision_score(y100_test, prob100)

print(f"  fail_50h   ROC-AUC={auc50:.3f}   PR-AUC={ap50:.3f}")
print(f"  fail_100h  ROC-AUC={auc100:.3f}   PR-AUC={ap100:.3f}")
print()
print("  fail_50h classification report:")
print(classification_report(y50_test, pred50,
                             target_names=["Healthy", "Critical"],
                             digits=3))

metrics = {
    "failure_50h":  {"roc_auc": round(auc50,  4), "pr_auc": round(ap50,  4),
                     "cv_auc_mean": round(cv_auc50.mean(),  4),
                     "cv_auc_std":  round(cv_auc50.std(),   4)},
    "failure_100h": {"roc_auc": round(auc100, 4), "pr_auc": round(ap100, 4),
                     "cv_auc_mean": round(cv_auc100.mean(), 4),
                     "cv_auc_std":  round(cv_auc100.std(),  4)},
    "rul_regressor": {"mae": round(mae, 1), "rmse": round(rmse, 1),
                      "r2": round(r2, 4)},
    "dataset": {"n_train": len(X_train), "n_test": len(X_test),
                "fail_50h_rate": round(float(y50.mean()), 4),
                "fail_100h_rate": round(float(y100.mean()), 4)},
}
with open(os.path.join(MODEL_DIR, "metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PLOTS
# ═══════════════════════════════════════════════════════════════════════════════
section("5 / 6  Generating Plots")

# ─ PLOT 1: ROC + PR curves ────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
fig.suptitle("Predictive Maintenance — Model Performance",
             color="white", fontsize=14, fontweight="bold", y=1.01)

for ax, (y_true, prob, label, color) in zip(
    axes,
    [(y50_test,  prob50,  "fail_50h  (CRITICAL)",   BLUE),
     (y100_test, prob100, "fail_100h (AT-RISK)",    AMBER)],
):
    fpr, tpr, _ = roc_curve(y_true, prob)
    roc_auc_val = auc(fpr, tpr)
    ax.plot(fpr, tpr, color=color, lw=2.5,
            label=f"ROC AUC = {roc_auc_val:.3f}")
    ax.plot([0,1],[0,1], "--", color="#3A5A80", lw=1)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(f"ROC Curve — {label}", color="white", pad=8)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)

plt.tight_layout()
savefig("01_roc_curves.png")

# PR curves
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
fig.suptitle("Precision-Recall Curves", color="white",
             fontsize=14, fontweight="bold", y=1.01)
for ax, (y_true, prob, label, color) in zip(
    axes,
    [(y50_test,  prob50,  "fail_50h  (CRITICAL)", BLUE),
     (y100_test, prob100, "fail_100h (AT-RISK)", AMBER)],
):
    prec, rec, _ = precision_recall_curve(y_true, prob)
    ap_val = average_precision_score(y_true, prob)
    baseline = y_true.mean()
    ax.plot(rec, prec, color=color, lw=2.5, label=f"AP = {ap_val:.3f}")
    ax.axhline(baseline, linestyle="--", color="#3A5A80", lw=1,
               label=f"Baseline = {baseline:.2f}")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(f"PR Curve — {label}", color="white", pad=8)
    ax.legend()
    ax.grid(True, alpha=0.3)

plt.tight_layout()
savefig("01b_pr_curves.png")

# ─ PLOT 2: Feature importance ─────────────────────────────────────────────────
fi = pd.Series(clf50.feature_importances_, index=FEATURE_COLS)
fi.index = [FRIENDLY_NAMES.get(c, c) for c in fi.index]
fi = fi.sort_values(ascending=True).tail(15)

fig, ax = plt.subplots(figsize=(10, 7))
colors = [RED if v >= fi.quantile(0.7) else BLUE for v in fi.values]
bars = ax.barh(fi.index, fi.values, color=colors, height=0.65)
ax.set_xlabel("Feature Importance (gain)")
ax.set_title("Top 15 Features — failure_within_50h Classifier",
             color="white", fontsize=13, pad=12)
for bar, val in zip(bars, fi.values):
    ax.text(val + 0.001, bar.get_y() + bar.get_height()/2,
            f"{val:.3f}", va="center", fontsize=9, color=LGRAY)
ax.grid(True, axis="x", alpha=0.3)
plt.tight_layout()
savefig("02_feature_importance.png")

# ─ PLOT 3: SHAP beeswarm ──────────────────────────────────────────────────────
explainer = shap.TreeExplainer(clf50)
shap_vals  = explainer.shap_values(X_test)

fig, ax = plt.subplots(figsize=(10, 8))
# Replace feature names with friendly names for SHAP plot
X_test_named = X_test.rename(columns=FRIENDLY_NAMES)
shap.summary_plot(shap_vals, X_test_named, show=False,
                  plot_size=None, color_bar=True)
ax = plt.gca()
ax.set_facecolor("#0D1F3C")
ax.figure.set_facecolor(NAVY)
ax.tick_params(colors=LGRAY)
ax.xaxis.label.set_color(LGRAY)
for spine in ax.spines.values():
    spine.set_edgecolor("#1E3A5F")
plt.title("SHAP Feature Impact — failure_within_50h",
          color="white", fontsize=13, pad=12)
plt.tight_layout()
savefig("03_shap_beeswarm.png")

# ─ PLOT 4: Confusion matrix ───────────────────────────────────────────────────
cm = confusion_matrix(y50_test, pred50)
fig, ax = plt.subplots(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=["Predicted Healthy", "Predicted Critical"],
            yticklabels=["Actual Healthy", "Actual Critical"],
            linewidths=0.5, ax=ax, cbar=False,
            annot_kws={"size": 14, "weight": "bold", "color": "white"})
ax.set_title("Confusion Matrix — failure_within_50h", color="white",
             fontsize=13, pad=12)
ax.xaxis.label.set_color(LGRAY)
ax.yaxis.label.set_color(LGRAY)
plt.tight_layout()
savefig("04_confusion_matrix.png")

# ─ PLOT 5: RUL actual vs predicted ───────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
fig.suptitle("Remaining Useful Life — Regressor Performance",
             color="white", fontsize=14, fontweight="bold", y=1.01)

ax = axes[0]
lim = max(yrul_test.max(), rul_pred.max()) * 1.05
ax.scatter(yrul_test, rul_pred, alpha=0.5, s=20, color=BLUE,
           edgecolors="none")
ax.plot([0, lim], [0, lim], "--", color=AMBER, lw=1.5, label="Perfect")
ax.set_xlabel("Actual RUL (hours)")
ax.set_ylabel("Predicted RUL (hours)")
ax.set_title(f"Actual vs Predicted  |  R²={r2:.3f}",
             color="white", pad=8)
ax.legend()
ax.grid(True, alpha=0.3)

ax = axes[1]
residuals = rul_pred - yrul_test.values
ax.hist(residuals, bins=40, color=BLUE, edgecolor="none", alpha=0.8)
ax.axvline(0, color=AMBER, linestyle="--", lw=1.5)
ax.set_xlabel("Prediction Error (predicted − actual)")
ax.set_ylabel("Count")
ax.set_title(f"Residual Distribution  |  MAE={mae:.0f}h  RMSE={rmse:.0f}h",
             color="white", pad=8)
ax.grid(True, alpha=0.3)

plt.tight_layout()
savefig("05_rul_prediction.png")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. DEMO PREDICTIONS
# ═══════════════════════════════════════════════════════════════════════════════
section("6 / 6  Generating Demo Predictions")

# Score entire test set with risk labels
test_results = X_test.copy()
test_results["tail_number"]    = df.loc[X_test.index, "tail_number"].values
test_results["component_name"] = df.loc[X_test.index, "component_name"].values
test_results["aircraft_model"] = df.loc[X_test.index, "aircraft_model"].values
test_results["actual_fail_50h"]  = y50_test.values
test_results["actual_fail_100h"] = y100_test.values
test_results["actual_rul"]       = yrul_test.values
test_results["pred_prob_critical"]  = prob50.round(4)
test_results["pred_prob_at_risk"]   = prob100.round(4)
test_results["pred_rul_hours"]      = rul_pred.round(1)
test_results["alert_level"] = pd.cut(
    prob50,
    bins=[-0.001, 0.20, 0.50, 0.80, 1.001],
    labels=["HEALTHY", "WATCH", "WARNING", "CRITICAL"]
)

# Save demo predictions
demo_cols = [
    "tail_number", "component_name", "aircraft_model",
    "wear_pct_max", "max_vibration_30d", "max_anomaly_score_30d",
    "unscheduled_events_12m", "min_oil_pressure_30d",
    "pred_prob_critical", "pred_prob_at_risk", "pred_rul_hours",
    "alert_level",
    "actual_fail_50h", "actual_fail_100h", "actual_rul",
]
demo_df = test_results[demo_cols].sort_values("pred_prob_critical", ascending=False)
demo_df.to_csv(os.path.join(MODEL_DIR, "demo_predictions.csv"), index=False)

# Print top CRITICAL components
top = demo_df.head(10)
print(f"\n  {'Tail':<10} {'Component':<30} {'Wear%':>6} {'RiskProb':>9} "
      f"{'PredRUL':>9} {'Alert':<10}")
print(f"  {'─'*10} {'─'*30} {'─'*6} {'─'*9} {'─'*9} {'─'*10}")
for _, r in top.iterrows():
    print(f"  {r.tail_number:<10} {r.component_name:<30} "
          f"{r.wear_pct_max:>5.1f}% "
          f"{r.pred_prob_critical:>9.3f} "
          f"{r.pred_rul_hours:>8.0f}h "
          f"{str(r.alert_level):<10}")

# Alert summary
alert_counts = demo_df["alert_level"].value_counts()
print(f"\n  Alert summary (test set, {len(demo_df)} components):")
for level in ["CRITICAL", "WARNING", "WATCH", "HEALTHY"]:
    n = alert_counts.get(level, 0)
    bar = "█" * int(n / len(demo_df) * 40)
    print(f"    {level:<10} {n:>3}  {bar}")


# ── Summary ────────────────────────────────────────────────────────────────────
bar = "═" * 65
print(f"\n{bar}")
print("  TRAINING COMPLETE")
print(bar)
print(f"  fail_50h  ROC-AUC  : {auc50:.3f}   PR-AUC : {ap50:.3f}")
print(f"  fail_100h ROC-AUC  : {auc100:.3f}   PR-AUC : {ap100:.3f}")
print(f"  RUL       R²       : {r2:.3f}   MAE    : {mae:.0f} h")
print(f"\n  Models saved to    : output/predictive_maintenance/model/")
print(f"  Plots saved to     : output/predictive_maintenance/model/plots/")
print(bar)

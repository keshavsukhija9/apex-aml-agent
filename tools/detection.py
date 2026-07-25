"""
Anomaly & Detection Tool.
Rule Engine (primary): FinCEN 31 CFR 1010.311 threshold-based structuring detection.
ML Layer (fallback): IsolationForest on engineered features, for queries that
  explicitly request ML-based anomaly detection (per planner's requires_ml flag).

Explainability note: we do NOT use SHAP (deliberately de-risked per architecture
review -- IsolationForest + SHAP KernelExplainer is brittle and slow). Instead we
report which engineered features deviate most from the population norm ("deviation
drivers"), which is honest about what it is: a statistical deviation summary, not
a formal SHAP attribution.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest


STRUCTURING_STATUTE = "31 CFR 1010.311 (Currency Transaction Report threshold evasion)"
LAYERING_STATUTE = "31 CFR 1010.311 (layering indicator, FATF Recommendation 10)"

# Rule thresholds -- tuned against the planted ground truth in Step 2
RULE_MIN_ROLLING_COUNT = 5          # sub-$10k txns within 24h to flag structuring
RULE_MIN_ROLLING_SUM = 30000.0      # cumulative sub-$10k sum within 24h


def apply_structuring_rules(customer_summary: dict) -> dict:
    """
    Deterministic rule check against FinCEN-style thresholds.
    customer_summary comes from tools.feature_eng.get_customer_summary().
    """
    count = customer_summary.get("max_rolling_24h_sub_threshold_count", 0)
    amount_sum = customer_summary.get("max_rolling_24h_sub_threshold_sum", 0.0)

    triggered = count >= RULE_MIN_ROLLING_COUNT and amount_sum >= RULE_MIN_ROLLING_SUM

    return {
        "rule_triggered": triggered,
        "rule_name": "sub_threshold_clustering" if triggered else None,
        "statute_reference": STRUCTURING_STATUTE if triggered else None,
        "trigger_detail": (
            f"{count} sub-$10,000 transactions totaling ${amount_sum:,.2f} "
            f"within a 24-hour window (threshold: >= {RULE_MIN_ROLLING_COUNT} txns, "
            f">= ${RULE_MIN_ROLLING_SUM:,.0f})"
            if triggered
            else f"{count} sub-threshold txns / ${amount_sum:,.2f} -- below rule threshold"
        ),
    }


def apply_layering_rule(graph_result: dict) -> dict:
    """Wraps the graph engine's layering detection result into rule-style output."""
    triggered = graph_result.get("is_layering_intermediate", False)
    return {
        "rule_triggered": triggered,
        "rule_name": "multi_hop_layering" if triggered else None,
        "statute_reference": LAYERING_STATUTE if triggered else None,
        "trigger_detail": graph_result.get("reason", "no graph analysis performed"),
        "hop_trace": graph_result.get("hop_trace", []),
    }


def build_ml_training_matrix(df_featured: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Aggregate per-customer features into a matrix suitable for IsolationForest.
    One row per customer, not per transaction -- we're profiling customer behavior.
    """
    feature_cols = [
        "rolling_24h_sub_threshold_count",
        "rolling_24h_sub_threshold_sum",
    ]

    agg = df_featured.groupby("customer_id").agg(
        max_rolling_count=("rolling_24h_sub_threshold_count", "max"),
        max_rolling_sum=("rolling_24h_sub_threshold_sum", "max"),
        min_velocity=("velocity_minutes", lambda x: x.replace(np.inf, np.nan).min()),
        txn_count=("amount", "count"),
        mean_amount=("amount", "mean"),
    ).reset_index()

    agg["min_velocity"] = agg["min_velocity"].fillna(agg["min_velocity"].max())

    matrix_cols = ["max_rolling_count", "max_rolling_sum", "min_velocity", "txn_count", "mean_amount"]
    return agg, matrix_cols


def run_isolation_forest(df_featured: pd.DataFrame, contamination: float = 0.05) -> pd.DataFrame:
    """
    Fits IsolationForest on aggregated per-customer features.
    Returns a DataFrame with customer_id, anomaly_score, is_anomaly, and
    deviation_drivers (the cheap SHAP replacement: which features are furthest
    from the population mean, in standard deviations).
    """
    agg, matrix_cols = build_ml_training_matrix(df_featured)

    X = agg[matrix_cols].to_numpy()

    model = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
    predictions = model.fit_predict(X)  # -1 = anomaly, 1 = normal
    scores = model.decision_function(X)  # lower = more anomalous

    agg["is_anomaly"] = predictions == -1
    agg["anomaly_score"] = scores

    # Deviation drivers: z-score of each feature against the population, per customer
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds[stds == 0] = 1.0  # avoid div-by-zero for constant columns
    zscores = (X - means) / stds

    deviation_drivers = []
    for row in zscores:
        # top-2 features by absolute z-score deviation
        top_idx = np.argsort(-np.abs(row))[:2]
        drivers = [
            {"feature": matrix_cols[i], "zscore": round(float(row[i]), 2)}
            for i in top_idx
        ]
        deviation_drivers.append(drivers)

    agg["deviation_drivers"] = deviation_drivers

    return agg[["customer_id", "is_anomaly", "anomaly_score", "deviation_drivers"]]


def get_ml_result_for_customer(ml_results: pd.DataFrame, customer_id: int) -> dict:
    """Look up a single customer's ML result from the fitted IsolationForest output."""
    row = ml_results[ml_results["customer_id"] == customer_id]
    if row.empty:
        return {
            "is_anomaly": False,
            "anomaly_score": None,
            "deviation_drivers": [],
            "note": "customer not present in ML training population",
        }
    r = row.iloc[0]
    return {
        "is_anomaly": bool(r["is_anomaly"]),
        "anomaly_score": round(float(r["anomaly_score"]), 4),
        "deviation_drivers": r["deviation_drivers"],
    }

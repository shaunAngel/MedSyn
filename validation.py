"""
validation.py — Quality, privacy, missingness similarity, and TSTR wrappers.
"""

from typing import Dict, Any
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score


def _eval_slice(df: pd.DataFrame) -> pd.DataFrame:
    if "month" in df.columns and 6 in df["month"].values:
        return df[df["month"] == 6]
    if "patient_id" in df.columns:
        return df.drop_duplicates(subset=["patient_id"])
    return df


def _patient_slice(df: pd.DataFrame) -> pd.DataFrame:
    if "month" in df.columns and 1 in df["month"].values:
        return df[df["month"] == 1]
    if "patient_id" in df.columns:
        return df.drop_duplicates(subset=["patient_id"])
    return df


def compute_quality_metrics(source_df: pd.DataFrame, generated_df: pd.DataFrame) -> Dict[str, Any]:
    src_eval = _eval_slice(source_df)
    gen_eval = _eval_slice(generated_df)

    num_cols = [
        c for c in ["age", "systolic_bp", "activity_steps", "medication_adherence_pct", "pain_score"]
        if c in src_eval.columns and c in gen_eval.columns
    ]

    shape_scores = {}
    for col in num_cols:
        s_vals = src_eval[col].dropna().values
        g_vals = gen_eval[col].dropna().values
        if len(s_vals) == 0 or len(g_vals) == 0:
            continue
        w_dist = stats.wasserstein_distance(s_vals, g_vals)
        col_range = max(1.0, float(s_vals.max() - s_vals.min()))
        sim = max(0.0, 1.0 - (w_dist / col_range))
        shape_scores[col] = round(sim * 100.0, 1)

    overall_shape_score = round(float(np.mean(list(shape_scores.values()))), 1) if shape_scores else None

    ref_pairs = [
        ("activity_steps", "pain_score", "Activity ↔ Pain", -0.56),
        ("medication_adherence_pct", "pain_score", "Adherence ↔ Pain", -0.30),
        ("age", "systolic_bp", "Age ↔ BP", 0.54),
        ("diabetic", "systolic_bp", "Diabetic ↔ BP", 0.50),
    ]

    associations_table = []
    for var1, var2, label, expected_ref in ref_pairs:
        if not all(v in src_eval.columns and v in gen_eval.columns for v in (var1, var2)):
            continue
        s_corr = src_eval[var1].corr(src_eval[var2])
        g_corr = gen_eval[var1].corr(gen_eval[var2])
        if pd.isna(s_corr) or pd.isna(g_corr):
            continue
        s_val = round(float(s_corr), 2)
        g_val = round(float(g_corr), 2)
        diff = round(abs(g_val - s_val), 2)
        associations_table.append({
            "relationship": label,
            "source_correlation": s_val,
            "synthetic_correlation": g_val,
            "difference": diff,
            "expected_reference": expected_ref,
            "status": "PRESERVED" if diff <= 0.15 else "MODERATELY SHIFTED",
        })

    mean_corr_diff = None
    if num_cols:
        src_corr_mat = src_eval[num_cols].corr()
        gen_corr_mat = gen_eval[num_cols].corr()
        corr_diff_mat = (src_corr_mat - gen_corr_mat).abs()
        mean_corr_diff = round(float(corr_diff_mat.mean().mean()), 3)

    return {
        "overall_quality_score": overall_shape_score,
        "column_shape_similarity": shape_scores,
        "associations_table": associations_table,
        "mean_correlation_difference": mean_corr_diff,
        "scientific_label": "Observed statistical associations, not causal relationships.",
    }


def compute_privacy_metrics(source_df: pd.DataFrame, generated_df: pd.DataFrame) -> Dict[str, Any]:
    """Distance-to-closest-record. Always returns a number plus a label."""
    src = _patient_slice(source_df)
    gen = _patient_slice(generated_df)
    match_cols = [
        c for c in ["age", "diabetic", "systolic_bp", "activity_steps", "medication_adherence_pct", "pain_score"]
        if c in src.columns and c in gen.columns
    ]
    src_clean = src[match_cols].dropna()
    gen_clean = gen[match_cols].dropna()
    if len(src_clean) < 5 or len(gen_clean) < 5:
        return {
            "label": None,
            "metric_name": "distance_to_closest_record",
            "value": None,
            "available": False,
            "interpretation": "Not available.",
            "limitation": "Insufficient complete records for a nearest-neighbor privacy diagnostic.",
        }

    if len(gen_clean) > 4000:
        gen_clean = gen_clean.sample(4000, random_state=42)

    scaler = StandardScaler()
    X_src = scaler.fit_transform(src_clean.values)
    X_gen = scaler.transform(gen_clean.values)
    nn = NearestNeighbors(n_neighbors=1, metric="euclidean")
    nn.fit(X_src)
    distances, _ = nn.kneighbors(X_gen)
    dcr_values = distances.flatten()

    mean_dcr = round(float(np.mean(dcr_values)), 3)
    p5_dcr = round(float(np.percentile(dcr_values, 5)), 3)
    min_dcr = round(float(np.min(dcr_values)), 3)

    if p5_dcr > 0.15 and min_dcr > 0.01:
        risk_label = "LOW"
        interpretation = (
            f"Mean nearest-neighbor distance ({mean_dcr:.2f}σ) and 5th percentile ({p5_dcr:.2f}σ) "
            "are well above identity-duplication thresholds. No exact patient clones identified in this diagnostic."
        )
    elif min_dcr > 0.001:
        risk_label = "MODERATE"
        interpretation = (
            f"Proximity analysis indicates moderate separation ({mean_dcr:.2f}σ mean, {p5_dcr:.2f}σ 5th pct)."
        )
    else:
        risk_label = "ELEVATED"
        interpretation = (
            f"Proximity analysis detected potential near-duplicates (min distance = {min_dcr:.4f}σ)."
        )

    return {
        "label": risk_label,
        "metric_name": "distance_to_closest_record",
        "value": mean_dcr,
        "p5_dcr": p5_dcr,
        "min_dcr": min_dcr,
        "available": True,
        "interpretation": interpretation,
        "limitation": "This is a distance-based similarity diagnostic, not a formal guarantee of anonymity or differential privacy.",
    }


def compute_missingness_similarity(source_df: pd.DataFrame, generated_df: pd.DataFrame) -> Dict[str, Any]:
    table = []
    for col in source_df.columns:
        if col not in generated_df.columns:
            continue
        s_pct = round(float(source_df[col].isna().mean() * 100), 1)
        g_pct = round(float(generated_df[col].isna().mean() * 100), 1)
        table.append({
            "column": col,
            "source_missing_pct": s_pct,
            "synthetic_missing_pct": g_pct,
            "delta": round(g_pct - s_pct, 1),
        })
    return {"missingness_table": table, "available": True}


def compute_tstr(source_df: pd.DataFrame, generated_df: pd.DataFrame, target_col: str = "systolic_bp") -> Dict[str, Any]:
    feature_cols = [
        c for c in ["age", "diabetic", "activity_steps", "medication_adherence_pct", "pain_score"]
        if c in source_df.columns and c in generated_df.columns and c != target_col
    ]
    if not feature_cols or target_col not in source_df.columns or target_col not in generated_df.columns:
        return {"available": False, "message": "Not available."}

    src_clean = source_df[feature_cols + [target_col]].dropna()
    gen_clean = generated_df[feature_cols + [target_col]].dropna()
    if len(src_clean) < 50 or len(gen_clean) < 50:
        return {"available": False, "message": "Not available. Sample size insufficient for held-out TSTR evaluation."}

    X_real_train, X_real_test, y_real_train, y_real_test = train_test_split(
        src_clean[feature_cols], src_clean[target_col], test_size=0.30, random_state=42
    )
    model_trtr = Ridge(alpha=1.0)
    model_trtr.fit(X_real_train, y_real_train)
    r2_trtr = float(r2_score(y_real_test, model_trtr.predict(X_real_test)))

    model_tstr = Ridge(alpha=1.0)
    model_tstr.fit(gen_clean[feature_cols], gen_clean[target_col])
    r2_tstr = float(r2_score(y_real_test, model_tstr.predict(X_real_test)))

    if r2_trtr <= 0.01:
        return {
            "available": True,
            "target_variable": target_col,
            "trtr_baseline_r2": round(r2_trtr, 3),
            "tstr_synthetic_r2": round(r2_tstr, 3),
            "utility_retention_pct": None,
            "interpretation": "TRTR baseline R² is near zero; utility retention is not reported.",
        }

    utility_retention = round((max(0.0, r2_tstr) / r2_trtr) * 100.0, 1)
    return {
        "available": True,
        "target_variable": target_col,
        "trtr_baseline_r2": round(r2_trtr, 3),
        "tstr_synthetic_r2": round(max(0.0, r2_tstr), 3),
        "utility_retention_pct": utility_retention,
        "interpretation": (
            f"A model trained only on synthetic data retains {utility_retention}% of real-data "
            f"predictive R² on held-out source records for {target_col}."
        ),
    }

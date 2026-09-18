"""
shift.py — Population Shift analysis and Target Achievement module for Cohortly.
Contract:
- compute_population_shift(source_df, request: dict, generated_df) -> pd.DataFrame
- target_achievement(request: dict, generated_df) -> dict
"""

from typing import Dict, Any
import pandas as pd


def _patient_frame(df: pd.DataFrame) -> pd.DataFrame:
    """One row per patient, using min adherence across the trajectory when present."""
    if df.empty:
        return df
    if "patient_id" not in df.columns:
        return df.copy()

    agg: Dict[str, str] = {}
    for col in df.columns:
        if col == "patient_id":
            continue
        if col == "month":
            continue
        if "adher" in col.lower():
            agg[col] = "min"
        else:
            agg[col] = "first"
    return df.groupby("patient_id", as_index=False).agg(agg)


def _eval_condition_pct(df: pd.DataFrame, cond: dict) -> float:
    """Percentage of patients (or rows) that meet the condition."""
    if df.empty:
        return 0.0

    var = cond.get("variable", "")
    op = cond.get("operator", "==")
    val = cond.get("value", 1)

    target_df = _patient_frame(df)
    if var not in target_df.columns:
        return 0.0

    series = target_df[var]
    n = len(target_df)
    if n == 0:
        return 0.0

    if op == "==":
        mask = series == val
    elif op == ">":
        mask = series > float(val)
    elif op == ">=":
        mask = series >= float(val)
    elif op == "<":
        mask = series < float(val)
    elif op == "<=":
        mask = series <= float(val)
    elif op == "!=":
        mask = series != val
    else:
        mask = series == val

    return round(float(mask.fillna(False).sum() / n * 100), 1)


def compute_population_shift(source_df: pd.DataFrame, request: dict, generated_df: pd.DataFrame) -> pd.DataFrame:
    """Returns [variable, source_pct, target_pct, generated_pct] — Population Shift, not Cohort Drift."""
    conditions = request.get("conditions", [])
    rows = []

    for cond in conditions:
        var = cond.get("variable", "")
        op = cond.get("operator", "==")
        val = cond.get("value", 1)
        target_pct = float(cond.get("target_pct", 0.0))
        label = f"{var} {op} {val}" if op != "==" or val != 1 else var.capitalize()

        rows.append({
            "variable": label,
            "source_pct": _eval_condition_pct(source_df, cond),
            "target_pct": target_pct,
            "generated_pct": _eval_condition_pct(generated_df, cond),
        })

    return pd.DataFrame(rows)


def target_achievement(request: dict, generated_df: pd.DataFrame) -> Dict[str, Any]:
    """Returns {variable: {'target', 'generated', 'achieved'}} — achieved if within 2 pp."""
    result = {}
    for cond in request.get("conditions", []):
        var = cond.get("variable", "")
        target_pct = float(cond.get("target_pct", 0.0))
        generated_pct = _eval_condition_pct(generated_df, cond)
        result[var] = {
            "target": target_pct,
            "generated": generated_pct,
            "achieved": abs(target_pct - generated_pct) <= 2.0,
            "delta": round(generated_pct - target_pct, 1),
        }
    return result

"""Mechanical data-quality checks for generated patient data."""

from __future__ import annotations

from typing import Any

import pandas as pd

_RANGE_COLUMNS = ("age", "systolic_bp", "pain_score")
_NON_NEGATIVE_COLUMNS = ("age", "systolic_bp", "activity_steps", "medication_adherence_pct", "pain_score")


def _result(passed: bool, detail: str) -> dict[str, Any]:
    return {"passed": bool(passed), "detail": str(detail)}


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")


def run_sanity_checks(generated_df: pd.DataFrame, schema: dict, source_df: pd.DataFrame) -> dict:
    """Run mechanical checks; these do not establish clinical validity."""
    if not isinstance(generated_df, pd.DataFrame) or not isinstance(source_df, pd.DataFrame):
        return {"input": _result(False, "generated_df and source_df must be pandas DataFrames")}
    if generated_df.empty:
        return {"input": _result(False, "generated data is empty")}
    range_errors = []
    for column in _RANGE_COLUMNS:
        if column not in generated_df or column not in source_df:
            range_errors.append(f"missing column: {column}")
            continue
        source = _numeric_series(source_df, column).dropna()
        generated = _numeric_series(generated_df, column).dropna()
        if source.empty:
            continue
        margin = max(abs(float(source.min())), abs(float(source.max())), 1.0) * 0.10
        lower, upper = float(source.min()) - margin, float(source.max()) + margin
        outside = generated[(generated < lower) | (generated > upper)]
        if not outside.empty:
            range_errors.append(f"{column}: {len(outside)} values outside [{lower:.3g}, {upper:.3g}]")
    type_errors = []
    numeric_columns = schema.get("numeric_cols", []) if isinstance(schema, dict) else []
    for column in numeric_columns:
        if column in generated_df and not pd.api.types.is_numeric_dtype(generated_df[column]):
            type_errors.append(f"{column} is not numeric")
    for column in set(_RANGE_COLUMNS + _NON_NEGATIVE_COLUMNS + ("patient_id", "month", "diabetic")):
        if column in generated_df and column in source_df:
            coerced = _numeric_series(generated_df, column)
            if generated_df[column].notna().any() and coerced.notna().sum() != generated_df[column].notna().sum():
                type_errors.append(f"{column} contains non-numeric values")
    duplicate_errors = []
    if "patient_id" not in generated_df or "month" not in generated_df:
        duplicate_errors.append("patient_id and month are required")
    else:
        duplicate_count = int(generated_df.duplicated(["patient_id", "month"]).sum())
        if duplicate_count:
            duplicate_errors.append(f"{duplicate_count} duplicate patient_id + month rows")
    negative_errors = []
    for column in _NON_NEGATIVE_COLUMNS:
        if column in generated_df:
            count = int((_numeric_series(generated_df, column) < 0).sum())
            if count:
                negative_errors.append(f"{column}: {count} negative values")
    missing_errors = []
    for column in source_df.columns.intersection(generated_df.columns):
        source_pct = float(source_df[column].isna().mean() * 100)
        generated_pct = float(generated_df[column].isna().mean() * 100)
        if abs(source_pct - generated_pct) > 10.0:
            missing_errors.append(f"{column}: source {source_pct:.2f}%, generated {generated_pct:.2f}%")
    return {
        "valid_ranges": _result(not range_errors, "Within source-derived ranges with approximately 10% tolerance" if not range_errors else "; ".join(range_errors)),
        "valid_types": _result(not type_errors, "Column types are compatible with the schema" if not type_errors else "; ".join(type_errors)),
        "duplicate_ids": _result(not duplicate_errors, "No duplicate patient_id + month keys" if not duplicate_errors else "; ".join(duplicate_errors)),
        "negative_values": _result(not negative_errors, "No negative values in non-negative fields" if not negative_errors else "; ".join(negative_errors)),
        "missingness": _result(not missing_errors, "Missingness is within 10 percentage points of source" if not missing_errors else "; ".join(missing_errors)),
    }
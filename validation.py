"""Validation and evidence metrics for synthetic tabular data."""

from __future__ import annotations

import importlib
from typing import Any

import numpy as np
import pandas as pd

_RELATIONSHIPS = {
    "Activity ↔ Pain": ("activity_steps", "pain_score"),
    "Adherence ↔ Pain": ("medication_adherence_pct", "pain_score"),
    "Age ↔ BP": ("age", "systolic_bp"),
    "Diabetic ↔ BP": ("diabetic", "systolic_bp"),
}


def _json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(v) for v in value]
    if isinstance(value, (np.integer, np.floating)):
        return None if pd.isna(value) else value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


def _error(message: str, **extra: Any) -> dict:
    return _json({"status": "error", "error": message, **extra})


def _corr(df: pd.DataFrame, left: str, right: str) -> float | None:
    if left not in df or right not in df:
        return None
    values = df[[left, right]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(values) < 2 or values[left].nunique() < 2 or values[right].nunique() < 2:
        return None
    result = values[left].corr(values[right])
    return None if pd.isna(result) else float(result)


def _relationship_metrics(source_df: pd.DataFrame, generated_df: pd.DataFrame) -> dict:
    result = {}
    for name, (left, right) in _RELATIONSHIPS.items():
        source_value, synthetic_value = _corr(source_df, left, right), _corr(generated_df, left, right)
        result[name] = {"source_correlation": source_value, "synthetic_correlation": synthetic_value, "difference": None if source_value is None or synthetic_value is None else abs(source_value - synthetic_value), "interpretation": "Observed statistical associations - not causal relationships."}
    return result


def _distribution_similarity(source_df: pd.DataFrame, generated_df: pd.DataFrame) -> dict:
    result = {}
    for column in source_df.columns.intersection(generated_df.columns):
        source = pd.to_numeric(source_df[column], errors="coerce").dropna()
        synthetic = pd.to_numeric(generated_df[column], errors="coerce").dropna()
        if source.empty or synthetic.empty:
            continue
        result[column] = {"source_mean": float(source.mean()), "synthetic_mean": float(synthetic.mean()), "source_std": float(source.std(ddof=0)), "synthetic_std": float(synthetic.std(ddof=0)), "mean_difference": float(abs(source.mean() - synthetic.mean()))}
    return result


def compute_quality_metrics(source_df, generated_df) -> dict:
    """Return raw distribution/correlation evidence and an optional SDMetrics report."""
    if not isinstance(source_df, pd.DataFrame) or not isinstance(generated_df, pd.DataFrame):
        return _error("source_df and generated_df must be pandas DataFrames")
    if source_df.empty or generated_df.empty:
        return _error("source and generated data must not be empty")
    result = {"status": "ok", "distribution_similarity": _distribution_similarity(source_df, generated_df), "correlations": _relationship_metrics(source_df, generated_df), "observed_association_note": "Observed statistical associations - not causal relationships."}
    try:
        metadata_cls = getattr(importlib.import_module("sdv.metadata"), "SingleTableMetadata")
        report_cls = getattr(importlib.import_module("sdmetrics.reports.single_table"), "QualityReport")
        metadata = metadata_cls(); metadata.detect_from_dataframe(source_df)
        metadata_payload = metadata.to_dict() if hasattr(metadata, "to_dict") else metadata
        report = report_cls(); report.generate(source_df, generated_df, metadata_payload)
        result["sdmetrics_quality_report"] = _json(report.get_properties())
        result["sdmetrics_quality_score"] = _json(report.get_score())
    except (ImportError, AttributeError, TypeError, ValueError, RuntimeError) as exc:
        result["sdmetrics_quality_report"] = {"status": "unavailable", "reason": f"SDMetrics API unavailable: {exc}"}
    return _json(result)


def compute_privacy_metrics(source_df, generated_df) -> dict:
    """Compute a nearest-source-record distance when no supported privacy API exists."""
    if not isinstance(source_df, pd.DataFrame) or not isinstance(generated_df, pd.DataFrame):
        return _error("source_df and generated_df must be pandas DataFrames")
    common = [c for c in source_df.columns.intersection(generated_df.columns) if pd.api.types.is_numeric_dtype(source_df[c])]
    if not common or source_df.empty or generated_df.empty:
        return _error("numeric common columns and non-empty data are required for privacy distance")
    try:
        metadata_cls = getattr(importlib.import_module("sdv.metadata"), "SingleTableMetadata")
        privacy_module = importlib.import_module("sdmetrics.single_table")
        privacy_metric = getattr(privacy_module, "NewRowSynthesis")
        metadata = metadata_cls(); metadata.detect_from_dataframe(source_df)
        value = privacy_metric.compute(real_data=source_df, synthetic_data=generated_df, metadata=metadata)
        return _json({"status": "ok", "label": "SDMetrics", "metric_name": "NewRowSynthesis", "value": value, "interpretation": "SDMetrics privacy diagnostic; not a guarantee of anonymization, HIPAA compliance, or privacy."})
    except (ImportError, AttributeError, TypeError, ValueError, RuntimeError):
        pass
    source = source_df[common].apply(pd.to_numeric, errors="coerce")
    synthetic = generated_df[common].apply(pd.to_numeric, errors="coerce")
    medians = source.median(); source = source.fillna(medians).fillna(0); synthetic = synthetic.fillna(medians).fillna(0)
    scale = source.std(ddof=0).replace(0, 1).fillna(1)
    source_values, synthetic_values = source.to_numpy() / scale.to_numpy(), synthetic.to_numpy() / scale.to_numpy()
    nearest_distances = []
    for start in range(0, len(synthetic_values), 256):
        batch = synthetic_values[start : start + 256]
        distances = np.sqrt(((batch[:, None, :] - source_values[None, :, :]) ** 2).mean(axis=2))
        nearest_distances.append(np.min(distances, axis=1))
    value = float(np.concatenate(nearest_distances).mean())
    return _json({"status": "ok", "label": "measured distance", "metric_name": "mean_nearest_source_record_distance", "value": value, "interpretation": "A computed similarity distance, not a guarantee of anonymization, HIPAA compliance, or privacy."})


def compute_missingness_similarity(source_df, generated_df) -> dict:
    if not isinstance(source_df, pd.DataFrame) or not isinstance(generated_df, pd.DataFrame):
        return _error("source_df and generated_df must be pandas DataFrames")
    result = {}
    for column in source_df.columns.intersection(generated_df.columns):
        source_pct, synthetic_pct = float(source_df[column].isna().mean() * 100), float(generated_df[column].isna().mean() * 100)
        result[column] = {"source_missing_pct": source_pct, "synthetic_missing_pct": synthetic_pct, "difference_pct": abs(source_pct - synthetic_pct), "interpretation": "Missingness-rate comparison; not a clinical validity assessment."}
    return _json(result)


def compute_tstr(source_df, generated_df, target_col: str) -> dict:
    """Compare synthetic-trained and real-trained models on the same real holdout."""
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression, Ridge
        from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score, roc_auc_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
    except ImportError as exc:
        return _error(f"TSTR dependency unavailable: {exc}")
    if not isinstance(source_df, pd.DataFrame) or not isinstance(generated_df, pd.DataFrame):
        return _error("source_df and generated_df must be pandas DataFrames")
    if target_col not in source_df or target_col not in generated_df:
        return _error(f"target_col '{target_col}' must exist in both datasets")
    excluded = {target_col, "patient_id", "month", "date", "time", "timestamp"}
    features = [c for c in source_df.columns if c not in excluded and c in generated_df]
    real = source_df[features + [target_col]].dropna(subset=[target_col]); synthetic = generated_df[features + [target_col]].dropna(subset=[target_col])
    if len(real) < 20 or len(synthetic) < 10 or not features:
        return _error("insufficient rows or features for TSTR")
    classification = not pd.api.types.is_numeric_dtype(real[target_col]) or real[target_col].nunique() <= 10
    if classification and real[target_col].nunique() < 2:
        return _error("classification target must contain at least two classes")
    try:
        if "patient_id" in source_df:
            from backend.generation import train_holdout_split
            train_source, test_source = train_holdout_split(source_df, "patient_id", random_state=42)
            train_real = train_source[features + [target_col]].dropna(subset=[target_col])
            test_real = test_source[features + [target_col]].dropna(subset=[target_col])
        else:
            # Non-longitudinal datasets have no patient grouping contract.
            from sklearn.model_selection import train_test_split
            stratify = real[target_col] if classification and real[target_col].value_counts().min() >= 2 else None
            train_real, test_real = train_test_split(real, test_size=0.25, random_state=42, stratify=stratify)
        numeric = [c for c in features if pd.api.types.is_numeric_dtype(source_df[c])]; categorical = [c for c in features if c not in numeric]
        transformers = []
        if numeric:
            transformers.append(("numeric", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric))
        if categorical:
            transformers.append(("categorical", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical))
        def fit_score(training):
            model = LogisticRegression(max_iter=1000) if classification else Ridge()
            pipe = Pipeline([("preprocessor", ColumnTransformer(transformers)), ("model", model)])
            pipe.fit(training[features], training[target_col]); actual = test_real[target_col]; predicted = pipe.predict(test_real[features])
            metrics = {"accuracy": float(accuracy_score(actual, predicted)), "f1_weighted": float(f1_score(actual, predicted, average="weighted"))} if classification else {"mae": float(mean_absolute_error(actual, predicted)), "r2": float(r2_score(actual, predicted))}
            if classification and real[target_col].nunique() == 2:
                metrics["roc_auc"] = float(roc_auc_score(actual, pipe.predict_proba(test_real[features])[:, 1]))
            return metrics
        return _json({"status": "ok", "target_col": target_col, "task": "classification" if classification else "regression", "synthetic_to_real": fit_score(synthetic), "real_to_real": fit_score(train_real), "test_rows": len(test_real), "interpretation": "Synthetic-trained and real-trained models are evaluated on the same patient-level held-out real set; this is task-specific utility evidence."})
    except (ValueError, TypeError, RuntimeError) as exc:
        return _error(f"TSTR could not be performed reliably: {exc}")

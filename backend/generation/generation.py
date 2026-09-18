"""SDV-backed synthetic cohort generation.

Gaussian Copula is the default, dependable tabular generator. CTGAN is
available for comparison. Longitudinal fallback generation resamples observed
month-to-month changes rather than mechanistically modelling disease
progression.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


class GenerationError(RuntimeError):
    """Raised when a requested generation operation cannot be completed."""


def _require_dataframe(data: pd.DataFrame, name: str) -> None:
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame")
    if data.empty:
        raise ValueError(f"{name} must contain at least one row")


def _column_is_identifier(name: str, series: pd.Series) -> bool:
    name_hint = bool(re.search(r"(^|_)(id|uuid|identifier|key)$", str(name).lower()))
    return name_hint or (
        series.nunique(dropna=True) == len(series) and len(series) > 1
    )


def _column_is_temporal(name: str, series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    return bool(re.search(r"(^|_)(date|time|timestamp|month|year)$", str(name).lower()))


def _clean_source(source_df: pd.DataFrame) -> pd.DataFrame:
    result = source_df.copy()
    for column in result.columns:
        series = result[column]
        if pd.api.types.is_bool_dtype(series):
            result[column] = series.astype("int8")
        elif pd.api.types.is_numeric_dtype(series):
            result[column] = series.replace([np.inf, -np.inf], np.nan)
            if result[column].isna().any():
                result[column] = result[column].fillna(result[column].median())
        elif series.isna().any():
            result[column] = series.fillna("__missing__")
    if result.isna().any().any():
        raise GenerationError("Source data contains unsupported missing values after cleaning")
    return result


def _build_metadata(data: pd.DataFrame) -> Any:
    try:
        from sdv.metadata import SingleTableMetadata
    except ImportError as exc:
        raise GenerationError(
            "SDV is required for generation. Install the project's requirements first."
        ) from exc

    metadata = SingleTableMetadata()
    try:
        metadata.detect_from_dataframe(data)
    except Exception as exc:
        raise GenerationError(f"SDV metadata detection failed: {exc}") from exc

    # Repeated patient identifiers are not primary keys in longitudinal source
    # tables. Treat identifiers as categorical values while preserving strings.
    for column in data.columns:
        if _column_is_identifier(column, data[column]):
            if getattr(metadata, "primary_key", None) == column:
                metadata.remove_primary_key()
            try:
                metadata.update_column(column_name=column, sdtype="categorical")
            except Exception:
                # Some SDV versions expose update_column with positional args.
                metadata.update_column(column, sdtype="categorical")
        elif _column_is_temporal(column, data[column]) and not pd.api.types.is_numeric_dtype(
            data[column]
        ):
            try:
                metadata.update_column(column_name=column, sdtype="datetime")
            except Exception:
                metadata.update_column(column, sdtype="datetime")
    return metadata


def _make_synthesizer(model: str, metadata: Any, request: Optional[Mapping[str, Any]]) -> Any:
    model_name = str(model).lower().strip()
    request = request or {}
    try:
        if model_name in {"gaussian_copula", "gaussiancopula", "gc"}:
            from sdv.single_table import GaussianCopulaSynthesizer

            kwargs = {}
            if "default_distribution" in request:
                kwargs["default_distribution"] = request["default_distribution"]
            return GaussianCopulaSynthesizer(metadata, **kwargs)
        if model_name == "ctgan":
            from sdv.single_table import CTGANSynthesizer

            kwargs = {}
            if "epochs" in request:
                kwargs["epochs"] = int(request["epochs"])
            if "batch_size" in request:
                kwargs["batch_size"] = int(request["batch_size"])
            return CTGANSynthesizer(metadata, **kwargs)
    except ImportError as exc:
        raise GenerationError(f"SDV {model_name} synthesizer is unavailable: {exc}") from exc
    raise ValueError("model must be 'gaussian_copula' or 'ctgan'")


def _fit_and_sample(
    source_df: pd.DataFrame,
    request: Optional[Mapping[str, Any]],
    n_rows: int,
    model: str,
) -> pd.DataFrame:
    if not isinstance(n_rows, int) or n_rows < 1:
        raise ValueError("n_rows must be a positive integer")
    source = _clean_source(source_df)
    metadata = _build_metadata(source)
    synthesizer = _make_synthesizer(model, metadata, request)
    try:
        synthesizer.fit(source)
        result = synthesizer.sample(num_rows=n_rows)
    except Exception as exc:
        raise GenerationError(f"{model} synthesis failed: {exc}") from exc
    if not isinstance(result, pd.DataFrame):
        raise GenerationError(f"{model} returned an invalid result type")
    missing = [column for column in source_df.columns if column not in result.columns]
    if missing:
        raise GenerationError(f"{model} output is missing source columns: {missing}")
    result = result.loc[:, list(source_df.columns)]
    if len(result) != n_rows:
        raise GenerationError(f"{model} returned {len(result)} rows; expected {n_rows}")
    return _clean_output(result, source_df)


def _condition_mask(data: pd.DataFrame, condition: Mapping[str, Any]) -> pd.Series:
    variable = condition.get("variable")
    if variable not in data.columns:
        raise ValueError(f"Condition references unknown variable '{variable}'")
    operator = condition.get("operator", "==")
    value = condition.get("value")
    if operator == "==":
        return data[variable] == value
    if operator == "!=":
        return data[variable] != value
    if operator == ">":
        return data[variable] > value
    if operator == ">=":
        return data[variable] >= value
    if operator == "<":
        return data[variable] < value
    if operator == "<=":
        return data[variable] <= value
    raise ValueError(f"Unsupported condition operator '{operator}'")


def _conditioned_sample(
    source_df: pd.DataFrame,
    request: Mapping[str, Any],
    n_rows: int,
    model: str,
) -> pd.DataFrame:
    conditions = request.get("conditions") or []
    if not conditions:
        return _fit_and_sample(source_df, request, n_rows, model)
    validated = [dict(condition) for condition in conditions]
    pool_size = max(n_rows * 5, n_rows + 100)
    pool = _fit_and_sample(source_df, request, pool_size, model)
    selected: List[int] = []
    remaining = pool.index.to_numpy()
    target_counts = [
        max(0, min(n_rows, round(n_rows * float(condition.get("target_pct", 0)) / 100)))
        for condition in validated
    ]
    for condition, target_count in zip(validated, target_counts):
        mask = _condition_mask(pool, condition)
        already = int(mask.loc[selected].sum()) if selected else 0
        needed = max(0, target_count - already)
        candidates = [index for index in remaining if bool(mask.loc[index])]
        selected.extend(candidates[:needed])
        remaining = np.asarray([index for index in remaining if index not in set(selected)])
    if len(selected) < n_rows:
        selected.extend(list(remaining[: n_rows - len(selected)]))
    if len(selected) < n_rows:
        selected.extend(list(pool.index.to_numpy()[: n_rows - len(selected)]))
    result = pool.loc[selected[:n_rows]].reset_index(drop=True)
    actual = {
        str(condition.get("variable")): float(_condition_mask(result, condition).mean() * 100)
        for condition in validated
    }
    result.attrs["requested_proportions"] = {
        str(condition.get("variable")): float(condition.get("target_pct", 0))
        for condition in validated
    }
    result.attrs["actual_proportions"] = actual
    result.attrs["conditional_sampling_note"] = (
        "Targets were approximated from an oversampled synthetic pool; inspect "
        "actual_proportions rather than treating requests as guaranteed."
    )
    return result


def _clean_output(result: pd.DataFrame, source_df: pd.DataFrame) -> pd.DataFrame:
    result = result.replace([np.inf, -np.inf], np.nan)
    for column in result.columns:
        if result[column].isna().any():
            if pd.api.types.is_numeric_dtype(source_df[column]):
                result[column] = result[column].fillna(source_df[column].median())
            else:
                result[column] = result[column].fillna(source_df[column].mode().iloc[0])
    if result.isna().any().any():
        raise GenerationError("Generated output contains unresolved NaN values")
    for column in source_df.columns:
        source = source_df[column]
        if pd.api.types.is_bool_dtype(source):
            result[column] = result[column].astype(bool)
        elif pd.api.types.is_numeric_dtype(source):
            # Keep statistical samples within observed source support. This is
            # a bounded-data safeguard, not a claim of clinical validity.
            result[column] = result[column].clip(source.min(), source.max())
    return result.reset_index(drop=True)


def generate_cross_sectional(
    source_df: pd.DataFrame,
    request: Optional[Mapping[str, Any]],
    n_rows: int,
    model: str = "gaussian_copula",
) -> pd.DataFrame:
    """Generate a cross-sectional cohort with Gaussian Copula or CTGAN."""
    _require_dataframe(source_df, "source_df")
    if request is not None and not isinstance(request, Mapping):
        raise TypeError("request must be a mapping or None")
    if request and request.get("conditions"):
        return _conditioned_sample(source_df, request, n_rows, model)
    return _fit_and_sample(source_df, request, n_rows, model)


def _find_identifier(data: pd.DataFrame) -> Optional[str]:
    for column in data.columns:
        if _column_is_identifier(column, data[column]):
            return column
    return None


def _find_similar_patient(
    baseline: pd.Series,
    patients: Dict[Any, pd.DataFrame],
    feature_columns: Sequence[str],
    source: pd.DataFrame,
) -> pd.DataFrame:
    def distance(trajectory: pd.DataFrame) -> float:
        first = trajectory.iloc[0]
        score = 0.0
        for column in feature_columns:
            if column not in first or pd.isna(baseline.get(column)):
                continue
            if pd.api.types.is_numeric_dtype(source[column]):
                scale = float(source[column].std()) or 1.0
                score += abs(float(first[column]) - float(baseline[column])) / scale
            else:
                score += float(first[column] != baseline[column])
        return score

    return min(patients.values(), key=distance)


def bootstrap_trajectories(
    source_df: pd.DataFrame,
    synthetic_baseline_df: pd.DataFrame,
    time_col: str,
) -> pd.DataFrame:
    """Apply observed patient deltas to synthetic baselines and clip to source bounds."""
    _require_dataframe(source_df, "source_df")
    _require_dataframe(synthetic_baseline_df, "synthetic_baseline_df")
    if time_col not in source_df.columns:
        raise ValueError(f"time_col '{time_col}' is not present in source_df")
    identifier = _find_identifier(source_df)
    if identifier is None:
        raise ValueError("Longitudinal source requires an identifier column")
    source = _clean_source(source_df).sort_values([identifier, time_col])
    baseline = synthetic_baseline_df.copy()
    if identifier not in baseline.columns:
        baseline[identifier] = [f"synthetic_{index}" for index in range(len(baseline))]
    patient_groups = {key: group.copy() for key, group in source.groupby(identifier, sort=False)}
    if not patient_groups:
        raise ValueError("No source patient trajectories were found")
    source_time_values = list(source[time_col].drop_duplicates())
    numeric_columns = [
        column
        for column in source.columns
        if column in baseline.columns
        and column not in {identifier, time_col}
        and pd.api.types.is_numeric_dtype(source[column])
    ]
    feature_columns = [
        column for column in baseline.columns if column in source.columns and column not in {identifier, time_col}
    ]
    rows: List[Dict[str, Any]] = []
    for _, patient_baseline in baseline.iterrows():
        trajectory = _find_similar_patient(patient_baseline, patient_groups, feature_columns, source)
        trajectory = trajectory.sort_values(time_col).reset_index(drop=True)
        previous = patient_baseline.to_dict()
        for step, time_value in enumerate(source_time_values):
            row = dict(previous)
            row[identifier] = patient_baseline[identifier]
            row[time_col] = time_value
            if step > 0 and step < len(trajectory):
                prior = trajectory.iloc[step - 1]
                current = trajectory.iloc[step]
                for column in numeric_columns:
                    row[column] = float(previous[column]) + (
                        float(current[column]) - float(prior[column])
                    )
                for column in feature_columns:
                    if column not in numeric_columns:
                        row[column] = current[column]
            rows.append(row)
            previous = row
    result = pd.DataFrame(rows)
    for column in numeric_columns:
        result[column] = result[column].clip(source[column].min(), source[column].max())
    columns = [identifier, time_col] + [
        column for column in baseline.columns if column not in {identifier, time_col}
    ]
    return _clean_output(result.loc[:, columns], source_df)


def _try_par(
    source_df: pd.DataFrame,
    synthetic_baseline_df: pd.DataFrame,
    time_col: str,
) -> Optional[pd.DataFrame]:
    """Try PAR only when the installed SDV exposes its sequential API."""
    try:
        from sdv.sequential import PARSynthesizer
    except ImportError:
        return None
    try:
        identifier = _find_identifier(source_df)
        if identifier is None:
            return None
        # SDV's sequential metadata APIs differ materially across releases.
        # Keep this best-effort and use the deterministic fallback on any
        # incompatibility rather than returning unvalidated trajectories.
        from sdv.metadata import SingleTableMetadata

        metadata = SingleTableMetadata()
        metadata.detect_from_dataframe(source_df)
        synthesizer = PARSynthesizer(metadata, context_columns=[identifier])
        synthesizer.fit(source_df)
        sampled = synthesizer.sample(num_rows=len(synthetic_baseline_df))
        if not isinstance(sampled, pd.DataFrame) or time_col not in sampled:
            return None
        return bootstrap_trajectories(source_df, sampled, time_col)
    except Exception:
        return None


def generate_longitudinal(
    source_df: pd.DataFrame,
    synthetic_baseline_df: pd.DataFrame,
    time_col: str,
) -> pd.DataFrame:
    """Generate longitudinal records, using validated PAR or bootstrap fallback."""
    _require_dataframe(source_df, "source_df")
    _require_dataframe(synthetic_baseline_df, "synthetic_baseline_df")
    par_result = _try_par(source_df, synthetic_baseline_df, time_col)
    if par_result is not None:
        return par_result
    return bootstrap_trajectories(source_df, synthetic_baseline_df, time_col)

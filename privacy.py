"""Adversarial, patient-level membership-inference simulation for MedSyn.

This module is intentionally separate from the application layer.  It measures
one concrete threat model: an attacker compares patient-level clinical summaries
to synthetic patient summaries and treats a smaller nearest-neighbour distance
as evidence of membership in the generator's training source.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple

import numpy as np
import pandas as pd


_INTERPRETATION_BANDS = (
    (0.60, "near_random", "limited ability"),
    (0.75, "moderate_discrimination", "moderate ability"),
    (float("inf"), "high_discrimination", "stronger ability"),
)


def _error(message: str, **details: Any) -> Dict[str, Any]:
    return {"status": "error", "error": message, **details}


def _patient_split(
    source_df: pd.DataFrame, id_column: str, train_fraction: float, random_state: int
) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    """Split whole patients, never individual longitudinal records."""
    if id_column not in source_df.columns:
        raise ValueError(f"id_column '{id_column}' is not present in source_df")
    from backend.generation import train_holdout_split
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be strictly between 0 and 1")
    train_df, holdout_df = train_holdout_split(
        source_df, id_column, holdout_frac=1 - train_fraction, random_state=random_state
    )
    train_ids = train_df[id_column].dropna().drop_duplicates().to_numpy()
    holdout_ids = holdout_df[id_column].dropna().drop_duplicates().to_numpy()
    if set(train_ids).intersection(holdout_ids):
        raise RuntimeError("Patient split overlap detected")
    if train_df.empty or holdout_df.empty:
        raise ValueError("Patient split produced an empty group")
    return train_df, holdout_df, train_ids, holdout_ids


def _clinical_feature_columns(
    source_df: pd.DataFrame, id_column: str, time_column: str
) -> list[str]:
    """Choose numeric clinical fields while explicitly excluding identifiers and time."""
    excluded = {id_column, time_column}
    return [
        column
        for column in source_df.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(source_df[column])
    ]


def _aggregate_patients(data: pd.DataFrame, patient_column: str, features: Iterable[str]) -> pd.DataFrame:
    """Use one identical mean/std/min/max representation for every patient set."""
    features = list(features)
    numeric = data.loc[:, [patient_column] + features].copy()
    for feature in features:
        numeric[feature] = pd.to_numeric(numeric[feature], errors="coerce")
    grouped = numeric.groupby(patient_column, sort=False)[features]
    result = grouped.agg(["mean", "std", "min", "max"])
    result.columns = [f"{feature}__{stat}" for feature, stat in result.columns]
    # A one-record synthetic pseudo-patient has an undefined sample std; its
    # zero variability is the relevant fixed-length representation here.
    return result.replace([np.inf, -np.inf], np.nan)


def _generate_synthetic(
    train_without_identifiers: pd.DataFrame, generator_model: str, n_records: int
) -> pd.DataFrame:
    """Small adapter around the existing generation module, trained on train only."""
    from backend.generation import generate_cross_sectional

    return generate_cross_sectional(
        train_without_identifiers, request=None, n_rows=n_records, model=generator_model
    )


def _interpret_auroc(auroc: float) -> Tuple[str, str]:
    if auroc < 0.40:
        return (
            "inverse_discrimination",
            "The specified lower-distance membership score separated groups in the opposite direction; "
            "it did not provide useful membership evidence under this threat model.",
        )
    for upper_bound, band, description in _INTERPRETATION_BANDS:
        if auroc < upper_bound:
            return (
                band,
                f"Under this simulated membership-inference threat model, the attacker showed {description} "
                "to distinguish training members from held-out patients.",
            )
    raise AssertionError("AUROC interpretation band missing")


def run_membership_inference_simulation(
    source_df: pd.DataFrame,
    generator_model: str = "gaussian_copula",
    train_fraction: float = 0.8,
    random_state: int = 42,
    id_column: str = "patient_id",
    time_column: str = "month",
) -> Dict[str, Any]:
    """Run a reproducible patient-level membership-inference simulation.

    The generator receives only the training patients, and neither the patient
    identifier nor time value is an attack feature (or a generator input).
    The illustrative operating threshold is the pooled median observed distance:
    it is label-free and is not selected to maximize a privacy outcome.
    """
    if not isinstance(source_df, pd.DataFrame) or source_df.empty:
        return _error("source_df must be a non-empty pandas DataFrame")
    if time_column not in source_df.columns:
        return _error(f"time_column '{time_column}' is not present in source_df")
    try:
        train_df, holdout_df, train_ids, holdout_ids = _patient_split(
            source_df, id_column, train_fraction, random_state
        )
        features = _clinical_feature_columns(source_df, id_column, time_column)
        if not features:
            raise ValueError("No numeric clinical features remain after excluding identifier and time columns")

        # Generate a source-sized sample, derived entirely from input size for
        # predictable demo runtime.  Removing identifiers prevents either ID
        # values or the month index from becoming a shortcut for the attacker.
        n_synthetic_records = max(len(source_df), len(train_df))
        generator_input = train_df.loc[:, features].copy()
        synthetic_records = _generate_synthetic(generator_input, generator_model, n_synthetic_records)
        if not isinstance(synthetic_records, pd.DataFrame) or synthetic_records.empty:
            raise ValueError("Generator returned no synthetic records")

        records_per_patient = max(1, int(round(len(train_df) / len(train_ids))))
        synthetic = synthetic_records.loc[:, features].copy()
        synthetic["__synthetic_patient__"] = np.arange(len(synthetic)) // records_per_patient
        train_repr = _aggregate_patients(train_df, id_column, features)
        holdout_repr = _aggregate_patients(holdout_df, id_column, features)
        synthetic_repr = _aggregate_patients(synthetic, "__synthetic_patient__", features)

        from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score, roc_auc_score, roc_curve
        from sklearn.neighbors import NearestNeighbors
        from sklearn.preprocessing import StandardScaler

        fill_values = train_repr.median(axis=0).fillna(0.0)
        train_values = train_repr.fillna(fill_values).fillna(0.0)
        holdout_values = holdout_repr.reindex(columns=train_repr.columns).fillna(fill_values).fillna(0.0)
        synthetic_values = synthetic_repr.reindex(columns=train_repr.columns).fillna(fill_values).fillna(0.0)
        scaler = StandardScaler().fit(train_values)
        nearest = NearestNeighbors(n_neighbors=1, metric="euclidean").fit(scaler.transform(synthetic_values))
        train_distances = nearest.kneighbors(scaler.transform(train_values), return_distance=True)[0].ravel()
        holdout_distances = nearest.kneighbors(scaler.transform(holdout_values), return_distance=True)[0].ravel()
        labels = np.concatenate((np.ones(len(train_distances), dtype=int), np.zeros(len(holdout_distances), dtype=int)))
        scores = -np.concatenate((train_distances, holdout_distances))
        auroc = float(roc_auc_score(labels, scores))
        fpr, tpr, _ = roc_curve(labels, scores)

        # Pooled median is an observed, label-free illustrative operating point,
        # intentionally not a threshold optimized to make any result look good.
        threshold = float(np.median(np.concatenate((train_distances, holdout_distances))))
        predictions = (np.concatenate((train_distances, holdout_distances)) < threshold).astype(int)
        band, interpretation = _interpret_auroc(auroc)
        return {
            "status": "ok",
            "generator_model": generator_model,
            "n_train_patients": int(len(train_ids)),
            "n_holdout_patients": int(len(holdout_ids)),
            "n_synthetic_records": int(len(synthetic_records)),
            "attack_features": features,
            "representation": "Per-patient mean, standard deviation, minimum, and maximum of numeric clinical features; IDs and time excluded.",
            "distance_metric": "Euclidean nearest-neighbor distance after StandardScaler fit on training patient representations.",
            "attack_auroc": auroc,
            "interpretation_band": band,
            "interpretation": interpretation,
            "train_distance_mean": float(np.mean(train_distances)),
            "holdout_distance_mean": float(np.mean(holdout_distances)),
            "train_distance_median": float(np.median(train_distances)),
            "holdout_distance_median": float(np.median(holdout_distances)),
            "threshold_example": threshold,
            "threshold_method": "Pooled median of observed nearest-neighbor distances (label-free illustrative operating point; not optimized).",
            "threshold_accuracy": float(accuracy_score(labels, predictions)),
            "threshold_precision": float(precision_score(labels, predictions, zero_division=0)),
            "threshold_recall": float(recall_score(labels, predictions, zero_division=0)),
            "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
            "attack_labels": labels.tolist(),
            "train_distances": train_distances.tolist(),
            "holdout_distances": holdout_distances.tolist(),
            "roc_curve": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
            "warning": "This is a simulated membership-inference attack under a specific threat model. It is not a formal privacy guarantee. An attack result depends on the dataset, generator, representation, and threat model.",
        }
    except (ImportError, TypeError, ValueError, RuntimeError) as exc:
        return _error(str(exc))

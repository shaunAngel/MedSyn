"""Explicit, backend-only evidence comparison for supported synthesizers."""
from __future__ import annotations

from time import perf_counter
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from .generation import build_patient_baseline, generate_cross_sectional, train_holdout_split


def compare_generation_models(
    source_df: pd.DataFrame,
    request: Mapping[str, Any] | None,
    models: Sequence[str] = ("gaussian_copula", "ctgan"),
    target_n: int = 1000,
    random_state: int = 42,
    patient_id_col: str = "patient_id",
    time_col: str = "month",
    ctgan_epochs: int = 5,
    ctgan_batch_size: int | None = None,
    run_privacy: bool = True,
) -> dict[str, Any]:
    """Run requested models on one canonical train partition; never rank them."""
    train_df, _holdout_df = train_holdout_split(source_df, patient_id_col, random_state=random_state)
    baseline = build_patient_baseline(train_df, patient_id_col, time_col)
    clinical = [c for c in baseline if c not in {patient_id_col, time_col}]
    results = []
    for model in models:
        generation_request = dict(request or {})
        if model == "ctgan":
            generation_request["epochs"] = int(ctgan_epochs)
            if ctgan_batch_size is not None:
                generation_request["batch_size"] = int(ctgan_batch_size)
        started = perf_counter()
        try:
            generated = generate_cross_sectional(train_df, generation_request or None, target_n, model=model)
            seconds = perf_counter() - started
            from validation import compute_missingness_similarity, compute_quality_metrics
            quality = compute_quality_metrics(baseline[clinical], generated[clinical])
            correlations = quality.get("correlations", {})
            differences = [v.get("difference") for v in correlations.values() if v.get("difference") is not None]
            missingness = compute_missingness_similarity(baseline[clinical], generated[clinical])
            missing_diffs = [v["difference_pct"] for v in missingness.values()]
            actual = generated.attrs.get("actual_proportions", {})
            targets = generated.attrs.get("requested_proportions", {})
            target_deviation = float(np.mean([abs(actual[k] - targets[k]) for k in targets])) if targets else None
            privacy_auroc = None
            privacy_note = "not run"
            if run_privacy and model == "gaussian_copula":
                from privacy import run_membership_inference_simulation
                attack = run_membership_inference_simulation(source_df, generator_model=model, random_state=random_state, id_column=patient_id_col, time_column=time_col)
                privacy_auroc = attack.get("attack_auroc") if attack.get("status") == "ok" else None
                privacy_note = attack.get("error", "measured")
            elif run_privacy:
                privacy_note = "not run for CTGAN in comparison to keep controlled demo runtime practical"
            results.append({"model": model, "status": "ok", "generation_seconds": float(seconds), "n_records": int(len(generated)), "quality_score": quality.get("sdmetrics_quality_score"), "mean_correlation_difference": float(np.mean(differences)) if differences else None, "mean_missingness_difference": float(np.mean(missing_diffs)) if missing_diffs else None, "privacy_attack_auroc": privacy_auroc, "privacy_note": privacy_note, "target_deviation": target_deviation, "target_achievement": actual, "model_features": generated.attrs.get("model_features", [])})
        except Exception as exc:
            results.append({"model": model, "status": "error", "error": str(exc), "generation_seconds": float(perf_counter() - started), "n_records": 0, "quality_score": None, "mean_correlation_difference": None, "mean_missingness_difference": None, "privacy_attack_auroc": None, "target_deviation": None})
    return {"status": "ok", "train_patients": int(train_df[patient_id_col].nunique()), "target_n": int(target_n), "results": results, "note": "Evidence comparison only; no winner, ranking, or composite score is selected."}

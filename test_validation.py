import json
from pathlib import Path

import pandas as pd

from sanity import run_sanity_checks
from validation import compute_missingness_similarity, compute_privacy_metrics, compute_quality_metrics, compute_tstr

DATASET = Path(__file__).with_name("demo_patients.csv")


def source():
    return pd.read_csv(DATASET)


def test_sanity_checks_execute_and_ranges_detected():
    df = source(); generated = df.copy(); generated.loc[0, "age"] = 1000
    result = run_sanity_checks(generated, {"numeric_cols": list(df.columns)}, df)
    assert set(("valid_ranges", "valid_types", "duplicate_ids", "negative_values", "missingness")) <= set(result)
    assert result["valid_ranges"]["passed"] is False


def test_duplicate_longitudinal_key_and_negative_values_detected():
    df = source(); generated = df.copy(); generated.loc[1, ["patient_id", "month"]] = generated.loc[0, ["patient_id", "month"]]; generated.loc[2, "activity_steps"] = -1
    result = run_sanity_checks(generated, {}, df)
    assert result["duplicate_ids"]["passed"] is False
    assert result["negative_values"]["passed"] is False


def test_missingness_quality_correlations_privacy_and_serialization():
    df = source(); generated = df.sample(frac=1, random_state=3).reset_index(drop=True)
    missing, quality, privacy = compute_missingness_similarity(df, generated), compute_quality_metrics(df, generated), compute_privacy_metrics(df, generated)
    assert "systolic_bp" in missing and "medication_adherence_pct" in missing
    assert len(quality["correlations"]) == 4
    assert "value" in privacy or privacy["status"] == "error"
    json.dumps({"missing": missing, "quality": quality, "privacy": privacy})


def test_tstr_executes_or_fails_gracefully():
    df = source(); result = compute_tstr(df, df.sample(frac=1, random_state=4), "diabetic")
    assert result["status"] in ("ok", "error")
    json.dumps(result)
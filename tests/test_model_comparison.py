from pathlib import Path
import pandas as pd

from backend.generation import generate_cross_sectional, train_holdout_split
from backend.model_comparison import compare_generation_models

DATA = Path(__file__).parents[1] / "data" / "demo_patients.csv"


def test_ctgan_small_baseline_is_clinical_only_and_has_fresh_ids():
    source = pd.read_csv(DATA)
    train, _ = train_holdout_split(source, "patient_id")
    result = generate_cross_sectional(train, {"epochs": 1}, 12, model="ctgan")
    assert len(result) == 12
    assert "patient_id" not in result.attrs["model_features"]
    assert "month" not in result.attrs["model_features"]
    assert not set(result.patient_id).intersection(source.patient_id)


def test_model_comparison_returns_evidence_without_winner():
    source = pd.read_csv(DATA)
    comparison = compare_generation_models(source, None, models=("gaussian_copula", "ctgan"), target_n=12, ctgan_epochs=1, run_privacy=False)
    assert comparison["train_patients"] == 400
    assert "winner" not in comparison and "ranking" not in comparison
    assert {row["model"] for row in comparison["results"]} == {"gaussian_copula", "ctgan"}
    for row in comparison["results"]:
        assert row["generation_seconds"] >= 0
        assert row["status"] in {"ok", "error"}
        if row["status"] == "ok":
            assert row["quality_score"] is not None

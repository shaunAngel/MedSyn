from pathlib import Path
import pandas as pd
import pytest

from backend.generation import build_patient_baseline, generate_cross_sectional, train_holdout_split
from data_ingest import detect_schema, load_dataset
from sparsity import compute_sparsity

DATA = Path(__file__).parents[1] / "data" / "demo_patients.csv"


def test_ingest_schema_and_sparsity_contract(tmp_path):
    df = load_dataset(str(DATA))
    assert len(df) == 3000 and df.patient_id.nunique() == 500
    assert detect_schema(df)["patient_id_col"] == "patient_id"
    result = compute_sparsity(df, ["diabetic", "age_over_65", "low_adherence"])
    assert result["subgroup_counts"][frozenset(("diabetic",))] == 100
    # The checked-in CSV contains 20 at baseline (despite the brief's stale 25).
    assert result["subgroup_counts"][frozenset(("diabetic", "age_over_65"))] == 20
    assert result["subgroup_counts"][frozenset(("diabetic", "age_over_65", "low_adherence"))] == 2
    with pytest.raises(ValueError): load_dataset(str(tmp_path / "data.txt"))


def test_patient_split_baseline_and_fresh_ids():
    df = pd.read_csv(DATA)
    train, holdout = train_holdout_split(df, "patient_id")
    assert train.patient_id.nunique() == 400 and holdout.patient_id.nunique() == 100
    assert not set(train.patient_id).intersection(holdout.patient_id)
    assert train.groupby("patient_id").size().eq(6).all()
    baseline = build_patient_baseline(train, "patient_id", "month")
    assert len(baseline) == 400 and baseline.month.eq(0).all()
    generated = generate_cross_sectional(train, None, 30)
    assert generated.patient_id.nunique() == 30
    assert not set(generated.patient_id).intersection(df.patient_id)
    assert "month" not in generated and "patient_id" not in generated.attrs["model_features"]
    assert "month" in generated.attrs["excluded_columns"]

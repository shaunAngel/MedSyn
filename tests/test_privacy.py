"""Tests for patient-level adversarial privacy simulation."""

import numpy as np
import pandas as pd

import privacy


def _source() -> pd.DataFrame:
    rows = []
    for patient in range(12):
        for month in range(3):
            rows.append({
                "patient_id": f"P{patient}", "month": month, "age": 40 + patient,
                "diabetic": patient % 2, "systolic_bp": 110 + patient + month,
                "activity_steps": 6000 + patient * 10 - month, "medication_adherence_pct": 70 + month,
                "pain_score": patient % 6,
            })
    return pd.DataFrame(rows)


def _fake_generator(train_without_ids, _model, n_records):
    return train_without_ids.sample(n=n_records, replace=True, random_state=9).reset_index(drop=True)


def test_patient_level_split_is_disjoint_and_keeps_trajectories_together():
    train, holdout, train_ids, holdout_ids = privacy._patient_split(_source(), "patient_id", 0.75, 42)
    assert set(train_ids).isdisjoint(set(holdout_ids))
    assert set(train.patient_id).isdisjoint(set(holdout.patient_id))
    assert train.groupby("patient_id").size().eq(3).all()
    assert holdout.groupby("patient_id").size().eq(3).all()


def test_attack_excludes_identifier_and_is_reproducible(monkeypatch):
    seen = {}
    def capture_generator(data, model, count):
        seen["columns"] = list(data.columns)
        return _fake_generator(data, model, count)
    monkeypatch.setattr(privacy, "_generate_synthetic", capture_generator)
    first = privacy.run_membership_inference_simulation(_source(), random_state=7)
    second = privacy.run_membership_inference_simulation(_source(), random_state=7)
    assert first["status"] == "ok"
    assert "patient_id" not in first["attack_features"]
    assert "month" not in first["attack_features"]
    assert "patient_id" not in seen["columns"] and "month" not in seen["columns"]
    assert first["attack_auroc"] == second["attack_auroc"]
    assert first["train_distances"] == second["train_distances"]


def test_synthetic_generator_receives_training_patients_only(monkeypatch):
    data = _source()
    train, _holdout, _train_ids, _holdout_ids = privacy._patient_split(data, "patient_id", 0.8, 42)
    seen = {}
    def capture_generator(frame, model, count):
        seen["ages"] = set(frame["age"])
        return _fake_generator(frame, model, count)
    monkeypatch.setattr(privacy, "_generate_synthetic", capture_generator)
    result = privacy.run_membership_inference_simulation(data, random_state=42)
    assert result["status"] == "ok"
    assert seen["ages"] == set(train["age"])


def test_attack_outputs_distances_labels_metrics_and_handles_missing_values(monkeypatch):
    monkeypatch.setattr(privacy, "_generate_synthetic", _fake_generator)
    data = _source()
    data.loc[0, "systolic_bp"] = np.nan
    result = privacy.run_membership_inference_simulation(data)
    assert result["status"] == "ok"
    assert result["n_train_patients"] > 0 and result["n_holdout_patients"] > 0
    assert result["train_distances"] and result["holdout_distances"]
    assert 0 <= result["attack_auroc"] <= 1
    assert set(result["attack_labels"]) == {0, 1}
    assert len(result["confusion_matrix"]) == 2
    assert "formal privacy guarantee" in result["warning"]


def test_unsupported_structure_fails_gracefully(monkeypatch):
    monkeypatch.setattr(privacy, "_generate_synthetic", _fake_generator)
    result = privacy.run_membership_inference_simulation(pd.DataFrame({"patient_id": ["P1", "P2"], "month": [0, 0]}))
    assert result["status"] == "error"

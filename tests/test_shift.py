"""Unit tests for shift.py — MedSyn Population Shift & Drift Analysis."""

import os
import unittest
import pandas as pd
import numpy as np

from shift import (
    compute_population_shift,
    evaluate_shift_risk,
    format_population_shift_table,
    actual_proportions,
)
from feasibility import CohortRequest


class TestShiftRiskEvaluation(unittest.TestCase):
    """Test shift risk and extrapolation metrics."""

    def test_aligned_shift(self):
        # 20% source to 22% target
        risk = evaluate_shift_risk(source_pct=20.0, target_pct=22.0, source_count=100)
        self.assertEqual(risk["severity"], "Minimal Shift (Aligned)")
        self.assertAlmostEqual(risk["delta"], 2.0)
        self.assertGreater(risk["plausibility_score"], 90.0)

    def test_moderate_shift(self):
        # 20% source to 40% target
        risk = evaluate_shift_risk(source_pct=20.0, target_pct=40.0, source_count=100)
        self.assertEqual(risk["severity"], "Moderate Shift")
        self.assertAlmostEqual(risk["delta"], 20.0)

    def test_extreme_extrapolation(self):
        # 0.4% source (2 patients) to 40% target -> 100x ratio!
        risk = evaluate_shift_risk(source_pct=0.4, target_pct=40.0, source_count=2)
        self.assertIn("Extreme Extrapolation", risk["severity"])
        self.assertGreater(risk["ratio"], 50.0)
        self.assertIn("Extreme magnification", risk["warning"])

    def test_zero_source_evidence(self):
        risk = evaluate_shift_risk(source_pct=0.0, target_pct=25.0, source_count=0)
        self.assertIn("Impossible", risk["severity"])
        self.assertEqual(risk["plausibility_score"], 0.0)


class TestPopulationShiftEngine(unittest.TestCase):
    """Test compute_population_shift pre-generation and post-generation."""

    @classmethod
    def setUpClass(cls):
        csv_path = "data/demo_patients.csv"
        if os.path.exists(csv_path):
            cls.df = pd.read_csv(csv_path)
        else:
            cls.df = pd.DataFrame({
                "patient_id": [f"P{i:04d}" for i in range(500)],
                "diabetic": [1 if i < 100 else 0 for i in range(500)],
                "age": [70 if i < 90 else 40 for i in range(500)],
                "medication_adherence_pct": [25 if i in {0, 1} else 80 for i in range(500)],
            })

    def test_pre_generation_shift_table(self):
        request = {
            "target_n": 10000,
            "conditions": [
                {"variable": "diabetic", "operator": "==", "value": 1, "target_pct": 60.0},
                {"variable": "age", "operator": ">", "value": 65, "target_pct": 50.0},
                {"variable": "medication_adherence_pct", "operator": "<", "value": 40, "target_pct": 40.0},
            ],
            "metadata": {"joint_target_pct": 40.0},
        }

        result = compute_population_shift(self.df, request)
        self.assertFalse(result.has_generated)
        df_table = result.to_dataframe()

        # Check rows: 3 conditions + 1 joint combination = 4 rows
        self.assertEqual(len(df_table), 4)

        # Check Diabetic shift
        diab_row = df_table[df_table["Variable"] == "diabetic"].iloc[0]
        self.assertEqual(diab_row["Source %"], 20.0)
        self.assertEqual(diab_row["Target %"], 60.0)
        self.assertEqual(diab_row["Target Shift (Δ)"], "+40.0%")
        self.assertEqual(diab_row["Shift Ratio"], "3.0x")

        # Check Joint row (Triple combo)
        joint_row = df_table[df_table["Variable"] == "Combined (All Conditions)"].iloc[0]
        self.assertEqual(joint_row["Source count"], 2)
        self.assertEqual(joint_row["Target %"], 40.0)
        self.assertIn("Extreme Extrapolation", joint_row["Shift Severity"])

        # Check overall summary
        self.assertEqual(result.extrapolation_risk, "Extreme Extrapolation ⚠️")

    def test_post_generation_shift_table(self):
        request = {
            "target_n": 1000,
            "conditions": [
                {"variable": "diabetic", "operator": "==", "value": 1, "target_pct": 60.0},
            ],
        }

        # Mock generated dataset with 580 diabetics out of 1000 (58.0%)
        gen_df = pd.DataFrame({
            "patient_id": [f"synth_{i}" for i in range(1000)],
            "diabetic": [1 if i < 580 else 0 for i in range(1000)],
            "age": [50 for _ in range(1000)],
        })

        result = compute_population_shift(self.df, request, generated_df=gen_df)
        self.assertTrue(result.has_generated)
        df_table = result.to_dataframe()

        diab_row = df_table[df_table["Variable"] == "diabetic"].iloc[0]
        self.assertEqual(diab_row["Generated %"], 58.0)
        self.assertEqual(diab_row["Target Error (Δ)"], "-2.0%")
        self.assertEqual(diab_row["Target Status"], "Achieved (Within ±3%)")

    def test_actual_proportions_helper(self):
        request = {
            "conditions": [
                {"variable": "diabetic", "operator": "==", "value": 1, "target_pct": 60.0},
            ]
        }
        gen_df = pd.DataFrame({
            "diabetic": [1] * 60 + [0] * 40,
        })
        act_df = actual_proportions(gen_df, request)
        self.assertEqual(len(act_df), 1)
        self.assertEqual(act_df.iloc[0]["Generated %"], 60.0)
        self.assertEqual(act_df.iloc[0]["Status"], "Achieved")


if __name__ == "__main__":
    unittest.main()

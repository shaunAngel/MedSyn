"""Unit tests for feasibility.py — MedSyn Cohort Intelligence."""

import os
import unittest
import pandas as pd
import numpy as np

from feasibility import (
    CohortCondition,
    CohortRequest,
    CohortValidationError,
    EvidenceTier,
    check_feasibility,
    classify_evidence,
    confirm_sparse,
    find_patient_identifier,
    validate_cohort_request,
)


class TestCohortSchema(unittest.TestCase):
    """Test CohortCondition and CohortRequest validation."""

    def test_valid_condition(self):
        cond = CohortCondition(variable="age", operator=">", value=65, target_pct=50.0)
        self.assertEqual(cond.variable, "age")
        self.assertEqual(cond.operator, ">")
        self.assertEqual(cond.value, 65)
        self.assertEqual(cond.target_pct, 50.0)
        self.assertEqual(cond.format_expression(), "age > 65")

    def test_condition_invalid_operator(self):
        with self.assertRaises(CohortValidationError):
            CohortCondition(variable="age", operator="~=", value=65, target_pct=50.0)

    def test_condition_invalid_percentage(self):
        with self.assertRaises(CohortValidationError):
            CohortCondition(variable="age", operator=">", value=65, target_pct=150.0)
        with self.assertRaises(CohortValidationError):
            CohortCondition(variable="age", operator=">", value=65, target_pct=-5.0)

    def test_valid_request(self):
        req = CohortRequest(
            target_n=10000,
            conditions=[
                CohortCondition(variable="diabetic", operator="==", value=1, target_pct=60.0),
                {"variable": "age", "operator": ">", "value": 65, "target_pct": 50.0},
            ],
        )
        self.assertEqual(req.target_n, 10000)
        self.assertEqual(len(req.conditions), 2)
        self.assertIsInstance(req.conditions[1], CohortCondition)

    def test_request_invalid_target_n(self):
        with self.assertRaises(CohortValidationError):
            CohortRequest(target_n=0, conditions=[])
        with self.assertRaises(CohortValidationError):
            CohortRequest(target_n=-500, conditions=[])

    def test_validation_against_dataset_missing_column(self):
        df = pd.DataFrame({"age": [50, 60], "diabetic": [0, 1]})
        req = CohortRequest(
            target_n=1000,
            conditions=[
                CohortCondition(variable="cholesterol", operator=">", value=200, target_pct=30.0)
            ],
        )
        with self.assertRaises(CohortValidationError) as ctx:
            req.validate_against_dataset(df)
        self.assertIn("cholesterol", str(ctx.exception))


class TestPatientIdentifier(unittest.TestCase):
    """Test patient ID discovery in longitudinal and cross-sectional datasets."""

    def test_finds_patient_id(self):
        df = pd.DataFrame({"patient_id": ["P1", "P2"], "age": [30, 40]})
        self.assertEqual(find_patient_identifier(df), "patient_id")

    def test_finds_subject_id(self):
        df = pd.DataFrame({"subject_id": [1, 2], "val": [10, 20]})
        self.assertEqual(find_patient_identifier(df), "subject_id")

    def test_finds_mrn(self):
        df = pd.DataFrame({"hospital_mrn": ["M1", "M2"]})
        self.assertEqual(find_patient_identifier(df), "hospital_mrn")

    def test_no_identifier(self):
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        self.assertIsNone(find_patient_identifier(df))


class TestEvidenceClassification(unittest.TestCase):
    """Test classification into Strong, Moderate, Weak, and Sparse."""

    def test_sparse_tier(self):
        # Count < 10 or pct < 1%
        self.assertEqual(classify_evidence(count=2, pct=0.4, total_patients=500), EvidenceTier.SPARSE)
        self.assertEqual(classify_evidence(count=9, pct=1.8, total_patients=500), EvidenceTier.SPARSE)
        self.assertEqual(classify_evidence(count=0, pct=0.0, total_patients=500), EvidenceTier.SPARSE)

    def test_weak_tier(self):
        self.assertEqual(classify_evidence(count=15, pct=3.0, total_patients=500), EvidenceTier.WEAK)
        self.assertEqual(classify_evidence(count=25, pct=5.0, total_patients=500), EvidenceTier.WEAK)

    def test_moderate_tier(self):
        self.assertEqual(classify_evidence(count=60, pct=12.0, total_patients=500), EvidenceTier.MODERATE)
        self.assertEqual(classify_evidence(count=90, pct=18.0, total_patients=500), EvidenceTier.MODERATE)

    def test_strong_tier(self):
        self.assertEqual(classify_evidence(count=150, pct=30.0, total_patients=500), EvidenceTier.STRONG)
        self.assertEqual(classify_evidence(count=100, pct=20.0, total_patients=500), EvidenceTier.STRONG)


class TestFeasibilityEngine(unittest.TestCase):
    """Test full feasibility evaluation on realistic patient datasets."""

    @classmethod
    def setUpClass(cls):
        # Load the demo dataset generated for the project
        csv_path = "data/demo_patients.csv"
        if os.path.exists(csv_path):
            cls.df = pd.read_csv(csv_path)
        else:
            # Synthetic fallback fixture if running in isolated environment
            rng = np.random.default_rng(405)
            rows = []
            for p in range(500):
                pid = f"P{p:04d}"
                diab = 1 if p < 100 else 0
                age = 70 if p < 90 else 50
                adh = 25 if (p in {0, 1} or (p >= 100 and p < 203)) else 80
                for m in range(6):
                    rows.append({
                        "patient_id": pid, "month": m, "age": age,
                        "diabetic": diab, "medication_adherence_pct": adh,
                    })
            cls.df = pd.DataFrame(rows)

    def test_reference_prompt_scenario_sparse(self):
        """Test the exact scenario from Person 2 requirements:
        REQUEST:
        Diabetic: 60%
        Age >65: 50%
        Low adherence: 40%

        SOURCE:
        Diabetic: 20%
        Age >65: 18%
        Triple combo: 2 patients (0.4%)

        FEASIBILITY: SPARSE ⚠️
        """
        request = {
            "target_n": 10000,
            "conditions": [
                {"variable": "diabetic", "operator": "==", "value": 1, "target_pct": 60.0},
                {"variable": "age", "operator": ">", "value": 65, "target_pct": 50.0},
                {"variable": "medication_adherence_pct", "operator": "<", "value": 40, "target_pct": 40.0},
            ],
        }

        result = check_feasibility(self.df, request)

        # 1. Overall feasibility must be SPARSE
        self.assertEqual(result.overall, "Sparse")
        self.assertEqual(result["overall"], "Sparse")
        self.assertTrue(result.requires_confirmation)
        self.assertTrue(result["requires_confirmation"])

        # 2. Individual conditions count and prevalence
        conds = result.conditions
        self.assertEqual(len(conds), 3)

        diab_cond = next(c for c in conds if c["Variable"] == "diabetic")
        self.assertEqual(diab_cond["Source count"], 100)
        self.assertEqual(diab_cond["Source %"], 20.0)

        age_cond = next(c for c in conds if c["Variable"] == "age")
        self.assertEqual(age_cond["Source count"], 90)
        self.assertEqual(age_cond["Source %"], 18.0)

        # 3. Triple combo evaluation
        combo = result.combination
        self.assertEqual(combo["order"], 3)
        self.assertEqual(combo["source_count"], 2)
        self.assertAlmostEqual(combo["source_pct"], 0.4, places=1)
        self.assertEqual(combo["Evidence"], "Sparse")

        # 4. Confirmation message content
        self.assertIn("2 patient(s)", result["confirmation_message"])
        self.assertIn("Explicit confirmation is required", result["confirmation_message"])

    def test_two_way_combinations_calculated(self):
        request = {
            "target_n": 5000,
            "conditions": [
                {"variable": "diabetic", "operator": "==", "value": 1, "target_pct": 50.0},
                {"variable": "age", "operator": ">", "value": 65, "target_pct": 40.0},
            ],
        }
        result = check_feasibility(self.df, request)
        self.assertEqual(len(result.two_way_combinations), 1)
        pair = result.two_way_combinations[0]
        self.assertEqual(pair["Combination"], "diabetic & age")
        self.assertIn("Source count", pair)
        self.assertIn("Source %", pair)

    def test_confirmation_bypass_helper(self):
        request = {"target_n": 1000, "conditions": [{"variable": "diabetic", "operator": "==", "value": 1, "target_pct": 20.0}]}
        # Confirming without acknowledgment must raise PermissionError
        with self.assertRaises(PermissionError):
            confirm_sparse(request, acknowledged=False)
        # With acknowledgment, succeeds
        self.assertTrue(confirm_sparse(request, acknowledged=True))

    def test_mapping_interface_for_app_py(self):
        """Verify that result acts as a Mapping matching app.py contract."""
        request = {
            "target_n": 5000,
            "conditions": [{"variable": "diabetic", "operator": "==", "value": 1, "target_pct": 20.0}],
        }
        result = check_feasibility(self.df, request)
        self.assertIn("overall", result)
        self.assertIn("conditions", result)
        self.assertIn("combination", result)
        self.assertEqual(result.get("overall"), result["overall"])
        self.assertIsInstance(result.to_dataframe(), pd.DataFrame)


if __name__ == "__main__":
    unittest.main()

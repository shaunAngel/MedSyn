"""Integration test verifying app.py can import and interact with feasibility and shift."""

import unittest
import pandas as pd
import app


class TestAppIntegration(unittest.TestCase):
    """Test that app.py uses feasibility and shift correctly."""

    def setUp(self):
        self.data = pd.read_csv("data/demo_patients.csv")
        self.request = {
            "target_n": 10000,
            "conditions": [
                {"variable": "diabetic", "operator": "==", "value": 1, "target_pct": 60.0},
                {"variable": "age", "operator": ">", "value": 65, "target_pct": 50.0},
                {"variable": "medication_adherence_pct", "operator": "<", "value": 40, "target_pct": 40.0},
            ],
        }

    def test_app_check_feasibility_uses_real_module(self):
        """app._check_feasibility must invoke backend.feasibility or feasibility."""
        result = app._check_feasibility(self.data, self.request)
        self.assertIsInstance(result, dict)
        # Verify it did not fall back to mock
        self.assertFalse(result.get("development_fallback", True), "Expected real feasibility module, got fallback")
        self.assertEqual(result["overall"], "Sparse")
        self.assertEqual(result["combination"]["source_count"], 2)
        self.assertEqual(result["combination"]["order"], 3)
        self.assertTrue(result["requires_confirmation"])

    def test_app_actual_proportions(self):
        """app._actual_proportions should run properly."""
        synthetic_sample = self.data.sample(n=1000, replace=True, random_state=42)
        df_props = app._actual_proportions(synthetic_sample, self.request)
        self.assertIsInstance(df_props, pd.DataFrame)
        self.assertEqual(len(df_props), 3)
        self.assertIn("Source target %", df_props.columns)
        self.assertIn("Generated %", df_props.columns)


if __name__ == "__main__":
    unittest.main()

"""Unit checks for the HRI transformations and classes."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/calculate_hri.py"
SPEC = importlib.util.spec_from_file_location("calculate_hri", SCRIPT)
HRI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HRI)


class HriFunctionTests(unittest.TestCase):
    def test_log_cap_scale_bounds_and_missing(self):
        values = pd.Series([0.0, 1.0, 9.0, np.nan])
        result = HRI.log_cap_scale(values, 9.0)
        self.assertEqual(result.iloc[0], 0)
        self.assertEqual(result.iloc[2], 1)
        self.assertTrue(result.iloc[1] > 0)
        self.assertTrue(np.isnan(result.iloc[3]))

    def test_values_above_reference_are_capped(self):
        result = HRI.log_cap_scale(pd.Series([100.0]), 9.0)
        self.assertEqual(result.iloc[0], 1)

    def test_fixed_class_boundaries(self):
        result = HRI.fixed_class(pd.Series([0, 100 / 3, 50, 200 / 3, 100]))
        self.assertEqual(result.tolist(), ["Low", "Low", "Moderate", "Moderate", "High"])

    def test_weighted_score_requires_every_component(self):
        data = pd.DataFrame({"a": [0.2, np.nan], "b": [0.8, 0.5],
                             "core_hri_eligible": [True, True]})
        score, eligible = HRI.weighted_score(data, {"a": 0.5, "b": 0.5})
        self.assertAlmostEqual(score.iloc[0], 50)
        self.assertTrue(np.isnan(score.iloc[1]))
        self.assertEqual(eligible.tolist(), [True, False])

    def test_auc_ordering(self):
        self.assertEqual(HRI.binary_auc([False, False, True, True], [0, 1, 2, 3]), 1)
        self.assertEqual(HRI.binary_auc([False, False, True, True], [3, 2, 1, 0]), 0)


if __name__ == "__main__":
    unittest.main()

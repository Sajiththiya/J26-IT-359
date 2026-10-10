"""Checks for provisional weighting, missingness and fixed calibration."""
import json
import types
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "notebooks/hri/08_expanded_hri_provisional_weights.ipynb"
MODULE = types.ModuleType("expanded_hri_notebook")
MODULE.ROOT = ROOT
for cell in json.loads(PATH.read_text())["cells"]:
    if cell["cell_type"] == "code" and "expanded_definitions" in cell.get("metadata", {}).get("tags", []):
        exec(compile("".join(cell["source"]), str(PATH), "exec"), MODULE.__dict__)


class ExpandedHriTests(unittest.TestCase):
    def test_primary_and_alternative_weights_sum_to_one(self):
        for domain_weights in [MODULE.CONFIG["domain_weights"], MODULE.CONFIG["forest_climate_only_weights"],
                               *MODULE.CONFIG["domain_sensitivity_scenarios"].values()]:
            weights = MODULE.flatten_weights(domain_weights)
            self.assertAlmostEqual(sum(weights.values()), 1)
            self.assertTrue(all(v > 0 for v in weights.values()))

    def test_missing_weight_is_not_renormalized_or_zero_filled(self):
        frame = pd.DataFrame({"a": [.2, .2], "b": [.8, np.nan]})
        score, available = MODULE.weighted_index(frame, {"a": .5, "b": .5}, pd.Series([True, True]))
        self.assertEqual(score.iloc[0], 50)
        self.assertTrue(pd.isna(score.iloc[1]))
        self.assertEqual(available.iloc[1], .5)

    def test_ineligible_rows_cannot_receive_score(self):
        frame = pd.DataFrame({"a": [.2]})
        score, _ = MODULE.weighted_index(frame, {"a": 1.}, pd.Series([False]))
        self.assertTrue(score.isna().all())

    def test_negative_or_nonfinite_weights_rejected(self):
        for weights in [{"a": -.1, "b": 1.1}, {"a": np.nan}, {"a": 2.}]:
            with self.assertRaises(ValueError):
                MODULE.validate_weights(weights)

    def test_later_values_cannot_change_frozen_reference_scale(self):
        mask = pd.Series([True, True, False])
        original, upper = MODULE.frozen_scale(pd.Series([1., 2., 100.]), mask)
        altered, changed_upper = MODULE.frozen_scale(pd.Series([1., 2., 1e9]), mask)
        self.assertEqual(upper, changed_upper)
        np.testing.assert_allclose(original.iloc[:2], altered.iloc[:2])

    def test_negative_population_is_missing_but_absolute_departures_are_allowed(self):
        values = pd.Series([-2., 1., 3.])
        mask = pd.Series([True, True, True])
        population, _ = MODULE.frozen_scale(values, mask, logarithmic=True)
        climate, _ = MODULE.frozen_scale(values, mask, absolute=True)
        self.assertTrue(pd.isna(population.iloc[0]))
        self.assertTrue(np.isfinite(climate.iloc[0]))

    def test_terrain_and_raw_land_cover_do_not_receive_arbitrary_penalty(self):
        weights = MODULE.flatten_weights(MODULE.CONFIG["domain_weights"])
        self.assertFalse(any("terrain" in key or "elevation" in key or "land_cover" in key for key in weights))


if __name__ == "__main__":
    unittest.main()

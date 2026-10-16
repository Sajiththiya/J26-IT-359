"""Forecast horizon, past-only inputs, class contract and split leakage tests."""
import sys
import json
import types
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "notebooks/hri/HRI_t_plus_1"


def notebook_definitions(filename, tag, module_name, initial=None):
    module = types.ModuleType(module_name)
    module.__dict__.update(initial or {})
    module.ROOT = ROOT
    module.__dict__["__name__"] = module_name
    sys.modules[module_name] = module
    path = DIRECTORY / filename
    for cell in json.loads(path.read_text())["cells"]:
        if cell["cell_type"] == "code" and tag in cell.get("metadata", {}).get("tags", []):
            exec(compile("".join(cell["source"]), str(path), "exec"), module.__dict__)
    return module


data = notebook_definitions("00_hri_t_plus_1_data_preparation.ipynb", "runtime_data", "forecast_data")
training = notebook_definitions("04_model_comparison_and_final_test.ipynb", "runtime_training", "training", data.__dict__)
add_next_year_targets, build_frame, spatial_blocks = data.add_next_year_targets, data.build_frame, data.spatial_blocks
risk_class, RAW_FEATURES, CORE, FEATURES, WEIGHTS = data.risk_class, data.RAW_FEATURES, data.CORE, data.FEATURES, data.WEIGHTS
blocked_forward_cv = training.blocked_forward_cv


class ForecastTests(unittest.TestCase):
    def test_target_join_skips_missing_year_and_never_crosses_cells(self):
        scores = pd.DataFrame({"cell_id": ["a", "a", "a", "b"],
                               "reference_year": [2020, 2021, 2023, 2021],
                               "hri_score_0_100": [10., 20., 90., 50.]})
        out = add_next_year_targets(scores, scores)
        self.assertEqual(out.loc[0, "target_hri_score_t1"], 20)
        self.assertTrue(out.loc[1:, "target_hri_score_t1"].isna().all())
        self.assertEqual(out.loc[0, "target_hri_change_t1"], 10)

    def test_exact_class_boundaries_match_hri_release(self):
        actual = risk_class([0, 100/3, 50, 200/3, 100]).tolist()
        self.assertEqual(actual, ["Low", "Low", "Moderate", "Moderate", "High"])

    def test_negative_grid_coordinates_use_floor_blocks(self):
        actual = spatial_blocks(pd.Series(["lka_laea_5000m_-1_-1", "lka_laea_5000m_0_0", "lka_laea_5000m_4_4"])).tolist()
        self.assertEqual(actual, ["-1:-1", "0:0", "0:0"])

    def test_forward_cv_has_no_time_cell_or_block_overlap(self):
        frame = pd.DataFrame([{"cell_id": f"c{b}", "spatial_block": f"b{b}", "target_year_t1": y}
                              for b in range(12) for y in range(2015, 2020)])
        folds, _ = blocked_forward_cv(frame)
        for a, b in folds:
            fit, assessment = frame.iloc[a], frame.iloc[b]
            self.assertLess(fit.target_year_t1.max(), assessment.target_year_t1.min())
            self.assertFalse(set(fit.cell_id) & set(assessment.cell_id))
            self.assertFalse(set(fit.spatial_block) & set(assessment.spatial_block))

    def test_future_measurement_cannot_change_earlier_predictors(self):
        years = list(range(2005, 2017))
        master = pd.DataFrame({"cell_id": ["lka_laea_5000m_0_0"]*len(years), "reference_year": years})
        for col in RAW_FEATURES:
            master[col] = .1
        loss = np.arange(1, len(years)+1) * .001
        master["forest__annual_loss_fraction_of_baseline"] = loss
        master["forest__cumulative_prior_loss_fraction_of_baseline"] = np.cumsum(loss)-loss
        recent = pd.Series(loss).shift(1).rolling(3, min_periods=3).sum().fillna(0).to_numpy()
        hri = master[["cell_id", "reference_year"]].copy()
        hri[CORE[0]], hri[CORE[3]] = .3, .2
        hri[CORE[1]] = np.log1p(recent)/np.log1p(1.)
        hri[CORE[2]] = np.log1p(master["forest__cumulative_prior_loss_fraction_of_baseline"])/np.log1p(1.)
        hri["hri_score_0_100"] = hri[CORE].mul(pd.Series(WEIGHTS)).sum(axis=1)*100
        scales = {"recent_loss_p99_2010_2014": 1., "cumulative_loss_p99_2010_2014": 1.}
        original = build_frame(master, hri, scales)
        modified = hri.copy()
        modified.loc[modified.reference_year.eq(2016), CORE[0]] = .8
        modified["hri_score_0_100"] = modified[CORE].mul(pd.Series(WEIGHTS)).sum(axis=1)*100
        altered = build_frame(master, modified, scales)
        pd.testing.assert_frame_equal(original.loc[original.reference_year.eq(2014), FEATURES],
                                      altered.loc[altered.reference_year.eq(2014), FEATURES])
        self.assertNotEqual(original.loc[original.reference_year.eq(2015), "target_hri_score_t1"].iloc[0],
                            altered.loc[altered.reference_year.eq(2015), "target_hri_score_t1"].iloc[0])


if __name__ == "__main__":
    unittest.main()

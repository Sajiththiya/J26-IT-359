"""Small synthetic tests for temporal leakage and fragmentation edge cases."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/prepare_hri_inputs.py'
spec = importlib.util.spec_from_file_location('hri_inputs', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FragmentationTests(unittest.TestCase):
    def setUp(self):
        self.data = {'treecover2000': np.full((5, 5), 50, dtype=np.uint8),
                     'lossyear': np.zeros((5, 5), dtype=np.uint8),
                     'datamask': np.ones((5, 5), dtype=np.uint8)}
        self.inside = np.ones((5, 5), dtype=bool)

    def test_intact_patch(self):
        r = m.fragment_metrics(self.data, self.inside, 2010)
        self.assertEqual(r['cell_patch_count'], 1)
        self.assertEqual(r['largest_cell_patch_land_fraction'], 1)
        self.assertEqual(r['edge_m_per_land_ha'], 0)
        self.assertTrue(np.isnan(r['mean_nearest_patch_centroid_m']))

    def test_future_loss_does_not_change_present(self):
        a = m.fragment_metrics(self.data, self.inside, 2010)
        self.data['lossyear'][2, :] = 23
        b = m.fragment_metrics(self.data, self.inside, 2010)
        pd.testing.assert_series_equal(pd.Series(a), pd.Series(b))
        self.assertEqual(m.fragment_metrics(self.data, self.inside, 2023)['cell_patch_count'], 2)

    def test_zero_forest_is_explicit(self):
        self.data['treecover2000'][:] = 0
        r = m.fragment_metrics(self.data, self.inside, 2010)
        self.assertTrue(r['no_forest'])
        self.assertEqual(r['fragmentation_status'], 'no_forest')
        self.assertEqual(r['largest_cell_patch_land_fraction'], 0)
        self.assertTrue(np.isnan(r['largest_cell_patch_forest_fraction']))

    def test_water_is_observed_but_not_land(self):
        self.data['datamask'][0, :] = 2
        r = m.fragment_metrics(self.data, self.inside, 2010)
        self.assertEqual(r['mapped_observation_coverage'], 1)
        self.assertEqual(r['mapped_land_pixels'], 20)
        self.assertEqual(r['largest_cell_patch_land_fraction'], 1)

    def test_missing_is_not_water_or_zero_risk(self):
        self.data['datamask'][0, :] = 0
        r = m.fragment_metrics(self.data, self.inside, 2010)
        self.assertEqual(r['fragmentation_status'], 'insufficient_coverage')
        self.assertTrue(np.isnan(r['edge_m_per_land_ha']))

    def test_threshold_includes_exactly_thirty(self):
        self.data['treecover2000'][:] = 30
        self.assertEqual(m.fragment_metrics(self.data, self.inside, 2010)['cell_patch_count'], 1)
        self.assertEqual(m.fragment_metrics(self.data, self.inside, 2010, threshold=50)['cell_patch_count'], 0)

    def test_diagonals_are_not_connected(self):
        self.data['treecover2000'][:] = 0
        self.data['treecover2000'][1, 1] = 50
        self.data['treecover2000'][2, 2] = 50
        self.assertEqual(m.fragment_metrics(self.data, self.inside, 2010)['cell_patch_count'], 2)


if __name__ == '__main__':
    unittest.main()

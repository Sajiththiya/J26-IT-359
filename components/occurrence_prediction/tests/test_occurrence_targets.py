"""Regression checks for false absence, shared surveys and target leakage."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('targets', ROOT / 'scripts/data/build_occurrence_targets.py')
targets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(targets)


class LabelEvidenceTests(unittest.TestCase):
    def test_detection_survives_incomplete_checklist(self):
        self.assertEqual(targets.target_label(True, True, False, False), (1, 'detected'))

    def test_missing_species_on_incomplete_survey_is_unknown(self):
        self.assertIsNone(targets.target_label(False, True, False, True)[0])

    def test_filtered_or_unverified_species_list_cannot_produce_zero(self):
        self.assertIsNone(targets.target_label(False, False, True, True)[0])

    def test_inappropriate_survey_cannot_produce_zero(self):
        self.assertIsNone(targets.target_label(False, True, True, False)[0])

    def test_complete_verified_eligible_survey_supports_non_detection(self):
        self.assertEqual(targets.target_label(False, True, True, True), (0, 'verified_non_detection'))

    def test_released_training_surveys_are_independent_and_targets_are_separate(self):
        import json
        import pandas as pd
        folder = ROOT / 'data/processed/occurrence/targets_v1'
        data = pd.read_csv(folder / 'occurrence_training_dataset.csv')
        manifest = json.loads((ROOT / 'data/metadata/occurrence/targets_v1/manifest.json').read_text())
        self.assertEqual(len(data), manifest['selected_independent_surveys'] * 24)
        self.assertEqual(set(data.target_occurrence), {0, 1})
        self.assertEqual(data.groupby('survey_group_id').checklist_id.nunique().max(), 1)
        self.assertFalse(data.duplicated(['checklist_id', 'scientific_name']).any())
        self.assertTrue(set(manifest['X']).isdisjoint(manifest['exclude_from_X']))
        self.assertTrue(data.all_species_reported.eq(1).all())
        audit = pd.read_csv(ROOT / 'data/interim/occurrence/targets_v1/checklist_verification.csv')
        used = audit[audit.checklist_id.isin(data.checklist_id)]
        self.assertTrue(used.source_verified.all() and used.complete_checklist_verified.all() and used.eligible_survey.all())
        for cid, sub in data.groupby('checklist_id'):
            listed = used.loc[used.checklist_id.eq(cid), 'verified_detected_species'].iloc[0]
            expected = set(str(listed).split('|')) if pd.notna(listed) else set()
            self.assertEqual(set(sub.loc[sub.target_occurrence.eq(1), 'scientific_name']), expected)


if __name__ == '__main__':
    unittest.main()

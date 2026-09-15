"""Create checklist/species detection targets verified against the original eBird export.

Run: python3 scripts/data/build_occurrence_targets.py
Dependencies: pandas, numpy. Original input CSVs are read only.
"""
from __future__ import annotations

import argparse
import collections
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
VERSION = 'targets_v1'
REFERENCE = 'https://ebird.github.io/ebird-best-practices/ebird.html'
META_FIELDS = {
    'latitude': 'LATITUDE', 'longitude': 'LONGITUDE',
    'observation_date': 'OBSERVATION DATE', 'duration_minutes': 'DURATION MINUTES',
    'effort_distance_km': 'EFFORT DISTANCE KM', 'protocol': 'PROTOCOL NAME',
    'all_species_reported': 'ALL SPECIES REPORTED',
}
NUMERIC = {'latitude', 'longitude', 'duration_minutes', 'effort_distance_km', 'all_species_reported'}
FEATURES = ['scientific_name', 'latitude', 'longitude', 'year', 'month',
            'temperature_mean_c', 'rainfall_mm', 'elevation_m', 'ndvi', 'land_cover',
            'duration_minutes', 'survey_distance_km', 'protocol', 'hours_of_day', 'number_observers']


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def normalize(value, numeric=False):
    if value is None or pd.isna(value) or str(value).strip() == '':
        return ''
    s = str(value).strip()
    if numeric:
        try:
            return str(Decimal(s).normalize())
        except InvalidOperation:
            pass
    return s


def signature(row, original=False):
    return tuple(normalize(row[b if original else a], a in NUMERIC) for a, b in META_FIELDS.items())


def target_label(detected, verified, complete, suitable):
    """1 = detection; 0 = verified suitable complete-checklist non-detection."""
    if detected:
        return 1, 'detected'
    if verified and complete and suitable:
        return 0, 'verified_non_detection'
    return None, 'unknown'


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def hour(value):
    try:
        parts = str(value).split(':')
        result = int(parts[0]) + int(parts[1]) / 60
        return result if 0 <= result < 24 else np.nan
    except (ValueError, IndexError):
        return np.nan


def read_original(path, checklists, input_ids, species_map):
    evidence = {}
    matched_ids = set()
    row_count = 0
    all_species = set()
    with Path(path).open() as f:
        for row in csv.DictReader(f, delimiter='\t'):
            row_count += 1
            cid = row['SAMPLING EVENT IDENTIFIER']
            if cid not in checklists:
                continue
            a = evidence.setdefault(cid, {
                'signatures': set(), 'species': set(), 'detected': set(), 'unapproved_targets': set(),
                'rows': 0, 'group_ids': set(), 'times': set(), 'observers': set(), 'countries': set(),
            })
            a['rows'] += 1
            a['signatures'].add(signature(row, True))
            a['group_ids'].add(row['GROUP IDENTIFIER'].strip())
            a['times'].add(row['TIME OBSERVATIONS STARTED'].strip())
            a['observers'].add(row['NUMBER OBSERVERS'].strip())
            a['countries'].add(row['COUNTRY CODE'].strip())
            a['species'].add(row['SCIENTIFIC NAME'])
            all_species.add(row['SCIENTIFIC NAME'])
            name = species_map.get(row['SCIENTIFIC NAME'])
            if name and row['CATEGORY'] in {'species', 'issf', 'form'}:
                # X indicates detected but not counted. Explicit zero is not a detection.
                count = row['OBSERVATION COUNT'].strip()
                detection = count.upper() == 'X' or number(count) > 0
                if row['APPROVED'] == '1' and detection:
                    a['detected'].add(name)
                elif row['APPROVED'] != '1':
                    a['unapproved_targets'].add(name)
            if row['GLOBAL UNIQUE IDENTIFIER'] in input_ids:
                matched_ids.add(row['GLOBAL UNIQUE IDENTIFIER'])
    return evidence, matched_ids, row_count, len(all_species)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ebd', type=Path, default=Path('/Users/keerthikeerthi/Desktop/Filter data/ebd_LK_relMay-2026.txt'))
    args = parser.parse_args()
    source = ROOT / 'data/processed/requested_observation_dataset.csv'
    scope_path = ROOT / 'data/processed/hri/wp2_v1/final_species_scope.csv'
    metadata_path = ROOT / 'data/processed/requested_observation_dataset_metadata.json'
    input_hash = sha256(source)
    data = pd.read_csv(source)
    scope_all = pd.read_csv(scope_path)
    scope = scope_all[(scope_all.final_inclusion_status == 'include') & (scope_all.endemic_status == 'yes')].copy()
    names = sorted(scope.accepted_scientific_name.unique())
    species_map = dict(zip(scope.scientific_name, scope.accepted_scientific_name))
    species_map.update({name: name for name in names})
    assert len(names) == 24 and data.record_id.is_unique
    fields = [c for c in data.columns if c not in {'record_id', 'scientific_name'}]
    conflicts = data.groupby('checklist_id')[fields].nunique(dropna=False).gt(1).any(axis=1)
    # Preserve missing values: groupby.first() could silently substitute another row.
    checks = data.drop_duplicates('checklist_id')[fields].set_index('checklist_id').sort_index()
    input_detected = collections.defaultdict(set)
    for cid, name in zip(data.checklist_id, data.scientific_name):
        if name in species_map:
            input_detected[cid].add(species_map[name])
    print('Verifying', len(checks), 'checklists against the full original eBird export...', flush=True)
    evidence, recovered_ids, export_rows, source_species_count = read_original(
        args.ebd, set(checks.index), set(data.record_id), species_map)
    if recovered_ids != set(data.record_id):
        raise ValueError('Not every input observation ID is present in the supplied original export.')
    audit_rows = []
    detections = {}
    for cid, row in checks.iterrows():
        e = evidence.get(cid)
        verified = bool(e and e['signatures'] == {signature(row)} and
                        not conflicts[cid] and len(e['group_ids']) == 1 and e['countries'] == {'LK'})
        complete = verified and row.all_species_reported == 1
        groups = sorted(e['group_ids'] - {''}) if e else []
        group_id = groups[0] if len(groups) == 1 else cid
        count = number(next(iter(e['observers']))) if e and len(e['observers']) == 1 else np.nan
        start = hour(next(iter(e['times']))) if e and len(e['times']) == 1 else np.nan
        distance = row.effort_distance_km
        # Structural zero for the derived survey-distance feature only, never an imputation
        # of an unknown traveling distance. The original effort column is preserved.
        survey_distance = 0.0 if row.protocol == 'Stationary' and (pd.isna(distance) or distance == 0) else distance
        reasons = []
        if not verified:
            reasons.append('source_metadata_not_verified')
        if row.all_species_reported != 1:
            reasons.append('incomplete_checklist')
        if row.protocol not in {'Traveling', 'Stationary'}:
            reasons.append('unsupported_protocol')
        if not (pd.notna(row.duration_minutes) and 0 < row.duration_minutes <= 360):
            reasons.append('duration_missing_invalid_or_over_6h')
        distance_valid = ((row.protocol == 'Traveling' and pd.notna(distance) and 0 < distance <= 10) or
                          (row.protocol == 'Stationary' and (pd.isna(distance) or distance == 0)))
        if not distance_valid:
            reasons.append('distance_missing_invalid_or_over_10km')
        speed = survey_distance / (row.duration_minutes / 60) if pd.notna(row.duration_minutes) and row.duration_minutes > 0 else np.nan
        if pd.notna(speed) and speed > 100:
            reasons.append('speed_over_100kmh')
        if not (pd.notna(count) and 1 <= count <= 10):
            reasons.append('observer_count_missing_invalid_or_over_10')
        if pd.isna(start):
            reasons.append('start_time_missing_or_invalid')
        if pd.isna(row.cell_id):
            reasons.append('outside_verified_grid')
        if e and not input_detected[cid].issubset(e['detected']):
            reasons.append('input_detection_not_confirmed_in_original')
        eligible = not reasons
        detections[cid] = e['detected'] if verified else input_detected[cid]
        audit_rows.append({
            'checklist_id': cid, 'survey_group_id': group_id,
            'source_verified': verified, 'complete_checklist_verified': complete,
            'original_observation_rows': e['rows'] if e else 0,
            'original_species_count': len(e['species']) if e else 0,
            'verified_detected_species': '|'.join(sorted(e['detected'])) if e else '',
            'hours_of_day': start, 'number_observers': count,
            'survey_distance_km': survey_distance, 'effort_speed_kmph': speed,
            'eligible_survey': eligible, 'exclusion_reason': ';'.join(reasons),
        })
    audit = pd.DataFrame(audit_rows).set_index('checklist_id')
    # Keep one eligible representative of each shared event. Lexical checklist ID
    # breaks ties without choosing the checklist with the most target detections.
    eligible_ids = audit.index[audit.eligible_survey]
    representatives = set(audit.loc[eligible_ids].reset_index().sort_values('checklist_id')
                          .drop_duplicates('survey_group_id').checklist_id)
    audit['selected_for_training'] = audit.index.isin(representatives)
    checks = checks.join(audit[['survey_group_id', 'hours_of_day', 'number_observers',
                                'survey_distance_km', 'effort_speed_kmph']])
    records = []
    for cid, row in audit.iterrows():
        for name in names:
            unresolved = bool(evidence.get(cid) and name in evidence[cid]['unapproved_targets'])
            y, status = target_label(name in detections[cid], row.source_verified,
                                     row.complete_checklist_verified, row.eligible_survey and not unresolved)
            records.append((cid, row.survey_group_id, name, y, status, row.selected_for_training and y is not None))
    labels = pd.DataFrame(records, columns=['checklist_id', 'survey_group_id', 'scientific_name',
                                           'target_occurrence', 'label_status', 'selected_for_training'])
    labels['target_occurrence'] = labels.target_occurrence.astype('Int8')
    selected = labels[labels.selected_for_training].drop(columns=['selected_for_training'])
    training = selected.merge(checks.drop(columns=['survey_group_id']), left_on='checklist_id',
                              right_index=True, how='left', validate='many_to_one')
    ordered = ['checklist_id', 'survey_group_id', 'scientific_name', 'observation_date',
               'year', 'month', 'cell_id', 'latitude', 'longitude', 'temperature_mean_c',
               'rainfall_mm', 'elevation_m', 'ndvi', 'land_cover', 'duration_minutes',
               'effort_distance_km', 'survey_distance_km', 'protocol', 'all_species_reported',
               'hours_of_day', 'number_observers', 'effort_speed_kmph', 'target_occurrence', 'label_status']
    training = training[ordered].sort_values(['checklist_id', 'scientific_name'])
    assert not training.duplicated(['checklist_id', 'scientific_name']).any()
    assert len(training) == len(representatives) * len(names)
    assert training.target_occurrence.notna().all() and set(training.target_occurrence.unique()) == {0, 1}
    assert training.groupby('survey_group_id').checklist_id.nunique().max() == 1
    for cid, sub in training.groupby('checklist_id'):
        assert set(sub.loc[sub.target_occurrence == 1, 'scientific_name']) == detections[cid]
    zero_ids = set(labels.loc[labels.target_occurrence.eq(0).fillna(False), 'checklist_id'])
    assert audit.loc[list(zero_ids), 'eligible_survey'].all()
    assert len(labels) == len(checks) * len(names)
    summary = []
    for name, sub in labels.groupby('scientific_name'):
        t = training[training.scientific_name == name]
        summary.append({'scientific_name': name, 'audit_detected': int(sub.target_occurrence.eq(1).sum()),
                        'audit_non_detected': int(sub.target_occurrence.eq(0).sum()),
                        'audit_unknown': int(sub.target_occurrence.isna().sum()),
                        'training_detected': int(t.target_occurrence.eq(1).sum()),
                        'training_non_detected': int(t.target_occurrence.eq(0).sum()),
                        'training_detection_fraction': float(t.target_occurrence.mean())})
    interim = ROOT / 'data/interim/occurrence' / VERSION
    processed = ROOT / 'data/processed/occurrence' / VERSION
    meta = ROOT / 'data/metadata/occurrence' / VERSION
    for folder in [interim, processed, meta]:
        folder.mkdir(parents=True, exist_ok=True)
    audit.reset_index().to_csv(interim / 'checklist_verification.csv', index=False)
    labels.to_csv(interim / 'checklist_species_targets.csv', index=False)
    training.to_csv(processed / 'occurrence_training_dataset.csv', index=False)
    scope.to_csv(meta / 'species_scope.csv', index=False)
    pd.DataFrame(summary).to_csv(meta / 'target_summary_by_species.csv', index=False)
    feature_missing = training[FEATURES].isna().sum().astype(int).to_dict()
    manifest = {
        'created_date_local': '2026-10-12', 'target': 'target_occurrence',
        'target_definition': {'1': 'Species detected on this checklist', '0': 'Not detected on a verified suitable complete checklist; not confirmed biological absence', 'blank': 'Insufficient evidence for a non-detection'},
        'input_observation_rows': len(data), 'input_checklists': len(checks),
        'endemic_species': len(names), 'full_export_rows_scanned': export_rows,
        'source_taxa_on_input_checklists': source_species_count,
        'verified_checklists': int(audit.source_verified.sum()),
        'complete_verified_checklists': int(audit.complete_checklist_verified.sum()),
        'eligible_checklists_before_shared_event_deduplication': len(eligible_ids),
        'selected_independent_surveys': len(representatives),
        'shared_checklists_removed_from_training': len(eligible_ids) - len(representatives),
        'audit_target_rows': len(labels), 'training_rows': len(training),
        'training_positive_rows': int(training.target_occurrence.eq(1).sum()),
        'training_non_detection_rows': int(training.target_occurrence.eq(0).sum()),
        'audit_unknown_rows': int(labels.target_occurrence.isna().sum()),
        'training_feature_missing_counts': feature_missing,
        'exclusion_reason_counts': collections.Counter(reason for text in audit.exclusion_reason for reason in text.split(';') if reason),
        'effort_rule': {'protocols': ['Traveling', 'Stationary'], 'duration_minutes': '(0,360]', 'travel_distance_km': '(0,10]', 'maximum_speed_kmph': 100, 'observer_count': '[1,10]', 'start_time': 'valid required', 'spatial_scope': 'existing verified Sri Lanka 5km cell'},
        'shared_checklists': 'survey_group_id is the original GROUP IDENTIFIER where supplied, otherwise checklist_id. Training retains the lexically first eligible checklist for each group; labels refer to its own original species list, not an unverified union of shared lists.',
        'X': FEATURES, 'y': 'target_occurrence',
        'grouping_columns': ['survey_group_id', 'checklist_id', 'cell_id', 'year', 'observation_date'],
        'exclude_from_X': ['target_occurrence', 'label_status', 'checklist_id', 'survey_group_id', 'cell_id', 'all_species_reported'],
        'validation_status': 'passed', 'original_files_moved_or_modified': False,
        'inputs': [{'path': str(p), 'sha256': sha256(p)} for p in [source, scope_path, metadata_path, args.ebd]],
        'references': [REFERENCE],
        'limitations': [
            'Sampling frame is only the checklists in the supplied endemic-filtered CSV. Checklists containing no selected endemic observations are not added. Detection frequencies and model probabilities are conditional on this selected frame, not national occupancy.',
            'Species scope follows the existing verified 24-species WP2 release, not a claim to cover all Sri Lankan endemic species. Batrachostomus moniliger is excluded.',
            'Environmental missing values remain missing. Fit preprocessing using training folds only. Land cover switches product/classification in 2021; retain the original metadata.',
            'Weather provider/units remain partially verified. NDVI is a 16-day composite; annual land cover and contemporaneous weather require care for forecasting.',
            'Targets describe checklist detection, not true ecological absence. Use spatial cell blocks and temporal holdouts; never split checklist/species rows independently.',
        ],
    }
    (meta / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    readme = f'''# Endemic bird occurrence targets — {VERSION}

Y is `target_occurrence`: 1 = detected, 0 = not detected on a verified eligible complete survey.
A zero is not evidence of biological absence. Unknown labels are blank in the audit ledger.

## Files

- `data/processed/occurrence/{VERSION}/occurrence_training_dataset.csv`: one row per selected independent survey and target species, with X features and binary Y.
- `data/interim/occurrence/{VERSION}/checklist_verification.csv`: original-export verification, effort checks, shared-event grouping and all exclusion reasons.
- `data/interim/occurrence/{VERSION}/checklist_species_targets.csv`: every input checklist × the 24 endemic species, including unknown labels and excluded surveys.
- `data/metadata/occurrence/{VERSION}/species_scope.csv`: the existing WP2 verified species scope; non-endemic Batrachostomus moniliger excluded.
- `data/metadata/occurrence/{VERSION}/target_summary_by_species.csv`: positive, non-detection and unknown counts.
- `data/metadata/occurrence/{VERSION}/manifest.json`: input checksums, feature lists, rules, coverage and limitations.
- `scripts/data/build_occurrence_targets.py`: reproducible build. Run from the project root with Python, pandas and numpy. Use `--ebd /path/to/original.txt` to change the original-export location.

## Method and use

All {len(data):,} original observation IDs were found in the full Sri Lanka eBird export.
Checklist-level date, coordinates, completeness and effort must agree with the original rows;
inconsistent checklists cannot supply zeros. Detections use approved original species-level
records (including species-identified subspecific forms and X counts). Complete eligible
checklists provide zeros only for missing target species. Positives on incomplete/unsuitable
surveys remain in the audit but are withheld from the binary training release.

Suitable surveys are Traveling or Stationary, 0 < duration <= 360 minutes,
traveling distance 0 < distance <= 10 km, speed <= 100 km/h, 1–10 observers,
valid start time and a verified Sri Lanka grid cell. Stationary distance may be
blank or zero; only the derived `survey_distance_km` becomes a structural zero.
The original `effort_distance_km` is preserved. These effort limits follow the
[eBird best-practices guide]({REFERENCE}#accounting-for-variation-in-effort).

Training keeps one eligible checklist per shared survey group, selected by checklist ID
without selecting for the largest bird list. Its species detections are taken from that
representative's original checklist. Group all species rows from a survey in the same
validation fold. Use `cell_id` for spatial blocks and `year`/`observation_date` for temporal
holdouts. Identifiers, `label_status` and completeness are not normal X features.
Use `scientific_name` as a categorical feature for a joint model, or filter a single species
and remove that constant feature for separate models. The manifest lists X explicitly.

**Sampling limitation:** the supplied CSV selects checklists with an endemic observation.
This release does not add surveys with zero endemic detections. It supports detection
modelling within that selected sampling frame; national occurrence/occupancy modelling
requires a wider complete-checklist sampling frame. No model or train/test split is built here.

Environmental missingness is retained rather than used to alter Y. Fit imputation and
encoding only on training folds. The original environmental metadata continues to apply,
especially the change in land-cover product in 2021 and the NDVI composite interval.

## Release counts

{len(names)} species; {len(checks):,} input checklists; {len(representatives):,} selected independent surveys.
{len(training):,} training rows: {manifest['training_positive_rows']:,} detections and
{manifest['training_non_detection_rows']:,} non-detections. The complete audit retains
{manifest['audit_unknown_rows']:,} unknown targets. Original files are preserved.
'''
    (processed / 'README.md').write_text(readme)
    assert sha256(source) == input_hash
    print(json.dumps({k: manifest[k] for k in ['endemic_species', 'verified_checklists', 'selected_independent_surveys', 'training_rows', 'training_positive_rows', 'training_non_detection_rows', 'audit_unknown_rows']}, indent=2), flush=True)
    print('Saved', processed / 'occurrence_training_dataset.csv', flush=True)


if __name__ == '__main__':
    main()

"""WP2 release; mirrored as visible cells in the cleaning notebook."""
# %% Load existing draft and preserve provenance
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import geopandas as gpd

root = next(p for base in [Path.cwd(), *Path.cwd().parents]
            for p in [base, base / 'components/habitat_risk']
            if (p / 'configs/study.json').exists())
release = root / 'data/processed/hri/wp2_v1'
release.mkdir(parents=True, exist_ok=True)
draft = root / 'data/interim/hri/bird_observations_cleaning_draft.csv'
birds = pd.read_csv(draft, low_memory=False)
if 'source_row_id' not in birds:
    birds.insert(0, 'source_row_id', np.arange(1, len(birds) + 1))
assert birds.source_row_id.is_unique
for col in ['possible_duplicate', 'invalid_date', 'date_fields_disagree', 'count_needs_review']:
    values = birds[col].astype(str).str.strip().str.lower().map({'true': True, 'false': False})
    assert values.notna().all(), f'Invalid Boolean flag: {col}'
    birds[col] = values
birds['reference_year'] = pd.to_datetime(birds.observation_date, errors='coerce').dt.year
birds['observation_day'] = pd.to_datetime(birds.observation_date, errors='coerce').dt.normalize()

# %% Freeze observation species scope independently from vulnerability traits
traits = pd.read_csv(root / 'data/metadata/species_traits.csv')
assert traits.scientific_name.is_unique
assert set(birds.scientific_name) <= set(traits.scientific_name)
scope = traits[['scientific_name', 'accepted_scientific_name', 'endemic_status',
                'taxonomy_standard', 'taxonomy_source', 'endemic_source',
                'taxonomy_match_status', 'notes']].copy()
assert scope.endemic_status.isin(['yes', 'no']).all()
scope['final_inclusion_status'] = np.where(scope.endemic_status.eq('yes'), 'include', 'exclude')
scope['decision_date'] = '2026-10-05'
scope['decision_basis'] = 'Frozen endemic-only design; Clements 2025 names; existing sourced trait register'
scope['trait_status'] = 'Not approved for vulnerability scoring'
scope.to_csv(release / 'final_species_scope.csv', index=False)
birds = birds.merge(scope[['scientific_name', 'accepted_scientific_name', 'final_inclusion_status']],
                    on='scientific_name', how='left', validate='many_to_one')

# %% Recheck national boundary and reuse verified grid assignments
config = json.loads((root / 'configs/study.json').read_text())
boundary_path = root / config['boundary_file']
boundary = gpd.read_file(boundary_path).to_crs(4326)
polygon = boundary.geometry.union_all()
locations = birds[['latitude', 'longitude']].drop_duplicates().copy()
locations['inside_boundary_verified'] = [
    polygon.covers(point) for point in gpd.points_from_xy(locations.longitude, locations.latitude)
]
assignments = pd.read_csv(root / 'data/interim/spatial/lka_laea_5000m_location_assignments.csv')
assert not assignments.duplicated(['latitude', 'longitude']).any()
locations = locations.merge(assignments[['latitude', 'longitude', 'cell_id']],
                            on=['latitude', 'longitude'], how='left', validate='one_to_one')
grid = gpd.read_file(root / 'data/interim/spatial/lka_laea_5000m_grid.geojson').to_crs(4326)
assert grid.cell_id.is_unique
geometries = grid.set_index('cell_id').geometry
locations['grid_verified'] = [
    pd.notna(cid) and cid in geometries.index and geometries.loc[cid].covers(point)
    for cid, point in zip(locations.cell_id, gpd.points_from_xy(locations.longitude, locations.latitude))
]
locations.to_csv(release / 'location_verification.csv', index=False)
birds = birds.merge(locations, on=['latitude', 'longitude'], how='left', validate='many_to_one')
birds['spatial_decision'] = np.where(birds.inside_boundary_verified & birds.grid_verified,
                                     'keep', 'withhold_boundary_or_mapping')
# Outside polygon does not prove the coordinates are wrong; retain without invented corrections.

# %% Apply effort and eligibility decisions while retaining every source row
duration = pd.to_numeric(birds.duration_minutes, errors='coerce')
distance = pd.to_numeric(birds.effort_distance_km, errors='coerce')
birds['duration_minutes_valid'] = duration.where(duration.between(0, 1440))
birds['effort_distance_km_valid'] = distance.where(distance.ge(0) & np.isfinite(distance))
birds['effort_invalid'] = ((duration.notna() & birds.duration_minutes_valid.isna()) |
                           (distance.notna() & birds.effort_distance_km_valid.isna()))
birds['duration_available'] = birds.duration_minutes_valid.notna()
birds['distance_available'] = birds.effort_distance_km_valid.notna()
birds['effort_available'] = birds.duration_available | birds.distance_available
birds['analysis_status'] = 'eligible_occurrence'
birds['decision_reason'] = 'Included endemic; valid date/count; verified boundary and grid'
bad = (birds.invalid_date | birds.date_fields_disagree | birds.count_needs_review |
       ~birds.reference_year.between(2010, 2023) | birds.spatial_decision.ne('keep'))
birds.loc[bad, 'analysis_status'] = 'withheld_review'
birds.loc[bad, 'decision_reason'] = 'Date/count/period or boundary/grid review required; see individual flags'
birds.loc[birds.final_inclusion_status.eq('exclude'), 'analysis_status'] = 'excluded_scope'
birds.loc[birds.final_inclusion_status.eq('exclude'), 'decision_reason'] = 'Non-endemic under frozen observation taxonomy'
eligible = birds.loc[birds.analysis_status.eq('eligible_occurrence')].copy()
other = birds.loc[birds.analysis_status.ne('eligible_occurrence')].copy()
assert len(eligible) + len(other) == len(birds)
assert eligible.cell_id.notna().all()
birds.to_csv(release / 'bird_cleaning_decisions.csv', index=False)
eligible.to_csv(release / 'bird_observations_analysis_ready.csv', index=False)
other.to_csv(release / 'bird_observations_excluded_or_withheld.csv', index=False)

# %% Compare exact duplicates and grid-day-species thinning on identical eligibility rules
keys = ['cell_id', 'reference_year', 'accepted_scientific_name']
dedup = eligible.loc[~eligible.possible_duplicate].copy()
thinned = eligible.sort_values('source_row_id').drop_duplicates(
    ['cell_id', 'observation_day', 'accepted_scientific_name'])
def presence_set(data):
    return set(data[keys].itertuples(index=False, name=None))
primary_presence = presence_set(eligible)
results = []
for name, frame in [('complete', eligible), ('deduplicated', dedup), ('thinned', thinned)]:
    combos = presence_set(frame)
    results.append({'scenario': name, 'records': len(frame), 'presence_combinations': len(combos),
                    'lost_combinations': len(primary_presence - combos),
                    'added_combinations': len(combos - primary_presence)})
    assert combos == primary_presence, f'Unexpected presence changes: {name}'
sensitivity = pd.DataFrame(results)
sensitivity.to_csv(release / 'duplicate_thinning_sensitivity.csv', index=False)
evidence = eligible.groupby(keys).agg(
    observation_record_count=('source_row_id', 'size'),
    possible_duplicate_records=('possible_duplicate', 'sum'),
    unique_days=('observation_day', 'nunique')).reset_index()
assert not evidence.duplicated(keys).any()
evidence.to_csv(release / 'hri_cell_year_species_evidence.csv', index=False)
sample = eligible.groupby(['cell_id', 'reference_year']).agg(
    records=('source_row_id', 'size'), unique_observation_days=('observation_day', 'nunique'),
    species_recorded=('accepted_scientific_name', 'nunique'),
    valid_duration_records=('duration_available', 'sum'),
    valid_distance_records=('distance_available', 'sum'),
    valid_effort_records=('effort_available', 'sum')).reset_index()
sample['highly_sampled'] = sample.records.ge(sample.records.quantile(.95))
sample['effort_coverage_pct'] = sample.valid_effort_records / sample.records * 100
sample.to_csv(release / 'sampling_bias_cell_year.csv', index=False)
# This table covers observed cell-years; missing rows are unknown, never bird absence.

# %% Save a reproducible release report and input checksums
inputs = [draft, boundary_path, root / 'configs/study.json',
          root / 'data/metadata/species_traits.csv',
          root / 'data/interim/spatial/lka_laea_5000m_location_assignments.csv',
          root / 'data/interim/spatial/lka_laea_5000m_grid.geojson']
manifest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
(release / 'input_checksums.json').write_text(json.dumps(manifest, indent=2) + '\n')
report = f'''# WP2 versioned cleaning release

Date: 2026-10-05. Source: existing cleaning draft; source-row IDs are scoped to its recorded checksum.

- Source records: {len(birds):,}; eligible occurrences: {len(eligible):,}; excluded/withheld: {len(other):,}.
- Recorded species scope: {int(scope.final_inclusion_status.eq('include').sum())} included; {int(scope.final_inclusion_status.eq('exclude').sum())} excluded.
- Outside-boundary locations: {int((~locations.inside_boundary_verified).sum())}; records: {int((~birds.inside_boundary_verified).sum())}.
- Invalid effort records retained with invalid measurement fields masked: {int(birds.effort_invalid.sum())}.
- Observed cell-years: {len(sample):,}; cell-year-species combinations: {len(evidence):,}.

## Decisions

Retain exact duplicates in primary evidence because event identity is unavailable. Deduplicated and thinned scenarios preserve exactly the same cell-year-species membership (verified by set equality). Record totals differ; they are not independent survey counts or abundance. Priority sensitivity awaits a defined priority method.

Use Clements 2025 as documented in the existing source register and [Avibase checklist](https://avibase.bsc-eoc.org/checklist.jsp?lang=EN&region=LK), rechecked 2026-10-05. Include Zoothera imbricata for occurrence evidence; its BirdLife assessment mismatch remains unresolved for vulnerability. Exclude Batrachostomus moniliger under endemic-only scope. This freezes the recorded species list, not a claim of complete national species coverage.

Boundary covers includes polygon edges. Outside-boundary points are withheld without changing coordinates or claiming their true location. Original rows and values remain in the decision ledger. All accepted mappings are checked against grid geometry. No missing effort is converted to zero. Sampling metrics use valid effort fields and observed cell-years only.

## Status and limitations

Duplicate review and occurrence sensitivity, effort cleaning, boundary eligibility, recorded species scope and observed cell-year sampling summaries are completed for this release. Recovery of original event identifiers and correction of withheld locations require new source evidence. Trait verification, ecological validation, HRI/priority sensitivity and model training are not completed by WP2.

Use this versioned release instead of the older root-level processed files. Older interim species evidence and unresolved review templates are historical preparation artifacts and have not been silently overwritten.
'''
(release / 'README.md').write_text(report)
print(report)
print(sensitivity.to_string(index=False))

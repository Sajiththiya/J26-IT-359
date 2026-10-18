# Habitat Risk Index methodology — version 1

Prepared 2026-10-09. The executable, supervisor-facing implementation is
`notebooks/hri/06_habitat_risk_index_construction.ipynb`; the identical reusable script is
`scripts/calculate_hri.py`. Outputs are in `data/processed/hri/hri_v1/`.
This stage constructs and validates indices. It does not fit ML models.

## Interpretation and assessment unit

One result row represents one 5 km grid cell in one reference year under one
HRI scenario. The key is `cell_id + reference_year + hri_version`. Scores are
relative environmental-risk evidence for forest-oriented habitat. They are not
habitat suitability, causal effects, bird presence/absence, legal forest
classification, or an estimate of extinction probability.

The primary scope requires year-2000 forest at >=30% canopy cover to occupy at
least 10% of mapped cell land. This applicability threshold prevents naturally
near-zero-forest cells from automatically receiving extreme forest-scarcity
scores. It remains an analytical choice, tested at 5%, 10%, and 20%; expert
review and an alternative grid-size analysis are still needed.

## Core components

| Component | Source | Direction | Transformation |
|---|---|---|---|
| Forest amount | Remaining year-2000 baseline forest / mapped land at end of t | Less forest, more risk | `1 - proportion` |
| Recent loss | Loss during t-3 through t-1 / baseline forest | More recent loss, more risk | `log1p(x) / log1p(reference P99)` |
| Cumulative prior loss | Loss during 2001 through t-1 / baseline forest | More prior loss, more risk | `log1p(x) / log1p(reference P99)` |
| Fragmentation | Forest-edge metres / mapped land hectare at end of t | More edge, more risk | `log1p(x) / log1p(reference P99)` |

The P99 values are frozen from eligible 2010–2014 rows and all components are
clipped to 0–1. This reduces extreme-value dominance and avoids rescaling each
year. A forest-free but otherwise eligible cell receives fragmentation risk 1:
zero remaining edge must not be interpreted as intact, low-risk habitat.

The primary score is:

`core_equal = 100 × mean(forest amount, recent loss, cumulative loss, fragmentation)`

Core loss windows end at t-1. Forest amount and fragmentation describe the end
of t. Validation uses loss at t+1. This avoids using the validation outcome in
the HRI. Retrospective source revisions can still contain information that was
not available operationally in year t; this is a historical association test,
not a real-time forecasting reconstruction.

## Weight scenarios

Equal weighting is primary because verified literature/expert numerical weights
have not been obtained. Two declared alternatives are sensitivity analyses:

- Condition emphasis: 0.40, 0.20, 0.20, 0.20.
- Disturbance emphasis: 0.15, 0.35, 0.30, 0.20.

Two hundred deterministic Dirichlet perturbations around equal weighting test
ranking stability. These draws explore mathematical sensitivity and are not
expert opinions. Leave-one-indicator-out tests assess dependence on individual
components. Cumulative prior loss and recent loss overlap conceptually; the
omission test is therefore required and both should not be described as
independent causal pressures.

## Climate and human-pressure extensions

The exploratory climate version allocates 80% to the four core components and
10% each to absolute temperature and precipitation anomalies. Anomalies are
relative to the 2010–2014 cell reference and scaled with 2015–2019 absolute
anomaly P99 values. Absolute anomalies assume departures in either direction
represent potential stress. This is not species-specific climate tolerance and
must remain labelled exploratory.

The population version allocates 80% to the core and 20% to log-scaled WorldPop
population density. Its consistent coverage ends in 2020. No carry-forward,
interpolation, zero fill, or changing annual weights are used.

Extension validation is compared with the core on the exact same available
rows. Otherwise differences in climate/population coverage can be mistaken for
added value. On matched climate rows, the core had Spearman r about 0.436 with
next-year loss while the exploratory climate HRI had about 0.422; this version
did not improve that association. On matched population rows, pressure HRI had
r about 0.423 versus core r about 0.395, though its top-decile share of future
loss was lower. These are descriptive validation results, not model performance
or causal evidence.

## Classes

The continuous 0–100 score is the primary result. Two communication schemes are
provided:

- Fixed: Low <=33.33, Moderate <=66.67, High >66.67.
- Pooled scenario-specific terciles.

Fixed cut-offs are transparent but not ecologically validated. Terciles force
relative groups and are not absolute safety thresholds. Both are retained so
class dependence can be reported rather than hidden.

## Coverage and version-1 results

- Score rows across five scenarios: 200,830.
- Duplicate cell-year-version keys: 0.
- Primary core scores: 35,350 of 40,166 cell-years (88.0%).
- Exploratory climate scores: 21,078 (52.5%).
- Population-extension scores: 27,393 (68.2%).
- Primary score range: approximately 0.79–94.04.

Primary core HRI versus next-year loss used 32,825 rows and had pooled
Spearman r about 0.393 and AUC about 0.643 for any mapped next-year loss. The
top HRI decile contained about 27.9% of total next-year loss fraction. Pooled
metrics combine repeated cells and years and are not a substitute for spatial
and temporal model validation. Annual results are provided separately.

Weight perturbations showed median rank correlation about 0.998 and median
top-decile Jaccard overlap about 0.924. Indicator omission produced larger
changes, particularly for the cumulative-loss component's top-risk membership.
This supports reporting both score and sensitivity rather than calling the
ranking universally stable.

## Canopy, fragmentation and scale limitations

National 10%, 30%, and 50% forest-condition scenarios have rank correlations
about 0.990–0.997. National fragmentation was calculated for the working 30%
threshold; 10%/50% fragmentation comparisons use a stratified 30-cell sample.
Therefore the canopy output is labelled forest-component sensitivity, not a
complete national alternative-HRI sensitivity result.

The 5 km assessment grid remains provisional. Fragmentation raster/context
sensitivity does not replace recalculation on another assessment grid. The HRI
also omits annual NDVI, complete land-cover transitions, roads, built-up area,
night lights, protected areas and IBAs. It must be described as a forest-oriented
index with explicit climate and population extensions, not a complete measure
of every habitat-pressure dimension.

## Bird evidence

Bird evidence remains one cell-year-species table. `hri_bird_context.csv`
aggregates observed endemic-species richness and record counts once per
cell-year and joins them to the primary core HRI for interpretation. Missing
bird evidence remains missing: no record is not species absence. Sampling bias
prevents raw record counts from becoming environmental HRI components.

## Output files

- `hri_cell_year_scores.csv`: five score scenarios and component risks.
- `hri_core_equal_complete_cases.csv`: primary HRI rows and used fields, no
  missing score/components; no imputation.
- `hri_climate_enhanced_exploratory_complete_cases.csv`: complete climate scenario.
- `hri_pressure_enhanced_complete_cases.csv`: complete population scenario.
- `hri_indicator_definitions.csv`: sources, transformations and directions.
- `hri_weight_scenarios.csv`: explicit scenario weights.
- `hri_class_thresholds.csv`: fixed and pooled-tercile cut-offs.
- `hri_sensitivity_results.csv`: weights, omissions, applicability and canopy checks.
- `hri_validation_results.csv`: pooled and annual t-to-t+1 validation.
- `hri_validation_cell_year.csv`: validation pairs for later analysis.
- `hri_bird_context.csv`: separate bird-evidence interpretation table.
- `hri_missing_data_report.csv`: scenario coverage.
- `hri_ineligibility_reasons.csv`: scenario status and core exclusion reasons.
- `hri_audit.json`: checksums, limits and completion checks.
- `figures/`: distribution, annual trend, validation and map outputs.

The next stage should complete the species-vulnerability evidence, define the
biodiversity-importance calculation, and combine those bird-specific layers
with HRI in a transparent conservation-priority assessment. Forest-loss
prediction is outside the active bird-risk assessment.

# Endemic-bird habitat-risk assessment — active component

## HRI release (2026-10-09)

The executed [`notebooks/hri/06_habitat_risk_index_construction.ipynb`](notebooks/hri/06_habitat_risk_index_construction.ipynb)
calculates the versioned HRI release in `data/processed/hri/hri_v1/` using fully
visible code. The primary `core_equal` result is a forest-oriented environmental
index; climate and population are separately labelled extensions. It includes
weight/indicator/applicability sensitivity, year-t versus year-t+1 forest-loss
validation, bird-evidence context, maps and a machine-readable audit. It does
not train ML models. Read
[`docs/methodology/hri_methodology.md`](docs/methodology/hri_methodology.md)
before interpreting scores or classes.

## Latest preparation release (2026-10-08)

Use [`notebooks/hri/05_hri_input_preparation.ipynb`](notebooks/hri/05_hri_input_preparation.ipynb)
for the full visible code preparing inputs before HRI construction. Its script
equivalent is [`scripts/prepare_hri_inputs.py`](scripts/prepare_hri_inputs.py).
The new output directory is `data/processed/hri/pre_hri_v1/`; see its audit for
actual execution status and coverage. The workflow adds national fragmentation,
a documented working 30% canopy choice with sensitivity tests, WorldPop
2010–2020 population estimates, and a new audited master. Population for
2021–2023 remains missing. HRI weights, transformations, ecological applicability
and validation remain research decisions; no models are trained.

Read [`docs/methodology/pre_hri_data_preparation.md`](docs/methodology/pre_hri_data_preparation.md)
for sources, methods, deferrals and limitations. The older WP5/WP6 creation-time
statements below describe their initial state; saved outputs now exist. Earlier
root-level bird CSVs were archived; `data/processed/hri/wp2_v1/` is the versioned
bird release. Raw/processed datasets remain local and Git-ignored.

This component includes a versioned forest-oriented environmental HRI for the
Sri Lankan endemic-bird risk assessment. Original source data, preprocessing,
grid evidence and incomplete species-trait evidence remain preserved.

## Habitat Risk Index

The executed HRI notebook is
[`notebooks/hri/06_habitat_risk_index_construction.ipynb`](notebooks/hri/06_habitat_risk_index_construction.ipynb);
its reusable implementation is [`scripts/calculate_hri.py`](scripts/calculate_hri.py).
Read [`docs/methodology/hri_methodology.md`](docs/methodology/hri_methodology.md)
before interpreting the outputs in `data/processed/hri/hri_v1/`.

Species vulnerability remains evidence-incomplete, so no numerical conservation
priority score is approved or generated. Forest-loss prediction modelling is
outside the active bird-risk assessment and is not included in this component.

Work Package 3 evidence is tracked in [`literature_review_matrix.xlsx`](literature_review_matrix.xlsx). Its indicator and decision sheets distinguish supported core candidates, conditional candidates, context variables and uncertainty layers. See the [literature-review workflow](docs/methodology/literature_review_workflow.md) before adding indicators or assigning weights.

## Current dataset files

- `data/raw/observations/final_dataset_complete.csv`: ORIGINAL combined observation CSV. Its filename is historical; it is not the final HRI dataset.
- `data/interim/hri/bird_observations_cleaning_draft.csv`: observation cleaning draft, all rows and review flags retained.
- `data/interim/hri/bird_observations_deduplicated_candidate.csv`: separate provisional duplicate-removal candidate, not automatically the accepted dataset.
- `data/interim/hri/endemic_bird_candidates.csv`: endemic-scope candidates with unresolved record/trait review flags.
- `data/interim/hri/hri_cell_year_preparation.csv`: combined grid/forest/weather/terrain evidence with occurrence context.
- `data/interim/hri/hri_cell_year_species_evidence.csv`: linked dated species evidence and source traits.
- `data/interim/hri/endemic_mapping_review.csv`: unmapped/undated records for review.

These are cleaned/preprocessed DRAFTS, not final accepted HRI labels. Keep cell/year environmental and cell/year/species tables separate to avoid multiplying environmental observations. `data/processed/hri/` is reserved for a later documented release. See [DATASETS.md](DATASETS.md).

## Setup and execution

Open this component folder in VS Code, rather than treating the shared repository root as the notebook project root. Then:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Choose the new virtual environment as your notebook kernel. Requirements pin packages used in the source environment; installation on this new environment has not been performed. Historical lock files are retained for provenance. No environment, CDS credentials or Git history was copied.

## Notebook workflow

### Expanded indicators and provisional importance weights

[`08_expanded_hri_provisional_weights.ipynb`](notebooks/hri/08_expanded_hri_provisional_weights.ipynb)
adds an all-variable audit table, nine weighted pressure proxies, explicitly
provisional 60/20/20 forest/climate/population priorities, alternative weights,
and a separate sparse sampled-NDVI illustration. All terrain and product-prefixed
land-cover values are retained as context pending justified risk mappings.
See [expanded methodology](docs/methodology/hri_expanded_provisional.md) for
coverage limits, numerical assumptions and source evidence. This version does
not replace the existing core HRI or its frozen forecasting results.

### HRI(t+1): audited forecasting workflow

Use [`notebooks/hri/HRI_t_plus_1/README.md`](notebooks/hri/HRI_t_plus_1/README.md)
for the new end-of-year t to t+1 workflow. It includes forest inputs and current
HRI, exact next-year labels, 25 km block separation, later-year validation,
forward CV tuning for Ridge/Random Forest/XGBoost, and mean/persistence/known-
component baselines. Existing model CSVs receive future-target annotation
columns, and their earlier fields and split assignments are retained. Core
equal-contribution weights are explicit in `configs/hri.json`; ecological
expert approval is still pending. Read the separate v2 reports before using
these models for SHAP or recommendations.

### Model Experiment 2: nine environmental inputs

The ten notebooks in `notebooks/hri/Model_Training/` now use the six climate
and three terrain features only, with `hri_score_0_100` as target. They exclude
missing-value flags and observation context. Nonfinite/missing selected inputs
or targets are dropped within each frozen split; missing context alone does not
remove a row. The supplied predictors were already imputed during preparation,
so this does not restrict the experiment to originally observed complete cases.
Results are written to `artifacts/hri/experiment_2/<model>/` and compared in
`artifacts/hri/experiment_2/model_summary.csv`. The saved Experiment 1 archive
and existing 18-feature results remain preserved. Final-test scoring stays locked.

### Observation context in the existing model dataset

`scripts/build_final_model_dataset.py` also reads
`data/processed/requested_observation_dataset.csv`. It aggregates sampled NDVI,
elevation, land-cover mode, and survey effort once per checklist/location/date,
then joins by `cell_id + reference_year`. All added columns use `context__`.
The existing 18 model features and HRI targets are unchanged. Missing context
means unavailable evidence; it is not zero species richness, zero effort, or
zero vegetation. Counts summarize checklist-location events, not bird absence.
The CSV's NDVI product, date window and QA provenance have not been established;
these measurements must remain exploratory observation context. `ESA_CCI_*`
and `ESRI_*` categories retain their source prefixes and are not interchangeable
numeric predictors.

Notebook 07 rebuilds the final CSV and scales available numeric context using
training statistics, keeping missing context as missing. Its three existing
split files are refreshed. The final CSV retains physical units, while split
files contain scaled values. No new output files are required. Model-training
notebooks still use their explicit nine-feature lists; added context is excluded
until its suitability for a separate experiment is reviewed.

National annual NDVI would require a separate quality-filtered raster extraction
for every grid cell and year (for example MOD13Q1.061). Observation-point means
cannot replace this measurement. Missing survey duration/distance cannot be
recovered from satellite products. No national raster download or substitution
is performed by this observation integration.

The active notebooks are one numbered sequence under `notebooks/hri/`:

1. `01_bird_occurrence_cleaning_and_review.ipynb`
2. `02_endemic_species_verification.ipynb`
3. `03_environmental_feature_engineering.ipynb`
4. `04_cell_year_dataset_assembly.ipynb`
5. `05_hri_input_preparation.ipynb`
6. `06_habitat_risk_index_construction.ipynb`
7. `07_habitat_risk_split_normalization.ipynb`

Run them in order when rebuilding the workflow. Notebook 07 reads the released
model dataset, preserves its existing cell-level partitions, fits normalization
on training rows only, and writes the three model-input split files. The older root-level notebooks
were removed after their relevant HRI work was incorporated into this sequence.
Existing outputs and historical audit manifests remain preserved.

Next: complete the missing species-trait evidence and approve the vulnerability
and biodiversity-importance rules before generating conservation priority.

## Folder structure

```text
notebooks/hri/      Active numbered HRI notebook workflow
configs/            Study geometry and unresolved HRI decisions
scripts/            Reusable source acquisition and extraction utilities
data/raw/           Original observations, boundaries, forest, weather and terrain
data/interim/hri/   Cleaning drafts, combined evidence and review tables
data/interim/spatial/  Reusable grid and environmental summaries
data/metadata/      Species traits, source registry and download manifests
data/processed/hri/   Reserved for an accepted HRI release
data/splits/hri/    Reserved for HRI validation partitions
reports/            Source audits, coverage checks and figures
docs/               Current HRI workflow, source setup and original proposal
artifacts/hri/      HRI model experiments, forecast evaluations and reports
```

## Provenance and transfer

`reports/audits/repository_transfer_manifest.json` records checksums and source paths. Source paths in old manifests are provenance, not instructions to read files from another machine. The legacy-weather audit now uses its copied local source. No preprocessing or scoring was rerun by the transfer. Original project files remain unchanged.

Raw/intermediate data and artifacts are ignored by Git but physically present locally. This copy does not place them on GitHub. Preserve provider licences, especially the terrain archive's packaged terms, when arranging shared storage. Do not commit personal API credentials.

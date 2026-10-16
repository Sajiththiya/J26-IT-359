# HRI at t+1: work before SHAP

This folder now contains Jupyter notebooks with visible preparation, training,
cross-validation, scoring and export code. The six former Python scripts have
been converted to notebook cells. Run the notebooks in order:

| Notebook | Purpose |
| --- | --- |
| `00_hri_t_plus_1_data_preparation.ipynb` | HRI weights, next-year joins, forest inputs, blocks, audits and dataset backups |
| `01_ridge_training.ipynb` | Ridge model, parameters, preprocessing, CV search and validation |
| `02_random_forest_training.ipynb` | Random Forest model, parameters, CV search and validation |
| `03_xgboost_training.ipynb` | XGBoost model, parameters, CV search and validation |
| `04_model_comparison_and_final_test.ipynb` | Baselines, selection, learning history, one-time testing and final report |

Each model notebook includes the estimator and complete search/evaluation code
in its cells. There are no local Python helper files. This workflow ends before
SHAP and recommendation generation.

The v2 run is completed and frozen. Read the [executed results](../../../artifacts/hri/hri_t_plus_1_v2/RESULTS.md).
Ridge was selected by joint-validation MAE (0.05747). Its joint-test MAE is
0.05982 on 800 rows, with a 95% block-bootstrap interval of 0.05032–0.06985.
On those exact rows, persistence MAE is 1.05173 and transition-baseline MAE
is 0.08305. These very small errors concern a partly predictable constructed
index, not independently observed ecological risk.

## HRI weights and meaning

The existing released primary index is retained:

`HRI = 100 * (0.25*forest_amount_risk + 0.25*recent_loss_risk + 0.25*cumulative_loss_risk + 0.25*fragmentation_risk)`

Weights are recorded in `configs/hri.json`, and the HRI calculation reads that configuration. They sum to one and are checked against every released score before training. Equal contribution is a transparent analytical starting point because numerical expert weights have not been obtained. These weights are **not expert validated**. Choosing different weights merely to increase R² would change the research target. The existing condition-emphasis and disturbance-emphasis alternatives are retained in a training-only sensitivity report rather than selected using prediction error. The 30% canopy threshold, 10% baseline forest applicability and 5 km assessment unit remain provisional ecological choices.

The continuous forest-oriented index is primary. Communication classes use the exact released bounds `100/3` and `200/3`, not the proposal's illustrative 30/60 thresholds. Scores are relative environmental evidence, not observed bird mortality or independently validated ecological outcomes.

## Inputs and next-year columns

`forecast_dataset.csv` combines the physical-unit `pre_hri_v1` master and released `hri_v1` scores using exact `cell_id + year` joins. Only measurements available by the end of feature year t enter the allowlist `FEATURES`. They include current HRI, its four components, forest amount/loss/fragmentation, past HRI and forest changes, climate and terrain. Unavailable predictor values remain missing until a CV-fold-fitted imputer handles them. Population is excluded because its coverage ends in 2020. Observation-point NDVI and bird record counts are excluded because they are not a consistent national annual pressure series.

The existing final model CSV and its frozen train/validation/test files receive five appended columns: `target_year_t1`, `target_hri_score_t1`, `target_risk_class_t1`, `target_hri_change_t1`, and `target_hri_t1_available`. Existing predictors, rows, current HRI and old split labels are preserved. Missing future outcomes (including 2024 for a 2023 row) remain missing; they are never imputed. Targets must never enter X. Backups are under `data/processed/hri/hri_t_plus_1_v2/original_dataset_backups/`. The existing dataset builder also adds these columns when rebuilding, so notebook 07 preserves them automatically.

## Baselines and model targets

1. Mean: training mean HRI.
2. Persistence: predict HRI(t+1) = HRI(t).
3. Known-component transition: update the recent-loss and cumulative-loss components using observed losses through t, and carry forward current forest amount and fragmentation. The target index at t+1 deliberately uses prior losses only through t, so those two future index components are already calculable at forecast time. The implementation audits this identity against the released components.

The Ridge, Random Forest and XGBoost searches compare direct score prediction, residuals relative to persistence (equivalent to predicting HRI change), and residuals relative to the transition baseline. Validation can select a simple baseline when it outperforms the learned models. A high score alone does not demonstrate useful new ecological forecasting: much of next year's constructed HRI is persistent or already determined by known inputs. Always report gains over both persistence and the transition baseline.

The selected Ridge estimator uses transition-baseline residuals. Its full
prediction is the known baseline plus the learned correction. Subsequent
explanation work must account for both terms; explaining only the fitted
correction does not explain the full score. The legacy XGBoost SHAP script
does not load or interpret this composite estimator correctly without adaptation.

Run the imports and estimator-definition cells before loading saved forecasts.
The notebooks register their visible `HriForecaster` class as
`training.HriForecaster` in memory, which keeps the existing joblib artifacts
loadable after removal of the Python files. Supply the columns in `FEATURES`
in their original physical units; the saved estimator includes its fitted
imputer and scaler.

## Validation protocol

- Label calibration: fixed national 2010–2014 core scales, separate from learned predictor preprocessing. Only targets from 2015 onward enter the modelling experiment.
- Training: target years 2015–2019, training geographic blocks.
- Temporal validation: target years 2020–2021 on training blocks.
- Spatial validation: target years 2015–2019 on validation blocks.
- Joint validation: target years 2020–2021 on validation blocks. Lowest MAE here selects among the tuned models and baselines.
- Final tests: the corresponding temporal, spatial, and joint held-out views; future-year tests use target years 2022–2023 and geographic tests use a separate test-block cohort. Only the selected model and prespecified baselines are tested.

Blocks are 25 km squares formed from the existing 5 km grid coordinates, assigned once using seed 42 to 70/15/15% train/validation/test cohorts. Block counts, not exact row percentages, determine the split. There are no buffers; correlation across adjacent boundaries may remain. Internal tuning uses three forward folds: assessments in 2017, 2018 and 2019, each excluding its held-out block cohort from all fitting years. Imputation and scaling are fitted within each fold. Each model has 16 reproducible random candidates. The holdout model remains fitted to the original training cohort for consistency with validation; it is not silently refitted on validation data.

Historical products may have been revised after their nominal year. This is retrospective evaluation, not an operational as-published reconstruction. The source dataset has also been explored in earlier experiments; a newly frozen split does not erase prior research exposure. HRI expert validation and genuinely external prospective data remain separate research requirements.

## Running

Choose the project Python environment as the Jupyter kernel. Open notebook 00
and then the three model notebooks, followed by notebook 04. Use **Run All**
within each notebook. The defaults load the existing data/models and display
saved metrics, parameters and plots; they do not retrain or rerun final testing.

For new development, set a new `EXPERIMENT_NAME` consistently in all model and
comparison notebooks, then enable `RUN_TRAINING`. Reusing the frozen v2 data
for a new model experiment does not require preparation again. If changing
the dataset itself, choose a new `DATA_VERSION` as well and enable
`RUN_PREPARATION` in notebook 00. After all three models have run, enable
`RUN_SELECTION` in notebook 04. Enable `RUN_FINAL_TEST` once only after selection.

The completed v2 artifact directory stays locked. Further development must
disclose that the historical test has already been viewed; changing an
experiment name does not create genuinely new unseen data.

The removed scripts are recoverable from
`data/processed/hri/hri_t_plus_1_v2/original_code_backup.zip`.
`notebook_migration.json` records original source hashes and the new notebook
files. The original fitted models, scores and final-test manifest are retained.

## Outputs

Data and backups: `data/processed/hri/hri_t_plus_1_v2/`.

Models and reports: `artifacts/hri/hri_t_plus_1_v2/` with:

- Dataset, source and split audits; predictor missingness and weight sensitivity.
- Each model's saved forecast estimator, best parameters, full CV results and fold audit.
- Separate temporal, spatial and joint validation metrics, predictions, risk-band errors, classification reports and confusion matrices.
- Mean, persistence and transition baseline results on the same rows.
- Model comparison, selected estimator, validation diagnostics and historical learning results.
- Final-test predictions and metrics, block-bootstrap 95% MAE intervals and an immutable-test marker after testing.

The older `scripts/train_temporal_models.py` is a legacy fixed-parameter spatial experiment. Its threshold function has been corrected, but its existing saved artifacts and older SHAP/recommendation files are not outputs of this new protocol. Use the v2 artifacts for subsequent explanation work.

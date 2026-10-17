# Optimized HRI model training

These ten self-contained notebooks follow the step-by-step structure of `../Model_Training/`. Each notebook contains its own data loading, preprocessing pipeline, grouped cross-validation, hyperparameter search, validation plots, result exports, and locked final-test cell. Run from any working directory within the repository with the project Python environment selected as the Jupyter kernel. The separate `optimized_training.py` module provides an optional command-line way to run the same experiments.

## Method

- Target: `hri_score_0_100`; predictors: the nine climate and terrain fields used by the original notebooks. The frozen inputs are already normalized. Imputation, and scaling where needed, occur within each training fold.
- `GroupKFold` keeps every year of a `cell_id` in the same training or assessment fold. Search chooses the lowest mean cross-validation MAE; RMSE, R², fold standard deviation, and cross-validation training error are also saved. Regularization and model capacity parameters are searched to address overfitting and underfitting.
- After tuning, the selected parameters are refitted on all `train.csv` rows and scored on the frozen `validation.csv`. A mean-prediction baseline and train/validation error gap are reported. The test set is untouched during training and validation.
- The GAM notebook uses an additive cubic spline basis with Ridge regularization, matching the implementation style in the original GAM notebook. The linear notebook tunes Ridge; very small `alpha` approximates unregularized linear regression.
- These scores measure approximation of a same-year constructed HRI index. They do not demonstrate prediction of future habitat degradation. Grouping by cell prevents repeated-cell leakage but does not by itself guarantee independent neighboring locations or years.

## Run

Install the project dependencies plus `scikit-learn`, `joblib`, `xgboost`, `lightgbm`, and `catboost` if they are absent from your Python environment. You can execute one notebook at a time or run all ten from a shell:

```bash
python3 components/habitat_risk/notebooks/hri/Model_training_optimized/optimized_training.py --model all
```

Defaults are 3 grouped folds and 8 random candidates per model. Training all ten can take a long time, especially SVR and MLP. For a quick smoke run, use `--model linear_regression --n-iter 2 --folds 2`. A quick run is not a final comparison; use identical settings for the ten final experiments. Results are written to `components/habitat_risk/artifacts/hri/model_training_optimized/`, including `model_comparison.csv`, per-model CV results, validation predictions, risk-class errors, and saved pipelines.

After inspecting the comparison and selecting one model, evaluate the holdout test **once**:

```bash
python3 components/habitat_risk/notebooks/hri/Model_training_optimized/optimized_training.py --final-test MODEL_NAME
```

Replace `MODEL_NAME` with one of the ten names in `model_comparison.csv`. Do not use the test score to revise the model choice.

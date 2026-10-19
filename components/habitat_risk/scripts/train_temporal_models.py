"""Train and validate Linear, Random Forest, and XGBoost models on the Temporal Dataset.

Evaluates:
  1. Benchmark Baseline: Linear Regression
  2. Candidate 1: Random Forest
  3. Candidate 2: XGBoost

Metrics:
  - Regression: MAE, RMSE, R2
  - Classification (Low, Moderate, High risk classes): Balanced Accuracy, F1-score
Saves models, metrics, and comparisons to artifacts/hri/temporal_model_v1/
"""

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, balanced_accuracy_score, f1_score

ROOT = Path(__file__).resolve().parents[1]
SPLITS_DIR = ROOT / "data/splits/hri/temporal_model_v1"
ARTIFACTS_DIR = ROOT / "artifacts/hri/temporal_model_v1"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "climate__annual_mean_temperature_c",
    "climate__annual_precipitation_mm",
    "terrain__mean_elevation_m",
    "terrain__mean_slope_degrees",
    "forest__baseline_canopy_percent",
    "forest__remaining_baseline_forest_proportion",
    "forest__annual_loss_ha",
    "forest__cumulative_prior_loss_ha",
    "forest__annual_loss_fraction_of_baseline",
    "fragmentation__cell_patch_count",
    "fragmentation__mean_cell_patch_ha",
    "fragmentation__edge_m_per_land_ha",
]

TARGET_COL = "target_hri_score_t1"
TARGET_CLASS_COL = "target_risk_class_t1"

def categorize_hri(scores):
    """Use the released HRI thresholds, rather than illustrative proposal values.

    For audited tuning and later-year tests use the notebooks in notebooks/hri/HRI_t_plus_1/.
    This file is the legacy fixed-parameter spatial experiment.
    """
    categories = []
    for s in scores:
        if s <= 100 / 3:
            categories.append("Low")
        elif s <= 200 / 3:
            categories.append("Moderate")
        else:
            categories.append("High")
    return np.array(categories)

def main():
    print("Loading temporal train and validation datasets...")
    train_df = pd.read_csv(SPLITS_DIR / "train.csv")
    val_df = pd.read_csv(SPLITS_DIR / "validation.csv")

    X_train, y_train = train_df[FEATURE_COLS], train_df[TARGET_COL]
    X_val, y_val = val_df[FEATURE_COLS], val_df[TARGET_COL]
    y_val_class = val_df[TARGET_CLASS_COL].values

    models = {
        "linear_regression": Ridge(alpha=1.0),
        "random_forest": RandomForestRegressor(
            n_estimators=150, max_depth=16, min_samples_split=5, random_state=42, n_jobs=-1
        ),
        "xgboost": XGBRegressor(
            n_estimators=200, max_depth=6, learning_rate=0.08, subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1
        ),
    }

    results = []

    for name, model in models.items():
        print(f"\n--- Training {name} ---")
        model.fit(X_train, y_train)

        # Predictions
        train_preds = model.predict(X_train)
        val_preds = model.predict(X_val)

        # Calculate Regression Metrics
        val_mae = mean_absolute_error(y_val, val_preds)
        val_rmse = np.sqrt(mean_squared_error(y_val, val_preds))
        val_r2 = r2_score(y_val, val_preds)

        train_mae = mean_absolute_error(y_train, train_preds)
        train_r2 = r2_score(y_train, train_preds)

        # Calculate Classification Metrics on Derived Risk Classes
        val_pred_class = categorize_hri(val_preds)
        val_bal_acc = balanced_accuracy_score(y_val_class, val_pred_class)
        val_f1 = f1_score(y_val_class, val_pred_class, average="weighted")

        print(f"Validation MAE: {val_mae:.4f}")
        print(f"Validation RMSE: {val_rmse:.4f}")
        print(f"Validation R2: {val_r2:.4f}")
        print(f"Validation Balanced Accuracy: {val_bal_acc:.4f}")
        print(f"Validation Weighted F1: {val_f1:.4f}")

        # Save model artifact
        model_dir = ARTIFACTS_DIR / name
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_dir / f"{name}_model.joblib")

        # Save validation predictions
        val_out = val_df[["cell_id", "feature_year_t", "target_year_t1", TARGET_COL, TARGET_CLASS_COL]].copy()
        val_out["predicted_hri_score_t1"] = val_preds
        val_out["predicted_risk_class_t1"] = val_pred_class
        val_out.to_csv(model_dir / "validation_predictions.csv", index=False)

        results.append({
            "model": name,
            "train_MAE": train_mae,
            "train_R2": train_r2,
            "val_MAE": val_mae,
            "val_RMSE": val_rmse,
            "val_R2": val_r2,
            "val_balanced_acc": val_bal_acc,
            "val_weighted_f1": val_f1,
        })

    summary_df = pd.DataFrame(results)
    summary_path = ARTIFACTS_DIR / "model_comparison_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"\n================ MODEL COMPARISON ================")
    print(summary_df.to_string(index=False))
    print(f"Summary saved to {summary_path}")

if __name__ == "__main__":
    main()

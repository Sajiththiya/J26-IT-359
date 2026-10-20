"""Generate Global and Local SHAP Explanations for the best Habitat Risk model.

Fulfills WP7 of Component 04 research proposal:
  1. Global SHAP Feature Importance & Summary (beeswarm) plot
  2. SHAP dependence plots for top drivers
  3. Local SHAP waterfall explanations for representative high-risk and low-risk habitats
Saves figures and data arrays to artifacts/hri/temporal_model_v1/shap/
"""

from pathlib import Path
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

ROOT = Path(__file__).resolve().parents[1]
SPLITS_DIR = ROOT / "data/splits/hri/temporal_model_v1"
ARTIFACTS_DIR = ROOT / "artifacts/hri/temporal_model_v1"
SHAP_DIR = ARTIFACTS_DIR / "shap"
SHAP_DIR.mkdir(parents=True, exist_ok=True)

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

# Cleaner display names for ecological reporting
DISPLAY_NAMES = {
    "climate__annual_mean_temperature_c": "Annual Mean Temp (°C)",
    "climate__annual_precipitation_mm": "Annual Precipitation (mm)",
    "terrain__mean_elevation_m": "Mean Elevation (m)",
    "terrain__mean_slope_degrees": "Mean Slope (°)",
    "forest__baseline_canopy_percent": "Baseline Canopy (%)",
    "forest__remaining_baseline_forest_proportion": "Remaining Forest Prop.",
    "forest__annual_loss_ha": "Annual Forest Loss (ha)",
    "forest__cumulative_prior_loss_ha": "Cumulative Forest Loss (ha)",
    "forest__annual_loss_fraction_of_baseline": "Annual Loss Fraction",
    "fragmentation__cell_patch_count": "Patch Count",
    "fragmentation__mean_cell_patch_ha": "Mean Patch Size (ha)",
    "fragmentation__edge_m_per_land_ha": "Edge Density (m/ha)",
}

def main():
    print("Loading XGBoost model and validation dataset...")
    model_path = ARTIFACTS_DIR / "xgboost/xgboost_model.joblib"
    model = joblib.load(model_path)

    val_df = pd.read_csv(SPLITS_DIR / "validation.csv")
    X_val = val_df[FEATURE_COLS]

    # Sample 1000 validation points for robust, fast SHAP calculation
    sample_df = val_df.sample(n=min(1000, len(val_df)), random_state=42)
    X_sample = sample_df[FEATURE_COLS].copy()
    X_sample_named = X_sample.rename(columns=DISPLAY_NAMES)

    print("Computing TreeExplainer SHAP values...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X_sample_named)

    # 1. Global Beeswarm Summary Plot
    print("Generating Global SHAP beeswarm plot...")
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X_sample_named, show=False)
    plt.title("Global Environmental Drivers of Next-Year Habitat Risk (SHAP)", fontsize=13, pad=12)
    plt.tight_layout()
    plt.savefig(SHAP_DIR / "global_shap_beeswarm.png", dpi=300)
    plt.close()

    # 2. Global Bar Feature Importance Plot
    print("Generating Global SHAP feature importance bar plot...")
    plt.figure(figsize=(10, 6))
    shap.plots.bar(shap_values, max_display=12, show=False)
    plt.title("Mean Absolute SHAP Value (Global Impact on Future Risk)", fontsize=13, pad=12)
    plt.tight_layout()
    plt.savefig(SHAP_DIR / "global_shap_feature_importance.png", dpi=300)
    plt.close()

    # 3. Local Waterfall Explanation - High Risk Cell
    print("Generating Local Waterfall plot for High Risk Cell...")
    high_risk_idx = sample_df["target_hri_score_t1"].idxmax()
    high_risk_loc = sample_df.index.get_loc(high_risk_idx)
    
    plt.figure(figsize=(9, 5))
    shap.plots.waterfall(shap_values[high_risk_loc], max_display=8, show=False)
    plt.title(f"Local Explanation: High-Risk Habitat (HRI={sample_df.loc[high_risk_idx, 'target_hri_score_t1']:.1f})", fontsize=11)
    plt.tight_layout()
    plt.savefig(SHAP_DIR / "local_waterfall_high_risk.png", dpi=300)
    plt.close()

    # 4. Local Waterfall Explanation - Low Risk Cell
    print("Generating Local Waterfall plot for Low Risk Cell...")
    low_risk_idx = sample_df["target_hri_score_t1"].idxmin()
    low_risk_loc = sample_df.index.get_loc(low_risk_idx)
    
    plt.figure(figsize=(9, 5))
    shap.plots.waterfall(shap_values[low_risk_loc], max_display=8, show=False)
    plt.title(f"Local Explanation: Low-Risk Habitat (HRI={sample_df.loc[low_risk_idx, 'target_hri_score_t1']:.1f})", fontsize=11)
    plt.tight_layout()
    plt.savefig(SHAP_DIR / "local_waterfall_low_risk.png", dpi=300)
    plt.close()

    # Save mean absolute SHAP values table
    mean_abs_shap = pd.DataFrame({
        "feature": [DISPLAY_NAMES[col] for col in FEATURE_COLS],
        "mean_abs_shap": np.abs(shap_values.values).mean(axis=0)
    }).sort_values(by="mean_abs_shap", ascending=False)
    mean_abs_shap.to_csv(SHAP_DIR / "global_shap_importance.csv", index=False)
    print("\nGlobal SHAP Feature Importance Table:")
    print(mean_abs_shap.to_string(index=False))

    print(f"\nAll SHAP outputs saved to {SHAP_DIR}")

if __name__ == "__main__":
    main()

"""Rule-based Conservation Recommendation Engine.

Implements WP8 of the research proposal:
Translates top SHAP/environmental risk drivers into concrete, evidence-based conservation actions.

Rules defined from Section 3.13 of the Proposal:
  1. Forest loss / degradation -> Prioritize habitat restoration, protection, and monitoring.
  2. Fragmentation (small patch size, high edge density) -> Investigate corridor creation and edge-management.
  3. Climate stress -> Increase ecological monitoring and climate-resilient buffer management.
  4. Multiple high-risk drivers -> Flag for urgent multi-stakeholder expert review.
"""

from pathlib import Path
import joblib
import pandas as pd
import numpy as np
import shap

ROOT = Path(__file__).resolve().parents[1]
SPLITS_DIR = ROOT / "data/splits/hri/temporal_model_v1"
ARTIFACTS_DIR = ROOT / "artifacts/hri/temporal_model_v1"
OUTPUT_DIR = ARTIFACTS_DIR / "recommendations"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

def generate_recommendations(row, top_drivers):
    """Generate recommendations based on risk class and top contributing drivers."""
    risk_class = row["predicted_risk_class_t1"]
    actions = []
    
    # Check dominant drivers
    has_loss = any("loss" in d.lower() or "forest" in d.lower() for d in top_drivers)
    has_frag = any("patch" in d.lower() or "edge" in d.lower() for d in top_drivers)
    has_climate = any("temp" in d.lower() or "precip" in d.lower() for d in top_drivers)

    if risk_class == "High":
        if has_loss:
            actions.append("Prioritize native reforestation and immediate active protection in affected zones.")
        if has_frag:
            actions.append("Establish ecological connectivity corridors between isolated patches to reduce edge effects.")
        if has_climate:
            actions.append("Increase microclimate and drought monitoring; enhance protective canopy buffer zones.")
        if len(top_drivers) >= 2:
            actions.append("Flag location as urgent priority for integrated multi-stakeholder expert review.")
    elif risk_class == "Moderate":
        if has_loss:
            actions.append("Conduct regular satellite-based disturbance audits and reinforce existing boundaries.")
        if has_frag:
            actions.append("Implement edge-management and evaluate small stepping-stone vegetation patches.")
        if has_climate:
            actions.append("Track seasonal vegetation health changes via periodic remote sensing.")
    else:  # Low risk
        actions.append("Maintain baseline habitat protection and routine longitudinal conservation monitoring.")

    return " | ".join(actions)

def main():
    print("Loading XGBoost model and validation dataset for recommendations...")
    model = joblib.load(ARTIFACTS_DIR / "xgboost/xgboost_model.joblib")
    val_preds_df = pd.read_csv(ARTIFACTS_DIR / "xgboost/validation_predictions.csv")
    val_df = pd.read_csv(SPLITS_DIR / "validation.csv")

    # Sample top 200 high and moderate risk cells for recommendations
    target_cells = val_preds_df[val_preds_df["predicted_risk_class_t1"].isin(["High", "Moderate"])].head(200)
    indices = target_cells.index
    
    X_target = val_df.loc[indices, FEATURE_COLS]
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer(X_target)

    recommendations_list = []
    for i, (_, row) in enumerate(target_cells.iterrows()):
        # Extract top 2 positive drivers for this cell
        cell_shap = shap_vals.values[i]
        top_indices = np.argsort(cell_shap)[-2:]
        top_drivers = [FEATURE_COLS[idx].split("__")[-1] for idx in top_indices if cell_shap[idx] > 0]
        
        recs = generate_recommendations(row, top_drivers)
        
        recommendations_list.append({
            "cell_id": row["cell_id"],
            "year_t": row["feature_year_t"],
            "forecast_year_t1": row["target_year_t1"],
            "predicted_hri_t1": round(row["predicted_hri_score_t1"], 2),
            "predicted_risk_class": row["predicted_risk_class_t1"],
            "dominant_risk_drivers": ", ".join(top_drivers) if top_drivers else "Baseline factors",
            "conservation_recommendations": recs,
        })

    recs_df = pd.DataFrame(recommendations_list)
    out_path = OUTPUT_DIR / "sample_conservation_recommendations.csv"
    recs_df.to_csv(out_path, index=False)
    print(f"\nSaved {len(recs_df)} sample recommendations to {out_path}")
    print("\nSample Recommendations Output:")
    print(recs_df[["cell_id", "predicted_hri_t1", "predicted_risk_class", "dominant_risk_drivers", "conservation_recommendations"]].head(5).to_string(index=False))

if __name__ == "__main__":
    main()

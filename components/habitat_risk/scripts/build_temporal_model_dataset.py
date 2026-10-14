"""Build Temporal Forecasting Model Dataset (Year t -> Year t+1).

Legacy v1 builder retained for its existing artifacts. For raw missingness,
current-HRI/transition baselines, and later-year + block validation, use
notebooks/hri/HRI_t_plus_1/00_hri_t_plus_1_data_preparation.ipynb. Do not use this builder to recreate
the audited v2 experiment.

This script implements Section 3.7 of the Component 04 research proposal:
Predicting future habitat risk (Year t+1) using preceding environmental conditions (Year t).

Features in Year t:
  - Climate (Temperature, Precipitation)
  - Terrain (Elevation, Slope)
  - Forest Condition (Baseline Canopy %, Remaining Proportion)
  - Forest Disturbance (Annual Loss ha, Cumulative Prior Loss ha, Loss Fraction)
  - Habitat Fragmentation (Patch Count, Mean Patch ha, Edge Density m/ha)

Target in Year t+1:
  - HRI Score (0-100)
  - Fixed Risk Class (Low, Moderate, High)
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Paths
ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data/processed/hri/pre_hri_v1/master_cell_year_dataset.csv"
HRI_PATH = ROOT / "data/processed/hri/hri_v1/hri_core_equal_complete_cases.csv"
SPLITS_REF = ROOT / "data/splits/hri/model_v1/train.csv"
OUTPUT_DIR = ROOT / "data/processed/hri/temporal_model_v1"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SPLITS_DIR = ROOT / "data/splits/hri/temporal_model_v1"
SPLITS_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    # Climate (stress & context)
    "climate__annual_mean_temperature_c",
    "climate__annual_precipitation_mm",
    # Terrain (topography)
    "terrain__mean_elevation_m",
    "terrain__mean_slope_degrees",
    # Forest structure & degradation
    "forest__baseline_canopy_percent",
    "forest__remaining_baseline_forest_proportion",
    "forest__annual_loss_ha",
    "forest__cumulative_prior_loss_ha",
    "forest__annual_loss_fraction_of_baseline",
    # Fragmentation (breakup & edge exposure)
    "fragmentation__cell_patch_count",
    "fragmentation__mean_cell_patch_ha",
    "fragmentation__edge_m_per_land_ha",
]

def main():
    print("Loading pre_hri_v1 master dataset...")
    master = pd.read_csv(MASTER_PATH, low_memory=False)
    print("Loading HRI complete cases...")
    hri = pd.read_csv(HRI_PATH)

    # Load existing cell split assignments to maintain exact spatial separation
    train_ref = pd.read_csv(SPLITS_REF)
    val_ref = pd.read_csv(ROOT / "data/splits/hri/model_v1/validation.csv")
    test_ref = pd.read_csv(ROOT / "data/splits/hri/model_v1/test.csv")

    cell_split_map = {}
    for c in train_ref["cell_id"].unique():
        cell_split_map[c] = "train"
    for c in val_ref["cell_id"].unique():
        cell_split_map[c] = "validation"
    for c in test_ref["cell_id"].unique():
        cell_split_map[c] = "test"

    # Only include cells that have validated HRI records
    eligible_cells = set(hri["cell_id"].unique())
    master_sub = master[master["cell_id"].isin(eligible_cells)].copy()

    # Features at Year t (2010 to 2022)
    df_xt = master_sub[master_sub["reference_year"] <= 2022][
        ["cell_id", "reference_year"] + FEATURE_COLS
    ].copy()

    # Targets at Year t+1 (2011 to 2023)
    df_yt1 = hri[hri["reference_year"] >= 2011][
        ["cell_id", "reference_year", "hri_score_0_100", "fixed_risk_class", "quantile_risk_class"]
    ].copy()
    
    # Create matching key: X year t connects to Y year t+1
    df_yt1["reference_year_t"] = df_yt1["reference_year"] - 1

    temporal_df = pd.merge(
        df_xt,
        df_yt1,
        left_on=["cell_id", "reference_year"],
        right_on=["cell_id", "reference_year_t"],
        suffixes=("", "_target_year"),
    )

    temporal_df.rename(
        columns={
            "reference_year": "feature_year_t",
            "reference_year_target_year": "target_year_t1",
            "hri_score_0_100": "target_hri_score_t1",
            "fixed_risk_class": "target_risk_class_t1",
        },
        inplace=True,
    )
    temporal_df.drop(columns=["reference_year_t"], inplace=True)

    # Assign dataset split
    temporal_df["dataset_split"] = temporal_df["cell_id"].map(cell_split_map)

    # Median imputation using ONLY training partition to prevent leakage
    train_mask = temporal_df["dataset_split"] == "train"
    for col in FEATURE_COLS:
        median_val = temporal_df.loc[train_mask, col].median()
        temporal_df[col] = temporal_df[col].fillna(median_val)

    # Save full master temporal dataset
    master_out_path = OUTPUT_DIR / "final_temporal_model_dataset.csv"
    temporal_df.to_csv(master_out_path, index=False)
    print(f"Saved temporal dataset to {master_out_path} (Shape: {temporal_df.shape})")

    # Save train, validation, test splits
    for split_name in ["train", "validation", "test"]:
        split_data = temporal_df[temporal_df["dataset_split"] == split_name].copy()
        split_path = SPLITS_DIR / f"{split_name}.csv"
        split_data.to_csv(split_path, index=False)
        print(f"  - Saved {split_name}.csv: {split_data.shape[0]} rows")

    print("\nDataset preparation complete successfully!")

if __name__ == "__main__":
    main()

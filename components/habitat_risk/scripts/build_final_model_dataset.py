"""Create one leakage-controlled HRI modelling table with random cell splits.

The output contains the released core HRI targets joined to the older WP6
climate/terrain feature table. Missing predictor values are filled using
training-partition medians only, with a companion missing-value indicator for
each predictor. Entire cells are assigned to one partition so repeated annual
records from a location cannot leak across train, validation, and test. HRI
component risks are intentionally excluded because the targets are calculated
directly from those components.
"""

import json
import random
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WP6_PATH = ROOT / "data/processed/hri/wp6_v1/master_cell_year_dataset.csv"
HRI_PATH = ROOT / "data/processed/hri/hri_v1/hri_core_equal_complete_cases.csv"
OUTPUT = ROOT / "data/processed/hri/model_v1/final_hri_model_dataset.csv"
OBSERVATION_PATH = ROOT / "data/processed/requested_observation_dataset.csv"

KEY = ["cell_id", "reference_year"]
TARGETS = ["hri_score_0_100", "fixed_risk_class", "quantile_risk_class"]
PREDICTORS = [
    "climate__annual_mean_temperature_c",
    "climate__annual_precipitation_mm",
    "climate__temperature_c_anomaly",
    "climate__temperature_c_trailing5_slope_per_year",
    "climate__precipitation_mm_anomaly",
    "climate__precipitation_mm_trailing5_slope_per_year",
    "terrain__mean_elevation_m",
    "terrain__elevation_sd_m",
    "terrain__mean_slope_degrees",
]
RANDOM_SEED = 42
TRAIN_FRACTION = 0.70
VALIDATION_FRACTION = 0.15


def random_cell_splits(cell_ids: pd.Series) -> dict[str, str]:
    """Assign each spatial cell to exactly one reproducible random split."""
    cells = sorted(cell_ids.unique())
    random.Random(RANDOM_SEED).shuffle(cells)
    train_end = round(len(cells) * TRAIN_FRACTION)
    validation_end = train_end + round(len(cells) * VALIDATION_FRACTION)
    return {
        cell_id: (
            "train"
            if index < train_end
            else "validation"
            if index < validation_end
            else "test"
        )
        for index, cell_id in enumerate(cells)
    }


def main() -> None:
    wp6 = pd.read_csv(WP6_PATH, usecols=KEY + PREDICTORS)
    hri = pd.read_csv(HRI_PATH, usecols=KEY + TARGETS)

    if wp6.duplicated(KEY).any() or hri.duplicated(KEY).any():
        raise ValueError("Input tables must have unique cell_id + reference_year keys")

    data = hri.merge(wp6, on=KEY, how="left", validate="one_to_one", indicator=True)
    if not data["_merge"].eq("both").all():
        raise ValueError("Some released HRI rows have no matching WP6 feature row")
    data = data.drop(columns="_merge")
    split_map = random_cell_splits(data["cell_id"])
    data.insert(2, "dataset_split", data["cell_id"].map(split_map))

    # Fit all preprocessing statistics only on the training period.
    training = data["dataset_split"].eq("train")
    for column in PREDICTORS:
        missing_column = f"{column}__was_missing"
        data[missing_column] = data[column].isna().astype("int8")
        median = data.loc[training, column].median()
        if pd.isna(median):
            raise ValueError(f"No training values available to impute {column}")
        data[column] = data[column].fillna(median)

    ordered = KEY + ["dataset_split"] + PREDICTORS
    ordered += [f"{column}__was_missing" for column in PREDICTORS]
    ordered += TARGETS
    data = data[ordered].sort_values(["reference_year", "cell_id"]).reset_index(drop=True)

    # Observation context is sampled at visited locations, not a national raster
    # estimate. Keep it distinct from the explicit model predictor list.
    observations = pd.read_csv(OBSERVATION_PATH, low_memory=False)
    dates = pd.to_datetime(observations["observation_date"], errors="coerce")
    observations["reference_year"] = pd.to_numeric(observations["year"], errors="coerce")
    valid = (observations["cell_id"].notna() & dates.notna()
             & observations["reference_year"].eq(dates.dt.year)
             & observations["reference_year"].isin(data["reference_year"].unique()))
    observations = observations.loc[valid].copy()
    # Repeated species sightings on the same checklist must not give its
    # environmental measurements extra weight.
    for field in ["ndvi", "elevation_m", "duration_minutes", "effort_distance_km"]:
        observations[field] = pd.to_numeric(observations[field], errors="coerce")
    observations["ndvi"] = observations["ndvi"].where(observations["ndvi"].between(-1, 1))
    for field in ["duration_minutes", "effort_distance_km"]:
        observations[field] = observations[field].where(observations[field].ge(0))
    observations["land_cover"] = observations["land_cover"].astype("string")
    events = observations.drop_duplicates(KEY + ["checklist_id", "latitude", "longitude", "observation_date"])
    context = events.groupby(KEY).agg(**{
        "context__observed_checklist_locations": ("checklist_id", "size"),
        "context__sampled_ndvi_mean": ("ndvi", "mean"),
        "context__ndvi_valid_event_count": ("ndvi", "count"),
        "context__sampled_elevation_mean_m": ("elevation_m", "mean"),
        "context__survey_duration_mean_minutes": ("duration_minutes", "mean"),
        "context__survey_distance_mean_km": ("effort_distance_km", "mean"),
        "context__sampled_land_cover_mode": ("land_cover", lambda s: s.mode().iloc[0] if not s.mode().empty else pd.NA),
    }).reset_index()
    data = data.merge(context, on=KEY, how="left", validate="one_to_one")
    data["context__bird_evidence_available"] = data["context__observed_checklist_locations"].notna().astype("int8")
    data["context__sampled_ndvi_missing"] = data["context__sampled_ndvi_mean"].isna().astype("int8")
    if OUTPUT.exists():
        frozen = pd.read_csv(OUTPUT, usecols=KEY + ["dataset_split"])
        comparison = data[KEY + ["dataset_split"]].merge(
            frozen, on=KEY, how="outer", validate="one_to_one", indicator=True,
            suffixes=("", "_frozen"))
        if (not comparison["_merge"].eq("both").all()
                or not comparison["dataset_split"].eq(comparison["dataset_split_frozen"]).all()):
            raise ValueError("Refusing to change the frozen cell-year rows or split membership")
    print("Observation context matched:", int(data["context__bird_evidence_available"].sum()))
    print("Rows with sampled NDVI:", int(data["context__sampled_ndvi_mean"].notna().sum()))

    if data[ordered].isna().any().any():
        raise ValueError("Model predictors/targets unexpectedly contain missing values")
    if data.duplicated(KEY).any():
        raise ValueError("Final modelling table has duplicate keys")
    if data.groupby("cell_id")["dataset_split"].nunique().max() != 1:
        raise ValueError("A cell_id occurs in more than one dataset split")
    expected_years = set(data["reference_year"].unique())
    years_by_split = data.groupby("dataset_split")["reference_year"].agg(set)
    if not years_by_split.map(lambda years: years == expected_years).all():
        raise ValueError("Every split must contain all reference years")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # Append exact next-calendar-year labels; final-year/unavailable labels remain missing.
    # These columns are outcomes and must never enter a predictor feature list.
    notebook_path = ROOT / "notebooks/hri/HRI_t_plus_1/00_hri_t_plus_1_data_preparation.ipynb"
    notebook = json.loads(notebook_path.read_text())
    namespace = {"ROOT": ROOT, "__name__": "hri_dataset_annotation"}
    # Load definitions only; execution and review cells are deliberately excluded.
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code" and "runtime_data" in cell.get("metadata", {}).get("tags", []):
            exec(compile("".join(cell["source"]), str(notebook_path), "exec"), namespace)
    data = namespace["add_next_year_targets"](data, hri)
    data.to_csv(OUTPUT, index=False)

    print(f"Wrote {len(data):,} rows and {len(data.columns)} columns to {OUTPUT}")
    print(data.groupby("dataset_split", sort=False).size().to_string())
    print(f"Random cell split seed: {RANDOM_SEED}; ratios: 70%/15%/15%")
    print("Every split contains 2010-2023; no cell_id occurs in multiple splits")


if __name__ == "__main__":
    main()

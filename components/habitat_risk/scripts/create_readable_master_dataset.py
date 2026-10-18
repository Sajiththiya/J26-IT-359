"""Create a human-readable copy of the pre-HRI master without changing it.

The canonical double-underscore names are retained in the original dataset
because notebooks and provenance tables depend on them. This script changes
headers only; row order and values are preserved exactly.
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/processed/hri/pre_hri_v1"
SOURCE = RELEASE / "master_cell_year_dataset.csv"
OUTPUT = RELEASE / "master_cell_year_dataset_readable.csv"
GUIDE = RELEASE / "master_readable_column_guide.csv"

ALIASES = {
    "cell_id": "grid_cell_id",
    "reference_year": "year",
    "climate__annual_mean_temperature_c": "annual_mean_temperature_celsius",
    "climate__annual_mean_temperature_c_coverage": "temperature_data_coverage_fraction",
    "climate__annual_precipitation_mm": "annual_total_precipitation_mm",
    "climate__annual_precipitation_mm_coverage": "precipitation_data_coverage_fraction",
    "climate__weather_status": "climate_data_status",
    "climate__temperature_c_anomaly": "temperature_anomaly_from_2010_2014_celsius",
    "climate__temperature_c_trailing5_slope_per_year": "temperature_5yr_trend_celsius_per_year",
    "climate__precipitation_mm_anomaly": "precipitation_anomaly_from_2010_2014_mm",
    "climate__precipitation_mm_trailing5_slope_per_year": "precipitation_5yr_trend_mm_per_year",
    "terrain__terrain_sampled_pixels": "terrain_pixels_sampled",
    "terrain__terrain_valid_pixels": "terrain_valid_pixels",
    "terrain__terrain_valid_fraction": "elevation_data_coverage_fraction",
    "terrain__slope_valid_fraction": "slope_data_coverage_fraction",
    "terrain__mean_elevation_m": "mean_elevation_metres",
    "terrain__elevation_sd_m": "elevation_standard_deviation_metres",
    "terrain__mean_slope_degrees": "mean_slope_degrees",
    "terrain__terrain_status": "terrain_data_status",
    "climate__annual_mean_temperature_c__qa_reason": "temperature_missing_or_quality_reason",
    "climate__annual_precipitation_mm__qa_reason": "precipitation_missing_or_quality_reason",
    "climate__temperature_c_anomaly__qa_reason": "temperature_anomaly_missing_or_quality_reason",
    "climate__temperature_c_trailing5_slope_per_year__qa_reason": "temperature_trend_missing_or_quality_reason",
    "climate__precipitation_mm_anomaly__qa_reason": "precipitation_anomaly_missing_or_quality_reason",
    "climate__precipitation_mm_trailing5_slope_per_year__qa_reason": "precipitation_trend_missing_or_quality_reason",
    "terrain__mean_elevation_m__qa_reason": "elevation_missing_or_quality_reason",
    "terrain__elevation_sd_m__qa_reason": "elevation_variation_missing_or_quality_reason",
    "terrain__mean_slope_degrees__qa_reason": "slope_missing_or_quality_reason",
    "forest__baseline_canopy_percent": "mean_tree_canopy_cover_in_2000_percent",
    "forest__baseline_forest_ha": "forest_area_in_2000_hectares_at_30pct_threshold",
    "forest__remaining_baseline_forest_proportion": "remaining_2000_forest_share_at_end_of_year",
    "forest__annual_loss_ha": "tree_cover_loss_in_current_year_hectares",
    "forest__cumulative_prior_loss_ha": "tree_cover_loss_before_current_year_hectares",
    "forest__years_since_previous_loss": "years_since_last_tree_cover_loss_before_current_year",
    "forest__previous_1yr_loss_ha": "tree_cover_loss_in_previous_1_year_hectares",
    "forest__previous_1yr_window_complete": "previous_1_year_loss_window_available",
    "forest__previous_3yr_loss_ha": "tree_cover_loss_in_previous_3_years_hectares",
    "forest__previous_3yr_window_complete": "previous_3_year_loss_window_available",
    "forest__previous_5yr_loss_ha": "tree_cover_loss_in_previous_5_years_hectares",
    "forest__previous_5yr_window_complete": "previous_5_year_loss_window_available",
    "forest__annual_loss_fraction_of_baseline": "current_year_loss_share_of_2000_forest",
    "forest__cumulative_prior_loss_fraction_of_baseline": "prior_cumulative_loss_share_of_2000_forest",
    "forest__previous_1yr_loss_fraction_of_baseline": "previous_1yr_loss_share_of_2000_forest",
    "forest__previous_3yr_loss_fraction_of_baseline": "previous_3yr_loss_share_of_2000_forest",
    "forest__previous_5yr_loss_fraction_of_baseline": "previous_5yr_loss_share_of_2000_forest",
    "forest__previous_loss_detected": "tree_cover_loss_detected_before_current_year",
    "forest__forest_coverage": "forest_source_observed_area_fraction",
    "forest__sampled_to_polygon_area_ratio": "forest_sampled_area_to_grid_cell_area_ratio",
    "forest__feature_status": "forest_data_status",
    "forest__canopy_threshold_percent": "forest_definition_canopy_threshold_percent",
    "fragmentation__canopy_threshold_percent": "fragmentation_canopy_threshold_percent",
    "fragmentation__cell_patch_count": "forest_patch_count_in_grid_cell",
    "fragmentation__mean_cell_patch_ha": "mean_forest_patch_area_inside_cell_hectares",
    "fragmentation__largest_cell_patch_land_fraction": "largest_forest_patch_share_of_cell_land",
    "fragmentation__largest_cell_patch_forest_fraction": "largest_patch_share_of_cell_forest",
    "fragmentation__edge_m_per_land_ha": "forest_edge_metres_per_land_hectare",
    "fragmentation__mean_nearest_patch_centroid_m": "mean_nearest_forest_patch_centroid_distance_metres",
    "fragmentation__mapped_observation_coverage": "fragmentation_source_coverage_fraction",
    "fragmentation__mapped_land_pixels": "mapped_land_pixels_for_fragmentation",
    "fragmentation__forest_pixels": "forest_pixels_for_fragmentation",
    "fragmentation__no_forest": "no_forest_at_30pct_threshold",
    "fragmentation__fragmentation_status": "fragmentation_data_status",
    "pressure__population_count": "estimated_population_count",
    "pressure__population_density_per_km2": "estimated_population_density_per_sq_km",
    "pressure__population_coverage": "population_data_coverage_fraction",
    "pressure__population_source_year": "population_raster_year",
    "pressure__population_status": "population_data_status",
    "forest_core_data_available": "all_core_forest_hri_inputs_available",
    "pressure_extension_data_available": "core_forest_and_population_inputs_available",
}

GROUP_PURPOSE = {
    "cell_id": "Identifier",
    "reference_year": "Identifier",
    "climate__": "Climate predictor or climate-HRI scenario",
    "terrain__": "Static model and ecological context",
    "forest__": "Forest condition, disturbance, QA, or future target source",
    "fragmentation__": "Forest fragmentation measurement or QA",
    "pressure__": "Human-pressure extension (2010–2020)",
    "forest_core_data_available": "Availability flag",
    "pressure_extension_data_available": "Availability flag",
}


def purpose(column):
    for prefix, value in GROUP_PURPOSE.items():
        if column == prefix or column.startswith(prefix):
            return value
    raise KeyError(column)


def main():
    data = pd.read_csv(SOURCE, low_memory=False)
    assert set(data.columns) == set(ALIASES), {
        "missing_aliases": sorted(set(data.columns) - set(ALIASES)),
        "unused_aliases": sorted(set(ALIASES) - set(data.columns)),
    }
    assert len(set(ALIASES.values())) == len(ALIASES), "Readable names must be unique"

    readable = data.rename(columns=ALIASES)
    readable.to_csv(OUTPUT, index=False)

    dictionary = pd.read_csv(RELEASE / "master_feature_dictionary.csv")
    guide = pd.DataFrame({
        "column_number": range(1, len(data.columns) + 1),
        "readable_column_name": [ALIASES[c] for c in data.columns],
        "original_column_name": data.columns,
        "data_group_and_research_use": [purpose(c) for c in data.columns],
    }).merge(dictionary.rename(columns={"feature": "original_column_name"}),
             on="original_column_name", how="left", validate="one_to_one")
    assert guide.source_table.notna().all()
    guide.to_csv(GUIDE, index=False)

    # Header conversion must not alter values, row order, or key uniqueness.
    restored = readable.rename(columns={v: k for k, v in ALIASES.items()})
    pd.testing.assert_frame_equal(data, restored)
    assert not readable.duplicated(["grid_cell_id", "year"]).any()

    report = {
        "source": str(SOURCE.relative_to(ROOT)),
        "readable_output": str(OUTPUT.relative_to(ROOT)),
        "column_guide": str(GUIDE.relative_to(ROOT)),
        "rows": len(readable), "columns": len(readable.columns),
        "duplicate_keys": int(readable.duplicated(["grid_cell_id", "year"]).sum()),
        "values_changed": False,
        "note": "Human-readable copy only; canonical source remains authoritative for code."
    }
    (RELEASE / "readable_dataset_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

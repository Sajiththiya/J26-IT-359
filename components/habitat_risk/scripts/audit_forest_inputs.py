"""Audit recovered forest rasters without creating target labels or loading full tiles."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / "reports/audits"
    cfg = json.loads((ROOT / "configs/study.json").read_text())
    grid_id = f"lka_laea_{int(cfg['grid_size_m'])}m"
    grid = gpd.read_file(ROOT / f"data/interim/spatial/{grid_id}_grid.geojson")
    locations = pd.read_csv(ROOT / "data/interim/location_reference.csv")
    forest = pd.read_csv(ROOT / "data/interim/location_forest_review.csv")
    locations = locations.merge(forest, on="location_id", validate="one_to_one")
    metadata, comparisons, footprints = [], [], {}
    for path in sorted((ROOT / "data/raw/forest").glob("*.tif")):
        band = next((b for b in ["treecover2000", "lossyear", "datamask"] if b in path.name), "unknown")
        with rasterio.open(path) as src:
            if src.crs != rasterio.crs.CRS.from_epsg(4326):
                raise ValueError("Audit expects WGS84 inputs; adapt coordinate transformation before sampling.")
            metadata.append({"path": str(path.relative_to(ROOT)), "band_from_filename": band,
                             "crs": str(src.crs), "bounds": list(src.bounds),
                             "width": src.width, "height": src.height, "count": src.count,
                             "dtype": src.dtypes[0], "pixel_size_degrees": list(src.res),
                             "transform": list(src.transform), "nodata": src.nodata,
                             "mask_flags": [[x.name for x in flags] for flags in src.mask_flag_enums]})
            footprints.setdefault(band, []).append(box(*src.bounds))
            inside = (locations.longitude.ge(src.bounds.left) & locations.longitude.lt(src.bounds.right)
                      & locations.latitude.gt(src.bounds.bottom) & locations.latitude.le(src.bounds.top))
            # Deterministic small sample, for consistency checks rather than full raster validation.
            candidates = locations.loc[inside].sort_values("location_id")
            subset = candidates.iloc[np.linspace(0, len(candidates)-1, min(250, len(candidates)), dtype=int)] if len(candidates) else candidates
            values = [int(v[0]) for v in src.sample(zip(subset.longitude, subset.latitude))]
            if band in {"treecover2000", "lossyear"}:
                limit = 100 if band == "treecover2000" else 24
                assert all(0 <= value <= limit for value in values), "Unexpected sampled band values"
            for (_, row), value in zip(subset.iterrows(), values):
                expected = int(row.treecover2000) if band == "treecover2000" else (int(row.forest_loss_year)-2000 if row.forest_loss_year > 0 else 0) if band == "lossyear" else None
                comparisons.append({"location_id": row.location_id, "raster": path.name,
                                    "sampled_value": value, "existing_value": expected,
                                    "agrees": value == expected if expected is not None else None})
    from shapely.ops import unary_union
    for tile in ["10N_070E", "10N_080E"]:
        group = [m for m in metadata if tile in m["path"]]
        assert len(group) == 3, f"Missing band for {tile}"
        assert all(all(m[key] == group[0][key] for key in
                       ["crs", "transform", "width", "height", "dtype", "count"])
                   for m in group), f"Raster alignment mismatch: {tile}"
    manifest = json.loads((ROOT / "data/metadata/forest_download_manifest.json").read_text())
    provider_verified = len(manifest) == 6 and all(m["provider_checksum_verified"] for m in manifest)
    coverage = grid[["cell_id", "geometry"]].to_crs(cfg["projected_crs"])
    available = []
    for band in ["treecover2000", "lossyear", "datamask"]:
        union = unary_union(footprints.get(band, []))
        available.append(union)
        projected = gpd.GeoSeries([union], crs="EPSG:4326").to_crs(coverage.crs).iloc[0]
        coverage[f"{band}_footprint_fraction"] = coverage.geometry.intersection(projected).area / coverage.geometry.area
    common = available[0].intersection(available[1])
    point_geo = gpd.GeoSeries(gpd.points_from_xy(locations.longitude, locations.latitude), crs="EPSG:4326")
    locations["within_tree_loss_footprints"] = point_geo.covered_by(common).to_numpy()
    fractions = coverage[["treecover2000_footprint_fraction", "lossyear_footprint_fraction"]].min(axis=1)
    grid_counts = {"fully_inside_tree_loss_footprints": int(fractions.ge(1-1e-6).sum()),
                   "partially_inside_tree_loss_footprints": int((fractions.gt(1e-6)&fractions.lt(1-1e-6)).sum()),
                   "outside_tree_loss_footprints": int(fractions.le(1e-6).sum())}
    sample = pd.DataFrame(comparisons)
    summary = {"raster_count": len(metadata), "bands_found": sorted(footprints),
               "locations_outside_tree_loss_footprints": int((~locations.within_tree_loss_footprints).sum()),
               "grid_counts": grid_counts,
               "sample_comparisons": int(sample.existing_value.notna().sum()),
               "provider_checksums_verified_at_download": provider_verified,
               "aligned_tile_groups": 2,
               "sample_mismatches": int(sample.agrees.eq(False).sum()) if len(sample) else None,
               "footprint_is_not_valid_data_mask": True,
               "ready_for_full_country_labels": False,
               "remaining": ["Review grid-level evidence and cells with no pixel centres",
                             "Justified canopy threshold, coverage policy and final spatial scale"]}
    (out / "forest_raster_metadata.json").write_text(json.dumps(metadata, indent=2)+"\n")
    (out / "forest_input_audit.json").write_text(json.dumps(summary, indent=2)+"\n")
    coverage.drop(columns="geometry").to_csv(out / "forest_grid_footprint_coverage.csv", index=False)
    locations.loc[~locations.within_tree_loss_footprints, ["location_id", "latitude", "longitude"]].to_csv(out / "locations_outside_forest_tiles.csv", index=False)
    sample.to_csv(out / "forest_point_sample_check.csv", index=False)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()

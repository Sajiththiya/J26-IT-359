# Recovered forest and upstream data evidence

## Update: missing tiles obtained (2026-10-02)

All four files listed in the original inspection below have now been downloaded from the [official v1.12 archive](https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/download.html). All six project TIFFs, including the original eastern pair, match provider MD5 checksums and file lengths. See `data/metadata/forest_download_manifest.json` and the refreshed `forest_input_audit.json`. The original inspection below is retained as history. Its missing-file and filename-only provenance findings are superseded. Grid evidence is now extracted: 2,867 cells have mapped land evidence and two tiny clipped cells have no pixel centres. See Notebook 06. Threshold justification, final eligibility and model readiness remain unresolved.

Mapped loss is a remote-sensing proxy. The provider notes changing detection methods over time and cautions against interpreting pixel sums as definitive unbiased area estimates. Report mapped areas and preserve these limitations in the research.

## Original inspection (before downloads)

Source folder: `/Users/keerthikeerthi/Desktop/Final dataset for RP`.

Two original TIFFs were copied byte-for-byte into `data/raw/forest/`; the external files were not changed. The upstream `build_final_dataset.py` was archived under `data/raw/source_scripts/` for inspection, not execution. The copy manifest records original paths and SHA-256 checksums.

## Forest raster inspection

Both TIFFs identify Hansen GFC 2024 v1.12 in their filenames. They are aligned WGS84, single-band uint8 rasters, 40,000 × 40,000 pixels, with 0.00025-degree cells and bounds 80–90°E, 0–10°N. Provider authenticity is not established by filename alone. Neither TIFF declares no-data, and their internal masks mark all pixels valid; this does not replace the product's land/water/no-data band.

The working country grid includes 2,544 cells wholly inside the available tree/loss footprints, 66 partially covered cells and 259 outside cells. There are 1,052 observation locations outside those footprints. These are different from the 17 points outside the country boundary.

For a deterministic sample of 250 covered locations, both TIFF bands agree with existing point-level forest values (500 comparisons, zero mismatches). This supports consistency in the sampled eastern locations only, not original extraction correctness across the country. Existing western CSV values cannot be validated using these TIFFs.

The [official v1.12 catalog](https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2024_v1_12) documents canopy cover for 2000, loss-year codes 1–24 for 2001–2024 (0 for no mapped loss), and a separate datamask distinguishing no-data, land and water. The release is superseded; keep all tiles on one recorded release if retaining v1.12.

Remaining raster inputs for this tile layout:

- `Hansen_GFC-2024-v1.12_treecover2000_10N_070E.tif`
- `Hansen_GFC-2024-v1.12_lossyear_10N_070E.tif`
- `Hansen_GFC-2024-v1.12_datamask_10N_070E.tif`
- `Hansen_GFC-2024-v1.12_datamask_10N_080E.tif`

These are expected input names, not claims that downloads or their availability have been verified. Full-country label generation remains blocked by coverage/masking and unresolved eligibility/coverage rules. Do not assign missing western pixels zero loss.

## Upstream CSV construction

The supplied combined CSV has the same SHA-256 as the project's raw combined CSV. The build script maps each bird coordinate to the nearest location in the weather table using Haversine distance, then joins weather on city and observation date. It assigns that source location's elevation to the bird record. Consequently, the existing elevation is a weather-location attribute, not a DEM sample at the bird coordinate. Replace it with verified terrain extraction if modelling local elevation; alternatively rename and document it as weather-source elevation.

The weather file contains 147,480 rows, 30 distinct city/coordinate/elevation combinations and 21 elevation values, covering 2010-01-01 through 2023-06-17. No duplicate city/date keys were found. The retained combined CSV uses a subset of these locations, explaining its 18 elevation values. The original provider, units and whether the source locations represent stations or gridded estimates remain unverified. Do not call them measured weather stations based on the script's variable naming.

The bird and extracted forest inputs each contain 228,274 rows. Their coordinates and common names align in the supplied row order. However, the script attaches forest columns by row index after merges rather than by a verified unique identifier; the matching lengths alone are not a general guarantee of correctness. Future rebuilding should use explicit keys and merge validation.

The so-called complete CSV is filtered only on nonmissing maximum temperature. It is not a general complete-case filter over all predictors. The original bird input includes locality IDs, but no explicit checklist identifier column; locality ID must not be substituted for checklist ID.

No source code was executed and no original data were repaired in this inspection. The findings resolve parts of the assembly method, not all provider provenance. Species vulnerability and risk scores are unchanged.

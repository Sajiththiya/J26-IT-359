# Forest grid evidence

Run `scripts/download_forest_inputs.py`, then `scripts/audit_forest_inputs.py`, then `scripts/summarize_forest_grid.py` using the project environment. Notebook 06 explains and reproduces the last step. Downloads use curl with certificate verification and provider MD5 comparison; SHA-256 is recorded locally. Existing source files are preserved and verified, never silently replaced.

## Outputs

`data/interim/spatial/lka_laea_5000m_forest_evidence.csv` has one row per provisional country-clipped cell, with geodesic mapped area for source no-data, land and persistent water, and mean canopy on mapped land.

`data/interim/spatial/lka_laea_5000m_canopy_loss_histogram.csv` has one row per nonempty cell/canopy/loss-code combination. It includes only datamask=1 land. It is an intermediate evidence table, **not a predictor table**: loss codes contain information through 2024.

`reports/audits/forest_grid_evidence.json` records status counts and limitations.

## Geometry and missingness

Rasterize each country-clipped cell on native raster windows using pixel-centre membership. Calculate each included pixel's WGS84 ellipsoidal area from its row coordinates. The tile grids share latitude origin and pixel size, so row areas can be reused. This avoids treating all geographic pixels as identical area. It does not fractionally allocate boundary pixels: coastal and very small cells require review. No pixel centres gives missing fractions, not zero loss.

Observed area fraction uses (land + persistent water)/(land + water + no-data) among included pixel centres. It measures source coverage, not the fraction of the cell that is forest. Water and no-data are excluded from canopy/loss histograms. Do not interpret datamask as a year-specific observation-quality mask.

## Future target calculation

After justifying canopy threshold C and reference year t, denominator is the histogram area where canopy >= C and loss code is zero or 2000 + loss code > t. Numerator is the eligible area with 2000 + loss code = t + 1. Reject years beyond the source release; a zero denominator is undefined. This estimates mapped loss of remaining baseline forest, excludes regrowth reconstruction, and is not bird population decline.

Do not treat full-period code-zero status or future losses as input features. Historical canopy depletion predictors may use only loss years through the reference year. Release revisions make retrospective validation a hindcast, not proof that identical inputs were available historically.

## Attribution and limitations

Source: Hansen/UMD/Google/USGS/NASA. Hansen et al. (2013), Science 342, 850–853. Pinned release: GFC 2024 v1.12. [Official release and usage notes](https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/download.html). [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

These summaries are mapped areas, not unbiased statistical estimates. Detection changes across years and grid/boundary choices must be addressed in research limitations and sensitivity checks. No canopy threshold, minimum forest area, final coverage rule or ecological grid scale is finalized here.

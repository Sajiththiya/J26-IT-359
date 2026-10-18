# Review of environmental inputs prepared on 2026-10-08

Release: `data/processed/hri/pre_hri_v1/`. The machine-readable master audit
is authoritative for execution time, checksums, coverage and open decisions.
This review concerns input preparation; no HRI score or model was fitted.

## Coverage and checks

| Item | Result |
|---|---:|
| National grid cells | 2,869 |
| Years | 2010–2023 |
| Master cell-year rows | 40,166 |
| Duplicate cell-year keys | 0 |
| Forest-core candidate measurements available | 39,368 rows |
| Forest-core plus population measurements available | 30,410 rows |
| Population product years downloaded | 11 (2010–2020) |
| Synthetic fragmentation tests passed | 7 |
| Cells in fragmentation scale/threshold check | 30 |

The two availability counts refer to specified candidate columns. They are
not final index eligibility counts. Forest-free cells, natural non-forest
habitats, and species applicability require explicit decisions before scoring.
All scaffold rows are retained, with missing values and source-specific flags.

## Threshold and resolution findings

The working forest threshold is >=30% treecover2000, with 10%/50% alternatives.
National remaining-cover rank correlations range from 0.9899 to 0.9974.
This supports reporting stability of ordering under these scenarios; it does
not prove equal loss totals or validate a forest definition for endemic birds.

In the stratified 30-cell 2020 fragmentation sample, the edge-density rank
correlation between 30 m and 60 m rasters is approximately 0.993. The
nearest-centroid-distance correlation is lower, approximately 0.884.
Absolute changes are retained in `fragmentation_scale_sensitivity_summary.csv`.
Sampled context/raster tests cannot establish national ecological robustness
or resolve the separate question of 5 km versus another assessment-grid size.

The official 1 km WorldPop aggregation was compared with the downloaded
100 m 2010 raster for 2,488 cells passing both coverage checks. The rank
correlation is 0.9996 and median absolute relative count difference is 1.95%.
Both resolution and boundary allocation differ between the two calculations;
the comparison is not a validation against observed population counts.

## Redundancy and indicator interpretation

Remaining forest proportion and largest cell-patch land fraction have
Spearman correlation about 0.9875. Including both with full independent
weights would strongly duplicate forest-amount information. Retain both
physical measurements for review but select/weight indicators deliberately.
Patch metrics are local, cell-clipped quantities; centroid distance is not
true edge-to-edge ecological connectivity.

Population density is a modelled human-pressure proxy. Global1 2021–2023
values are unavailable and remain missing. A consistent population-extended
index should use the supported period or wait for a documented alternative
series. Do not vary weights silently by year to compensate for missing data.

Climate and terrain remain context. In particular, absolute temperature or
precipitation anomalies are not automatically interpreted as adverse habitat
conditions. Vegetation health and conservation designation are explicitly
deferred; the release does not claim to measure those dimensions.

## Next research step

Use the prepared physical measurements to specify HRI applicability,
non-redundant indicators, transformations, missingness rules, alternative
weights, classes and independent ecological validation. The canopy threshold
is an analyst working choice and awaits supervisor review. Any subsequent
forecast experiment must use future observed outcomes, appropriate temporal
and spatial splits, and an explicit account of retrospective source revisions.

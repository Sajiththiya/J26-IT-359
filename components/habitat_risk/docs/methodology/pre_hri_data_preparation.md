# Data preparation before HRI construction

Prepared 2026-10-08. Execution entry point:
`scripts/prepare_hri_inputs.py`; visible numbered equivalent:
`notebooks/hri/05_hri_input_preparation.ipynb`.
Outputs are a new release at `data/processed/hri/pre_hri_v1/`.
Previous WP5/WP6 releases are retained. This release prepares physical
measurements; it does not assign risk scores, weights, classes or fit models.

## 1. Assessment and source timing

The row unit is one provisional 5 km country-clipped grid cell in one
reference year (2010–2023). The primary key is `cell_id, reference_year`.
Projected area uses the equal-area CRS in `configs/study.json`. Raster
coordinates are transformed explicitly to that CRS for fragmentation.
Population counts are allocated by native-pixel overlap area and divided by
the projected country-clipped cell area in km².

Forest condition is assessed at the **end** of year t. Loss through t may
affect year-t condition. Three-year prior loss uses t-3, t-2 and t-1.
Predicting a future outcome requires a later target year. Published
retrospective rasters can contain revised information unavailable in year t;
this workflow must not be described as a verified real-time forecasting
reconstruction. HRI normalisation and model preprocessing remain to be defined.

## 2. Forest canopy choice

The working primary threshold is **treecover2000 >= 30%**. WRI/GFW uses
30% as a common tree-cover reporting benchmark:
https://gfr.wri.org/annual-tree-cover-loss-data-explained
and https://gfr.wri.org/es/node/124 .
Some narrative descriptions say “greater than 30%”; our operator is explicitly
`>=`, retaining the existing histogram scenarios. This is an analyst's
documented working choice, not claimed supervisor/expert approval and not a
national legal forest definition or a species-specific ecological threshold.

All-country forest results at 10%, 30%, and 50% are retained with annual totals
and Spearman rank comparisons. The final interpretation must consider this
sensitivity. Canopy cover includes plantations; tree-cover loss is not always
permanent deforestation. The reconstruction tracks surviving **2000 baseline
tree cover**, excludes gains/regrowth, and is not a full map of contemporary
natural forest. Low remaining cover in a naturally non-forest cell cannot
automatically be called degradation. Habitat-type applicability needs review
before scoring all Sri Lankan endemic birds with a forest-oriented index.

## 3. Fragmentation

National calculations use 30 m nearest-neighbour resampling, four-neighbour
patch connectivity and a 1 km surrounding context. Reported patch areas are
the portions intersecting the focal cell, not whole national patch areas.
Observed coverage includes mapped land and persistent water; patch metrics
use mapped land. At least 95% observed pixel-centre coverage is required.
No-pixel or insufficient-coverage cells remain missing.

Forest-free cells explicitly have `no_forest=True`. Edge density is zero in
such cells, but zero must not be interpreted as low habitat risk. Mean patch
size and relative largest-forest-patch fraction are undefined when no forest
exists. A single contextual patch has undefined nearest-patch distance.
Nearest-centroid distance is a descriptive local approximation, not a measure
of edge-to-edge movement connectivity or species dispersal.

Thirty deterministic cells (six in each baseline forest-area quintile) test
30 m versus 60 m raster resolution, 1 km versus 2 km context, and 10/30/50%
thresholds in 2020. These tests assess raster/context assumptions; they do
**not** replace a comparison of 5 km assessment cells against another grid size.
Future-loss perturbation tests verify that changing events after 2020 does
not change 2020 fragmentation for these cells. Synthetic tests cover exact
threshold inclusion, water coverage, no forest, missing data and connectivity.

## 4. Population as a human-pressure proxy

Source: WorldPop Global1, annual unconstrained UN-adjusted Sri Lanka counts,
official 1 km aggregated product, 2010–2020. Product catalogue and methods:

- https://hub.worldpop.org/Global1_2000-2020
- https://www.worldpop.org/methods/populations/

Provider licence: CC BY 4.0. Attribute WorldPop / University of Southampton;
retain the download manifest, original source URLs and SHA-256 checksums.
The provider distributes modelled population counts, not observed habitat
damage. Each 1 km pixel's count is allocated by its intersection-area fraction
with each assessment cell, calculated in the equal-area CRS. This assumes
uniform population within each source pixel. Density is estimated persons
per country-clipped cell km². The downloaded 2010 100 m raster provides a
resolution/boundary-method sensitivity check using pixel-centre sums.
The official 1 km series is approximately 4 MB for all eleven years;
the 100 m reference raster is approximately 33 MB. Coastal masks affect coverage;
missing raster values are never treated as zero inhabitants.

**2021–2023 remain missing.** No Global1 values are invented, interpolated,
or carried forward. Global2 is not silently spliced into Global1: the provider
documents changed census inputs and modelling:
https://www.worldpop.org/blog/worldpop-global2-global-high-resolution-population-estimates-for-2015-2030/
Using two generations would require overlap calibration and a documented
comparability study. Original publication availability and internal covariate
dates are not established for simulated real-time prediction.

For a pressure-extended HRI, restrict the comparable period to 2010–2020
or obtain and validate a different complete series. A forest-oriented core can
be considered for 2010–2023 independently. Do not change HRI weights each year
because population is missing: this would change the meaning of the index.

## 5. Explicit scope and deferrals

- Vegetation: a harmonised QA-filtered annual NDVI series is not admitted.
  Sensor/season/cloud QA and a defensible reference are required. Surviving
  baseline tree cover does not measure vegetation health or greenness trends.
- Roads, built-up area and night lights: deferred rather than adding multiple
  correlated proxies; population supplies one pressure candidate where available.
  A modern road snapshot must not be presented as a historical annual layer.
- Protected areas and IBAs: deferred pending authorised polygons and temporal
  interpretation. They primarily supply designation/priority context; protection
  status does not guarantee low measured environmental pressure.
- Climate/terrain: existing audited measurements and missingness are retained
  as context. More rainfall, elevation, or absolute temperature/rainfall anomaly
  does not universally imply greater ecological risk. The earlier suggestion
  to automatically score absolute anomalies is not adopted.
- Bird observations and SVI remain separate. Observation counts are affected
  by sampling effort and are not direct environmental-risk scores.

## 6. Candidate review before HRI

Consider remaining baseline forest, prior three-year loss and a defensible
fragmentation variable as a small starting set **for forest-associated habitat**.
Population can form a separately labelled extension in supported years.
Cumulative loss, remaining cover, largest patch and overlapping loss windows
may double-count related evidence. The release supplies pairwise Spearman
correlations (with sample counts), an absolute-r >=0.8 review list, descriptive
complete-case VIF and distribution plots. These flag redundancy; they do not
automatically choose indicators or demonstrate ecological validity.

`forest_core_data_available` and `pressure_extension_data_available` mean only
that candidate measurements exist. They are not evidence of forest habitat,
bird presence, suitability, index validity or model-training eligibility.

Before HRI calculation, define ecological scope and eligibility, select
non-redundant indicators, source and document transformations, fix missingness
rules, compare weight schemes, justify class thresholds and identify independent
validation evidence. Supervisor review and full 5 km grid-scale sensitivity
remain open research decisions. No HRI is trained by this workflow.

## 7. Reproduction

Run the four stages in order, in the foreground:

```bash
python3 components/habitat_risk/scripts/prepare_hri_inputs.py --stage download
python3 components/habitat_risk/scripts/prepare_hri_inputs.py --stage forest
python3 components/habitat_risk/scripts/prepare_hri_inputs.py --stage population
python3 components/habitat_risk/scripts/prepare_hri_inputs.py --stage master
python3 -m unittest discover -s components/habitat_risk/tests -v
```

The notebook includes full function definitions and explicit execution cells.
Existing downloads are reused. Per-cell forest checkpoints permit resumption.
Re-running a stage replaces only its outputs within this new version directory.
The final master audit gives actual coverage; missing rows remain present in
the 40,166-row scaffold. Study-wide training readiness is not inferred from a
successful run.

# Expanded HRI: provisional priorities and sensitivity

Prepared 2026-10-21 following user approval to prepare provisional weights and sensitivity comparisons. The executable implementation is `notebooks/hri/08_expanded_hri_provisional_weights.ipynb`. Configuration is in `configs/hri_expanded_provisional.json`; outputs are in `data/processed/hri/expanded_provisional_v1/`.

This is a new exploratory version. It does not change the released core HRI, the old datasets, the fitted forecasting models, or the viewed final tests. Existing performance claims cannot be transferred to a new index definition.

## Provisional weights

| Domain | Component | Total-index weight |
| --- | --- | ---: |
| Forest | Forest amount risk | 20% |
| Forest | Recent loss risk | 15% |
| Forest | Cumulative loss risk | 10% |
| Forest | Fragmentation risk | 15% |
| Climate departure | Absolute temperature departure | 7.5% |
| Climate departure | Absolute precipitation departure | 7.5% |
| Climate departure | Absolute five-year temperature trend | 2.5% |
| Climate departure | Absolute five-year precipitation trend | 2.5% |
| Human pressure | Population density proxy | 20% |
| **Total** | | **100%** |

These numerical priorities are proposed analyst scenarios, not estimates from ecological experts or from the cited literature. Forest receives the largest domain share to retain the forest-oriented scope. The recent/cumulative pair receives less combined weight than in the original equal four-component index because both describe overlapping loss histories. Climate departures receive more weight than their correlated trend summaries. Grouping avoids giving a domain extra influence just because more related variables were measured.

The sources below support broad mechanisms and construction methods; they do not establish these percentages. The climate transformation is explicitly an exposure hypothesis: departures or trends in either direction are not automatically harmful to a particular species. Ecological applicability, weights, thresholds and validation still require review.

## What happens to every other available variable

The wide export retains the master measurements and all available observation context. A per-column register explains each variable's role and nominal weight.

- Raw annual temperature and precipitation supply the departure calculations. They do not receive another independent contribution on top of those departures.
- Elevation, elevation variability, slope, and sampled elevation are retained as terrain context. Generic terrain penalties are not assigned: a species-specific tolerance or response model is required.
- NDVI is retained. A separate sparse sampled-greenness sensitivity score assigns 10% to `1 - NDVI` for valid 0–1 values, with 55% forest, 20% climate and 15% population. It is a greenness illustration, not a validated degradation measurement. Its sensor, acquisition dates, seasonal comparability and QA provenance remain unresolved. Negative/water-like values are missing for this illustration. It is not a forecasting label.
- Land-cover categories retain their `ESA_CCI_`/`ESRI_` prefixes. No pressure is inferred from category integers. Product/year/QA verification and an ecologically justified response mapping are required. The category inventory lists all observed codes for review.
- Population count and population density describe the same pressure dimension; density supplies the weighted proxy, while count and coverage remain audit fields.
- Forest hectare/fraction/patch measures remain available, but multiple representations of the same signal are not each given additional independent weights.
- Bird records, survey effort, missing flags and coverage describe sampling and uncertainty. They are not automatically interpreted as habitat degradation.
- Annual national NDVI, land-cover transitions, roads, built-up fractions, night lights and historical protection layers are not present as accepted aligned national time series. No substitute values are fabricated.

## Calibration, coverage and missing values

The four forest risk components retain the original frozen definitions. Raw annual climate measurements are compared with each cell's 2010–2014 mean, requiring at least three valid reference years. Absolute departures and absolute trailing five-year slopes are scaled linearly by their eligible 2010–2014 P99 and clipped to 0–1. Trend calibration within this window has limited years (the earliest full five-year window ends in 2014), which is a methodological limitation.

Population uses log-density scaled by the eligible 2010–2014 log-density P99. A source year after the assessment year is rejected. All published provisional assessments start in 2015, after calibration. Measurements in earlier years remain in the table as calibration/context rows.

Every positively weighted component must be observed. Missing components leave the score missing and reduce the reported available nominal weight. The remaining weights are not silently renormalized. Therefore, population-dependent scores are unavailable after 2020.

A separately declared forest-plus-climate index uses 80% forest and 20% climate over its own eligible period. It has a different scope; it is not a substitute population measurement. The next-year expanded-label column uses an exact cell/year join and preserves absent future outcomes as missing. The current data do not support complete population-inclusive target labels for a 2022–2023 forecast test.

## Sensitivity comparisons

The notebook compares the primary 60/20/20 split with balanced domains, forest emphasis, climate emphasis and population emphasis. All comparisons use identical complete cell-years. Outputs include rank correlations, class transitions, top-decile membership overlap, score differences and indicator correlations. Two hundred hierarchical Dirichlet draws explore domain and within-domain weights. Their P05/P95 score envelope reflects choices of weights; it is not a statistical confidence interval or expert-consensus range.

Communication classes retain the original thirds for comparison. They are not ecological safety thresholds. No model accuracy metric is used to choose the index weights, and no forecasting model is retrained in this notebook.

## Evidence sources and their limits

- [OECD/JRC composite-indicator handbook](https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf): weighting choices, correlated indicators, double counting and sensitivity methods; no bird-specific numerical weights.
- [Foden et al. (2013)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0065427): climate exposure, sensitivity and adaptive capacity are distinct dimensions; does not validate these departure/trend transformations.
- [Venter et al. (2016)](https://www.nature.com/articles/ncomms12558): multiple human pressures and a population proxy; population alone is not their full human-footprint measure.
- [MODIS vegetation-index algorithm documentation](https://lpdaac.usgs.gov/documents/449/MOD13_ATBD_V5.pdf): vegetation-index measurement and quality considerations; does not validate the project's sampled NDVI provenance or this greenness score.

Next decisions are ecological review of domains, a species-specific terrain/climate response, verified land-cover mapping, and accepted vegetation/later-population measurements. Final weights require those decisions and a recorded justification.

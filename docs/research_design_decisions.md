# Work Package 1 — Research design decisions

Version: 1.0 · Decision date: 2026-10-05 · Status: research design frozen; measurement and data acceptance gates remain open.

This document adopts the requested Work Package 1 decisions for the habitat-risk component. It is the authoritative design baseline for subsequent datasets, indicator selection and modelling. A design freeze does not certify existing data or establish validated scores. Changes to the objective, units, period, scope or prediction task require a dated amendment here, its rationale and a list of affected datasets and analyses.

## 1. Research problem and objective

The research problem is how to combine environmental evidence and endemic-bird evidence into an interpretable assessment of habitat risk and conservation priority across Sri Lanka, while accounting for incomplete observations, species differences, spatial dependence and time. Environmental condition, species sensitivity and conservation importance must have explicit, distinguishable roles so that a priority map has an auditable interpretation.

**Confirmed objective:** Develop and evaluate a species-aware, spatially and temporally validated framework for identifying habitat-risk and conservation-priority areas for Sri Lankan endemic birds.

The operational objectives are to construct a transparent environmental Habitat Risk Index (HRI), assess species vulnerability using supported traits, combine risk with biodiversity importance for conservation prioritisation, evaluate prediction of future observed degradation, and quantify sensitivity to analytical choices. Species awareness enters through verified species evidence, vulnerability and priority interpretation; a national environmental HRI alone does not demonstrate species-specific habitat suitability or population effects.

## 2. Confirmed assessment structure

| Decision | Adopted value and interpretation |
|---|---|
| Study area | Entire Sri Lanka, using the versioned national boundary; retain all intersecting land cells regardless of bird-record coverage. |
| Primary spatial unit | Provisional 5 km × 5 km grid; nominal full-cell area 25 km². Boundary cells use their actual land intersection and documented denominators. |
| Environmental unit | Cell × year, unique key `(grid_version, cell_id, reference_year)`. |
| Species evidence unit | Cell × year × species, unique key `(grid_version, cell_id, reference_year, species_id)`. |
| Environmental assessment period | 2010–2023 inclusive; one calendar-year assessment per eligible cell. Missing evidence stays explicit. |
| Species scope | Sri Lankan endemic birds, subject to a versioned taxonomic authority and explicit inclusion decisions. |
| HRI purpose | Environmental habitat-risk assessment. |
| Vulnerability purpose | Species sensitivity assessment, with uncertainty and evidence dates. |
| Priority purpose | Combine environmental risk and biodiversity importance, including supported species vulnerability. |
| ML purpose | Predict a future observed degradation outcome using information available by the end of year `t`. |

Reuse the configured Sri Lanka-centred Lambert azimuthal equal-area projection (`+proj=laea +lat_0=7.9 +lon_0=80.7 +datum=WGS84 +units=m +no_defs`) and origin `(0, 0)` as the provisional geometry baseline. Record the boundary checksum, CRS, origin, cell size and grid-generation version in each release. A changed geometry requires a new grid version; cell identifiers alone are insufficient across resolutions.

Assess 5 km suitability against coordinate uncertainty, native environmental resolution, coverage, within-cell habitat variation and species ecology. Plan a 10 km comparison, recomputing indicators from their underlying numerators/denominators or sources and repeating relevant assessment steps. Compare coverage, risk/priority rank stability and high-priority area overlap on a common spatial support. Do not compare unmatched cell identifiers. If the comparison is infeasible, document the reason and explicitly limit conclusions to the 5 km scale. Neither resolution is established here as biologically optimal.

## 3. Final research questions

1. How can environmental and species evidence identify habitat-risk areas for Sri Lankan endemic birds?
2. Which environmental indicators contribute most to habitat risk?
3. How can habitat risk and species vulnerability be combined to identify conservation priorities?
4. Can conditions in year `t` predict habitat degradation in a future year?
5. How does model performance differ under random, spatial and temporal validation?
6. How stable are HRI and priority results when weights and thresholds change?

RQ1 is addressed by the documented HRI and evidence coverage; RQ2 by index contribution and sensitivity analysis, with predictive feature importance reported separately; RQ3 by explicit priority alternatives; RQ4–5 by held-out future-outcome prediction; and RQ6 by sensitivity experiments. Predictive importance and index weights do not establish causal environmental effects.

## 4. Definitions and assessment roles

### Habitat Risk Index (HRI)

HRI is an environmental composite at cell × year describing habitat condition or pressure relevant to the study. Higher values will consistently indicate greater risk. Indicator eligibility, ecological direction, temporal availability, transformations, normalisation, weights, minimum coverage and class thresholds must be specified before scores are produced. Continuous scores are the primary assessment; any Low/Moderate/High classes require a separate justification.

Elevation, rainfall and temperature are environmental context until an ecologically supported risk transformation is established. Bird record counts and species vulnerability are not direct HRI components under this design. Missing environmental evidence is not zero risk; insufficient coverage produces an unavailable assessment with a reason. Any permitted imputation or partial-index calculation must be declared and evaluated before use.

### Species vulnerability

Vulnerability describes species sensitivity using verified, relevant traits or assessments. Store its components, sources, uncertainty and effective dates at species × trait-snapshot level. A contemporary trait snapshot may support a clearly labelled retrospective interpretation, but cannot silently become a historical predictor. No vulnerability formula or weights are approved by this design freeze.

### Conservation priority

Priority is a decision-support assessment at cell × year combining HRI with biodiversity importance derived from eligible species evidence and supported vulnerability. Retain species-level contributions so that the aggregate is explainable. Select the combination rule, treatment of low-risk but important habitat, normalisation and thresholds before producing a ranked map. Audit shared inputs to prevent double-counting the same evidence through multiple components.

Occurrence supports recorded presence in its eligible place and time; it does not establish abundance, absence elsewhere or complete richness. Unknown species coverage must remain distinguishable from low biodiversity importance. Report HRI, biodiversity evidence, vulnerability contributions and coverage alongside any priority score. Recommendations remain conditional on the evidence and are not a demonstrated conservation intervention effect.

## 5. Dataset contracts: row units and research purposes

Paths below are relative to `components/habitat_risk/`. Existing preparation outputs are candidates, not accepted analysis releases. `scientific_name` is the current species join field; a frozen taxonomic mapping must supply a stable `species_id` or formally adopt the accepted name as its versioned identifier before release.

| Dataset or planned product | One row represents / unique key | Research purpose |
|---|---|---|
| `data/raw/observations/final_dataset_complete.csv` | One supplied observation record; preserve source-file checksum + original row number | Immutable source evidence and provenance; its historical filename does not denote model readiness. |
| Cleaning draft and deduplicated candidate | One source observation; `source_row_id` with source version | Review quality, dates, coordinates, effort and duplicate decisions without losing provenance. |
| Endemic candidates and mapping review | One source observation; `source_row_id` | Record eligibility and mapping/date exceptions; retain unresolved cases for review. |
| Taxonomic inclusion register | One source taxon × taxonomy version | Map recorded names to accepted species and justify endemic inclusion/exclusion/uncertainty. |
| Grid geometry and static terrain | One cell per grid version | Provide spatial support, land area, terrain context and coverage. |
| Annual forest/weather/other environmental summaries | One cell × year per grid version per source product version | Supply temporally aligned environmental measurements and valid-area denominators. |
| `data/interim/hri/hri_cell_year_preparation.csv` | One cell × year per grid version | Candidate environmental assessment table; occurrence context is not an environmental replicate. |
| `data/interim/hri/hri_cell_year_species_evidence.csv` | One cell × year × accepted species per grid version | Dated species evidence, observation effort where defensible, coverage and uncertainty. |
| `data/metadata/species_traits.csv` and later versioned snapshots | One species per snapshot; snapshot version required on release | Source species sensitivity evidence; current metadata is partially verified. |
| Trait evidence ledger | One species × trait × source/evidence entry | Preserve traceable trait claims, conflicts and dates. |
| Accepted HRI release | One cell × year per grid version and HRI specification version | Publish indicator values, continuous HRI, optional class and assessment coverage (RQ1–2, RQ6). |
| Vulnerability release | One species × vulnerability specification/trait snapshot | Publish sensitivity components, score if justified, and uncertainty (RQ3). |
| Priority species contributions | One cell × year × species per grid/specification version | Explain each eligible species contribution and evidence status (RQ3). |
| Priority release | One cell × year per grid/priority specification version | Combine risk and biodiversity importance with coverage and uncertainty (RQ3, RQ6). |
| Future observed outcome | One cell × predictor year × forecast horizon per grid/outcome version | Store observed future degradation, outcome interval and eligibility; no index-derived labels (RQ4). |
| ML analysis table | One cell × predictor year × horizon per grid/data release | Join predictors available by `t` to their observed future outcome; species rows must be aggregated before this join (RQ4–5). |
| Validation assignments | One ML sample × validation scheme × fold/repeat | Record training/validation/test membership and excluded buffers reproducibly (RQ5). |
| Held-out predictions | One ML sample × scheme × fold/repeat × model | Evaluate genuinely held-out outcomes with the corresponding observed label (RQ4–5). |
| Sensitivity results | One cell × year × scenario per grid/specification version | Compare scores, ranks, classes and priority selection across prespecified alternatives (RQ6). |
| Evaluation summary | One model/assessment × scheme × fold or aggregate × metric × scenario | Report performance, uncertainty and sensitivity without treating folds as new observations. |

Every later dataset must declare its row unit, unique key, research purpose/RQ, source and specification versions, geographic/temporal coverage, column meanings/units, missingness semantics and eligibility rules in accompanying metadata before it enters analysis. New products absent from this register must add a contract here first. Validate key uniqueness, join cardinality, date eligibility, valid-area coverage and sample counts before and after joins. Never expand the environmental sample size by joining one cell-year to multiple species rows.

Environmental tables retain the national cell-year scaffold, including unavailable assessments. Species evidence may be stored sparsely for observed combinations, provided separate coverage/eligibility metadata makes omitted combinations explicitly unknown. A dense species table must likewise distinguish unobserved from surveyed non-detection; the current source has no verified checklist key supporting an automatic absence interpretation.

## 6. Intended ML target and temporal alignment

The confirmed prediction task is future observed environmental degradation at cell level. The primary design horizon is one year: predictors through the end of year `t` predict degradation during calendar year `t+1`. A candidate operational target is the fraction of eligible habitat present at the end of `t` that is observed to be lost during `t+1`. Its habitat definition, observation source, measurement validity, denominator, minimum valid coverage and uncertainty must be accepted before labels are built. Zero eligible habitat or unavailable observation coverage yields an ineligible/missing target, not zero loss.

Forest-cover loss may operationalise this candidate if evidence supports it, but would restrict prediction claims to that measured habitat-change outcome; it does not alone validate endemic-bird population risk or all forms of habitat degradation. Outcome observations must be distinct from same-time formula-generated HRI labels. Predicting a calculated HRI from its own ingredients is not the adopted ML evaluation.

With environmental and outcome coverage restricted to 2010–2023, eligible one-year prediction origins are at most 2010–2022. The 2023 environmental assessment remains valid, but a 2023-origin forecast requires a separately approved and verified 2024 outcome extension. Earlier origins may also be excluded where baseline or lagged measurements are unavailable. Longer horizons are secondary amendments and must not reuse an incompatible split.

All features must have an explicit availability cutoff. Exclude future loss, full-period occurrence summaries and later trait information from historical predictors unless they demonstrably existed at prediction time. Audit the raw CSV's `forest_loss`, `forest_loss_year`, weather and tree-cover fields before any predictive reuse. A modern extraction can represent historical measurements, but retrospective processing and any unavailable-at-the-time information must be disclosed. Fit imputation, scaling, feature selection and any learned thresholds using training data only.

## 7. Validation and sensitivity strategy

Compare the following schemes on the same target, eligible data rules, baseline and metric definitions; report differing test populations explicitly.

| Scheme | Required design | Interpretation |
|---|---|---|
| Random | Random held-out cell-year samples; keep identical samples and derived duplicates in one partition | Diagnostic benchmark; shared cells/nearby years can make performance optimistic. |
| Spatial | Group entire cells into spatial blocks; keep every year of a cell in its assigned block; select block/buffer distances from spatial dependence and geography | Generalisation to held-out locations. |
| Temporal | Forward validation: train on earlier information and test on later origins; training outcome windows must finish by the test forecast cutoff | Generalisation to later years. |
| Combined spatial–temporal, where feasible | Hold out both location blocks and later time intervals | Stronger test of transfer to new locations in a later period; report if sample size prevents it. |

Choose block sizes, fold counts, date cutoffs, embargoes for overlapping outcome windows and minimum eligible samples after coverage review but before fitting or inspecting test performance. Save assignments and seeds. Use validation data within the training partition for tuning; reserve final test partitions for final evaluation. Report fold/year/block counts and variation, accounting for dependence when calculating uncertainty.

For a continuous degradation fraction, prespecify MAE and RMSE and compare with a training-only constant baseline; add a past-observed-degradation persistence baseline where valid. If evidence instead supports a binary endpoint, amend the outcome specification before fitting and prespecify precision–recall performance, recall, precision and calibration with a training-derived decision threshold. Model family/count remains pending the existing two-model versus ten-model decision and is not resolved by WP1.

HRI and priority validation is separate from forecast validation. Assess independent ecological or habitat evidence where available, document independence from index inputs, and report explicitly when such validation cannot be performed. A good degradation forecast does not by itself validate priority rankings. Index contribution analysis and model explanations answer different questions; neither is causal attribution.

Prespecify sensitivity scenarios for plausible weights, risk/priority thresholds, indicator inclusion, normalisation, supported missing-data treatments, vulnerability uncertainty and grid resolution. Report score/rank changes, class transitions, high-priority area overlap and coverage changes against the baseline. Define scenario ranges before examining preferred maps; label unsupported alternatives as exploratory.

## 8. Known limitations and current repository evidence

- Observation records may reflect unequal effort, accessibility and detection. Counts cannot automatically be interpreted as abundance; missing observations cannot establish absence.
- Taxonomy and endemic inclusion require verification. The archived spatial audit lists 25 recorded scientific names; that is an inventory count, not an authoritative endemic-species total.
- The archived grid audit reports 2,869 cells, 1,112 with records and 17 locations outside the boundary. These are historical audit results and must be rechecked for the accepted release; they do not imply complete annual species coverage.
- A 5 km cell can contain mixed habitats and uncertain point locations. Boundary clipping, source resolution and incomplete raster coverage affect denominators and interpretation.
- Tree cover, forest loss and environmental context do not automatically measure species-specific habitat quality. Missing fragmentation, human-pressure or trait evidence must not be presented as already available.
- Current trait snapshots have incomplete verification and limited historical interpretation. Retrospective priority maps must state the dates of the vulnerability evidence used.
- Temporal coverage limits future-outcome samples; annual aggregation can hide seasonal effects. Spatial and temporal dependence reduces the effective independent sample size.
- HRI weights, vulnerability formulas, priority rules and classification thresholds remain unvalidated. Sensitivity supports robustness assessment but does not substitute for external validation.

Repository evidence reviewed for this decision: [component README](../components/habitat_risk/README.md), [dataset inventory](../components/habitat_risk/DATASETS.md), [existing workflow](../components/habitat_risk/docs/methodology/hri_workflow.md), [study configuration](../components/habitat_risk/configs/study.json), [HRI configuration](../components/habitat_risk/configs/hri.json), and [archived grid audit](../components/habitat_risk/reports/audits/spatial_grid_summary.json). These establish the local implementation state, not external scientific validation. Literature and source evidence must accompany the subsequent measurement decisions.

## 9. Decisions awaiting evidence and their gates

| Open decision | Evidence required | Must be settled before |
|---|---|---|
| Taxonomic authority, accepted species list and trait dating | Versioned sources, name mappings and conflict review | Accepted species evidence/vulnerability release |
| Observation QC, duplicates, coordinate/date eligibility and effort interpretation | Reviewed flags, provenance and checklist availability | Accepted observation aggregation |
| Grid suitability and alternative-resolution feasibility | Coverage, positional uncertainty, source scale and ecological rationale | Final spatial interpretation; document any omitted comparison |
| Indicator set, direction, reference periods and normalisation | Ecological/source rationale and coverage audit | Adding indicators to the accepted HRI specification |
| HRI weights, classes and partial-data eligibility | Documented assumptions, minimum coverage and sensitivity plan | HRI scoring |
| Vulnerability and biodiversity-importance definitions; priority combination | Trait verification, double-counting review and decision rationale | Priority scoring |
| Operational degradation label and source | Observed outcome validity, habitat denominator and availability audit | Label generation and model fitting |
| Split geometry, dates, tuning procedure and model families/count | Eligible sample coverage, dependence assessment and agreed comparison scope | Model fitting |
| External validation evidence and sensitivity ranges | Independence review and prespecified feasible tests | Assessment evaluation |

These are measurement/implementation gates within the frozen design, not permission to change its objective or row units silently. Record each resolution with date, evidence, specification version and affected outputs. Existing configuration nulls remain unresolved until corresponding decisions are accepted; existing exploratory outputs must be checked against this baseline before reuse.

## 10. WP1 completion record

- [x] Task 1.1: objective adopted.
- [x] Task 1.2: assessment structure adopted, including provisional 5 km resolution and a 10 km comparison plan/limitation route.
- [x] Task 1.3: six research questions finalised.
- [x] Task 1.4: research design documented, with dataset row units, research purposes, validation, limitations and open evidence gates.

WP1 is complete as a research-design deliverable. Later datasets are governed by the contract register and admission rule in Section 5. This status does not declare HRI, vulnerability, priority, predictive labels, training data or trained models complete. The next work is to resolve data acceptance and measurement specifications against this document before scoring or training.

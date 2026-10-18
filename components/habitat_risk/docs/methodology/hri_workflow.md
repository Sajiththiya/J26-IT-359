# Current HRI workflow and remaining decisions

## Research objective

Assess habitat risk relevant to Sri Lankan endemic birds and provide explainable, evidence-linked conservation recommendations. Forest loss contributes potential evidence; forecasting forest loss alone does not fulfil the objective.

## What is already available

Bird records, partial species traits, source provenance, a provisional national grid and environmental summaries can be reused. Downloading the sources again is unnecessary. Old processing outputs require checks against the new HRI definitions before reuse. No HRI weights, classes or vulnerability weights have been validated.

## Lecturer-facing implementation

Use `notebooks/hri/01_bird_occurrence_cleaning_and_review.ipynb` first. Preserve original rows and show flags before making cleaning decisions. Each later notebook should show its input, transformation, reason, output preview and checks.

## Decisions to establish before HRI calculation

- Assessment unit: choose and justify cell/year, species/cell/year, or another explicit unit. Determine how endemic-bird evidence constrains assessment; an unvisited cell is not bird absence.
- Species scope: resolve taxonomy and endemic-only inclusion; retain uncertain records in review. Current observation summaries pool years and are not automatically historical predictors.
- Indicators: identify which forest condition, recent loss, fragmentation, human pressure or other signals are supported by available data and literature. Acquire missing signals where needed; do not claim they exist already.
- Risk direction: justify the relationship between each signal and habitat risk. Elevation, rainfall and temperature are not inherently higher/lower risk without ecological context.
- HRI construction: document transformations, reference periods, normalisation, weights, missing-data handling and Low/Moderate/High thresholds. Compare plausible alternatives and assess independent ecological evidence where feasible.
- Species vulnerability: decide whether it modifies HRI or appears in a separate conservation-priority calculation. Prevent double-counting and record temporal interpretation of traits.
- ML task: explicitly distinguish reproducing a formula-derived HRI from forecasting a future HRI or validating against an independent outcome. Same-time formula reconstruction is not independent ecological predictive validation.
- Model plan: reconcile the latest two-model outline (Random Forest and XGBoost plus baseline) with the earlier ten-model request. Do not silently choose either before the task definition is settled.
- Evaluation: design spatial and temporal partitions for the selected HRI task. Do not reuse the old forest-loss partitions as though they validate a different target.

## Sequence and completion evidence

1. Bird-data cleaning: visible flags, review decisions and saved drafts.
2. Endemic species verification: sourced accepted names and explicit inclusion decisions.
3. Mapping: cell membership, boundary review, dates and effort limitations.
4. Environmental preprocessing: verified indicators aligned to the assessment unit and time.
5. HRI: transparent formula, classes, sensitivity and validation evidence.
6. ML: explicit target, fair baseline comparison and defensible held-out tests.
7. SHAP and recommendations: explanations interpreted as associations, supported actions and a documented evaluation method.
8. Dashboard/report: risk, uncertainty and data gaps shown distinctly; align all claims with actual evidence.

Current completion state is documented in the active README and versioned output audits. The six notebooks under `notebooks/hri/` are the single active notebook sequence; redundant root-level notebooks have been removed.

## Preservation and code adaptation policy

Modify the retained six-notebook HRI sequence in reviewable steps and preserve original source data and useful evidence. No new download or wholesale rerun is required merely because the notebook layout was cleaned up.

Keep existing forest, weather, terrain and mapping calculations where appropriate. Add supported risk transformations and an HRI calculation only after their rationale is documented. Replace target-dependent modelling logic for the chosen HRI task when defined; renaming future_loss_fraction to HRI would be incorrect. Model selection between the latest two-model outline and earlier ten-model request remains unresolved.

## Latest cleanup

Removed active notebooks 05 and 07–14, plus their nine target-dependent scripts. Kept raw data, derived environmental/spatial evidence, species traits and reusable download/extraction utilities. Simple HRI teaching notebooks remain available. Older restoration records are historical; reports/audits/obsolete_code_removal.json records the latest action.

## Integrated preparation code now available

The active sequence covers occurrence cleaning, species verification,
environmental feature engineering, cell-year assembly, HRI input preparation,
HRI construction, and leakage-controlled split normalization for modelling.
Environmental cell-year and species-evidence tables remain separate to avoid
duplicating environmental rows.

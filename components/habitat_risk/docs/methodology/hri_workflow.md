# Current HRI workflow and remaining decisions

## Research objective

Assess habitat risk relevant to Sri Lankan endemic birds and provide explainable, evidence-linked conservation recommendations. Forest loss contributes potential evidence; forecasting forest loss alone does not fulfil the objective.

## What is already available

Bird records, partial species traits, source provenance, a provisional national grid and environmental summaries can be reused. Downloading the sources again is unnecessary. Old processing outputs require checks against the new HRI definitions before reuse. No HRI weights, classes or vulnerability weights have been validated.

## Lecturer-facing implementation

Use `notebooks/hri/01_bird_data_cleaning.ipynb` first. Its code is short and visible. Preserve original rows and show flags before making cleaning decisions. Do not hide processing inside calls to archived scripts. Each later teaching notebook should show its input, transformation, reason, output preview and checks. Do not execute processing in the background on the student's behalf.

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

Current completion state: source acquisition and exploratory preprocessing exist; the new teaching notebook and any existing user execution outputs are preserved. HRI steps 2–8 above are not declared complete. Notebooks 01–04 and 06 remain active, alongside the simple teaching notebooks. Obsolete target-dependent notebooks/scripts were removed at the user’s later request; recovery copies and previous results are retained. See the active README and removal manifest.

## Preservation and code adaptation policy

Preserve and adapt useful preparation notebooks 01–04 and 06. The user subsequently authorised removing irrelevant forest-loss modelling notebooks/scripts. Modify retained code in reviewable steps and preserve original source data and useful evidence. The simple notebooks under notebooks/hri explain the same work for teaching. No new download or wholesale rerun is required.

Keep existing forest, weather, terrain and mapping calculations where appropriate. Add supported risk transformations and an HRI calculation only after their rationale is documented. Replace target-dependent modelling logic for the chosen HRI task when defined; renaming future_loss_fraction to HRI would be incorrect. Model selection between the latest two-model outline and earlier ten-model request remains unresolved.

## Latest cleanup

Removed active notebooks 05 and 07–14, plus their nine target-dependent scripts. Kept raw data, derived environmental/spatial evidence, species traits and reusable download/extraction utilities. Simple HRI teaching notebooks remain available. Older restoration records are historical; reports/audits/obsolete_code_removal.json records the latest action.

## Integrated preparation code now available

The original notebooks 01–04 contain self-contained HRI sections: inventory, cleaning plus species verification, provenance, and grid/year integration. They are written but not executed by the assistant. Use the README execution sequence rather than running all historical cells. Notebook 04 creates separate cell/year environmental and cell/year/species evidence tables to avoid repeated environmental rows. All country cells remain represented, with coverage/occurrence flags; invalid mapping/date rows are exported for review. No HRI score or class is fabricated.

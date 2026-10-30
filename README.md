# AI-Powered Conservation Intelligence for Sri Lankan Endemic Birds

**Project ID:** J26-IT-359  
**Institution:** Sri Lanka Institute of Information Technology (SLIIT)  
**Degree:** B.Sc. (Hons) in Information Technology, specializing in Information Technology  
**Status:** Under development - PP1 research and implementation stage

## 1. Project Overview

This research develops an explainable, modular conservation intelligence framework for Sri Lankan endemic birds. It brings together image-based species recognition, bird-call recognition, occurrence and biodiversity prediction, and habitat risk assessment to support bird monitoring and conservation planning.

Bird photographs and audio recordings collected in rainforest environments can be difficult to interpret because of low light, motion blur, foliage, and background noise. Historical observations also provide limited information about where birds may occur at another location or time, while environmental threats are distributed across separate datasets.

The proposed framework connects these sources of evidence through four research components. It is intended to help researchers, conservation organizations, wildlife officers, and birdwatchers interpret bird observations and plan conservation activities.

## 2. Research Objective

Develop and evaluate an AI-powered conservation intelligence framework that can:

- Identify selected Sri Lankan bird species from photographs under challenging visual conditions.
- Recognize bird calls under realistic rainforest noise conditions.
- Predict potential occurrence areas and endemic-bird biodiversity patterns using historical observations and environmental data.
- Assess habitat risks, explain contributing environmental factors, and provide evidence-based conservation recommendations.

The research evaluates the individual components and their integration. Improvements over baseline models must be demonstrated through experiments rather than assumed.

## 3. Team Members and Responsibilities

| Component | Research area | Team member | Student ID |
| --- | --- | --- | --- |
| C1 | Robust Image-Based Bird Species Recognition | R. Verjith | IT23245938 |
| C2 | Noise-Robust Bioacoustic Bird Call Recognition | V. Abiththa | IT23220324 |
| C3 | AI-Based Endemic Bird Occurrence and Biodiversity Prediction | N. Sajiththiya | IT23343870 |
| C4 | Explainable Habitat Risk Assessment and Conservation Recommendations | M. Keerthihan | IT23189812 |

**Supervisor:** Ms. Sanjeevi Chandrasiri  
**Co-supervisor:** Ms. Karthiga Rajendran

## 4. Research Components

### C1 - Robust Image-Based Bird Species Recognition

**Responsible member:** R. Verjith - IT23245938

**Objective:** Identify selected bird species from photographs and evaluate recognition robustness under challenging rainforest image conditions.

**Research approach:**

- Use transfer learning with EfficientNetV2 as the primary baseline.
- Integrate the Convolutional Block Attention Module (CBAM) with EfficientNetV2 as the proposed architecture.
- Apply training augmentation for low light, motion blur, partial foliage occlusion, and complex backgrounds.
- Compare baseline and proposed models on clean and degraded images.
- Use Grad-CAM to explain image regions influencing predictions.
- Evaluate prediction confidence and communicate uncertain or poor-quality inputs.

**Expected outputs:** Predicted species, confidence score, visual explanation, and applicable image-quality or uncertainty warnings.

**Evaluation:** Accuracy, macro precision, macro recall, macro F1-score, confusion matrices, calibration, inference time, and performance changes under image degradation.

### C2 - Noise-Robust Bioacoustic Bird Call Recognition

**Responsible member:** V. Abiththa - IT23220324

**Objective:** Recognize selected endemic bird species from audio recordings containing rainforest background noise.

**Research approach:**

- Curate labeled bird-call recordings and relevant environmental noise recordings.
- Develop augmentation using rain, wind, insects, streams, and other background sounds.
- Fine-tune and compare Wav2Vec2 and Audio Spectrogram Transformer (AST) models.
- Evaluate clean, synthetic-noise, and real-noise recordings at different noise levels.
- Analyze acoustic embeddings for rare or under-represented species.
- Develop and evaluate noise-robustness information alongside species predictions.

**Expected outputs:** Predicted species, prediction confidence, and noise-robustness information, with acoustic embedding analysis as a research output.

**Evaluation:** Accuracy, precision, recall, F1-score, confusion matrices, and comparative performance under different noise conditions.

### C3 - AI-Based Endemic Bird Occurrence and Biodiversity Prediction

**Responsible member:** N. Sajiththiya - IT23343870

**Objective:** Use historical bird observations and environmental, spatial, and seasonal data to predict potential occurrence areas and endemic-bird biodiversity patterns.

**Research approach:**

- Prepare georeferenced and dated occurrence records for selected endemic species.
- Integrate temperature, rainfall, vegetation, land cover, elevation, and other available environmental features.
- Engineer location and time features, including geographic coordinates, spatial groups, month, and season.
- Develop and compare Random Forest and XGBoost models.
- Use spatially aware validation and evaluate temporal generalization where the data support it.
- Apply SHAP or feature-importance analysis to interpret model behavior.
- Develop species occurrence maps, biodiversity maps, and location-aware candidate observation areas with distance information.

**Expected outputs:** Species occurrence prediction scores or probabilities, occurrence maps, endemic-bird biodiversity maps, and candidate observation areas for a selected species and time period.

**Evaluation:** Precision, recall, F1-score, average precision/PR-AUC, ROC-AUC where defined, and confusion matrices. Per-species results and class support should accompany aggregate metrics.

Predictions indicate where a bird may be observed; they do not guarantee a sighting. Future-period predictions depend on the availability and suitability of environmental inputs for that period. Biodiversity outputs describe the modeled species set rather than all biodiversity in an area.

### C4 - Explainable Habitat Risk Assessment and Conservation Recommendations

**Responsible member:** M. Keerthihan - IT23189812

**Objective:** Assess habitat threats at bird-relevant locations and translate explained environmental risks into conservation recommendations.

**Research approach:**

- Integrate occurrence records with tree cover, forest loss, fragmentation, vegetation condition, climate, elevation, and human-pressure data.
- Develop a Habitat Risk Index (HRI) using normalized indicators and justified weights.
- Evaluate sensitivity to indicator weights and risk-category thresholds.
- Explore Random Forest and XGBoost for risk prediction where defensible historical targets can be constructed.
- Use SHAP to explain environmental contributions to model predictions.
- Generate rule- and evidence-based recommendations for restoration, connectivity improvement, buffer management, and monitoring.

**Expected outputs:** Integrated environmental-risk data, habitat-risk scores or categories, risk maps, explanations of major risk drivers, and conservation recommendations.

**Evaluation:** Spatial validation, temporal validation where applicable, suitable classification or regression metrics, HRI sensitivity analysis, and literature- or expert-supported review of risk indicators and recommendations.

HRI-based assessment and machine-learning risk prediction are distinct outputs. Future-risk prediction requires suitable historical targets and temporal evaluation; learning a same-time index formula alone does not establish forecasting ability.

## 5. Proposed System Integration

The framework is designed around four cooperating modules:

| Module | Main input | Main contribution |
| --- | --- | --- |
| C1 | Bird photograph | Visual species identification and explanation |
| C2 | Bird-call recording | Acoustic species identification and noise-robustness information |
| C3 | Historical observations, location, time, and environmental features | Occurrence and biodiversity predictions with spatial outputs |
| C4 | Occurrence context and environmental risk indicators | Habitat-risk assessment, explanations, and recommendations |

C1 and C2 provide complementary identification evidence. C3 uses historical observations and environmental data and does not require a new photograph or audio recording for every prediction. C4 provides the environmental threat and conservation-action layer.

Integration will use consistent species identifiers, geographic coordinates, timestamps, and documented data formats. New identification results must be verified and supplied with appropriate observation metadata before they are considered for prediction datasets.

## 6. Datasets and Data Management

The sources below are identified in the project research design. Actual downloaded versions, species coverage, licenses, and preprocessing decisions must be recorded by each component.

| Component | Data | Sources identified in the research design |
| --- | --- | --- |
| C1 | Labeled bird photographs | iNaturalist, GBIF, Birds 525 Species dataset, and curated Sri Lankan bird images |
| C2 | Bird-call and environmental noise recordings | Xeno-Canto, field recordings, and suitable eBird/BirdCLEF material where available |
| C3 | Historical bird occurrences and environmental features | eBird, GBIF, WorldClim/weather data, MODIS vegetation/land-cover data, and SRTM/DEM elevation |
| C4 | Occurrence records and environmental risk layers | eBird, GBIF, Hansen Global Forest Change, climate/weather data, Human Footprint, vegetation data, and SRTM/DEM |

### Initial C1 Species Folders

The initial C1 setup contains the following ten species folders. This is the initial image-recognition scope, not a shared species count for every component.

1. `Ashy-headed_Laughingthrush`
2. `Chestnut-backed_Owlet`
3. `Green-billed_Coucal`
4. `Spot-winged_Thrush`
5. `Sri_Lanka_Blue_Magpie`
6. `Sri_Lanka_Frogmouth`
7. `Sri_Lanka_Hanging_Parrot`
8. `Sri_Lanka_Junglefowl`
9. `Sri_Lanka_Spurfowl`
10. `Yellow-fronted_Barbet`

Final labels, scientific names, and endemic-species eligibility must be verified before training. Each component should maintain its own documented species list and a shared identifier mapping for integration.

### Data Handling

- Keep raw datasets and large generated artifacts outside ordinary Git commits; document their approved storage locations and access steps.
- Retain source attribution, dataset versions, licenses, and permission records.
- Audit duplicate records, species labels, geographic coordinates, timestamps, and missing values.
- Separate training, validation, and test data before fitting preprocessing or augmentation pipelines.
- Group related images, recordings, or spatial observations appropriately to reduce leakage.
- Distinguish confirmed detections, verified non-detections, and unknown occurrence labels. An absent record alone is not a confirmed absence.
- Handle sensitive species-location information according to data-provider terms and project guidance.

## 7. Technology Stack

The stack includes selected and planned technologies; it does not imply that every integration is complete.

| Area | Technologies |
| --- | --- |
| Core development | Python, VS Code, Google Colab, Git, GitHub |
| Image recognition | PyTorch, torchvision, EfficientNetV2, CBAM, OpenCV, Grad-CAM |
| Audio recognition | Wav2Vec2, AST, Librosa, audio preprocessing and augmentation |
| Tabular machine learning | scikit-learn, Random Forest, XGBoost |
| Data preparation | Pandas, GeoPandas |
| Explainability | Grad-CAM, SHAP, feature-importance analysis |
| Geospatial analysis and maps | QGIS, GIS tools, Folium/Leaflet |
| Inference services | FastAPI planned for inference API development |

Exact dependencies and tested versions should be maintained in the relevant requirements or environment files.

## 8. Repository Organization

The following is the proposed organization for the shared repository. Only the C1 component path and branch were specified in the initial repository description; the other paths below are recommended conventions to align with the actual repository during integration.

```text
J26-IT-359/
|-- README.md
|-- .gitignore
|-- requirements.txt
|-- components/
|   |-- c1-bird-recognition/
|   |-- c2-bird-call-recognition/
|   |-- c3-bird-occurrence/
|   `-- c4-habitat-risk/
`-- docs/
```

Each component should maintain its own `README.md`, configurations, notebooks, source code, appropriate tests, and artifact-access instructions. Local data and artifact directories should follow the repository's `.gitignore` policy.

The root README describes the complete research project. Component READMEs should provide the exact setup, preprocessing, training, evaluation, and inference commands for that component.

## 9. Development Workflow

1. Develop each component on a dedicated feature branch.
2. Keep component-specific code inside its component directory.
3. Commit changes with clear messages describing the work performed.
4. Open a pull request for review before merging into the shared integration branch.
5. Review root-level dependencies, shared schemas, and integration changes with the team.
6. Update component documentation and the main README when behavior or project status changes.

**Existing C1 development branch:** `feature/c1-bird-recognition`

Branches for C2, C3, and C4 should be recorded once agreed by the team. API keys, credentials, raw datasets, and large model checkpoints must not be committed to ordinary Git history.

## 10. Setup and Execution

The repository is under active development. There is no verified single command for running the complete integrated system in the supplied documentation.

For each component:

1. Obtain the repository and switch to the relevant development branch.
2. Read the component README and create its documented Python environment.
3. Install the component's tested dependency versions.
4. Obtain the permitted datasets from the documented source or approved project storage.
5. Run preprocessing, training, and evaluation in the documented order.
6. Load the selected model and its matching preprocessing artifacts for inference.

Component owners should add exact runnable commands as implementation is verified. GPU requirements for image and audio training should be documented separately from inference requirements.

## 11. Evaluation and Reproducibility

Each component should record:

- Dataset versions, source access dates, species labels, and label mappings.
- Cleaning rules, feature definitions, augmentation settings, and preprocessing artifacts.
- Training, validation, and test split definitions, including spatial or recording groups.
- Random seeds, model configurations, dependency versions, and computing resources.
- Baseline comparisons, experiment identifiers, selected thresholds, and evaluation metrics.
- Model checkpoints or access instructions and the code version used to generate results.
- Limitations, rare-species performance, and conditions under which predictions are uncertain.

Select models and thresholds using training/validation data, then report final performance on held-out test data. Report measured results with their dataset split and experiment configuration. Accuracy, F1-score, and average precision are different metrics and should be labeled separately.

## 12. Implementation Roadmap

1. Audit datasets, verify species labels, and document source permissions.
2. Prepare component datasets and leakage-aware evaluation splits.
3. Develop baseline image, audio, occurrence, and habitat-assessment pipelines.
4. Train and evaluate proposed methods against the baselines.
5. Add confidence analysis, explanations, and spatial outputs.
6. Develop inference interfaces and agree on shared integration formats.
7. Integrate the components into the conservation intelligence prototype.
8. Perform component testing, integration testing, and stakeholder review.
9. Document results, limitations, deployment steps, and research findings.

## 13. Project Status

**Under development.** This README describes the four-component research scope and intended implementation. It does not certify completion of every listed feature or model experiment.

Each component owner should maintain current implementation progress, verified results, and execution instructions in their component README. Final model comparisons, integrated deployment instructions, and validated performance summaries will be added as they become available.

## 14. Research Use and Attribution

This repository supports an undergraduate research project. Predictions, habitat-risk estimates, and recommendations are decision-support outputs that require interpretation in their data and ecological context.

Third-party datasets, pretrained models, and software remain subject to their respective licenses and terms. A repository license should be added only after the team agrees on an appropriate license and checks applicable university requirements.

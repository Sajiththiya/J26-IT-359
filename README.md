# AI-Powered Conservation Intelligence for Sri Lankan Endemic Birds

**Project ID:** J26-IT-359  
**Institution:** Sri Lanka Institute of Information Technology (SLIIT)  
**Degree:** B.Sc. (Hons) in Information Technology, specializing in Information Technology  
**Status:** Under development

## Project Overview

This research project aims to support the conservation of Sri Lankan endemic birds through image-based species recognition, bird-call recognition, occurrence and biodiversity prediction, and habitat risk assessment. It combines bird observations and environmental data to help researchers, wildlife officers, and conservation groups identify birds, locate potential observation areas, and understand habitat threats.

## Research Objectives

- Identify selected bird species from photographs taken in challenging rainforest conditions.
- Recognize bird calls in recordings affected by environmental noise.
- Predict potential bird occurrence areas and biodiversity patterns using historical observations and environmental data.
- Assess habitat pressure, explain important risk factors, and suggest conservation options for expert review.
- Evaluate the individual components and their integration into a shared system.

## Research Team

| Component | Member | Student ID |
| --- | --- | --- |
| C1 - Image-Based Bird Species Recognition | R. Verjith | IT23245938 |
| C2 - Noise-Robust Bioacoustic Bird Call Recognition | V. Abiththa | IT23220324 |
| C3 - Bird Occurrence and Biodiversity Prediction | N. Sajiththiya | IT23343870 |
| C4 - Habitat Risk Assessment and Conservation Recommendations | M. Keerthihan | IT23189812 |

**Supervisor:** Ms. Sanjeevi Chandrasiri  
**Co-supervisor:** Ms. Karthiga Rajendran

## Research Components

### Component 01 - Image-Based Bird Species Recognition

This component focuses on identifying selected bird species from photographs taken under challenging conditions, including low light, motion blur, and partial cover from leaves. The research compares EfficientNetV2 with EfficientNetV2 + CBAM and uses Grad-CAM to explain the image regions that influence predictions. Planned outputs include the predicted species, a confidence score, and a visual explanation.

[Component 01 README](https://github.com/Sajiththiya/J26-IT-359/blob/feature/c1-bird-recognition/components/c1-bird-recognition/README.md) | [Development branch](https://github.com/Sajiththiya/J26-IT-359/tree/feature/c1-bird-recognition)

### Component 02 - Noise-Robust Bioacoustic Bird Call Recognition

This component focuses on recognizing selected endemic bird species from audio recordings containing rainforest sounds such as rain, wind, insects, and streams. The research plans to compare Wav2Vec2 and Audio Spectrogram Transformer (AST) under different noise conditions. Planned outputs include species predictions and information about prediction reliability in noisy recordings.

[Component 02 README](https://github.com/Sajiththiya/J26-IT-359/blob/abiththa-audio-classification/components/audio_classification/README.md) | [Development branch](https://github.com/Sajiththiya/J26-IT-359/tree/abiththa-audio-classification)

### Component 03 - Bird Occurrence and Biodiversity Prediction

This component uses historical bird observations together with location, seasonal, and environmental data to predict potential occurrence areas for selected Sri Lankan endemic birds. The research includes model development and comparison, with Random Forest and XGBoost among the proposed approaches. Planned outputs include occurrence maps, biodiversity summaries for the modeled species, and candidate observation areas with distance information. Predictions indicate possible sightings and do not guarantee that a bird will be present.

[View Component 03 - Occurrence Prediction](https://github.com/Sajiththiya/J26-IT-359/tree/sajiththiya-occurrence-prediction)

### Component 04 - Habitat Risk Assessment and Conservation Recommendations

This component combines bird observations with environmental measurements to assess habitat pressure across Sri Lanka. Its research includes a Habitat Risk Index (HRI), analysis of possible changes in risk, model explanations, and conservation options for expert review. Existing preparation work and modelling experiments require further review of data coverage, indicators, and validation before final national results are reported.

[Component 04 README](https://github.com/Sajiththiya/J26-IT-359/blob/Risk-Assessment/components/habitat_risk/README.md) | [Development branch](https://github.com/Sajiththiya/J26-IT-359/tree/Risk-Assessment)

## Planned System Outputs

| Component | Input | Expected output |
| --- | --- | --- |
| C1 | Bird photograph | Species prediction, confidence score, and image explanation |
| C2 | Bird-call recording | Species prediction and noise-related reliability information |
| C3 | Historical observations, location, time, and environmental features | Occurrence maps, biodiversity summaries, and candidate observation areas |
| C4 | Bird records and environmental measurements | Habitat risk scores, maps, explanations, and conservation options |

The components address related research questions but do not require every input for every task. For example, C3 can use its prepared dataset without a new photo or audio recording. Shared species identifiers, coordinates, and dates will support integration where appropriate.

## Data Sources and Management

| Component | Data sources identified in the research design |
| --- | --- |
| C1 | iNaturalist, GBIF, Birds 525 Species dataset, and curated bird images |
| C2 | Xeno-Canto and field recordings, with suitable eBird or BirdCLEF material where available |
| C3 | eBird, GBIF, weather and climate data, vegetation and land-cover data, and elevation data |
| C4 | Bird observations, Hansen Global Forest Change, weather, terrain, vegetation, and available human-pressure data |

Each component documents the sources, versions, permissions, species coverage, and preparation steps actually used. Species coverage may differ between components. Data checks include duplicate records, uncertain labels, missing values, geographic coordinates, and observation dates.

Raw datasets and large model files are stored separately where required. Source licenses and access conditions apply to all shared data. A missing bird record is not automatically treated as a confirmed absence.

## Evaluation and Reproducibility

The research compares proposed methods with suitable baselines and reports results on separate evaluation data.

| Component | Main evaluation focus |
| --- | --- |
| C1 | Accuracy, macro precision, macro recall, macro F1-score, confidence calibration, and performance on clear and degraded images |
| C2 | Accuracy, precision, recall, F1-score, and performance across clean and noisy recordings |
| C3 | Precision, recall, F1-score, average precision, per-species results, and performance across separate geographic areas |
| C4 | HRI indicator and weight review, sensitivity analysis, and appropriate spatial and temporal evaluation of risk models |

Data preparation is fitted on training data, with related observations grouped appropriately to reduce leakage. Models and decision thresholds are selected using training and validation data; final test data are kept separate for evaluation. Temporal prediction claims require evaluation that supports the stated prediction period.

Experiments record dataset versions, split definitions, random seeds, model settings, package versions, and preprocessing files. Results are reported with their metric names and limitations, including low support for rare species.

## Main Technologies

| Area | Selected or planned technologies |
| --- | --- |
| Development and data preparation | Python, Jupyter Notebooks, Pandas, GeoPandas, VS Code, Google Colab |
| Image recognition | PyTorch, torchvision, EfficientNetV2, CBAM, OpenCV |
| Audio recognition | Wav2Vec2, AST, Librosa |
| Occurrence and habitat modelling | scikit-learn, Random Forest, XGBoost |
| Model explanations | Grad-CAM, SHAP |
| Spatial analysis and maps | QGIS, Folium/Leaflet |
| Prediction API | FastAPI, planned |
| Version control | Git and GitHub |

## Repository Structure

The project uses the following component folders. Their contents may differ between `main` and the development branches.

```text
J26-IT-359/
├── README.md
└── components/
    ├── c1-bird-recognition/       # C1: Image-based species recognition
    │   └── README.md
    ├── audio_classification/     # C2: Bird-call recognition
    │   └── README.md
    ├── occurrence_prediction/    # C3: Occurrence and biodiversity prediction
    └── habitat_risk/             # C4: Habitat risk and conservation recommendations
        └── README.md
```

Each component keeps its own code, notebooks, configuration files, and documentation. Detailed folder structures are described in the component READMEs. Component 03 documentation and available files can be accessed through its development-branch link above.

## Documentation and Setup

Each component maintains its own documentation for datasets, dependencies, methods, execution steps, results, and limitations. Follow the component links above for details. Development branches may include work that has not yet been merged into `main`.

Raw datasets, large model files, generated outputs, and virtual environments may be stored separately from the repository. Refer to the relevant component documentation for data access and environment setup.

## Development Workflow

Each member develops their component on its own branch. Changes are reviewed through pull requests before they are merged into `main`. Shared dependencies, data formats, and integration changes are coordinated across the team.

The main README provides the project overview. Individual component READMEs contain detailed methods, setup instructions, progress, and results. API keys, credentials, local environments, and large datasets are excluded from normal Git commits.

## Project Status

The project is under development. Data preparation, model experiments, and system integration are at different stages across the four components. Features described as planned are research goals rather than completed functionality. Verified progress and evaluation results are documented with the relevant component work.

## Research Use

This repository supports an undergraduate research project. Predictions and recommendations are intended to assist bird observation planning and conservation decisions. Third-party datasets, pretrained models, and software remain subject to their respective licenses and terms.

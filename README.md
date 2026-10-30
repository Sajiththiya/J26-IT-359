# Bird Occurrence and Biodiversity Prediction for Sri Lankan Endemic Birds

**Project ID:** J26-IT-359  
**Component:** C3 - AI-Based Endemic Bird Occurrence and Biodiversity Prediction  
**Researcher:** N. Sajiththiya - IT23343870  
**Development branch:** `sajiththiya-occurrence-prediction`  
**Component folder:** `components/occurrence_prediction/`  
**Status:** Under development

## About This Component

Historical bird records show where and when a species was observed. This component uses those records together with environmental, spatial, and seasonal information to study where selected Sri Lankan endemic birds may be found.

The research aims to develop occurrence predictions, maps of the selected species, and biodiversity summaries. A planned location-based feature will suggest possible observation areas and show their distance from a selected location. These outputs are intended to support bird observation planning, biodiversity monitoring, and conservation research.

The preparation workflow described here contains two notebooks and an existing verified occurrence dataset. Model training, final evaluation, and application development are separate stages. Running the preparation notebooks does not produce a completed prediction model or web application.

## Research Question and Study Area

The main research question is: **how well can historical observations and environmental data predict the occurrence of selected endemic birds in Sri Lanka?**

The research considers location, time, season, and available environmental measurements. Random Forest and XGBoost are included in the model comparison planned for the component.

Predictions indicate where a bird may be observed; they cannot guarantee a sighting. Future-period predictions require suitable inputs for that period and an evaluation that supports the intended forecast. Biodiversity summaries cover the species included in the models rather than all biodiversity in an area.

## Data Needed

| Data | Purpose | Preparation |
| --- | --- | --- |
| Bird observation records | Provide species, coordinates, dates, and detection evidence. | Check labels, missing values, duplicate records, and geographic validity. |
| Checklist and effort information | Help interpret detections and suitable non-detections. | Preserve checklist identifiers and review observation effort. |
| Weather measurements | Describe environmental conditions associated with observations. | Check that locations and dates match the observation records. |
| Forest and other environmental features | Describe habitat conditions and changes before observation. | Verify source coverage and forest-loss timing. |
| Species scope and metadata | Define the birds included in the research and preserve source history. | Keep species mappings, summaries, and verification evidence. |
| Spatial split mappings | Separate training and evaluation observations by the accepted spatial design. | Recover and verify the existing mapping for the V2 workflow. |

The existing input dataset contains verified binary targets and features. A missing observation alone is not evidence that a bird was absent. Confirmed detections, verified suitable non-detections, and unknown records need to remain distinguishable during target preparation.

## Research Workflow

### 1. Understand and Review the Data

The first notebook, [`01_Data_Understanding_EDA.ipynb`](Notebooks/01_Data_Understanding_EDA.ipynb), reads the prepared occurrence training dataset. It supports data inspection, cleaning, and exploratory analysis before the next preparation stage.

### 2. Prepare Added Environmental Features

The V2 script, `scripts/data/build_preprocessing_v2.py`, creates a separate preprocessing release. It checks that added checklist-level features are consistent within each checklist and validates forest-loss timing against local Hansen raster files.

It also recovers and verifies the existing spatial split. Existing target releases, preprocessing files, split files, and model results are preserved.

### 3. Prepare Model Inputs and Data Splits

The second notebook, [`02_Normalization_Train_Test_Split.ipynb`](Notebooks/02_Normalization_Train_Test_Split.ipynb), follows notebook 01. In the V2 workflow, both notebooks use the V2 outputs, and notebook 02 reads the recovered split mapping rather than generating a new split.

Preprocessing is fitted on training rows only. The saved preprocessor and feature list allow the same transformations to be applied to validation, test, and later prediction inputs.

### 4. Train and Evaluate Models

Model training follows data preparation as a separate stage. The research design includes comparing Random Forest and XGBoost, with further model experiments documented alongside their own inputs and results.

Models and decision thresholds are selected using training and validation data. Final test data remain separate until evaluation. Results should include precision, recall, F1-score, average precision, confusion matrices, and ROC-AUC where it can be calculated. Per-species results and sample counts are needed to show how performance varies between common and rare species.

### 5. Develop Maps and Prediction Outputs

The planned mapping stage uses validated model outputs to show potential occurrence areas and biodiversity patterns for the selected species. SHAP or feature-importance analysis will support interpretation of the predictions. Map outputs need to identify the species, period, and relevant limitations.

## Expected Outputs

1. A cleaned and documented occurrence dataset.
2. Prepared training, validation, and test data.
3. Saved spatial split mappings, feature names, and fitted preprocessing files.
4. Model comparison and per-species evaluation results.
5. Species occurrence maps and biodiversity summaries for the modeled species.
6. Candidate observation areas and distance information in the planned application.

The preparation scripts produce the data and supporting reports needed for later experiments. Prediction maps and application features require additional implementation and validation.

## Running the Preparation Notebooks on Windows

### Create the Environment

Install Python 3.13. From the repository root, run:

```powershell
cd components/occurrence_prediction
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Where present, `requirements-lock.txt` records the exact installed versions used for validation and can be used instead of `requirements.txt`.

### Run the Notebooks

From the component folder, run:

```powershell
.\.venv\Scripts\python.exe scripts/run_notebooks.py
```

The runner executes notebook 01 followed by notebook 02. Executed copies are saved in `reports/executed_notebooks/`.

Preparation outputs include the cleaned dataset and training, validation, and test CSVs. Timestamped output folders allow separate notebook runs to preserve earlier exports and reduce file-lock conflicts when CSVs are open in another application. In V2, the split assignments come from the recovered mapping.

### Open JupyterLab

For interactive use, run:

```powershell
.\.venv\Scripts\python.exe -m jupyterlab
```

In VS Code, open a notebook and choose **Select Kernel > Python Environments**. Select this component's `.venv/Scripts/python.exe`. Run notebook 01 before notebook 02.

## Versioned Preprocessing With Added Environmental Features

After installing the dependencies, run the following from the component folder:

```powershell
.\.venv\Scripts\python.exe scripts/data/build_preprocessing_v2.py
```

The script creates:

```text
data/processed/occurrence/targets_v1/preprocessing_v2/
```

Its main outputs include:

- Joined and cleaned labeled tables.
- `row_split_mapping.csv` and `survey_split_mapping.csv`.
- `feature_names.json` and `preprocessor.joblib`.
- Feature-redundancy and join reports.
- Prepared training, validation, and test files under `splits/`.

The command requires its source data and local Hansen rasters. It does not train models or perform final test evaluation.

## Validation

Run the component tests and dependency checks from the component folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

These checks cover software and dependency consistency. Research model performance is assessed separately using the accepted evaluation design.

## Data and Output Locations

| Path within this component | Contents |
| --- | --- |
| `data/processed/occurrence/targets_v1/occurrence_training_dataset.csv` | Existing verified targets and features required by notebook 01. |
| `data/processed/occurrence/targets_v1/preprocessing/` | Cleaned data and exploratory-analysis summaries. |
| `data/processed/occurrence/targets_v1/preprocessing_v2/` | V2 preprocessing release and supporting reports. |
| `data/splits/occurrence/targets_v1/spatial/joint_minmax_seed42_effort/run_*/` | Timestamped split exports from the documented spatial preparation workflow. |
| `data/interim/occurrence/targets_v1/` | Target-verification evidence used by regression tests. |
| `data/metadata/occurrence/targets_v1/` | Species scope, dataset summaries, and source history. |
| `reports/executed_notebooks/` | Executed copies of the preparation notebooks. |

## Repository Structure

```text
occurrence_prediction/
├── README.md
├── requirements.txt
├── requirements-lock.txt          # Where available
├── Notebooks/
│   ├── 01_Data_Understanding_EDA.ipynb
│   └── 02_Normalization_Train_Test_Split.ipynb
├── scripts/
│   ├── run_notebooks.py
│   └── data/
│       ├── build_preprocessing_v2.py
│       └── build_occurrence_targets.py
├── data/
│   ├── processed/
│   ├── interim/
│   ├── metadata/
│   └── splits/
├── reports/
│   └── executed_notebooks/
└── tests/
```

This structure describes the preparation workflow. Additional model experiments are documented separately as they are added to the component.

## Current Status and Next Steps

The component includes an existing verified occurrence dataset, preparation notebooks, a notebook runner, and versioned environmental preprocessing. This document covers their setup and intended use; it does not report a final deployed model or completed application.

The next stages are to review preparation outputs, document model experiments and their results, complete prediction and mapping features, and integrate the component with the wider conservation system.

## Data Access and Reproducibility

Raw, intermediate, and processed datasets, model artifacts, the virtual environment, and executed notebook copies are excluded from normal Git tracking. A fresh clone therefore requires the relevant local datasets before the preparation workflow can run.

The optional `scripts/data/build_occurrence_targets.py` script rebuilds targets from the original eBird export and species-scope inputs. Some of those inputs are not included in the copied component. Rebuilding targets is separate from running the two preparation notebooks with the existing verified dataset.

Dataset versions, source permissions, feature definitions, split mappings, random seeds, and dependency versions should be recorded with each experiment. Preserve the local data when transferring the project between computers and follow the original providers' licenses and access conditions.

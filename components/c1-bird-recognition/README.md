
# AI-Powered Conservation Intelligence for Sri Lankan Birds

## Project Information

- Project ID: J26-IT-359
- Component: C1 — Image-Based Species Recognition
- Development Branch: feature/c1-bird-recognition
- Status: Under Development

## 1. Overview

This repository contains research and implementation work for an AI-powered bird conservation system.

Component 1 focuses on identifying Sri Lankan bird species from photographs, particularly under challenging environmental conditions.

## 2. C1 Research Objective

Develop and evaluate a bird species recognition model using:

- EfficientNetV2 as the baseline architecture
- EfficientNetV2 + Convolutional Block Attention Module (CBAM) as the proposed architecture
- Transfer learning
- Image preprocessing and data augmentation
- Robustness evaluation
- Grad-CAM explainability
- Confidence-aware prediction

The research will compare the baseline and proposed models to determine whether CBAM improves bird species recognition under challenging image conditions.

## 3. Dataset

The initial dataset contains images organized into 10 species folders:

1. Ashy-headed_Laughingthrush
2. Chestnut-backed_Owlet
3. Green-billed_Coucal
4. Spot-winged_Thrush
5. Sri_Lanka_Blue_Magpie
6. Sri_Lanka_Frogmouth
7. Sri_Lanka_Hanging_Parrot
8. Sri_Lanka_Junglefowl
9. Sri_Lanka_Spurfowl
10. Yellow-fronted_Barbet

Dataset auditing, label verification and train/validation/test splitting will be performed before training.

Raw datasets are excluded from Git.

## 4. Technology Stack

- Python
- PyTorch
- torchvision
- OpenCV
- scikit-learn
- Google Colab
- VS Code
- Git and GitHub
- FastAPI (planned inference API)

## 5. Repository Structure

```text
J26-IT-359/
├── .gitignore
├── README.md
├── requirements.txt
└── components/
    └── c1-bird-recognition/
        ├── configs/
        ├── data/
        ├── notebooks/
        ├── src/
        ├── tests/
        └── artifacts/
```

## 6. Planned Implementation

1. Dataset inspection and validation
2. Dataset preprocessing and splitting
3. Training augmentation
4. EfficientNetV2 baseline training
5. CBAM integration and proposed model training
6. Model evaluation and comparison
7. Grad-CAM and confidence analysis
8. Prediction API development
9. System integration and testing
10. Research documentation

## 7. Development Workflow

C1 development takes place on:

`feature/c1-bird-recognition`

Component implementation files will remain under:

`components/c1-bird-recognition/`

Changes to shared root-level files must be reviewed before integration with other components.

## 8. Reproducibility

The implementation will document:

- Dataset versions and species labels
- Training and validation splits
- Random seeds
- Model configurations
- Library dependencies
- Experiment results
- Model checkpoints and evaluation metrics

## 9. Project Status

Initial development setup is in progress.

Training results, performance metrics and model deployment instructions will be added after implementation and testing.

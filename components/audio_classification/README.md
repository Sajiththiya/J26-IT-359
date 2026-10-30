# Noise-Robust Bioacoustic Bird Call Recognition for Sri Lankan Endemic Birds

## About this project

Sri Lanka has endemic birds whose calls can help researchers and conservation practitioners identify species without needing to see them. However, real recordings often contain rain, insects, flowing water, wind, forest ambience, and calls from other birds. These sounds can make automatic recognition difficult, especially when recordings are limited or classes are imbalanced.

**Component 02** of the *AI-Powered Conservation Intelligence for Sri Lankan Endemic Birds* research project (J26-IT-359) investigates whether pretrained audio transformers can recognize ten selected bird species from short recordings, and how their performance changes under environmental noise.

The component combines an auditable audio-preparation pipeline, recording-group-aware dataset splits, training-only noise augmentation, transformer fine-tuning, model evaluation, and a web application for uploading audio and viewing predictions. **Noise robustness remains a research objective, not a demonstrated conclusion, until held-out noisy evaluations are completed.**

This README describes the intended research workflow and the code and results currently reported in `components/audio_classification/`. It distinguishes implemented work from experiments that still require evaluation.

## The research question and scope

**Research question:** How effectively can pretrained audio transformers identify selected Sri Lankan endemic bird calls in recordings affected by environmental noise, and how does performance vary across species and noise conditions?

The current classifier is a **closed-set, ten-class** system. It predicts among the ten supported classes; it does not establish that an uploaded recording actually contains one of those species. A prediction score is a model output, not proof of species presence or a measure of population abundance.

### Selected species

| Species 
| --- | ---: |
| Chestnut-backed Owlet 
| Crimson-fronted Barbet 
| Green-billed Coucal 
| Spot-winged Thrush 
| Sri Lanka Blue Magpie 
| Sri Lanka Frogmouth 
| Sri Lanka Grey Hornbill 
| Sri Lanka Junglefowl 
| Sri Lanka Spurfowl 
| Yellow-fronted Barbet 



## Data needed

The dataset includes original bird recordings, metadata, and environmental-noise recordings. The project has used bird audio from documented collection efforts involving **eBird, Xeno-canto, and external-supervisor-provided material**. Exact provenance, reuse permissions, and the association of each file with a provider should be verified against the source records before public redistribution.

| Data | Why it matters | Position in this component |
| --- | --- | --- |
| Original bird recordings | Provide the species-labeled audio examples | `birds_audio/` |
| Recording metadata | Links clips to species and original recordings | Dataset CSVs and preparation reports |
| Prepared five-second clips | Standardize model inputs | `birds_audio_prepared/` |
| Group-aware train/validation/test partitions | Reduce leakage between evaluation partitions | `birds_audio_split/` |
| Environmental noise | Supports controlled training augmentation | `Noisy/` |
| Augmented training examples | Expose the model to different noise levels | `birds_audio_augmented/` |
| Portable training package | Supports Colab or another training environment | `colab_training_package/` and `colab_training_package.zip` |

### Environmental noise categories

Six categories are included: **forest ambient sound, insects, mixed calls from other birds, rain, flowing streams, and wind**. Synthetic mixtures are created at nominal **20 dB (light), 10 dB (medium), and 0 dB (heavy) signal-to-noise ratios (SNR)**. These labels describe intended augmentation levels; achieved SNR and quality flags must be checked in the augmentation report.

## How the research workflow fits together

### 1. Collect, label, and audit the recordings

Recordings are organized into species folders and checked for supported audio formats, readable content, duration, label consistency, and recording relationships. Metadata tracks the source recording so that segmented clips can be associated with their parent. Uncertain acoustic matches and incomplete provenance are documented rather than silently treated as independent field recordings.

Useful scripts include `src/audit_dataset.py`, `src/review_data_quality.py`, and `src/check_recording_similarity.py`. Audit outputs are under `reports/`.

### 2. Standardize and segment the audio

The preparation pipeline converts inputs into a consistent format:

- **16,000 Hz** sample rate
- **Mono** (one audio channel)
- **16-bit PCM WAV**
- **Five-second clips** (80,000 samples each)

Shorter trailing segments may be padded to the target duration. Silence, heavy padding, clipping, and other quality concerns should be reviewed; fixed-length segmentation can also cut through longer calls or retain recordings with little useful vocalization.

The prepared dataset has **9,233 five-second clips**. See `src/prepare_audio.py` and `reports/audio_preprocessing/` for implementation and audit details.

### 3. Create recording-group-aware partitions

The current split was made using parent-recording and acoustic-similarity grouping rather than randomly splitting individual clips. This reduces the risk that near-identical examples appear in both training and evaluation partitions.

| Partition | Original recordings | Five-second clips |
| --- | ---: | ---: |
| Training | 755 | 7,384 |
| Validation | 94 | 925 |
| Test | 96 | 924 |
| **Total** | **945** | **9,233** |

The intended proportion is approximately **80% training, 10% validation, and 10% testing**. These are grouped partitions, **not a guarantee of independence at the field-recording or recording-session level**, because source provenance is incomplete. The split report also records unresolved cross-species similarity cases that require manual review.

Relevant code: `src/review_dataset_split.py`, `src/finalize_dataset_split.py`. Report: `reports/final_dataset_split/final_dataset_split_report.md`.

### 4. Augment only the training partition

Training clips are combined with selected environmental-noise recordings at different target SNRs. The original validation and test sets remain separate from this augmentation. This separation prevents the same augmented training examples from being used to select or evaluate a model.

The augmented training layout includes `clean/`, `light_noise/`, `medium_noise/`, and `heavy_noise/`. **The `clean/` folders may contain `references.csv` rather than duplicate WAV files.** Data loaders must resolve these references to the original clean training clips, or use the supplied manifest. Simply scanning the augmented folders for WAVs would miss clean training examples.

Review `reports/noise_augmentation/noise_augmentation_report.md` for actual SNR deviations, exclusions, and quality warnings. Using the same small collection of noise recordings for both augmentation and a later noisy test would not demonstrate generalization to independent noise sources.

### 5. Fine-tune pretrained audio transformers

Two model families are in scope:

| Model | Input representation | Role |
| --- | --- | --- |
| **Wav2Vec2** (`facebook/wav2vec2-base`) | Audio waveform | Main trained classifier with saved validation results |
| **Audio Spectrogram Transformer (AST)** (`MIT/ast-finetuned-audioset-10-10-0.4593`) | Spectrogram-derived filter-bank features | Comparison architecture; full comparable evaluation not yet established |

Both models require a new ten-class classification head and task-specific fine-tuning. Their respective feature extractors must be used correctly; the same raw-waveform preprocessing cannot be assumed to work identically for both architectures.

The training notebooks are located in `notebooks/`, including `train_wav2vec2_colab.ipynb` and `train_ast_colab.ipynb`. CPU-specific notebook variants may also be present in a local checkout. Hyperparameter search uses Optuna; training and validation outputs should be retained alongside the exact model, dataset, and software configuration.

**Training-only tuning scores are not final test scores.** A CPU smoke test using a small subset is a pipeline check, not a valid comparison with a fully trained model.

### 6. Validate, test, and measure robustness

The model-development process uses training data to update weights and validation data to select checkpoints and examine performance. The held-out test partition should be evaluated **only after model selection**. Useful metrics include:

- **Macro F1:** gives each species equal weight in the average.
- **Accuracy:** fraction of evaluated clips predicted correctly.
- **Per-species precision and recall:** reveal which birds are confused or missed.
- **Confusion matrix:** shows the pattern of class errors.
- **Clean-versus-noisy performance:** compares results at controlled noise levels, ideally using independent noise sources.

The verified **Wav2Vec2 validation accuracy is 63.57%**, and **validation macro F1 is approximately 0.6349**. These values should **not** be presented as held-out test performance or proof of noise robustness. No saved final held-out test or noise-level evaluation was confirmed in the most recent integration audit.

A prior Wav2Vec2 tuning trial reached approximately **0.6597 macro F1 on a training-only selection split**. That is a different evaluation context from the reported validation result.

### 7. Serve predictions through the application

A **Next.js frontend** provides audio upload and result views. A **FastAPI backend** loads the saved Wav2Vec2 checkpoint and its matching feature extractor, processes uploaded audio, and returns class predictions.

The most recent integration verification reported successful `/health`, `/species`, and `/predict` requests, with `ready: true` and `demo_mode: false`. It also reported that a five-second Chestnut-backed Owlet validation clip was correctly predicted with an **89.49% model score**. That one result demonstrates working inference, **not overall model accuracy**.

The checkpoint used in that verification was:

```text
model_runs/wav2vec2/20261020T072702969170Z/final/best_model/
```

The checkpoint's `model.safetensors`, `config.json`, and `preprocessor_config.json` were used with the run's `label_mapping.json`. A fresh environment must have those files available before real inference will work.

## Expected outputs

A completed Component 02 should provide:

1. **A traceable audio dataset** with documented species labels, recording groups, preprocessing, and quality flags.
2. **Reproducible train/validation/test partitions** with leakage checks.
3. **Noise-augmented training data** with target and achieved SNR records.
4. **Trained transformer checkpoints** and reproducible hyperparameter and training histories.
5. **A fair model comparison** on the same held-out evaluation protocol.
6. **Clean and noisy test results**, including macro F1, per-class metrics, and confusion matrices.
7. **A functioning upload-and-predict web application** that clearly identifies its loaded model and supported classes.

## Current project status

| Work item | Status |
| --- | --- |
| Ten-class bird dataset collection and organization | Prepared |
| Standardization and five-second segmentation | Implemented |
| Group-aware train/validation/test split | Implemented; independence limitations documented |
| Training-only noise augmentation | Implemented; quality flags need review |
| Wav2Vec2 tuning and validation | Results available |
| Wav2Vec2 final checkpoint | Available and verified for inference |
| Next.js / FastAPI integration | Verified in a local end-to-end test |
| AST full comparable training | Not confirmed complete |
| Held-out test metrics | Pending / not confirmed saved |
| Independent noise-level robustness evaluation | Pending |

The project should not claim a validated improvement over AST, a CNN baseline, or clean-only training without a comparable experiment. Source provenance, recording-group uncertainty, unequal class sizes, and limited noise diversity are relevant research limitations.

## Running the web application

These commands assume **Windows PowerShell** and that VS Code is opened at the repository root (`J26-IT-359-NEW/`). The model checkpoint and Python/Node dependencies must be available locally.

### 1. Start the FastAPI backend

Open the first VS Code terminal:

```powershell
.\.venv\Scripts\Activate.ps1
cd components\audio_classification\birdcall_app\backend
.\run-model.ps1
```

Keep this terminal open. Visit **http://localhost:8000/health** and confirm the actual response reports `ready: true` and `demo_mode: false`. If the script or environment is missing, consult `birdcall_app/README.md` for setup details instead of assuming a different launch command.

### 2. Start the Next.js frontend

Open a **second** terminal from the repository root:

```powershell
cd components\audio_classification\birdcall_app\frontend
npm install
npm run dev
```

`npm install` is needed for first-time setup or when dependencies have changed; it can be skipped when `node_modules/` is already correctly installed. Open **http://localhost:3000** (or the local URL displayed by Next.js).

### 3. Test a real prediction

Upload a supported bird recording through the UI, start analysis, and check the predicted class and confidence scores. The backend must remain running while the frontend sends requests. If the frontend loads but prediction fails, check the backend terminal, `/health`, checkpoint location, and frontend API configuration.

## Running the training notebooks

Training notebooks are under `notebooks/`. They may be opened in Google Colab or a compatible local Jupyter environment. Before running a notebook:

1. Select the intended runtime and check available memory, storage, and compute limits.
2. Verify the training ZIP path, output directory, model kind, and selected dataset manifests.
3. Run setup and dataset verification cells **in order**.
4. Enable tuning or final training only when ready; avoid `Run all` until the notebook's execution switches are understood.
5. Keep model runs in separate timestamped directories and retain validation metrics, checkpoint files, and configuration.

Full AST and Wav2Vec2 training can be slow on CPU. A CPU smoke test confirms that code runs but is not a substitute for full training or scientific evaluation. The `colab_training_package.zip` file is a data package, not a trained model.

## Repository guide

| Location | Purpose |
| --- | --- |
| `birds_audio/` | Original bird audio organized by species |
| `birds_audio_prepared/` | Standardized, segmented clips |
| `birds_audio_split/` | Group-aware train/validation/test partitions |
| `birds_audio_augmented/` | Clean references and noisy training variants |
| `Noisy/` | Environmental noise source recordings |
| `src/` | Auditing, preparation, split, augmentation, and packaging scripts |
| `notebooks/` | Transformer training and evaluation notebooks |
| `reports/` | Dataset, split, preprocessing, augmentation, and quality audits |
| `model_runs/` | Saved training runs, checkpoints, and metrics |
| `colab_training_package/` | Portable training manifests and dataset layout |
| `birdcall_app/backend/` | FastAPI inference service |
| `birdcall_app/frontend/` | Next.js user interface |

Some datasets, checkpoints, and large archives may exist only on a local machine or Google Drive and may be excluded from Git. A fresh clone should not be assumed to contain every artifact needed to reproduce results or run inference.

## Interpretation and limitations

The model classifies audio **among ten supported species**. Its prediction score is not a calibrated probability unless calibration has been established. Performance on a single uploaded example cannot replace evaluation on independent recordings. Five-second clipping, class imbalance, limited original recording provenance, and limited diversity of available environmental-noise recordings can affect generalization.

When reporting a result, state the **model checkpoint, dataset split, evaluation condition (clean or noisy), metric, and known limitations** together. These details are necessary to make claims about bird call recognition and noise robustness scientifically interpretable.

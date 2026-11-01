# C1 — Sri Lankan Bird Species Recognition

**Project:** J26-IT-359 — AI-Powered Multimodal Conservation Intelligence Framework for Sri Lankan Birds  
**Component:** C1 — Image-Based Bird Species Recognition  
**Stack:** Next.js / React / TypeScript / Tailwind CSS · FastAPI · PyTorch / Torchvision · Grad-CAM

## Overview

This C1 component lets a user upload a bird photograph and compare predictions from two trained image-classification models:

- **EfficientNetV2-S baseline** — primary classifier.
- **EfficientNetV2-S + CBAM** — research comparison model with a channel-and-spatial attention module inserted after backbone feature stage 6.

The web application displays the uploaded photograph, predicted species and softmax model score from each model, plus Grad-CAM heatmaps with an adjustable overlay opacity. The classifier supports **10 selected Sri Lankan bird species**. It is a research prototype, not a general-purpose identification or conservation decision system.

## Verified functionality

- Responsive Next.js interface (desktop and mobile)
- JPG/JPEG and PNG upload, image preview, and upload validation (10 MB limit)
- Predictions from both pretrained-and-fine-tuned PyTorch checkpoints
- Original photograph and baseline/CBAM Grad-CAM heatmaps
- Heatmap opacity slider
- Friendly handling of invalid uploads

The user reported successful end-to-end browser testing of these functions. Generated or unverified bird images should be used only for demonstrations, not scientific accuracy claims.

## Repository layout

```text
J26-IT-359/
├── .venv/                                  # local Python environment (not committed)
└── components/
    └── c1-bird-recognition/
        ├── frontend/                       # Next.js app
        │   ├── src/app/page.tsx
        │   ├── src/app/layout.tsx
        │   └── package.json
        ├── backend/
        │   └── main.py                     # FastAPI app
        ├── models/                         # local trained weights (not committed)
        │   ├── baseline_best_model.pt
        │   └── cbam_best_model.pt
        ├── src/
        │   ├── bird_dataset.py
        │   ├── bird_transforms.py
        │   ├── cbam.py
        │   ├── efficientnetv2_cbam.py
        │   ├── grad_cam.py
        │   ├── train_efficientnetv2_baseline.py
        │   └── train_efficientnetv2_cbam.py
        └── data/                           # research dataset/manifests (may be local)
```

**Note:** This README documents C1, not the entire team's other components. The exact files in your checkout may include additional tests and reports.

## Requirements

- Windows PowerShell and VS Code (commands below are for Windows)
- Python **3.11** (the version used in the C1 environment)
- Node.js **22** and npm **10** (versions confirmed during development)
- Local copies of **both** trained `.pt` checkpoints
- Internet access for the initial package installation

The C1 API was tested with Python packages including FastAPI, Uvicorn, `python-multipart`, Pillow, PyTorch and Torchvision. A CUDA GPU is **not required** for local prediction; the tested local setup used CPU inference.

## 1. Get the code

Open PowerShell in the repository root:

```powershell
cd C:\Sliit_Research\J26-IT-359
```

Use your current C1 implementation branch, if applicable:

```powershell
git switch feature/c1-bird-recognition
```

If the checkout has newer work on another branch, use the branch containing `frontend/` and `backend/`; do not switch away from uncommitted work without checking `git status`.

## 2. Place the trained model files

Create this folder if necessary:

```powershell
New-Item -ItemType Directory -Force components\c1-bird-recognition\models
```

Copy your local files (downloaded from Google Drive) to:

```text
components/c1-bird-recognition/models/baseline_best_model.pt
components/c1-bird-recognition/models/cbam_best_model.pt
```

Google Drive original locations:

```text
MyDrive/C1_Bird_Recognition/runs/baseline_v1/best_model.pt
MyDrive/C1_Bird_Recognition/runs/cbam_v1/best_model.pt
```

Rename the **downloaded local copies** as above so the identically named Drive files do not overwrite each other. The previously verified checkpoint sizes were approximately **77.88 MB** (baseline) and **77.93 MB** (CBAM).

Verify local files:

```powershell
Get-ChildItem components\c1-bird-recognition\models\*.pt |
  Select-Object Name, @{Name="SizeMB";Expression={[math]::Round($_.Length / 1MB,2)}}
```

**Do not commit trained weights or the dataset.** The existing `.gitignore` included `*.pt` during development; confirm this before committing.

## 3. Set up the Python backend

From the repository root:

```powershell
cd C:\Sliit_Research\J26-IT-359
```

If you already have the project `.venv`, activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If it does not exist, create it with Python 3.11 and activate:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies (minimum packages used by this component):

```powershell
python -m pip install torch torchvision fastapi uvicorn python-multipart pillow numpy
```

**Version note:** Prefer the project's existing pinned requirements/lockfile if present. The project was verified locally with PyTorch `2.14.1+cpu`, Torchvision `0.29.1+cpu`, FastAPI `0.143.0` and Uvicorn `0.54.0`; a new installation may resolve different versions. Additional dependencies are needed only if imported by your current `backend/main.py` (for example `opencv-python` if it directly imports `cv2`).

## 4. Start the FastAPI server (Terminal 1)

Keep this terminal running:

```powershell
cd C:\Sliit_Research\J26-IT-359
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --app-dir components/c1-bird-recognition/backend --host 127.0.0.1 --port 8000
```

Check:

- **Health:** http://127.0.0.1:8000/health
- **API documentation:** http://127.0.0.1:8000/docs

The backend is expected to load the saved trained checkpoints, not download new ImageNet weights at every request. `/predict` accepts a multipart image upload; the current API may additionally return CBAM and Grad-CAM data. Check `/docs` for the exact response schema in your checkout.

## 5. Install and start the Next.js frontend (Terminal 2)

Open a **second** PowerShell terminal:

```powershell
cd C:\Sliit_Research\J26-IT-359\components\c1-bird-recognition\frontend
npm install
npm run dev
```

Open **http://localhost:3000** in your browser.

Keep **both** terminals running while testing. In the tested local setup, the browser communicates with FastAPI on `http://127.0.0.1:8000`. The backend must allow the local frontend origin (`http://localhost:3000`) through CORS. If the frontend uses a configurable API URL, set it to that backend address according to your current code.

## 6. Use the application

1. Open `http://localhost:3000`.
2. Upload one bird photograph (`.jpg`, `.jpeg` or `.png`; up to 10 MB).
3. Check the preview and select **Analyze Bird**.
4. Read the **baseline** and **CBAM** predicted species and model scores.
5. Scroll to **Understand the prediction** to view the original image and both Grad-CAM heatmaps.
6. Adjust **Heatmap opacity** to see the highlighted region over the original photograph.
7. Try another image; both models may agree or disagree.

A previously tested **Sri Lanka Frogmouth** photograph (`0003.jpg`) produced *Sri Lanka Frogmouth* from both models with model scores around **99.98%**. This is an example, not a guarantee for other images.

### Reading the results

- **Model score:** A softmax value; it is **not** a calibrated probability that the species is correct.
- **Model disagreement:** The two models have learned different representations and may predict different species.
- **Grad-CAM:** Warmer colors indicate regions with greater positive contribution to that model's chosen class score. A heatmap is **not** a segmentation mask or proof the prediction is correct.
- **Supported species only:** Uploading an unfamiliar bird still forces a choice among the ten known classes. The app does not yet have verified unknown-species rejection.

## Supported bird classes

1. Ashy-headed Laughingthrush
2. Chestnut-backed Owlet
3. Green-billed Coucal
4. Spot-winged Thrush
5. Sri Lanka Blue Magpie
6. Sri Lanka Frogmouth
7. Sri Lanka Hanging Parrot
8. Sri Lanka Junglefowl
9. Sri Lanka Spurfowl
10. Yellow-fronted Barbet

Use **“10 selected Sri Lankan bird species”**, not **“10 endemic species”**, until the endemic status of each class has been individually checked.

## Training and evaluation summary

The training was previously completed in **Google Colab (Tesla T4)** using transfer learning from ImageNet-pretrained EfficientNetV2-S weights. Both architectures used 384×384 RGB input and the same main training settings.

| Item | Baseline | CBAM |
|---|---:|---:|
| Training epochs | 10 | 10 |
| Batch size | 8 | 8 |
| Optimizer | AdamW | AdamW |
| Learning rate | 0.0001 | 0.0001 |
| Best validation checkpoint | Epoch 10 | Epoch 7 |
| Test accuracy | **97.91%** | **96.93%** |
| Test macro-F1 | **97.69%** | **97.14%** |
| Test incorrect predictions | 17 / 814 | 25 / 814 |

Dataset: **5,454 original records**, **5,420 provisionally included images**; train **3,792**, validation **814**, test **814**. Preprocessing included EXIF correction, RGB conversion, 384×384 resizing and ImageNet normalization. Training augmentations included horizontal flipping, small rotations and modest color jitter.

CBAM adds **8,290 trainable parameters** after feature stage 6 (256 channels). In this **single-run** comparison, CBAM did **not** improve overall test accuracy or macro-F1, although four individual species had improved F1 scores.

**Scientific limitations:** The splits and labels are provisional, possible hidden photographer/session/source overlap has not been fully ruled out, and robustness under poor lighting, motion blur, foliage occlusion and different viewpoints has not been systematically validated. AI-generated bird pictures do not provide reliable ground truth for an accuracy benchmark. Do not retrain or reselect checkpoints using the held-out test results.

## Optional development checks

For the frontend:

```powershell
cd C:\Sliit_Research\J26-IT-359\components\c1-bird-recognition\frontend
npm run lint
npm run build
```

For API smoke testing, visit `/health` and `/docs`, then submit an image through the application or the Swagger `/docs` interface. Use a **real, labeled photograph** when checking prediction correctness; a synthetic/noise image only checks that inference runs.

## Troubleshooting

| Symptom | Check |
|---|---|
| Frontend does not load | Is `npm run dev` still running? Is `http://localhost:3000` available? |
| Prediction fails / network error | Is FastAPI still running on port 8000? Does `/health` respond? |
| Browser reports CORS error | The backend should explicitly allow `http://localhost:3000` (and any local origin actually used). Restart FastAPI after changes. |
| Model checkpoint missing | Confirm exact filenames in `models/` and that files are valid, not empty downloads. |
| CPU inference is slow | Wait for the request to finish; both models and Grad-CAM are computationally intensive. Keep the app running locally for the demo. |
| Port 3000 or 8000 in use | Stop the old server with `Ctrl + C`, or check the port before starting another instance. |
| Invalid image / file too large | Use JPG/JPEG or PNG under 10 MB; ensure the file is a decodable image. |
| Python import error | Activate `.venv` and install packages imported by the current source. |
| Model predictions disagree | This can be expected; use both outputs and interpret each Grad-CAM map for its own predicted class. |

## Safe Git workflow

From the repository root:

```powershell
git branch --show-current
git status --short
```

Review the changes first. Stage only C1 source, documentation, frontend configuration and dependency lockfiles intentionally. **Do not use `git add .` blindly**: exclude dataset directories, `C1_colab_bundle/`, `models/*.pt`, `frontend/node_modules/`, `frontend/.next/`, local environment files and temporary screenshots not intended for the repository.

## Future work

- Expert-verify species labels and image provenance; strengthen leakage-safe, independent evaluation.
- Evaluate matched, labeled images under systematic low-light, blur, occlusion and viewpoint changes.
- Repeat training across different random seeds; test alternative CBAM placements and augmentation settings.
- Study confidence calibration and safe handling of unsupported species.
- Coordinate integration with the rest of the team’s conservation system.

---

**Research-use notice:** This prototype provides model predictions, not guaranteed species identifications. Use human expert review for consequential conservation decisions.

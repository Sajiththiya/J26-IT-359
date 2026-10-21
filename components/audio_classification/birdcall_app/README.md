# Birdcall · Component 02

A local Next.js + FastAPI application for **Noise-Robust Bioacoustic Bird Call Recognition for Sri Lankan Endemic Birds**. The app now uses the finalized Wav2Vec2 run `20261020T072702969170Z`. It does not train models or modify research artifacts.

## Run your trained Wav2Vec2 model

From the repository root, open a PowerShell terminal:

```powershell
cd components/audio_classification/birdcall_app/backend
.\.venv\Scripts\python.exe -m pip install -r requirements-model.txt
.\run-model.ps1
```

Stop any old backend on port 8000 with Ctrl+C first. If your PowerShell policy blocks scripts, use these commands instead, from the backend folder:

```powershell
$env:DEMO_MODE = "false"
Remove-Item Env:MODEL_PATH -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

The default checkpoint is `model_runs/wav2vec2/20261020T072702969170Z/final/best_model` within Component 02. No model files need to be moved. The loader reads the run-level label mapping and the checkpoint's own feature extractor. It matches the notebook's five-second windows, skips digitally silent windows, zero-pads the final window, and weights each window's probabilities by its original sample count. Transformers is pinned to the training export's version, 4.57.1.

In another terminal, run the frontend as described below. Wait for `/health` to report `ready: true` and `demo_mode: false`. The upload panel displays **TRAINED MODEL READY** and refreshes readiness every 15 seconds or when you return to the window. The checkpoint takes time to load on CPU. Demo mode remains available only when explicitly enabled.

The **Model results** section reads `GET /model-info` and its allowlisted figure endpoints. It displays saved **validation** accuracy (63.57%), macro F1 (0.6349), 925 clips, selected epoch 2, per-species scores, learning curves, confusion matrix, and per-species precision/recall charts. These are not held-out test results or upload-specific confidence. The AST run is not selected. Report availability does not imply the model is loaded; live readiness is shown separately.

## Run locally (Windows PowerShell)

Prerequisites: Python 3.11+ and Node.js 20.9+ (Node 22 recommended). Run these commands from the repository root. Use two terminals.

Terminal 1 — backend, explicitly enabled demo:

```powershell
cd components/audio_classification/birdcall_app/backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DEMO_MODE = "true"
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend:

```powershell
cd components/audio_classification/birdcall_app/frontend
Copy-Item .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000. API documentation: http://localhost:8000/docs. Stop each server with Ctrl+C. No virtual-environment activation or PowerShell execution-policy change is needed.

Upload a WAV, MP3, or M4A, listen to it, and select **Run demo analysis**. Continue to results. The home page, analysis completion, result banner, confidence label, and model name distinguish demo examples from inference. The exact same decoded audio produces the same example ranking; the scores are fixed illustrative values, not acoustic recognition, accuracy, or research evidence.

Demo mode defaults to **false**. Without an available checkpoint, `/health` reports `ready: false` and `/predict` returns HTTP 503 with an explanation. The frontend disables analysis when the backend is unavailable or not ready. Restart the backend after changing environment variables.

## Small project structure

```text
birdcall_app/
  backend/
    main.py                 # API, validation, audio decoding, demo predictions
    inference.py            # Local PyTorch / Transformers checkpoint adapter
    test_api.py             # API and codec checks
    requirements.txt        # Demo/server dependencies
    requirements-model.txt  # Additional real-inference dependencies
  frontend/
    app/                    # Home, analysis, results, shared layout and styles
    components/             # Session state, HTTP client, audio preview
```

Species are read from `../colab_training_package/label_mapping.json`, in its existing ID order. Keep the app within Component 02 so this relative path remains valid. No names are invented, and the frontend fetches the list from `/species`. The project's research title is retained; the interface describes these as dataset species without adding unverified endemic-status claims.

## API and audio processing

- `GET /health`: service status, mode, model readiness, and explanatory message.
- `GET /species`: exactly ten labels, readable names, IDs, and mapping provenance.
- `POST /predict`: multipart form field `file`; returns `demo_mode`, `notice`, `prediction`, `top_three`, `model_name`, and processed audio metadata.

Limits: 20 MB, 0.1–60 seconds, supported filename extension plus successful content decoding. Empty, malformed, silent, oversized, and excessively long audio is rejected. PyAV decodes WAV/MP3/M4A and resamples to float32, 16 kHz, mono. Its wheels include FFmpeg libraries; a separate FFmpeg executable is normally unnecessary. Decoded audio is processed in memory. FastAPI may spool multipart uploads to a temporary file; the upload is closed after each request, and recordings are not retained by the application. Browser previews use the browser's decoder; if a codec is unsupported there, backend decoding can still work. Waveforms represent decoded samples, not decorative placeholder data.

`NEXT_PUBLIC_API_URL` configures the frontend API address (default `http://localhost:8000`); restart/rebuild Next.js after changing it. `CORS_ORIGINS` is a comma-separated backend allowlist, defaulting to localhost and 127.0.0.1 on port 3000. For a different frontend port, update it. File/result state exists only in React memory and clears on refresh. Analysis requests time out after two minutes; navigating away cancels the browser request, but server work already started may finish.

## Override with a different trained checkpoint

Install optional inference dependencies:

```powershell
cd components/audio_classification/birdcall_app/backend
.\.venv\Scripts\python.exe -m pip install -r requirements-model.txt
$env:DEMO_MODE = "false"
$env:MODEL_PATH = "C:\path\to\exported-checkpoint"
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Supply a local Hugging Face `save_pretrained` export containing model weights, `config.json`, the **matching trained feature extractor** (`preprocessor_config.json`), `label_mapping.json` with `id2label`, and `inference_config.json`. This app never downloads checkpoints or starts training. Raw `.pt` state dictionaries need to be exported using the matching model architecture outside this app.

Example `inference_config.json`, **only if five-second windows match your final training setup**:

```json
{"clip_seconds": 5.0}
```

The prepared dataset currently has five-second clips, but the final checkpoint's training configuration is authoritative. Set the window accordingly. The adapter supports Wav2Vec2 and AST through `AutoModelForAudioClassification`; it requires 16 kHz and ten labels. The checkpoint mapping must contain the same dataset labels, and its order must exactly match `config.json`'s `id2label`. Generic `LABEL_0` values are rejected. AST normalization and spectrogram dimensions come from its exported feature extractor. No arbitrary feature-extractor defaults are substituted.

Recordings are split into non-overlapping windows, silent windows are skipped, the final window is zero-padded, and softmax probabilities are averaged using original window lengths as weights, matching the Wav2Vec2 notebook. Inference runs on CPU in eval/inference mode. A model-load failure leaves the health endpoint available but prediction unavailable; it never silently enables demo mode. Scores are not calibrated confidence, and the closed-set classifier has no unknown-species rejection. Noise robustness is an objective, not an implemented denoiser or an established accuracy claim. An overridden checkpoint does not change the pinned Wav2Vec2 validation report; the prediction's model name identifies the active checkpoint.

## Verify

```powershell
# Backend directory
.\.venv\Scripts\python.exe -m pytest -q
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/species
# Frontend directory
npm run typecheck
npm run build
```

Tests cover deterministic demo results, all three codecs, stereo/44.1 kHz conversion, error responses, silence/duration limits, missing checkpoints, and CORS. Real model correctness requires the future trained artifact and evaluation data. Local development only: configure deployment authentication, request limits, and concurrency capacity before exposing the API publicly.

For the optional browser smoke test, start both servers with demo mode explicitly enabled, then run in the frontend directory:

```powershell
npm install --no-save --package-lock=false playwright
node smoke-test.cjs
```

The script uses an installed Microsoft Edge browser and synthetic audio generated in memory. It checks actual HTTP requests, waveform rendering, the ten-species list, demo labels, success/error states, refresh fallback, and mobile overflow. It saves `demo-results.png` and `mobile-home.png` for review.

Verified on 2026-10-21: production build, TypeScript check, all 10 backend tests, and the browser smoke test passed. The unavailable-backend state was also checked in Edge. The installed Starlette version emits a non-failing deprecation warning about its HTTPX test adapter. That initial verification used demo mode. The trained-model integration is verified separately below.

Implementation references: [Next.js App Router](https://nextjs.org/docs/app/getting-started/installation) and [Hugging Face feature extractors](https://huggingface.co/docs/transformers/v4.52.2/feature_extractors).

## Trained-model verification

The finalized Wav2Vec2 checkpoint was loaded locally on CPU and one validation clip produced the same label as its saved validation prediction. This is an integration check, not a new accuracy evaluation. The build, TypeScript check, and 11 API tests passed.

`powershell
# Backend folder: load the real checkpoint and compare one saved prediction
.\.venv\Scripts\python.exe verify_model.py
# Frontend folder, with both servers running in real-model mode
node smoke-model.cjs
`

The browser check verifies report values, all ten species, saved figures, a real audio upload and model result, and mobile overflow. It requires Playwright and Microsoft Edge, as described above.

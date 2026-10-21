import hashlib
import io
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
import av
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from inference import BirdModel
from fastapi.responses import FileResponse
from research import CHECKPOINT, RUN, FIGURES, model_report

SOURCE = Path(__file__).resolve().parents[2] / "colab_training_package" / "label_mapping.json"
MAPPING = json.loads(SOURCE.read_text())
SPECIES = [MAPPING["id2label"][str(i)] for i in range(10)]
if len(set(SPECIES)) != 10 or len(MAPPING["id2label"]) != 10:
    raise RuntimeError("Dataset mapping must contain exactly ten unique species.")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
MAX_BYTES = 20 * 1024 * 1024
model = None
model_error = "No checkpoint configured. Set MODEL_PATH or explicitly set DEMO_MODE=true."


@asynccontextmanager
async def lifespan(app):
    global model, model_error
    model = None
    if not DEMO_MODE:
        try:
            model = BirdModel(os.getenv("MODEL_PATH") or str(CHECKPOINT), SPECIES)
            model_error = ""
        except Exception as exc:
            logging.exception("Checkpoint could not be loaded")
            model_error = f"Checkpoint unavailable: {exc}. Install requirements-model.txt in the backend environment and restart the server."
    yield


app = FastAPI(title="Birdcall · Component 02", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","), allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.get("/health")
def health():
    return {"status": "ok", "demo_mode": DEMO_MODE, "ready": DEMO_MODE or model is not None,
            "model_name": model.name if model else None,
            "message": "DEMO MODE: example scores, not AI predictions." if DEMO_MODE else (model_error or f"{model.name} is ready for real inference.")}


@app.get("/model-info")
def model_info():
    try:
        return model_report()
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(503, "The finalized Wav2Vec2 report is unavailable or incomplete.") from exc


@app.get("/model-info/figures/{figure}")
def model_figure(figure: str):
    if figure not in FIGURES:
        raise HTTPException(404, "Unknown research figure.")
    path = RUN / "final" / FIGURES[figure]
    if not path.is_file():
        raise HTTPException(404, "Research figure is unavailable.")
    return FileResponse(path, media_type="image/png")


@app.get("/species")
def species():
    return {"species": [{"id": i, "label": label, "name": label.replace("_", " ")} for i, label in enumerate(SPECIES)], "source": "colab_training_package/label_mapping.json"}


def decode(data):
    chunks = []
    count = 0
    try:
        with av.open(io.BytesIO(data)) as container:
            if not container.streams.audio:
                raise ValueError("No audio stream found.")
            resampler = av.AudioResampler(format="fltp", layout="mono", rate=16000)
            for frame in container.decode(audio=0):
                for converted in resampler.resample(frame):
                    values = converted.to_ndarray().reshape(-1)
                    count += len(values)
                    if count > 16000 * 60:
                        raise ValueError("Audio must be no longer than 60 seconds.")
                    chunks.append(values)
            for converted in resampler.resample(None):
                chunks.append(converted.to_ndarray().reshape(-1))
        audio = np.concatenate(chunks) if chunks else np.array([])
        if not 1600 <= len(audio) <= 960000:
            raise ValueError("Audio must be between 0.1 and 60 seconds.")
        if not np.isfinite(audio).all() or np.max(np.abs(audio)) < 1e-7:
            raise ValueError("Audio is silent or contains invalid samples.")
        return audio.astype(np.float32)
    except av.FFmpegError as exc:
        raise HTTPException(422, "Cannot decode this recording. Upload a valid WAV, MP3, or M4A file.") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(422, "Cannot decode this recording. Upload a valid WAV, MP3, or M4A file.") from exc


def analyze(data):
    audio = decode(data)
    if DEMO_MODE:
        seed = int(hashlib.sha256(audio.tobytes()).hexdigest()[:16], 16)
        order = np.random.default_rng(seed).permutation(10)
        scores = np.empty(10)
        scores[order] = [0.72, 0.16, 0.06, 0.015, 0.012, 0.01, 0.008, 0.006, 0.005, 0.004]
        labels, name = SPECIES, "Deterministic demo · no trained model"
    else:
        try:
            labels, scores = model.predict(audio)
            name = model.name
        except Exception as exc:
            logging.exception("Inference failed")
            raise HTTPException(503, "Checkpoint inference failed. Check the server logs and checkpoint configuration.") from exc
    top = [{"species": labels[i].replace("_", " "), "label": labels[i], "confidence": float(scores[i])} for i in np.argsort(scores)[::-1][:3]]
    return {"demo_mode": DEMO_MODE, "notice": "Example scores only. These are not AI predictions or measured accuracy." if DEMO_MODE else "Model scores are not calibrated certainty; unknown species may match a supported class.", "prediction": top[0], "top_three": top, "model_name": name, "audio": {"sample_rate": 16000, "channels": 1, "duration_seconds": round(len(audio) / 16000, 3)}}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        if Path(file.filename or "").suffix.lower() not in {".wav", ".mp3", ".m4a"}:
            raise HTTPException(415, "Supported formats: WAV, MP3, M4A.")
        data = await file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "Maximum upload size is 20 MB.")
        if not data:
            raise HTTPException(422, "The uploaded file is empty.")
        if not DEMO_MODE and model is None:
            raise HTTPException(503, model_error)
        return await run_in_threadpool(analyze, data)
    finally:
        await file.close()

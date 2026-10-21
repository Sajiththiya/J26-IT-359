"""Optional real-checkpoint integration check; reads one existing validation clip."""
import csv
import os

os.environ["DEMO_MODE"] = "false"
os.environ.pop("MODEL_PATH", None)

from fastapi.testclient import TestClient
from research import RUN, COMPONENT
from main import app

with (RUN / "final" / "validation_predictions.csv").open(encoding="utf-8", newline="") as file:
    reference = next(csv.DictReader(file))
audio = COMPONENT / "colab_training_package" / reference["audio_path"]

with TestClient(app) as client:
    health = client.get("/health").json()
    assert health["ready"] and not health["demo_mode"], health
    with audio.open("rb") as file:
        response = client.post("/predict", files={"file": (audio.name, file, "audio/wav")})
    assert response.status_code == 200, response.text
    result = response.json()
    labels = client.get("/species").json()["species"]
    expected = labels[int(reference["predicted_label"])]["label"]
    assert result["prediction"]["label"] == expected, result
    assert not result["demo_mode"] and len(result["top_three"]) == 3
    print("PASS: real checkpoint loaded; prediction matches the saved validation prediction.")
    print(result["model_name"], result["prediction"])

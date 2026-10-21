"""Read-only access to the finalized Wav2Vec2 run used by this app."""
import csv
import json
from pathlib import Path

COMPONENT = Path(__file__).resolve().parents[2]
RUN_ID = "20261020T072702969170Z"
RUN = COMPONENT / "model_runs" / "wav2vec2" / RUN_ID
CHECKPOINT = RUN / "final" / "best_model"
# The training notebook verifies 80,000 samples and uses five-second windows.
CLIP_SECONDS = 5.0
FIGURES = {
    "learning-curves": "learning_curves.png",
    "confusion-matrix": "validation_confusion_matrix.png",
    "precision-recall": "validation_precision_recall.png",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def model_report():
    final = RUN / "final"
    metrics = read_json(final / "validation_metrics.json")
    selection = read_json(final / "selection_finalized.json")
    integrity = read_json(RUN / "data_integrity.json")
    environment = read_json(RUN / "environment.json")
    with (final / "validation_per_species.csv").open(encoding="utf-8", newline="") as file:
        species = [{"name": row["species"].replace("_", " "),
                    "precision": float(row["precision"]), "recall": float(row["recall"]),
                    "f1": float(row["f1-score"]), "support": int(float(row["support"]))}
                   for row in csv.DictReader(file)]
    return {"name": "Wav2Vec2", "base_model": environment["checkpoint"],
            "run_id": RUN_ID, "checkpoint_available": (CHECKPOINT / "model.safetensors").is_file(),
            "split": "validation", "metrics": metrics,
            "validation_clips": integrity["counts"]["val"],
            "best_epoch": selection["best_epoch"], "hyperparameters": selection["hyperparameters"],
            "test_used_for_selection": selection["test_used_for_selection"],
            "species": species, "source": f"model_runs/wav2vec2/{RUN_ID}/final",
            "figures": [{"id": key, "url": f"/model-info/figures/{key}"}
                        for key, name in FIGURES.items() if (final / name).is_file()],
            "notice": "Validation results, not held-out test performance or proof of noise robustness. Upload confidence is a separate model score."}

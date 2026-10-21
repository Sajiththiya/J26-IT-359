"""Local-only inference; importing the demo server never loads Torch or weights."""
import json
from pathlib import Path
import numpy as np
from research import CHECKPOINT, RUN, RUN_ID, CLIP_SECONDS


class BirdModel:
    def __init__(self, checkpoint: str, species: list[str]):
        import torch
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

        root = Path(checkpoint)
        if not root.is_dir():
            raise ValueError("MODEL_PATH must point to a local exported checkpoint directory.")
        is_research_run = root.resolve() == CHECKPOINT.resolve()
        mapping_path = RUN / "label_mapping.json" if is_research_run else root / "label_mapping.json"
        mapping = json.loads(mapping_path.read_text())
        self.labels = [mapping["id2label"][str(i)] for i in range(10)]
        if len(set(self.labels)) != 10 or set(self.labels) != set(species):
            raise ValueError("Checkpoint labels must match the ten dataset species exactly.")
        settings = {"clip_seconds": CLIP_SECONDS} if is_research_run else json.loads((root / "inference_config.json").read_text())
        seconds = float(settings["clip_seconds"])
        if not 0.1 <= seconds <= 30:
            raise ValueError("clip_seconds must be between 0.1 and 30.")
        self.samples = round(seconds * 16000)
        self.extractor = AutoFeatureExtractor.from_pretrained(root, local_files_only=True)
        self.model = AutoModelForAudioClassification.from_pretrained(root, local_files_only=True, attn_implementation="eager").eval()
        if self.model.config.model_type not in {"wav2vec2", "audio-spectrogram-transformer"}:
            raise ValueError("Only Wav2Vec2 and AST checkpoints are supported.")
        if self.extractor.sampling_rate != 16000 or self.model.config.num_labels != 10:
            raise ValueError("Checkpoint must expect 16 kHz audio and ten classes.")
        if [self.model.config.id2label[i] for i in range(10)] != self.labels:
            raise ValueError("Model config and label_mapping.json disagree on class order.")
        self.torch = torch
        self.name = f"Wav2Vec2 · {RUN_ID}" if is_research_run else f"{self.model.config.model_type} / {root.name}"

    def predict(self, audio):
        scores = []
        durations = []
        with self.torch.inference_mode():
            for start in range(0, len(audio), self.samples):
                chunk = audio[start:start + self.samples]
                actual = len(chunk)
                if not np.any(chunk):
                    continue
                chunk = np.pad(chunk, (0, self.samples - len(chunk)))
                kwargs = {"padding": True, "return_attention_mask": self.model.config.feat_extract_norm == "layer"} if self.model.config.model_type == "wav2vec2" else {}
                inputs = self.extractor([chunk], sampling_rate=16000, return_tensors="pt", **kwargs)
                logits = self.model(**inputs).logits
                scores.append(self.torch.softmax(logits, dim=-1)[0].cpu().numpy())
                durations.append(actual)
        if not scores:
            raise ValueError("No non-silent audio windows found.")
        result = np.average(scores, axis=0, weights=durations)
        if not np.isfinite(result).all():
            raise ValueError("Checkpoint produced invalid scores.")
        return self.labels, result

"""Load included C1 experiment images with deterministic initial preprocessing."""

import csv
from pathlib import Path

from PIL import Image, ImageOps
from torch.utils.data import Dataset
from torchvision import transforms


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = (
    REPO_ROOT
    / "components/c1-bird-recognition/data/reports/experiment_manifest_provisional.csv"
)


class BirdDataset(Dataset):
    def __init__(self, split, transform=None, manifest_path=MANIFEST):
        if split not in {"train", "val", "test"}:
            raise ValueError(f"Invalid split: {split}")
        self.split = split
        self.transform = transform if transform is not None else transforms.Compose([
            transforms.Resize((384, 384)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])
        with Path(manifest_path).open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.DictReader(file)
            required = {"image_path", "species", "experiment_status", "split"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError("Manifest is missing required dataset columns")
            rows = list(reader)
        self.samples = [
            row for row in rows
            if row["experiment_status"] == "include"
            and row["split"] == split
        ]
        self.species = sorted({
            row["species"]
            for row in rows
            if row["experiment_status"] == "include"
        })
        self.class_to_idx = {
            species: index
            for index, species in enumerate(self.species)
        }
        if not self.samples:
            raise ValueError(f"No included images for split: {split}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        row = self.samples[index]
        image_path = REPO_ROOT / row["image_path"].replace("\\", "/")
        with Image.open(image_path) as image:
            with ImageOps.exif_transpose(image) as corrected:
                rgb = corrected.convert("RGB")
        try:
            image = self.transform(rgb)
        finally:
            rgb.close()
        label = self.class_to_idx[row["species"]]
        return image, label

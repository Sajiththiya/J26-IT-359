"""Sample eligible images per species for a pending human label review.

This initial sample does not establish label correctness for the full dataset.
Only label_review_sample.csv is written; images and split inputs are unchanged.
"""

import csv
import random
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
COMPONENT = ROOT / "components/c1-bird-recognition"
INPUT = COMPONENT / "data/reports/dataset_splits.csv"
OUTPUT = COMPONENT / "data/reports/label_review_sample.csv"
SEED = 42
SAMPLES_PER_SPECIES = 10


def main():
    with INPUT.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        fields = reader.fieldnames or []
        required = {"image_path", "species", "split", "exclude"}
        if not required.issubset(fields):
            raise ValueError("Dataset split CSV is missing required columns.")
        rows = list(reader)
    if not rows:
        raise ValueError("Dataset split CSV is empty.")
    if len({row["image_path"] for row in rows}) != len(rows):
        raise ValueError("Duplicate image paths in dataset split CSV.")
    if "review_status" in fields or "review_notes" in fields:
        raise ValueError("Input already contains review columns; refusing to reset them.")

    by_species = defaultdict(list)
    for row in rows:
        if row["split"] in {"train", "val", "test"}:
            if row["exclude"].lower() != "false":
                raise ValueError(f"Excluded image assigned to a partition: {row['image_path']}")
            if not row["image_path"] or not row["species"]:
                raise ValueError("Eligible image has an empty path or species.")
            by_species[row["species"]].append(row)
    if len(by_species) != 10:
        raise ValueError(f"Expected 10 species, found {len(by_species)}.")

    rng = random.Random(SEED)
    selected = []
    for species in sorted(by_species):
        candidates = sorted(by_species[species], key=lambda row: row["image_path"])
        if len(candidates) < SAMPLES_PER_SPECIES:
            raise ValueError(f"Insufficient eligible images for species: {species}")
        for row in rng.sample(candidates, SAMPLES_PER_SPECIES):
            selected.append({**row, "review_status": "pending", "review_notes": ""})

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields + ["review_status", "review_notes"])
        writer.writeheader()
        writer.writerows(selected)

    print("=== C1 LABEL REVIEW SAMPLE ===")
    print(f"Species sampled: {len(by_species)}")
    print(f"Sampled images: {len(selected)}")
    print(f"Images per species: {SAMPLES_PER_SPECIES}")
    print("Review status: pending")
    print(f"Output: {OUTPUT}")
    print("Original images modified: 0")
    print("================================")


if __name__ == "__main__":
    main()

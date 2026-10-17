"""Screen within-species image pairs for visual review without changing images.

The 64-bit pHash distance threshold is a screening heuristic. A match is
only a potential near-duplicate and must be reviewed before exclusion.
Cross-species and same-observation checks remain necessary before splitting.
"""

import csv
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import imagehash
from PIL import Image, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPONENT_DIR = Path(__file__).resolve().parents[1]
DATASET_DIR = COMPONENT_DIR / "data" / "raw"
REPORT_DIR = COMPONENT_DIR / "data" / "reports"
INPUT_CSV = REPORT_DIR / "clean_manifest.csv"
OUTPUT_CSV = REPORT_DIR / "near_duplicates.csv"
PHASH_THRESHOLD = 6
REPORT_FIELDS = [
    "species",
    "image_path_a",
    "image_path_b",
    "sha256_a",
    "sha256_b",
    "phash_a",
    "phash_b",
    "phash_distance",
    "phash_threshold",
]


def calculate_phash(image_path: Path) -> imagehash.ImageHash:
    with Image.open(image_path) as image:
        # Apply EXIF orientation before calculating the 64-bit hash.
        with ImageOps.exif_transpose(image) as oriented:
            with oriented.convert("RGB") as rgb:
                return imagehash.phash(rgb, hash_size=8)


def main() -> None:
    if not INPUT_CSV.is_file():
        raise FileNotFoundError(f"Clean manifest not found: {INPUT_CSV}")

    with INPUT_CSV.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required_fields = {"species", "image_path", "sha256"}
        if not required_fields.issubset(reader.fieldnames or []):
            raise ValueError("Clean manifest requires species, image_path, and sha256.")
        records = sorted(reader, key=lambda row: (row["species"], row["image_path"]))

    print("=== C1 NEAR-DUPLICATE DETECTION ===")
    print(f"Images in manifest: {len(records)}")
    print(f"64-bit pHash threshold: {PHASH_THRESHOLD} (screening heuristic)")
    grouped = defaultdict(list)
    successful = 0
    failed = 0

    for index, record in enumerate(records, start=1):
        try:
            image_path = (PROJECT_ROOT / record["image_path"]).resolve()
            if not image_path.is_relative_to(DATASET_DIR.resolve()):
                raise ValueError("Image path is outside the raw dataset directory.")
            if not record["species"] or not record["sha256"]:
                raise ValueError("Species and SHA-256 must not be empty.")
            phash = calculate_phash(image_path)
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
            failed += 1
            print(f"FAILED {record['image_path']}: {type(error).__name__}: {error}")
        else:
            grouped[record["species"]].append((record, phash))
            successful += 1

        if index % 500 == 0 or index == len(records):
            print(f"Processed {index}/{len(records)} images")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    pair_count = 0
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for species, images in sorted(grouped.items()):
            for (record_a, hash_a), (record_b, hash_b) in combinations(images, 2):
                # Exact duplicates are handled by the clean-manifest step.
                if record_a["sha256"] == record_b["sha256"]:
                    continue
                distance = hash_a - hash_b
                if distance <= PHASH_THRESHOLD:
                    writer.writerow({
                        "species": species,
                        "image_path_a": record_a["image_path"],
                        "image_path_b": record_b["image_path"],
                        "sha256_a": record_a["sha256"],
                        "sha256_b": record_b["sha256"],
                        "phash_a": str(hash_a),
                        "phash_b": str(hash_b),
                        "phash_distance": distance,
                        "phash_threshold": PHASH_THRESHOLD,
                    })
                    pair_count += 1

    print("\n=== RESULTS ===")
    print(f"Images processed successfully: {successful}")
    print(f"Failed images: {failed}")
    print(f"Potential near-duplicate pairs: {pair_count}")
    print(f"Report saved: {OUTPUT_CSV}")
    print("Original images were not modified.")


if __name__ == "__main__":
    main()

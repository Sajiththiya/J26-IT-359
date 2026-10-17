"""Screen raw images for cross-species, distance-0 pHash candidates.

Matches require visual review and do not establish label correctness. Only
the audit CSV is written; raw images are never modified or excluded.
"""

import csv
import hashlib
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from PIL import Image

from detect_near_duplicates import calculate_phash


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPONENT_DIR = PROJECT_ROOT / "components" / "c1-bird-recognition"
RAW_DIR = COMPONENT_DIR / "data/raw"
REPORT_DIR = COMPONENT_DIR / "data/reports"
OUTPUT_CSV = REPORT_DIR / "cross_species_phash_zero.csv"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
REPORT_FIELDS = [
    "species_a", "species_b", "image_path_a", "image_path_b",
    "phash_a", "phash_b", "phash_distance",
    "sha256_a", "sha256_b", "exact_sha256_match",
]


def calculate_hash(path: Path) -> str:
    # Reuse EXIF correction, RGB conversion and 64-bit pHash settings.
    return str(calculate_phash(path))


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not RAW_DIR.is_dir():
        raise FileNotFoundError(f"Raw dataset not found: {RAW_DIR}")
    paths = sorted(
        path for path in RAW_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in EXTENSIONS
    )
    grouped = defaultdict(list)
    successful = 0
    failures = 0
    print(f"Scanning {len(paths)} original images (no exclusions applied).", flush=True)
    for index, path in enumerate(paths, start=1):
        try:
            phash = calculate_hash(path)
            sha256 = calculate_sha256(path)
            species = path.relative_to(RAW_DIR).parts[0]
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
            failures += 1
            print(f"FAILED {path}: {type(error).__name__}: {error}", flush=True)
        else:
            grouped[phash].append({
                "species": species,
                "image_path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256,
            })
            successful += 1
        if index % 500 == 0 or index == len(paths):
            print(f"Processed {index}/{len(paths)} images", flush=True)

    pair_count = 0
    exact_count = 0
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        # Identical hashes share a bucket; no quadratic scan across all images.
        for phash, records in sorted(grouped.items()):
            for a, b in combinations(records, 2):
                if a["species"] == b["species"]:
                    continue
                exact = a["sha256"] == b["sha256"]
                writer.writerow({
                    "species_a": a["species"],
                    "species_b": b["species"],
                    "image_path_a": a["image_path"],
                    "image_path_b": b["image_path"],
                    "phash_a": phash,
                    "phash_b": phash,
                    "phash_distance": 0,
                    "sha256_a": a["sha256"],
                    "sha256_b": b["sha256"],
                    "exact_sha256_match": exact,
                })
                pair_count += 1
                exact_count += int(exact)

    print("\n=== CROSS-SPECIES PHASH AUDIT ===")
    print(f"Images scanned: {len(paths)}")
    print(f"Images successfully hashed: {successful}")
    print(f"Hashing failures: {failures}")
    print(f"Cross-species distance-0 pairs: {pair_count}")
    print(f"Exact SHA-256 matches: {exact_count}")
    print(f"Report saved: {OUTPUT_CSV}")
    print("Distance-0 screening only; matches require visual review.")
    print("Original images were not modified.")


if __name__ == "__main__":
    main()

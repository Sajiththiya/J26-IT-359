"""Screen all original images for cross-species pHash distances up to six.

Matches are candidates for visual review, not confirmed label errors.
Only the audit CSV is written; images and split assignments are untouched.
"""

import csv
from collections import Counter, defaultdict
from itertools import combinations, product
from pathlib import Path

from PIL import Image

from detect_near_duplicates import calculate_phash


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPONENT = PROJECT_ROOT / "components/c1-bird-recognition"
RAW_DIR = COMPONENT / "data/raw"
OUTPUT = COMPONENT / "data/reports/cross_species_near_duplicates.csv"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
THRESHOLD = 6
REPORT_FIELDS = [
    "species_a", "species_b", "image_path_a", "image_path_b",
    "phash_a", "phash_b", "phash_distance", "phash_threshold",
]


def get_phash(path):
    # Reuse the detector's EXIF correction, RGB conversion and hash_size=8.
    return calculate_phash(path)


def find_candidates(records, threshold=THRESHOLD):
    grouped = defaultdict(list)
    for record in records:
        grouped[record["species"]].append(record)
    for species_a, species_b in combinations(sorted(grouped), 2):
        for a, b in product(grouped[species_a], grouped[species_b]):
            # XOR population count is the same Hamming distance as hash_a - hash_b.
            distance = (a["hash_bits"] ^ b["hash_bits"]).bit_count()
            if distance <= threshold:
                yield a, b, distance


def main():
    if not RAW_DIR.is_dir():
        raise FileNotFoundError(f"Raw dataset not found: {RAW_DIR}")
    paths = sorted(
        path for path in RAW_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in EXTENSIONS
    )
    records = []
    failures = []
    print(f"Scanning {len(paths)} original images (no exclusions applied).", flush=True)
    for index, path in enumerate(paths, start=1):
        try:
            phash = get_phash(path)
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
            failures.append(path)
            print(f"FAILED {path}: {type(error).__name__}: {error}", flush=True)
        else:
            records.append({
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "species": path.relative_to(RAW_DIR).parts[0],
                "hash": str(phash),
                "hash_bits": int(str(phash), 16),
            })
        if index % 500 == 0 or index == len(paths):
            print(f"Processed {index}/{len(paths)} images", flush=True)

    species_counts = Counter(record["species"] for record in records)
    comparison_count = sum(
        count_a * count_b
        for count_a, count_b in combinations(species_counts.values(), 2)
    )
    print(f"Comparing {comparison_count} cross-species pairs...", flush=True)
    distribution = Counter()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for a, b, distance in find_candidates(records):
            writer.writerow({
                "species_a": a["species"],
                "species_b": b["species"],
                "image_path_a": a["path"],
                "image_path_b": b["path"],
                "phash_a": a["hash"],
                "phash_b": b["hash"],
                "phash_distance": distance,
                "phash_threshold": THRESHOLD,
            })
            distribution[distance] += 1

    print("\n=== CROSS-SPECIES NEAR-DUPLICATE AUDIT ===")
    print(f"Images scanned: {len(paths)}")
    print(f"Images successfully hashed: {len(records)}")
    print(f"Hashing failures: {len(failures)}")
    print(f"Cross-species pairs compared: {comparison_count}")
    print(f"Total candidate pairs (distance <= {THRESHOLD}): {sum(distribution.values())}")
    print("Distance distribution:")
    for distance in range(THRESHOLD + 1):
        print(f"  {distance}: {distribution[distance]}")
    print(f"Report saved: {OUTPUT}")
    print("Matches require visual review; this is not a complete label audit.")
    print("Original images were not modified. No dataset splits were created.")


if __name__ == "__main__":
    main()

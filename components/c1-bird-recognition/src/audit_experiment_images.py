"""Read-only availability and full-decoding audit of included experiment images."""

import csv
from collections import Counter
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "components/c1-bird-recognition/data/reports"
MANIFEST = REPORTS / "experiment_manifest_provisional.csv"


def main():
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not {"image_path", "experiment_status"}.issubset(reader.fieldnames or []):
            raise ValueError("Manifest requires image_path and experiment_status columns")
        rows = list(reader)
    included = [row for row in rows if row["experiment_status"] == "include"]
    if len(included) != 5420:
        raise ValueError(f"Expected 5420 included images, found {len(included)}")
    paths = [row["image_path"].replace("\\", "/") for row in included]
    if any(not path.strip() for path in paths) or len(set(paths)) != len(paths):
        raise ValueError("Empty or repeated included image paths")

    missing = []
    unreadable = []
    formats = Counter()
    raw = (ROOT / "components/c1-bird-recognition/data/raw").resolve()
    for index, relative_path in enumerate(paths, start=1):
        image_path = (ROOT / relative_path).resolve()
        if not image_path.is_relative_to(raw):
            raise ValueError(f"Image path is outside the C1 raw dataset: {relative_path}")
        if not image_path.is_file():
            missing.append(relative_path)
        else:
            try:
                with Image.open(image_path) as image:
                    # load() decodes pixel data; opening headers alone is insufficient.
                    image.load()
                    formats[image.format or "UNKNOWN"] += 1
            except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
                unreadable.append((relative_path, f"{type(error).__name__}: {error}"))
        if index % 500 == 0 or index == len(paths):
            print(f"Processed {index}/{len(paths)} included images", flush=True)

    passed = not missing and not unreadable
    print("\n=== C1 EXPERIMENT IMAGE AUDIT ===")
    print(f"Included images: {len(included)}")
    print(f"Missing images: {len(missing)}")
    print(f"Unreadable images: {len(unreadable)}")
    print(f"Image formats: {dict(sorted(formats.items()))}")
    print(f"IMAGE AUDIT: {'PASS' if passed else 'FAIL'}")
    print("Original images modified: 0")
    for path in missing:
        print(f"MISSING: {path}")
    for path, error in unreadable:
        print(f"UNREADABLE: {path} | {error}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

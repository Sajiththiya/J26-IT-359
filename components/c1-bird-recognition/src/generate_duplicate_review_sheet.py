"""Create a reproducible sample sheet for manual near-duplicate review."""

import csv
import random
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPONENT_DIR = PROJECT_ROOT / "components" / "c1-bird-recognition"
INPUT_CSV = COMPONENT_DIR / "data/reports/near_duplicates.csv"
OUTPUT_IMAGE = COMPONENT_DIR / "data/reports/near_duplicate_review_sample.jpg"
SAMPLES_PER_DISTANCE = 5
DISTANCES = [0, 2, 4, 6]
RANDOM_SEED = 42
IMAGE_SIZE = (280, 210)
LABEL_HEIGHT = 65
ROW_HEIGHT = IMAGE_SIZE[1] + LABEL_HEIGHT
SHEET_WIDTH = 620


def create_sheet() -> None:
    rng = random.Random(RANDOM_SEED)
    grouped = defaultdict(list)
    with INPUT_CSV.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"image_path_a", "image_path_b", "phash_distance"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Required CSV columns missing")
        for row in reader:
            distance = int(row["phash_distance"])
            if distance in DISTANCES:
                grouped[distance].append(row)

    selected = []
    for distance in DISTANCES:
        candidates = sorted(
            grouped[distance],
            key=lambda row: (row["image_path_a"], row["image_path_b"]),
        )
        sample = rng.sample(candidates, min(SAMPLES_PER_DISTANCE, len(candidates)))
        selected.extend(sample)
        print(f"Distance {distance}: sampled {len(sample)} of {len(candidates)} pairs")
        if len(sample) < SAMPLES_PER_DISTANCE:
            print(f"WARNING: fewer than {SAMPLES_PER_DISTANCE} pairs at distance {distance}")

    if not selected:
        print("No candidate pairs found at the requested distances; no sheet generated.")
        return

    heading_height = 50
    sheet = Image.new(
        "RGB", (SHEET_WIDTH, heading_height + ROW_HEIGHT * len(selected)), "white"
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=12)
    filename_font = ImageFont.load_default(size=10)
    draw.text((20, 8), "Near-duplicate review sample | seed 42", fill="black", font=font)
    draw.text((20, 27), "Candidates for review; no exclusion decisions made.", fill="black", font=font)

    for index, pair in enumerate(selected):
        top = heading_height + index * ROW_HEIGHT
        draw.line((0, top, SHEET_WIDTH, top), fill="#aaaaaa")
        draw.text(
            (20, top + 5),
            f"Pair {index + 1:02d} | pHash distance {pair['phash_distance']}",
            fill="black", font=font,
        )
        for column, key in enumerate(("image_path_a", "image_path_b")):
            relative_path = Path(pair[key])
            left = 20 + column * 300
            side = "A" if column == 0 else "B"
            draw.text((left, top + 23), relative_path.parent.name, fill="black", font=filename_font)
            draw.text((left, top + 40), f"{side}: {relative_path.name}", fill="black", font=filename_font)
            draw.rectangle(
                (left, top + LABEL_HEIGHT, left + IMAGE_SIZE[0] - 1, top + ROW_HEIGHT - 1),
                fill="#eeeeee",
            )
            with Image.open(PROJECT_ROOT / relative_path) as original:
                with ImageOps.exif_transpose(original) as corrected:
                    with corrected.convert("RGB") as rgb:
                        with ImageOps.contain(rgb, IMAGE_SIZE, Image.Resampling.LANCZOS) as thumbnail:
                            x = left + (IMAGE_SIZE[0] - thumbnail.width) // 2
                            y = top + LABEL_HEIGHT + (IMAGE_SIZE[1] - thumbnail.height) // 2
                            sheet.paste(thumbnail, (x, y))

    OUTPUT_IMAGE.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUTPUT_IMAGE, quality=95, subsampling=0)
    sheet.close()
    print("=== NEAR-DUPLICATE REVIEW SHEET ===")
    print(f"Pairs displayed: {len(selected)}")
    print(f"Image saved to: {OUTPUT_IMAGE}")
    print("Original bird images were not modified.")


if __name__ == "__main__":
    create_sheet()

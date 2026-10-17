"""Render per-species samples for human review without changing review status."""

import csv
import textwrap
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPONENT = PROJECT_ROOT / "components/c1-bird-recognition"
INPUT_CSV = COMPONENT / "data/reports/label_review_sample.csv"
OUTPUT_DIR = COMPONENT / "data/reports/label_review_sheets"
COLUMNS = 5
CELL_WIDTH = 240
IMAGE_HEIGHT = 175
LABEL_HEIGHT = 65
ROWS = 2
HEADER_HEIGHT = 44


def main():
    with INPUT_CSV.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not {"image_path", "species"}.issubset(reader.fieldnames or []):
            raise ValueError("Review CSV requires image_path and species columns.")
        records = list(reader)
    if not records or len({r["image_path"] for r in records}) != len(records):
        raise ValueError("Review CSV is empty or contains repeated image paths.")
    grouped = defaultdict(list)
    for record in records:
        species = record["species"]
        if not species or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in species):
            raise ValueError(f"Invalid species filename: {species}")
        grouped[species].append(record)
    for species, items in grouped.items():
        if len(items) != COLUMNS * ROWS:
            raise ValueError(f"Expected 10 sample images for {species}, found {len(items)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    title_font = ImageFont.load_default(size=16)
    label_font = ImageFont.load_default(size=12)
    note_font = ImageFont.load_default(size=11)
    for species, items in sorted(grouped.items()):
        sheet = Image.new(
            "RGB",
            (COLUMNS * CELL_WIDTH, HEADER_HEIGHT + ROWS * (IMAGE_HEIGHT + LABEL_HEIGHT)),
            "white",
        )
        draw = ImageDraw.Draw(sheet)
        draw.text((10, 4), species.replace("_", " "), font=title_font, fill="black")
        draw.text((10, 25), "Candidate folder label | Human review pending | Sample only", font=note_font, fill="black")
        for index, record in enumerate(items):
            left = (index % COLUMNS) * CELL_WIDTH
            top = HEADER_HEIGHT + (index // COLUMNS) * (IMAGE_HEIGHT + LABEL_HEIGHT)
            draw.rectangle(
                (left + 4, top, left + CELL_WIDTH - 5, top + IMAGE_HEIGHT - 1),
                fill="#eeeeee",
            )
            path = (PROJECT_ROOT / record["image_path"]).resolve()
            try:
                if not path.is_relative_to((COMPONENT / "data/raw").resolve()):
                    raise ValueError("Image is outside the raw dataset directory.")
                with Image.open(path) as original:
                    with ImageOps.exif_transpose(original) as corrected:
                        with corrected.convert("RGB") as rgb:
                            with ImageOps.contain(
                                rgb, (CELL_WIDTH - 12, IMAGE_HEIGHT - 8), Image.Resampling.LANCZOS
                            ) as thumbnail:
                                sheet.paste(thumbnail, (
                                    left + (CELL_WIDTH - thumbnail.width) // 2,
                                    top + (IMAGE_HEIGHT - thumbnail.height) // 2,
                                ))
            except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
                failures.append((record["image_path"], f"{type(error).__name__}: {error}"))
                draw.text((left + 10, top + 70), "IMAGE LOAD FAILED", font=label_font, fill="red")
            filename = Path(record["image_path"]).name
            lines = textwrap.wrap(filename, width=29)
            if len(lines) > 3:
                raise ValueError(f"Filename too long for contact-sheet label: {filename}")
            draw.multiline_text(
                (left + 7, top + IMAGE_HEIGHT + 4),
                f"{index + 1:02d}: " + "\n".join(lines),
                font=label_font, fill="black", spacing=2,
            )
        sheet.save(OUTPUT_DIR / f"{species}.jpg", quality=95, subsampling=0)
        sheet.close()

    print("=== C1 LABEL REVIEW SHEETS ===")
    print(f"Species sheets: {len(grouped)}")
    print(f"Sample images: {len(records)}")
    print(f"Image loading failures: {len(failures)}")
    print(f"Output folder: {OUTPUT_DIR}")
    print("Original images modified: 0")
    print("===============================")
    for image_path, error in failures:
        print(f"FAILED {image_path}: {error}")


if __name__ == "__main__":
    main()

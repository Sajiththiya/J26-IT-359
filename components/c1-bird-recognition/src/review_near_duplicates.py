"""Display the first five distance-0 candidate pairs for manual review."""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPONENT_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = COMPONENT_DIR / "data" / "reports"
INPUT_CSV = REPORT_DIR / "near_duplicates.csv"
OUTPUT_PNG = REPORT_DIR / "duplicate_review_sample.png"
SAMPLE_SIZE = 5


def load_image(relative_path: str) -> Image.Image:
    with Image.open(PROJECT_ROOT / relative_path) as img:
        with ImageOps.exif_transpose(img) as corrected:
            return corrected.convert("RGB")


def main() -> None:
    if not INPUT_CSV.is_file():
        raise FileNotFoundError(INPUT_CSV)
    with INPUT_CSV.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {"image_path_a", "image_path_b", "phash_distance"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Required CSV columns missing")
        candidates = [
            row for row in reader if int(row["phash_distance"]) == 0
        ][:SAMPLE_SIZE]

    if not candidates:
        print("No distance-0 candidate pairs found.")
        return

    fig, axes = plt.subplots(
        len(candidates), 2, figsize=(12, 3.5 * len(candidates)), squeeze=False
    )
    try:
        for index, pair in enumerate(candidates):
            for column, key in enumerate(("image_path_a", "image_path_b")):
                with load_image(pair[key]) as image:
                    axes[index, column].imshow(image)
                axes[index, column].axis("off")
                side = "A" if column == 0 else "B"
                filename = Path(pair[key]).name
                axes[index, column].set_title(
                    f"Pair {index + 1} - Image {side}\n{filename}", fontsize=10
                )
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        fig.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight")
    finally:
        plt.close(fig)

    print("=== VISUAL DUPLICATE REVIEW ===")
    print(f"Pairs displayed: {len(candidates)}")
    print(f"Image saved to: {OUTPUT_PNG}")
    print("Original bird images were not modified.")


if __name__ == "__main__":
    main()

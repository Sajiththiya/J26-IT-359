"""Back up the label review and synchronize only its split column."""

import csv
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "components/c1-bird-recognition/data/reports"
REVIEW = REPORTS / "label_review_sample.csv"
SPLITS = REPORTS / "dataset_splits.csv"
BACKUP = REPORTS / "label_review_sample_before_split_sync.csv"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader), reader.fieldnames


def normalize(path):
    return path.replace("\\", "/")


def main():
    review_rows, columns = read_csv(REVIEW)
    split_rows, split_columns = read_csv(SPLITS)
    if not review_rows:
        raise ValueError("Review CSV is empty")
    required = {"image_path", "split", "review_status", "review_notes"}
    if not required.issubset(columns or []):
        raise ValueError("Missing required review columns")
    if not {"image_path", "split"}.issubset(split_columns or []):
        raise ValueError("Missing required split-manifest columns")

    lookup = {}
    for row in split_rows:
        key = normalize(row["image_path"])
        if not key or key in lookup:
            raise ValueError(f"Empty or duplicate split-manifest image path: {key}")
        if row["split"] not in {"train", "val", "test", "excluded"}:
            raise ValueError(f"Invalid split value for {key}: {row['split']}")
        lookup[key] = row["split"]

    seen = set()
    missing = []
    updated_rows = []
    updates = 0
    for row in review_rows:
        key = normalize(row["image_path"])
        if not key or key in seen:
            raise ValueError(f"Empty or duplicate review image path: {key}")
        seen.add(key)
        updated = dict(row)
        if key not in lookup:
            missing.append(key)
        else:
            updates += row["split"] != lookup[key]
            updated["split"] = lookup[key]
        updated_rows.append(updated)
    if missing:
        raise ValueError(f"Missing split records ({len(missing)}): {missing}")

    # Preserve the original checkpoint; never overwrite an existing backup.
    if BACKUP.exists():
        raise FileExistsError(f"Backup already exists; no changes made: {BACKUP}")
    original = REVIEW.read_bytes()
    shutil.copy2(REVIEW, BACKUP)
    if BACKUP.read_bytes() != original:
        raise ValueError("Backup verification failed; review CSV was not changed")

    # Fully serialize and verify before replacing the review file.
    temporary = None
    try:
        encoding = "utf-8-sig" if original.startswith(b"\xef\xbb\xbf") else "utf-8"
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding=encoding,
            dir=REPORTS, prefix="label_review_split_sync_", suffix=".tmp", delete=False,
        ) as file:
            temporary = Path(file.name)
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(updated_rows)
        saved_rows, saved_columns = read_csv(temporary)
        if saved_columns != columns or saved_rows != updated_rows:
            raise ValueError("Serialized review CSV failed verification")
        for before, after in zip(review_rows, saved_rows):
            if any(before[key] != after[key] for key in columns if key != "split"):
                raise ValueError("A field other than split changed; review CSV not replaced")
        os.replace(temporary, REVIEW)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

    flagged = Counter(
        row["split"] for row in updated_rows
        if row["review_status"] == "needs_expert_review"
    )
    print("=== C1 REVIEW SPLIT SYNC ===")
    print(f"Review records: {len(updated_rows)}")
    print(f"Split assignments updated: {updates}")
    print(f"Missing split records: {len(missing)}")
    print(f"Backup: {BACKUP}")
    print("Review decisions and notes preserved")
    print(f"Expert-review images: train={flagged['train']}, val={flagged['val']}, test={flagged['test']}")
    print("Original bird images modified: 0")
    print("============================")


if __name__ == "__main__":
    main()

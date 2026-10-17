"""Create a valid-image manifest with exact duplicate entries removed."""

import csv
from collections import Counter
from pathlib import Path


COMPONENT_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = COMPONENT_DIR / "data" / "reports"
INPUT_FILE = REPORT_DIR / "image_manifest.csv"
OUTPUT_FILE = REPORT_DIR / "clean_manifest.csv"
EXPECTED_COLUMNS = {"species", "image_path", "sha256", "status"}


def main() -> None:
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(f"Audit manifest not found: {INPUT_FILE}")

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        if not EXPECTED_COLUMNS.issubset(set(fieldnames or [])):
            raise ValueError("Missing required manifest columns")
        records = list(reader)

    valid_records = [row for row in records if row["status"] == "valid"]
    seen_digests: dict[str, str] = {}
    clean_records: list[dict[str, str]] = []
    duplicates_removed = 0

    for row in valid_records:
        digest = row["sha256"].strip().lower()
        if not digest:
            raise ValueError(
                f"Valid image has no SHA-256 hash: {row['image_path']}"
            )

        species = row["species"]
        previous_species = seen_digests.get(digest)
        if previous_species is not None:
            if previous_species != species:
                raise ValueError(
                    "Exact duplicate hash appears under different species "
                    f"labels: {row['image_path']} ({species}) conflicts "
                    f"with {previous_species}"
                )
            duplicates_removed += 1
            continue

        seen_digests[digest] = species
        clean_records.append(row)

    with OUTPUT_FILE.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean_records)

    species_counts = Counter(row["species"] for row in clean_records)
    for species in sorted(species_counts, key=str.casefold):
        print(f"{species}: {species_counts[species]}")

    print(f"Total eligible images: {len(clean_records)}")
    print(f"Exact duplicate entries removed: {duplicates_removed}")
    print(f"Non-valid images excluded: {len(records) - len(valid_records)}")
    print(f"Clean manifest saved to: {OUTPUT_FILE}")
    print("Original images were not modified.")


if __name__ == "__main__":
    main()

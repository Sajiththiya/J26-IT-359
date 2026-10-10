"""Read-only audit of the C1 bird image dataset."""

import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, UnidentifiedImageError


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "components" / "c1-bird-recognition" / "data"
RAW_DIR = DATA_DIR / "raw"
REPORT_DIR = DATA_DIR / "reports"
METADATA_FILENAME = "metadata.csv"
EXPECTED_SPECIES = {
    "Ashy-headed_Laughingthrush",
    "Chestnut-backed_Owlet",
    "Green-billed_Coucal",
    "Spot-winged_Thrush",
    "Sri_Lanka_Blue_Magpie",
    "Sri_Lanka_Frogmouth",
    "Sri_Lanka_Hanging_Parrot",
    "Sri_Lanka_Junglefowl",
    "Sri_Lanka_Spurfowl",
    "Yellow-fronted_Barbet",
}
UNSUPPORTED_IMAGE_EXTENSIONS = {
    ".arw",
    ".avif",
    ".cr2",
    ".dng",
    ".heic",
    ".heif",
    ".jxl",
    ".nef",
    ".orf",
    ".raf",
    ".raw",
    ".rw2",
}
PIL_IMAGE_EXTENSIONS = {
    extension.lower() for extension in Image.registered_extensions()
}
IMAGE_EXTENSIONS = PIL_IMAGE_EXTENSIONS | UNSUPPORTED_IMAGE_EXTENSIONS
CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_image(species: str, image_path: Path) -> dict[str, str | int]:
    relative_path = image_path.relative_to(PROJECT_ROOT).as_posix()
    extension = image_path.suffix.lower()
    record: dict[str, str | int] = {
        "species": species,
        "image_path": relative_path,
        "extension": extension,
        "width": "",
        "height": "",
        "format": "",
        "sha256": "",
        "status": "unsupported",
        "error": "",
    }
    errors: list[str] = []

    if extension in PIL_IMAGE_EXTENSIONS:
        try:
            with Image.open(image_path) as image:
                record["width"], record["height"] = image.size
                record["format"] = image.format or ""
                image.verify()
            record["status"] = "valid"
        except (
            Image.DecompressionBombError,
            OSError,
            SyntaxError,
            UnidentifiedImageError,
            ValueError,
        ) as error:
            record["status"] = "corrupt"
            errors.append(f"{type(error).__name__}: {error}")

    try:
        record["sha256"] = sha256_file(image_path)
    except OSError as error:
        errors.append(f"SHA-256 failed: {type(error).__name__}: {error}")

    record["error"] = "; ".join(errors)
    return record


def write_csv(
    filename: str,
    fieldnames: list[str],
    rows: list[dict[str, str | int]],
) -> None:
    with (REPORT_DIR / filename).open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def audit_dataset() -> None:
    if not RAW_DIR.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {RAW_DIR}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str | int]] = []
    unexpected_items: list[dict[str, str]] = []
    class_directories = sorted(
        (path for path in RAW_DIR.iterdir() if path.is_dir()),
        key=lambda path: path.name.casefold(),
    )

    for path in RAW_DIR.iterdir():
        if path.is_file():
            unexpected_items.append(
                {
                    "item_type": "file",
                    "path": path.relative_to(PROJECT_ROOT).as_posix(),
                    "reason": "Files must be inside a species folder.",
                }
            )
        elif path.is_dir() and path.name not in EXPECTED_SPECIES:
            unexpected_items.append(
                {
                    "item_type": "folder",
                    "path": path.relative_to(PROJECT_ROOT).as_posix(),
                    "reason": "Folder name is not an expected species class.",
                }
            )

    for species_dir in class_directories:
        for path in sorted(species_dir.rglob("*")):
            relative_path = path.relative_to(PROJECT_ROOT).as_posix()
            if path.is_dir():
                unexpected_items.append(
                    {
                        "item_type": "folder",
                        "path": relative_path,
                        "reason": "Nested folders are not part of the dataset layout.",
                    }
                )
                continue

            if path.parent != species_dir:
                unexpected_items.append(
                    {
                        "item_type": "file",
                        "path": relative_path,
                        "reason": "Files must be directly inside a species folder.",
                    }
                )
                continue

            if path.name.casefold() == METADATA_FILENAME:
                continue

            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                unexpected_items.append(
                    {
                        "item_type": "file",
                        "path": relative_path,
                        "reason": "File is not a recognized image or metadata.csv.",
                    }
                )
                continue

            records.append(audit_image(species_dir.name, path))

    hashes: dict[str, list[str]] = defaultdict(list)
    species_names = EXPECTED_SPECIES | {
        species_dir.name for species_dir in class_directories
    }
    counts_by_species: dict[str, Counter[str]] = {
        species: Counter() for species in species_names
    }
    for record in records:
        counts_by_species[str(record["species"])][str(record["status"])] += 1
        digest = str(record["sha256"])
        if digest:
            hashes[digest].append(str(record["image_path"]))

    summary: list[dict[str, str | int]] = []
    for species in sorted(counts_by_species, key=str.casefold):
        counts = counts_by_species[species]
        summary.append(
            {
                "species": species,
                "total": sum(counts.values()),
                "valid": counts["valid"],
                "corrupt": counts["corrupt"],
                "unsupported": counts["unsupported"],
            }
        )
        print(
            f"{species}: {sum(counts.values())} images "
            f"({counts['valid']} valid, {counts['corrupt']} corrupt, "
            f"{counts['unsupported']} unsupported)"
        )

    duplicate_groups = [
        paths for paths in hashes.values() if len(paths) > 1
    ]
    duplicate_rows = [
        {"sha256": digest, "image_path": path}
        for digest, paths in hashes.items()
        if len(paths) > 1
        for path in paths
    ]

    write_csv(
        "image_manifest.csv",
        [
            "species",
            "image_path",
            "extension",
            "width",
            "height",
            "format",
            "sha256",
            "status",
            "error",
        ],
        records,
    )
    write_csv(
        "species_summary.csv",
        ["species", "total", "valid", "corrupt", "unsupported"],
        summary,
    )
    write_csv(
        "exact_duplicates.csv",
        ["sha256", "image_path"],
        duplicate_rows,
    )
    write_csv(
        "unexpected_items.csv",
        ["item_type", "path", "reason"],
        unexpected_items,
    )

    empty_classes = [row["species"] for row in summary if row["total"] == 0]
    print("\n=== AUDIT COMPLETE ===")
    print(f"Total image files audited: {len(records)}")
    print(f"Exact duplicate groups: {len(duplicate_groups)}")
    print(f"Unexpected files/folders: {len(unexpected_items)}")
    if empty_classes:
        print(f"Empty classes: {', '.join(str(name) for name in empty_classes)}")
    print(f"Reports saved in: {REPORT_DIR}")
    print("No original images were modified.")


if __name__ == "__main__":
    audit_dataset()

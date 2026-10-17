"""Combine image inventory, exact exclusions, candidate groups and manual links.

Only the master CSV is written. Similarity relationships are conservative
grouping constraints, not confirmed duplicate decisions. Splits remain
unassigned; image-quality, label and source/session review are separate.
"""

import csv
import hashlib
from collections import defaultdict
from pathlib import Path

from build_similarity_groups import UnionFind


ROOT = Path(__file__).resolve().parents[3]
COMPONENT = ROOT / "components/c1-bird-recognition"
RAW = COMPONENT / "data/raw"
REPORTS = COMPONENT / "data/reports"
EXCLUSIONS = REPORTS / "exact_duplicate_exclusions.csv"
SIMILARITY = REPORTS / "similarity_groups.csv"
MANUAL_LINKS = REPORTS / "manual_similarity_links.csv"
OUTPUT = REPORTS / "master_dataset_manifest.csv"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
FIELDS = [
    "image_path", "species", "sha256", "exclude", "exclusion_reason",
    "keep_image_path", "similarity_group_id", "group_id", "group_size", "split",
]


def read_report(path, required):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing required columns in {path}: {sorted(required)}")
        return list(reader)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    exclusions = read_report(
        EXCLUSIONS, {"image_path", "keep_image_path", "sha256", "reason"}
    )
    similarity = read_report(SIMILARITY, {"group_id", "image_path", "species"})
    if not RAW.is_dir():
        raise FileNotFoundError(f"Raw dataset not found: {RAW}")
    paths = sorted(
        path for path in RAW.rglob("*")
        if path.is_file() and path.suffix.lower() in EXTENSIONS
    )
    if not paths:
        raise ValueError("No original images found; refusing to write an empty manifest.")

    uf = UnionFind()
    records = {}
    hash_groups = defaultdict(list)
    for path in paths:
        relative = path.relative_to(RAW)
        if len(relative.parts) < 2:
            raise ValueError(f"Image has no species folder: {path}")
        image_path = path.relative_to(ROOT).as_posix()
        digest = sha256_file(path)
        records[image_path] = {
            "image_path": image_path,
            "species": relative.parts[0],
            "sha256": digest,
            "exclude": False,
            "exclusion_reason": "",
            "keep_image_path": "",
            "similarity_group_id": "",
            "split": "unassigned",
        }
        uf.find(image_path)
        hash_groups[digest].append(image_path)

    # Include all byte-identical relationships, including excluded originals.
    for members in hash_groups.values():
        for member in members[1:]:
            uf.union(members[0], member)

    excluded_paths = set()
    for row in exclusions:
        image_path, keeper = row["image_path"], row["keep_image_path"]
        if image_path not in records or keeper not in records:
            raise ValueError(f"Exclusion references an unknown image: {row}")
        if image_path == keeper or image_path in excluded_paths:
            raise ValueError(f"Self-reference or repeated exclusion: {image_path}")
        if row["reason"] != "exact_sha256_duplicate":
            raise ValueError(f"Unexpected exclusion reason: {row['reason']}")
        if not (records[image_path]["sha256"] == records[keeper]["sha256"] == row["sha256"]):
            raise ValueError(f"Exclusion SHA-256 mismatch: {image_path}")
        excluded_paths.add(image_path)
        records[image_path].update(
            exclude=True, exclusion_reason=row["reason"], keep_image_path=keeper
        )
        uf.union(image_path, keeper)
    if any(row["keep_image_path"] in excluded_paths for row in exclusions):
        raise ValueError("An exclusion keeper is itself excluded.")

    candidate_groups = defaultdict(list)
    for row in similarity:
        image_path, group_id = row["image_path"], row["group_id"]
        if image_path not in records or not group_id:
            raise ValueError(f"Invalid similarity report entry: {row}")
        record = records[image_path]
        if record["similarity_group_id"] or record["species"] != row["species"]:
            raise ValueError(f"Repeated image or species mismatch: {image_path}")
        record["similarity_group_id"] = group_id
        candidate_groups[group_id].append(image_path)
    for members in candidate_groups.values():
        members.sort()
        for member in members[1:]:
            uf.union(members[0], member)

    # Merge manually reviewed related images, retaining the separate audit CSV.
    manual_links = read_report(
        MANUAL_LINKS, {"image_path_a", "image_path_b", "reason", "review_status"}
    )
    for row in manual_links:
        if row["review_status"] != "reviewed":
            continue
        image_a = Path(row["image_path_a"].replace("\\", "/")).as_posix()
        image_b = Path(row["image_path_b"].replace("\\", "/")).as_posix()
        if image_a not in records:
            raise ValueError(f"Missing image: {image_a}")
        if image_b not in records:
            raise ValueError(f"Missing image: {image_b}")
        if image_a == image_b:
            raise ValueError("Manual similarity self-link")
        if records[image_a]["species"] != records[image_b]["species"]:
            raise ValueError("Cross-species manual link")
        uf.union(image_a, image_b)

    connected = defaultdict(list)
    for image_path in sorted(records):
        connected[uf.find(image_path)].append(image_path)
    groups = sorted(connected.values(), key=lambda members: members[0])
    for index, members in enumerate(groups, start=1):
        for image_path in members:
            records[image_path].update(
                group_id=f"GROUP_{index:05d}", group_size=len(members)
            )

    REPORTS.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records[path] for path in sorted(records))

    print("=== C1 MASTER DATASET MANIFEST ===")
    print(f"Total image records: {len(records)}")
    print(f"Species: {len({record['species'] for record in records.values()})}")
    print(f"Excluded images: {len(excluded_paths)}")
    print(f"Eligible images: {len(records) - len(excluded_paths)}")
    print(f"Connected groups: {len(groups)}")
    print("Split status: unassigned")
    print("Original images modified: 0")
    print(f"Manifest: {OUTPUT}")
    print("==================================")


if __name__ == "__main__":
    main()

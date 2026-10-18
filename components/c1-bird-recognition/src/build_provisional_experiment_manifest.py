"""Record provisional whole-group quarantines without changing candidate splits.

Quarantine is temporary and does not establish that an image is mislabeled.
Included images have not all received independent species verification.
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "components/c1-bird-recognition/data/reports"
SPLITS = REPORTS / "dataset_splits.csv"
QUEUE = REPORTS / "expert_review_queue.csv"
OUTPUT = REPORTS / "experiment_manifest_provisional.csv"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader), reader.fieldnames


def normalize(path):
    return path.replace("\\", "/")


def excluded(row):
    return row.get("exclude", "False").strip().lower() in {"true", "1", "yes"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"Output already exists; refusing to overwrite: {OUTPUT}")
    splits, columns = read_csv(SPLITS)
    queue, queue_columns = read_csv(QUEUE)
    require(
        {"image_path", "species", "split", "exclude", "group_id"}.issubset(columns or []),
        "Required split columns missing",
    )
    require(
        {"image_path", "species", "split", "review_status"}.issubset(queue_columns or []),
        "Required expert-review queue columns missing",
    )
    require("experiment_status" not in columns, "Input already has experiment_status")
    require(len(splits) == 5454, f"Expected 5454 original records, found {len(splits)}")
    require(len(queue) == 11, f"Expected 11 expert-review flags, found {len(queue)}")

    lookup = {}
    group_splits = defaultdict(set)
    for row in splits:
        key = normalize(row["image_path"])
        require(key and key not in lookup, f"Empty or duplicate split image path: {key}")
        require(row["group_id"].strip(), f"Missing group ID: {key}")
        require(row["species"].strip(), f"Missing species: {key}")
        flag = row["exclude"].strip().lower()
        require(flag in {"true", "1", "yes", "false", "0", "no"}, f"Invalid exclude flag: {key}")
        if excluded(row):
            require(row["split"] == "excluded", f"Excluded image in experiment split: {key}")
        else:
            require(row["split"] in {"train", "val", "test"}, f"Invalid eligible split: {key}")
            group_splits[row["group_id"]].add(row["split"])
        lookup[key] = row
    require(all(len(values) == 1 for values in group_splits.values()), "Candidate group leakage found")

    flagged_paths = set()
    flagged_groups = set()
    for row in queue:
        key = normalize(row["image_path"])
        require(key not in flagged_paths, f"Repeated expert-review image: {key}")
        require(key in lookup, f"Expert-review image missing from splits: {key}")
        source = lookup[key]
        require(row["review_status"] == "needs_expert_review", f"Unexpected review status: {key}")
        require(not excluded(source), f"Flagged image already exactly excluded: {key}")
        require(row["species"] == source["species"], f"Queue species mismatch: {key}")
        require(row["split"] == source["split"], f"Outdated queue split: {key}")
        flagged_paths.add(key)
        flagged_groups.add(source["group_id"])
    require(len(flagged_groups) == 11, "Expected 11 affected similarity groups")

    output_rows = []
    statuses = Counter()
    included_splits = Counter()
    quarantined_splits = Counter()
    for row in splits:
        if excluded(row):
            status = "exclude_exact_duplicate"
        elif row["group_id"] in flagged_groups:
            status = "quarantine_expert_review"
            quarantined_splits[row["split"]] += 1
        else:
            status = "include"
            included_splits[row["split"]] += 1
        output_rows.append({**row, "experiment_status": status})
        statuses[status] += 1

    require(
        statuses == {"include": 5420, "quarantine_expert_review": 19, "exclude_exact_duplicate": 15},
        f"Unexpected experiment status counts: {dict(statuses)}",
    )
    require(
        included_splits == {"train": 3792, "val": 814, "test": 814},
        f"Unexpected included split counts: {dict(included_splits)}",
    )
    require(
        quarantined_splits == {"train": 14, "val": 5},
        f"Unexpected quarantine split counts: {dict(quarantined_splits)}",
    )
    # Exclusive creation also guards against a file appearing after initial checks.
    with OUTPUT.open("x", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns + ["experiment_status"])
        writer.writeheader()
        writer.writerows(output_rows)

    print("=== C1 PROVISIONAL EXPERIMENT MANIFEST ===")
    print(f"Total records: {len(output_rows)}")
    print(f"Include: {statuses['include']}")
    print(f"Quarantine: {statuses['quarantine_expert_review']}")
    print(f"Exact duplicate exclusions: {statuses['exclude_exact_duplicate']}")
    print(f"Training: {included_splits['train']}")
    print(f"Validation: {included_splits['val']}")
    print(f"Testing: {included_splits['test']}")
    print("Original images modified: 0")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()

"""Independently validate the provisional experiment CSV without writing files.

This checks manifest integrity and recorded grouping constraints, not image
content, species correctness or undiscovered photographic relationships.
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "components/c1-bird-recognition/data/reports"
SPLITS = REPORTS / "dataset_splits.csv"
QUEUE = REPORTS / "expert_review_queue.csv"
EXPERIMENT = REPORTS / "experiment_manifest_provisional.csv"


def check(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path, required):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []
        check(len(columns) == len(set(columns)), f"Repeated CSV columns: {path}")
        check(required.issubset(columns), f"Missing required columns: {path}")
        rows = list(reader)
    check(rows, f"Empty CSV: {path}")
    check(all(None not in row and None not in row.values() for row in rows), f"Malformed CSV rows: {path}")
    return rows, columns


def index_paths(rows, name):
    indexed = {}
    for row in rows:
        path = row["image_path"].replace("\\", "/")
        check(path.strip() and path not in indexed, f"Empty or repeated image path in {name}: {path}")
        indexed[path] = row
    return indexed


def excluded(row):
    value = row["exclude"].strip().lower()
    check(value in {"true", "1", "yes", "false", "0", "no"}, "Invalid exclusion flag")
    return value in {"true", "1", "yes"}


def main():
    required = {"image_path", "species", "group_id", "split", "exclude"}
    split_rows, split_columns = read_csv(SPLITS, required)
    experiment_rows, experiment_columns = read_csv(
        EXPERIMENT, required | {"experiment_status"}
    )
    queue_rows, _ = read_csv(
        QUEUE, {"image_path", "species", "split", "review_status"}
    )
    check("experiment_status" not in split_columns, "Source already has experiment status")
    check(
        set(experiment_columns) == set(split_columns) | {"experiment_status"},
        "Experiment columns differ from source plus experiment_status",
    )
    original = index_paths(split_rows, "candidate splits")
    updated = index_paths(experiment_rows, "experiment manifest")
    flags = index_paths(queue_rows, "expert-review queue")
    check(len(original) == 5454, f"Expected 5454 source records, found {len(original)}")
    check(original.keys() == updated.keys(), "Source and experiment image-path sets differ")
    check(len(flags) == 11, f"Expected 11 expert-review flags, found {len(flags)}")

    flagged_groups = set()
    for path, row in flags.items():
        check(path in original, f"Flagged image missing from source: {path}")
        source = original[path]
        check(row["review_status"] == "needs_expert_review", f"Unexpected review status: {path}")
        check(not excluded(source), f"Flagged image already excluded: {path}")
        check(row["species"] == source["species"], f"Flagged species mismatch: {path}")
        check(row["split"] == source["split"], f"Outdated queue split: {path}")
        check(source["group_id"].strip(), f"Missing flagged group ID: {path}")
        flagged_groups.add(source["group_id"])
    check(len(flagged_groups) == 11, "Expected 11 expert-review groups")

    counts = Counter()
    include_splits = Counter()
    group_splits = defaultdict(set)
    field_errors = []
    status_errors = []
    for path, source in original.items():
        result = updated[path]
        for column in split_columns:
            if source[column] != result[column]:
                field_errors.append(f"Changed {column}: {path}")
        check(source["group_id"].strip(), f"Missing source group ID: {path}")
        if excluded(source):
            check(source["split"] == "excluded", f"Exact exclusion assigned to experiment split: {path}")
            expected = "exclude_exact_duplicate"
        else:
            check(source["split"] in {"train", "val", "test"}, f"Invalid eligible split: {path}")
            expected = (
                "quarantine_expert_review"
                if source["group_id"] in flagged_groups else "include"
            )
        actual = result["experiment_status"]
        if actual != expected:
            status_errors.append(f"Incorrect status ({actual}; expected {expected}): {path}")
        counts[actual] += 1
        if actual == "include":
            include_splits[result["split"]] += 1
            group_splits[result["group_id"]].add(result["split"])

    leaking_groups = {group: values for group, values in group_splits.items() if len(values) > 1}
    errors = field_errors + status_errors
    check(not errors, "\n".join(errors[:20]))
    check(not leaking_groups, f"Group leakage: {leaking_groups}")
    check(
        counts == {"include": 5420, "quarantine_expert_review": 19, "exclude_exact_duplicate": 15},
        f"Unexpected experiment status counts: {dict(counts)}",
    )
    check(
        include_splits == {"train": 3792, "val": 814, "test": 814},
        f"Unexpected included split counts: {dict(include_splits)}",
    )
    print("=== C1 EXPERIMENT MANIFEST VALIDATION ===")
    print("Source records preserved:", len(original))
    print("Original fields changed:", len(field_errors))
    print("Expert-review groups:", len(flagged_groups))
    print("Included images:", counts["include"])
    print("Quarantined images:", counts["quarantine_expert_review"])
    print("Exact duplicate exclusions:", counts["exclude_exact_duplicate"])
    print("Training:", include_splits["train"])
    print("Validation:", include_splits["val"])
    print("Testing:", include_splits["test"])
    print("Leaking included similarity groups:", len(leaking_groups))
    print("VALIDATION: PASS")
    print("========================================")


if __name__ == "__main__":
    main()

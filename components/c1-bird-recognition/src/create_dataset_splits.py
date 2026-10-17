"""Create a reproducible candidate split without changing images or master CSV.

Groups are indivisible. Per-species 70/15/15 ratios are targets, not strict
quotas. This guards only the relationships already recorded in the master
manifest; label, quality and source/session review remain necessary.
"""

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPONENT = PROJECT_ROOT / "components/c1-bird-recognition"
INPUT = COMPONENT / "data/reports/master_dataset_manifest.csv"
OUTPUT = COMPONENT / "data/reports/dataset_splits.csv"
SEED = 42
SPLITS = ("train", "val", "test")
RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}
TRIALS = 100


def assign_species_groups(groups, rng):
    """Try largest-first greedy allocations; retain the closest image counts.

Each trial randomizes ties among equal-sized groups. The score is the sum
of squared image-count deviations from the three per-species targets.
"""
    if len(groups) < len(SPLITS):
        raise ValueError("Each species needs at least three eligible groups.")
    total = sum(len(members) for members in groups.values())
    targets = {split: total * RATIOS[split] for split in SPLITS}
    best = None
    best_score = float("inf")
    for _ in range(TRIALS):
        ordered = sorted(groups)
        rng.shuffle(ordered)
        ordered.sort(key=lambda group: -len(groups[group]))
        counts = Counter()
        assignment = {}
        for group in ordered:
            size = len(groups[group])
            # Choose the placement that most reduces squared target error.
            split = min(
                SPLITS,
                key=lambda name: (
                    (counts[name] + size - targets[name]) ** 2
                    - (counts[name] - targets[name]) ** 2
                ),
            )
            assignment[group] = split
            counts[split] += size
        score = sum((counts[split] - targets[split]) ** 2 for split in SPLITS)
        if all(counts[split] for split in SPLITS) and score < best_score:
            best, best_score = assignment, score
    if best is None:
        raise ValueError("Could not represent this species in every partition.")
    return best


def main():
    with INPUT.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        fields = reader.fieldnames
        required = {"image_path", "species", "exclude", "group_id", "split"}
        if not required.issubset(fields or []):
            raise ValueError("Master manifest is missing required columns.")
        rows = sorted(reader, key=lambda row: row["image_path"])
    if not rows:
        raise ValueError("Master manifest is empty")
    if len({row["image_path"] for row in rows}) != len(rows):
        raise ValueError("Duplicate image paths found")

    group_species = defaultdict(set)
    for row in rows:
        if not all(row[key].strip() for key in ("image_path", "species", "group_id")):
            raise ValueError("Empty image path, species or group ID.")
        if row["exclude"].lower() not in {"true", "false"}:
            raise ValueError(f"Invalid exclusion flag: {row['image_path']}")
        if row["split"] != "unassigned":
            raise ValueError("Master split values must remain unassigned.")
        group_species[row["group_id"]].add(row["species"])
    if any(len(species) != 1 for species in group_species.values()):
        raise ValueError("A group spans multiple species; review before stratifying.")

    eligible = [row for row in rows if row["exclude"].lower() == "false"]
    excluded = len(rows) - len(eligible)
    if len(eligible) != 5439:
        raise ValueError(f"Expected 5439 eligible images, found {len(eligible)}")
    if len(rows) != 5454 or excluded != 15:
        raise ValueError("Expected 5454 original records and 15 excluded images.")
    by_species = defaultdict(lambda: defaultdict(list))
    for row in eligible:
        by_species[row["species"]][row["group_id"]].append(row)
    if len(by_species) != 10:
        raise ValueError(f"Expected 10 eligible species, found {len(by_species)}")

    rng = random.Random(SEED)
    assignments = {}
    for species, groups in sorted(by_species.items()):
        assignments.update(assign_species_groups(groups, rng))

    counts = Counter()
    per_species = defaultdict(Counter)
    group_splits = defaultdict(set)
    for row in rows:
        split = "excluded" if row["exclude"].lower() == "true" else assignments[row["group_id"]]
        row["split"] = split
        counts[split] += 1
        per_species[row["species"]][split] += 1
        if split in SPLITS:
            group_splits[row["group_id"]].add(split)
    leaking = sum(len(splits) > 1 for splits in group_splits.values())
    if leaking:
        raise ValueError(f"Refusing to save: {leaking} leaking similarity groups.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print("=== C1 DATASET SPLIT RESULTS ===")
    print(f"Random seed: {SEED}")
    print(f"Trials per species: {TRIALS}")
    print(f"Train: {counts['train']}")
    print(f"Validation: {counts['val']}")
    print(f"Test: {counts['test']}")
    print(f"Excluded: {counts['excluded']}")
    print(f"Leaking similarity groups: {leaking}")
    print(f"Species: {len(by_species)}")
    print("\n=== PER-SPECIES DISTRIBUTION ===")
    print(f"{'Species':<30} {'Train':>6} {'Val':>6} {'Test':>6} {'Eligible':>9} {'Excluded':>9}")
    for species, tally in sorted(per_species.items()):
        total = sum(tally[split] for split in SPLITS)
        print(
            f"{species:<30} {tally['train']:>6} {tally['val']:>6} "
            f"{tally['test']:>6} {total:>9} {tally['excluded']:>9}"
        )
    print(f"\nCandidate split saved: {OUTPUT}")
    print("Excluded records have split=excluded and are outside train/val/test.")
    print("Master manifest and original images were not modified.")


if __name__ == "__main__":
    main()

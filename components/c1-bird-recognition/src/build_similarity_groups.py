"""Group connected near-duplicate candidates without modifying source images.

Only images appearing in near_duplicates.csv are included. Groups express
candidate similarity, not confirmed duplicates. Cross-species auditing and
exact-duplicate integration remain separate steps before dataset splitting.
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
COMPONENT = ROOT / "components" / "c1-bird-recognition"
INPUT = COMPONENT / "data/reports/near_duplicates.csv"
OUTPUT = COMPONENT / "data/reports/similarity_groups.csv"


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while x != root:
            parent = self.parent[x]
            self.parent[x] = root
            x = parent
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def main():
    uf = UnionFind()
    with INPUT.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"image_path_a", "image_path_b"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Required CSV columns missing: image_path_a, image_path_b")
        rows = list(reader)

    for index, row in enumerate(rows, start=2):
        a, b = row["image_path_a"], row["image_path_b"]
        if not a or not b:
            raise ValueError(f"Empty image path at CSV row {index}")
        uf.union(a, b)

    groups = defaultdict(list)
    for image_path in sorted(uf.parent):
        groups[uf.find(image_path)].append(image_path)

    # Sorted components and members make IDs reproducible for the same graph,
    # even if input pair order or the A/B ordering changes.
    ordered_groups = sorted(groups.values(), key=lambda paths: paths[0])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["group_id", "image_path", "species", "group_size"]
        )
        writer.writeheader()
        for index, paths in enumerate(ordered_groups, start=1):
            for image_path in paths:
                writer.writerow({
                    "group_id": f"similarity_{index:05d}",
                    "image_path": image_path,
                    "species": Path(image_path).parent.name,
                    "group_size": len(paths),
                })

    sizes = Counter(len(paths) for paths in ordered_groups)
    print("=== CANDIDATE SIMILARITY GROUPS ===")
    print(f"Input candidate pairs: {len(rows)}")
    print(f"Unique images grouped: {len(uf.parent)}")
    print(f"Candidate similarity groups: {len(ordered_groups)}")
    print(f"Largest group size: {max(sizes, default=0)}")
    print("Group size distribution (images per group: number of groups):")
    for size, count in sorted(sizes.items()):
        print(f"  {size}: {count}")
    print(f"Report saved: {OUTPUT}")
    print("Only images appearing in the candidate-pair CSV are included.")
    print("Original images were not modified. No dataset splits were created.")


if __name__ == "__main__":
    main()

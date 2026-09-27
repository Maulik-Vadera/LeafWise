"""Create deterministic splits, keeping physical-leaf groups and duplicates together."""
import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict, Counter
from pathlib import Path
from PIL import Image, ImageOps
from app.catalog import canonical

SPLITS = ("train", "val", "calibration", "test")

def prepare(csv_path, image_root, output, seed=42):
    root = Path(image_root).resolve()
    rows = list(csv.DictReader(Path(csv_path).open(newline="", encoding="utf-8-sig")))
    if not rows or not {"path", "label", "group"}.issubset(rows[0]):
        raise ValueError("CSV needs path,label,group columns. group must identify the physical leaf or plant, not an augmented image.")
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)
    group_labels, pixel_hashes, used_paths = {}, {}, set()
    clean = []
    for row in rows:
        path = (root / row["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"Image path must exist inside --root: {row['path']}")
        if str(path) in used_paths:
            continue
        used_paths.add(str(path))
        label, group = canonical(row["label"]), row["group"].strip()
        if not group:
            raise ValueError(f"Missing physical-leaf group: {path.name}")
        if group in group_labels and group_labels[group] != label:
            raise ValueError(f"Group has conflicting labels: {group}")
        group_labels[group] = label
        find(group)
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            digest = hashlib.sha256(str(im.size).encode() + im.tobytes()).hexdigest()
        if digest in pixel_hashes:
            other_group, other_label = pixel_hashes[digest]
            if label != other_label:
                raise ValueError(f"Identical image has contradictory labels: {path}")
            union(group, other_group)
        else:
            pixel_hashes[digest] = group, label
        clean.append({"path": str(path), "label": label, "group": group, "pixel_sha256": digest})
    groups_by_label = defaultdict(set)
    for row in clean:
        row["group"] = find(row["group"])
        groups_by_label[row["label"]].add(row["group"])
    mapping = {}
    rng = random.Random(seed)
    for label, values in sorted(groups_by_label.items()):
        groups = sorted(values)
        rng.shuffle(groups)
        n = len(groups)
        if n < 4:
            raise ValueError(f"{label} has only {n} independent groups. At least four are required; many more are needed for useful evaluation.")
        n_val = max(1, int(n * .15)); n_cal = max(1, int(n * .10)); n_test = max(1, int(n * .10))
        n_train = n - n_val - n_cal - n_test
        offset = 0
        for split, count in zip(SPLITS, [n_train, n_val, n_cal, n_test]):
            for group in groups[offset:offset + count]:
                mapping[group] = split
            offset += count
    for row in clean:
        row["split"] = mapping[row["group"]]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "label", "group", "pixel_sha256", "split"])
        writer.writeheader(); writer.writerows(clean)
    report = {"seed": seed, "images": len(clean), "groups": len(mapping),
              "counts": {split: dict(Counter(r["label"] for r in clean if r["split"] == split)) for split in SPLITS},
              "note": "Physical group boundaries are only as good as the supplied metadata. Exact pixel duplicates are merged; near duplicates need separate auditing."}
    output.with_suffix(".report.json").write_text(json.dumps(report, indent=2))
    return report

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", required=True); p.add_argument("--root", required=True)
    p.add_argument("--out", required=True); p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    print(json.dumps(prepare(a.csv, a.root, a.out, a.seed), indent=2))

if __name__ == "__main__":
    main()

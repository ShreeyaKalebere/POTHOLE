"""Table I - dataset summary, counted directly from image files and YOLO label .txt files.
Run: python paper_table1_dataset.py     Output: paper_results/table1_dataset.csv (+ printed)"""
import collections
import csv
import json
import re
from pathlib import Path

ROOT = Path("F:/POTHOLE_PROJECT")
D = ROOT / "dataset"
OUT = ROOT / "paper_results"


def count_split(img_dir, lbl_dir):
    imgs = [p for p in img_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    c = collections.Counter()
    for p in imgs:
        lp = lbl_dir / f"{p.stem}.txt"
        lines = [l.split() for l in lp.read_text().splitlines() if l.strip()] if lp.exists() else []
        if not lines:
            c["negative_images"] += 1
        for v in lines:
            c[f"class{v[0]}"] += 1
    c["images"] = len(imgs)
    return c


def main():
    rows = []
    # A) the base dataset used by v1 (dataset/data.yaml) and its clean subsets
    for name, splits in [("base dataset (data.yaml: v1-v7 val/test)", ["train", "val", "test"]),
                         ("v8 cleaned (data_v8.yaml)", ["train_clean", "val_clean"]),
                         ("clean test (data_cleantest.yaml)", ["test_clean"])]:
        for s in splits:
            c = count_split(D / "images" / s, D / "labels" / s)
            rows.append([name, s, c["images"], c["class0"], c["class1"], c["negative_images"]])
    # B) Kolhapur frame sets
    K = ROOT / "kolhapur_labeling"
    for s, lbl in [("train pool (morning rides)", K / "train/labels"), ("test pool (afternoon ride)", K / "test/labels")]:
        img_dir = K / s.split()[0] / "images"
        c = count_split(img_dir, lbl)
        rows.append(["Kolhapur frames - model pre-labels (NOT human-verified)", s, c["images"], c["class0"], c["class1"], c["negative_images"]])
    c = count_split(K / "train/images", K / "train_fixed/labels")
    rows.append(["Kolhapur train frames - reviewed labels (train_fixed, used in v7/v8)", "train pool", c["images"], c["class0"], c["class1"], c["negative_images"]])
    for s in ["train_kol_reviewed", "train_kol_v7"]:
        c = count_split(D / "images" / s, D / "labels" / s)
        rows.append(["Kolhapur images in training set (incl. 3x repeats)", s, c["images"], c["class0"], c["class1"], c["negative_images"]])

    OUT.mkdir(exist_ok=True)
    with open(OUT / "table1_dataset.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["set", "split", "images", "pothole_boxes(class0)", "alligator_crack_boxes(class1)", "negative_images(empty label)"])
        w.writerows(rows)
    for r in rows:
        print(r)

    # C) per-source contribution of the base dataset
    man = json.load(open(D / "manifest.json"))
    src = collections.defaultdict(collections.Counter)
    for m in man:
        key = "RDD2022 (all countries)" if m["source"].startswith("RDD2022") else m["source"]
        src[key][m["split"]] += 1
        src[key]["total"] += 1
    with open(OUT / "table1_sources.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["source", "train", "val", "test", "total"])
        for k, v in sorted(src.items(), key=lambda x: -x[1]["total"]):
            w.writerow([k, v["train"], v["val"], v["test"], v["total"]])
            print("source", k, dict(v))

    # D) dedup count from the dataset build report
    rep = (ROOT / "qa/dataset_report.md").read_text(encoding="utf-8")
    m = re.search(r"near-duplicate of another image \| (\d+)", rep)
    print("near-duplicates removed (automatic dHash, Hamming<=3):", m.group(1) if m else "not found")

    # E) Kolhapur video-level split check
    fr = list(csv.DictReader(open(K / "frames.csv")))
    vid_split = collections.defaultdict(set)
    for r in fr:
        vid_split[(r["person"], r["source_file"])].add(r["split"])
    mixed = [k for k, v in vid_split.items() if len(v) > 1]
    print("Kolhapur source files:", len(vid_split), "| files whose frames appear in >1 split:", len(mixed))


if __name__ == "__main__":
    main()

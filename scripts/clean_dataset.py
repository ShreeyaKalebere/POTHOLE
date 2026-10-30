"""
Builds a CLEANED copy of the training + validation data for v8.  The original dataset and the
TEST set are not changed, so v8 compares fairly with v1-v7.

Step 1  remove tiny boxes        (area < MIN_AREA of the image - too small to judge reliably)
Step 2  inconsistent sources     drop RDD Norway + RDD Czech; keep only 50% of RDD Japan (train)
Step 3  clear label errors       (using the v1 model)
          - duplicate boxes on the same damage (same class, IoU > 0.7) -> keep one
          - class swapped: model >= 0.70 sure it is the OTHER class at the same place (IoU > 0.5)
Step 4  (people) list of doubtful images -> qa/v8_doubtful.csv  for the team to check

Kolhapur frames with checked labels (kolhapur_labeling/train_fixed) are added like in v7.

Output: dataset/images|labels/{train_clean, val_clean, train_kol_v7} + dataset/data_v8.yaml
        qa/v8_cleaning_report.md
Run:    python clean_dataset.py
"""
import collections
import csv
import json
import os
import random
import shutil
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
D = ROOT / "dataset"
MIN_AREA = 0.001
DROP_SOURCES = {"RDD2022_Norway", "RDD2022_Czech"}
REDUCE = {"RDD2022_Japan": 0.5}          # keep this share of training images
CLASS_SWAP_CONF = 0.70
NAMES = ["pothole", "alligator_crack"]
random.seed(8)


def iou(a, b):
    ax1, ay1, ax2, ay2 = a[0] - a[2] / 2, a[1] - a[3] / 2, a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1, bx2, by2 = b[0] - b[2] / 2, b[1] - b[3] / 2, b[0] + b[2] / 2, b[1] + b[3] / 2
    ix, iy = max(0, min(ax2, bx2) - max(ax1, bx1)), max(0, min(ay2, by2) - max(ay1, by1))
    inter = ix * iy
    u = a[2] * a[3] + b[2] * b[3] - inter
    return inter / u if u else 0


def main():
    src_of = {Path(m["file"]).stem: m["source"] for m in json.load(open(D / "manifest.json"))}
    model = YOLO(str(ROOT / "runs/yolo11s_v1/weights/best.pt"))
    st = collections.Counter()
    per_src = collections.defaultdict(collections.Counter)
    doubtful = []

    for split in ("train", "val"):
        oi, ol = D / "images" / f"{split}_clean", D / "labels" / f"{split}_clean"
        for d in (oi, ol):
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True)
        for img in sorted((D / "images" / split).iterdir()):
            src = src_of.get(img.stem, "?")
            st[f"{split}_images_in"] += 1
            # ---- step 2: sources
            if src in DROP_SOURCES:
                st[f"{split}_images_dropped_source"] += 1
                continue
            if split == "train" and src in REDUCE and random.random() > REDUCE[src]:
                st["train_images_reduced_japan"] += 1
                continue
            lp = D / "labels" / split / f"{img.stem}.txt"
            boxes = []
            if lp.exists():
                for line in lp.read_text().splitlines():
                    v = line.split()
                    if len(v) == 5:
                        boxes.append([int(v[0])] + [float(x) for x in v[1:]])
            n0 = len(boxes)
            # ---- step 1: tiny boxes
            big = [b for b in boxes if b[3] * b[4] >= MIN_AREA]
            st[f"{split}_tiny_removed"] += n0 - len(big)
            per_src[src]["tiny_removed"] += n0 - len(big)
            boxes = big
            # ---- step 3a: duplicates
            keep = []
            for b in sorted(boxes, key=lambda b: -b[3] * b[4]):
                if any(k[0] == b[0] and iou(k[1:], b[1:]) > 0.7 for k in keep):
                    st[f"{split}_duplicates_removed"] += 1
                    continue
                keep.append(b)
            boxes = keep
            # ---- step 3b: class swaps (+ step 4 doubtful list)
            if boxes:
                r = model.predict(str(img), conf=0.25, verbose=False)[0]
                preds = [(int(c), float(p), [float(x) for x in xywh])
                         for c, p, xywh in zip(r.boxes.cls, r.boxes.conf, r.boxes.xywhn)]
                for b in boxes:
                    best = max(preds, key=lambda p: iou(p[2], b[1:]), default=None)
                    if best and iou(best[2], b[1:]) > 0.5 and best[0] != b[0]:
                        if best[1] >= CLASS_SWAP_CONF:
                            st[f"{split}_class_fixed"] += 1
                            b[0] = best[0]
                        else:
                            doubtful.append((split, img.name, src, "class unclear",
                                             f"label {NAMES[b[0]]}, model {NAMES[best[0]]} {best[1]:.2f}"))
            if n0 and not boxes:
                st[f"{split}_images_now_empty"] += 1
            os.link(img, oi / img.name)
            (ol / f"{img.stem}.txt").write_text("".join(
                f"{b[0]} {b[1]:.6f} {b[2]:.6f} {b[3]:.6f} {b[4]:.6f}\n" for b in boxes))
            st[f"{split}_images_out"] += 1
            st[f"{split}_boxes_out"] += len(boxes)
        print(split, "done", flush=True)

    kol = D / "images/train_kol_v7"
    (D / "data_v8.yaml").write_text(
        "# v8: CLEANED public data (tiny boxes removed, Norway/Czech dropped, Japan halved,\n"
        "#     duplicates + confident class errors fixed) + checked Kolhapur frames. Test set unchanged.\n"
        f"path: {D.as_posix()}\ntrain: [images/train_clean, images/train_kol_v7]\n"
        "val: images/val_clean\ntest: images/test\n\nnc: 2\nnames: ['pothole', 'alligator_crack']\n")

    with open(ROOT / "qa/v8_doubtful.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["split", "image", "source", "issue", "detail"])
        w.writerows(doubtful)

    lines = ["# v8 data cleaning report\n", "| Item | Count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(st.items())]
    lines += [f"| Kolhapur frames added (train_kol_v7) | {len(list(kol.iterdir())) if kol.exists() else 0} |",
              f"| Doubtful images for team review (qa/v8_doubtful.csv) | {len(doubtful)} |",
              "\n## Tiny boxes removed per source\n", "| Source | Removed |", "|---|---|"]
    lines += [f"| {s} | {c['tiny_removed']} |" for s, c in sorted(per_src.items(), key=lambda x: -x[1]['tiny_removed'])]
    (ROOT / "qa/v8_cleaning_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

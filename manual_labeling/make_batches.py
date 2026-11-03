"""Splits every image of POTHOLEDATASET into batch folders of at most 1000 images for verification.

  batches/<Dataset>_<NNN>/
      images/            original images, ORIGINAL file names (hard links: no extra disk space)
      labels/            YOLO txt (0 pothole, 1 alligator_crack) + classes.txt  <- LabelImg / the tool edit these
      labels_dataset/    the same default labels, never edited (used for "Reset to dataset label")
      original_labels/   the dataset's own label files, unchanged (txt / json / mask png)
      manifest.csv       name, original path, default label state, hint

Default label state per image:
  boxes  - the dataset has damage boxes for it
  empty  - the dataset labels it, but with no pothole / alligator crack (empty txt)
  none   - the dataset has no labels for it (no txt written; use AI label or draw)
A batch holds images of one dataset only, and never two files with the same name.
Run once:  python make_batches.py         (refuses to overwrite existing batches)
"""
import csv
import glob
import json
import os
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "POTHOLEDATASET"
OUT = ROOT / "batches"
SIZE = 1000
CLASSES = ["pothole", "alligator_crack"]


def yolo_txt(path, class_map):
    """YOLO txt (box or polygon lines) -> [(cls, xc, yc, w, h)], only classes in class_map."""
    boxes = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        v = line.split()
        if len(v) < 5 or int(float(v[0])) not in class_map:
            continue
        nums = list(map(float, v[1:]))
        if len(nums) == 4:
            xc, yc, w, h = nums
        else:
            xs, ys = nums[0::2], nums[1::2]
            xc, yc, w, h = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys)
        boxes.append((class_map[int(float(v[0]))], xc, yc, w, h))
    return boxes


def mask_boxes(path, cls, min_area_frac=0.0005):
    m = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if m is None:
        return []
    h, w = m.shape
    m = cv2.morphologyEx((m > 127).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    return [(cls, (x + bw / 2) / w, (y + bh / 2) / h, bw / w, bh / h)
            for x, y, bw, bh, area in stats[1:n] if area >= min_area_frac * w * h]


def g(pattern):
    return sorted(os.path.normpath(p) for p in glob.glob(pattern))


def item(img, boxes, originals=(), hint=""):
    """boxes: list -> labeled (maybe empty); None -> dataset has no label for this image."""
    return dict(img=Path(img), boxes=boxes, originals=[Path(o) for o in originals if os.path.exists(o)], hint=hint)


# ---------------------------------------------------------------- one reader per dataset
def bharat():
    for p in g(f"{RAW}/BharatPotHole/*/images/*.jpg"):
        lbl = p.replace(f"{os.sep}images{os.sep}", f"{os.sep}labels{os.sep}")[:-4] + ".txt"
        yield item(p, yolo_txt(lbl, {0: 0}) if os.path.exists(lbl) else None, [lbl])


def roboflow_iit():
    # 0 crocodile crack -> alligator_crack, 1 longitudinal crack (not used), 2 pothole
    for p in g(f"{RAW}/RoboflowIIT/*/images/*.jpg"):
        lbl = p.replace(f"{os.sep}images{os.sep}", f"{os.sep}labels{os.sep}")[:-4] + ".txt"
        yield item(p, yolo_txt(lbl, {0: 1, 2: 0}) if os.path.exists(lbl) else None, [lbl])


def indian_roads():
    # 0 speed bump, 1 pothole, 2 unpaved road -> only 1 is used
    for p in g(f"{RAW}/IndianRoadsDataset/*.jpg"):
        name, lbl = os.path.basename(p), p[:-4] + ".txt"
        hint = ("screenshot of another model's output (boxes burned in) - usually Skip" if name.startswith("frame+")
                else "duplicate copy of another image - usually Skip" if " - Copy" in name else "")
        yield item(p, yolo_txt(lbl, {1: 0}) if os.path.exists(lbl) else None, [lbl], hint)


def pothole600():
    for p in g(f"{RAW}/Pothole600/*/rgb/*.png"):
        mp = p.replace(f"{os.sep}rgb{os.sep}", f"{os.sep}label{os.sep}")
        split = Path(p).parent.parent.name
        yield item(p, mask_boxes(mp, 0) if os.path.exists(mp) else None, [mp], f"Pothole600 {split} split")


def biankatpas():
    for p in g(f"{RAW}/BiankatpasDataset/Dataset/*/*.jpg"):
        d = Path(p).parent
        pm, cm = d / f"{d.name}_POTHOLE.png", d / f"{d.name}_CRACK.png"
        hint = "copy of the RAW image in the same folder - usually Skip" if "(1)" in Path(p).name else ""
        if not pm.exists() and cm.exists():
            hint = (hint + "; " if hint else "") + "dataset marks only generic cracks here (not alligator) - check"
        yield item(p, mask_boxes(pm, 0) if pm.exists() else ([] if cm.exists() else None), [pm, cm], hint)


def rdd2022():
    cmap = {"pothole": 0, "alligator crack": 1}
    for split in ("train", "test"):
        for p in g(f"{RAW}/RDD2022Dataset/{split}/img/*.jpg"):
            a = Path(p).parent.parent / "ann" / (Path(p).name + ".json")
            boxes = None
            if a.exists():
                d = json.load(open(a, encoding="utf-8"))
                W, H = d["size"]["width"], d["size"]["height"]
                boxes = []
                for o in d["objects"]:
                    c = cmap.get(o["classTitle"])
                    if c is None or o["geometryType"] != "rectangle":
                        continue
                    (x0, y0), (x1, y1) = o["points"]["exterior"]
                    boxes.append((c, (x0 + x1) / 2 / W, (y0 + y1) / 2 / H, abs(x1 - x0) / W, abs(y1 - y0) / H))
                if split == "test" and not d["objects"]:
                    boxes = None          # RDD2022 test has no annotations at all: unknown, not "no damage"
            yield item(p, boxes, [a], "RDD2022 test split: dataset gives no labels" if split == "test" else "")


def sp_dataset():
    for p in g(f"{RAW}/SPDataset/*.jpg"):
        yield item(p, None, hint="SPDataset has no labels")


def urban_civic():
    for p in g(f"{RAW}/Urban Civic/yes/*.jpg"):
        yield item(p, None, hint="dataset says: pothole present (no boxes given) - draw or AI label")
    for p in g(f"{RAW}/Urban Civic/no/*.jpg"):
        yield item(p, [], hint="dataset says: no pothole")


DATASETS = [("BharatPotHole", bharat), ("BiankatpasDataset", biankatpas), ("IndianRoadsDataset", indian_roads),
            ("Pothole600", pothole600), ("RDD2022Dataset", rdd2022), ("RoboflowIIT", roboflow_iit),
            ("SPDataset", sp_dataset), ("UrbanCivic", urban_civic)]


def write_yolo(path, boxes):
    lines = []
    for c, xc, yc, w, h in boxes:
        x0, y0, x1, y1 = max(0, xc - w / 2), max(0, yc - h / 2), min(1, xc + w / 2), min(1, yc + h / 2)
        if x1 - x0 > 0 and y1 - y0 > 0:
            lines.append(f"{c} {(x0 + x1) / 2:.6f} {(y0 + y1) / 2:.6f} {x1 - x0:.6f} {y1 - y0:.6f}\n")
    path.write_text("".join(lines))


def link(src, dst):
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def main():
    if OUT.exists() and any(OUT.iterdir()) and "--force" not in sys.argv:
        sys.exit(f"{OUT} already has batches (and maybe your verified labels). Not overwriting. "
                 "Delete it yourself or run with --force.")
    if OUT.exists():
        shutil.rmtree(OUT)
    summary = []
    for ds, reader in DATASETS:
        pending, batches = list(reader()), []
        while pending:                       # fill batches; a clashing name waits for the next batch
            names, cur, rest = set(), [], []
            for it in pending:
                if len(cur) < SIZE and it["img"].name not in names:
                    names.add(it["img"].name)
                    cur.append(it)
                else:
                    rest.append(it)
            batches.append(cur)
            pending = rest
        for k, items in enumerate(batches, 1):
            b = OUT / f"{ds}_{k:03d}"
            for sub in ("images", "labels", "labels_dataset", "original_labels"):
                (b / sub).mkdir(parents=True)
            for sub in ("labels", "labels_dataset"):
                (b / sub / "classes.txt").write_text("\n".join(CLASSES) + "\n")
            counts = {"boxes": 0, "empty": 0, "none": 0}
            with open(b / "manifest.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["name", "original", "default_label", "default_boxes", "hint"])
                for it in items:
                    link(it["img"], b / "images" / it["img"].name)
                    for o in it["originals"]:
                        dst = b / "original_labels" / o.name
                        if not dst.exists():
                            link(o, dst)
                    if it["boxes"] is None:
                        state = "none"
                    else:
                        state = "boxes" if it["boxes"] else "empty"
                        for sub in ("labels", "labels_dataset"):
                            write_yolo(b / sub / (it["img"].stem + ".txt"), it["boxes"])
                    counts[state] += 1
                    w.writerow([it["img"].name, str(it["img"].relative_to(RAW)), state,
                                len(it["boxes"] or []), it["hint"]])
            summary.append((b.name, len(items), counts))
            print(f"{b.name:24s} {len(items):5d} images   with boxes {counts['boxes']:4d}   "
                  f"labeled-empty {counts['empty']:4d}   no label {counts['none']:4d}", flush=True)
    print(f"\n{len(summary)} batches, {sum(n for _, n, _ in summary)} images -> {OUT}")


if __name__ == "__main__":
    main()

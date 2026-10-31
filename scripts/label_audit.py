"""
Ensemble label-support audit of the TEST set.

A ground-truth box that NO independent model finds, across several models, is evidence that
the box does not contain visible damage (label error).  A confident detection with no GT box
is evidence of a missed label.  Both are measured here, per data source.

Run:  python scripts/label_audit.py [model1.pt model2.pt ...] [--device cpu]
Out:  qa/label_audit.csv            per test GT box: support score + size
      qa/label_audit_summary.md     per-source label-quality table + ceiling estimate
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
D = ROOT / "dataset"
MODELS = ["runs/yolo11s_v1/weights/best.pt", "runs/yolo11s_v8_clean/weights/best.pt"]


def xywhn_to_xyxy(b, w, h):
    x, y, bw, bh = b
    return np.array([(x - bw / 2) * w, (y - bh / 2) * h, (x + bw / 2) * w, (y + bh / 2) * h])


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, x2 - x1), max(0.0, y2 - y1)
    inter = iw * ih
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0.0


def main():
    argv = sys.argv[1:]
    args, device = [], "cpu"
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--device"):
            device = a.split("=")[1] if "=" in a else argv[i + 1]
            i += 1 if "=" in a else 2
            continue
        if not a.startswith("--"):
            args.append(a)
        i += 1
    weights = args or MODELS
    imgs = sorted((D / "images/test").glob("*.jpg"))
    src_of = {Path(m["file"]).stem: m["source"] for m in json.load(open(D / "manifest.json")) if m["split"] == "test"}

    # support[img] = list of (xyxy, conf)
    support = defaultdict(list)
    for w in weights:
        model = YOLO(str(ROOT / w))
        for i in range(0, len(imgs), 16):
            batch = imgs[i:i + 16]
            for r, p in zip(model.predict([str(x) for x in batch], imgsz=640, conf=0.02, iou=0.7,
                                          max_det=100, device=device, verbose=False), batch):
                for bb, cf in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()):
                    support[p.stem].append((bb, float(cf)))
        print("done", w, flush=True)

    rows = []
    per_src = defaultdict(lambda: dict(n=0, unsupported=0, supported=0))
    from PIL import Image
    for img in imgs:
        with Image.open(img) as im:
            w, h = im.size
        lp = D / "labels/test" / (img.stem + ".txt")
        if not lp.exists():
            continue
        preds = support.get(img.stem, [])
        src = src_of.get(img.stem, "?")
        for bi, line in enumerate(lp.read_text().splitlines()):
            v = line.split()
            if len(v) != 5:
                continue
            c, x, y, bw, bh = int(v[0]), *map(float, v[1:])
            g = xywhn_to_xyxy((x, y, bw, bh), w, h)
            best = 0.0
            for bb, cf in preds:
                if iou(g, bb) >= 0.3:
                    best = max(best, cf)
            area = bw * bh
            rows.append(dict(source=src, image=img.name, box_index=bi, cls=c, area=round(area, 6),
                             support=round(best, 4), w=round(bw, 4), h=round(bh, 4)))
            per_src[src]["n"] += 1
            if best == 0.0:
                per_src[src]["unsupported"] += 1
            else:
                per_src[src]["supported"] += 1

    import csv
    with open(ROOT / "qa/label_audit.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)

    L = ["# Test-set label audit\n",
         "A box is *unsupported* when none of the independent models detects anything at that place\n"
         "(IoU >= 0.3, conf >= 0.02). Unsupported small boxes are label errors; unsupported large boxes\n"
         "are either real damage all models miss or a region-level annotation.\n",
         "| source | boxes | unsupported | % unsupported | unsupported & area<0.2% |",
         "|---|---|---|---|---|"]
    tot = uns = 0
    small_uns = 0
    for s in sorted(per_src):
        v = per_src[s]
        su = sum(1 for r in rows if r["source"] == s and r["support"] == 0 and r["area"] < 0.002)
        small_uns += su
        tot += v["n"]; uns += v["unsupported"]
        L.append(f"| {s} | {v['n']} | {v['unsupported']} | {100*v['unsupported']/max(1,v['n']):.1f} | {su} |")
    n = len(rows)
    L += [f"\n**All test boxes: {tot}. Unsupported by every model: {uns} ({100*uns/tot:.1f}%). "
          f"Unsupported and smaller than 0.2% of the image: {small_uns} ({100*small_uns/tot:.1f}%).**\n",
          "Recall can never exceed the share of GT that contains visible damage, so these boxes bound\n"
          "the achievable mAP@50 on this test set."]
    (ROOT / "qa/label_audit_summary.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[-4:]))
    print("WROTE qa/label_audit.csv and qa/label_audit_summary.md")


if __name__ == "__main__":
    main()

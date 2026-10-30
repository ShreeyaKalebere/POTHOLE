"""
Finds training images whose labels are probably WRONG, using the trained model.
Run AFTER training finishes:   python find_label_errors.py

Three kinds of suspects (model must be confident for a case to count):
  MISSING  - model sees damage (conf >= 0.6) where no label box exists   -> unlabelled pothole?
  EXTRA    - a label box the model finds nothing at all near               -> wrong / sloppy box?
  CLASS    - model is confident it's the other class at the same place     -> pothole vs crack mix-up?

Output: qa/label_review/  with side-by-side pictures (green = label, red = model)
        and qa/label_review/suspects.csv  sorted by how sure the model is.
Review the top ~200 pictures; fix real mistakes (Roboflow or any labelling tool),
then rebuild the dataset and retrain.
"""
import csv
import shutil
from pathlib import Path

import cv2
from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
WEIGHTS = ROOT / "runs/yolo11s_v1/weights/best.pt"
OUT = ROOT / "qa/label_review"
NAMES = ["pothole", "alligator_crack"]
CONF_MISSING = 0.60
TOP_N_IMAGES = 300


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u else 0


def load_labels(p, W, H):
    boxes = []
    if p.exists():
        for line in open(p):
            c, x, y, w, h = map(float, line.split())
            boxes.append((int(c), [(x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H]))
    return boxes


def main():
    model = YOLO(str(WEIGHTS))
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "images").mkdir(parents=True)
    suspects = []
    imgs = sorted((ROOT / "dataset/images/train").glob("*"))
    for k, ip in enumerate(imgs):
        if k % 1000 == 0:
            print(f"{k}/{len(imgs)}")
        r = model.predict(str(ip), conf=0.25, verbose=False)[0]
        H, W = r.orig_shape
        gts = load_labels(ROOT / "dataset/labels/train" / (ip.stem + ".txt"), W, H)
        preds = [(int(b.cls), float(b.conf), [float(v) for v in b.xyxy[0]]) for b in r.boxes]
        issues = []
        for c, conf, pb in preds:
            best = max(gts, key=lambda g: iou(g[1], pb), default=None)
            ov = iou(best[1], pb) if best else 0
            if ov < 0.1 and conf >= CONF_MISSING:
                issues.append(("MISSING", conf, NAMES[c]))
            elif ov >= 0.5 and best[0] != c and conf >= CONF_MISSING:
                issues.append(("CLASS", conf, f"label {NAMES[best[0]]} / model {NAMES[c]}"))
        for c, gb in gts:
            if not any(iou(gb, pb) >= 0.1 for _, _, pb in preds):
                issues.append(("EXTRA", 0.5, NAMES[c]))
        if issues:
            score = sum(i[1] for i in issues if i[0] != "EXTRA") + 0.3 * sum(i[0] == "EXTRA" for i in issues)
            suspects.append((score, ip, issues, gts, preds))

    suspects.sort(key=lambda s: -s[0])
    with open(OUT / "suspects.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "image", "score", "issues"])
        for rank, (score, ip, issues, gts, preds) in enumerate(suspects, 1):
            w.writerow([rank, ip.name, round(score, 2), "; ".join(f"{t}:{d}" for t, _, d in issues)])
            if rank <= TOP_N_IMAGES:
                im = cv2.imread(str(ip))
                lab, prd = im.copy(), im.copy()
                for c, b in gts:
                    cv2.rectangle(lab, tuple(map(int, b[:2])), tuple(map(int, b[2:])), (0, 200, 0), 3)
                for c, conf, b in preds:
                    cv2.rectangle(prd, tuple(map(int, b[:2])), tuple(map(int, b[2:])), (0, 0, 255), 3)
                    cv2.putText(prd, f"{NAMES[c][:7]} {conf:.2f}", (int(b[0]), int(b[1]) - 5), 0, 0.7, (0, 0, 255), 2)
                cv2.putText(lab, "LABEL", (10, 35), 0, 1.2, (0, 200, 0), 3)
                cv2.putText(prd, "MODEL", (10, 35), 0, 1.2, (0, 0, 255), 3)
                cv2.imwrite(str(OUT / "images" / f"{rank:04d}_{ip.stem}.jpg"), cv2.hconcat([lab, prd]))
    counts = {t: sum(any(i[0] == t for i in s[2]) for s in suspects) for t in ("MISSING", "EXTRA", "CLASS")}
    print(f"\n{len(suspects)} suspect images of {len(imgs)}  {counts}")
    print("Review pictures in", OUT / "images")


if __name__ == "__main__":
    main()

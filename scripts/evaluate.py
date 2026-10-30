"""
Module 5 - Final evaluation for the report.
Run AFTER training finishes (it uses the GPU):

    python evaluate.py                      # evaluates runs/yolo11s_v1/weights/best.pt
    python evaluate.py yolo11n_v1           # another run

Produces F:/POTHOLE_PROJECT/qa/evaluation_<run>.md with:
  - test-set Precision, Recall, F1, mAP@50, mAP@50-95 (overall + per class)
  - results per data source (does it work on Indian roads? on RDD Japan? ...)
  - speed: ms per image and FPS on GPU and on CPU (for the "lightweight" claim)
  - model size and parameter count
Graphs (confusion matrix, PR curve ...) are saved by Ultralytics in runs/<run>_test/.
"""
import json
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
RUN = sys.argv[1] if len(sys.argv) > 1 else "yolo11s_v1"
WEIGHTS = ROOT / "runs" / RUN / "weights" / "best.pt"
DATA = ROOT / "dataset" / "data.yaml"
NAMES = ["pothole", "alligator_crack"]
IMGSZ = 640


def f1(p, r):
    return 2 * p * r / (p + r) if p + r else 0.0


def train_imgsz(model):
    """Evaluate at the image size the model was trained with (640 for v1, 960 for v2)."""
    return int((getattr(model, "ckpt", None) or {}).get("train_args", {}).get("imgsz", 640))


def speed(model, device, n=100):
    imgs = sorted((ROOT / "dataset/images/test").glob("*"))[:n]
    frames = [cv2.imread(str(p)) for p in imgs]
    for f in frames[:5]:                       # warm-up
        model.predict(f, device=device, imgsz=IMGSZ, verbose=False)
    t = time.perf_counter()
    for f in frames:
        model.predict(f, device=device, imgsz=IMGSZ, verbose=False)
    ms = (time.perf_counter() - t) / len(frames) * 1000
    return round(ms, 1), round(1000 / ms, 1)


def per_source(model):
    """mAP@50 separately for every data source, using a temporary yaml per source."""
    manifest = json.load(open(ROOT / "dataset/manifest.json"))
    by_src = defaultdict(list)
    for m in manifest:
        if m["split"] == "test":
            by_src[m["source"]].append(str(ROOT / "dataset/images/test" / m["file"]))
    tmp = ROOT / "qa" / "_eval_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    out = {}
    for src, files in sorted(by_src.items()):
        if len(files) < 20:
            continue
        lst = tmp / f"{src}.txt"
        lst.write_text("\n".join(files))
        y = tmp / f"{src}.yaml"
        y.write_text(f"path: {ROOT / 'dataset'}\ntrain: {lst}\nval: {lst}\nnc: 2\nnames: {NAMES}\n")
        m = model.val(data=str(y), split="val", verbose=False, plots=False, batch=8, imgsz=IMGSZ)
        out[src] = {"images": len(files), "mAP50": round(m.box.map50, 3), "P": round(m.box.mp, 3),
                    "R": round(m.box.mr, 3)}
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def main():
    global IMGSZ
    model = YOLO(str(WEIGHTS))
    IMGSZ = train_imgsz(model)
    print("Evaluating", WEIGHTS)
    m = model.val(data=str(DATA), split="test", project=str(ROOT / "runs"), name=f"{RUN}_test",
                  exist_ok=True, plots=True, imgsz=IMGSZ, batch=8)
    P, R = m.box.mp, m.box.mr
    rows = [("All", P, R, m.box.map50, m.box.map)]
    for i, n in enumerate(NAMES):
        p, r, ap50, ap = m.box.class_result(i)
        rows.append((n, p, r, ap50, ap))

    gpu_ms, gpu_fps = speed(model, 0)
    cpu_ms, cpu_fps = speed(model, "cpu", n=40)
    params = sum(p.numel() for p in model.model.parameters())
    size_mb = WEIGHTS.stat().st_size / 1e6
    src = per_source(model)

    L = [f"# Final evaluation — {RUN}\n",
         f"Weights: `{WEIGHTS}`  \nTest set: 2,652 images never seen during training\n",
         "## Accuracy (test set)\n",
         "| Class | Precision | Recall | F1 | mAP@50 | mAP@50-95 |", "|---|---|---|---|---|---|"]
    for n, p, r, a50, a in rows:
        L.append(f"| {n} | {p:.3f} | {r:.3f} | {f1(p, r):.3f} | {a50:.3f} | {a:.3f} |")
    L += ["\n## Speed\n", "| Device | ms / image | FPS |", "|---|---|---|",
          f"| GPU (RTX 4060 Laptop) | {gpu_ms} | {gpu_fps} |", f"| CPU (i7-13650HX) | {cpu_ms} | {cpu_fps} |",
          f"\nModel size: **{size_mb:.1f} MB**, parameters: **{params / 1e6:.2f} M**\n",
          "## mAP@50 by data source (test images)\n",
          "| Source | Test images | Precision | Recall | mAP@50 |", "|---|---|---|---|---|"]
    for s, v in src.items():
        L.append(f"| {s} | {v['images']} | {v['P']:.3f} | {v['R']:.3f} | {v['mAP50']:.3f} |")
    L.append(f"\nGraphs: `runs/{RUN}_test/` (confusion_matrix.png, BoxPR_curve.png, BoxF1_curve.png)")
    out = ROOT / "qa" / f"evaluation_{RUN}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print("\nSaved", out)


if __name__ == "__main__":
    main()

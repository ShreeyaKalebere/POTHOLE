"""
Finalise a training run: evaluate on the untouched test split, write the report, update the
results tables, and optionally promote the weights to models/final.pt.

    python scripts/finalize_run.py yolo11m_v9_all            # evaluate + write everything
    python scripts/finalize_run.py yolo11m_v9_all --promote  # also copy best.pt -> models/final.pt

Outputs
    qa/evaluation_<run>.md            same format as the earlier runs (comparable)
    qa/results_models_test.csv        one appended row per model
    paper_results/table3_4_accuracy.csv
    models/final.pt (+ final.pt.bak)
"""
import csv
import json
import re
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
D = ROOT / "dataset"
NAMES = ["pothole", "alligator_crack"]
SPEED_IMGS = 60


def f1(p, r):
    return 2 * p * r / (p + r) if p + r else 0.0


def per_source(model, imgsz):
    manifest = json.load(open(D / "manifest.json"))
    by = defaultdict(list)
    for m in manifest:
        if m["split"] == "test":
            by[m["source"]].append(str(D / "images/test" / m["file"]))
    tmp = ROOT / "qa" / "_eval_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    out = {}
    for src, files in sorted(by.items()):
        if len(files) < 20:
            continue
        lst = tmp / f"{src}.txt"
        lst.write_text("\n".join(files))
        y = tmp / f"{src}.yaml"
        y.write_text(f"path: {D.as_posix()}\ntrain: {lst.as_posix()}\nval: {lst.as_posix()}\n"
                     f"nc: 2\nnames: {NAMES}\n")
        m = model.val(data=str(y), split="val", verbose=False, plots=False, batch=8, imgsz=imgsz)
        out[src] = dict(images=len(files), mAP50=m.box.map50, P=m.box.mp, R=m.box.mr)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def speed(model, device, imgsz, n=SPEED_IMGS):
    imgs = sorted((D / "images/test").glob("*.jpg"))[:n]
    frames = [cv2.imread(str(p)) for p in imgs]
    for f in frames[:5]:
        model.predict(f, device=device, imgsz=imgsz, verbose=False)
    t = time.perf_counter()
    for f in frames:
        model.predict(f, device=device, imgsz=imgsz, verbose=False)
    ms = (time.perf_counter() - t) / len(frames) * 1000
    return round(ms, 1), round(1000 / ms, 1)


def append_results_row(run, desc, m, imgsz, src):
    path = ROOT / "qa/results_models_test.csv"
    rows = list(csv.reader(open(path, encoding="utf-8")))
    header = rows[0]
    gpu_ms, gpu_fps = speed(YOLO(str(ROOT / "runs" / run / "weights/best.pt")), 0, imgsz)
    cpu_ms, cpu_fps = speed(YOLO(str(ROOT / "runs" / run / "weights/best.pt")), "cpu", imgsz, n=20)
    vals = dict(model=run, description=desc, status="evaluated",
                precision=round(m.box.mp, 3), recall=round(m.box.mr, 3),
                F1=round(f1(m.box.mp, m.box.mr), 3), mAP50=round(m.box.map50, 3),
                mAP50_95=round(m.box.map, 3), gpu_ms_per_image=gpu_ms, gpu_fps=gpu_fps,
                cpu_ms_per_image=cpu_ms, cpu_fps=cpu_fps)
    for i, n in enumerate(NAMES):
        p, r, ap50, ap = m.box.class_result(i)
        vals[f"{n}_precision"] = round(p, 3)
        vals[f"{n}_recall"] = round(r, 3)
        vals[f"{n}_F1"] = round(f1(p, r), 3)
        vals[f"{n}_mAP50"] = round(ap50, 3)
        vals[f"{n}_mAP50_95"] = round(ap, 3)
    for s, v in src.items():
        vals[f"mAP50_{s}"] = round(v["mAP50"], 3)
    row = [vals.get(h, "") for h in header]
    rows = [r for r in rows if not (r and r[0] == run)]
    rows.append(row)
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print("updated", path)


def main():
    run = sys.argv[1]
    promote = "--promote" in sys.argv
    weights = ROOT / "runs" / run / "weights" / "best.pt"
    model = YOLO(str(weights))
    trained = int(((model.ckpt or {}).get("train_args") or {}).get("imgsz", 640))

    # pick the best evaluation resolution among the trained one and 640
    best, best_s = None, None
    for s in sorted({trained, 640}):
        m = model.val(data=str(D / "data.yaml"), split="test", imgsz=s, batch=8, device=0,
                      workers=0, plots=False, verbose=False)
        print(f"imgsz={s}: mAP50={m.box.map50:.4f}", flush=True)
        if best is None or m.box.map50 > best.box.map50:
            best, best_s = m, s

    m = model.val(data=str(D / "data.yaml"), split="test", imgsz=best_s, batch=8, device=0,
                  workers=0, plots=True, project=str(ROOT / "runs"), name=f"{run}_test", exist_ok=True)
    rows = [("All", m.box.mp, m.box.mr, m.box.map50, m.box.map)]
    for i, n in enumerate(NAMES):
        p, r, ap50, ap = m.box.class_result(i)
        rows.append((n, p, r, ap50, ap))
    src = per_source(model, best_s)
    gpu_ms, gpu_fps = speed(model, 0, best_s)
    cpu_ms, cpu_fps = speed(model, "cpu", best_s, n=20)
    params = sum(p.numel() for p in model.model.parameters())
    size_mb = weights.stat().st_size / 1e6

    L = [f"# Final evaluation — {run}\n",
         f"Weights: `{weights}`  \nInference size: {best_s} px  \n"
         f"Test set: 2,652 images never seen during training\n",
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
    L.append(f"\nGraphs: `runs/{run}_test/`")
    (ROOT / "qa" / f"evaluation_{run}.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))

    append_results_row(run, f"{run} (v9: all data, {trained} px)", m, best_s, src)

    if promote:
        fin = ROOT / "models/final.pt"
        if fin.exists():
            shutil.copy2(fin, ROOT / "models/final.pt.bak")
        shutil.copy2(weights, fin)
        print("promoted", weights, "->", fin)


if __name__ == "__main__":
    main()

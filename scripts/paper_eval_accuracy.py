"""Tables III/IV - detection accuracy, measured with model.val() exactly as requested.
Run: python paper_eval_accuracy.py [run ...]     (device can be set with DEVICE=cpu|0)
Each run/split writes plots + predictions.json to paper_results/val_<run>_<split>/
and one row to paper_results/table3_4_accuracy.csv (appended)."""
import csv
import os
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
OUT = ROOT / "paper_results"
DATA = ROOT / "dataset/data.yaml"        # the base split used by v1-v7 for val/test
DEVICE = os.getenv("DEVICE", "cpu")
NAMES = ["pothole", "alligator_crack"]


def f1(p, r):
    return 2 * p * r / (p + r) if (p + r) else 0.0


def main(runs):
    out_csv = OUT / "table3_4_accuracy.csv"
    new = not out_csv.exists()
    with open(out_csv, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["run", "weights", "split", "class", "images", "instances", "P", "R", "F1", "mAP50", "mAP50_95"])
        for run in runs:
            weights = ROOT / "runs" / run / "weights" / "best.pt"
            model = YOLO(str(weights))
            imgsz = int((model.ckpt or {}).get("train_args", {}).get("imgsz", 640))
            for split in ("val", "test"):
                m = model.val(data=str(DATA), split=split, imgsz=imgsz, batch=8, device=DEVICE, workers=0,
                              plots=True, save_json=True, project=str(OUT), name=f"val_{run}_{split}", exist_ok=True)
                P, R = m.box.mp, m.box.mr
                print(run, split, "P", P, "R", R, "mAP50", m.box.map50, "mAP50-95", m.box.map,
                      "per-class mAP50-95", list(m.box.maps), flush=True)
                n_img = getattr(m, "seen", "")
                w.writerow([run, str(weights), split, "all", n_img, int(m.nt_per_class.sum()) if hasattr(m, "nt_per_class") else "",
                            f"{P:.4f}", f"{R:.4f}", f"{f1(P, R):.4f}", f"{m.box.map50:.4f}", f"{m.box.map:.4f}"])
                for i, n in enumerate(NAMES):
                    p, r, ap50, ap = m.box.class_result(i)
                    w.writerow([run, str(weights), split, n, "", int(m.nt_per_class[i]) if hasattr(m, "nt_per_class") else "",
                                f"{p:.4f}", f"{r:.4f}", f"{f1(p, r):.4f}", f"{ap50:.4f}", f"{ap:.4f}"])
                f.flush()


if __name__ == "__main__":
    main(sys.argv[1:] or ["yolo11s_v1", "yolo11s_v6_kolreview", "yolo11s_v8_clean"])

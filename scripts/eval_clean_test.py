"""
Evaluates every trained model on BOTH test sets and writes qa/results_full_vs_clean_test.csv

  full test  = the original 2,652-image test set (main, honest comparison)
  clean test = same images minus RDD Norway/Czech, and boxes < 0.1% of the image removed
               (damage a road inspector could clearly see). Always report together with full test.

Run:  python eval_clean_test.py
"""
import csv
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
RUNS = ["yolo11s_v1", "yolo11s_v2_960", "yolo11s_v3_aug", "yolo11s_v4_fixed", "yolo11s_v5_kolpseudo",
        "yolo11s_v6_kolreview", "yolo11s_v7_kolfixed", "yolo11s_v8_clean", "yolo11m_v8_clean"]


def score(model, data, imgsz):
    m = model.val(data=str(data), split="test", imgsz=imgsz, batch=8, workers=0, verbose=False, plots=False)
    return m.box.mp, m.box.mr, m.box.map50, m.box.map


def main():
    rows = []
    for run in RUNS:
        w = ROOT / "runs" / run / "weights" / "best.pt"
        if not w.exists():
            continue
        model = YOLO(str(w))
        imgsz = int((model.ckpt or {}).get("train_args", {}).get("imgsz", 640))
        full = score(model, ROOT / "dataset/data.yaml", imgsz)
        clean = score(model, ROOT / "dataset/data_cleantest.yaml", imgsz)
        rows.append([run, imgsz] + [round(x, 3) for x in full + clean])
        print(f"{run:24s} full mAP50 {full[2]:.3f} | clean mAP50 {clean[2]:.3f}", flush=True)
    with open(ROOT / "qa/results_full_vs_clean_test.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["model", "imgsz",
                    "FULL_precision", "FULL_recall", "FULL_mAP50", "FULL_mAP50_95",
                    "CLEAN_precision", "CLEAN_recall", "CLEAN_mAP50", "CLEAN_mAP50_95"])
        w.writerows(rows)
    print("saved qa/results_full_vs_clean_test.csv")


if __name__ == "__main__":
    main()

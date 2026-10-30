"""Table V - inference speed on the RTX 4060 (GPU must be otherwise idle).
model.val() on the full test split at the training image size, batch=1 (per-image latency),
after a 50-image warm-up. Ultralytics reports preprocess / inference / postprocess ms per image.
No tracking is included here. Output: paper_results/table5_speed.csv
Run: python paper_table5_speed.py"""
import csv
import glob
from pathlib import Path

import torch
from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
RUNS = ["yolo11s_v1", "yolo11s_v6_kolreview", "yolo11s_v8_clean", "yolo11m_v8_clean"]


def main():
    rows = []
    warm = sorted(glob.glob(str(ROOT / "dataset/images/test/*")))[:50]
    for run in RUNS:
        w = ROOT / "runs" / run / "weights" / "best.pt"
        if not w.exists():
            continue
        model = YOLO(str(w))
        imgsz = int((model.ckpt or {}).get("train_args", {}).get("imgsz", 640))
        for p in warm:
            model.predict(p, imgsz=imgsz, device=0, verbose=False)
        torch.cuda.synchronize()
        m = model.val(data=str(ROOT / "dataset/data.yaml"), split="test", imgsz=imgsz, batch=1, device=0,
                      workers=0, plots=False, verbose=False)
        s = m.speed
        total = s["preprocess"] + s["inference"] + s["postprocess"]
        rows.append([run, torch.cuda.get_device_name(0), imgsz, 1, round(s["preprocess"], 2), round(s["inference"], 2),
                     round(s["postprocess"], 2), round(total, 2), round(1000 / total, 1), "no"])
        print(rows[-1], flush=True)
    with open(ROOT / "paper_results/table5_speed.csv", "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.writer(f)
        wr.writerow(["run", "gpu", "imgsz", "batch", "preprocess_ms", "inference_ms", "postprocess_ms", "total_ms",
                     "FPS(=1000/total)", "tracking_included"])
        wr.writerows(rows)


if __name__ == "__main__":
    main()

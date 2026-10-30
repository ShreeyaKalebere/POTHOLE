"""
Training run v2 - aimed at small potholes and Indian roads.

Changes vs v1 (yolo11s_v1, test mAP50 0.639):
  1. imgsz 960 instead of 640  -> far-away potholes keep 2.25x more pixels
     (63% of pothole boxes cover < 1% of the image)
  2. data_v2.yaml: BharatPotHole, IndianRoads and RDD India images appear twice
  3. starts FROM the v1 best model (fine-tuning), so it needs fewer epochs

Run:     python train_v2.py [workers]      (starts, or resumes if a v2 run already exists)
"""
import faulthandler
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
RUN = "yolo11s_v2_960"
LAST = ROOT / "runs" / RUN / "weights" / "last.pt"


def _rearm(_trainer=None):
    """If no batch finishes for 2 minutes, write every thread's stack to the log (hang diagnosis)."""
    faulthandler.cancel_dump_traceback_later()
    faulthandler.dump_traceback_later(120, repeat=False, file=sys.stderr)


if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 2

    if LAST.exists():
        model = YOLO(str(LAST))
        args = dict(resume=True, workers=workers)
    else:
        model = YOLO(str(ROOT / "runs/yolo11s_v1/weights/best.pt"))
        args = dict(
            data=str(ROOT / "dataset/data_v2.yaml"),
            project=str(ROOT / "runs"), name=RUN, exist_ok=True,
            imgsz=960,
            batch=8,                 # 960 px needs ~2.25x memory per image; 8 fits the 8 GB GPU
            epochs=40,
            patience=12,
            workers=workers,
            device=0,
            optimizer="SGD", lr0=0.003, lrf=0.1,   # small learning rate: fine-tuning, not from scratch
            warmup_epochs=1,
            cos_lr=True,
            close_mosaic=8,
            hsv_h=0.015, hsv_s=0.6, hsv_v=0.5,
            degrees=3.0, translate=0.1, scale=0.5, fliplr=0.5, mosaic=1.0, mixup=0.1,
            plots=True,
        )

    for event in ("on_train_batch_end", "on_val_batch_end", "on_train_epoch_start", "on_val_start"):
        model.add_callback(event, _rearm)
    _rearm()
    model.train(**args)
    faulthandler.cancel_dump_traceback_later()

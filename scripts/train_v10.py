"""
Training run v10 - short, high-value fine-tune.

Starting point: runs/yolo11s_v1/weights/best.pt - already converged on this dataset (mAP@50 0.639,
107 epochs).  v9 (YOLO11m trained from scratch at 768) needed 8-13 h on this laptop and the session
died at epoch 4, so v10 takes the cheap path instead:

  * start from the converged v1 weights, low LR (0.002, cosine to 1 %)
  * train at 768 px - 23 % of test instances are smaller than 32 px at 640, the weakest bucket
  * on ALL usable data (train + val + reviewed Kolhapur frames = 16,185 images)
  * 18 epochs  ->  ~2 h on the 8 GB 4060 instead of 13 h from scratch

Comparable with v1-v8 because the TEST split is still untouched.

Run:   python scripts/train_v10.py [epochs] [imgsz] [batch]
"""
import faulthandler
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
RUN = "yolo11s_v10_768"
LAST = ROOT / "runs" / RUN / "weights" / "last.pt"
START = ROOT / "runs" / "yolo11s_v1" / "weights" / "best.pt"


def _rearm(_trainer=None):
    faulthandler.cancel_dump_traceback_later()
    faulthandler.dump_traceback_later(600, repeat=False, file=sys.stderr)


if __name__ == "__main__":
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 18
    imgsz = int(sys.argv[2]) if len(sys.argv) > 2 else 768
    batch = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    if LAST.exists():
        print("resuming", LAST, flush=True)
        model, args = YOLO(str(LAST)), dict(resume=True)
    else:
        print("fine-tuning from", START, "at", imgsz, "px", flush=True)
        model = YOLO(str(START))
        args = dict(
            data=str(ROOT / "dataset/data_v9.yaml"), project=str(ROOT / "runs"), name=RUN,
            exist_ok=True, imgsz=imgsz, batch=batch, epochs=epochs, patience=epochs + 5,
            workers=4, device=0, amp=True, cache=False,
            optimizer="SGD", lr0=0.002, lrf=0.01, momentum=0.937, weight_decay=0.0005,
            warmup_epochs=0.5, cos_lr=True,
            hsv_h=0.015, hsv_s=0.6, hsv_v=0.4,
            degrees=3.0, translate=0.1, scale=0.5, shear=0.0, perspective=0.0,
            fliplr=0.5, flipud=0.0, mosaic=1.0, mixup=0.05, erasing=0.2,
            close_mosaic=max(2, epochs // 4), rect=False,
            plots=True, seed=0, save_period=-1, val=True,
        )
    for ev in ("on_train_batch_end", "on_val_batch_end", "on_train_epoch_start", "on_val_start"):
        model.add_callback(ev, _rearm)
    _rearm()
    model.train(**args)
    faulthandler.cancel_dump_traceback_later()

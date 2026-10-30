"""
Training run v8m - YOLO11m (medium, ~2x larger than YOLO11s) on the CLEANED data (data_v8.yaml).
Starts from the COCO-pretrained yolo11m.pt (a YOLO11s model cannot be used as a start for 11m).

Run:   python train_v8m.py [workers]     (starts, or resumes if the run already exists)
"""
import faulthandler
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
RUN = "yolo11m_v8_clean"
LAST = ROOT / "runs" / RUN / "weights" / "last.pt"


def _rearm(_trainer=None):
    faulthandler.cancel_dump_traceback_later()
    faulthandler.dump_traceback_later(180, repeat=False, file=sys.stderr)


if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    if LAST.exists():
        model, args = YOLO(str(LAST)), dict(resume=True, workers=workers)
    else:
        model = YOLO("yolo11m.pt")
        args = dict(
            data=str(ROOT / "dataset/data_v8.yaml"), project=str(ROOT / "runs"), name=RUN, exist_ok=True,
            imgsz=640, batch=12,          # 11m needs more GPU memory than 11s; 12 fits the 8 GB card
            epochs=40, patience=12, workers=workers, device=0,
            cos_lr=True, close_mosaic=10,
            hsv_h=0.015, hsv_s=0.6, hsv_v=0.5,
            degrees=3.0, translate=0.1, scale=0.5, fliplr=0.5, mosaic=1.0, mixup=0.1,
            plots=True,
        )
    for event in ("on_train_batch_end", "on_val_batch_end", "on_train_epoch_start", "on_val_start"):
        model.add_callback(event, _rearm)
    _rearm()
    model.train(**args)
    faulthandler.cancel_dump_traceback_later()

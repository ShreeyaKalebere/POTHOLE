"""
Training run v11 - the manually verified dataset (manual_labeling/build_training_set.py).

Starts fresh from the COCO-pretrained YOLO11s rather than from an older model, so nothing learned
from the old inconsistent labels carries over.

Run:   python train_v11.py [workers]
"""
import faulthandler
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
RUN = "yolo11s_v11_verified"
LAST = ROOT / "runs" / RUN / "weights" / "last.pt"


def _rearm(_trainer=None):
    faulthandler.cancel_dump_traceback_later()
    faulthandler.dump_traceback_later(120, repeat=False, file=sys.stderr)


if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    if LAST.exists():
        model, args = YOLO(str(LAST)), dict(resume=True, workers=workers)
    else:
        model = YOLO(str(ROOT / "scripts" / "yolo11s.pt"))
        args = dict(
            data=str(ROOT / "dataset_verified" / "data.yaml"), project=str(ROOT / "runs"), name=RUN, exist_ok=True,
            imgsz=640, batch=16, epochs=60, patience=15, workers=workers, device=0,
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

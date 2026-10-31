"""
Training run v9 - YOLO11m on ALL usable data (train + val + reviewed Kolhapur frames), at 768 px.
The test split is never seen.  Resumable: re-running continues from runs/<RUN>/weights/last.pt.

Why this recipe (from qa/audit_summary.md + qa/diagnose_*):
  * v1 (all data, 640, 107 epochs) = 0.639 mAP50 is still the best; every "cleaning" run was worse,
    so v9 keeps every image and box.
  * 23% of test instances are <32 px at 640 - small-object AP is the weakest bucket
    (mAP50 0.09-0.37), so v9 trains at 768.
  * 11m has ~3x the capacity of 11s at the same latency class.

Run:   python scripts/train_v9.py [epochs] [imgsz] [batch]
"""
import faulthandler
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
RUN = "yolo11m_v9_all"
LAST = ROOT / "runs" / RUN / "weights" / "last.pt"
DATA = ROOT / "dataset/data_v9.yaml"


def _rearm(_trainer=None):
    faulthandler.cancel_dump_traceback_later()
    faulthandler.dump_traceback_later(300, repeat=False, file=sys.stderr)


if __name__ == "__main__":
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    imgsz = int(sys.argv[2]) if len(sys.argv) > 2 else 768
    batch = int(sys.argv[3]) if len(sys.argv) > 3 else 8

    if LAST.exists():
        model, args = YOLO(str(LAST)), dict(resume=True)
        print("resuming", LAST, flush=True)
    else:
        model = YOLO(str(ROOT / "scripts/yolo11m.pt"))
        args = dict(
            data=str(DATA), project=str(ROOT / "runs"), name=RUN, exist_ok=True,
            imgsz=imgsz, batch=batch, epochs=epochs, patience=epochs + 10,
            workers=4, device=0, amp=True, cache=False,
            optimizer="SGD", lr0=0.01, lrf=0.01, momentum=0.937, weight_decay=0.0005,
            warmup_epochs=3.0, warmup_bias_lr=0.1, cos_lr=True,
            box=7.5, cls=0.5, dfl=1.5,
            hsv_h=0.015, hsv_s=0.7, hsv_v=0.4,
            degrees=5.0, translate=0.1, scale=0.5, shear=0.0, perspective=0.0,
            fliplr=0.5, flipud=0.0, mosaic=1.0, mixup=0.1, copy_paste=0.0,
            erasing=0.4, close_mosaic=10, rect=False,
            plots=True, seed=0, deterministic=False, val=True, save_period=-1,
        )
    for ev in ("on_train_batch_end", "on_val_batch_end", "on_train_epoch_start", "on_val_start"):
        model.add_callback(ev, _rearm)
    _rearm()
    model.train(**args)
    faulthandler.cancel_dump_traceback_later()

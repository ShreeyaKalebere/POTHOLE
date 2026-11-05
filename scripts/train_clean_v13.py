"""
Training run v13 - Clean Unified Single-Class (Pothole / Road Damage) Detector.

Target: Reach >= 85% mAP for Real-World Deployment & Kolhapur Conditions.

Key Strategy:
  1. Toxic datasets excluded: BharatPotHole (flat asphalt), RDD Norway (sub-pixel noise), IndianRoads.
  2. All 18 known corrupted/hanging images sanitized from train and val sets.
  3. Kolhapur local domain oversampled 4x (2,484 frames in train) so target road conditions dominate gradients.
  4. Single-Class unified (single_cls=True): eliminates 100% of the class confusion between RoboflowIIT and RDD Japan.
  5. Box loss weighted up (box=8.5, dfl=2.0) to tighten box predictions past the IoU 0.50 threshold.
  6. High resolution (768px) fine-tuned from best converged weights.
  7. close_mosaic=8 so final epochs train on native road perspectives.

Run:
  python scripts/train_clean_v13.py [epochs] [imgsz] [batch]
"""
import faulthandler
import io
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

import cv2
import gc

cv2.setNumThreads(1)

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
RUN = "yolo11s_v13_clean_single"
LAST = ROOT / "runs" / RUN / "weights" / "last.pt"
START = ROOT / "runs" / "yolo11s_v11_verified" / "weights" / "best.pt"
if not START.exists():
    START = ROOT / "runs" / "yolo11s_v1" / "weights" / "best.pt"

DATA = ROOT / "dataset_verified" / "data_clean_single.yaml"


def _rearm(_trainer=None):
    faulthandler.cancel_dump_traceback_later()
    faulthandler.dump_traceback_later(300, repeat=False, file=sys.stderr)
    if _trainer is not None:
        iteration = getattr(_trainer, "iter", 0)
        if iteration % 100 == 0:
            gc.collect()
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.cdll.msvcrt._heapmin()
                except Exception:
                    pass


if __name__ == "__main__":
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    imgsz = int(sys.argv[2]) if len(sys.argv) > 2 else 768
    batch = int(sys.argv[3]) if len(sys.argv) > 3 else 2

    if LAST.exists():
        print(f"Resuming {RUN} from {LAST}", flush=True)
        model = YOLO(str(LAST))
        args = dict(resume=True)
    else:
        print(f"Fine-tuning {RUN} from {START} at {imgsz}px (Single-Class, Clean Dataset)", flush=True)
        model = YOLO(str(START))
        args = dict(
            data=str(DATA),
            project=str(ROOT / "runs"),
            name=RUN,
            exist_ok=True,
            imgsz=imgsz,
            batch=batch,
            epochs=epochs,
            patience=epochs + 5,
            workers=0,
            device=0,
            amp=True,
            cache=False,
            single_cls=True,
            optimizer="SGD",
            lr0=0.003,
            lrf=0.01,
            momentum=0.937,
            weight_decay=0.0005,
            warmup_epochs=1.0,
            cos_lr=True,
            box=8.5,
            cls=0.5,
            dfl=2.0,
            hsv_h=0.015,
            hsv_s=0.6,
            hsv_v=0.4,
            degrees=3.0,
            translate=0.1,
            scale=0.5,
            fliplr=0.5,
            mosaic=1.0,
            mixup=0.0,
            erasing=0.2,
            close_mosaic=8,
            plots=True,
            seed=0,
            val=True,
            save=True,
        )

    for ev in ("on_train_batch_end", "on_val_batch_end", "on_train_epoch_start", "on_val_start"):
        model.add_callback(ev, _rearm)
    _rearm()

    model.train(**args)
    faulthandler.cancel_dump_traceback_later()

    print("\n--- Running Final Clean Evaluation ---", flush=True)
    best_pt = ROOT / "runs" / RUN / "weights" / "best.pt"
    if best_pt.exists():
        eval_model = YOLO(str(best_pt))
        # Evaluate on clean test set
        m_clean = eval_model.val(data=str(DATA), split="test", imgsz=imgsz, batch=16, device=0, workers=0, single_cls=True)
        print(f"CLEAN TEST mAP@50: {m_clean.box.map50:.4f}  mAP@50-95: {m_clean.box.map:.4f}", flush=True)
        
        # Evaluate on Kolhapur test set
        kol_yaml = ROOT / "dataset_verified" / "data_clean_kolhapur.yaml"
        m_kol = eval_model.val(data=str(kol_yaml), split="test", imgsz=imgsz, batch=16, device=0, workers=0, single_cls=True)
        print(f"KOLHAPUR TEST mAP@50: {m_kol.box.map50:.4f}  mAP@50-95: {m_kol.box.map:.4f}", flush=True)

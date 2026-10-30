"""
Module 2 - YOLO11 training on the merged dataset (RTX 4060, 8 GB).
Run:  python train.py            (default yolo11s)
      python train.py yolo11n    (lightweight model for comparison)
"""
import faulthandler
import sys
from ultralytics import YOLO

if __name__ == "__main__":
    # python train.py resume yolo11s   -> continue a stopped run from its last epoch
    if len(sys.argv) > 2 and sys.argv[1] == "resume":
        # optional 3rd arg = number of data-loading workers (CPU processes preparing photos)
        extra = {"workers": int(sys.argv[3])} if len(sys.argv) > 3 else {}
        model = YOLO(f"F:/POTHOLE_PROJECT/runs/{sys.argv[2]}_v1/weights/last.pt")

        # Hang diagnostics: if no batch finishes for 2 minutes, Python writes the stack
        # of every thread to the log, showing exactly where training is stuck.
        def _rearm(_trainer=None):
            faulthandler.cancel_dump_traceback_later()
            faulthandler.dump_traceback_later(120, repeat=False, file=sys.stderr)
        for event in ("on_train_batch_end", "on_val_batch_end", "on_train_epoch_start", "on_val_start"):
            model.add_callback(event, _rearm)
        _rearm()

        model.train(resume=True, **extra)
        faulthandler.cancel_dump_traceback_later()
        sys.exit()
    model_name = sys.argv[1] if len(sys.argv) > 1 else "yolo11s"
    model = YOLO(f"{model_name}.pt")          # COCO-pretrained start
    model.train(
        data="F:/POTHOLE_PROJECT/dataset/data.yaml",
        project="F:/POTHOLE_PROJECT/runs",
        name=f"{model_name}_v1",
        epochs=100,
        patience=20,          # stop early if val mAP stops improving
        imgsz=640,
        batch=16,
        workers=4,
        device=0,
        cos_lr=True,
        close_mosaic=10,
        # augmentation for weather / lighting robustness
        hsv_h=0.015, hsv_s=0.6, hsv_v=0.5,
        degrees=3.0, translate=0.1, scale=0.5, fliplr=0.5, mosaic=1.0, mixup=0.1,
        plots=True,
        exist_ok=True,
    )
    metrics = model.val(split="test")
    print("TEST mAP50:", metrics.box.map50, " mAP50-95:", metrics.box.map)

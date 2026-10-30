"""
Training run v8 - CLEANED public data (clean_dataset.py) + checked Kolhapur frames, 20 epochs.

v6 = v1 training images + Kolhapur morning-ride frames whose model boxes were reviewed one by one
     by Claude (false alarms such as shadows, manholes, road markings, gravel, litter removed), x3,
     plus Kolhapur no-damage frames as negatives. Missed potholes were NOT added (needs the team).
Validation and test = the ORIGINAL sets, so the result compares fairly with v1.
Kolhapur afternoon (test) frames are NOT used.
Starts from v1 (models/final.pt) at 640 px and fine-tunes for 10 epochs.

Run:   python train_v8.py [workers]
"""
import faulthandler
import re
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
RUN = "yolo11s_v8_clean"
LAST = ROOT / "runs" / RUN / "weights" / "last.pt"


def test_map50(run):
    """Reads the test mAP50 ('All' row) from qa/evaluation_<run>.md."""
    f = ROOT / "qa" / f"evaluation_{run}.md"
    if not f.exists():
        return -1
    m = re.search(r"^\| All \|[^|]+\|[^|]+\|[^|]+\| ([0-9.]+) \|", f.read_text(encoding="utf-8"), re.M)
    return float(m.group(1)) if m else -1


def pick_base():
    scores = {"yolo11s_v1": (test_map50("yolo11s_v1"), 640), "yolo11s_v2_960": (test_map50("yolo11s_v2_960"), 960)}
    best = max(scores, key=lambda k: scores[k][0])
    print("test mAP50:", {k: v[0] for k, v in scores.items()}, "-> starting from", best, flush=True)
    return ROOT / "runs" / best / "weights" / "best.pt", scores[best][1]


def _rearm(_trainer=None):
    faulthandler.cancel_dump_traceback_later()
    faulthandler.dump_traceback_later(120, repeat=False, file=sys.stderr)


if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    data = ROOT / "dataset" / "data_v8.yaml"

    if LAST.exists():
        model, args = YOLO(str(LAST)), dict(resume=True, workers=workers)
    else:
        base, imgsz = ROOT / "models" / "final.pt", 640
        model = YOLO(str(base))
        args = dict(
            data=str(data), project=str(ROOT / "runs"), name=RUN, exist_ok=True,
            imgsz=imgsz, batch=16 if imgsz == 640 else 8,
            epochs=20, patience=10, workers=workers, device=0,
            optimizer="SGD", lr0=0.002, lrf=0.1, warmup_epochs=0.5, cos_lr=True,
            close_mosaic=5,
            hsv_h=0.015, hsv_s=0.6, hsv_v=0.5,
            degrees=3.0, translate=0.1, scale=0.5, fliplr=0.5, mosaic=1.0, mixup=0.1,
            plots=True,
        )

    for event in ("on_train_batch_end", "on_val_batch_end", "on_train_epoch_start", "on_val_start"):
        model.add_callback(event, _rearm)
    _rearm()
    model.train(**args)
    faulthandler.cancel_dump_traceback_later()

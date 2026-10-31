"""Quick probe: class-agnostic mAP@50 (localisation ceiling) + effect of TTA and imgsz.
Run: python scripts/probe_ceiling.py <run_or_weights> [imgsz]
"""
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
DATA = ROOT / "dataset/data.yaml"

w = sys.argv[1] if len(sys.argv) > 1 else "runs/yolo11s_v1/weights/best.pt"
if not w.endswith(".pt"):
    w = f"runs/{w}/weights/best.pt"
imgsz = int(sys.argv[2]) if len(sys.argv) > 2 else 640
model = YOLO(str(ROOT / w))

print(f"== {w} @ {imgsz} ==", flush=True)
for tag, kw in [("2class", {}), ("single_cls", dict(single_cls=True)),
                ("single_cls+TTA", dict(single_cls=True, augment=True)),
                ("2class+TTA", dict(augment=True))]:
    m = model.val(data=str(DATA), split="test", imgsz=imgsz, batch=8, device=0, workers=0,
                  plots=False, verbose=False, **kw)
    print(f"{tag:16s} P={m.box.mp:.4f} R={m.box.mr:.4f} mAP50={m.box.map50:.4f} "
          f"mAP50-95={m.box.map:.4f} per-class mAP50={[round(x, 4) for x in m.box.maps] if len(m.box.maps) > 1 else '-'}",
          flush=True)

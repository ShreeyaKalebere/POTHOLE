"""Does evaluating the SAME weights at a higher resolution raise mAP?
Run: python scripts/probe_imgsz.py <weights.pt> [--device=cpu] [--sizes=640,768,896,1024]
"""
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
DATA = ROOT / "dataset/data.yaml"


def main():
    argv = sys.argv[1:]
    w, device, sizes = None, "cpu", [640, 768, 896, 1024]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--device"):
            device = a.split("=")[1] if "=" in a else argv[i + 1]
            i += 1 if "=" in a else 2
            continue
        if a.startswith("--sizes"):
            sizes = [int(x) for x in (a.split("=")[1] if "=" in a else argv[i + 1]).split(",")]
            i += 1 if "=" in a else 2
            continue
        if not a.startswith("--"):
            w = a
        i += 1
    model = YOLO(str(ROOT / w))
    print(f"{w}  device={device}")
    for s in sizes:
        m = model.val(data=str(DATA), split="test", imgsz=s, batch=8, device=device, workers=0,
                      plots=False, verbose=False)
        print(f"imgsz={s:5d}  P={m.box.mp:.4f}  R={m.box.mr:.4f}  mAP50={m.box.map50:.4f}  "
              f"mAP50-95={m.box.map:.4f}", flush=True)


if __name__ == "__main__":
    main()

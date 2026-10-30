"""Evaluates v1 and v4 on the SAME validation photos (val_rest, used during v4 training),
to show why v4's validation numbers can't be compared with v1's."""
from ultralytics import YOLO

if __name__ == "__main__":
    for name, w in [("v1", "F:/POTHOLE_PROJECT/runs/yolo11s_v1/weights/best.pt"),
                    ("v4", "F:/POTHOLE_PROJECT/runs/yolo11s_v4_fixed/weights/best.pt")]:
        m = YOLO(w).val(data="F:/POTHOLE_PROJECT/dataset/data_v4.yaml", split="val", imgsz=640,
                        batch=16, workers=0, verbose=False, plots=False)
        print(f"RESULT {name}: P {m.box.mp:.3f}  R {m.box.mr:.3f}  mAP50 {m.box.map50:.3f}  mAP50-95 {m.box.map:.3f}",
              flush=True)

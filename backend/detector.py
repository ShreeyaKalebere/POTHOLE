from typing import List, Dict, Any, Optional
from pathlib import Path
import cv2
import numpy as np
import torch
from ultralytics import YOLO

def find_best_model_weights(base_dir: Optional[Path] = None) -> str:
    """Dynamically resolve the newest trained best.pt or fall back to yolo11n.pt."""
    search_root = base_dir if base_dir else Path(__file__).resolve().parent.parent
    
    candidates = sorted(
        list(search_root.glob("runs/**/weights/best.pt")) +
        list(search_root.glob("runs/**/weights/last.pt")) +
        list(search_root.glob("**/best.pt")),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if candidates:
        return str(candidates[0])
    
    # Fallback default pretrained backbone
    default_backbone = search_root / "yolo11n.pt"
    if default_backbone.exists():
        return str(default_backbone)
    return "yolo11n.pt"

def estimate_severity(class_name: str, box_norm_area: float) -> str:
    """
    Compute severity based on normalized bounding box surface area:
    - Pothole:
        * Low:    < 2%
        * Medium: 2% - 6%
        * High:   >= 6%
    - Alligator Crack:
        * Low:    < 4%
        * Medium: 4% - 10%
        * High:   >= 10%
    """
    cname = class_name.lower()
    if "pothole" in cname:
        if box_norm_area < 0.02:
            return "Low"
        elif box_norm_area < 0.06:
            return "Medium"
        else:
            return "High"
    elif "alligator" in cname or "crack" in cname:
        if box_norm_area < 0.04:
            return "Low"
        elif box_norm_area < 0.10:
            return "Medium"
        else:
            return "High"
    return "Medium"

class RoadDistressDetector:
    """Real-time YOLO11 inference engine for live video patrol and mobile camera stream."""

    def __init__(self, model_path: Optional[str] = None, conf_threshold: float = 0.25):
        resolved_path = model_path or find_best_model_weights()
        self.model_path = resolved_path
        self.conf_threshold = conf_threshold
        self.device = 0 if torch.cuda.is_available() else "cpu"
        
        print(f"[Detector] Loading YOLO11 model from: {resolved_path} (Device: {self.device})")
        self.model = YOLO(resolved_path)
        # Warmup
        try:
            dummy = np.zeros((320, 320, 3), dtype=np.uint8)
            self.model(dummy, device=self.device, verbose=False)
            print("[Detector] Model warmup complete.")
        except Exception as e:
            print(f"[Detector] Warmup skipped: {e}")

    def detect_frame(self, frame: np.ndarray, conf_threshold: Optional[float] = None) -> Dict[str, Any]:
        """
        Run inference on a single BGR OpenCV frame.
        Returns detection metadata and normalized box coordinates for frontend canvas rendering.
        """
        conf = conf_threshold or self.conf_threshold
        h, w = frame.shape[:2]
        frame_area = max(1, h * w)

        results = self.model(frame, conf=conf, device=self.device, verbose=False, imgsz=640)
        
        detections: List[Dict[str, Any]] = []
        highest_severity = "None"
        severity_order = {"None": 0, "Low": 1, "Medium": 2, "High": 3}

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = self.model.names.get(class_id, f"class_{class_id}")

                box_w = max(0.0, x2 - x1)
                box_h = max(0.0, y2 - y1)
                box_area = box_w * box_h
                norm_area = box_area / frame_area

                sev = estimate_severity(class_name, norm_area)
                if severity_order.get(sev, 0) > severity_order.get(highest_severity, 0):
                    highest_severity = sev

                # Normalized coordinates (0.0 to 1.0) for resolution-independent canvas drawing
                detections.append({
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": round(confidence, 3),
                    "severity": sev,
                    "box_pixels": [int(x1), int(y1), int(x2), int(y2)],
                    "box_norm": [
                        round(x1 / w, 4),
                        round(y1 / h, 4),
                        round(x2 / w, 4),
                        round(y2 / h, 4)
                    ],
                    "norm_area": round(norm_area, 4)
                })

        return {
            "num_detections": len(detections),
            "highest_severity": highest_severity,
            "detections": detections,
            "frame_dims": {"width": w, "height": h},
            "model_path": str(Path(self.model_path).name)
        }

# Global singleton instance loaded on demand
_detector_instance: Optional[RoadDistressDetector] = None

def get_detector() -> RoadDistressDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = RoadDistressDetector()
    return _detector_instance

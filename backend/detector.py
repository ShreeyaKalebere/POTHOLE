"""Module 2 - wraps the trained YOLO11 model."""
import os
import shutil
import threading
import time
import uuid
import zipfile
from pathlib import Path

import cv2

from config import MODEL_CANDIDATES, CONF_THRESHOLD, CLASS_NAMES, BACKEND_DIR, INFER_DEVICE
from severity import severity_score, severity_label

COLORS = {"Low": (80, 175, 76), "Medium": (0, 165, 255), "High": (54, 67, 244)}   # BGR


def boxes_to_dets(res, W, H):
    """Ultralytics result -> list of detection dicts (with track_id when tracking)."""
    dets = []
    ids = res.boxes.id
    for k, b in enumerate(res.boxes):
        cls = int(b.cls)
        name = CLASS_NAMES.get(cls, str(cls))
        x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
        xc, yc, w, h = (x1 + x2) / 2 / W, (y1 + y2) / 2 / H, (x2 - x1) / W, (y2 - y1) / H
        score = severity_score(xc, yc, w, h, name)
        dets.append({"damage_type": name, "confidence": round(float(b.conf), 3),
                     "bbox": [round(x1), round(y1), round(x2), round(y2)],
                     "bbox_norm": [round(xc, 4), round(yc, 4), round(w, 4), round(h, 4)],
                     "severity": severity_label(score, name), "severity_score": score,
                     "track_id": int(ids[k]) if ids is not None else None})
    return dets


def _valid_checkpoint(path):
    """A .pt file is a zip archive; a half-written copy fails this check."""
    try:
        with zipfile.ZipFile(path) as z:
            return z.testzip() is None
    except (zipfile.BadZipFile, OSError):
        return False


_copy_lock = threading.Lock()


def current_weights():
    """Path of the weights file the backend should use.
    Training rewrites best.pt / last.pt every epoch, so we copy to a temp file,
    verify it is complete, then swap it in. A good older copy is kept on failure."""
    with _copy_lock:
        for p in MODEL_CANDIDATES:
            if not p.exists():
                continue
            local = BACKEND_DIR / "models_cache" / p.name
            local.parent.mkdir(exist_ok=True)
            if local.exists() and local.stat().st_mtime >= p.stat().st_mtime and _valid_checkpoint(local):
                return local, p
            for _ in range(5):
                tmp = local.with_name(f"{local.stem}.{uuid.uuid4().hex[:6]}.tmp")
                try:
                    shutil.copy2(p, tmp)
                    if _valid_checkpoint(tmp):
                        os.replace(tmp, local)
                        return local, p
                finally:
                    if tmp.exists():
                        tmp.unlink()
                time.sleep(1)                     # training was mid-write; try again
            if local.exists() and _valid_checkpoint(local):
                return local, p                   # fall back to the last good copy
        raise RuntimeError("No model weights found yet. Train first (scripts/train.py).")


class Detector:
    def __init__(self):
        self.model = None
        self.model_path = None
        self.loaded_at = None
        self._lock = threading.Lock()

    def load(self):
        from ultralytics import YOLO
        local, src = current_weights()
        with self._lock:
            self.model = YOLO(str(local))
            self.model_path = str(src)
            self.loaded_at = time.time()
        return self.info()

    def info(self):
        return {"loaded": self.model is not None, "weights": self.model_path,
                "provisional": bool(self.model_path and "final.pt" not in self.model_path),
                "loaded_at": self.loaded_at}

    def detect(self, image_path, conf=CONF_THRESHOLD):
        if self.model is None:
            self.load()
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError("Could not read image")
        H, W = img.shape[:2]
        t0 = time.time()
        with self._lock:
            res = self.model.predict(img, conf=conf, device=INFER_DEVICE, verbose=False)[0]
        ms = (time.time() - t0) * 1000

        return boxes_to_dets(res, W, H), img, round(ms, 1)

    @staticmethod
    def annotate(img, dets, out_path):
        cv2.imwrite(str(out_path), Detector.draw(img, dets))

    @staticmethod
    def draw(img, dets):
        im = img.copy()
        th = max(2, im.shape[1] // 400)
        for d in dets:
            x1, y1, x2, y2 = d["bbox"]
            c = COLORS[d["severity"]]
            cv2.rectangle(im, (x1, y1), (x2, y2), c, th)
            label = f"{'Pothole' if d['damage_type'] == 'pothole' else 'Alligator'} {d['severity']} {d['confidence']:.2f}"
            if d.get("track_id") is not None:
                label = f"#{d['track_id']} " + label
            fs = max(0.5, im.shape[1] / 1600)
            (tw, tht), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, fs, th)
            lx = max(0, min(x1, im.shape[1] - tw - 6))          # keep label inside the image
            ly = y1 if y1 - tht - 8 >= 0 else y2 + tht + 8       # below the box if no room above
            cv2.rectangle(im, (lx, ly - tht - 8), (lx + tw + 6, ly), c, -1)
            cv2.putText(im, label, (lx + 3, ly - 5), cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 255, 255), th)
        return im


detector = Detector()

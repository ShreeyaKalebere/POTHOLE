"""
Live patrol - YOLO11 detection + ByteTrack tracking over a stream of frames
(phone camera frames, or frames read from a dashcam video).

Why tracking: the same pothole is visible in many consecutive frames. Without
tracking it would be saved 20-30 times. ByteTrack gives each damage a track ID;
an incident is saved ONCE per track, after the damage is confirmed:

    seen in >= MIN_HITS frames  AND  best confidence >= CONF_THRESHOLD

The saved photo is the frame where that track had its highest confidence so far.
Same damage seen again on a later drive is merged by GPS (incident_store, 15 m).
"""
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

import cv2

import media_store
from config import CONF_THRESHOLD, INFER_DEVICE
from detector import Detector, boxes_to_dets, current_weights
from incident_store import upsert_incident

TRACKER_CFG = str(Path(__file__).with_name("bytetrack_road.yaml"))
TRACK_CONF = 0.15        # low threshold so ByteTrack can keep weak detections attached to a track
MIN_HITS = 3             # frames a damage must be seen before it becomes an incident
SESSION_TIMEOUT_S = 120  # idle phone sessions are closed after 2 minutes
MAX_SESSIONS = 3


class TrackSession:
    def __init__(self, source="live"):
        from ultralytics import YOLO
        local, src = current_weights()
        self.model = YOLO(str(local))     # own model instance = own tracker state
        self.weights = str(src)
        self.id = uuid.uuid4().hex[:10]
        self.source = source
        self.started = time.time()
        self.last_seen = time.time()
        self.frames = 0
        self.tracks = {}                  # track_id -> {hits, best_conf, best, incident_id, type}
        self.saved = []                   # incidents created/merged in this session
        self.lock = threading.Lock()
        self._times = []

    def process(self, img, lat=None, lng=None, save=True, frame_time=None):
        """Runs detection + tracking on one frame. Returns (detections, newly_saved)."""
        with self.lock:
            t0 = time.time()
            res = self.model.track(img, persist=True, tracker=TRACKER_CFG, conf=TRACK_CONF, device=INFER_DEVICE,
                                   verbose=False)[0]
            H, W = img.shape[:2]
            dets = [d for d in boxes_to_dets(res, W, H)]
            self.frames += 1
            self.last_seen = time.time()
            self._times = (self._times + [time.time() - t0])[-30:]

            new = []
            for d in dets:
                tid = d["track_id"]
                if tid is None:
                    continue
                t = self.tracks.setdefault(tid, {"hits": 0, "best_conf": 0.0, "best": None,
                                                 "incident_id": None, "type": d["damage_type"]})
                t["hits"] += 1
                if d["confidence"] > t["best_conf"]:
                    t["best_conf"], t["best"] = d["confidence"], d
                d["confirmed"] = t["incident_id"] is not None
                if (save and t["incident_id"] is None and t["hits"] >= MIN_HITS
                        and t["best_conf"] >= CONF_THRESHOLD):
                    inc_id, is_new = self._save(img, t["best"], lat, lng, frame_time)
                    t["incident_id"] = inc_id
                    d["confirmed"] = True
                    entry = {"incident_id": inc_id, "new_incident": is_new, "track_id": tid,
                             "damage_type": d["damage_type"], "severity": t["best"]["severity"],
                             "confidence": t["best_conf"], "lat": lat, "lng": lng}
                    self.saved.append(entry)
                    new.append(entry)
            # only report boxes worth showing; weak ones are kept internally for tracking
            shown = [d for d in dets if d["confidence"] >= 0.25 or d.get("confirmed")]
            return shown, new

    def _save(self, img, det, lat, lng, frame_time):
        now = frame_time or datetime.now()
        name = f"{now:%Y%m%d_%H%M%S}_{self.source}_{self.id}_{det['track_id']}"
        raw_url = media_store.save_image(f"{name}.jpg", img)
        ann_url = media_store.save_image(f"{name}_det.jpg", Detector.draw(img, [det]))
        return upsert_incident(det, lat, lng, raw_url, ann_url, self.source, now)

    def summary(self):
        avg = sum(self._times) / len(self._times) if self._times else 0
        return {"session_id": self.id, "source": self.source, "weights": self.weights,
                "frames": self.frames, "tracks": len(self.tracks),
                "incidents_saved": sum(1 for s in self.saved if s["new_incident"]),
                "incidents_merged": sum(1 for s in self.saved if not s["new_incident"]),
                "avg_inference_ms": round(avg * 1000, 1),
                "duration_s": round(time.time() - self.started, 1)}


# ---------------------------------------------------------------- session registry (phone mode)
_sessions = {}
_reg_lock = threading.Lock()


def _expire():
    now = time.time()
    for sid in [s for s, v in _sessions.items() if now - v.last_seen > SESSION_TIMEOUT_S]:
        _sessions.pop(sid, None)


def start_session():
    with _reg_lock:
        _expire()
        if len(_sessions) >= MAX_SESSIONS:
            oldest = min(_sessions.values(), key=lambda s: s.last_seen)
            _sessions.pop(oldest.id, None)
        s = TrackSession("live")
        _sessions[s.id] = s
        return s


def get_session(sid):
    with _reg_lock:
        _expire()
        return _sessions.get(sid)


def stop_session(sid):
    with _reg_lock:
        return _sessions.pop(sid, None)


def active_sessions():
    with _reg_lock:
        _expire()
        return [s.summary() for s in _sessions.values()]

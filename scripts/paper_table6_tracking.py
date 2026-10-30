"""Table VI (tracking part) - runs the ByteTrack live-patrol pipeline (backend/live.py, same code as
the phone Live Patrol) over Kolhapur clips and counts the incident records it produces.

Distinct physical defects per clip must be counted by a PERSON watching the clip; this script
leaves that column empty ("not measured") on purpose. GPS: the clip's start GPS from the MP4
metadata is used for every frame (the videos store only one GPS point).
Records are written to a separate database (road_damage_tracktest) which is dropped at the end.
Run: python paper_table6_tracking.py
"""
import csv
import os
import re
import sys
import time
from pathlib import Path

os.environ["DB_NAME"] = "road_damage_tracktest"
os.environ.setdefault("INFER_DEVICE", "0")
sys.path.insert(0, "F:/POTHOLE_PROJECT/backend")
import cv2  # noqa: E402
from live import TrackSession  # noqa: E402
from db import client  # noqa: E402

ROOT = Path("F:/POTHOLE_PROJECT")
SRC = ROOT / "new testing dataset"
CLIPS = ["Shree/20261027_134820.mp4", "Shree/20261027_140627.mp4", "Shree/20261027_141627.mp4",
         "Shree/20261027_143831.mp4", "Shree/20261027_155111.mp4", "shubh/VID_20261027_135754125.mp4",
         "shubh/VID_20261027_150632852.mp4", "shubh/VID_20261027_154417601.mp4"]
EVERY = 6   # process every 6th frame of 30 fps video = 5 frames/s, similar to phone Live Patrol


def start_gps(path):
    with open(path, "rb") as f:
        head = f.read(4_000_000)
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 4_000_000))
        tail = f.read()
    m = re.search(rb"([+-]\d{1,2}\.\d{3,})([+-]\d{1,3}\.\d{3,})", head + tail)
    if not m or float(m.group(1)) == 0:
        return None, None
    return float(m.group(1)), float(m.group(2))


def main():
    rows = []
    for clip in CLIPS:
        p = SRC / clip
        lat, lng = start_gps(p)
        cap = cv2.VideoCapture(str(p))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        s = TrackSession(source="video")
        idx, t0 = -1, time.perf_counter()
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            idx += 1
            if idx % EVERY:
                continue
            s.process(frame, lat, lng, save=True)
        cap.release()
        sm = s.summary()
        rows.append([clip, round(idx / fps, 1), sm["frames"], sm["tracks"], len(s.saved), sm["incidents_saved"],
                     sm["incidents_merged"], sm["avg_inference_ms"], f"{lat},{lng}" if lat else "no GPS in file",
                     "not measured (needs a person to watch the clip)", "not measured", "not measured"])
        print(rows[-1], f"processing {time.perf_counter() - t0:.0f}s", flush=True)
    with open(ROOT / "paper_results/table6_tracking.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["clip", "duration_s", "frames_processed(5/s)", "track_ids_created", "confirmed_tracks(records)",
                    "new_incident_records", "merged_into_existing(<=15m)", "avg_inference+tracking_ms",
                    "gps_used(clip start)", "distinct_defects(manual)", "duplicate_rate", "id_splits"])
        w.writerows(rows)
    client.drop_database("road_damage_tracktest")


if __name__ == "__main__":
    main()

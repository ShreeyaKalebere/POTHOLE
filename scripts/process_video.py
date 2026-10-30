"""
Module 5 - Run a recorded road / dashcam video through the full pipeline:
YOLO11 detection -> ByteTrack tracking -> severity -> GPS -> MongoDB incidents.
Writes an annotated output video with track IDs.

GPS options (pick one):
  --lat 16.70 --lng 74.24          one fixed location for the whole video
  --gps track.csv                  CSV with columns  seconds,lat,lng  (time in video -> position);
                                   positions between rows are interpolated
  (none)                           incidents are saved without location

Examples:
  python process_video.py --video F:/videos/road1.mp4 --lat 16.6985 --lng 74.2335
  python process_video.py --video road1.mp4 --gps road1_gps.csv --every 2
  python process_video.py --video road1.mp4 --no-save        (only make the annotated video)
"""
import argparse
import bisect
import csv
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from live import TrackSession          # noqa: E402
from detector import Detector          # noqa: E402

OUT_DIR = Path(__file__).resolve().parent.parent / "runs" / "videos"


def load_gps(path):
    rows = sorted((float(r["seconds"]), float(r["lat"]), float(r["lng"]))
                  for r in csv.DictReader(open(path, encoding="utf-8-sig")))
    ts = [r[0] for r in rows]

    def at(t):
        i = bisect.bisect_left(ts, t)
        if i <= 0:
            return rows[0][1:]
        if i >= len(rows):
            return rows[-1][1:]
        (t0, a0, b0), (t1, a1, b1) = rows[i - 1], rows[i]
        f = (t - t0) / (t1 - t0) if t1 > t0 else 0
        return a0 + f * (a1 - a0), b0 + f * (b1 - b0)
    return at


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lng", type=float)
    ap.add_argument("--gps", help="CSV: seconds,lat,lng")
    ap.add_argument("--every", type=int, default=1, help="process every Nth frame (2 = twice as fast)")
    ap.add_argument("--no-save", action="store_true", help="do not write incidents to MongoDB")
    ap.add_argument("--start", default=None, help="recording start time 'YYYY-MM-DD HH:MM' (default: now)")
    a = ap.parse_args()

    cap = cv2.VideoCapture(a.video)
    if not cap.isOpened():
        sys.exit(f"Cannot open video {a.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    gps_at = load_gps(a.gps) if a.gps else (lambda t: (a.lat, a.lng))
    start = datetime.strptime(a.start, "%Y-%m-%d %H:%M") if a.start else datetime.now()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{Path(a.video).stem}_tracked.mp4"
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps / a.every, (W, H))

    s = TrackSession(source="video")
    print(f"Video {W}x{H} @ {fps:.1f} fps, {total} frames | weights: {s.weights}")
    t_start, idx = time.time(), -1
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx += 1
        if idx % a.every:
            continue
        sec = idx / fps
        lat, lng = gps_at(sec)
        dets, new = s.process(frame, lat, lng, save=not a.no_save,
                              frame_time=start + timedelta(seconds=sec))
        vis = Detector.draw(frame, dets)
        cv2.putText(vis, f"t={sec:6.1f}s  tracks={len(s.tracks)}  incidents={len(s.saved)}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        writer.write(vis)
        for n in new:
            print(f"  [{sec:6.1f}s] track #{n['track_id']} {n['damage_type']} {n['severity']} "
                  f"conf {n['confidence']:.2f} -> {'NEW' if n['new_incident'] else 'merged'} incident")
        if idx % 100 == 0 and total:
            el = time.time() - t_start
            print(f"  {idx}/{total} frames  ({idx / max(el, 1e-6):.1f} frames/s)")

    cap.release()
    writer.release()
    summ = s.summary()
    summ["processing_fps"] = round(s.frames / max(time.time() - t_start, 1e-6), 1)
    print("\nDone:", summ)
    print("Annotated video:", out_path)


if __name__ == "__main__":
    main()

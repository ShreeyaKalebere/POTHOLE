"""
Imports the team's Kolhapur field photos (27 Oct) as incidents for inspection in the dashboard.

Each photo with GPS is run through the current model; every detected damage is saved at the
photo's REAL GPS position and capture time (same 15 m merge rule as live patrol).
Records are tagged source="kolhapur_field" and demo=True, so "Clear demo data" removes them too.
Video frames are NOT used: the videos only store the GPS point where recording started.

Run (from the backend folder):  python import_field_photos.py
"""
import glob
from datetime import datetime
from pathlib import Path

from PIL import Image

from config import PROJECT_DIR
from db import incidents, init_indexes
from detector import detector
from gps import exif_gps
from incident_store import upsert_incident
import media_store

SRC = PROJECT_DIR / "new testing dataset"


def taken_at(path):
    try:
        v = Image.open(path).getexif().get_ifd(0x8769).get(36867)     # DateTimeOriginal
        return datetime.strptime(v, "%Y:%m:%d %H:%M:%S")
    except Exception:
        return datetime.fromtimestamp(Path(path).stat().st_mtime)


def main():
    init_indexes()
    # remove an earlier import so running this twice does not duplicate anything
    old = incidents.delete_many({"source": "kolhapur_field"}).deleted_count
    if old:
        print("removed previous import:", old)
    stats = dict(photos=0, no_gps=0, no_damage=0, new=0, merged=0)
    for p in sorted(glob.glob(str(SRC / "*" / "*.jpg"))):
        stats["photos"] += 1
        lat, lng = exif_gps(p)
        if lat is None:
            stats["no_gps"] += 1
            continue
        dets, img, _ = detector.detect(p)
        if not dets:
            stats["no_damage"] += 1
            continue
        when = taken_at(p)
        name = f"field/{Path(p).parent.name}_{Path(p).stem}"
        raw_url = media_store.save_image(f"{name}.jpg", img)
        ann_url = media_store.save_image(f"{name}_det.jpg", detector.draw(img, dets))
        for d in dets:
            inc_id, is_new = upsert_incident(d, lat, lng, raw_url, ann_url, "kolhapur_field", when)
            stats["new" if is_new else "merged"] += 1
    n = incidents.update_many({"source": "kolhapur_field"},
                              {"$set": {"demo": True, "field_test": True}}).modified_count
    print(stats, "| incidents on the map:", n)


if __name__ == "__main__":
    main()

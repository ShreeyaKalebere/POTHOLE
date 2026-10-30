"""
Fills MongoDB with DEMO incidents around Kolhapur so the dashboard can be shown
before real field data exists. Every demo record has demo=True and can be removed
with:  DELETE /api/demo   (or the "Clear demo data" button in the dashboard).

Photos are real test-set images from our dataset with their ground-truth boxes;
locations, dates and statuses are randomly generated.
Run:  python seed_demo.py 120
"""
import glob
import random
import sys
from datetime import datetime, timedelta

import cv2

import media_store
from config import PROJECT_DIR, CLASS_NAMES
from db import incidents, init_indexes, next_incident_code
from detector import Detector
from severity import severity_score, severity_label
from zones import ZONES, zone_for

TEAMS = ["Ward Team A", "Ward Team B", "Road Repair Unit 1", "Road Repair Unit 2", "PWD Contractor"]


def seed(n=120):
    init_indexes()
    random.seed()
    labels = [p for p in glob.glob(str(PROJECT_DIR / "dataset/labels/test/*.txt"))
              if open(p).read().strip()]
    random.shuffle(labels)
    now = datetime.now()
    inserted = 0
    for lp in labels[:n]:
        lines = [l.split() for l in open(lp) if l.strip()]
        c, xc, yc, w, h = int(lines[0][0]), *map(float, lines[0][1:5])
        dtype = CLASS_NAMES[c]
        ip = glob.glob(lp.replace("labels", "images")[:-4] + ".*")
        if not ip:
            continue
        img = cv2.imread(ip[0])
        if img is None:
            continue
        H, W = img.shape[:2]
        score = severity_score(xc, yc, w, h, dtype)
        sev = severity_label(score, dtype)
        det = {"damage_type": dtype, "confidence": round(random.uniform(0.55, 0.95), 2), "severity": sev,
               "bbox": [int((xc - w / 2) * W), int((yc - h / 2) * H), int((xc + w / 2) * W), int((yc + h / 2) * H)]}
        stem = f"demo_{inserted:04d}"
        url = media_store.save_image(f"demo/{stem}.jpg", img)
        media_store.save_image(f"demo/{stem}_det.jpg", Detector.draw(img, [det]))

        zname = random.choice(list(ZONES))
        zl, zg = ZONES[zname]
        lat, lng = zl + random.gauss(0, 0.004), zg + random.gauss(0, 0.004)
        detected = now - timedelta(days=random.randint(0, 29), hours=random.randint(0, 23),
                                   minutes=random.randint(0, 59))
        status = random.choices(["Reported", "In Progress", "Repaired"], [0.55, 0.25, 0.20])[0]
        team = random.choice(TEAMS) if status != "Reported" else None
        hist = [{"at": detected, "status": "Reported", "by": "system", "note": "Detected via live patrol (demo)"}]
        updated = detected
        if status != "Reported":
            updated = detected + timedelta(hours=random.randint(2, 48))
            hist.append({"at": updated, "status": "In Progress", "by": "officer", "note": f"Assigned to {team}"})
        if status == "Repaired":
            updated += timedelta(hours=random.randint(12, 96))
            hist.append({"at": updated, "status": "Repaired", "by": team, "note": "Repair completed"})
        incidents.insert_one({
            "incident_code": next_incident_code(), "damage_type": dtype, "severity": sev,
            "severity_score": score, "confidence": det["confidence"],
            "location": {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]},
            "zone": zone_for(lat, lng), "status": status, "assigned_to": team,
            "reports_count": random.choices([1, 2, 3, 4], [0.6, 0.25, 0.1, 0.05])[0],
            "source": "demo", "demo": True,
            "images": [{"url": url, "annotated_url": url.replace(".jpg", "_det.jpg"), "bbox": det["bbox"],
                        "confidence": det["confidence"], "severity": sev, "at": detected}],
            "detected_at": detected, "updated_at": updated, "history": hist,
        })
        inserted += 1
    return inserted


if __name__ == "__main__":
    print("inserted", seed(int(sys.argv[1]) if len(sys.argv) > 1 else 120))

"""
Replaces the photos of the DEMO incidents (source="demo") with real Kolhapur road photos.

Photos come from the team's 27 Oct recordings: the frames where Claude's box-by-box review
confirmed real damage (qa/kol_review). Each demo incident gets one frame + its confirmed box;
damage type and severity are recomputed from that box. Location, status, history and dates of
the demo incidents are unchanged (they stay demo records - their map positions are not real).

Run (from the backend folder):  python demo_use_kolhapur_photos.py
"""
import json
import random

import cv2

from config import PROJECT_DIR, CLASS_NAMES
from db import incidents
from detector import Detector
from severity import severity_score, severity_label
import media_store

REVIEW = PROJECT_DIR / "qa" / "kol_review"
FRAMES = PROJECT_DIR / "kolhapur_labeling" / "train"


def confirmed_boxes():
    dec = {}
    for line in open(REVIEW / "decisions.txt"):
        v = line.split()
        if len(v) == 2 and v[0].isdigit():
            dec[int(v[0])] = v[1]
    out = []
    for it in json.load(open(REVIEW / "index.json")):
        d = dec.get(it["n"], "K")
        if d == "R":
            continue
        v = open(FRAMES / "labels" / f"{it['stem']}.txt").read().splitlines()[it["line"]].split()
        c = {"P": 0, "A": 1}.get(d, int(v[0]))
        out.append((it["stem"], c, *map(float, v[1:5])))
    return out


def main():
    items = confirmed_boxes()
    print("confirmed Kolhapur damage boxes:", len(items))
    # prepare one stored photo pair per confirmed box
    prepared = []
    for k, (stem, c, xc, yc, w, h) in enumerate(items):
        img = cv2.imread(str(FRAMES / "images" / f"{stem}.jpg"))
        H, W = img.shape[:2]
        dtype = CLASS_NAMES[c]
        score = severity_score(xc, yc, w, h, dtype)
        det = {"damage_type": dtype, "severity": severity_label(score, dtype), "severity_score": score,
               "confidence": 0.0,
               "bbox": [int((xc - w / 2) * W), int((yc - h / 2) * H), int((xc + w / 2) * W), int((yc + h / 2) * H)]}
        name = f"demo_kol/kol_{k:04d}"
        url = media_store.save_image(f"{name}.jpg", img)
        prepared.append((det, url, name, img))
    demos = list(incidents.find({"source": "demo"}, {"_id": 1, "confidence": 1}))
    random.seed(7)
    random.shuffle(demos)
    drawn = set()
    for i, doc in enumerate(demos):
        det, url, name, img = prepared[i % len(prepared)]
        det = {**det, "confidence": doc.get("confidence", 0.8)}
        ann = f"/media/{name}_det.jpg"
        if name not in drawn:                      # annotated image drawn once per photo
            media_store.save_image(f"{name}_det.jpg", Detector.draw(img, [det]))
            drawn.add(name)
        incidents.update_one({"_id": doc["_id"]}, {"$set": {
            "damage_type": det["damage_type"], "severity": det["severity"],
            "severity_score": det["severity_score"],
            "images": [{"url": url, "annotated_url": ann, "bbox": det["bbox"],
                        "confidence": det["confidence"], "severity": det["severity"]}],
            "photo_source": "kolhapur_27oct"}})
    print(f"updated {len(demos)} demo incidents using {len(prepared)} different Kolhapur photos")


if __name__ == "__main__":
    main()

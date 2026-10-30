"""
Turns the Kolhapur field recordings into pre-labelled frames for the team to correct.

Input : F:/POTHOLE_PROJECT/new testing dataset/<person>/*.mp4 and *.jpg
Output: F:/POTHOLE_PROJECT/kolhapur_labeling/
          train/  images/  labels/  previews/     morning rides  -> become training data
          test/   images/  labels/  previews/     afternoon ride -> Kolhapur TEST set (never trained on)
          classes.txt, data.yaml, frames.csv

Split is by RECORDING TIME, not by person: several phones filmed the same road at the
same moment, and those copies must stay on the same side (otherwise the test is unfair).

Run:  python prepare_kolhapur.py
"""
import csv
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
SRC = ROOT / "new testing dataset"
OUT = ROOT / "kolhapur_labeling"
TEST_FROM = "15:00"          # recordings started at/after this time -> Kolhapur test set
EVERY_SEC = 1.5              # one frame every 1.5 s of video
MAX_W = 1920                 # 4K frames are shrunk to 1920 px wide
DUP_HAMMING = 4              # frame almost identical to the last kept one (stopped vehicle) -> skip
BLUR_FACTOR = 0.35           # sharpness below 35% of that video's median -> skip
PRELABEL_CONF = 0.25

sys.path.insert(0, str(ROOT / "backend"))
from detector import Detector, boxes_to_dets  # noqa: E402


def start_time(p):
    m = re.search(r"(\d{8})_(\d{6})", p.name)
    return datetime.strptime("".join(m.groups()), "%Y%m%d%H%M%S") if m else None


def split_for(p):
    t = start_time(p)
    return "test" if t and t.strftime("%H:%M") >= TEST_FROM else "train"


def dhash(img):
    g = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (9, 8), interpolation=cv2.INTER_AREA)
    return int("".join("1" if b else "0" for b in (g[:, 1:] > g[:, :-1]).flatten()), 2)


def sharpness(img):
    return cv2.Laplacian(cv2.cvtColor(cv2.resize(img, (640, 360)), cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()


def shrink(img):
    h, w = img.shape[:2]
    return cv2.resize(img, (MAX_W, int(h * MAX_W / w)), interpolation=cv2.INTER_AREA) if w > MAX_W else img


def video_frames(path):
    """Yields (second, frame) every EVERY_SEC seconds, skipping duplicates and blurry frames."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step = max(1, round(fps * EVERY_SEC))
    cand, idx = [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if idx % step == 0:
            ok, fr = cap.retrieve()
            if ok:
                fr = shrink(fr)
                cand.append((idx / fps, fr, sharpness(fr)))
        idx += 1
    cap.release()
    if not cand:
        return
    med = float(np.median([c[2] for c in cand]))
    last = None
    for sec, fr, sh in cand:
        if sh < BLUR_FACTOR * med:
            continue
        h = dhash(fr)
        if last is not None and bin(h ^ last).count("1") <= DUP_HAMMING:
            continue
        last = h
        yield sec, fr


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    for sp in ("train", "test"):
        for sub in ("images", "labels", "previews"):
            (OUT / sp / sub).mkdir(parents=True)
    model = YOLO(str(ROOT / "models/final.pt"))
    rows = []

    def save(sp, name, img, source, person, second=""):
        r = model.predict(img, conf=PRELABEL_CONF, verbose=False)[0]
        H, W = img.shape[:2]
        dets = boxes_to_dets(r, W, H)
        cv2.imwrite(str(OUT / sp / "images" / f"{name}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        with open(OUT / sp / "labels" / f"{name}.txt", "w") as f:
            for d in dets:
                c = 0 if d["damage_type"] == "pothole" else 1
                xc, yc, w, h = d["bbox_norm"]
                f.write(f"{c} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")
        cv2.imwrite(str(OUT / sp / "previews" / f"{name}.jpg"),
                    cv2.resize(Detector.draw(img, dets), (960, int(960 * H / W))), [cv2.IMWRITE_JPEG_QUALITY, 80])
        rows.append([sp, f"{name}.jpg", person, source, second, len(dets)])

    videos = sorted(SRC.glob("*/*.mp4"))
    for k, v in enumerate(videos, 1):
        person, sp = v.parent.name, split_for(v)
        n = 0
        for sec, fr in video_frames(v):
            save(sp, f"{person}_{v.stem}_{int(sec):04d}s", fr, v.name, person, f"{sec:.1f}")
            n += 1
        print(f"[{k}/{len(videos)}] {person}/{v.name} -> {sp}: {n} frames", flush=True)

    for p in sorted(SRC.glob("*/*.jpg")):
        img = cv2.imread(str(p))
        if img is not None:
            save(split_for(p), f"{p.parent.name}_{p.stem}", shrink(img), p.name, p.parent.name)
    print(f"photos added: {len(list(SRC.glob('*/*.jpg')))}", flush=True)

    with open(OUT / "frames.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["split", "image", "person", "source_file", "second_in_video", "prelabel_boxes"])
        w.writerows(rows)
    (OUT / "classes.txt").write_text("pothole\nalligator_crack\n")
    (OUT / "data.yaml").write_text("nc: 2\nnames: ['pothole', 'alligator_crack']\n")
    for sp in ("train", "test"):
        imgs = [r for r in rows if r[0] == sp]
        print(f"{sp}: {len(imgs)} images, {sum(r[5] > 0 for r in imgs)} with pre-labelled damage, "
              f"{sum(r[5] for r in imgs)} boxes")


if __name__ == "__main__":
    main()

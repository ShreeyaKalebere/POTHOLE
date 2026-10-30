"""
Condition augmentation for YOLO11 - simulates the situations where the model fails
(found in qa/missed/): rain / wet roads, night & dusk, motion blur from a two-wheeler,
tree & building shadows, fog / haze.

Only colour / lighting / blur effects are used - nothing moves or resizes the image,
so the existing YOLO labels stay exactly valid and are simply copied.
(YOLO's own mosaic / flip / scale / HSV augmentation still runs on top during training.)

Output (added to training, originals untouched):
    dataset/images/train_cond/<name>_<condition>.jpg
    dataset/labels/train_cond/<name>_<condition>.txt

Run:
    python make_condition_aug.py --preview      -> qa/condition_aug_preview.jpg (look first)
    python make_condition_aug.py --run          -> creates the augmented training images
"""
import argparse
import random
import shutil
from pathlib import Path

import albumentations as A
import cv2
import numpy as np

ROOT = Path("F:/POTHOLE_PROJECT")
SRC_IMG, SRC_LBL = ROOT / "dataset/images/train", ROOT / "dataset/labels/train"
OUT_IMG, OUT_LBL = ROOT / "dataset/images/train_cond", ROOT / "dataset/labels/train_cond"
INDIAN = ("BharatPotHole__", "IndianRoads__", "RDD2022_India__", "RoboflowIIT__")
OTHERS_FRACTION = 0.25          # share of non-Indian images that also get one augmented copy
SEED = 42

CONDITIONS = {
    # wet road: rain streaks, darker, a little blur, lower contrast
    "rain": A.Compose([
        A.RandomBrightnessContrast(brightness_limit=(-0.30, -0.15), contrast_limit=(-0.25, -0.1), p=1),
        A.RandomRain(slant_range=(-12, 12), drop_length=20, drop_width=1, blur_value=3,
                     brightness_coefficient=0.85, rain_type="default", p=1),
        A.GaussianBlur(blur_limit=(3, 5), p=0.5),
    ]),
    # dusk / night: dark, noisy sensor, sometimes headlight / street-light glare
    "night": A.Compose([
        A.RandomGamma(gamma_limit=(160, 220), p=1),          # darkens but keeps road detail visible
        A.RandomBrightnessContrast(brightness_limit=(-0.30, -0.15), contrast_limit=0, p=1),
        A.HueSaturationValue(hue_shift_limit=(0, 8), sat_shift_limit=(-30, -10), val_shift_limit=0, p=1),
        A.GaussNoise(std_range=(0.02, 0.05), p=1),
    ]),
    # phone shaking on a moving two-wheeler
    "motion": A.Compose([
        A.MotionBlur(blur_limit=(9, 17), p=1),
        A.RandomBrightnessContrast(brightness_limit=0.1, contrast_limit=0.1, p=0.5),
    ]),
    # shadows of trees / buildings across the road
    "shadow": A.Compose([
        A.RandomShadow(shadow_roi=(0, 0.35, 1, 1), num_shadows_limit=(1, 2), shadow_dimension=8,
                       shadow_intensity_range=(0.2, 0.4), p=1),
        A.GaussianBlur(blur_limit=(3, 3), p=1),                # soften the shadow edges
    ]),
    # morning haze / dust
    "fog": A.Compose([
        A.RandomFog(fog_coef_range=(0.15, 0.35), alpha_coef=0.08, p=1),
    ]),
}
# shadow polygons look artificial, so they are used rarely
WEIGHTS = {"rain": 0.33, "night": 0.32, "motion": 0.20, "shadow": 0.05, "fog": 0.10}


def pick_images():
    rnd = random.Random(SEED)
    chosen = []
    for img in sorted(SRC_IMG.iterdir()):
        lbl = SRC_LBL / f"{img.stem}.txt"
        if not lbl.exists() or lbl.stat().st_size == 0:
            continue                                  # only images that contain damage
        if img.name.startswith(INDIAN) or rnd.random() < OTHERS_FRACTION:
            chosen.append(img)
    return chosen


def augment(img_bgr, cond):
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    out = CONDITIONS[cond](image=rgb)["image"]
    return cv2.cvtColor(out, cv2.COLOR_RGB2BGR)


def preview():
    rnd = random.Random(7)
    imgs = [p for p in pick_images() if p.name.startswith(INDIAN)]
    rows = []
    for p in rnd.sample(imgs, 3):
        im = cv2.imread(str(p))
        tiles = [im] + [augment(im, c) for c in CONDITIONS]
        tiles = [cv2.resize(t, (320, 240)) for t in tiles]
        for t, name in zip(tiles, ["original"] + list(CONDITIONS)):
            cv2.rectangle(t, (0, 0), (110, 26), (0, 0, 0), -1)
            cv2.putText(t, name, (6, 19), 0, 0.6, (255, 255, 255), 2)
        rows.append(np.hstack(tiles))
    out = ROOT / "qa/condition_aug_preview.jpg"
    cv2.imwrite(str(out), np.vstack(rows))
    print("preview saved:", out)


def run():
    rnd = random.Random(SEED)
    for d in (OUT_IMG, OUT_LBL):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
    imgs = pick_images()
    counts = {c: 0 for c in CONDITIONS}
    for k, p in enumerate(imgs):
        cond = rnd.choices(list(WEIGHTS), weights=list(WEIGHTS.values()))[0]
        im = cv2.imread(str(p))
        if im is None:
            continue
        cv2.imwrite(str(OUT_IMG / f"{p.stem}_{cond}.jpg"), augment(im, cond), [cv2.IMWRITE_JPEG_QUALITY, 90])
        shutil.copy2(SRC_LBL / f"{p.stem}.txt", OUT_LBL / f"{p.stem}_{cond}.txt")
        counts[cond] += 1
        if k % 1000 == 0:
            print(f"{k}/{len(imgs)}", flush=True)
    print("created", sum(counts.values()), "augmented images:", counts)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.run:
        run()
    else:
        preview()

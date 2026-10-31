"""Build review sheets for suspicious test labels.
  phantom : GT boxes the model cannot find at all (delete-candidates)
  missed  : confident detections with no GT box (label-missed-candidates)
Run: python scripts/review_suspects.py <name> [n]
Out: qa/review_<name>_phantom.jpg, qa/review_<name>_missed.jpg
"""
import csv
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path("F:/POTHOLE_PROJECT")
D = ROOT / "dataset"
TILE, COLS, ROWS = 420, 4, 3


def load(path):
    rows = list(csv.DictReader(open(path)))
    return rows


def sheet(rows, kind, out):
    random.seed(1)
    pick = random.sample(rows, min(len(rows), COLS * ROWS))
    canvas = Image.new("RGB", (COLS * TILE, ROWS * TILE), (18, 18, 18))
    for i, r in enumerate(pick):
        p = D / "images/test" / r["image"]
        im = Image.open(p).convert("RGB")
        w, h = im.size
        im = im.resize((TILE, TILE))
        d = ImageDraw.Draw(im)
        if kind == "phantom":
            x1, y1, bw, bh = float(r["x1"]), float(r["y1"]), float(r["w"]), float(r["h"])
            d.rectangle([x1 / w * TILE, y1 / h * TILE, (x1 + bw) / w * TILE, (y1 + bh) / h * TILE],
                        outline=(255, 0, 255), width=4)
        else:
            x1, y1, bw, bh = float(r["x1"]), float(r["y1"]), float(r["w"]), float(r["h"])
            d.rectangle([x1 / w * TILE, y1 / h * TILE, (x1 + bw) / w * TILE, (y1 + bh) / h * TILE],
                        outline=(0, 255, 255), width=4)
        d.text((5, 5), f"{r['source'][:18]} {r['image'][-16:]}", fill=(255, 255, 0))
        canvas.paste(im, ((i % COLS) * TILE, (i // COLS) * TILE))
    canvas.save(out, quality=88)
    print("wrote", out)


if __name__ == "__main__":
    name = sys.argv[1]
    a = ROOT / f"qa/diagnose_{name}_unmatched_gt.csv"
    b = ROOT / f"qa/diagnose_{name}_extra_preds.csv"
    if a.exists():
        sheet(load(a), "phantom", ROOT / f"qa/review_{name}_phantom.jpg")
    if b.exists():
        sheet(load(b), "missed", ROOT / f"qa/review_{name}_missed.jpg")

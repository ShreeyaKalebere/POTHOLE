"""
Visual QA sheets: 4x3 grid per data source with ground-truth boxes drawn
(green = pothole, red = alligator_crack).  Used to judge whether a source's
class convention matches the others.

Run:  python scripts/make_source_sheets.py [split] [n_per_sheet]
Out:  qa/sheets/<source>.jpg
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path("F:/POTHOLE_PROJECT")
D = ROOT / "dataset"
OUT = ROOT / "qa" / "sheets"
COLOR = {0: (0, 220, 0), 1: (255, 60, 60)}
TILE = 420
COLS, ROWS = 4, 3


def draw(img_path, lab_path, tile=TILE):
    im = Image.open(img_path).convert("RGB")
    w, h = im.size
    im = im.resize((tile, tile))
    d = ImageDraw.Draw(im)
    if lab_path.exists():
        for line in lab_path.read_text().splitlines():
            v = line.split()
            if len(v) != 5:
                continue
            c, x, y, bw, bh = int(v[0]), *map(float, v[1:])
            x1, y1 = (x - bw / 2) * tile, (y - bh / 2) * tile
            x2, y2 = (x + bw / 2) * tile, (y + bh / 2) * tile
            d.rectangle([x1, y1, x2, y2], outline=COLOR.get(c, (0, 0, 255)), width=3)
    d.text((6, 6), Path(img_path).stem[:34], fill=(255, 255, 0))
    return im


def main():
    split = sys.argv[1] if len(sys.argv) > 1 else "test"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.load(open(D / "manifest.json"))
    by_src = defaultdict(list)
    for m in manifest:
        if m["split"] == split:
            by_src[m["source"]].append(m["file"])
    random.seed(3)
    for src, files in sorted(by_src.items()):
        pick = random.sample(files, min(n, len(files)))
        sheet = Image.new("RGB", (COLS * TILE, ROWS * TILE), (20, 20, 20))
        for i, f in enumerate(pick):
            im = draw(D / "images" / split / f, D / "labels" / split / (Path(f).stem + ".txt"))
            sheet.paste(im, ((i % COLS) * TILE, (i // COLS) * TILE))
        sheet.save(OUT / f"{src}.jpg", quality=88)
        print("wrote", OUT / f"{src}.jpg", len(pick), "images")


if __name__ == "__main__":
    main()

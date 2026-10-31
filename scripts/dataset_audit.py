"""
Full dataset audit - reads EVERY image header and EVERY label line and reports the numbers
that decide detection accuracy: instance size, box counts, label conflicts, leakage.

Output:
  qa/audit_summary.md        human-readable report per source / split
  qa/audit_per_source.csv    one row per source+split
  qa/audit_bad_boxes.csv     boxes that are structurally invalid or clearly wrong
  qa/audit_leakage.csv       identical originals appearing in more than one split

Run:  python scripts/dataset_audit.py
"""
import collections
import csv
import json
import math
import sys
from pathlib import Path

from PIL import Image

ROOT = Path("F:/POTHOLE_PROJECT")
D = ROOT / "dataset"
NAMES = ["pothole", "alligator_crack"]
SPLITS = ["train", "val", "test"]
TINY = 0.001          # area fraction below which a box is unusable for 640 px training
WHOLE = (0.90, 0.90)  # boxes covering almost the whole frame


def pct(vals, p):
    if not vals:
        return 0.0
    s = sorted(vals)
    i = min(len(s) - 1, max(0, int(round(p / 100 * (len(s) - 1)))))
    return s[i]


def iou(a, b):
    ax1, ay1, ax2, ay2 = a[0] - a[2] / 2, a[1] - a[3] / 2, a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1, bx2, by2 = b[0] - b[2] / 2, b[1] - b[3] / 2, b[0] + b[2] / 2, b[1] + b[3] / 2
    ix, iy = max(0.0, min(ax2, bx2) - max(ax1, bx1)), max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = ix * iy
    u = a[2] * a[3] + b[2] * b[3] - inter
    return inter / u if u > 0 else 0.0


def main():
    manifest = json.load(open(D / "manifest.json"))
    meta = {Path(m["file"]).stem: m for m in manifest}

    per = collections.defaultdict(lambda: collections.defaultdict(float))
    areas = collections.defaultdict(list)
    ars = collections.defaultdict(list)
    sizes = collections.Counter()
    bad = []
    class_counts = collections.defaultdict(collections.Counter)
    leak = collections.defaultdict(set)
    per_image = []

    for split in SPLITS:
        img_dir, lab_dir = D / "images" / split, D / "labels" / split
        for img in sorted(img_dir.iterdir()):
            stem = img.stem
            m = meta.get(stem, {})
            src = m.get("source", "?")
            leak[Path(m["original"]).name if m else stem].add(split)
            try:
                with Image.open(img) as im:
                    w, h = im.size
            except Exception as e:  # noqa: BLE001
                bad.append([split, img.name, src, "unreadable image", str(e)[:80]])
                continue
            sizes[f"{w}x{h}"] += 1
            for scope in (src, "__ALL__"):
                per[(scope, split)]["images"] += 1
                per[(scope, split)]["pixels"] += w * h

            lp = lab_dir / f"{stem}.txt"
            boxes = []
            if lp.exists():
                for li, line in enumerate(lp.read_text().splitlines(), 1):
                    v = line.split()
                    if not v:
                        continue
                    if len(v) != 5:
                        bad.append([split, img.name, src, "malformed line", line[:60]])
                        continue
                    try:
                        c = int(v[0]); x, y, bw, bh = (float(t) for t in v[1:])
                    except ValueError:
                        bad.append([split, img.name, src, "non-numeric", line[:60]])
                        continue
                    if c < 0 or c > 1:
                        bad.append([split, img.name, src, "bad class id", line[:60]])
                        continue
                    if bw <= 0.002 or bh <= 0.002:
                        bad.append([split, img.name, src, "zero-size box", line[:60]])
                        continue
                    if not (0 <= x <= 1 and 0 <= y <= 1):
                        bad.append([split, img.name, src, "centre outside image", line[:60]])
                        continue
                    boxes.append([c, x, y, bw, bh])
            if not boxes:
                for scope in (src, "__ALL__"):
                    per[(scope, split)]["empty_images"] += 1
            for b in boxes:
                a, ar = b[3] * b[4], b[3] / b[4]
                areas[(src, split)].append(a)
                ars[(src, split)].append(ar)
                class_counts[(src, split)][NAMES[b[0]]] += 1
                for scope in (src, "__ALL__"):
                    per[(scope, split)]["boxes"] += 1
                    per[(scope, split)][f"boxes_{NAMES[b[0]]}"] += 1
                    if a < TINY:
                        per[(scope, split)]["tiny_boxes"] += 1
                    if a >= 0.25:
                        per[(scope, split)]["huge_boxes"] += 1
                    if b[3] >= WHOLE[0] and b[4] >= WHOLE[1]:
                        per[(scope, split)]["whole_frame_boxes"] += 1
            for i in range(len(boxes)):
                for j in range(i + 1, len(boxes)):
                    if iou(boxes[i][1:], boxes[j][1:]) > 0.80:
                        per[(src, split)]["duplicate_pairs"] += 1
                        per[("__ALL__", split)]["duplicate_pairs"] += 1
                        if boxes[i][0] != boxes[j][0]:
                            per[(src, split)]["class_conflict_pairs"] += 1
                            per[("__ALL__", split)]["class_conflict_pairs"] += 1
            if len(boxes) >= 40:
                bad.append([split, img.name, src, "suspicious box count", str(len(boxes))])

            # one row per image so every single file is accounted for
            flags = []
            if not boxes:
                flags.append("no_boxes")
            areas_i = [b[3] * b[4] for b in boxes]
            if boxes and min(areas_i) < 0.0002:
                flags.append("tiny_box")
            if boxes and max(areas_i) > 0.5:
                flags.append("huge_box")
            if len(boxes) >= 40:
                flags.append("many_boxes")
            if len({b[0] for b in boxes}) == 2:
                flags.append("both_classes")
            per_image.append([split, img.name, src, w, h, len(boxes),
                              sum(1 for b in boxes if b[0] == 0), sum(1 for b in boxes if b[0] == 1),
                              round(min(areas_i), 6) if areas_i else 0,
                              round(max(areas_i), 6) if areas_i else 0, "|".join(flags)])

    rows = []
    for key, s in sorted(per.items()):
        scope, split = key
        n = s.get("images", 0) or 1
        rows.append(dict(
            source=scope, split=split,
            images=int(s.get("images", 0)), boxes=int(s.get("boxes", 0)),
            boxes_per_image=round(s.get("boxes", 0) / n, 2),
            empty_images=int(s.get("empty_images", 0)),
            pct_empty=round(100 * s.get("empty_images", 0) / n, 1),
            pothole=int(s.get("boxes_pothole", 0)), alligator=int(s.get("boxes_alligator_crack", 0)),
            tiny=int(s.get("tiny_boxes", 0)),
            pct_tiny=round(100 * s.get("tiny_boxes", 0) / max(1, s.get("boxes", 0)), 1),
            huge=int(s.get("huge_boxes", 0)), whole_frame=int(s.get("whole_frame_boxes", 0)),
            dup_pairs=int(s.get("duplicate_pairs", 0)), class_conflict=int(s.get("class_conflict_pairs", 0)),
        ))

    with open(ROOT / "qa/audit_per_source.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    leak_rows = {k: v for k, v in leak.items() if len(v) > 1}
    with open(ROOT / "qa/audit_leakage.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["original", "splits"])
        for k, v in sorted(leak_rows.items()):
            w.writerow([k, "/".join(sorted(v))])

    with open(ROOT / "qa/audit_bad_boxes.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["split", "image", "source", "issue", "detail"])
        w.writerows(bad)

    with open(ROOT / "qa/audit_per_image.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["split", "image", "source", "width", "height", "boxes", "pothole",
                    "alligator_crack", "min_area", "max_area", "flags"])
        w.writerows(per_image)

    L = ["# Dataset audit\n", f"images={len(manifest)} label files scanned, "
         f"bad box records={len(bad)}, cross-split duplicates={len(leak_rows)}\n",
         "## Totals per split\n",
         "| split | images | boxes | boxes/img | empty img | % empty | pothole | alligator | tiny<0.1% | % tiny | huge>25% | whole frame | dup pairs | class conflicts |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["source"] == "__ALL__":
            L.append("| {split} | {images} | {boxes} | {boxes_per_image} | {empty_images} | {pct_empty} | "
                     "{pothole} | {alligator} | {tiny} | {pct_tiny} | {huge} | {whole_frame} | {dup_pairs} | "
                     "{class_conflict} |".format(**r))
    L += ["\n## Per source (all splits)\n",
          "| source | split | images | boxes | boxes/img | % empty | tiny<0.1% | % tiny | huge | whole frame | dup | conflicts |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["source"] != "__ALL__":
            L.append("| {source} | {split} | {images} | {boxes} | {boxes_per_image} | {pct_empty} | {tiny} | "
                     "{pct_tiny} | {huge} | {whole_frame} | {dup_pairs} | {class_conflict} |".format(**r))

    L += ["\n## Instance area (fraction of image) per source\n",
          "| source | split | n | p1 | p5 | median | mean | p95 | p99 | %area<0.1% | %area<0.5% |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for (src, split), a in sorted(areas.items()):
        small = sum(1 for v in a if v < TINY) / len(a) * 100
        small5 = sum(1 for v in a if v < 0.005) / len(a) * 100
        L.append(f"| {src} | {split} | {len(a)} | {pct(a,1):.4f} | {pct(a,5):.4f} | {pct(a,50):.4f} | "
                 f"{sum(a)/len(a):.4f} | {pct(a,95):.4f} | {pct(a,99):.4f} | {small:.1f} | {small5:.1f} |")

    L += ["\n## Aspect ratio (w/h) per source\n", "| source | split | p5 | median | p95 |",
          "|---|---|---|---|---|"]
    for (src, split), a in sorted(ars.items()):
        L.append(f"| {src} | {split} | {pct(a,5):.2f} | {pct(a,50):.2f} | {pct(a,95):.2f} |")

    L += ["\n## Image resolutions (top 15)\n", "| size | count |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sizes.most_common(15)]

    L += ["\n## Class balance\n", "| source | split | pothole | alligator_crack | % pothole |",
          "|---|---|---|---|---|"]
    for (src, split), c in sorted(class_counts.items()):
        t = sum(c.values())
        L.append(f"| {src} | {split} | {c['pothole']} | {c['alligator_crack']} | {100*c['pothole']/t:.1f} |")

    (ROOT / "qa/audit_summary.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[:40]))
    print("\nWROTE qa/audit_summary.md, qa/audit_per_source.csv, qa/audit_bad_boxes.csv, qa/audit_leakage.csv")


if __name__ == "__main__":
    main()

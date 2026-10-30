"""
Module 1 - Data Collection & Preprocessing
Merges the 8 raw datasets in F:/POTHOLEDATASET into one clean YOLO dataset.

Classes (final):  0 = pothole   1 = alligator_crack

Raw folders are only READ, never modified. Output goes to F:/POTHOLE_PROJECT/dataset.
Run:  python build_dataset.py
"""
import os, re, json, glob, random, shutil, collections
from multiprocessing import Pool
import cv2
import numpy as np

RAW = "F:/POTHOLEDATASET"
OUT = "F:/POTHOLE_PROJECT/dataset"
QA = "F:/POTHOLE_PROJECT/qa"
SEED = 42
SPLIT = (0.70, 0.15, 0.15)
NEG_FRACTION = 0.10          # background (no-damage) images, as share of final dataset
MIN_BOX_SIDE = 0.008         # boxes thinner than 0.8% of the image are dropped (unlearnable)
NEAR_DUP_HAMMING = 3         # dHash distance at or below this = same picture

NAMES = ["pothole", "alligator_crack"]
removed = collections.Counter()


# ---------------------------------------------------------------- readers
def yolo_lines_to_boxes(path, class_map):
    """Reads YOLO txt (box or polygon lines) -> list of (cls, xc, yc, w, h)."""
    boxes = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        v = line.split()
        if len(v) < 5:
            continue
        c = int(float(v[0]))
        if c not in class_map:
            continue
        nums = list(map(float, v[1:]))
        if len(nums) == 4:
            xc, yc, w, h = nums
        else:  # polygon -> bounding box
            xs, ys = nums[0::2], nums[1::2]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            xc, yc, w, h = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        boxes.append((class_map[c], xc, yc, w, h))
    return boxes


def mask_to_boxes(mask_path, cls, min_area_frac=0.0005):
    m = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if m is None:
        return None
    h, w = m.shape
    m = (m > 127).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))  # join broken pieces
    n, _, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    boxes = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if area < min_area_frac * w * h:
            continue
        boxes.append((cls, (x + bw / 2) / w, (y + bh / 2) / h, bw / w, bh / h))
    return boxes


# ---------------------------------------------------------------- sources
def src_bharat():
    for p in glob.glob(f"{RAW}/BharatPotHole/*/images/*.jpg"):
        lbl = p.replace("/images", "/labels").replace("\\images", "\\labels")[:-4] + ".txt"
        name = os.path.basename(p)
        m = re.match(r"(.+?)_frame_\d+", name)
        group = m.group(1) if m else name.split(".rf.")[0]       # whole video in one split
        yield dict(src="BharatPotHole", img=p, group=group,
                   boxes=yolo_lines_to_boxes(lbl, {0: 0}) if os.path.exists(lbl) else None)


def src_roboflow_iit():
    # 0 crocodile(=alligator) crack, 1 longitudinal crack (not our class), 2 pothole
    for p in glob.glob(f"{RAW}/RoboflowIIT/*/images/*.jpg"):
        lbl = p.replace("/images", "/labels").replace("\\images", "\\labels")[:-4] + ".txt"
        name = os.path.basename(p)
        yield dict(src="RoboflowIIT", img=p, group=name.split(".rf.")[0],
                   boxes=yolo_lines_to_boxes(lbl, {0: 1, 2: 0}) if os.path.exists(lbl) else None)


def src_indian_roads():
    # verified visually: 0 speed-bump, 1 pothole, 2 unpaved road
    for p in glob.glob(f"{RAW}/IndianRoadsDataset/*.jpg"):
        name = os.path.basename(p)
        if name.startswith("frame+"):
            removed["IndianRoads: screenshot of another model's output (FPS/labels burned in)"] += 1
            continue
        if " - Copy" in name:
            removed["IndianRoads: '- Copy' duplicate file"] += 1
            continue
        lbl = p[:-4] + ".txt"
        b = yolo_lines_to_boxes(lbl, {1: 0}) if os.path.exists(lbl) else None
        yield dict(src="IndianRoads", img=p, group=name[:-4], boxes=b,
                   neg_ok=not name.startswith(("PotHoles", "UnPaved", "Ungraded", "AN_unpaved")))


def src_pothole600():
    for p in glob.glob(f"{RAW}/Pothole600/*/rgb/*.png"):
        mp = p.replace("rgb", "label")
        idx = int(os.path.basename(p)[:-4])
        split = os.path.basename(os.path.dirname(os.path.dirname(p)))
        yield dict(src="Pothole600", img=p, group=f"{split}_{idx // 25}",
                   boxes=mask_to_boxes(mp, 0) if os.path.exists(mp) else None)


def src_biankatpas():
    for d in glob.glob(f"{RAW}/BiankatpasDataset/Dataset/*"):
        base = os.path.basename(d)
        raw = os.path.join(d, base + "_RAW.jpg")
        pm = os.path.join(d, base + "_POTHOLE.png")
        if not (os.path.exists(raw) and os.path.exists(pm)):
            removed["Biankatpas: missing RAW or POTHOLE mask"] += 1
            continue
        b = mask_to_boxes(pm, 0)
        if not b:
            removed["Biankatpas: crack-only image (generic cracks, not alligator) - skipped"] += 1
            continue
        road, seq = base.rsplit("_", 1)
        yield dict(src="Biankatpas", img=raw, group=f"{road}_{int(seq) // 20}", boxes=b)


RDD_MAP = {"pothole": 0, "alligator crack": 1}


def src_rdd():
    # RDD2022/test has NO annotations -> unusable, only train is read
    removed["RDD2022: test folder has zero labels (9035 imgs) - not used"] = 9035
    for a in glob.glob(f"{RAW}/RDD2022Dataset/train/ann/*.json"):
        d = json.load(open(a, encoding="utf-8"))
        W, H = d["size"]["width"], d["size"]["height"]
        boxes, other = [], 0
        for o in d["objects"]:
            if o["geometryType"] != "rectangle":
                continue
            (x0, y0), (x1, y1) = o["points"]["exterior"]
            c = RDD_MAP.get(o["classTitle"])
            if c is None:
                other += 1
                continue
            boxes.append((c, (x0 + x1) / 2 / W, (y0 + y1) / 2 / H, abs(x1 - x0) / W, abs(y1 - y0) / H))
        name = os.path.basename(a)[:-5]
        yield dict(src="RDD2022_" + name.rsplit("_", 1)[0], img=f"{RAW}/RDD2022Dataset/train/img/{name}",
                   group=name, boxes=boxes, neg_ok=True)


def src_urban_no():
    for p in glob.glob(f"{RAW}/Urban Civic/no/*.jpg"):
        yield dict(src="UrbanCivic_no", img=p, group=os.path.basename(p), boxes=[], neg_ok=True)


SOURCES = [src_bharat, src_roboflow_iit, src_indian_roads, src_pothole600,
           src_biankatpas, src_rdd, src_urban_no]


# ---------------------------------------------------------------- cleaning
def clean_boxes(boxes):
    out = []
    for c, xc, yc, w, h in boxes:
        x0, y0 = max(0.0, xc - w / 2), max(0.0, yc - h / 2)
        x1, y1 = min(1.0, xc + w / 2), min(1.0, yc + h / 2)
        if x1 - x0 < MIN_BOX_SIDE or y1 - y0 < MIN_BOX_SIDE:
            removed["box: too small / outside image"] += 1
            continue
        out.append((c, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0))
    # exact duplicate boxes
    uniq = list(dict.fromkeys(tuple(round(v, 4) for v in b) for b in out))
    removed["box: exact duplicate"] += len(out) - len(uniq)
    return [(int(b[0]),) + b[1:] for b in uniq]


def dhash(path):
    im = cv2.imread(path, cv2.IMREAD_REDUCED_GRAYSCALE_4)
    if im is None or im.size == 0:
        return path, None
    small = cv2.resize(im, (9, 8), interpolation=cv2.INTER_AREA)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return path, int("".join("1" if b else "0" for b in bits), 2)


def near_dup_clusters(hashes):
    """Multi-index hashing: hamming<=3 on 64 bits => some 16-bit chunk matches exactly."""
    parent = list(range(len(hashes)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for k in range(4):
        buckets = collections.defaultdict(list)
        for i, h in enumerate(hashes):
            buckets[(h >> (16 * k)) & 0xFFFF].append(i)
        for idx in buckets.values():
            if len(idx) < 2 or len(idx) > 400:   # huge buckets = flat/blank images, skip
                continue
            for a in range(len(idx)):
                for b in range(a + 1, len(idx)):
                    i, j = idx[a], idx[b]
                    if bin(hashes[i] ^ hashes[j]).count("1") <= NEAR_DUP_HAMMING:
                        parent[find(i)] = find(j)
    return [find(i) for i in range(len(hashes))]


# ---------------------------------------------------------------- main
def main():
    random.seed(SEED)
    recs = []
    for s in SOURCES:
        n0 = len(recs)
        for r in s():
            if r["boxes"] is None:
                removed[f"{r['src']}: missing label file"] += 1
                continue
            r["boxes"] = clean_boxes(r["boxes"])
            recs.append(r)
        print(f"{s.__name__:22s} {len(recs) - n0:6d} images read")

    # split positives / negatives
    pos = [r for r in recs if r["boxes"]]
    neg = [r for r in recs if not r["boxes"] and r.get("neg_ok")]
    removed["image: no usable boxes and not a trusted negative"] += len(recs) - len(pos) - len(neg)
    random.shuffle(neg)
    n_neg = int(len(pos) * NEG_FRACTION / (1 - NEG_FRACTION))
    removed["negative images beyond 10% cap (not needed)"] += max(0, len(neg) - n_neg)
    neg = neg[:n_neg]
    recs = pos + neg

    # hash + corrupt check
    print(f"hashing {len(recs)} images ...")
    with Pool(max(2, os.cpu_count() - 2)) as pool:
        hmap = dict(pool.imap_unordered(dhash, [r["img"] for r in recs], chunksize=64))
    ok = []
    for r in recs:
        if hmap[r["img"]] is None:
            removed["image: corrupt / unreadable"] += 1
        else:
            r["hash"] = hmap[r["img"]]
            ok.append(r)
    recs = ok

    # near-duplicates: keep the copy with most boxes, others removed;
    # cluster also merges groups so split can't leak
    roots = near_dup_clusters([r["hash"] for r in recs])
    clusters = collections.defaultdict(list)
    for r, root in zip(recs, roots):
        clusters[root].append(r)
    kept, dup_examples = [], []
    for members in clusters.values():
        members.sort(key=lambda r: -len(r["boxes"]))
        kept.append(members[0])
        for m in members[1:]:
            removed["image: near-duplicate of another image"] += 1
            if len(dup_examples) < 12:
                dup_examples.append((members[0]["img"], m["img"]))
    recs = kept

    # group-aware split, done per source so every source is in train/val/test
    by_src = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in recs:
        by_src[r["src"]][r["src"] + "|" + r["group"]].append(r)
    for src, groups in by_src.items():
        keys = sorted(groups)
        random.shuffle(keys)
        total = sum(len(groups[k]) for k in keys)
        acc = 0
        for k in keys:
            frac = acc / total
            sp = "train" if frac < SPLIT[0] else ("val" if frac < SPLIT[0] + SPLIT[1] else "test")
            for r in groups[k]:
                r["split"] = sp
            acc += len(groups[k])

    # write (hard links: no extra disk space, raw data untouched)
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    for sp in ("train", "val", "test"):
        os.makedirs(f"{OUT}/images/{sp}", exist_ok=True)
        os.makedirs(f"{OUT}/labels/{sp}", exist_ok=True)
    manifest = []
    for i, r in enumerate(recs):
        ext = os.path.splitext(r["img"])[1].lower()
        stem = f"{r['src']}__{i:06d}"
        dst = f"{OUT}/images/{r['split']}/{stem}{ext}"
        try:
            os.link(r["img"], dst)
        except OSError:
            shutil.copy2(r["img"], dst)
        with open(f"{OUT}/labels/{r['split']}/{stem}.txt", "w") as f:
            for c, xc, yc, w, h in r["boxes"]:
                f.write(f"{c} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")
        manifest.append(dict(file=stem + ext, split=r["split"], source=r["src"],
                             original=r["img"], n_boxes=len(r["boxes"])))

    with open(f"{OUT}/data.yaml", "w") as f:
        f.write(f"path: {OUT}\ntrain: images/train\nval: images/val\ntest: images/test\n\n"
                f"nc: {len(NAMES)}\nnames: {NAMES}\n")
    json.dump(manifest, open(f"{OUT}/manifest.json", "w"), indent=0)

    # ------------------------------------------------------------ report
    stats = collections.defaultdict(lambda: collections.Counter())
    sizes = collections.Counter()
    for r in recs:
        s = stats[r["src"]]
        s["images"] += 1
        s[r["split"]] += 1
        if not r["boxes"]:
            s["background"] += 1
        for c, _, _, w, h in r["boxes"]:
            s[NAMES[c]] += 1
            a = w * h
            sizes[(NAMES[c], "small(<1%)" if a < 0.01 else "medium(1-10%)" if a < 0.1 else "large(>10%)")] += 1
    os.makedirs(QA, exist_ok=True)
    tot = collections.Counter()
    lines = ["# Dataset Health Report\n", f"Final images: **{len(recs)}**\n",
             "| Source | Images | Train | Val | Test | Pothole boxes | Alligator boxes | Background imgs |",
             "|---|---|---|---|---|---|---|---|"]
    for src in sorted(stats):
        s = stats[src]
        tot.update(s)
        lines.append(f"| {src} | {s['images']} | {s['train']} | {s['val']} | {s['test']} | "
                     f"{s['pothole']} | {s['alligator_crack']} | {s['background']} |")
    lines.append(f"| **TOTAL** | **{tot['images']}** | {tot['train']} | {tot['val']} | {tot['test']} | "
                 f"**{tot['pothole']}** | **{tot['alligator_crack']}** | {tot['background']} |")
    lines += ["\n## Box sizes (area as % of image)\n", "| Class | Size | Count |", "|---|---|---|"]
    for (c, z), n in sorted(sizes.items()):
        lines.append(f"| {c} | {z} | {n} |")
    lines += ["\n## Removed / fixed\n", "| Reason | Count |", "|---|---|"]
    for k, v in sorted(removed.items(), key=lambda x: -x[1]):
        if v:
            lines.append(f"| {k} | {v} |")
    lines += ["\n## Not used for training (no box labels)\n",
              "- SPDataset (618 images) - no annotations -> use for demo / pseudo-labeling later",
              "- Urban Civic/yes (1004 images) - only 'has pothole' tag, no boxes -> pseudo-label later"]
    open(f"{QA}/dataset_report.md", "w", encoding="utf-8").write("\n".join(lines))
    json.dump(dup_examples, open(f"{QA}/duplicate_examples.json", "w"), indent=1)
    print("\n".join(lines))


if __name__ == "__main__":
    main()

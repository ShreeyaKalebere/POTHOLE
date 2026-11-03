"""Builds the YOLO training dataset from the manually checked images -> F:/POTHOLE_PROJECT/dataset_verified

Used:     images checked as damage or no damage (skipped and deleted images are left out).
Split:    Kolhapur train -> train, Kolhapur test -> test (different rides), everything else 70/15/15.
          Frames of one video stay together, and byte-identical copies always go to the same split,
          so an image can never be in both train and test.
Safety:   every image is read once with a time limit; a file that hangs is left out and reported,
          so it cannot freeze training later.
Images are hard links (no extra disk space). Sources are only read.
Run: python build_training_set.py
"""
import collections
import csv
import hashlib
import json
import os
import re
import shutil
import threading
from pathlib import Path

ROOT = Path("F:/POTHOLE_PROJECT")
OUT = ROOT / "dataset_verified"
BATCHES = ROOT / "manual_labeling/batches"
CLASSES = ["pothole", "alligator_crack"]
IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
READ_TIMEOUT = 15
FIXED_SPLIT = {"kolhapur_train": "train", "kolhapur_test": "test"}


def datasets():
    yield "kolhapur_train", ROOT / "kolhapur_labeling/train/images", ROOT / "kolhapur_labeling/train_fixed/labels", ROOT / "kolhapur_labeling/verification_train_progress.json", None
    yield "kolhapur_test", ROOT / "kolhapur_labeling/test/images", ROOT / "kolhapur_labeling/test_fixed/labels", ROOT / "kolhapur_labeling/verification_test_progress.json", None
    yield "fix_labels_val", ROOT / "fix_labels/val/images", ROOT / "fix_labels/val/labels_fixed", ROOT / "fix_labels/verification_progress.json", None
    for b in sorted(BATCHES.iterdir()):
        if (b / "images").is_dir():
            yield b.name, b / "images", b / "labels", b / "verification_progress.json", b / "manifest.csv"


def group_of(key, name, original):
    """Images that belong together: one video / one road sequence."""
    base = name.split(".rf.")[0]
    base = base.split("_frame_")[0]
    orig = original.replace("\\", "/")
    if orig.startswith("Pothole600/"):
        base = f"{orig.split('/')[1]}_{int(Path(name).stem) // 25}"
    elif orig.startswith("BiankatpasDataset/"):
        road, seq = orig.split("/")[2].rsplit("_", 1)
        base = f"{road}_{int(seq) // 20}"
    elif key.startswith("kolhapur"):
        base = "_".join(name.split("_")[:3])
    return re.sub(r"_\d+$", "", key) + "|" + base


def md5_with_limit(path):
    out = []

    def run():
        with open(path, "rb") as f:
            out.append(hashlib.md5(f.read()).hexdigest())

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(READ_TIMEOUT)
    return out[0] if out else None


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    items, hung = [], []
    for key, idir, ldir, pf, manifest in datasets():
        prog = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else {}
        orig = {}
        if manifest and manifest.exists():
            with open(manifest, encoding="utf-8") as f:
                orig = {r["name"]: r["original"] for r in csv.DictReader(f)}
        for name, e in prog.items():
            status = e.get("status") or ("verified" if e.get("box_count", 0) else "negative")
            p = idir / name
            if status not in ("verified", "negative") or not p.exists() or p.suffix.lower() not in IMG:
                continue
            digest = md5_with_limit(p)
            if digest is None:
                hung.append(str(p))
                print("HANGS, left out:", p, flush=True)
                continue
            items.append(dict(key=key, name=name, path=p, status=status, label=ldir / f"{p.stem}.txt",
                              group=group_of(key, name, orig.get(name, "")), md5=digest))
        print(key, "read; total so far", len(items), flush=True)

    # groups joined by byte-identical copies must share one split
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first = {}
    for it in items:
        find(it["group"])
        if it["md5"] in first:
            parent[find(it["group"])] = find(first[it["md5"]])
        else:
            first[it["md5"]] = it["group"]
    forced = {}
    for it in items:
        if it["key"] in FIXED_SPLIT:
            forced[find(it["group"])] = FIXED_SPLIT[it["key"]]

    summary = collections.defaultdict(collections.Counter)
    rows = []
    for it in items:
        root = find(it["group"])
        if root in forced:
            split = forced[root]
        else:
            h = int(hashlib.md5(root.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
            split = "train" if h < 0.70 else "val" if h < 0.85 else "test"
        idir, ldir = OUT / "images" / split / it["key"], OUT / "labels" / split / it["key"]
        idir.mkdir(parents=True, exist_ok=True)
        ldir.mkdir(parents=True, exist_ok=True)
        os.link(it["path"], idir / it["name"])
        lines = []
        if it["status"] == "verified":
            for line in it["label"].read_text(encoding="utf-8", errors="ignore").splitlines():
                v = line.split()
                if len(v) >= 5 and v[0] in ("0", "1"):
                    lines.append(" ".join(v[:5]))
        (ldir / f"{it['path'].stem}.txt").write_text("".join(x + "\n" for x in lines), encoding="utf-8")
        s = summary[split]
        s["images"] += 1
        s["no_damage"] += not lines
        for x in lines:
            s[CLASSES[int(x[0])]] += 1
        rows.append([split, it["key"], it["name"], it["status"], len(lines), it["group"]])

    (OUT / "data.yaml").write_text(f"path: {OUT.as_posix()}\ntrain: images/train\nval: images/val\ntest: images/test\n\n"
                                   f"nc: 2\nnames: {CLASSES}\n", encoding="utf-8")
    with open(OUT / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["split", "dataset", "file", "status", "boxes", "group"])
        w.writerows(rows)
    print("\nsplit   images  no_damage  pothole  alligator_crack")
    for sp in ("train", "val", "test"):
        s = summary[sp]
        print(f"{sp:6} {s['images']:7} {s['no_damage']:10} {s['pothole']:8} {s['alligator_crack']:16}")
    by_md5 = collections.defaultdict(set)
    for r, it in zip(rows, items):
        by_md5[it["md5"]].add(r[0])
    print("identical images in more than one split:", sum(len(v) > 1 for v in by_md5.values()))
    print("files that hang, left out:", hung)
    print("DONE", flush=True)
    os._exit(0)                 # a hung read thread must not keep this script alive


if __name__ == "__main__":
    main()

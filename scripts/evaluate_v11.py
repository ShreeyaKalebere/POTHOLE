"""
Evaluates a v11 model on the verified test set: overall, per class, per source, Kolhapur Test alone,
and recall by box size (conf 0.25, IoU 0.5). The old test set is covered by evaluate.py.
Writes qa/evaluation_<run>_verified_test.md

Run:   python evaluate_v11.py [run]
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
RUN = sys.argv[1] if len(sys.argv) > 1 else "yolo11s_v11_verified"
DATA = ROOT / "dataset_verified"
WEIGHTS = ROOT / "runs" / RUN / "weights" / "best.pt"
TMP = ROOT / "qa" / "_eval_v11_tmp"
NAMES = ["pothole", "alligator_crack"]
SIZES = [("under 16 px", 16 ** 2), ("16-32 px", 32 ** 2), ("32-96 px", 96 ** 2), ("over 96 px", float("inf"))]


def run_val(model, folders, tag, plots=False):
    imgsz = int(((model.ckpt or {}).get("train_args") or {}).get("imgsz", 640))
    TMP.mkdir(exist_ok=True)
    y = TMP / f"{tag}.yaml"
    listed = "".join(f"  - {f.as_posix()}\n" for f in folders)
    y.write_text(f"path: {DATA.as_posix()}\ntrain: images/train\nval: images/val\ntest:\n{listed}\nnc: 2\nnames: {NAMES}\n", encoding="utf-8")
    return model.val(data=str(y), split="test", imgsz=imgsz, batch=8, workers=2, device=0, plots=plots, verbose=False,
                     project=str(ROOT / "runs"), name=f"{RUN}_verified_test" if plots else f"{RUN}_tmp", exist_ok=True)


def row(name, images, m):
    return f"| {name} | {images} | {m.box.mp:.3f} | {m.box.mr:.3f} | {m.box.map50:.3f} | {m.box.map:.3f} |"


def source_of(key):
    return re.sub(r"_\d+$", "", key)


def iou(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    inter = w * h
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


def recall_by_size(model, folders):
    total, found = Counter(), Counter()
    imgsz = int(((model.ckpt or {}).get("train_args") or {}).get("imgsz", 640))
    for folder in folders:
        for r in model.predict(source=str(folder), imgsz=imgsz, conf=0.25, device=0, stream=True, verbose=False):
            lab = Path(str(r.path).replace("\\", "/").replace("/images/test/", "/labels/test/")).with_suffix(".txt")
            if not lab.exists():
                continue
            preds = [(int(c), b) for c, b in zip(r.boxes.cls.tolist(), r.boxes.xyxyn.tolist())]
            used = set()
            for line in lab.read_text(encoding="utf-8").splitlines():
                c, x, y, w, h = line.split()
                c, x, y, w, h = int(c), float(x), float(y), float(w), float(h)
                gt = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
                bucket = next(n for n, limit in SIZES if w * h * 640 * 640 < limit)
                total[(c, bucket)] += 1
                best, best_i = 0.0, None
                for i, (pc, pb) in enumerate(preds):
                    v = iou(gt, pb) if pc == c and i not in used else 0.0
                    if v > best:
                        best, best_i = v, i
                if best >= 0.5:
                    used.add(best_i)
                    found[(c, bucket)] += 1
    return total, found


def main():
    model = YOLO(str(WEIGHTS))
    folders = sorted(p for p in (DATA / "images" / "test").iterdir() if p.is_dir())
    counts = {f: sum(1 for _ in f.iterdir()) for f in folders}
    out = [f"# {RUN}: verified test set", "", f"Weights: `{WEIGHTS.relative_to(ROOT).as_posix()}`, {int(((model.ckpt or {}).get('train_args') or {}).get('imgsz', 640))} px.", "",
           "| Set | Images | Precision | Recall | mAP@50 | mAP@50-95 |", "|---|---:|---:|---:|---:|---:|"]

    m = run_val(model, folders, "all", plots=True)
    out.append(row("**All test**", sum(counts.values()), m))
    for i, n in zip(m.box.ap_class_index, m.box.ap_class_index):
        out.append(f"| {NAMES[int(n)]} | | {m.box.p[list(m.box.ap_class_index).index(i)]:.3f} | {m.box.r[list(m.box.ap_class_index).index(i)]:.3f} "
                   f"| {m.box.ap50[list(m.box.ap_class_index).index(i)]:.3f} | {m.box.ap[list(m.box.ap_class_index).index(i)]:.3f} |")
    print("\n".join(out), flush=True)

    by_source = defaultdict(list)
    for f in folders:
        by_source[source_of(f.name)].append(f)
    out += ["", "## Per source", "", "| Source | Images | Precision | Recall | mAP@50 | mAP@50-95 |", "|---|---:|---:|---:|---:|---:|"]
    for src, fs in sorted(by_source.items(), key=lambda kv: -sum(counts[f] for f in kv[1])):
        m = run_val(model, fs, f"src_{src}")
        out.append(row(src, sum(counts[f] for f in fs), m))
        print(out[-1], flush=True)

    total, found = recall_by_size(model, folders)
    out += ["", "## Recall by box size, measured on a 640 px image (conf 0.25, IoU 0.5)", "", "| Class | Size | Boxes | Found | Recall |", "|---|---|---:|---:|---:|"]
    for c, name in enumerate(NAMES):
        for bucket, _ in SIZES:
            t, g = total[(c, bucket)], found[(c, bucket)]
            out.append(f"| {name} | {bucket} | {t} | {g} | {g / t if t else 0:.3f} |")
    (ROOT / "qa" / f"evaluation_{RUN}_verified_test.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()

"""
Error diagnosis on the test set - where is mAP actually lost?

For every test image: run the model at conf=0.001, then match predictions to ground
truth. Reports
  * AP@50 / AP@50-95 per class and per GT size bucket (COCO small/medium/large at the input size)
  * recall@IoU0.5 per size bucket and per data source
  * label-noise evidence: GT boxes nothing detects at all, and confident detections with no GT

Run: python scripts/diagnose_errors.py <weights.pt> [<weights2.pt> ...] [--imgsz 640]
Out: qa/diagnose_<name>.md, qa/diagnose_<name>_unmatched_gt.csv, qa/diagnose_<name>_extra_preds.csv
"""
import csv
import sys
from pathlib import Path

import numpy as np
from ultralytics import YOLO

ROOT = Path("F:/POTHOLE_PROJECT")
D = ROOT / "dataset"
NAMES = ["pothole", "alligator_crack"]
# COCO size buckets expressed as fraction of input area (input 640 -> 409600 px)
BUCKETS = [("small <32px", 0.0, 1024 / 409600), ("medium 32-96px", 1024 / 409600, 9216 / 409600),
           ("large >96px", 9216 / 409600, 1.0)]


def iou_matrix(a, b):
    """a: (N,4) xyxy, b: (M,4) xyxy -> (N,M)"""
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    lt = np.maximum(a[:, None, :2], b[None, :, :2])
    rb = np.minimum(a[:, None, 2:], b[None, :, 2:])
    wh = np.clip(rb - lt, 0, None)
    inter = wh[:, :, 0] * wh[:, :, 1]
    aa = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    bb = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (aa[:, None] + bb[None, :] - inter)


def ap_from_curve(conf, tp, n_gt):
    """VOC-style all-points AP."""
    order = np.argsort(-conf)
    tp = tp[order]
    ctp = np.cumsum(tp)
    cfp = np.cumsum(1 - tp)
    rec = ctp / max(n_gt, 1)
    prec = ctp / np.maximum(ctp + cfp, 1e-9)
    mrec = np.concatenate([[0.0], rec, [1.0]])
    mpre = np.concatenate([[1.0], prec, [0.0]])
    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])
    return float(np.sum((mrec[1:] - mrec[:-1]) * mpre[1:]))


def analyse(weights, imgsz=640):
    name = Path(weights).parent.parent.name if Path(weights).name == "best.pt" else Path(weights).stem
    model = YOLO(weights)
    imgs = sorted((D / "images/test").glob("*.jpg"))
    res = {}
    paths = [str(p) for p in imgs]
    for i in range(0, len(paths), 8):
        batch = paths[i:i + 8]
        out = model.predict(batch, imgsz=imgsz, conf=0.001, iou=0.7, max_det=100,
                            batch=8, device=0, verbose=False)
        for r, p in zip(out, batch):
            res[Path(p)] = r
        del out
    import torch
    torch.cuda.empty_cache()

    rows, unmatched, extra = [], [], []
    # accumulators: per (class, bucket) lists of (conf, tp)
    acc = {(c, b[0]): [] for c in range(2) for b in BUCKETS}
    n_gt = {(c, b[0]): 0 for c in range(2) for b in BUCKETS}
    rec_hits = {(b[0], "hit"): 0 for b in BUCKETS}
    rec_tot = {(b[0], "n"): 0 for b in BUCKETS}
    per_src = {}
    stats = dict(gt=0, gt_found=0, gt_lost=0, extra_conf=0, extra_conf_nogt=0)

    from collections import defaultdict
    src_of = defaultdict(lambda: "?")
    import json
    for m in json.load(open(D / "manifest.json")):
        if m["split"] == "test":
            src_of[Path(m["file"]).stem] = m["source"]
    # cached sizes
    for img in imgs:
        r = res[img]
        h, w = r.orig_shape
        g = []
        lp = D / "labels/test" / (img.stem + ".txt")
        if lp.exists():
            for line in lp.read_text().splitlines():
                v = line.split()
                if len(v) == 5:
                    c, x, y, bw, bh = int(v[0]), *map(float, v[1:])
                    g.append([c, (x - bw / 2) * w, (y - bh / 2) * h, (x + bw / 2) * w, (y + bh / 2) * h])
        g = np.array(g, dtype=float).reshape(-1, 5)
        p = np.column_stack([r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy(),
                             r.boxes.cls.cpu().numpy()]).reshape(-1, 6)
        # scale GT area to input-relative (fraction of image)
        garea = ((g[:, 3] - g[:, 1]) * (g[:, 4] - g[:, 2]) / (w * h)) if len(g) else np.zeros(0)
        parea = ((p[:, 2] - p[:, 0]) * (p[:, 3] - p[:, 1]) / (w * h)) if len(p) else np.zeros(0)
        src = src_of[img.stem]
        s = per_src.setdefault(src, dict(n_gt=0, n_found=0, n_img=0))
        s["n_img"] += 1

        matched_g = np.zeros(len(g), bool)
        matched_p = np.zeros(len(p), bool)
        if len(g) and len(p):
            M = iou_matrix(g[:, 1:5], p[:, :4])
            # per-class greedy matching at IoU .5 for the recall statistic
            for gi in range(len(g)):
                cand = np.where((p[:, 5] == g[gi, 0]) & (M[gi] >= 0.5) & ~matched_p)[0]
                if len(cand):
                    best = cand[np.argmax(M[gi, cand])]
                    matched_g[gi] = matched_p[best] = True
        # classification-agnostic "is there anything here" check (conf>0.1, IoU>0.3)
        near = np.zeros(len(g), bool)
        if len(g) and len(p):
            M2 = iou_matrix(g[:, 1:5], p[:, :4])
            near = (M2.max(axis=1) >= 0.3) & (p[:, 4][M2.argmax(axis=1)] > 0.1)

        for gi in range(len(g)):
            c = int(g[gi, 0])
            a = garea[gi]
            b = next((bb[0] for bb in BUCKETS if bb[1] <= a < bb[2]), "large >96px")
            n_gt[(c, b)] += 1
            rec_tot[(b, "n")] += 1
            s["n_gt"] += 1
            stats["gt"] += 1
            if matched_g[gi]:
                rec_hits[(b, "hit")] += 1
                s["n_found"] += 1
                stats["gt_found"] += 1
            elif not near[gi]:
                stats["gt_lost"] += 1
                unmatched.append([src, img.name, c, f"{g[gi,1]:.1f}", f"{g[gi,2]:.1f}",
                                  f"{g[gi,3]-g[gi,1]:.1f}", f"{g[gi,4]-g[gi,2]:.1f}", f"{a:.5f}"])
        # per-class AP contributions
        for c in range(2):
            gidx = np.where(g[:, 0] == c)[0] if len(g) else np.array([], int)
            pidx = np.where(p[:, 5] == c)[0] if len(p) else np.array([], int)
            if len(gidx) and len(pidx):
                M = iou_matrix(g[gidx, 1:5], p[pidx, :4])
                used = np.zeros(len(pidx), bool)
                for gi_local, gi in enumerate(gidx):
                    b = next((bb[0] for bb in BUCKETS if bb[1] <= garea[gi] < bb[2]), "large >96px")
                    cand = np.where((M[gi_local] >= 0.5) & ~used)[0]
                    hit = -1
                    if len(cand):
                        hit = cand[np.argmax(M[gi_local, cand])]
                        used[hit] = True
                    # every prediction of this class that overlaps this GT contributes
                    for pi_local in np.where(M[gi_local] >= 0.5)[0]:
                        if hit >= 0 and pi_local != hit:
                            continue
                        tp = 1.0 if pi_local == hit else 0.0
                        acc[(c, b)].append((float(p[pidx[pi_local], 4]), tp))
                for pi_local in pidx:
                    if not used[np.where(pidx == pi_local)[0][0]]:
                        b = next((bb[0] for bb in BUCKETS if bb[1] <= parea[pi_local] < bb[2]), "large >96px")
                        acc[(c, b)].append((float(p[pi_local, 4]), 0.0))
            elif len(pidx):
                for pi_local in pidx:
                    b = next((bb[0] for bb in BUCKETS if bb[1] <= parea[pi_local] < bb[2]), "large >96px")
                    acc[(c, b)].append((float(p[pi_local, 4]), 0.0))

        # confident detections with no GT nearby
        if len(p):
            if len(g):
                M3 = iou_matrix(g[:, 1:5], p[:, :4])
                has = (M3.max(axis=0) >= 0.5) if len(g) else np.zeros(len(p), bool)
            else:
                has = np.zeros(len(p), bool)
            for pi_ in range(len(p)):
                if p[pi_, 4] >= 0.6:
                    stats["extra_conf"] += 1
                    if not has[pi_]:
                        stats["extra_conf_nogt"] += 1
                        extra.append([src, img.name, NAMES[int(p[pi_, 5])], f"{p[pi_, 4]:.3f}",
                                      f"{p[pi_, 0]:.1f}", f"{p[pi_, 1]:.1f}", f"{p[pi_, 2]-p[pi_, 0]:.1f}",
                                      f"{p[pi_, 3]-p[pi_, 1]:.1f}", f"{parea[pi_]:.5f}"])

    print(f"\n===== {name} =====")
    print(f"GT instances {stats['gt']}, matched@IoU.5 (same class) {stats['gt_found']} "
          f"({100*stats['gt_found']/max(1,stats['gt']):.1f}%), nothing within IoU.3 {stats['gt_lost']} "
          f"({100*stats['gt_lost']/max(1,stats['gt']):.1f}%)")
    print(f"confident detections>=0.6: {stats['extra_conf']}, of which without GT {stats['extra_conf_nogt']} "
          f"({100*stats['extra_conf_nogt']/max(1,stats['extra_conf']):.1f}%)")
    print("\nsize bucket      n_gt   recall@IoU.5   AP50(pothole)  AP50(alligator)")
    for bb in BUCKETS:
        b = bb[0]
        aps = []
        for c in range(2):
            lst = acc[(c, b)]
            aps.append(ap_from_curve(np.array([t[0] for t in lst]), np.array([t[1] for t in lst]),
                                     n_gt[(c, b)]) if lst else float("nan"))
        print(f"{b:15s} {rec_tot[(b,'n')]:6d}   {100*rec_hits[(b,'hit')]/max(1,rec_tot[(b,'n')]):8.1f}%      "
              f"{aps[0]:.3f}          {aps[1]:.3f}")
    print("\nper source     n_img  n_gt  recall@IoU.5")
    for s in sorted(per_src):
        v = per_src[s]
        print(f"{s:26s} {v['n_img']:5d} {v['n_gt']:6d}  {100*v['n_found']/max(1,v['n_gt']):6.1f}%")

    with open(ROOT / f"qa/diagnose_{name}_unmatched_gt.csv", "w", newline="") as f:
        w_ = csv.writer(f); w_.writerow(["source", "image", "class", "x1", "y1", "w", "h", "area_frac"]); w_.writerows(unmatched)
    with open(ROOT / f"qa/diagnose_{name}_extra_preds.csv", "w", newline="") as f:
        w_ = csv.writer(f); w_.writerow(["source", "image", "class", "conf", "x1", "y1", "w", "h", "area_frac"]); w_.writerows(extra)
    print(f"\nwrote qa/diagnose_{name}_unmatched_gt.csv ({len(unmatched)}) and _extra_preds.csv ({len(extra)})")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    imgsz = 640
    for a in sys.argv[1:]:
        if a.startswith("--imgsz"):
            imgsz = int(a.split("=")[1]) if "=" in a else 640
    for wpath in args:
        analyse(str(ROOT / wpath if not Path(wpath).is_absolute() else wpath), imgsz)

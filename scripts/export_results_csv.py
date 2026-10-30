"""Writes qa/results_models_test.csv and qa/results_all_epochs.csv (re-run any time to refresh)."""
import csv, re
from pathlib import Path
ROOT = Path("F:/POTHOLE_PROJECT")
RUNS = {"yolo11s_v1": "v1 (640px, baseline)", "yolo11s_v2_960": "v2 (960px + Indian x2)",
        "yolo11s_v3_aug": "v3 (rain/night/blur aug)", "yolo11s_v4_fixed": "v4 (fixed labels)", "yolo11s_v5_kolpseudo": "v5p (Kolhapur pseudo-labels)", "yolo11s_v6_kolreview": "v6 (Kolhapur reviewed boxes)", "yolo11s_v7_kolfixed": "v7 (Kolhapur + Codex checked)"}

# 1. test-set comparison, parsed from qa/evaluation_<run>.md
rows = []
for run, desc in RUNS.items():
    md = ROOT / "qa" / f"evaluation_{run}.md"
    if not md.exists():
        rows.append({"model": run, "description": desc, "status": "not evaluated yet"}); continue
    t = md.read_text(encoding="utf-8")
    r = {"model": run, "description": desc, "status": "evaluated"}
    for cls in ("All", "pothole", "alligator_crack"):
        m = re.search(rf"^\| {cls} \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|", t, re.M)
        if m:
            p, rc, f1, a50, a = m.groups()
            pre = "" if cls == "All" else cls + "_"
            r.update({f"{pre}precision": p, f"{pre}recall": rc, f"{pre}F1": f1, f"{pre}mAP50": a50, f"{pre}mAP50_95": a})
    for dev, key in (("GPU", "gpu"), ("CPU", "cpu")):
        m = re.search(rf"^\| {dev}[^|]*\| ([\d.]+) \| ([\d.]+) \|", t, re.M)
        if m: r[f"{key}_ms_per_image"], r[f"{key}_fps"] = m.groups()
    for src, n, p, rc, a50 in re.findall(r"^\| (\w+) \| (\d+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$", t, re.M):
        r[f"mAP50_{src}"] = a50
    rows.append(r)
cols = []
for r in rows:
    cols += [k for k in r if k not in cols]
with open(ROOT / "qa/results_models_test.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

# 2. every epoch of every run
with open(ROOT / "qa/results_all_epochs.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["model", "epoch", "precision", "recall", "mAP50", "mAP50_95", "train_box_loss", "train_cls_loss", "val_box_loss", "val_cls_loss", "validation_set"])
    for run in RUNS:
        p = ROOT / "runs" / run / "results.csv"
        if not p.exists(): continue
        for x in csv.DictReader(open(p)):
            x = {k.strip(): v for k, v in x.items()}
            w.writerow([run, int(float(x["epoch"])), x["metrics/precision(B)"], x["metrics/recall(B)"], x["metrics/mAP50(B)"],
                        x["metrics/mAP50-95(B)"], x["train/box_loss"], x["train/cls_loss"], x["val/box_loss"], x["val/cls_loss"],
                        "val_rest (1750, easier - not comparable)" if run == "yolo11s_v4_fixed" else "val (2692)"])
print("written qa/results_models_test.csv and qa/results_all_epochs.csv")

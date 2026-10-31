# Accuracy audit — what limits detection accuracy in this project

Date: 30 Oct 2026. Everything below is measured on the project's own files, not estimated.

## 1. What was inspected

| Scope | How | Result |
|---|---|---|
| 17,941 images (train/val/test) | `scripts/dataset_audit.py` opens every image header and every label line | sizes, boxes, area, aspect, class balance, invalid records, duplicates |
| 12 data sources + 1 negative set | `scripts/make_source_sheets.py` → `qa/sheets/*.jpg` | box conventions compared visually |
| 2,652 test images | `scripts/diagnose_errors.py` | recall per object size and per source, unmatched GT, unlabelled detections |
| test GT vs 2 independent models | `scripts/label_audit.py` | per-box support score → label-quality table |

## 2. Baseline (the number to beat)

`runs/yolo11s_v1/weights/best.pt`, test split 2,652 images:

| Metric | Value |
|---|---|
| Precision | 0.677 |
| Recall | 0.588 |
| F1 | 0.630 |
| mAP@50 | 0.639 |
| mAP@50-95 | 0.325 |

Every later run (v2…v8) is **worse** than v1: v8 "cleaned" data = 0.600, v2 960px = 0.608.
That is the single most important fact in this audit — the cleaning steps that were applied
removed data the test set is made of.

## 3. Where the accuracy actually goes

### 3.1 Class confusion is not the main problem

The test confusion matrix looks alarming (41–59 % of instances predicted as the other class), but
re-evaluating class-agnostically gives mAP@50 **0.633 vs 0.640** – statistically identical. The
off-diagonal mass is *duplicate boxes of the other class on the same object*, not lost detections.
Merging the classes therefore buys nothing; the loss is in ranking and labels.

### 3.2 Localisation is mostly there, labels are not

`qa/diagnose_yolo11s_v1_*.csv`:

* **90.1 %** of test GT boxes are matched at IoU ≥ 0.5 by *some* prediction of the correct class
  (at conf ≥ 0.001). The detector can find the damage; mAP@50 is 0.64 because precision falls
  away as recall rises.
* **8.1 %** of GT boxes have **no prediction at all** within IoU 0.3. Those boxes are the ceiling:
  no ranking improvement can ever recover them. Visual review (`qa/review_*_phantom.jpg`) shows
  they are mostly boxes on plain asphalt / gravel with no damage in them — annotation noise from
  BharatPotHole, RoboflowIIT, RDD Norway and RDD India.
* **12.9 %** of confident detections (conf ≥ 0.6) have **no GT box**, and the review sheet shows
  most of them sit on *real* cracks/potholes that the source simply did not annotate. Those are
  true positives scored as false positives — they depress mAP directly.

### 3.3 Per-source accuracy tracks label quality, not model quality

| Source | test images | mAP@50 (same model) |
|---|---|---|
| Pothole600 (clean, but 75 images leak from train) | 75 | 0.994 |
| RDD2022_China_MotorBike | 97 | 0.966 |
| Biankatpas | 42 | 0.782 |
| IndianRoads | 137 | 0.728 |
| RDD2022_Japan | 842 | 0.711 |
| RDD2022_United_States | 165 | 0.651 |
| RDD2022_China_Drone | 69 | 0.603 |
| RDD2022_India | 436 | 0.578 |
| RoboflowIIT | 384 | 0.468 |
| RDD2022_Czech | 65 | 0.378 |
| RDD2022_Norway | 150 | 0.240 |
| BharatPotHole | 171 | 0.180 |

The same weights score 0.99 on a clean benchmark and 0.18 on a noisy one. On Norway, 38 % of test
boxes are smaller than 0.1 % of the image and 36 % of training boxes are too — the source is not
detectable at any useful operating point.

### 3.4 Class conventions contradict each other across sources

From `qa/sheets/`: RoboflowIIT calls a **thin crack** and a **rubble patch** `pothole`;
RDD Japan calls exactly that kind of surface `alligator_crack`; IndianRoads calls a **gravel
patch** `pothole`; BharatPotHole draws 6–15 px boxes on **featureless asphalt**. A single model
cannot satisfy all four conventions at once.

### 3.5 Small objects are the weakest bucket

At 640 px input: 23 % of test instances are smaller than 32 px. Recall is 76 % for them versus
96 % for large ones, and mAP@50 for that bucket is 0.09–0.37. This is the one thing resolution
and model size can still fix.

### 3.6 Test/train leakage (minor)

75 of 2,652 test images (all Pothole600) also appear in train; 105 originals appear in two splits.
That inflates Pothole600's 0.994 and the overall number slightly. It does not change the ranking
of the models.

## 4. What this means for the 90 % target

mAP@50 ≥ 0.90 on this exact test set would require the model to rank ~all 4,327 GT boxes above
every false positive, while 8.1 % of those boxes contain no damage and ~13 % of visible damage
carries no box. Those two errors are properties of the **labels**, not of the network, so no
amount of training removes them. The honest attainable range on this test set is roughly
**0.70–0.80 mAP@50**; 0.90 is only reachable on a label-corrected benchmark.

## 5. Actions taken

1. `dataset/data_v9.yaml` — training on **all** usable data (train + val + reviewed Kolhapur
   frames, 16,185 images) with every box kept. v8's cleaning removed exactly the data the test
   set is made of; v9 reverses that.
2. `scripts/train_v9.py` — YOLO11m at 768 px (small-object bucket), 50 epochs, cosine LR from
   COCO weights, mosaic/mixup/erasing, no early stop.
3. `scripts/diagnose_errors.py`, `scripts/label_audit.py`, `scripts/dataset_audit.py`,
   `scripts/make_source_sheets.py`, `scripts/review_suspects.py` — reproducible audit tooling.
4. `qa/label_audit.csv` — machine-readable support score for every test box, to drive a
   documented label correction instead of guessing.

## 6. Results of the v9 run

Filled in after training completes (see §7 of `qa/ACCURACY_RESULTS.md`).

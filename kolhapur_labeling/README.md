# Kolhapur labelling — instructions for the team

These frames come from **your own recordings on 27 Oct** (74 min of video + 108 photos).
The current model (v1) has **already drawn its best guess** on every frame.
Your job: **correct** the boxes. You do not draw everything from scratch.

## Folders

```
kolhapur_labeling/
  train/   frames from the MORNING rides   -> will become training data
  test/    frames from the AFTERNOON ride (started 15:00 or later)
           -> the KOLHAPUR TEST SET: used only to measure accuracy, never for training
    images/     the frames
    labels/     model's pre-labels, YOLO format   <- this is what you correct
    previews/   same frames with the model's boxes drawn (for a quick look)
  frames.csv    which video and second each frame came from
  classes.txt / data.yaml   class list for Roboflow
```

Classes: `0 = pothole`, `1 = alligator_crack`

## Do the TEST folder first (most important)
The test set gives the **real Kolhapur accuracy** for your report.
It must be labelled **carefully and completely**: every pothole and alligator crack box,
no wrong boxes. Do not skip frames.

## Rules (same as before)

| You see | Do |
|---|---|
| Model box on a real pothole / alligator crack | **Keep**, make it tight |
| Model box on shadow, puddle on flat road, patch repair, manhole, speed breaker, gravel heap | **Delete** |
| Real damage with **no** box | **Draw** a box (`B`) and pick the class |
| Pothole too small / far to judge | **Leave unlabelled** |
| Single straight crack (not a "crocodile skin" network) | **Not** alligator crack — leave unlabelled |
| Water-filled pothole | **Is a pothole** — label it |
| Good road, nothing wrong | **No boxes** — that is a correct, useful frame |

Rule of thumb: **label what a road inspector would report from that frame.**

## Roboflow steps
1. Create **two** projects (Object Detection): `kolhapur-test` and `kolhapur-train`
   (keeping them separate guarantees test frames never leak into training).
2. Upload `test/images` + `test/labels` + `classes.txt` into `kolhapur-test`
   (and later `train/...` into `kolhapur-train`).
3. Split the images among the team, correct, approve.
4. Export each project: **Generate → no preprocessing, no augmentation → Export → YOLOv8 format**.
5. Unzip into `kolhapur_labeling/test_fixed/` and `kolhapur_labeling/train_fixed/` and tell Claude.

## Privacy
Frames show **people's faces and vehicle number plates**.
- On the **free** Roboflow plan projects are **public** — consider a private workspace,
  or label offline with LabelImg (instructions in `fix_labels/README.md`).
- Do **not** put these frames in the public report or on GitHub without blurring.

# Fix the labels — instructions for the team

These are photos where the model **missed** a pothole or alligator crack.
Everything here is a **copy**. Editing these files does not change the real dataset.
When you're done, tell Claude, and the fixed labels will be merged back and the model retrained.

## What's in each folder

```
fix_labels/
  val/
    images/        photos (copies)
    labels/        their CURRENT labels, YOLO format  <- this is what you fix
    previews/      same photos with boxes drawn, to see the problem quickly
    missed_list.csv  one row per photo: source, how many boxes were missed, smallest box size
  data.yaml / classes.txt   class list for Roboflow / LabelImg
```

Classes: `0 = pothole`, `1 = alligator_crack`

### Colours in `previews/`
| Colour | Meaning |
|---|---|
| **Thick yellow** | the label the model **missed** (the reason this photo is here) |
| Thin green | other existing labels |
| **Red** | what the model detected |

## How to decide, for each yellow box

| What you see | What to do |
|---|---|
| A real pothole or alligator crack, clearly visible | **Keep it.** The label is right; the model needs to learn it. Check the box fits tightly. |
| Nothing there, or a shadow, puddle, patch repair, manhole or road marking | **Delete the box.** Wrong label. |
| A pothole too small or far away to judge (just a few pixels) | **Delete the box.** We are setting a minimum size. |
| A single long crack, not a network ("crocodile skin") | **Delete it**, because it's not an alligator crack. |
| Wrong class (pothole labelled as crack or the reverse) | **Change the class.** |
| A **red** box (model) on real damage that has **no** label | **Add a label** there. The model was right and the label was missing. |

**Rule of thumb: label what a road inspector would report from that photo.**

## Where to start (most useful first)
Sort `missed_list.csv` by `source` and do these first. They're Indian roads, which matter most for Kolhapur:
1. `BharatPotHole` (176 photos)
2. `RDD2022_India` (175)
3. `RoboflowIIT` (163)
4. `IndianRoads` (29)

Even fixing only these ~540 photos is worthwhile. The rest (Japan, Norway, …) are optional.

## Tools

**Option A — Roboflow (easiest for a team):**
1. Roboflow → New project → Object Detection → Upload `val/images` **and** `val/labels` together, plus `classes.txt`.
2. Fix boxes in the annotation editor.
3. Export → **YOLOv8 / YOLO11 format** → download → give the `labels` folder back.

**Option B — LabelImg (offline, on this laptop):**
1. `pip install labelImg`, then run `labelImg`.
2. Open Dir → `fix_labels/val/images`, Change Save Dir → `fix_labels/val/labels`, format **YOLO**.
3. Fix and save each photo (Ctrl+S). The `.txt` files in `labels/` are updated.

**Important:** keep the file names exactly the same (e.g. `BharatPotHole__000214.txt`).
That is how the fixes get matched back to the dataset.

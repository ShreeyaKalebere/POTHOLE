# Computer Vision & Deep Learning Based Road Damage and Municipal Reporting System

YOLO11 + FastAPI + MongoDB + React system that detects **potholes** and **alligator cracks** from road
photos and live phone video, estimates severity, records GPS, and gives municipal officers a dashboard
(map, repair worklist, inspect & dispatch, PDF/CSV reports).

## Results (test set: 2,652 unseen images)

| Model | Training change | mAP@50 | Precision | Recall |
|---|---|---|---|---|
| **v1** | baseline YOLO11s, 640 px, 107 epochs | **0.639** | 0.677 | 0.588 |
| v2 | 960 px + Indian images x2 | 0.608 | 0.673 | 0.572 |
| v3 | rain/night/blur augmentation | 0.616 | 0.670 | 0.559 |
| v4 | label fixes | 0.626 | 0.682 | 0.572 |
| v5 | Kolhapur model pseudo-labels | 0.618 | 0.667 | 0.575 |
| **v6** (deployed) | Kolhapur frames, boxes reviewed | 0.623 | **0.690** | 0.567 |
| v8 | cleaned data (tiny boxes, Norway/Czech removed) | 0.600 | 0.659 | 0.557 |

Stopped early, not evaluated on test: YOLO11m (v8m, 30/40 epochs, best val mAP@50 0.524),
v9 (YOLO11m 768 px, 3/50 epochs), v10 (YOLO11s 768 px, 4/18 epochs; its val set is inside its training data).
All runs land between 0.60 and 0.64 on the test set - see `qa/ACCURACY_AUDIT.md` / `qa/audit_summary.md`.

- Speed: ~10 ms / image on RTX 4060 (≈100 FPS), ~105 ms on CPU. Model size 19 MB.
- Kolhapur field test (469 frames, 27 Oct 2026): v6 found ~24% more real damage than v1.
- All epoch-by-epoch numbers: `qa/results_all_epochs.csv`; graphs and confusion matrices: `results/`.
- Datasets and field videos are **not** in this repository (size, and faces / number plates in the videos).


Group G3 · DYPCET Kolhapur · Guide: Mrs. S. V. Shinge

## Folder layout

| Folder | What it is | Module |
|---|---|---|
| `scripts/build_dataset.py` | Merges the 8 raw datasets in `F:\POTHOLEDATASET` into one clean YOLO dataset | 1 |
| `dataset/` | Clean dataset (images, labels, `data.yaml`, `manifest.json`) | 1 |
| `qa/` | Dataset health report + label check images | 1 |
| `scripts/train.py` | YOLO11 training | 2 |
| `runs/` | Training results (weights, mAP curves, confusion matrix) | 2 |
| `backend/` | FastAPI + MongoDB API: detection, severity, GPS, incidents, reports | 3, 5 |
| `dashboard/` | React.js dashboard: map, worklist, dispatch, charts, exports | 4 |

Classes: `0 = pothole`, `1 = alligator_crack`. Severity: Low / Medium / High.

## Run it (VS Code)

1. Open this folder in VS Code.
2. **Ctrl+Shift+B** → runs *Start everything* (backend + dashboard in two terminals).
3. Open http://localhost:5173 — dashboard.
   http://localhost:8000/docs — API documentation (try every endpoint from the browser).

Manually instead:

```
cd backend   &&  python -m uvicorn main:app --reload --port 8000
cd dashboard &&  npm run dev
```

MongoDB must be running (Windows service "MongoDB", database `road_damage`).

## Dashboard pages

- **Dashboard** – totals, high-hazard count, map, priority list, severity / status / zone / trend charts
- **Road Map** – all incidents on OpenStreetMap, colour = severity, click → inspect
- **Repair Worklist** – priority-sorted table, change status inline
- **Incident page** – annotated photo(s), GPS, history timeline, assign team + status (Inspect & Dispatch)
- **Detect Damage** – upload a road photo → YOLO11 detection → saved as incident (GPS from photo EXIF or browser)
- **Reports** – PDF / CSV export with filters, demo data, reload model

## Live Patrol (phone camera) — Module 5

1. VS Code → Terminal → Run Task → **Start everything (phone / live patrol)**
   (dashboard runs on **https** because phones only allow camera + GPS on secure pages).
2. Phone on the same Wi-Fi / hotspot → open `https://<laptop-ip>:5173/live`
   (laptop IP: `ipconfig` → Wi-Fi → IPv4). Accept the certificate warning
   (Advanced → Proceed) — it is the laptop's own self-signed certificate.
3. Press **Start patrol**, allow camera + location, point at the road.

Pipeline per frame: YOLO11 → ByteTrack (`backend/bytetrack_road.yaml`) → severity → GPS → MongoDB.
An incident is saved **once per tracked damage** (seen in ≥ 3 frames, confidence ≥ 0.35), not once per frame.

Recorded video instead of live:

```
cd scripts
python process_video.py --video road.mp4 --lat 16.6985 --lng 74.2335
python process_video.py --video road.mp4 --gps road_gps.csv      # CSV: seconds,lat,lng
```

Annotated video with track IDs is written to `runs/videos/`.

**GPU note:** while training runs, backend detection uses the CPU (`INFER_DEVICE` in `backend/config.py`).
Sharing the 8 GB GPU with training caused an out-of-memory crash. After training, set it to `"0"`.

## Key backend logic

- `severity.py` – score = √(box area) × perspective factor; per-class thresholds calibrated on 21k training boxes
- `main.py: upsert_incident` – same damage type within 15 m that is not yet repaired is **merged** into
  the existing incident (reports_count +1) instead of creating a duplicate
- `zones.py` – approximate Kolhapur zone centres; incident → nearest zone
- `seed_demo.py` – demo incidents (flagged `demo: true`, removable from Reports page)

## After training finishes

1. Reports page → **Reload model** (or `POST /api/model/reload`).
2. Copy the final weights to `models/final.pt` to mark the model as final.

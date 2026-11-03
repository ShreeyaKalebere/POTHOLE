"""
Interactive Road Damage Label Verification & Annotation Tool
FastAPI server for web-based verification of pothole & alligator-crack datasets.

Every dataset has
  images_dir     the images (never modified)
  labels_raw     the original labels (never modified; "Reset" restores from here)
  labels_fixed   the checked / edited labels (YOLO txt) - the tool and LabelImg write here
  progress_file  JSON: filename -> {status, verified_at, box_count, pothole_count, crack_count, notes, user, source}
                 status: verified (has damage boxes) | negative (no damage) | skipped (bad image)

Datasets: the three Kolhapur / fix_labels sets below, plus every batch folder made by
make_batches.py (batches/<Dataset>_<NNN>, next to this file).

Run:  python server.py            -> http://localhost:8090
      python server.py --team     -> teammates on the same Wi-Fi open http://<this-laptop-ip>:8090
"""
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent          # manual_labeling/
ROOT = HERE.parent                               # project root
STATIC_DIR = HERE / "static"
EXPORT_DIR = HERE / "exports"
BATCHES_DIR = Path(os.getenv("VERIFIER_BATCHES", HERE / "batches"))
LABELIMG_PY = ROOT / "kolhapur_labeling" / "labelimg_env" / "Scripts" / "python.exe"
CLASSES = ["pothole", "alligator_crack"]
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
LOCK_SECONDS = 600

# ---------------------------------------------------------------- datasets
DATASETS: Dict[str, dict] = {
    "kolhapur_train": {
        "name": "Kolhapur Train Set (Morning Rides)",
        "group": "Kolhapur",
        "images_dir": ROOT / "kolhapur_labeling" / "train" / "images",
        "labels_raw": ROOT / "kolhapur_labeling" / "train" / "labels",
        "labels_fixed": ROOT / "kolhapur_labeling" / "train_fixed" / "labels",
        "progress_file": ROOT / "kolhapur_labeling" / "verification_train_progress.json",
    },
    "kolhapur_test": {
        "name": "Kolhapur Test Set (Afternoon Rides)",
        "group": "Kolhapur",
        "images_dir": ROOT / "kolhapur_labeling" / "test" / "images",
        "labels_raw": ROOT / "kolhapur_labeling" / "test" / "labels",
        "labels_fixed": ROOT / "kolhapur_labeling" / "test_fixed" / "labels",
        "progress_file": ROOT / "kolhapur_labeling" / "verification_test_progress.json",
    },
    "fix_labels_val": {
        "name": "Fix Labels Validation (Missed Boxes)",
        "group": "Kolhapur",
        "images_dir": ROOT / "fix_labels" / "val" / "images",
        "labels_raw": ROOT / "fix_labels" / "val" / "labels",
        "labels_fixed": ROOT / "fix_labels" / "val" / "labels_fixed",
        "progress_file": ROOT / "fix_labels" / "verification_progress.json",
    },
}
for _b in sorted(BATCHES_DIR.glob("*/images")):
    _d = _b.parent
    DATASETS[_d.name] = {
        "name": _d.name, "group": "POTHOLEDATASET batches", "images_dir": _b,
        "labels_raw": _d / "labels_dataset", "labels_fixed": _d / "labels",
        "progress_file": _d / "verification_progress.json", "manifest": _d / "manifest.csv",
    }

DEFAULT_DATASET = "kolhapur_train"
active_dataset_key = DEFAULT_DATASET
_locks: Dict[str, threading.RLock] = {}
_locks_guard = threading.Lock()
MOVE_TIMEOUT = 20      # seconds to wait for one file move before giving up with a clear error
_cache: Dict[str, dict] = {}          # per dataset: image list, progress (+ file mtime), manifest
_claims: Dict[str, dict] = {}         # per dataset: filename -> (user, until) so two people never get the same image


def ds_lock(key: str) -> threading.RLock:
    """One lock per dataset: trouble with a file in one batch must not freeze the other batches."""
    with _locks_guard:
        return _locks.setdefault(key, threading.RLock())


def safe_move(src: Path, dst: Path):
    """Moves a file, but never waits forever: on Windows another program (antivirus, indexer, Explorer
    preview) can block a rename indefinitely, and that must not hang the request and everyone behind it."""
    done, err = threading.Event(), []

    def run():
        try:
            shutil.move(str(src), str(dst))
        except Exception as e:
            err.append(e)
        finally:
            done.set()

    threading.Thread(target=run, daemon=True).start()
    if not done.wait(MOVE_TIMEOUT):
        raise HTTPException(503, f"{src.name} is locked by another program (antivirus or indexing?). Please try again.")
    if err:
        raise HTTPException(503, f"Could not move {src.name}: {err[0]}")


# Some image files hang forever when opened (seen on this laptop; the cause is outside this tool).
# Each attempt ties up a thread that cannot be stopped, so every read is tried once, with a time limit,
# and a file that does not answer is remembered and never opened again.
READ_TIMEOUT = 10
_reads: Dict[str, dict] = {}          # file path -> the one read attempt in progress
_read_ok: Dict[str, tuple] = {}       # file path -> (width, height) of a file that read fine
_reads_guard = threading.Lock()


def _unreadable_file(key: str) -> Path:
    return DATASETS[key]["progress_file"].with_name(f"unreadable_{key}.json")


def unreadable(key: str) -> set:
    c = _cache.setdefault(key, {})
    if "unreadable" not in c:
        f = _unreadable_file(key)
        try:
            c["unreadable"] = set(json.loads(f.read_text(encoding="utf-8"))) if f.exists() else set()
        except Exception:
            c["unreadable"] = set()
    return c["unreadable"]


def _read_bytes(path: Path) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def check_readable(key: str, path: Path) -> tuple:
    """(width, height) of the image, or HTTP 423 when the file cannot be read in time."""
    locked = HTTPException(423, f"{path.name} cannot be opened (the file hangs). Skipping it.")
    if path.name in unreadable(key):
        raise locked
    sp = str(path)
    with _reads_guard:
        if sp in _read_ok:
            return _read_ok[sp]
        job = _reads.get(sp)
        if job is None:
            job = _reads[sp] = {"done": threading.Event(), "size": (1920, 1080)}

            def run(job=job):
                try:
                    data = _read_bytes(path)
                    with Image.open(io.BytesIO(data)) as im:
                        job["size"] = im.size
                except Exception:
                    pass                    # a damaged picture still answers; only a hang counts as unreadable
                job["done"].set()

            threading.Thread(target=run, daemon=True).start()
    if not job["done"].wait(READ_TIMEOUT):
        with ds_lock(key):
            names = unreadable(key)
            names.add(path.name)
            _unreadable_file(key).write_text(json.dumps(sorted(names), indent=1), encoding="utf-8")
        print(f"UNREADABLE FILE (hangs when opened): {path}")
        raise locked
    with _reads_guard:
        _reads.pop(sp, None)
        _read_ok[sp] = job["size"]
    return job["size"]


def get_dataset_config(key: Optional[str] = None):
    k = key or active_dataset_key
    if k not in DATASETS:
        raise HTTPException(status_code=400, detail=f"Unknown dataset '{k}'")
    ds = DATASETS[k]
    ds["labels_fixed"].mkdir(parents=True, exist_ok=True)
    return k, ds


def get_image_list(key: str) -> List[Path]:
    c = _cache.setdefault(key, {})
    if "images" not in c:
        d = DATASETS[key]["images_dir"]
        c["images"] = sorted((p for p in d.iterdir() if p.suffix.lower() in IMG_EXT), key=lambda x: x.name) if d.exists() else []
        c["index"] = {p.name: i for i, p in enumerate(c["images"])}
    return c["images"]


def image_at(key: str, index: int, filename: Optional[str] = None) -> Path:
    """The image at `index`. With `filename`, also checks it is still the same image: after a delete
    the indexes shift, and a page that has not reloaded yet must not save onto the wrong image."""
    images = get_image_list(key)
    if index < 0 or index >= len(images):
        raise HTTPException(status_code=404, detail="Image index out of bounds")
    if filename and images[index].name != filename:
        raise HTTPException(status_code=409, detail="The image list changed (an image was deleted). Reloading - please redo this image.")
    return images[index]


def trash_dir(ds) -> Path:
    return ds["images_dir"].parent / "_deleted_images"


def trash_log(ds) -> List[dict]:
    f = trash_dir(ds) / "deleted.json"
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    except Exception:
        return []


def save_trash_log(ds, log):
    t = trash_dir(ds)
    t.mkdir(parents=True, exist_ok=True)
    (t / "deleted.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


def get_manifest(key: str) -> Dict[str, dict]:
    c = _cache.setdefault(key, {})
    if "manifest" not in c:
        m = DATASETS[key].get("manifest")
        c["manifest"] = {}
        if m and m.exists():
            with open(m, encoding="utf-8") as f:
                c["manifest"] = {r["name"]: r for r in csv.DictReader(f)}
    return c["manifest"]


def load_progress(key: str) -> Dict[str, dict]:
    pf = DATASETS[key]["progress_file"]
    c = _cache.setdefault(key, {})
    mtime = pf.stat().st_mtime if pf.exists() else 0
    if c.get("progress_mtime") != mtime:
        data = {}
        if pf.exists():
            try:
                data = json.loads(pf.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        for v in data.values():             # entries written by the first version had no status
            v.setdefault("status", "verified" if v.get("box_count", 0) else "negative")
        c["progress"], c["progress_mtime"] = data, mtime
    return c["progress"]


def save_progress(key: str, data: Dict[str, dict]):
    pf = DATASETS[key]["progress_file"]
    tmp = pf.with_name(f"{pf.stem}.tmp.json")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(pf)
    c = _cache.setdefault(key, {})
    c["progress"], c["progress_mtime"] = data, pf.stat().st_mtime


# ---------------------------------------------------------------- label files
def parse_yolo_file(file_path: Path):
    """YOLO txt -> list of boxes. Returns None when the file does not exist."""
    if not file_path.exists():
        return None
    boxes = []
    try:
        for line in file_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            cls_id = int(float(parts[0]))
            if cls_id not in (0, 1):
                continue
            boxes.append({
                "class_id": cls_id, "class_name": CLASSES[cls_id],
                "x_center": float(parts[1]), "y_center": float(parts[2]),
                "width": float(parts[3]), "height": float(parts[4]),
                "confidence": round(float(parts[5]), 3) if len(parts) > 5 else 1.0,
            })
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return boxes


def write_yolo_file(file_path: Path, boxes):
    lines = []
    for b in boxes:
        xc, yc = max(0.0, min(1.0, float(b["x_center"]))), max(0.0, min(1.0, float(b["y_center"])))
        bw, bh = max(0.001, min(1.0, float(b["width"]))), max(0.001, min(1.0, float(b["height"])))
        lines.append(f"{int(b['class_id'])} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
    file_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def current_label(ds, stem):
    """(boxes, source): the fixed label if there is one, else the raw label, else none."""
    fixed, raw = ds["labels_fixed"] / f"{stem}.txt", ds["labels_raw"] / f"{stem}.txt"
    b = parse_yolo_file(fixed)
    if b is not None:
        edited = not raw.exists() or raw.read_bytes() != fixed.read_bytes()
        return b, ("fixed" if edited else "raw")
    b = parse_yolo_file(raw)
    return (b, "raw") if b is not None else ([], "none")


def counts_of(boxes):
    return sum(b["class_id"] == 0 for b in boxes), sum(b["class_id"] == 1 for b in boxes)


def neighbour(key, index, step, want):
    """Next/previous index (step +1/-1) whose status matches `want` ('all', 'unverified', a status)."""
    images, prog = get_image_list(key), load_progress(key)
    j = index + step
    while 0 <= j < len(images):
        st = prog.get(images[j].name, {}).get("status", "unverified")
        if want == "all" or st == want:
            return j
        j += step
    return None


# ---------------------------------------------------------------- AI model
class AI:
    model = None
    imgsz = 640
    device = "cpu"
    path = None
    lock = threading.Lock()

    @classmethod
    def predict(cls, image_path, conf):
        with cls.lock:
            if cls.model is None:
                import torch
                from ultralytics import YOLO
                p = ROOT / "models" / "final.pt"
                if not p.exists():
                    cands = sorted(ROOT.glob("runs/**/best.pt"), key=lambda x: x.stat().st_mtime, reverse=True)
                    if not cands:
                        raise HTTPException(500, "No model weights found (models/final.pt)")
                    p = cands[0]
                print(f"Loading YOLO model from {p} ...")
                cls.model, cls.path = YOLO(str(p)), p
                # predict at the resolution the weights were trained at
                cls.imgsz = int(((cls.model.ckpt or {}).get("train_args") or {}).get("imgsz", 640))
                cls.device = 0 if torch.cuda.is_available() else "cpu"
            try:
                res = cls.model.predict(str(image_path), conf=conf, imgsz=cls.imgsz, device=cls.device, verbose=False)[0]
            except Exception as e:
                if cls.device == "cpu":
                    raise HTTPException(500, f"AI error: {e}")
                # the laptop GPU can drop out (e.g. after sleep): carry on on the CPU instead of failing every call
                print(f"GPU inference failed ({e}); switching AI to CPU")
                cls.device = "cpu"
                from ultralytics import YOLO
                cls.model = YOLO(str(cls.path))      # fresh copy: the old one lives on the broken GPU
                try:
                    res = cls.model.predict(str(image_path), conf=conf, imgsz=cls.imgsz, device="cpu", verbose=False)[0]
                except Exception as e2:
                    raise HTTPException(500, f"AI error: {e2}")
        H, W = res.orig_shape
        out = []
        for b in res.boxes:
            cls_id = int(b.cls)
            if cls_id not in (0, 1):
                continue
            x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
            out.append({"class_id": cls_id, "class_name": CLASSES[cls_id],
                        "x_center": round((x1 + x2) / 2 / W, 6), "y_center": round((y1 + y2) / 2 / H, 6),
                        "width": round((x2 - x1) / W, 6), "height": round((y2 - y1) / H, 6),
                        "confidence": round(float(b.conf), 3)})
        return out


AI_JOB = {"running": False, "dataset": None, "done": 0, "total": 0, "boxes": 0, "error": None, "stop": False}


def run_ai_batch(key, mode, conf):
    AI_JOB.update(running=True, dataset=key, done=0, total=0, boxes=0, error=None, stop=False)
    try:
        ds, prog = DATASETS[key], load_progress(key)
        todo = [p for p in get_image_list(key) if p.name not in prog]
        if mode == "missing":   # only images with no label at all
            todo = [p for p in todo if not (ds["labels_fixed"] / f"{p.stem}.txt").exists()
                    and not (ds["labels_raw"] / f"{p.stem}.txt").exists()]
        AI_JOB["total"] = len(todo)
        for p in todo:
            if AI_JOB["stop"]:
                break
            try:
                check_readable(key, p)
            except HTTPException:
                continue
            boxes = AI.predict(p, conf)
            write_yolo_file(ds["labels_fixed"] / f"{p.stem}.txt", boxes)
            AI_JOB["done"] += 1
            AI_JOB["boxes"] += len(boxes)
    except Exception as e:
        AI_JOB["error"] = str(getattr(e, "detail", e))
    finally:
        AI_JOB["running"] = False


# ---------------------------------------------------------------- API
app = FastAPI(title="Road Damage Label Verification Tool", version="3.0")


class BoxModel(BaseModel):
    class_id: int
    class_name: Optional[str] = None
    x_center: float
    y_center: float
    width: float
    height: float
    confidence: Optional[float] = 1.0


class VerifyPayload(BaseModel):
    dataset: Optional[str] = None
    boxes: List[BoxModel]
    notes: Optional[str] = ""
    user: Optional[str] = ""
    source: Optional[str] = ""      # "ai" when the saved boxes came from the AI button
    filename: Optional[str] = None


class SkipPayload(BaseModel):
    dataset: Optional[str] = None
    notes: Optional[str] = ""
    user: Optional[str] = ""
    filename: Optional[str] = None


class SwitchDatasetPayload(BaseModel):
    dataset: str


class PredictPayload(BaseModel):
    dataset: Optional[str] = None
    conf: Optional[float] = 0.25
    filename: Optional[str] = None


class BatchPredictPayload(BaseModel):
    dataset: str
    mode: str = "missing"           # missing | unverified
    conf: float = 0.25


class UserPayload(BaseModel):
    dataset: str
    user: Optional[str] = ""


@app.get("/api/datasets")
def list_datasets():
    res = []
    for k, v in DATASETS.items():
        prog = load_progress(k)
        res.append({"key": k, "name": v["name"], "group": v["group"], "total_images": len(get_image_list(k)),
                    "verified_count": len(prog), "is_active": k == active_dataset_key})
    return {"datasets": res, "active": active_dataset_key}


@app.post("/api/dataset/select")
def select_dataset(payload: SwitchDatasetPayload):
    global active_dataset_key
    if payload.dataset not in DATASETS:
        raise HTTPException(status_code=400, detail="Invalid dataset key")
    active_dataset_key = payload.dataset
    return {"success": True, "active": active_dataset_key}


@app.get("/api/stats")
def get_stats(dataset: Optional[str] = None):
    key, ds = get_dataset_config(dataset)
    images, prog = get_image_list(key), load_progress(key)
    st = {"verified": 0, "negative": 0, "skipped": 0}
    pothole = crack = 0
    people: Dict[str, dict] = {}
    for p in images:
        e = prog.get(p.name)
        if e:
            st[e["status"]] = st.get(e["status"], 0) + 1
            pothole += e.get("pothole_count", 0)
            crack += e.get("crack_count", 0)
            u = people.setdefault(e.get("user") or "(no name)", {"user": e.get("user") or "(no name)", "verified": 0, "negative": 0, "skipped": 0})
            u[e["status"]] = u.get(e["status"], 0) + 1
    done = sum(st.values())
    return {"dataset": key, "total_images": len(images), "verified_count": done,
            "pending_count": max(0, len(images) - done), "damage_count": st["verified"],
            "clean_count": st["negative"], "skipped_count": st["skipped"],
            "pothole_count": pothole, "crack_count": crack, "deleted_count": len(trash_log(ds)), "people": sorted(people.values(), key=lambda u: u["user"])}


@app.get("/api/images")
def get_images(dataset: Optional[str] = None, filter: str = "all", search: str = "", offset: int = 0, limit: int = 60):
    key, ds = get_dataset_config(dataset)
    images, prog = get_image_list(key), load_progress(key)
    s = search.lower().strip()
    matched = []
    for i, p in enumerate(images):
        if s and s not in p.name.lower():
            continue
        e = prog.get(p.name)
        status = e["status"] if e else "unverified"
        if filter in ("unverified", "verified", "negative", "skipped") and status != filter:
            continue
        if filter in ("has_damage", "empty_road"):
            n = e["box_count"] if e else len(current_label(ds, p.stem)[0])
            if (filter == "has_damage") != (n > 0):
                continue
        matched.append((i, p, status))
    items = []
    for i, p, status in matched[offset:offset + limit]:
        boxes, source = current_label(ds, p.stem)
        items.append({"index": i, "filename": p.name, "status": status, "is_verified": status != "unverified",
                      "box_count": len(boxes), "source": source, "boxes": boxes})
    return {"total_matched": len(matched), "total_dataset": len(images), "images": items}


@app.get("/api/next")
def next_unverified(dataset: str, user: str = "", after: int = -1):
    """Next not-yet-checked image after `after` (wraps around) that nobody else has open."""
    key, ds = get_dataset_config(dataset)
    images, prog = get_image_list(key), load_progress(key)
    now = time.time()
    bad = unreadable(key)
    with ds_lock(key):
        claims = _claims.setdefault(key, {})
        order = list(range(after + 1, len(images))) + list(range(0, after + 1))
        for j in order:
            name = images[j].name
            if name in prog or name in bad:
                continue
            who, until = claims.get(name, ("", 0))
            if until > now and who != user:
                continue
            claims[name] = (user, now + LOCK_SECONDS)
            return {"index": j}
    return {"index": None, "unreadable": sum(p.name in bad for p in images)}


@app.get("/api/image/{index}")
def get_image_details(index: int, dataset: Optional[str] = None, filter: str = "all", filename: Optional[str] = None):
    key, ds = get_dataset_config(dataset)
    images = get_image_list(key)
    if filename and not (0 <= index < len(images) and images[index].name == filename):
        index = _cache[key]["index"].get(filename, -1)      # the list changed since the page got this index
        if index < 0:
            raise HTTPException(status_code=404, detail=f"{filename} is no longer in this dataset (deleted?)")
    if index < 0 or index >= len(images):
        raise HTTPException(status_code=404, detail="Image index out of bounds")
    p = images[index]
    prog = load_progress(key)
    info = prog.get(p.name)
    w, h = check_readable(key, p)
    boxes, source = current_label(ds, p.stem)
    raw = parse_yolo_file(ds["labels_raw"] / f"{p.stem}.txt")
    m = get_manifest(key).get(p.name, {})
    nxt = next((j for j in list(range(index + 1, len(images))) + list(range(0, index)) if images[j].name not in prog), None)
    return {
        "index": index, "filename": p.name, "width": w, "height": h,
        "status": info["status"] if info else "unverified", "is_verified": info is not None, "verified_info": info,
        "source": source, "boxes": boxes, "raw_box_count": None if raw is None else len(raw),
        "original": m.get("original", ""), "hint": m.get("hint", ""),
        "total_images": len(images), "next_unverified_index": nxt,
        "prev_index": neighbour(key, index, -1, filter), "next_index": neighbour(key, index, +1, filter),
    }


@app.get("/api/image_raw/{index}")
def get_image_raw(index: int, dataset: Optional[str] = None, f: Optional[str] = None):
    key, ds = get_dataset_config(dataset)
    images = get_image_list(key)
    if f:
        target = ds["images_dir"] / Path(f).name
        if target.exists():
            check_readable(key, target)
            return FileResponse(str(target), headers={"Cache-Control": "no-cache, must-revalidate"})
    if index < 0 or index >= len(images):
        raise HTTPException(status_code=404, detail="Image index out of bounds")
    check_readable(key, images[index])
    return FileResponse(str(images[index]), headers={"Cache-Control": "no-cache, must-revalidate"})


def _record(key, name, status, boxes, notes, user, source):
    pc, cc = counts_of(boxes)
    with ds_lock(key):
        prog = dict(load_progress(key))
        prog[name] = {"status": status, "verified_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "box_count": len(boxes), "pothole_count": pc, "crack_count": cc,
                      "notes": notes or "", "user": user or "", "source": source or ""}
        save_progress(key, prog)
        _claims.get(key, {}).pop(name, None)


@app.post("/api/verify/{index}")
def verify_image(index: int, payload: VerifyPayload):
    """Saves the boxes as the checked label. No boxes = image checked as 'no damage'."""
    key, ds = get_dataset_config(payload.dataset)
    p = image_at(key, index, payload.filename)
    boxes = [b.model_dump() for b in payload.boxes if b.class_id in (0, 1) and b.width > 0.001 and b.height > 0.001]
    fixed_file = ds["labels_fixed"] / f"{p.stem}.txt"
    write_yolo_file(fixed_file, boxes)
    _record(key, p.name, "verified" if boxes else "negative", boxes, payload.notes, payload.user, payload.source)
    return {"success": True, "saved_file": str(fixed_file), "box_count": len(boxes),
            "status": "verified" if boxes else "negative",
            "next_unverified_index": next_unverified(key, payload.user or "", index)["index"]}


@app.post("/api/skip/{index}")
def skip_image(index: int, payload: SkipPayload):
    """Bad image (blurry, not a road, duplicate...). Its label file is left as it is; export leaves it out."""
    key, ds = get_dataset_config(payload.dataset)
    p = image_at(key, index, payload.filename)
    _record(key, p.name, "skipped", [], payload.notes, payload.user, "")
    return {"success": True, "next_unverified_index": next_unverified(key, payload.user or "", index)["index"]}


@app.post("/api/unverify/{index}")
def unverify_image(index: int, dataset: Optional[str] = None, filename: Optional[str] = None):
    key, ds = get_dataset_config(dataset)
    p = image_at(key, index, filename)
    with ds_lock(key):
        prog = dict(load_progress(key))
        if prog.pop(p.name, None) is not None:
            save_progress(key, prog)
    return {"success": True, "is_verified": False}


@app.post("/api/reset/{index}")
def reset_image(index: int, dataset: Optional[str] = None, filename: Optional[str] = None):
    """Throws away the edited label (labels_fixed) so the original raw label shows again; marks unchecked."""
    key, ds = get_dataset_config(dataset)
    p = image_at(key, index, filename)
    fixed, raw = ds["labels_fixed"] / f"{p.stem}.txt", ds["labels_raw"] / f"{p.stem}.txt"
    if raw.exists():
        shutil.copy2(raw, fixed)
    elif fixed.exists():
        fixed.unlink()
    unverify_image(index, key, p.name)
    return {"success": True}


@app.post("/api/predict/{index}")
def predict_image(index: int, payload: PredictPayload):
    key, ds = get_dataset_config(payload.dataset)
    p = image_at(key, index, payload.filename)
    check_readable(key, p)
    t0 = time.time()
    boxes = AI.predict(p, payload.conf or 0.25)
    return {"success": True, "inference_ms": round((time.time() - t0) * 1000, 1), "boxes": boxes,
            "count": len(boxes), "device": str(AI.device), "model": str(AI.path)}


# ---------------------------------------------------------------- delete / restore
@app.post("/api/delete/{index}")
def delete_image(index: int, payload: SkipPayload):
    """Removes the image from the dataset: the image and its labels move to <dataset>/../_deleted_images
    (Restore puts them back; 'Empty deleted folder' removes them for good)."""
    key, ds = get_dataset_config(payload.dataset)
    with ds_lock(key):
        p = image_at(key, index, payload.filename)
        t = trash_dir(ds)
        moves = [(ds["labels_fixed"] / f"{p.stem}.txt", t / "labels_fixed" / f"{p.stem}.txt"),
                 (ds["labels_raw"] / f"{p.stem}.txt", t / "labels_raw" / f"{p.stem}.txt"),
                 (p, t / "images" / p.name)]       # image last: until it moves, the image stays in the dataset
        moved = []
        try:
            for src, dst in moves:
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    safe_move(src, dst)
                    moved.append((src, dst))
        except HTTPException:
            for src, dst in moved:             # the image stayed: its labels go back with it
                if dst.exists() and not src.exists():
                    shutil.move(str(dst), str(src))
            raise
        prog = dict(load_progress(key))
        before = prog.pop(p.name, {}).get("status", "unverified")
        save_progress(key, prog)
        log = [e for e in trash_log(ds) if e["filename"] != p.name]
        log.append({"filename": p.name, "deleted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "user": payload.user or "", "status_before": before})
        save_trash_log(ds, log)
        _cache[key].pop("images", None)          # indexes shift after a delete
        _claims.get(key, {}).pop(p.name, None)
        n = len(get_image_list(key))
    return {"success": True, "deleted": p.name, "total_images": n,
            "next_index": min(index, n - 1) if n else None,
            "next_unverified_index": next_unverified(key, payload.user or "", index - 1)["index"] if n else None}


@app.get("/api/deleted")
def list_deleted(dataset: str):
    key, ds = get_dataset_config(dataset)
    t = trash_dir(ds)
    log = trash_log(ds)
    known = {e["filename"] for e in log}
    late = [f.name for f in (t / "images").iterdir() if f.name not in known] if (t / "images").exists() else []
    if late:
        with ds_lock(key):
            log += [{"filename": n, "deleted_at": time.strftime("%Y-%m-%d %H:%M:%S"), "user": "", "status_before": "unverified"} for n in late]
            save_trash_log(ds, log)
            _cache.get(key, {}).pop("images", None)
    items = [e for e in log if (t / "images" / e["filename"]).exists()]
    return {"total": len(items), "images": items[::-1]}


@app.get("/api/deleted_raw")
def deleted_raw(dataset: str, filename: str):
    key, ds = get_dataset_config(dataset)
    if Path(filename).name != filename:
        raise HTTPException(400, "bad file name")
    f = trash_dir(ds) / "images" / filename
    if not f.exists():
        raise HTTPException(404, "not in the deleted folder")
    check_readable(key, f)
    return FileResponse(str(f))


class RestorePayload(BaseModel):
    dataset: str
    filename: str


@app.post("/api/restore")
def restore_image(payload: RestorePayload):
    key, ds = get_dataset_config(payload.dataset)
    name = Path(payload.filename).name
    stem = Path(name).stem
    t = trash_dir(ds)
    with ds_lock(key):
        if not (t / "images" / name).exists():
            raise HTTPException(404, "not in the deleted folder")
        if (ds["images_dir"] / name).exists():
            raise HTTPException(409, "an image with this name is already in the dataset")
        for src, dst in [(t / "images" / name, ds["images_dir"] / name),
                         (t / "labels_fixed" / f"{stem}.txt", ds["labels_fixed"] / f"{stem}.txt"),
                         (t / "labels_raw" / f"{stem}.txt", ds["labels_raw"] / f"{stem}.txt")]:
            if src.exists() and not dst.exists():
                safe_move(src, dst)
        save_trash_log(ds, [e for e in trash_log(ds) if e["filename"] != name])
        _cache[key].pop("images", None)
        get_image_list(key)
        idx = _cache[key]["index"].get(name)
    return {"success": True, "restored": name, "index": idx}


@app.post("/api/empty_deleted")
def empty_deleted(dataset: str, confirm: bool = False):
    """Permanently removes the deleted folder of this dataset (cannot be undone)."""
    key, ds = get_dataset_config(dataset)
    if not confirm:
        raise HTTPException(400, "confirm=true is required")
    t = trash_dir(ds)
    n = len(trash_log(ds))
    if t.exists():
        shutil.rmtree(t)
    return {"success": True, "removed": n}


@app.post("/api/predict_batch")
def predict_batch(payload: BatchPredictPayload):
    get_dataset_config(payload.dataset)
    if AI_JOB["running"]:
        raise HTTPException(409, f"AI is already labeling {AI_JOB['dataset']}")
    if payload.mode not in ("missing", "unverified"):
        raise HTTPException(400, "mode must be 'missing' or 'unverified'")
    threading.Thread(target=run_ai_batch, args=(payload.dataset, payload.mode, payload.conf), daemon=True).start()
    return {"started": True}


@app.get("/api/predict_batch")
def predict_batch_status():
    return AI_JOB


@app.delete("/api/predict_batch")
def predict_batch_stop():
    AI_JOB["stop"] = True
    return AI_JOB


# ---------------------------------------------------------------- LabelImg
_labelimg_opened: Dict[str, float] = {}


@app.post("/api/labelimg/open")
def labelimg_open(payload: UserPayload, request: Request):
    if request.client.host not in ("127.0.0.1", "::1"):
        raise HTTPException(403, "LabelImg can only be opened on the laptop that runs this tool")
    key, ds = get_dataset_config(payload.dataset)
    if not LABELIMG_PY.exists():
        raise HTTPException(500, f"LabelImg is not installed at {LABELIMG_PY}")
    # LabelImg only reads labels from its save folder: copy raw labels in where no fixed label exists yet
    for p in get_image_list(key):
        fixed, raw = ds["labels_fixed"] / f"{p.stem}.txt", ds["labels_raw"] / f"{p.stem}.txt"
        if not fixed.exists() and raw.exists():
            shutil.copy2(raw, fixed)
    (ds["labels_fixed"] / "classes.txt").write_text("\n".join(CLASSES) + "\n")
    _labelimg_opened[key] = time.time()
    subprocess.Popen([str(LABELIMG_PY), "-m", "labelImg.labelImg", str(ds["images_dir"]),
                      str(ds["labels_fixed"] / "classes.txt"), str(ds["labels_fixed"])])
    return {"opened": key}


def _saved_in_labelimg(key):
    since = _labelimg_opened.get(key, 0)
    if not since:
        return []
    ds, prog = DATASETS[key], load_progress(key)
    return [p for p in get_image_list(key) if p.name not in prog
            and (ds["labels_fixed"] / f"{p.stem}.txt").exists()
            and (ds["labels_fixed"] / f"{p.stem}.txt").stat().st_mtime > since]


@app.get("/api/labelimg")
def labelimg_status(dataset: str):
    key, _ = get_dataset_config(dataset)
    return {"opened": bool(_labelimg_opened.get(key)), "saved_in_labelimg": len(_saved_in_labelimg(key))}


@app.post("/api/labelimg/accept")
def labelimg_accept(payload: UserPayload):
    """Images saved in LabelImg (after it was opened from here) count as checked."""
    key, ds = get_dataset_config(payload.dataset)
    n = {"verified": 0, "negative": 0}
    for p in _saved_in_labelimg(key):
        boxes = parse_yolo_file(ds["labels_fixed"] / f"{p.stem}.txt") or []
        st = "verified" if boxes else "negative"
        _record(key, p.name, st, boxes, "", payload.user, "labelimg")
        n[st] += 1
    return n


# ---------------------------------------------------------------- export
def _group(key, name):
    """Images that must stay in the same split: frames of one video / one road sequence."""
    m = get_manifest(key).get(name, {})
    orig = m.get("original", "").replace("\\", "/")
    base = name.split(".rf.")[0]
    if "_frame_" in base:
        base = base.split("_frame_")[0]
    if orig.startswith("Pothole600/"):
        base = f"{orig.split('/')[1]}_{int(Path(name).stem) // 25}"
    elif orig.startswith("BiankatpasDataset/"):
        road, seq = orig.split("/")[2].rsplit("_", 1)
        base = f"{road}_{int(seq) // 20}"
    elif key.startswith(("kolhapur", "fix_labels")):
        base = "_".join(name.split("_")[:3])        # one ride video
    return key.rsplit("_", 1)[0] + "|" + base


@app.post("/api/export")
def export(dataset: str = "all"):
    """Checked images (verified + no damage) -> exports/<name>/ as a YOLO dataset, original file names.
    dataset=all: every dataset, split 70/15/15 by video/sequence group (stable between exports)."""
    keys = list(DATASETS) if dataset == "all" else [get_dataset_config(dataset)[0]]
    out = EXPORT_DIR / ("all_checked" if dataset == "all" else dataset)
    if out.exists():
        shutil.rmtree(out)
    summary = {sp: {"images": 0, "negative": 0, "pothole": 0, "alligator_crack": 0} for sp in ("train", "val", "test")}
    for key in keys:
        ds, prog = DATASETS[key], load_progress(key)
        for p in get_image_list(key):
            e = prog.get(p.name)
            if not e or e["status"] not in ("verified", "negative"):
                continue
            h = int(hashlib.md5(_group(key, p.name).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
            sp = "train" if h < 0.70 else "val" if h < 0.85 else "test"
            idir, ldir = out / "images" / sp / key, out / "labels" / sp / key
            idir.mkdir(parents=True, exist_ok=True)
            ldir.mkdir(parents=True, exist_ok=True)
            try:
                os.link(p, idir / p.name)
            except OSError:
                shutil.copy2(p, idir / p.name)
            boxes = (parse_yolo_file(ds["labels_fixed"] / f"{p.stem}.txt") or []) if e["status"] == "verified" else []
            write_yolo_file(ldir / f"{p.stem}.txt", boxes)
            s = summary[sp]
            s["images"] += 1
            s["negative"] += not boxes
            for b in boxes:
                s[CLASSES[b["class_id"]]] += 1
    if not any(s["images"] for s in summary.values()):
        raise HTTPException(400, "Nothing checked yet in this selection")
    (out / "data.yaml").write_text(f"path: {out.as_posix()}\ntrain: images/train\nval: images/val\ntest: images/test\n"
                                   "names:\n  0: pothole\n  1: alligator_crack\n")
    return {"folder": str(out), "split": summary}


@app.middleware("http")
async def no_stale_page(request: Request, call_next):
    """The page files (html/js/css) must be re-checked on every load, or a browser keeps running an
    old app.js after an update."""
    resp = await call_next(request)
    if not request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8090))
    host = "0.0.0.0" if "--team" in sys.argv else "127.0.0.1"
    print(f"Starting Road Damage Verifier on http://localhost:{port}")
    uvicorn.run(app, host=host, port=port)

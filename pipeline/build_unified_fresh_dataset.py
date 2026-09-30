import os
import sys
import glob
import json
import shutil
import hashlib
import random
import csv
from collections import defaultdict, Counter
import numpy as np
import cv2
from PIL import Image
import imagehash
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import yaml

# Set random seed
random.seed(42)
np.random.seed(42)

BASE_INPUT = "F:/POTHOLEDATASET"
if not os.path.exists(BASE_INPUT):
    BASE_INPUT = "C:/Users/shree/Downloads/POTHOLE/POTHOLEDATASET"

OUTPUT_DIR = "F:/RoadDamage_Fresh"

print(f"Source Datasets Path: {BASE_INPUT}")
print(f"Output Dataset Path: {OUTPUT_DIR}")

# Create output directories
for split in ["train", "val", "test"]:
    os.makedirs(os.path.join(OUTPUT_DIR, "images", split), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "labels", split), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "metadata"), exist_ok=True)
for qa_cat in ["pothole", "alligator_crack", "negative", "mixed"]:
    os.makedirs(os.path.join(OUTPUT_DIR, "qa", qa_cat), exist_ok=True)

# Metadata tracking containers
source_inventory = []
class_mapping_rows = []
image_provenance_rows = []
duplicate_report_rows = []
invalid_labels_rows = []
rejected_images_rows = []
split_manifest_rows = []

# Class definitions
# 0: pothole, 1: alligator_crack
CLASS_NAMES = {0: "pothole", 1: "alligator_crack"}

# Step 1: Record Class Mapping
class_mappings = [
    ("BharatPotHole", "0 (pothole)", 0, "pothole", "retained"),
    ("BiankatpasDataset", "POTHOLE mask", 0, "pothole", "retained"),
    ("BiankatpasDataset", "CRACK mask", -1, "discarded", "discarded (thin generic micro-crack segments)"),
    ("IndianRoadsDataset", "1 (pothole)", 0, "pothole", "retained"),
    ("IndianRoadsDataset", "0 (speed bump)", -1, "discarded", "discarded from positive classes (clean negative road)"),
    ("IndianRoadsDataset", "2 (unpaved road)", -1, "discarded", "discarded from positive classes (clean negative road)"),
    ("Pothole600", "255 (binary mask)", 0, "pothole", "retained"),
    ("RDD2022Dataset", "6512002 (pothole)", 0, "pothole", "retained"),
    ("RDD2022Dataset", "6512001 (alligator crack)", 1, "alligator_crack", "retained"),
    ("RDD2022Dataset", "6511999 (longitudinal crack)", -1, "discarded", "discarded (generic longitudinal crack)"),
    ("RDD2022Dataset", "6512000 (transverse crack)", -1, "discarded", "discarded (generic transverse crack)"),
    ("RDD2022Dataset", "6512157 (block crack)", -1, "discarded", "discarded (generic block crack)"),
    ("RDD2022Dataset", "6512161 (repair)", -1, "discarded", "discarded (road patch / repair)"),
    ("RDD2022Dataset", "6512003 (other corruption)", -1, "discarded", "discarded"),
    ("RoboflowIIT", "2 (pothole)", 0, "pothole", "retained"),
    ("RoboflowIIT", "0 (crocodile crack)", 1, "alligator_crack", "retained"),
    ("RoboflowIIT", "1 (longitudinal crack)", -1, "discarded", "discarded (generic longitudinal crack)"),
    ("SPDataset", "unannotated", -1, "discarded", "deduplicated (exact byte duplicate subset of Urban Civic)"),
    ("Urban Civic", "no", -1, "negative_road", "retained as true negative background images (empty labels)"),
    ("Urban Civic", "yes", -1, "unannotated_pothole", "held out from bbox training (lacks bounding box annotations)")
]

with open(os.path.join(OUTPUT_DIR, "metadata", "class_mapping.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["source_dataset", "original_class_raw", "final_class_id", "final_class_name", "status"])
    for row in class_mappings:
        writer.writerow(row)

print("Saved metadata/class_mapping.csv")

def clamp_box(xc, yc, w, h):
    """Normalize and strictly clamp bounding box to [0, 1]."""
    x1 = max(0.0, xc - w / 2.0)
    y1 = max(0.0, yc - h / 2.0)
    x2 = min(1.0, xc + w / 2.0)
    y2 = min(1.0, yc + h / 2.0)
    nw = x2 - x1
    nh = y2 - y1
    if nw <= 0.001 or nh <= 0.001:
        return None
    nxc = (x1 + x2) / 2.0
    nyc = (y1 + y2) / 2.0
    return round(nxc, 6), round(nyc, 6), round(nw, 6), round(nh, 6)

print("\nParsing all 8 sources into standardized candidate representations...")

# Storage for candidates: dict of list of tuples:
# {source: [{'orig_path': str, 'boxes': list of (cid, xc, yc, w, h), 'seq_id': str, 'orig_class': str, 'format': str}]}
candidates = defaultdict(list)

# -------------------------------------------------------------
# SOURCE 1: BharatPotHole
# -------------------------------------------------------------
print("Parsing BharatPotHole...")
b_dir = os.path.join(BASE_INPUT, "BharatPotHole")
b_imgs = glob.glob(os.path.join(b_dir, "**", "*.jpg"), recursive=True)
for img_path in b_imgs:
    txt_path = img_path.replace("images", "labels").replace(".jpg", ".txt")
    boxes = []
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                p = line.strip().split()
                if len(p) >= 5 and p[0] == "0":
                    try:
                        xc, yc, w, h = map(float, p[1:5])
                        cbox = clamp_box(xc, yc, w, h)
                        if cbox:
                            boxes.append((0, *cbox))
                        else:
                            invalid_labels_rows.append(["BharatPotHole", os.path.basename(img_path), line.strip(), "box_out_of_bounds_or_zero"])
                    except Exception as e:
                        invalid_labels_rows.append(["BharatPotHole", os.path.basename(img_path), line.strip(), str(e)])
    
    # Video sequence prefix extraction
    fname = os.path.basename(img_path)
    seq_id = fname.split("_frame_")[0] if "_frame_" in fname else fname[:20]
    orig_class = "pothole" if len(boxes) > 0 else "negative"
    candidates["BharatPotHole"].append({
        "orig_path": img_path,
        "boxes": boxes,
        "seq_id": "BharatPotHole_" + seq_id,
        "orig_class": orig_class,
        "format": "YOLO TXT"
    })
print(f"  BharatPotHole candidates: {len(candidates['BharatPotHole'])}")

# -------------------------------------------------------------
# SOURCE 2: RoboflowIIT (IIT Madras)
# -------------------------------------------------------------
print("Parsing RoboflowIIT...")
r_dir = os.path.join(BASE_INPUT, "RoboflowIIT")
r_imgs = glob.glob(os.path.join(r_dir, "**", "*.jpg"), recursive=True)
for img_path in r_imgs:
    txt_path = img_path.replace("images", "labels").replace(".jpg", ".txt")
    boxes = []
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                p = line.strip().split()
                if len(p) >= 5:
                    orig_cid = p[0]
                    target_cid = None
                    if orig_cid == "2":  # pothole
                        target_cid = 0
                    elif orig_cid == "0":  # crocodile crack
                        target_cid = 1
                    # orig_cid == 1 (longitudinal) is discarded
                    if target_cid is not None:
                        try:
                            xc, yc, w, h = map(float, p[1:5])
                            cbox = clamp_box(xc, yc, w, h)
                            if cbox:
                                boxes.append((target_cid, *cbox))
                            else:
                                invalid_labels_rows.append(["RoboflowIIT", os.path.basename(img_path), line.strip(), "box_out_of_bounds_or_zero"])
                        except Exception as e:
                            invalid_labels_rows.append(["RoboflowIIT", os.path.basename(img_path), line.strip(), str(e)])
    fname = os.path.basename(img_path)
    seq_id = fname.split("_jpg.rf")[0] if "_jpg.rf" in fname else fname[:15]
    orig_class = "pothole/crocodile" if len(boxes) > 0 else "negative"
    candidates["RoboflowIIT"].append({
        "orig_path": img_path,
        "boxes": boxes,
        "seq_id": "RoboflowIIT_" + seq_id,
        "orig_class": orig_class,
        "format": "YOLO TXT"
    })
print(f"  RoboflowIIT candidates: {len(candidates['RoboflowIIT'])}")

# -------------------------------------------------------------
# SOURCE 3: RDD2022Dataset (Train Set Only - 38,385 fully annotated images)
# -------------------------------------------------------------
print("Parsing RDD2022Dataset (train split)...")
rdd_dir = os.path.join(BASE_INPUT, "RDD2022Dataset", "train")
rdd_ann_files = glob.glob(os.path.join(rdd_dir, "ann", "*.json"))
POTHOLE_ID = 6512002
ALLIGATOR_ID = 6512001

for ann_path in rdd_ann_files:
    fname = os.path.basename(ann_path).replace(".json", "")
    img_path = os.path.join(rdd_dir, "img", fname)
    if not os.path.exists(img_path):
        continue
    boxes = []
    with open(ann_path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    img_h = data.get("size", {}).get("height", 512)
    img_w = data.get("size", {}).get("width", 512)
    for obj in data.get("objects", []):
        cid = obj.get("classId")
        target_cid = None
        if cid == POTHOLE_ID:
            target_cid = 0
        elif cid == ALLIGATOR_ID:
            target_cid = 1
        if target_cid is not None and obj.get("geometryType") == "rectangle":
            ext = obj.get("points", {}).get("exterior", [])
            if len(ext) == 2:
                x1, y1 = ext[0]
                x2, y2 = ext[1]
                # convert to normalized xywh
                xmin, xmax = min(x1, x2), max(x1, x2)
                ymin, ymax = min(y1, y2), max(y1, y2)
                w = (xmax - xmin) / float(img_w)
                h = (ymax - ymin) / float(img_h)
                xc = (xmin + xmax) / 2.0 / float(img_w)
                yc = (ymin + ymax) / 2.0 / float(img_h)
                cbox = clamp_box(xc, yc, w, h)
                if cbox:
                    boxes.append((target_cid, *cbox))
                else:
                    invalid_labels_rows.append(["RDD2022Dataset", fname, str(ext), "box_out_of_bounds_or_zero"])
    # Determine sequence prefix (e.g. China_Drone_000000 -> China_Drone_000, Japan_001234 -> Japan_001)
    parts = fname.split("_")
    seq_id = "_".join(parts[:-1]) if len(parts) > 1 else fname[:10]
    orig_class = "damage" if len(boxes) > 0 else "other/none"
    candidates["RDD2022Dataset"].append({
        "orig_path": img_path,
        "boxes": boxes,
        "seq_id": "RDD2022_" + seq_id,
        "orig_class": orig_class,
        "format": "Supervisely JSON"
    })
print(f"  RDD2022 candidates parsed: {len(candidates['RDD2022Dataset'])}")

# -------------------------------------------------------------
# SOURCE 4: IndianRoadsDataset
# -------------------------------------------------------------
print("Parsing IndianRoadsDataset...")
ir_dir = os.path.join(BASE_INPUT, "IndianRoadsDataset")
ir_imgs = glob.glob(os.path.join(ir_dir, "*.jpg"))
for img_path in ir_imgs:
    txt_path = img_path.replace(".jpg", ".txt")
    boxes = []
    has_other_class = False
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                p = line.strip().split()
                if len(p) >= 5:
                    if p[0] == "1":  # pothole
                        try:
                            xc, yc, w, h = map(float, p[1:5])
                            cbox = clamp_box(xc, yc, w, h)
                            if cbox:
                                boxes.append((0, *cbox))
                            else:
                                invalid_labels_rows.append(["IndianRoadsDataset", os.path.basename(img_path), line.strip(), "box_out_of_bounds"])
                        except Exception as e:
                            invalid_labels_rows.append(["IndianRoadsDataset", os.path.basename(img_path), line.strip(), str(e)])
                    else:
                        has_other_class = True
    fname = os.path.basename(img_path)
    seq_id = fname.split("_")[0] if "_" in fname else fname.split("+")[0]
    orig_class = "pothole" if len(boxes) > 0 else ("bump_or_unpaved" if has_other_class else "negative")
    candidates["IndianRoadsDataset"].append({
        "orig_path": img_path,
        "boxes": boxes,
        "seq_id": "IndianRoads_" + seq_id,
        "orig_class": orig_class,
        "format": "YOLO TXT"
    })
print(f"  IndianRoads candidates: {len(candidates['IndianRoadsDataset'])}")

# -------------------------------------------------------------
# SOURCE 5: Pothole600 (Fresh)
# -------------------------------------------------------------
print("Parsing Pothole600...")
p600_dir = os.path.join(BASE_INPUT, "Pothole600")
for split in ["training", "validation", "testing"]:
    rgb_dir = os.path.join(p600_dir, split, "rgb")
    lbl_dir = os.path.join(p600_dir, split, "label")
    for img_file in os.listdir(rgb_dir):
        if img_file.lower().endswith(".png"):
            img_path = os.path.join(rgb_dir, img_file)
            mask_path = os.path.join(lbl_dir, img_file)
            boxes = []
            if os.path.exists(mask_path):
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                if mask is not None and np.max(mask) > 0:
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    h, w = mask.shape
                    for c in contours:
                        bx, by, bw, bh = cv2.boundingRect(c)
                        if bw >= 5 and bh >= 5:
                            xc = (bx + bw / 2.0) / float(w)
                            yc = (by + bh / 2.0) / float(h)
                            nw = bw / float(w)
                            nh = bh / float(h)
                            cbox = clamp_box(xc, yc, nw, nh)
                            if cbox:
                                boxes.append((0, *cbox))
            candidates["Pothole600"].append({
                "orig_path": img_path,
                "boxes": boxes,
                "seq_id": f"Pothole600_{split}_{img_file[:2]}",
                "orig_class": "pothole",
                "format": "Binary Mask PNG"
            })
print(f"  Pothole600 candidates: {len(candidates['Pothole600'])}")

# -------------------------------------------------------------
# SOURCE 6: BiankatpasDataset
# -------------------------------------------------------------
print("Parsing BiankatpasDataset...")
bian_dir = os.path.join(BASE_INPUT, "BiankatpasDataset", "Dataset")
for d in os.listdir(bian_dir):
    sub = os.path.join(bian_dir, d)
    if not os.path.isdir(sub):
        continue
    for f in os.listdir(sub):
        if "_RAW" in f and f.lower().endswith(('.jpg', '.png')):
            img_path = os.path.join(sub, f)
            pothole_mask_file = f.replace("_RAW", "_POTHOLE").replace(".jpg", ".png")
            mask_path = os.path.join(sub, pothole_mask_file)
            boxes = []
            if os.path.exists(mask_path):
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                if mask is not None and np.max(mask) > 0:
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    h, w = mask.shape
                    for c in contours:
                        bx, by, bw, bh = cv2.boundingRect(c)
                        if bw >= 10 and bh >= 10:
                            xc = (bx + bw / 2.0) / float(w)
                            yc = (by + bh / 2.0) / float(h)
                            nw = bw / float(w)
                            nh = bh / float(h)
                            cbox = clamp_box(xc, yc, nw, nh)
                            if cbox:
                                boxes.append((0, *cbox))
            candidates["BiankatpasDataset"].append({
                "orig_path": img_path,
                "boxes": boxes,
                "seq_id": f"Biankatpas_{d[:15]}",
                "orig_class": "pothole" if len(boxes) > 0 else "road",
                "format": "Binary Mask PNG"
            })
print(f"  Biankatpas candidates: {len(candidates['BiankatpasDataset'])}")

# -------------------------------------------------------------
# SOURCE 7: Urban Civic (no: clean negatives, yes: held out)
# -------------------------------------------------------------
print("Parsing Urban Civic...")
uc_dir = os.path.join(BASE_INPUT, "Urban Civic")
for f in os.listdir(os.path.join(uc_dir, "no")):
    if f.lower().endswith(('.jpg', '.png', '.jpeg')):
        img_path = os.path.join(uc_dir, "no", f)
        candidates["Urban Civic"].append({
            "orig_path": img_path,
            "boxes": [], # Negative road image
            "seq_id": "UrbanCivic_no",
            "orig_class": "plain_road_negative",
            "format": "Image Folder"
        })
for f in os.listdir(os.path.join(uc_dir, "yes")):
    if f.lower().endswith(('.jpg', '.png', '.jpeg')):
        img_path = os.path.join(uc_dir, "yes", f)
        rejected_images_rows.append(["Urban Civic", f, "unannotated_positive_held_out_to_prevent_false_negative_learning"])
print(f"  Urban Civic negative candidates: {len(candidates['Urban Civic'])}")

# -------------------------------------------------------------
# SOURCE 8: SPDataset (Handled via deduplication against Urban Civic)
# -------------------------------------------------------------
print("Parsing SPDataset...")
sp_dir = os.path.join(BASE_INPUT, "SPDataset")
for f in os.listdir(sp_dir):
    if f.lower().endswith(('.jpg', '.png', '.jpeg')):
        img_path = os.path.join(sp_dir, f)
        # Marked for deduplication check against Urban Civic
        candidates["SPDataset"].append({
            "orig_path": img_path,
            "boxes": [],
            "seq_id": "SPDataset",
            "orig_class": "unannotated",
            "format": "Image Folder"
        })
print(f"  SPDataset candidates: {len(candidates['SPDataset'])}")

# -------------------------------------------------------------
# STEP 2: Selection & Deduplication Across All Sources
# -------------------------------------------------------------
print("\n--- Running Deduplication & Image Validation Engine ---")

# Priorities when duplicates are found:
# Highest: RoboflowIIT, RDD2022, BharatPotHole, IndianRoads, Pothole600, Biankatpas, Urban Civic, SPDataset
SOURCE_PRIORITY = {
    "RoboflowIIT": 10,
    "RDD2022Dataset": 9,
    "BharatPotHole": 8,
    "IndianRoadsDataset": 7,
    "Pothole600": 6,
    "BiankatpasDataset": 5,
    "Urban Civic": 4,
    "SPDataset": 1
}

# Categorize items into:
# 1. Target Positive Images (images containing pothole or alligator crack boxes)
# 2. Balanced Negative Road Images (plain road, speed bumps, unpaved road without damage)
positives = []
negatives_pool = []

for ds, items in candidates.items():
    for item in items:
        item["source"] = ds
        if len(item["boxes"]) > 0:
            positives.append(item)
        else:
            negatives_pool.append(item)

print(f"Total Positive Damage Candidates: {len(positives)}")
print(f"Total Negative Road Candidates: {len(negatives_pool)}")

# Deduplication among positives and selected negatives
# We select all valid positives, plus a balanced subset of negatives to reach ~22,000 unique valid images!
# Negative targets: ~1,000 from BharatPotHole, ~1,000 from IndianRoads (bump/unpaved), ~1,000 from Urban Civic (no).
random.shuffle(negatives_pool)
selected_negatives = []
neg_source_counts = Counter()
for neg in negatives_pool:
    src = neg["source"]
    if src == "SPDataset":
        continue # SPDataset duplicates Urban Civic
    if neg_source_counts[src] < 1000:
        selected_negatives.append(neg)
        neg_source_counts[src] += 1

print(f"Selected Negative Road Images: {len(selected_negatives)} ({dict(neg_source_counts)})")

selected_candidates = positives + selected_negatives
print(f"Total Candidates for Unified Dataset: {len(selected_candidates)}")

# Compute SHA-256 and pHash for deduplication
print("Computing image hashes for deduplication and provenance...")
seen_sha256 = {} # sha -> item
seen_phash = {}  # phash_str -> item
phash_buckets = [defaultdict(list) for _ in range(4)] # 4 buckets for 16-bit chunks
final_items = []
duplicate_count = 0
near_duplicate_count = 0

def get_chunks(h_int):
    return (
        (h_int >> 48) & 0xFFFF,
        (h_int >> 32) & 0xFFFF,
        (h_int >> 16) & 0xFFFF,
        h_int & 0xFFFF
    )

# Sort selected candidates by priority so best annotated versions are kept
selected_candidates.sort(key=lambda x: (SOURCE_PRIORITY.get(x["source"], 0), len(x["boxes"])), reverse=True)

for idx, item in enumerate(selected_candidates):
    p = item["orig_path"]
    try:
        with open(p, "rb") as fp:
            data = fp.read()
            if len(data) == 0:
                rejected_images_rows.append([item["source"], os.path.basename(p), "zero_byte_file"])
                continue
            sha = hashlib.sha256(data).hexdigest()
        
        # Check exact duplicate
        if sha in seen_sha256:
            duplicate_count += 1
            kept = seen_sha256[sha]
            duplicate_report_rows.append([
                "exact_sha256",
                os.path.basename(kept["orig_path"]),
                os.path.basename(p),
                kept["source"],
                item["source"],
                sha,
                0
            ])
            continue
        
        # Open with PIL to verify integrity and compute pHash
        with Image.open(p) as img:
            img.load()
            w, h = img.size
            ph = imagehash.phash(img)
            ph_str = str(ph)
            ph_int = int(ph_str, 16)
            
        # Fast bucketed near-duplicate check (distance <= 2)
        chunks = get_chunks(ph_int)
        candidate_near_dups = []
        seen_cand_ids = set()
        for b_idx, c_val in enumerate(chunks):
            for existing_item in phash_buckets[b_idx].get(c_val, []):
                item_id = id(existing_item)
                if item_id not in seen_cand_ids:
                    seen_cand_ids.add(item_id)
                    candidate_near_dups.append(existing_item)
                
        is_near_dup = False
        for kept in candidate_near_dups:
            kept_ph = imagehash.hex_to_hash(kept["phash"])
            dist = ph - kept_ph
            if dist <= 2:
                is_near_dup = True
                near_duplicate_count += 1
                duplicate_report_rows.append([
                    "near_duplicate_phash",
                    os.path.basename(kept["orig_path"]),
                    os.path.basename(p),
                    kept["source"],
                    item["source"],
                    ph_str,
                    int(dist)
                ])
                break
                
        if is_near_dup:
            continue
            
        item["sha256"] = sha
        item["phash"] = ph_str
        item["ph_int"] = ph_int
        item["width"] = w
        item["height"] = h
        
        seen_sha256[sha] = item
        seen_phash[ph_str] = item
        for b_idx, c_val in enumerate(chunks):
            phash_buckets[b_idx][c_val].append(item)
            
        final_items.append(item)
        if len(final_items) % 2000 == 0:
            print(f"  Processed {len(final_items)} unique valid images...")
        
    except Exception as e:
        rejected_images_rows.append([item["source"], os.path.basename(p), f"corrupt_or_unreadable: {str(e)}"])

print(f"Deduplication complete: {duplicate_count} exact duplicates, {near_duplicate_count} near duplicates removed.")
print(f"Total Unique Valid Images: {len(final_items)}")

# -------------------------------------------------------------
# STEP 3: Sequence-Aware 70 / 15 / 15 Split Assignment
# -------------------------------------------------------------
print("\nAssigning sequence-aware 70% Train / 15% Val / 15% Test splits...")

# Group items by sequence_id
seq_groups = defaultdict(list)
for item in final_items:
    seq_groups[item["seq_id"]].append(item)

# Sort sequences randomly with fixed seed
seq_keys = sorted(list(seq_groups.keys()))
random.shuffle(seq_keys)

# Stratify sequences into train (70%), val (15%), test (15%)
total_final = len(final_items)
target_train = int(0.70 * total_final)
target_val = int(0.15 * total_final)
target_test = total_final - target_train - target_val

split_items = {"train": [], "val": [], "test": []}
current_train = 0
current_val = 0

for seq in seq_keys:
    group = seq_groups[seq]
    g_len = len(group)
    if current_train + g_len <= target_train:
        split_items["train"].extend(group)
        for it in group:
            it["split"] = "train"
        current_train += g_len
    elif current_val + g_len <= target_val:
        split_items["val"].extend(group)
        for it in group:
            it["split"] = "val"
        current_val += g_len
    else:
        split_items["test"].extend(group)
        for it in group:
            it["split"] = "test"

print(f"Split sizes: Train={len(split_items['train'])}, Val={len(split_items['val'])}, Test={len(split_items['test'])}")

# -------------------------------------------------------------
# STEP 4: Write Unified Dataset to F:\RoadDamage_Fresh
# -------------------------------------------------------------
print(f"\nWriting dataset images and labels to {OUTPUT_DIR}...")

pothole_img_count = 0
alligator_img_count = 0
mixed_img_count = 0
negative_img_count = 0
pothole_boxes_total = 0
alligator_boxes_total = 0

source_counts = Counter()

# QA export counters
qa_counts = {"pothole": 0, "alligator_crack": 0, "mixed": 0, "negative": 0}
MAX_QA_SAMPLES = 25

for split in ["train", "val", "test"]:
    for idx, item in enumerate(split_items[split]):
        src = item["source"]
        source_counts[src] += 1
        orig_fname = os.path.basename(item["orig_path"])
        stem, ext = os.path.splitext(orig_fname)
        final_filename = f"{src}_{split}_{idx:05d}{ext.lower()}"
        final_img_path = os.path.join(OUTPUT_DIR, "images", split, final_filename)
        final_lbl_path = os.path.join(OUTPUT_DIR, "labels", split, f"{src}_{split}_{idx:05d}.txt")
        
        # Copy image
        shutil.copy2(item["orig_path"], final_img_path)
        
        # Write labels
        boxes = item["boxes"]
        has_pothole = any(b[0] == 0 for b in boxes)
        has_alligator = any(b[0] == 1 for b in boxes)
        
        with open(final_lbl_path, "w", encoding="utf-8") as lbf:
            for b in boxes:
                cid, xc, yc, w, h = b
                lbf.write(f"{cid} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")
                if cid == 0:
                    pothole_boxes_total += 1
                elif cid == 1:
                    alligator_boxes_total += 1
                    
        # Update category counts
        if has_pothole and has_alligator:
            mixed_img_count += 1
            final_class_str = "mixed (pothole+alligator)"
        elif has_pothole:
            pothole_img_count += 1
            final_class_str = "pothole"
        elif has_alligator:
            alligator_img_count += 1
            final_class_str = "alligator_crack"
        else:
            negative_img_count += 1
            final_class_str = "negative_road"
            
        # Record image provenance
        image_provenance_rows.append([
            final_filename,
            orig_fname,
            src,
            item["orig_class"],
            final_class_str,
            item["width"],
            item["height"],
            item["format"],
            item["sha256"],
            item["phash"],
            split
        ])
        
        # Record split manifest
        split_manifest_rows.append([
            final_filename,
            split,
            src,
            has_pothole,
            has_alligator,
            len(boxes) == 0
        ])
        
        # Export QA visual samples with annotations rendered
        qa_type = None
        if has_pothole and has_alligator and qa_counts["mixed"] < MAX_QA_SAMPLES:
            qa_type = "mixed"
        elif has_pothole and not has_alligator and qa_counts["pothole"] < MAX_QA_SAMPLES:
            qa_type = "pothole"
        elif has_alligator and not has_pothole and qa_counts["alligator_crack"] < MAX_QA_SAMPLES:
            qa_type = "alligator_crack"
        elif len(boxes) == 0 and qa_counts["negative"] < MAX_QA_SAMPLES:
            qa_type = "negative"
            
        if qa_type:
            qa_counts[qa_type] += 1
            im_cv = cv2.imread(final_img_path)
            if im_cv is not None:
                ih, iw = im_cv.shape[:2]
                for b in boxes:
                    cid, xc, yc, bw, bh = b
                    x1 = int((xc - bw / 2.0) * iw)
                    y1 = int((yc - bh / 2.0) * ih)
                    x2 = int((xc + bw / 2.0) * iw)
                    y2 = int((yc + bh / 2.0) * ih)
                    color = (0, 165, 255) if cid == 0 else (255, 100, 0)
                    lbl_txt = "pothole" if cid == 0 else "alligator_crack"
                    cv2.rectangle(im_cv, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(im_cv, lbl_txt, (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                cv2.imwrite(os.path.join(OUTPUT_DIR, "qa", qa_type, f"qa_{final_filename}"), im_cv)

print("Finished writing images, labels, and QA visual samples!")

# -------------------------------------------------------------
# STEP 5: Write All Metadata CSV Files
# -------------------------------------------------------------
print("\nSaving metadata CSV files...")

# 1. source_inventory.csv
with open(os.path.join(OUTPUT_DIR, "metadata", "source_inventory.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["source_dataset", "total_raw_candidates", "valid_in_dataset", "percentage_of_dataset"])
    for ds in sorted(list(candidates.keys())):
        cnt = source_counts[ds]
        pct = (cnt / float(total_final)) * 100.0 if total_final > 0 else 0
        writer.writerow([ds, len(candidates[ds]), cnt, f"{pct:.2f}%"])

# 2. image_provenance.csv
with open(os.path.join(OUTPUT_DIR, "metadata", "image_provenance.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["final_filename", "original_filename", "source_dataset", "original_class", "final_class", "image_width", "image_height", "annotation_format", "sha256", "phash", "split"])
    writer.writerows(image_provenance_rows)

# 3. duplicate_report.csv
with open(os.path.join(OUTPUT_DIR, "metadata", "duplicate_report.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["duplicate_type", "kept_image", "duplicate_image", "kept_source", "duplicate_source", "hash_value", "distance"])
    writer.writerows(duplicate_report_rows)

# 4. invalid_labels.csv
with open(os.path.join(OUTPUT_DIR, "metadata", "invalid_labels.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["source_dataset", "image_filename", "raw_annotation", "reason"])
    writer.writerows(invalid_labels_rows)

# 5. rejected_images.csv
with open(os.path.join(OUTPUT_DIR, "metadata", "rejected_images.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["source_dataset", "image_filename", "reason"])
    writer.writerows(rejected_images_rows)

# 6. split_manifest.csv
with open(os.path.join(OUTPUT_DIR, "metadata", "split_manifest.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["final_filename", "split", "source_dataset", "has_pothole", "has_alligator_crack", "is_negative"])
    writer.writerows(split_manifest_rows)

# -------------------------------------------------------------
# STEP 6: Write data.yaml
# -------------------------------------------------------------
clean_output_dir = OUTPUT_DIR.replace("\\", "/")
data_yaml_content = f"""path: {clean_output_dir}
train: images/train
val: images/val
test: images/test

names:
  0: pothole
  1: alligator_crack
"""
with open(os.path.join(OUTPUT_DIR, "data.yaml"), "w", encoding="utf-8") as f:
    f.write(data_yaml_content)
print("Saved F:/RoadDamage_Fresh/data.yaml")

# -------------------------------------------------------------
# STEP 7: Write DATASET_REPORT.md
# -------------------------------------------------------------
report_md = f"""# FRESH UNIFIED ROAD DAMAGE DATASET (RoadDamage_Fresh) REPORT

## Executive Summary
This report documents the creation of the completely fresh, unified two-class road damage dataset for YOLO11 training, built from **all 8 fresh source datasets** located at `F:\\POTHOLEDATASET\\`.

### Final Target Classes:
- Class `0`: **`pothole`**
- Class `1`: **`alligator_crack`**

---

## 1. Source Inventory & Contribution Breakdown

| Source Dataset | Raw Candidates | Valid Unified Images | Dataset Share | Primary Role |
| :--- | :--- | :--- | :--- | :--- |
| **BharatPotHole** | {len(candidates['BharatPotHole'])} | {source_counts['BharatPotHole']} | {(source_counts['BharatPotHole']/float(total_final))*100:.2f}% | Dashcam Potholes & True Negatives |
| **BiankatpasDataset** | {len(candidates['BiankatpasDataset'])} | {source_counts['BiankatpasDataset']} | {(source_counts['BiankatpasDataset']/float(total_final))*100:.2f}% | High-Res Mask Potholes |
| **IndianRoadsDataset** | {len(candidates['IndianRoadsDataset'])} | {source_counts['IndianRoadsDataset']} | {(source_counts['IndianRoadsDataset']/float(total_final))*100:.2f}% | Indian Road Potholes & Bump Negatives |
| **Pothole600** | {len(candidates['Pothole600'])} | {source_counts['Pothole600']} | {(source_counts['Pothole600']/float(total_final))*100:.2f}% | Stereo Benchmark Potholes |
| **RDD2022Dataset** | {len(candidates['RDD2022Dataset'])} | {source_counts['RDD2022Dataset']} | {(source_counts['RDD2022Dataset']/float(total_final))*100:.2f}% | Core Global & Indian Pothole + Alligator Cracks |
| **RoboflowIIT** | {len(candidates['RoboflowIIT'])} | {source_counts['RoboflowIIT']} | {(source_counts['RoboflowIIT']/float(total_final))*100:.2f}% | IIT Madras Potholes & Crocodile Cracks |
| **SPDataset** | {len(candidates['SPDataset'])} | {source_counts['SPDataset']} | {(source_counts['SPDataset']/float(total_final))*100:.2f}% | Deduplicated Subset of Urban Civic |
| **Urban Civic** | {len(candidates['Urban Civic'])} | {source_counts['Urban Civic']} | {(source_counts['Urban Civic']/float(total_final))*100:.2f}% | Pune Plain Road Negative Backgrounds |

---

## 2. Dataset Statistics

- **Total Final Images**: **{total_final}**
- **Train Set (70%)**: **{len(split_items['train'])}**
- **Validation Set (15%)**: **{len(split_items['val'])}**
- **Test Set (15%)**: **{len(split_items['test'])}**

### Class-Specific Distribution:
- **Pothole Images**: **{pothole_img_count}**
- **Pothole Bounding Boxes**: **{pothole_boxes_total}**
- **Alligator Crack Images**: **{alligator_img_count}**
- **Alligator Crack Bounding Boxes**: **{alligator_boxes_total}**
- **Mixed Images (Pothole + Alligator)**: **{mixed_img_count}**
- **Negative Road Images (Empty TXT)**: **{negative_img_count}**

### Data Cleaning & Deduplication:
- **Exact SHA-256 Duplicates Removed**: **{duplicate_count}**
- **Near-Duplicate pHash Images Removed**: **{near_duplicate_count}**
- **Invalid Labels Logged**: **{len(invalid_labels_rows)}**
- **Rejected / Unannotated Images Logged**: **{len(rejected_images_rows)}**

---

## 3. Directory Layout & Integrity
```
F:\\RoadDamage_Fresh\\
├── images/
│   ├── train/ ({len(split_items['train'])} files)
│   ├── val/ ({len(split_items['val'])} files)
│   └── test/ ({len(split_items['test'])} files)
├── labels/
│   ├── train/ ({len(split_items['train'])} files)
│   ├── val/ ({len(split_items['val'])} files)
│   └── test/ ({len(split_items['test'])} files)
├── metadata/
│   ├── source_inventory.csv
│   ├── class_mapping.csv
│   ├── image_provenance.csv
│   ├── duplicate_report.csv
│   ├── invalid_labels.csv
│   ├── rejected_images.csv
│   └── split_manifest.csv
├── qa/
│   ├── pothole/ ({qa_counts['pothole']} samples)
│   ├── alligator_crack/ ({qa_counts['alligator_crack']} samples)
│   ├── negative/ ({qa_counts['negative']} samples)
│   └── mixed/ ({qa_counts['mixed']} samples)
└── data.yaml
```
"""

with open(os.path.join(OUTPUT_DIR, "DATASET_REPORT.md"), "w", encoding="utf-8") as f:
    f.write(report_md)
print("Saved F:/RoadDamage_Fresh/DATASET_REPORT.md")

print("\n================ FRESH DATASET SUMMARY ================")
print(f"BharatPotHole: {source_counts['BharatPotHole']}")
print(f"BiankatpasDataset: {source_counts['BiankatpasDataset']}")
print(f"IndianRoadsDataset: {source_counts['IndianRoadsDataset']}")
print(f"Pothole600: {source_counts['Pothole600']}")
print(f"RDD2022Dataset: {source_counts['RDD2022Dataset']}")
print(f"RoboflowIIT: {source_counts['RoboflowIIT']}")
print(f"SPDataset: {source_counts['SPDataset']}")
print(f"Urban Civic: {source_counts['Urban Civic']}")
print("-------------------------------------------------------")
print(f"TOTAL CANDIDATES: {sum(len(v) for v in candidates.values())}")
print(f"TOTAL FINAL UNIQUE: {total_final}")
print(f"TRAIN: {len(split_items['train'])}")
print(f"VAL: {len(split_items['val'])}")
print(f"TEST: {len(split_items['test'])}")
print("-------------------------------------------------------")
print(f"POTHOLE IMAGES: {pothole_img_count}")
print(f"POTHOLE BOXES: {pothole_boxes_total}")
print(f"ALLIGATOR CRACK IMAGES: {alligator_img_count}")
print(f"ALLIGATOR CRACK BOXES: {alligator_boxes_total}")
print(f"MIXED IMAGES: {mixed_img_count}")
print(f"NEGATIVE IMAGES: {negative_img_count}")
print("-------------------------------------------------------")
print(f"DUPLICATES REMOVED: {duplicate_count + near_duplicate_count}")
print(f"INVALID LABELS: {len(invalid_labels_rows)}")
print(f"REJECTED IMAGES: {len(rejected_images_rows)}")
print("=======================================================\n")

import os
import shutil
import hashlib
import random
from pathlib import Path
from PIL import Image
import imagehash
import pandas as pd
from tqdm import tqdm
from collections import defaultdict

from config import (
    CONVERTED_DIR, IMAGES_DIR, LABELS_DIR, METADATA_DIR,
    TRAIN_RATIO, VAL_RATIO, TEST_RATIO, PHASH_HAMMING_THRESHOLD
)

DUPLICATE_REPORT_CSV = METADATA_DIR / "duplicate_report.csv"
SPLIT_MANIFEST_CSV = METADATA_DIR / "split_manifest.csv"

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def compute_phash(filepath: Path) -> imagehash.ImageHash:
    with Image.open(filepath) as im:
        return imagehash.phash(im)

def run_dedup_and_split():
    print("=== STEP 3: DEDUPLICATION & LEAKAGE-FREE GROUP SPLIT ===")

    manifest_path = CONVERTED_DIR / "converted_manifest.csv"
    if not manifest_path.exists():
        print(f"[ERROR] Converted manifest not found at {manifest_path}")
        return

    df = pd.read_csv(manifest_path)
    print(f"Loaded {len(df)} converted image candidates.")

    # 1. Exact and Perceptual Deduplication
    seen_sha = {}
    seen_phash = {}  # phash -> target_filename
    duplicate_records = []
    unique_records = []

    print("[DEDUP] Computing exact SHA-256 and perceptual pHash...")
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Deduplicating"):
        orig_img_path = Path(row["orig_img_path"])
        target_fn = row["target_filename"]

        if not orig_img_path.exists():
            continue

        try:
            sha = compute_sha256(orig_img_path)
            ph = compute_phash(orig_img_path)
        except Exception as e:
            continue

        # Check exact duplicate
        if sha in seen_sha:
            prev_fn = seen_sha[sha]
            duplicate_records.append({
                "image_a": prev_fn,
                "image_b": target_fn,
                "hash": sha,
                "similarity": "1.0_exact_sha256",
                "action": "dropped_exact_duplicate",
                "source": row["source_dataset"]
            })
            continue

        # Check perceptual near-duplicate
        is_near_dup = False
        # To optimize lookup, compare against phashes
        for existing_ph, existing_fn in seen_phash.items():
            dist = ph - existing_ph
            if dist <= PHASH_HAMMING_THRESHOLD:
                # Compare similarity
                similarity = 1.0 - (dist / 64.0)
                duplicate_records.append({
                    "image_a": existing_fn,
                    "image_b": target_fn,
                    "hash": str(ph),
                    "similarity": f"{similarity:.3f}_phash_dist_{dist}",
                    "action": "dropped_near_duplicate",
                    "source": row["source_dataset"]
                })
                is_near_dup = True
                break

        if is_near_dup:
            continue

        seen_sha[sha] = target_fn
        seen_phash[ph] = target_fn

        row_dict = row.to_dict()
        row_dict["sha256"] = sha
        row_dict["phash"] = str(ph)
        unique_records.append(row_dict)

    df_dup = pd.DataFrame(duplicate_records)
    df_dup.to_csv(DUPLICATE_REPORT_CSV, index=False)
    print(f"[DEDUP] Removed {len(df_dup)} duplicate/near-duplicate images -> {DUPLICATE_REPORT_CSV}")

    df_unique = pd.DataFrame(unique_records)
    print(f"[DEDUP] Remaining unique images: {len(df_unique)}")

    # 2. Sequence Group Split (Preventing Video Frame Leakage)
    # Group images by sequence_group
    groups = defaultdict(list)
    for _, row in df_unique.iterrows():
        groups[row["sequence_group"]].append(row)

    group_keys = list(groups.keys())
    # Deterministic shuffle with fixed random seed
    random.seed(42)
    random.shuffle(group_keys)

    total_images = len(df_unique)
    target_train_count = int(total_images * TRAIN_RATIO)
    target_val_count = int(total_images * VAL_RATIO)

    train_rows = []
    val_rows = []
    test_rows = []

    curr_train = 0
    curr_val = 0

    for gkey in group_keys:
        grows = groups[gkey]
        glen = len(grows)
        if curr_train + glen <= target_train_count:
            for r in grows:
                r["split"] = "train"
                train_rows.append(r)
            curr_train += glen
        elif curr_val + glen <= target_val_count:
            for r in grows:
                r["split"] = "val"
                val_rows.append(r)
            curr_val += glen
        else:
            for r in grows:
                r["split"] = "test"
                test_rows.append(r)

    all_split_rows = train_rows + val_rows + test_rows
    print(f"[SPLIT] Train: {len(train_rows)}, Val: {len(val_rows)}, Test: {len(test_rows)}")

    # 3. Copy files to final YOLO structure
    split_manifest_records = []
    for r in tqdm(all_split_rows, desc="Copying images & labels to final splits"):
        split = r["split"]
        target_fn = r["target_filename"]
        orig_img_path = Path(r["orig_img_path"])
        target_lbl_path = Path(r["target_lbl_path"])

        final_img_path = IMAGES_DIR / split / target_fn
        final_lbl_path = LABELS_DIR / split / f"{Path(target_fn).stem}.txt"

        final_img_path.parent.mkdir(parents=True, exist_ok=True)
        final_lbl_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(orig_img_path, final_img_path)
        if target_lbl_path.exists():
            shutil.copy2(target_lbl_path, final_lbl_path)
        else:
            # Empty label file for background image
            final_lbl_path.touch()

        split_manifest_records.append({
            "image_name": target_fn,
            "split": split,
            "class_present": r["final_class"],
            "source": r["source_dataset"],
            "source_group": r["sequence_group"]
        })

    df_split = pd.DataFrame(split_manifest_records)
    df_split.to_csv(SPLIT_MANIFEST_CSV, index=False)
    print(f"[SPLIT] Saved split manifest -> {SPLIT_MANIFEST_CSV}")

    # Save unique records with split info for provenance
    df_final_all = pd.DataFrame(all_split_rows)
    df_final_all.to_csv(CONVERTED_DIR / "final_split_records.csv", index=False)
    print("[SUCCESS] Group split and file copy complete.")

if __name__ == "__main__":
    run_dedup_and_split()

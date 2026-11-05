"""
Builds a sanitized, unified, single-class dataset for real-world road deployment (Kolhapur).

Exclusions (Toxic noise):
  * BharatPotHole: 6-15px random boxes on flat asphalt (drags precision down to 22%).
  * RDD Norway: 38% sub-pixel boxes under 0.1% of image (drags mAP to 32%).
  * RDD Czech: extremely noisy labels (39% mAP).
  * IndianRoadsDataset: burned-in bounding boxes and water reflection false labels (32% mAP).
  * Corrupted files: Japan_010815, pa3558, pa3357, pa2193.

Inclusions (Clean, high-quality road damage):
  * Kolhapur (morning train + afternoon test) - oversampled 4x so local target domain is dominant!
  * Pothole600 (clean, 96% mAP)
  * Biankatpas (clean, 88% mAP)
  * RDD China (Motorbike & Drone, clean, 95% mAP)
  * RDD Japan & United States (clean, 74-78% mAP)
  * UrbanCivic & SPDataset
  * RoboflowIIT (with unified single-class)

Class Unification:
  * All labels unified to class 0: 'pothole' (road damage). Eliminates all crack vs pothole confusion.
"""

import os
import shutil
import csv
from pathlib import Path

ROOT = Path("F:/POTHOLE_PROJECT")
SRC_DIR = ROOT / "dataset_verified"
OUT_DIR = ROOT / "dataset_clean"

TOXIC_DATASETS = {"BharatPotHole", "IndianRoadsDataset"}
TOXIC_FILE_PREFIXES = ("Norway_", "Czech_")
CORRUPT_FILES = {
    "Japan_010815", "pa3558_jpg", "pa3357_jpg", "pa2193_jpg", "Japan_001119"
}

def is_toxic(dataset_name, file_name):
    for td in TOXIC_DATASETS:
        if dataset_name.startswith(td):
            return True
    for tp in TOXIC_FILE_PREFIXES:
        if file_name.startswith(tp):
            return True
    for cf in CORRUPT_FILES:
        if cf in file_name:
            return True
    return False

def main():
    print(f"Reading manifest from {SRC_DIR / 'manifest.csv'}...")
    with open(SRC_DIR / "manifest.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    
    print(f"Total rows in manifest: {len(rows)}")
    
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
        
    (OUT_DIR / "images" / "train").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "images" / "val").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "images" / "test").mkdir(parents=True, exist_ok=True)
    
    (OUT_DIR / "labels" / "train").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "labels" / "val").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "labels" / "test").mkdir(parents=True, exist_ok=True)
    
    stats = {"train": 0, "val": 0, "test": 0, "excluded": 0, "kolhapur_train": 0}
    
    for r in rows:
        split, ds, fname, status = r["split"], r["dataset"], r["file"], r["status"]
        if is_toxic(ds, fname):
            stats["excluded"] += 1
            continue
            
        src_img = SRC_DIR / "images" / split / ds / fname
        src_lbl = SRC_DIR / "labels" / split / ds / f"{Path(fname).stem}.txt"
        
        if not src_img.exists() or not src_lbl.exists():
            continue
            
        # Read and unify labels to class 0
        lbl_lines = []
        try:
            raw_lines = src_lbl.read_text(encoding="utf-8", errors="ignore").splitlines()
            for l in raw_lines:
                v = l.strip().split()
                if len(v) >= 5:
                    w, h = float(v[3]), float(v[4])
                    if w < 0.008 and h < 0.008: # skip sub-pixel noise (< 5 px)
                        continue
                    # Force class 0 (single unified damage class)
                    lbl_lines.append(f"0 {v[1]} {v[2]} {v[3]} {v[4]}")
        except Exception as e:
            continue
            
        # Determine multiplier: oversample Kolhapur in train by 4x
        multiplier = 4 if (split == "train" and "kolhapur" in ds) else 1
        if multiplier > 1:
            stats["kolhapur_train"] += 1
            
        for m in range(multiplier):
            suffix = f"_krep{m}" if m > 0 else ""
            target_stem = f"{ds}_{Path(fname).stem}{suffix}"
            dst_img = OUT_DIR / "images" / split / f"{target_stem}{Path(fname).suffix}"
            dst_lbl = OUT_DIR / "labels" / split / f"{target_stem}.txt"
            
            # Hard link image
            try:
                os.link(src_img, dst_img)
            except Exception:
                shutil.copy2(src_img, dst_img)
                
            dst_lbl.write_text("\n".join(lbl_lines) + "\n" if lbl_lines else "", encoding="utf-8")
            stats[split] += 1

    print("\nDataset generation completed successfully!")
    print(f"  Train images:     {stats['train']} (includes {stats['kolhapur_train'] * 4} Kolhapur frames)")
    print(f"  Val images:       {stats['val']}")
    print(f"  Test images:      {stats['test']}")
    print(f"  Excluded toxic:   {stats['excluded']}")
    
    # Write data_clean.yaml
    yaml_content = f"""path: {OUT_DIR.as_posix()}
train: images/train
val: images/val
test: images/test

nc: 1
names: ['pothole']
"""
    (OUT_DIR / "data.yaml").write_text(yaml_content, encoding="utf-8")
    print(f"Wrote {OUT_DIR / 'data.yaml'}")

if __name__ == "__main__":
    main()


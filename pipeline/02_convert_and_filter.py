import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import pandas as pd
from tqdm import tqdm

from config import (
    RAW_DIR, CONVERTED_DIR, METADATA_DIR, RAW_CLASS_MAPPING,
    CLASS_NAMES
)

BROKEN_IMAGES_CSV = METADATA_DIR / "broken_images.csv"
INVALID_LABELS_CSV = METADATA_DIR / "invalid_labels.csv"
CLASS_MAPPING_CSV = METADATA_DIR / "class_mapping.csv"

def save_class_mapping_csv():
    records = []
    for raw_name, (mapped_name, cid) in RAW_CLASS_MAPPING.items():
        records.append({
            "source_class_raw": raw_name,
            "mapped_class_name": mapped_name,
            "final_class_id": cid,
            "status": "retained" if cid >= 0 else "discarded"
        })
    df = pd.DataFrame(records)
    CLASS_MAPPING_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLASS_MAPPING_CSV, index=False)
    print(f"[METADATA] Saved class mapping table -> {CLASS_MAPPING_CSV}")

def parse_voc_xml(xml_path: Path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        return None, None, [], f"XML Parse Error: {e}"

    size_elem = root.find("size")
    if size_elem is not None:
        try:
            width = float(size_elem.findtext("width", "0"))
            height = float(size_elem.findtext("height", "0"))
        except ValueError:
            width, height = 0, 0
    else:
        width, height = 0, 0

    boxes = []
    errors = []

    for obj in root.findall("object"):
        raw_name = obj.findtext("name", "").strip()
        bndbox = obj.find("bndbox")
        if bndbox is None:
            continue
        try:
            xmin = float(bndbox.findtext("xmin"))
            ymin = float(bndbox.findtext("ymin"))
            xmax = float(bndbox.findtext("xmax"))
            ymax = float(bndbox.findtext("ymax"))
        except (ValueError, TypeError):
            errors.append(f"Invalid coordinate format in {raw_name}")
            continue

        boxes.append({
            "raw_name": raw_name,
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax
        })

    return width, height, boxes, errors

def process_rdd_country(country_dir: Path, country_name: str, source_name: str, source_url: str, license_str: str, max_negatives: int = 700):
    images_dir = country_dir / "images"
    xmls_dir = country_dir / "annotations" / "xmls"

    if not images_dir.exists():
        return [], [], []

    img_files = sorted(list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png")))
    converted_records = []
    broken_records = []
    invalid_label_records = []

    out_img_dir = CONVERTED_DIR / "images"
    out_lbl_dir = CONVERTED_DIR / "labels"
    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)

    print(f"[PROCESSING] {source_name} - {country_name}: {len(img_files)} images found...")
    negative_count = 0

    for img_path in tqdm(img_files, desc=f"Converting {country_name}"):
        orig_filename = img_path.name
        stem = img_path.stem
        xml_path = xmls_dir / f"{stem}.xml"

        # Verify image readability and actual dimensions
        try:
            with Image.open(img_path) as im:
                im_w, im_h = im.size
                im.verify()
        except Exception as e:
            broken_records.append({
                "image_path": str(img_path),
                "error": str(e),
                "source": source_name,
                "country": country_name
            })
            continue

        # Extract sequence ID from filename (e.g. India_001234 -> prefix India_001)
        parts = stem.split("_")
        if len(parts) >= 2 and parts[-1].isdigit():
            num = int(parts[-1])
            seq_group = f"{parts[0]}_{num // 100:04d}"
        else:
            seq_group = f"{country_name}_seq0"

        # Parse labels
        yolo_lines = []
        pothole_count = 0
        alligator_count = 0
        original_classes = []

        if xml_path.exists():
            xml_w, xml_h, raw_boxes, parse_errs = parse_voc_xml(xml_path)
            for err in parse_errs:
                invalid_label_records.append({
                    "image": orig_filename,
                    "label_file": xml_path.name,
                    "error_type": "parse_error",
                    "details": err,
                    "action": "skipped_box"
                })

            w_scale = im_w if im_w > 0 else xml_w
            h_scale = im_h if im_h > 0 else xml_h

            for box in raw_boxes:
                raw_cls = box["raw_name"]
                original_classes.append(raw_cls)
                mapping = RAW_CLASS_MAPPING.get(raw_cls, (raw_cls, -1))
                mapped_name, class_id = mapping

                # Discard non-target classes (D00, D10, repairs, etc.)
                if class_id not in (0, 1):
                    continue

                xmin = max(0.0, box["xmin"])
                ymin = max(0.0, box["ymin"])
                xmax = min(w_scale, box["xmax"])
                ymax = min(h_scale, box["ymax"])

                bw = xmax - xmin
                bh = ymax - ymin

                # Validation checks
                if bw <= 3 or bh <= 3:
                    invalid_label_records.append({
                        "image": orig_filename,
                        "label_file": xml_path.name,
                        "error_type": "degenerate_box",
                        "details": f"box {bw}x{bh} pixels too small",
                        "action": "filtered"
                    })
                    continue

                if bw >= 0.99 * w_scale and bh >= 0.99 * h_scale:
                    invalid_label_records.append({
                        "image": orig_filename,
                        "label_file": xml_path.name,
                        "error_type": "oversized_box",
                        "details": f"box covers >98% of image ({bw}x{bh})",
                        "action": "filtered"
                    })
                    continue

                # Normalized YOLO format: class x_center y_center width height
                x_center = (xmin + xmax) / 2.0 / w_scale
                y_center = (ymin + ymax) / 2.0 / h_scale
                norm_w = bw / w_scale
                norm_h = bh / h_scale

                # Boundary check
                if not (0.0 <= x_center <= 1.0 and 0.0 <= y_center <= 1.0 and 0.0 < norm_w <= 1.0 and 0.0 < norm_h <= 1.0):
                    invalid_label_records.append({
                        "image": orig_filename,
                        "label_file": xml_path.name,
                        "error_type": "out_of_bounds",
                        "details": f"norm coords ({x_center:.3f}, {y_center:.3f}, {norm_w:.3f}, {norm_h:.3f})",
                        "action": "filtered"
                    })
                    continue

                yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {norm_w:.6f} {norm_h:.6f}")
                if class_id == 0:
                    pothole_count += 1
                elif class_id == 1:
                    alligator_count += 1

        # Class presence status
        if pothole_count > 0 and alligator_count > 0:
            final_class_label = "both"
        elif pothole_count > 0:
            final_class_label = "pothole"
        elif alligator_count > 0:
            final_class_label = "alligator_crack"
        else:
            final_class_label = "negative_background"
            # Cap background images per country to avoid overwhelming the detector
            if negative_count >= max_negatives:
                continue
            negative_count += 1

        # Unique target filename
        target_filename = f"{source_name}_{country_name}_{orig_filename}"
        target_lbl_path = out_lbl_dir / f"{Path(target_filename).stem}.txt"

        # Write converted label
        with open(target_lbl_path, "w", encoding="utf-8") as lf:
            if yolo_lines:
                lf.write("\n".join(yolo_lines) + "\n")

        converted_records.append({
            "target_filename": target_filename,
            "orig_img_path": str(img_path),
            "target_lbl_path": str(target_lbl_path),
            "source_dataset": source_name,
            "source_url": source_url,
            "source_country": country_name,
            "license": license_str,
            "original_filename": orig_filename,
            "original_classes": ";".join(set(original_classes)) if original_classes else "none",
            "final_class": final_class_label,
            "pothole_boxes": pothole_count,
            "alligator_boxes": alligator_count,
            "image_width": im_w,
            "image_height": im_h,
            "sequence_group": seq_group
        })

    return converted_records, broken_records, invalid_label_records

def process_pothole600():
    pothole600_root = RAW_DIR / "other_sources" / "Pothole600" / "pothole600"
    if not pothole600_root.exists():
        return [], [], []

    print("[PROCESSING] Pothole600 dataset...")
    out_img_dir = CONVERTED_DIR / "images"
    out_lbl_dir = CONVERTED_DIR / "labels"
    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)

    converted_records = []
    broken_records = []
    invalid_label_records = []

    for split in ["training", "validation", "testing"]:
        rgb_dir = pothole600_root / split / "rgb"
        lbl_dir = pothole600_root / split / "label"
        if not rgb_dir.exists():
            continue

        for img_path in rgb_dir.glob("*.png"):
            stem = img_path.stem
            mask_path = lbl_dir / f"{stem}.png"
            if not mask_path.exists():
                continue

            try:
                im = Image.open(img_path)
                im_w, im_h = im.size
                im.verify()
            except Exception as e:
                broken_records.append({
                    "image_path": str(img_path),
                    "error": str(e),
                    "source": "Pothole600",
                    "country": "India/Mixed"
                })
                continue

            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            if mask is None:
                continue

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            yolo_lines = []
            pothole_count = 0

            for c in contours:
                x, y, bw, bh = cv2.boundingRect(c)
                if bw >= 5 and bh >= 5:
                    xc = (x + bw / 2.0) / im_w
                    yc = (y + bh / 2.0) / im_h
                    nw = bw / float(im_w)
                    nh = bh / float(im_h)
                    yolo_lines.append(f"0 {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}")
                    pothole_count += 1

            if pothole_count > 0:
                final_class = "pothole"
            else:
                final_class = "negative_background"

            target_filename = f"Pothole600_{split}_{img_path.name}"
            target_lbl_path = out_lbl_dir / f"{Path(target_filename).stem}.txt"

            with open(target_lbl_path, "w", encoding="utf-8") as lf:
                if yolo_lines:
                    lf.write("\n".join(yolo_lines) + "\n")

            seq_group = f"pothole600_{split}"
            converted_records.append({
                "target_filename": target_filename,
                "orig_img_path": str(img_path),
                "target_lbl_path": str(target_lbl_path),
                "source_dataset": "Pothole600",
                "source_url": "Academic/Research Road Pothole Benchmark",
                "source_country": "India/Roads",
                "license": "Research Use Only",
                "original_filename": img_path.name,
                "original_classes": "pothole",
                "final_class": final_class,
                "pothole_boxes": pothole_count,
                "alligator_boxes": 0,
                "image_width": im_w,
                "image_height": im_h,
                "sequence_group": seq_group
            })

    print(f"[SUCCESS] Converted {len(converted_records)} Pothole600 images.")
    return converted_records, broken_records, invalid_label_records

def run_conversion():
    print("=== STEP 2: CONVERSION, NORMALIZATION & QC CHECKS ===")
    save_class_mapping_csv()

    all_converted = []
    all_broken = []
    all_invalid = []

    # 1. Process RDD2020 sources (India, Japan, Czech)
    rdd2020_root = RAW_DIR / "RDD2020" / "train"
    if not rdd2020_root.exists():
        alt = list(RAW_DIR.glob("**/RDD2020/**/India"))
        if alt:
            rdd2020_root = alt[0].parent
        else:
            alt2 = list(RAW_DIR.glob("**/train/India"))
            if alt2:
                rdd2020_root = alt2[0].parent

    if rdd2020_root.exists():
        # Retain up to 800 difficult negatives from India, 500 from Japan, 300 from Czech
        limits = {"India": 800, "Japan": 500, "Czech": 300}
        for country in ["India", "Japan", "Czech"]:
            cdir = rdd2020_root / country
            if cdir.exists():
                c_recs, b_recs, inv_recs = process_rdd_country(
                    country_dir=cdir,
                    country_name=country,
                    source_name="RDD2020",
                    source_url="https://doi.org/10.17632/5ty2wb6gvg.1",
                    license_str="CC BY 4.0",
                    max_negatives=limits.get(country, 500)
                )
                all_converted.extend(c_recs)
                all_broken.extend(b_recs)
                all_invalid.extend(inv_recs)

    # 2. Process Pothole600
    p600_conv, p600_brk, p600_inv = process_pothole600()
    all_converted.extend(p600_conv)
    all_broken.extend(p600_brk)
    all_invalid.extend(p600_inv)

    # Save broken images
    if all_broken:
        df_broken = pd.DataFrame(all_broken)
        df_broken.to_csv(BROKEN_IMAGES_CSV, index=False)
        print(f"[QC] Logged {len(df_broken)} broken images -> {BROKEN_IMAGES_CSV}")
    else:
        pd.DataFrame(columns=["image_path", "error", "source", "country"]).to_csv(BROKEN_IMAGES_CSV, index=False)

    # Save invalid labels
    if all_invalid:
        df_inv = pd.DataFrame(all_invalid)
        df_inv.to_csv(INVALID_LABELS_CSV, index=False)
        print(f"[QC] Logged {len(df_inv)} invalid/filtered labels -> {INVALID_LABELS_CSV}")
    else:
        pd.DataFrame(columns=["image", "label_file", "error_type", "details", "action"]).to_csv(INVALID_LABELS_CSV, index=False)

    df_conv = pd.DataFrame(all_converted)
    intermediate_csv = CONVERTED_DIR / "converted_manifest.csv"
    df_conv.to_csv(intermediate_csv, index=False)
    print(f"\n[SUCCESS] Total dataset pool prepared: {len(df_conv)} images.")
    if not df_conv.empty:
        print("\nClass breakdown:")
        print(df_conv["final_class"].value_counts())
        print("\nCountry / Region breakdown:")
        print(df_conv["source_country"].value_counts())
        print("\nTotal Damage Boxes:")
        print(f"Pothole boxes: {df_conv['pothole_boxes'].sum()}")
        print(f"Alligator crack boxes: {df_conv['alligator_boxes'].sum()}")

if __name__ == "__main__":
    run_conversion()

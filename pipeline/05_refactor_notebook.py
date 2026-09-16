import json
from pathlib import Path

def create_notebook():
    nb = {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": {
            "colab": {
                "provenance": []
            },
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3"
            },
            "language_info": {
                "name": "python"
            },
            "accelerator": "GPU"
        },
        "cells": []
    }

    def add_md(text):
        nb["cells"].append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in text.strip().split("\n")]
        })

    def add_code(code):
        nb["cells"].append({
            "cell_type": "code",
            "metadata": {},
            "execution_count": None,
            "outputs": [],
            "source": [line + "\n" for line in code.strip().split("\n")]
        })

    # Header
    add_md("""# Computer Vision & Deep Learning Based Road Damage and Municipal Reporting System
## YOLO11 Two-Class Baseline Training & Evaluation Pipeline
**Target Classes:**
- Class `0`: `pothole`
- Class `1`: `alligator_crack`

This notebook provides a complete, robust, and reproducible training, validation, testing, and inference pipeline using Ultralytics YOLO11 on the curated Indian road damage dataset (`RoadDamage20K`).""")

    # SECTION 1: Environment Check
    add_md("### SECTION 1: Environment & Hardware Verification\nVerify Python runtime, PyTorch installation, CUDA availability, and active GPU device.")
    add_code("""import sys
import torch

print(f"Python Version: {sys.version}")
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"Active GPU: {torch.cuda.get_device_name(0)}")
    print(f"Device Count: {torch.cuda.device_count()}")
    print(f"Current Device ID: {torch.cuda.current_device()}")
else:
    print("WARNING: CUDA is not available. Execution will fall back to CPU.")""")

    # SECTION 2: Install Dependencies
    add_md("### SECTION 2: Dependencies Installation\nEnsure all required packages for YOLO11 training, data processing, and visualization are installed.")
    add_code("""!pip install -q ultralytics opencv-python pandas numpy Pillow matplotlib pyyaml imagehash tqdm

from ultralytics import YOLO
import cv2
import pandas as pd
import numpy as np
import yaml
from PIL import Image
import matplotlib.pyplot as plt
from pathlib import Path
import zipfile

print("Ultralytics YOLO and all required dependencies imported successfully!")""")

    # SECTION 3: Dataset Path Verification
    add_md("### SECTION 3: Dataset Path & Structure Verification\nUnpack dataset archive if needed, verify directory layout of `RoadDamage20K`, inspect `data.yaml`, and confirm folder integrity.")
    add_code("""# Optional: mount Google Drive if running in Colab and dataset is in Drive
try:
    from google.colab import drive
    if not Path("/content/drive").exists():
        drive.mount('/content/drive')
except Exception:
    pass

# Unpack RoadDamage20K.zip if present
if not Path("dataset/RoadDamage20K").exists() and not Path("/content/dataset/RoadDamage20K").exists():
    for zip_candidate in [Path("/content/RoadDamage20K.zip"), Path("/content/drive/MyDrive/RoadDamage20K.zip"), Path("RoadDamage20K.zip")]:
        if zip_candidate.exists():
            print(f"Unpacking {zip_candidate}...")
            target_extract = Path("/content") if Path("/content").exists() else Path()
            with zipfile.ZipFile(zip_candidate, "r") as zf:
                zf.extractall(target_extract)
            print("Unpacked RoadDamage20K.zip successfully!")
            break

# Set the dataset root path (supports Colab /content and local environments)
dataset_root = Path("/content/dataset/RoadDamage20K")
if not dataset_root.exists():
    dataset_root = Path("dataset/RoadDamage20K")

print(f"Dataset root: {dataset_root.resolve()}")
assert dataset_root.exists(), f"Dataset root not found at {dataset_root}"

# Check images and labels directories
for split in ["train", "val", "test"]:
    img_dir = dataset_root / "images" / split
    lbl_dir = dataset_root / "labels" / split
    print(f"[{split.upper()}] Images: {img_dir.exists()} | Labels: {lbl_dir.exists()}")
    assert img_dir.exists(), f"Missing {img_dir}"
    assert lbl_dir.exists(), f"Missing {lbl_dir}"

# Check and adapt data.yaml
yaml_path = dataset_root / "data.yaml"
assert yaml_path.exists(), f"Missing data.yaml at {yaml_path}"
with open(yaml_path, "r", encoding="utf-8") as f:
    yaml_config = yaml.safe_load(f)

# Auto-adapt path for local environment if not running in Google Colab /content
if not Path("/content").exists():
    yaml_config["path"] = str(dataset_root.resolve()).replace("\\\\", "/")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_config, f, default_flow_style=False)
    print("Adjusted data.yaml path for local environment.")

print("\\n--- Current data.yaml configuration ---")
print(yaml.dump(yaml_config, default_flow_style=False))
assert len(yaml_config.get("names", {})) == 2, "ERROR: data.yaml must define exactly 2 classes!"
assert yaml_config["names"][0] == "pothole", "ERROR: Class 0 must be pothole!"
assert yaml_config["names"][1] == "alligator_crack", "ERROR: Class 1 must be alligator_crack!"
""")

    # SECTION 4: Dataset Statistics
    add_md("### SECTION 4: Dataset Integrity & Class Distribution Statistics\nInspect split counts and quantify bounding-box annotations across `pothole` (0) and `alligator_crack` (1).")
    add_code("""class_names = {0: "pothole", 1: "alligator_crack"}
stats = []

for split in ["train", "val", "test"]:
    img_files = list((dataset_root / "images" / split).glob("*.*"))
    lbl_files = list((dataset_root / "labels" / split).glob("*.txt"))
    
    pothole_boxes = 0
    alligator_boxes = 0
    
    for lf in lbl_files:
        with open(lf, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    cid = int(parts[0])
                    if cid == 0:
                        pothole_boxes += 1
                    elif cid == 1:
                        alligator_boxes += 1
                        
    stats.append({
        "Split": split,
        "Images": len(img_files),
        "Label Files": len(lbl_files),
        "Pothole Boxes": pothole_boxes,
        "Alligator Crack Boxes": alligator_boxes,
        "Total Boxes": pothole_boxes + alligator_boxes
    })

stats_df = pd.DataFrame(stats)
print(stats_df.to_string(index=False))""")

    # SECTION 5: Visualize Dataset Examples
    add_md("### SECTION 5: Visual Inspection of Labeled Ground-Truth Samples\nRender sample training images with ground-truth bounding boxes for both `pothole` and `alligator_crack`.")
    add_code("""import random

train_images = list((dataset_root / "images" / "train").glob("*.*"))
sample_images = random.sample(train_images, min(6, len(train_images)))

fig, axes = plt.subplots(2, 3, figsize=(16, 10))
axes = axes.flatten()

for idx, img_p in enumerate(sample_images):
    im = cv2.imread(str(img_p))
    im_rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    h, w, _ = im.shape
    
    lbl_p = dataset_root / "labels" / "train" / f"{img_p.stem}.txt"
    if lbl_p.exists():
        with open(lbl_p, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    cid = int(parts[0])
                    xc, yc, bw, bh = map(float, parts[1:5])
                    x1 = int((xc - bw/2) * w)
                    y1 = int((yc - bh/2) * h)
                    x2 = int((xc + bw/2) * w)
                    y2 = int((yc + bh/2) * h)
                    
                    color = (255, 140, 0) if cid == 0 else (0, 150, 255)
                    label = class_names.get(cid, str(cid))
                    cv2.rectangle(im_rgb, (x1, y1), (x2, y2), color, 3)
                    cv2.putText(im_rgb, label, (x1, max(20, y1-8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    
    axes[idx].imshow(im_rgb)
    axes[idx].set_title(img_p.name, fontsize=10)
    axes[idx].axis("off")

plt.tight_layout()
plt.show()""")

    # SECTION 6: Load YOLO11
    add_md("### SECTION 6: Initialize YOLO11 Baseline Architecture\nLoad the pretrained YOLO11 Nano (`yolo11n.pt`) backbone.")
    add_code("""model = YOLO("yolo11n.pt")
print(f"YOLO11 Model Architecture: {model.model.__class__.__name__}")
print("Pretrained weights loaded successfully.")""")

    # SECTION 7: Baseline Training
    add_md("### SECTION 7: YOLO11 Baseline Training Execution\nTrain for 50 epochs with `imgsz=640`, `batch=16`, and early-stopping `patience=10`.")
    add_code("""device_id = 0 if torch.cuda.is_available() else "cpu"

training_results = model.train(
    data=str(yaml_path.resolve()),
    epochs=50,
    imgsz=640,
    batch=16,
    device=device_id,
    project="runs/detect",
    name="road_damage_yolo11n",
    patience=10,
    save=True,
    plots=True,
    verbose=True
)

print("\\n Training completed successfully!")
print(f"Results saved to directory: {training_results.save_dir}")""")

    # SECTION 8: Dynamic Best Weights Locator
    add_md("### SECTION 8: Programmatic Best Weights Resolution\nLocate `best.pt` dynamically from the Ultralytics training run directory.")
    add_code("""best_weight_path = Path(training_results.save_dir) / "weights" / "best.pt"
if not best_weight_path.exists():
    # Fallback search if loaded from earlier session
    found_weights = sorted(list(Path("runs/detect").glob("**/weights/best.pt")), key=lambda p: p.stat().st_mtime, reverse=True)
    if found_weights:
        best_weight_path = found_weights[0]

print(f"Resolved Best Model Weights: {best_weight_path.resolve()}")
assert best_weight_path.exists(), f"best.pt not found at {best_weight_path}"

# Load the best model checkpoint
best_model = YOLO(str(best_weight_path))""")

    # SECTION 9: Validation
    add_md("### SECTION 9: Validation Metrics & Per-Class Breakdown\nEvaluate on the validation split and report Precision, Recall, mAP@50, and mAP@50:95 separately for `pothole` and `alligator_crack`.")
    add_code("""val_metrics = best_model.val(
    data=str(yaml_path.resolve()),
    split="val",
    device=device_id
)

print("\\n=== OVERALL VALIDATION METRICS ===")
print(f"mAP@50      : {val_metrics.box.map50:.4f}")
print(f"mAP@50:95   : {val_metrics.box.map:.4f}")
print(f"Precision   : {val_metrics.box.mp:.4f}")
print(f"Recall      : {val_metrics.box.mr:.4f}")

print("\\n=== PER-CLASS VALIDATION METRICS ===")
class_map50 = val_metrics.box.maps50
class_map = val_metrics.box.maps

for cid, cname in class_names.items():
    ap50 = class_map50[cid] if cid < len(class_map50) else 0.0
    ap = class_map[cid] if cid < len(class_map) else 0.0
    print(f"Class {cid} [{cname:15s}] -> AP@50: {ap50:.4f} | AP@50:95: {ap:.4f}")""")

    # SECTION 10: Test Set Evaluation
    add_md("### SECTION 10: Unseen Test Set Evaluation\nEvaluate the trained detector against the held-out `test` split to measure real-world generalization.")
    add_code("""test_metrics = best_model.val(
    data=str(yaml_path.resolve()),
    split="test",
    device=device_id
)

print("\\n=== HELD-OUT TEST METRICS ===")
print(f"Test mAP@50    : {test_metrics.box.map50:.4f}")
print(f"Test mAP@50:95 : {test_metrics.box.map:.4f}")
print(f"Test Precision : {test_metrics.box.mp:.4f}")
print(f"Test Recall    : {test_metrics.box.mr:.4f}")

# Display validation / test plot if generated
confusion_matrix_path = Path(val_metrics.save_dir) / "confusion_matrix.png"
if confusion_matrix_path.exists():
    from IPython.display import display
    display(Image.open(confusion_matrix_path))""")

    # SECTION 11: Real-World Test Inference
    add_md("### SECTION 11: Real-World Road Image Inference\nRun predictions on unannotated road imagery in `real_world_test/` and display detections.")
    add_code("""real_world_dir = Path("real_world_test")
if real_world_dir.exists() and any(real_world_dir.glob("*.*")):
    test_results = best_model.predict(
        source=str(real_world_dir),
        conf=0.25,
        save=True,
        device=device_id
    )
    print(f"Inference completed on {len(test_results)} real-world images.")
    print(f"Predictions saved to: {test_results[0].save_dir}")
    
    # Display the first 4 detections
    pred_images = list(Path(test_results[0].save_dir).glob("*.jpg"))[:4]
    fig, axes = plt.subplots(1, min(4, len(pred_images)), figsize=(18, 5))
    if len(pred_images) == 1:
        axes = [axes]
    for ax, pimg in zip(axes, pred_images):
        ax.imshow(cv2.cvtColor(cv2.imread(str(pimg)), cv2.COLOR_BGR2RGB))
        ax.set_title(pimg.name, fontsize=9)
        ax.axis("off")
    plt.tight_layout()
    plt.show()
else:
    print("real_world_test/ directory is empty or not found.")""")

    # SECTION 12: Video Inference Pipeline
    add_md("### SECTION 12: Frame-by-Frame Video / Live Camera Compatibility\nDemonstrates live video and webcam frame capture loop with YOLO11 inference, architected for downstream object tracking (ByteTrack / BoT-SORT).")
    add_code("""def process_video_stream(video_source, output_path="output_detection.mp4", max_frames=100):
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print(f"Cannot open video source: {video_source}")
        return
        
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    frame_count = 0
    print("Processing video frames with YOLO11...")
    
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        # YOLO11 frame inference
        results = best_model(frame, conf=0.25, verbose=False)
        annotated_frame = results[0].plot()
        
        out.write(annotated_frame)
        frame_count += 1
        
    cap.release()
    out.release()
    print(f"Processed {frame_count} frames. Video saved to {output_path}")

print("Video stream inference helper defined. Ready for video file or webcam testing.")""")

    # SECTION 13: Model Export
    add_md("### SECTION 13: Export Weights for Deployment\nExport the trained model weights to ONNX format for deployment in the municipal reporting backend (FastAPI / OpenCV).")
    add_code("""try:
    onnx_path = best_model.export(format="onnx", dynamic=True)
    print(f"Successfully exported model to ONNX: {onnx_path}")
except Exception as e:
    print(f"ONNX export exception: {e}")""")

    out_path = Path("Untitled1.ipynb")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)
    print(f"[NOTEBOOK] Successfully created clean 13-section notebook -> {out_path.resolve()}")

if __name__ == "__main__":
    create_notebook()

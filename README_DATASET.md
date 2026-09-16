# RoadDamage20K: Road Damage Detection Dataset & YOLO11 Pipeline

A curated, leak-free, verified two-class road distress dataset and training pipeline for the final-year project:
**"Computer Vision and Deep Learning Based Road Damage and Municipal Reporting System"**

## 1. Classes
- **Class 0**: `pothole`
- **Class 1**: `alligator_crack`

## 2. Directory Layout
```
dataset/
└── RoadDamage20K/
    ├── raw/
    │   ├── RDD2022/
    │   ├── RDD2020/
    │   ├── RAD/
    │   ├── SVRDD/
    │   ├── HRP4K/
    │   └── other_sources/
    ├── intermediate/
    │   ├── converted/
    │   ├── normalized/
    │   └── reviewed/
    ├── images/
    │   ├── train/
    │   ├── val/
    │   └── test/
    ├── labels/
    │   ├── train/
    │   ├── val/
    │   └── test/
    ├── metadata/
    │   ├── source_manifest.csv
    │   ├── IMAGE_PROVENANCE.csv
    │   ├── class_mapping.csv
    │   ├── dataset_statistics.csv
    │   ├── duplicate_report.csv
    │   ├── broken_images.csv
    │   ├── invalid_labels.csv
    │   └── split_manifest.csv
    ├── qa/
    │   ├── visual_samples/
    │   ├── label_statistics/
    │   └── reports/
    └── data.yaml
```

## 3. Data Sources & Licensing
- **RDD2020 / RDD2022 (India, Japan, Czech Republic)**: CC BY 4.0 (DOI: 10.17632/5ty2wb6gvg.1)
- Vehicle-mounted smartphone perspective road imagery capturing genuine asphalt surfaces.

## 4. Pipeline Execution
Run the automated pipeline sequentially:
```bash
# Step 1: Download external sources
python pipeline/01_download_sources.py

# Step 2: Convert VOC annotations to normalized YOLO format & run QC
python pipeline/02_convert_and_filter.py

# Step 3: Deduplicate (SHA-256 + pHash) & perform sequence-group split (70/15/15)
python pipeline/03_dedup_and_split.py

# Step 4: Generate visual QA samples, provenance records, and dataset reports
python pipeline/04_qa_and_reports.py

# Step 5: Refactor Google Colab notebook
python pipeline/05_refactor_notebook.py
```

## 5. Model Training (Google Colab / Local)
Open `Untitled1.ipynb` in Google Colab or Jupyter Lab. The notebook includes:
1. Environment & CUDA check
2. Dependency installation
3. Dataset path & `data.yaml` verification
4. Dataset statistics calculation
5. Sample ground-truth visualization
6. YOLO11 Nano baseline loading
7. 50-epoch training (`imgsz=640`, `batch=16`, `patience=10`)
8. Dynamic best weights resolution (`best.pt`)
9. Validation with per-class metrics (`pothole` vs `alligator_crack`)
10. Held-out test set evaluation
11. Real-world test inference on `real_world_test/`
12. Video and live webcam frame-by-frame inference loop
13. Model export to ONNX format

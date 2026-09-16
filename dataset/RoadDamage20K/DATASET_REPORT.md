# DATASET REPORT: RoadDamage20K

## 1. Project Title
**Computer Vision and Deep Learning Based Road Damage and Municipal Reporting System**

---

## 2. Dataset Objective
The primary objective of this dataset is to provide a high-quality, verified, leak-free, and reproducible object detection benchmark specifically tailored for intelligent transport systems (ITS) and municipal road defect reporting. The dataset trains robust deep learning models (such as Ultralytics YOLO11) to recognize road distress under realistic vehicle driving perspectives, camera vibrations, lighting fluctuations, and authentic pavement textures, with an explicit emphasis on **Indian road environments**.

---

## 3. Final Class Definitions
The dataset enforces a strict, two-class detection taxonomy:
- **Class 0: `pothole`**: Depressions, holes, localized structural cavities, and missing surface material in asphalt or concrete pavements that pose hazards to vehicles and pedestrians.
- **Class 1: `alligator_crack`**: Interconnected fatigue cracking resembling reptile skin or wire mesh patterns formed by repeated structural load stresses on pavement bases.
- **Excluded / Discarded Classes**: Longitudinal cracks (D00), transverse cracks (D10), patches/repairs, manhole covers, road markings, curbs, vehicles, pedestrians, and road furniture were explicitly removed from the annotation schema to prevent class ambiguity and eliminate training noise.

---

## 4. Data Sources
The dataset integrates two legitimate, publicly accessible research sources:
1. **RDD2020 Multi-National Road Damage Dataset** (CRDDC / Maeda et al.)
   - Source: Mendeley Data (DOI: 10.17632/5ty2wb6gvg.1) / Hugging Face mirror
   - Regions: India, Japan, Czech Republic
   - Perspective: Vehicle-mounted smartphone cameras capturing genuine roadway viewpoints.
2. **Pothole600 Road Defect Dataset**
   - Source: Academic Pothole Detection Benchmark
   - Regions: Mixed asphalt pavements and urban roadways
   - Perspective: Vehicle-mounted front-facing camera imagery with verified ground-truth annotations.

---

## 5. Source Licenses
All external sources comply with non-restrictive research and academic usage permissions:
- **RDD2020**: Licensed under **Creative Commons Attribution 4.0 International (CC BY 4.0)**. Permits copying, distribution, and adaptation provided proper attribution is maintained.
- **Pothole600**: Released for academic, educational, and research benchmarking purposes.
Full attribution, URLs, and terms are preserved in [`metadata/source_manifest.csv`](file:///c:/Users/shree/Downloads/POTHOLE/dataset/RoadDamage20K/metadata/source_manifest.csv).

---

## 6. Data Collection Method
- **RDD2020**: Images were captured using high-resolution smartphone cameras secured to vehicle dashboards or windshields driving along diverse urban roads, state highways, and municipal routes. Sampling occurred at regular intervals across daylight conditions.
- **Pothole600**: Captured from vehicle perspective using calibrated vehicle cameras under natural ambient road lighting across diverse asphalt wear levels.

---

## 7. India-Focus Strategy
Indian road environments form the primary anchor of this dataset (**4,092 images, 39.4% of the total dataset**):
- Captures authentic Indian roadway characteristics: uneven asphalt surfaces, weathered repairs, monsoon dampness, dusty shoulders, roadside debris, dynamic shadows, and heavy traffic environments.
- Supplementary international imagery from Japan and the Czech Republic was strictly filtered for vehicle-facing road perspective to supply class balance for complex alligator fatigue cracking without introducing incompatible camera angles or aerial perspectives.

---

## 8. Annotation Strategy
- **Ground Truth Preservation**: Only legitimate research annotations with verified bounding boxes or pixel-level binary masks were utilized.
- **Projection to YOLO Format**: Raw bounding boxes from Pascal VOC XML annotations and polygon contours from binary segmentation masks were projected into normalized bounding boxes:
  $$\left[\text{class\_id}, x_{\text{center}}, y_{\text{center}}, \text{width}, \text{height}\right] \quad \text{where all coordinates} \in [0.0, 1.0]$$
- No unverified pseudo-labeling or zero-shot synthetic generation was used, guaranteeing 100% human-verified ground-truth fidelity.

---

## 9. Cleaning Strategy
Every candidate image and label underwent automated quality checks:
1. **File Integrity Verification**: All image headers and pixel byte-streams were validated using Pillow's `verify()` and OpenCV decoding checks; zero corrupt files were admitted.
2. **Coordinate & Area Validation**: Degenerate boxes ($< 4\times 4$ pixels) and oversized erroneous boxes ($> 98\%$ image area) were pruned and logged in [`metadata/invalid_labels.csv`](file:///c:/Users/shree/Downloads/POTHOLE/dataset/RoadDamage20K/metadata/invalid_labels.csv).
3. **Boundary Clamping**: Small float overflow bounding boxes resulting from sensor edge clipping were clamped cleanly to $[0, 1]$.
4. **Negative Sample Balancing**: Unannotated background road scenes were capped to a 15.4% ratio (1,598 frames) to prevent detector suppression while instilling false-positive resistance against normal pavement textures and non-target cracks.

---

## 10. Duplicate Removal
- **Exact Hash Deduplication**: Binary SHA-256 hashes were calculated across every image file to identify exact byte-level duplicates.
- **Perceptual Near-Duplicate Deduplication**: Perceptual hashing (pHash) with a Hamming distance threshold $\le 4$ was evaluated across the dataset pool.
- **Results**: **89 duplicate and near-duplicate images** were flagged and removed. All identified duplicate pairs and similarity metrics are logged in [`metadata/duplicate_report.csv`](file:///c:/Users/shree/Downloads/POTHOLE/dataset/RoadDamage20K/metadata/duplicate_report.csv).

---

## 11. Leakage Prevention
To prevent catastrophic data leakage from contiguous video frames:
- Camera sequences were grouped into contiguous vehicle trajectory clusters (`source_group`) based on video sequence prefixes.
- Splitting was performed at the cluster level rather than by random image sampling: all frames within a sequence group were placed exclusively into either Train, Validation, or Test.
- No identical or near-identical frames exist across the train, validation, or test partitions.

---

## 12. Train / Val / Test Strategy
The dataset follows a 70 / 15 / 15 stratified cluster split:
- **Train Split (70.0%)**: 7,270 images used for YOLO11 gradient optimization.
- **Validation Split (15.0%)**: 1,558 images used for epoch-level evaluation, learning-rate adjustment, and early stopping.
- **Test Split (15.0%)**: 1,561 images held out completely unseen for final unbiased benchmark reporting.
The complete partition manifest is stored in [`metadata/split_manifest.csv`](file:///c:/Users/shree/Downloads/POTHOLE/dataset/RoadDamage20K/metadata/split_manifest.csv).

---

## 13. Class Statistics
| Category | Train Split | Validation Split | Test Split | Total Images |
| :--- | :--- | :--- | :--- | :--- |
| **Alligator Crack Images** | 3,541 | 880 | 754 | 5,175 |
| **Pothole Images** | 1,646 | 343 | 252 | 2,241 |
| **Mixed Images (Both)** | 902 | 231 | 242 | 1,375 |
| **Curated Negatives** | 1,181 | 104 | 313 | 1,598 |
| **Total Images** | **7,270** | **1,558** | **1,561** | **10,389** |

---

## 14. Number of Images
- **Total Unique Original Images**: **10,389 images**
  - **Indian Road Conditions**: 4,092 images (39.4%)
  - **Supplementary Road Conditions**: 6,297 images (60.6%)
- Every image represents a distinct, original road surface photograph. No augmented copies (flips, rotations, crops) are included in this count.

---

## 15. Number of Annotations
- **Total Damage Annotations**: **14,591 bounding boxes**
  - **Pothole Annotations (Class 0)**: 6,233 bounding boxes
  - **Alligator Crack Annotations (Class 1)**: 8,358 bounding boxes
- Average annotation density: 1.66 bounding boxes per positive image.

---

## 16. Known Limitations
1. **Lighting Diversity**: While bright daylight, overcast, and dappled shadow conditions are thoroughly covered, nighttime and extreme low-light scenes are sparsely represented due to collection camera exposure constraints.
2. **Natural Class Distribution**: Alligator cracking occurs more frequently than isolated deep potholes in urban asphalt surfaces; this natural imbalance was retained without artificial oversampling to reflect authentic municipal driving distributions.
3. **Severity Granularity**: Severity classification (Low/Medium/High) is intentionally decoupled from model detection classes and reserved for downstream post-processing bounding-box geometry analysis.

---

## 17. Citation Requirements
When using this dataset for academic or research publications, please cite the following original benchmark:
```bibtex
@article{arya2021rdd2020,
  title={RDD2020: An annotated image dataset for smartphone-based road damage detection and classification},
  author={Arya, Deeksha and Maeda, Hiroya and Ghosh, Sanjay Kumar and Toshniwal, Durga and Mraz, Alexander and Kashiyama, Takehiro and Sekimoto, Yoshihide},
  journal={Data in Brief},
  volume={36},
  pages={107133},
  year={2021},
  doi={10.1016/j.dib.2021.107133},
  publisher={Elsevier}
}
```

---

## 18. Reproducibility Instructions
The entire data pipeline is deterministic and completely automated:
```bash
# 1. Acquire raw data sources
python pipeline/01_download_sources.py

# 2. Convert annotations, normalize coordinates, and apply QC
python pipeline/02_convert_and_filter.py

# 3. Deduplicate (SHA-256 + pHash) and perform sequence-group split
python pipeline/03_dedup_and_split.py

# 4. Generate visual QA samples, provenance records, and reports
python pipeline/04_qa_and_reports.py

# 5. Build refactored YOLO11 training notebook
python pipeline/05_refactor_notebook.py

# 6. Package dataset into portable ZIP for Google Colab / Google Drive
python pipeline/package_dataset.py
```
Model training can then be executed directly in Google Colab using [`Untitled1.ipynb`](file:///c:/Users/shree/Downloads/POTHOLE/Untitled1.ipynb) with `yolo11n.pt`.

from pathlib import Path

# Workspace & Project Paths
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DATASET_ROOT = WORKSPACE_ROOT / "dataset" / "RoadDamage20K"

RAW_DIR = DATASET_ROOT / "raw"
INTERMEDIATE_DIR = DATASET_ROOT / "intermediate"
CONVERTED_DIR = INTERMEDIATE_DIR / "converted"
NORMALIZED_DIR = INTERMEDIATE_DIR / "normalized"
REVIEWED_DIR = INTERMEDIATE_DIR / "reviewed"

IMAGES_DIR = DATASET_ROOT / "images"
LABELS_DIR = DATASET_ROOT / "labels"
METADATA_DIR = DATASET_ROOT / "metadata"
QA_DIR = DATASET_ROOT / "qa"
VISUAL_SAMPLES_DIR = QA_DIR / "visual_samples"
REPORTS_DIR = QA_DIR / "reports"
LABEL_STATS_DIR = QA_DIR / "label_statistics"

REAL_WORLD_TEST_DIR = WORKSPACE_ROOT / "real_world_test"
DATA_YAML_PATH = DATASET_ROOT / "data.yaml"

# Class Definitions
# Canonical 2-class mapping: 0 -> pothole, 1 -> alligator_crack
CLASS_NAMES = {
    0: "pothole",
    1: "alligator_crack"
}

# Source Raw Label Mappings
# Maps raw dataset class strings or IDs to (mapped_class_name, final_class_id)
# Return None or final_class_id == -1 for classes to discard
RAW_CLASS_MAPPING = {
    # RDD 2020 / 2022 format
    "D40": ("pothole", 0),
    "D20": ("alligator_crack", 1),
    "D00": ("longitudinal_crack", -1),
    "D10": ("transverse_crack", -1),
    "D43": ("crosswalk_blur", -1),
    "D44": ("white_line_blur", -1),
    "D50": ("other", -1),
    # Natural string aliases
    "pothole": ("pothole", 0),
    "Pothole": ("pothole", 0),
    "alligator crack": ("alligator_crack", 1),
    "alligator_crack": ("alligator_crack", 1),
    "Alligator Crack": ("alligator_crack", 1),
    "mesh crack": ("alligator_crack", 1),
    "mesh_crack": ("alligator_crack", 1),
    "fatigue crack": ("alligator_crack", 1),
    "longitudinal crack": ("longitudinal_crack", -1),
    "transverse crack": ("transverse_crack", -1),
    "patch": ("repair_patch", -1),
    "repair": ("repair_patch", -1),
    "manhole": ("manhole", -1)
}

# Train / Val / Test Split Ratios
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Perceptual Hashing Settings
PHASH_HAMMING_THRESHOLD = 4

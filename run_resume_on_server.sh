#!/bin/bash
set -e

export PATH=$HOME/.local/bin:$PATH

echo "=========================================================="
echo "  Resuming YOLO11 Training on College AI Server"
echo "=========================================================="

cd ~/POTHOLE

# 1. Check if checkpoint exists
if [ ! -f "last.pt" ] && [ ! -f "runs/detect/road_damage_fresh/weights/last.pt" ]; then
    echo "[!] ERROR: last.pt checkpoint not found!"
    exit 1
fi

CHECKPOINT="last.pt"
if [ ! -f "$CHECKPOINT" ]; then
    CHECKPOINT="runs/detect/road_damage_fresh/weights/last.pt"
fi

# 2. Check for dataset archive if images folder not present
if [ ! -d "images" ] && [ ! -d "RoadDamage_Fresh/images" ]; then
    if [ -f "RoadDamage_Fresh_Server_21K.zip" ]; then
        echo "Extracting RoadDamage_Fresh_Server_21K.zip..."
        unzip -q RoadDamage_Fresh_Server_21K.zip
        echo "Dataset unzipped."
    else
        echo "[!] WARNING: RoadDamage_Fresh_Server_21K.zip not found yet."
    fi
fi

# 3. Target epochs (defaults to 100, pass custom number as 1st argument if desired)
TARGET_EPOCHS=${1:-100}
echo "Target Total Epochs: $TARGET_EPOCHS"

# 4. Launch resume training with Python 3.11
python3.11 train_server_resume.py --weights "$CHECKPOINT" --epochs "$TARGET_EPOCHS"

#!/bin/bash
set -e

echo "=========================================================="
echo "  Setting up AI Server Environment for YOLO11 Training"
echo "=========================================================="

# 1. Update pip & install Ultralytics / PyTorch dependencies
pip install --upgrade pip
pip install ultralytics torch torchvision opencv-python-headless pyyaml pandas pillow tqdm

# 2. Extract dataset archive if zipped
if [ -f "RoadDamage_Fresh_Server_21K.zip" ] && [ ! -d "images" ]; then
    echo "Unzipping RoadDamage_Fresh_Server_21K.zip..."
    unzip -q RoadDamage_Fresh_Server_21K.zip
    echo "Dataset unzipped successfully."
fi

# 3. Launch YOLO11 Training
echo "Starting fresh YOLO11 training pipeline..."
python train_server.py

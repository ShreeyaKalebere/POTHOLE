#!/bin/bash
set -e

export PATH=$HOME/.local/bin:$PATH
export CUDA_VISIBLE_DEVICES=0,1,2,3

echo "=========================================================="
echo "  Launching 4-GPU YOLO11-Medium High Accuracy Training"
echo "  CUDA Devices: $CUDA_VISIBLE_DEVICES"
echo "=========================================================="

cd ~/POTHOLE

# Launch training with Python 3.11
python3.11 train_4gpu_resume.py

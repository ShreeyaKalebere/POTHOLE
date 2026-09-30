#!/bin/bash
set -e

export PATH=$HOME/.local/bin:$PATH

echo "=========================================================="
echo "  Launching YOLO11-Medium (1280px) High Accuracy Training"
echo "=========================================================="

cd ~/POTHOLE

# Verify environment
python3.11 -c "import torch, ultralytics; print('CUDA Ready:', torch.cuda.is_available(), 'GPU:', torch.cuda.get_device_name(0))"

# Launch training with Python 3.11
python3.11 train_high_accuracy_server.py

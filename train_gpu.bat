@echo off
title Road Damage Detection - Local GPU Training (RTX 4060)
echo ====================================================================
echo Starting YOLO11 Training on NVIDIA GeForce RTX 4060 Laptop GPU...
echo Dataset: dataset\RoadDamage20K\data.yaml
echo Model:   yolo11n.pt (150 Epochs, Batch 16, Cosine LR, Patience 30)
echo ====================================================================
python train_local_gpu.py
pause

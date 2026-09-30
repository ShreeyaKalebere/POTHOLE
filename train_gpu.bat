@echo off
cd /d "%~dp0"
title Road Damage Detection - Fresh YOLO11 GPU Training (RTX 4060)
echo ====================================================================
echo Starting Fresh YOLO11 Training on NVIDIA GeForce RTX 4060 Laptop GPU...
echo Dataset: RoadDamage_Fresh\data.yaml
echo Model:   yolo11n.pt (100 Epochs, Batch 16, imgsz 640, Patience 50)
echo Results: Live epoch logs written to training_results.csv
echo ====================================================================
python pipeline\train_fresh_yolo11.py
pause

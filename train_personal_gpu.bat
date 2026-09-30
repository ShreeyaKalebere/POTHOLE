@echo off
title Road Damage Detection — 90%+ Target Training (RTX 4060)
cd /d "%~dp0"
echo ======================================================================
echo   ROAD DAMAGE DETECTION — 90%+ ACCURACY PIPELINE (RTX 4060)
echo   Backbone: YOLO11-Medium (20.1M) | Resolution: 768x768 | Batch: 8
echo ======================================================================
echo.
python train_personal_gpu.py --model yolo11m.pt --epochs 60 --batch 8 --imgsz 768
pause

@echo off
cd /d "%~dp0"
title YOLO11 Training Results Table
echo ====================================================================
echo  YOLO11 Training Metrics - Epoch Results
echo ====================================================================
python view_training_results.py
pause

@echo off
cd /d "%~dp0"
title YOLO11 GPU Training - Live Epoch Monitor
:loop
cls
echo ====================================================================
echo  YOLO11 FRESH TRAINING - LIVE EPOCH MONITOR
echo  Dataset: RoadDamage_Fresh\data.yaml (100 Epochs Target)
echo  Sync File: training_results.csv
echo ====================================================================
python view_training_results.py
echo.
echo Press 'R' and Enter to refresh immediately, or wait 30 seconds...
timeout /t 30 >nul
goto loop

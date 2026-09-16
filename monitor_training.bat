@echo off
title YOLO11 GPU Training — Live Monitor
echo ====================================================================
echo  LIVE TRAINING MONITOR (NVIDIA GeForce RTX 4060)
echo  Showing real-time training progress, batch speeds, and epoch losses.
echo  (Press Ctrl+C at any time to exit the viewer; training continues)
echo ====================================================================
powershell -Command "Get-Content 'C:\Users\shree\.gemini\antigravity-ide\brain\4e43cee8-b97b-4981-921d-9d67c81d6717\.system_generated\tasks\task-758.log' -Wait -Tail 25"
pause

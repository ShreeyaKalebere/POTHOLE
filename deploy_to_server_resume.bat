@echo off
title Deploy YOLO11 Resume Training to College AI Server
echo ========================================================
echo   Deploying YOLO11 Resume Training to College AI Server
echo ========================================================
python pipeline\deploy_resume_to_server.py %*
pause

@echo off
title Download Completed Results from College AI Server
echo ========================================================
echo   Downloading Trained Model and Metrics from Server
echo ========================================================
python pipeline\download_results.py %*
pause

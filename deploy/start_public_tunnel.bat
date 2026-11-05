@echo off
title Kolhapur Road Damage System - Live Cloudflare Deployment
echo ================================================================
echo   Kolhapur Road Damage & Municipal Reporting System
echo   Starting Local Backend + Cloudflare HTTPS Public Tunnel
echo ================================================================
echo.

cd /d "%~dp0\.."

REM Step 1: Ensure MongoDB Atlas backend is running or start it
echo [1/2] Verifying Python backend on port 8000...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/api/health' -TimeoutSec 2 -UseBasicParsing; Write-Host 'Backend is already running!' -ForegroundColor Green } catch { Start-Process python -ArgumentList '-m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000' -WindowStyle Minimized; Write-Host 'Started backend in background.' -ForegroundColor Cyan }"

REM Step 2: Start Cloudflare Tunnel
echo [2/2] Launching Cloudflare HTTPS Tunnel...
echo.
tools\cloudflared.exe tunnel --url http://localhost:8000
pause


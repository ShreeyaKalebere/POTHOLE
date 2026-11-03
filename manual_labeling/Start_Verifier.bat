@echo off
REM Road Damage Label Verifier - opens http://localhost:8090 (only on this laptop)
cd /d "%~dp0"
start "" http://localhost:8090
python server.py
pause

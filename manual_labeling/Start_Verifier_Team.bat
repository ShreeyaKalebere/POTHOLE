@echo off
REM Teammates on the SAME Wi-Fi open http://THIS-LAPTOP-IP:8090 (IP is printed below)
cd /d "%~dp0"
ipconfig | findstr /i "IPv4"
start "" http://localhost:8090
python server.py --team
pause

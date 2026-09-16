"""
RoadCare AI - Municipal System One-Click Launcher
Launches FastAPI backend service and opens the Web Dashboard in your default browser.
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent
    frontend_html = root_dir / "frontend" / "index.html"
    
    print("=" * 70)
    print("   RoadCare AI: Municipal Road Distress & Reporting System")
    print("   Computer Vision & Deep Learning Final-Year Project Demonstration")
    print("=" * 70)
    
    # 1. Start FastAPI Backend in background
    print("\n[1/3] Launching FastAPI Backend on 0.0.0.0:8000...")
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(root_dir / "backend")
    
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(root_dir),
        env=backend_env
    )
    
    # Wait for server to bind port
    time.sleep(2.0)
    
    # 2. Seed initial defects if empty
    print("[2/3] Verifying database telemetry state...")
    try:
        import urllib.request
        seed_req = urllib.request.Request(
            "http://127.0.0.1:8000/api/defects/seed_sample",
            data=b"",
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(seed_req, timeout=3)
        print("      -> Municipal defect database ready.")
    except Exception as e:
        print(f"      -> Backend connecting... ({e})")

    # Detect local LAN IP for mobile phone pairing
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        lan_ip = "127.0.0.1"

    mobile_patrol_url = f"http://{lan_ip}:8000/mobile.html"

    # 3. Open Frontend in Browser
    print("[3/3] Opening RoadCare AI Web Dashboard in your browser...")
    dashboard_url = "http://localhost:8000/"
    webbrowser.open(dashboard_url)
    
    print("\n" + "=" * 70)
    print("ROADCARE AI RUNNING SUCCESSFULLY:")
    print(" - Main Dashboard      : " + dashboard_url)
    print(" - 📱 Mobile Patrol HUD : " + mobile_patrol_url)
    print(" - Presentation Deck   : http://localhost:8000/presentation/")
    print(" - Swagger Docs        : http://localhost:8000/docs")
    print(" - Live Stream WS      : ws://0.0.0.0:8000/ws/live_patrol")
    print("=" * 70)
    print("Tip: On your phone, connect to same Wi-Fi and open the Mobile Patrol HUD URL.")
    print("\nPress Ctrl+C to shut down the backend server.")

    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down backend server...")
        backend_process.terminate()
        backend_process.wait()
        print("Backend server stopped.")

if __name__ == "__main__":
    main()

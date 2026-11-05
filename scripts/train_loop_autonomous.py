import os, sys, time, subprocess

TARGET_EPOCHS = 30
RESULTS_CSV = r"runs/yolo11s_v13_clean_single/results.csv"

def get_current_epoch():
    if not os.path.exists(RESULTS_CSV):
        return 0
    try:
        with open(RESULTS_CSV, "r", encoding="utf-8") as f:
            rows = [l.strip() for l in f if l.strip()]
        if len(rows) <= 1:
            return 0
        return int(rows[-1].split(",")[0])
    except Exception:
        return 0

print(f"[AUTONOMOUS_RUNNER] Starting persistent training loop up to {TARGET_EPOCHS} epochs...", flush=True)

while True:
    ep = get_current_epoch()
    print(f"[AUTONOMOUS_RUNNER] Completed epochs: {ep}/{TARGET_EPOCHS}", flush=True)
    if ep >= TARGET_EPOCHS:
        print(f"[AUTONOMOUS_RUNNER] SUCCESS: All {TARGET_EPOCHS} epochs finished!", flush=True)
        break

    print(f"[AUTONOMOUS_RUNNER] Running training for Epoch {ep + 1} to {TARGET_EPOCHS}...", flush=True)
    # Run train_clean_v13.py in a dedicated fresh process
    ret = subprocess.run([sys.executable, "scripts/train_clean_v13.py", str(TARGET_EPOCHS)])
    print(f"[AUTONOMOUS_RUNNER] Process returned code {ret.returncode}. Checking progress...", flush=True)
    time.sleep(3)


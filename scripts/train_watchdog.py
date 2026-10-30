"""
Overnight watchdog for training.

- Starts (or adopts) training:  python train.py resume yolo11s <workers>
- If the log file has not changed for STALL_MIN minutes (a data-loader worker hung,
  usually because RAM ran out), it kills the training processes and resumes from
  the last saved epoch. At most MAX_RESTARTS times.
- When training ends normally, runs evaluate.py and find_label_errors.py.

Run:  python train_watchdog.py [workers] [script] [logfile]
      python train_watchdog.py 2 train_v2.py train_v2.log   (v2 run)
"""
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path("F:/POTHOLE_PROJECT")
SCRIPT = sys.argv[2] if len(sys.argv) > 2 else "train.py"
LOG = ROOT / (sys.argv[3] if len(sys.argv) > 3 else "train_yolo11s.log")
RUN = {"train.py": "yolo11s_v1", "train_v2.py": "yolo11s_v2_960", "train_v3.py": "yolo11s_v3_aug", "train_v4.py": "yolo11s_v4_fixed", "train_v5p.py": "yolo11s_v5_kolpseudo", "train_v6.py": "yolo11s_v6_kolreview", "train_v7.py": "yolo11s_v7_kolfixed"}.get(SCRIPT, "yolo11s_v1")
SCRIPTS = ROOT / "scripts"
WORKERS = sys.argv[1] if len(sys.argv) > 1 else "4"
STALL_MIN = 8
MAX_RESTARTS = 10


def say(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def training_procs():
    """All python processes belonging to training (main + data-loader workers)."""
    me = psutil.Process().pid
    out = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if p.info["pid"] == me or "python" not in (p.info["name"] or "").lower():
                continue
            cmd = " ".join(p.info["cmdline"] or [])
            if SCRIPT in cmd or "multiprocessing.spawn" in cmd:
                out.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return out


def train_main_running():
    for p in training_procs():
        try:
            if p.is_running() and SCRIPT in " ".join(p.cmdline()):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def kill_training():
    procs = training_procs()
    for p in procs:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(procs, timeout=15)


def finished():
    # the final validation after training prints a lot, so look further back than the last few KB
    tail = LOG.read_bytes()[-200_000:].decode("utf-8", "ignore").replace("\r", "\n")
    return "epochs completed in" in tail or "EarlyStopping: " in tail


def start_training(workers):
    log = open(LOG, "ab")
    say(f"starting training with {workers} data workers")
    cmd = ([sys.executable, SCRIPT, str(workers)] if SCRIPT != "train.py"
           else [sys.executable, "train.py", "resume", "yolo11s", str(workers)])
    return subprocess.Popen(cmd,
                            cwd=SCRIPTS, stdout=log, stderr=subprocess.STDOUT)


def main():
    restarts = 0
    main_proc = None
    workers = int(WORKERS)
    if not LOG.exists():
        LOG.touch()
    if not train_main_running():
        say("no training running - starting it")
        main_proc = start_training(workers)
    else:
        say("adopting the training that is already running")

    # progress = log file growing. (On Windows the "modified" time of a file that is
    # still open for writing is not updated reliably, so it cannot be used.)
    last_size, last_change = LOG.stat().st_size, time.time()
    while True:
        time.sleep(30)
        size = LOG.stat().st_size
        if size != last_size:
            last_size, last_change = size, time.time()
        running = train_main_running()
        if finished():
            say("TRAINING FINISHED")
            break
        idle = (time.time() - last_change) / 60
        if running and idle < STALL_MIN:
            continue
        if restarts >= MAX_RESTARTS:
            say(f"gave up after {restarts} restarts")
            return
        reason = f"stalled {idle:.0f} min" if running else "training process exited"
        say(f"{reason} - restarting from last saved epoch (restart {restarts + 1})")
        kill_training()
        time.sleep(10)
        # every freeze so far came from data-loader workers running out of RAM:
        # use fewer of them after each restart (4 -> 2 -> 0)
        workers = max(0, workers - 1)
        main_proc = start_training(workers)
        restarts += 1
        last_size, last_change = LOG.stat().st_size, time.time()

    kill_training()                     # leftover hung workers, if any
    say("running evaluate.py")
    with open(ROOT / "qa" / f"evaluate_{RUN}.log", "w") as f:
        r = subprocess.run([sys.executable, "evaluate.py", RUN], cwd=SCRIPTS, stdout=f, stderr=subprocess.STDOUT)
    say(f"evaluate.py exit code {r.returncode}")
    say("ALL DONE")


if __name__ == "__main__":
    main()

"""Central settings for the backend. Change values here, not inside other files."""
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent          # F:/POTHOLE_PROJECT
BACKEND_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BACKEND_DIR / "media"                                # uploaded + annotated images
MEDIA_DIR.mkdir(exist_ok=True)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "road_damage")              # the cloud sets its own DB_NAME in render.yaml

# Model: first file that exists is used. best.pt appears when training finishes.
MODEL_CANDIDATES = [
    PROJECT_DIR / "models" / "final.pt",
    PROJECT_DIR / "runs" / "yolo11s_v1" / "weights" / "best.pt",
    PROJECT_DIR / "runs" / "yolo11s_v1" / "weights" / "last.pt",
]
CONF_THRESHOLD = 0.35
# Device for detection in the backend: "0" = GPU. Use "cpu" while a training run is using the GPU,
# because sharing the 8 GB GPU with training caused an out-of-memory crash.
# (set INFER_DEVICE=cpu before starting the backend in that case).
INFER_DEVICE = os.getenv("INFER_DEVICE", "0")
CLASS_NAMES = {0: "pothole", 1: "alligator_crack"}


def _allowed_cpus():
    """CPUs this process may really use. In a cloud container os.cpu_count() reports the whole host,
    while the container may only get a fraction of one CPU (Linux cgroup quota)."""
    count = os.cpu_count() or 1
    for path, split in (("/sys/fs/cgroup/cpu.max", True), ("/sys/fs/cgroup/cpu/cpu.cfs_quota_us", False)):
        try:
            text = Path(path).read_text().split()
            if split:
                quota, period = text[0], text[1]
            else:
                quota = text[0]
                period = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text().split()[0]
            if quota not in ("max", "-1"):
                return max(1, min(count, int(int(quota) / int(period) + 0.999)))
        except (OSError, IndexError, ValueError):
            continue
    return count


# CPU threads for detection. Too many threads on a small cloud CPU make every frame much slower.
CPU_THREADS = int(os.getenv("CPU_THREADS", "0")) or max(1, min(8, _allowed_cpus() - (0 if _allowed_cpus() <= 2 else 1)))
# Image size for Live Patrol only (0 = the size the model was trained at). 320 is about twice as fast on CPU.
LIVE_IMGSZ = int(os.getenv("LIVE_IMGSZ", "0"))

# Same damage within this distance (metres) and still open = same incident, not a new one
DEDUP_RADIUS_M = 15

# ---- deployment settings (all set through environment variables in the cloud) ----
MEDIA_BACKEND = os.getenv("MEDIA_BACKEND", "local")          # "local" or "gridfs"
CLOUD_MAX_IMAGE_SIDE = int(os.getenv("CLOUD_MAX_IMAGE_SIDE", "1280"))
APP_PASSWORD = os.getenv("APP_PASSWORD", "")                  # first admin password, if ADMIN_PASSWORD is not set
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
APP_SECRET = os.getenv("APP_SECRET", "")                      # signs login cookies
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "14"))
DASHBOARD_DIST = Path(os.getenv("DASHBOARD_DIST", str(PROJECT_DIR / "dashboard" / "dist")))

STATUSES = ["Reported", "In Progress", "Repaired"]
SEVERITIES = ["Low", "Medium", "High"]

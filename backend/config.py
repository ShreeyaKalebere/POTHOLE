"""Central settings for the backend. Change values here, not inside other files."""
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent          # F:/POTHOLE_PROJECT
BACKEND_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BACKEND_DIR / "media"                                # uploaded + annotated images
MEDIA_DIR.mkdir(exist_ok=True)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "road_damage")

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

# Same damage within this distance (metres) and still open = same incident, not a new one
DEDUP_RADIUS_M = 15

# ---- deployment settings (all set through environment variables in the cloud) ----
MEDIA_BACKEND = os.getenv("MEDIA_BACKEND", "local")          # "local" or "gridfs"
CLOUD_MAX_IMAGE_SIDE = int(os.getenv("CLOUD_MAX_IMAGE_SIDE", "1280"))
APP_PASSWORD = os.getenv("APP_PASSWORD", "")                  # empty = no login (laptop use)
APP_SECRET = os.getenv("APP_SECRET", "")                      # signs login cookies
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "14"))
DASHBOARD_DIST = Path(os.getenv("DASHBOARD_DIST", str(PROJECT_DIR / "dashboard" / "dist")))

STATUSES = ["Reported", "In Progress", "Repaired"]
SEVERITIES = ["Low", "Medium", "High"]

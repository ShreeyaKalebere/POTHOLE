"""Build the clean Render deployment repository.
Copies only the production runtime files (backend, compiled dashboard dist, model, Dockerfile, render.yaml).
"""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_BACKEND = ROOT / "backend"
SRC_DIST = ROOT / "dashboard" / "dist"
SRC_MODEL = ROOT / "models" / "final.pt"
DEST = ROOT / "deploy" / "render_repo"

if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir(parents=True, exist_ok=True)

# 1. Copy backend python files
dest_backend = DEST / "backend"
dest_backend.mkdir(parents=True, exist_ok=True)
for item in SRC_BACKEND.glob("*.py"):
    shutil.copy2(item, dest_backend / item.name)
for item in SRC_BACKEND.glob("*.yaml"):
    shutil.copy2(item, dest_backend / item.name)

# 2. Copy pre-built dashboard dist
dest_dist = DEST / "dashboard" / "dist"
shutil.copytree(SRC_DIST, dest_dist)

# 3. Copy model
dest_models = DEST / "models"
dest_models.mkdir(parents=True, exist_ok=True)
shutil.copy2(SRC_MODEL, dest_models / "final.pt")

# 4. Copy cloud requirements
shutil.copy2(ROOT / "deploy" / "requirements-cloud.txt", DEST / "requirements.txt")

# 5. Create optimized Dockerfile
dockerfile_content = """# Render.com 24/7 Web Service - Pothole & Road Damage Detection
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    INFER_DEVICE=cpu \\
    MEDIA_BACKEND=gridfs \\
    DASHBOARD_DIST=/app/dashboard/dist \\
    YOLO_CONFIG_DIR=/tmp/ultralytics

WORKDIR /app/backend

# System dependencies for OpenCV and PyTorch CPU
RUN apt-get update && apt-get install -y --no-install-recommends \\
    libgl1 \\
    libglib2.0-0 \\
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU directly from official wheels (no CUDA bloat)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install backend dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy backend code, models, and pre-built frontend dashboard
COPY backend/ /app/backend/
COPY models/final.pt /app/models/final.pt
COPY dashboard/dist/ /app/dashboard/dist/

# Security: non-root user and required writeable dirs
RUN useradd -m app && mkdir -p /app/backend/media /app/backend/models_cache /tmp/ultralytics \\
    && chown -R app /app /tmp/ultralytics
USER app

EXPOSE 8000

# Render injects $PORT automatically
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
"""
(DEST / "Dockerfile").write_text(dockerfile_content, encoding="utf-8")

# 6. Create render.yaml blueprint
render_yaml = """services:
  - type: web
    name: kolhapur-road-damage
    runtime: docker
    plan: free
    region: singapore
    envVars:
      - key: MONGO_URI
        value: mongodb+srv://pothole_admin:aTwRZO0bZZCLFIMK@cluster0.lag8x5i.mongodb.net/pothole_detection?retryWrites=true&w=majority
      - key: DB_NAME
        value: pothole_detection
      - key: INFER_DEVICE
        value: cpu
      - key: MEDIA_BACKEND
        value: gridfs
      - key: PORT
        value: 8000
"""
(DEST / "render.yaml").write_text(render_yaml, encoding="utf-8")

# 7. Create .gitignore
gitignore_content = """__pycache__/
*.pyc
*.tmp
*.log
.DS_Store
"""
(DEST / ".gitignore").write_text(gitignore_content, encoding="utf-8")

# 8. Create README.md
readme_content = """# Kolhapur Road Damage & Municipal Reporting System

Production deployment for [Render.com](https://render.com).

## Features
- **FastAPI Backend** with real-time YOLO11s road damage detection.
- **Pre-built React Dashboard** with interactive Leaflet GIS map and Kolhapur ward heatmaps.
- **MongoDB Atlas Cloud Database** (768 verified incidents).
- **GridFS Media Storage** for persistent photo storage on cloud instances.
"""
(DEST / "README.md").write_text(readme_content, encoding="utf-8")

print(f"Successfully assembled render deployment repo at {DEST}")

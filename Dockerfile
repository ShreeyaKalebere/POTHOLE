# Road Damage & Municipal Reporting System - Render.com / Cloud Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INFER_DEVICE=cpu \
    MEDIA_BACKEND=gridfs \
    DASHBOARD_DIST=/app/dashboard/dist \
    YOLO_CONFIG_DIR=/tmp/ultralytics

WORKDIR /app/backend

# System dependencies for OpenCV and PyTorch CPU
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU directly from official wheels (no CUDA bloat)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install backend dependencies
COPY deploy/requirements-cloud.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

# Copy backend code, models, and pre-built frontend dashboard
COPY backend/ /app/backend/
COPY models/final.pt /app/models/final.pt
COPY dashboard/dist/ /app/dashboard/dist/

# Security: non-root user and required writeable dirs
RUN useradd -m app && mkdir -p /app/backend/media /app/backend/models_cache /tmp/ultralytics \
    && chown -R app /app /tmp/ultralytics
USER app

EXPOSE 8000

# Cloud hosts set $PORT; default 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]

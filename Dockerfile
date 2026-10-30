# Road Damage & Municipal Reporting System - one container: React dashboard + FastAPI + YOLO11 model.
# Build:  docker build -t road-damage .
# Run:    docker run -p 8000:8000 -e MONGO_URI=... -e APP_PASSWORD=... road-damage

# ---- 1. build the React dashboard ----
FROM node:20-alpine AS dashboard
WORKDIR /app
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY dashboard/ ./
RUN npm run build

# ---- 2. Python backend + model ----
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    INFER_DEVICE=cpu MEDIA_BACKEND=gridfs \
    DASHBOARD_DIST=/app/dashboard/dist YOLO_CONFIG_DIR=/tmp/ultralytics
WORKDIR /app/backend

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY deploy/requirements-cloud.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

COPY backend/ /app/backend/
COPY models/final.pt /app/models/final.pt
COPY --from=dashboard /app/dist /app/dashboard/dist

# run as a normal user, not root
RUN useradd -m app && mkdir -p /app/backend/media /app/backend/models_cache /tmp/ultralytics \
    && chown -R app /app/backend /tmp/ultralytics
USER app

EXPOSE 8000
# cloud hosts set $PORT; default 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]

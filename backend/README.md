# Kolhapur Municipal Corporation (KMC) Road Distress Backend Service

A high-performance FastAPI backend service for ingesting vehicle road damage detections, maintaining municipal repair workflows, generating GeoJSON feeds for Leaflet / GIS, and serving the area-wise triage portal for the **Kolhapur Region, Maharashtra, India**.

---

## Architecture Overview
- **Framework**: FastAPI + Pydantic v2 + Starlette StaticFiles
- **Regional Focus**: Kolhapur Region across 5 administrative zones (Central, North, South, East, West Kolhapur)
- **Database Engine**: Dual-Engine Support:
  - **MongoDB**: Activated automatically when `MONGO_URI` environment variable is set (e.g., local MongoDB or MongoDB Atlas).
  - **SQLite Fallback**: Activates automatically with zero configuration, persisting records to `backend/road_damage.db` with auto-migration support.
- **Unified Hosting**: The FastAPI service serves the complete web portal directly:
  - `http://localhost:8000/`: Kolhapur Road Safety Web Dashboard
  - `http://localhost:8000/presentation/`: Academic 16:9 Presentation Deck
  - `http://localhost:8000/docs`: Interactive OpenAPI / Swagger Documentation
  - `http://localhost:8000/api/health`: Service health and supported zone metadata

---

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the Kolhapur Road Safety Web Portal (HTML/CSS/JS) |
| `GET` | `/presentation` | Serves the academic thesis presentation slide deck |
| `GET` | `/api/health` | Service health status, supported classes, and Kolhapur zones |
| `POST` | `/api/auth/login` | Authenticates ward officer by Kolhapur zone (`Central Kolhapur`, `West Kolhapur`, etc.) |
| `GET` | `/api/auth/zones` | Returns all 5 Kolhapur municipal zone profiles, GPS centers, and jurisdiction areas |
| `POST` | `/api/defects/report` | Ingests batch defect records from `track_and_severity.py` edge tracker |
| `GET` | `/api/defects` | Lists defect records with filters (`zone`, `area`, `class_name`, `severity`, `status`) |
| `GET` | `/api/defects/geojson` | Returns standard GeoJSON RFC 7946 FeatureCollection filtered by zone |
| `PATCH` | `/api/defects/{id}/status` | Updates municipal triage status (`reported`, `inspected`, `in_progress`, `repaired`) |
| `GET` | `/api/analytics/summary` | Municipal KPIs filtered by zone (total potholes, cracks, severity counts, repair rate) |
| `POST` | `/api/defects/seed_sample` | Seeds database with 25 authentic Kolhapur defect detections across all 5 zones |

---

## Running the Server

1. **One-Click Launch (Recommended)**:
   Run from repository root:
   ```bash
   python run_system.py
   ```
   or double-click `start_demo.bat`.

2. **Manual Launch**:
   ```bash
   python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```

3. **Interactive Swagger Documentation**:
   Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to inspect and test all endpoints interactively.


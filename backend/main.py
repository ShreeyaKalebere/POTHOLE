from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import socket
import time
import uuid
from datetime import datetime
import cv2
import numpy as np

from fastapi import FastAPI, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from models import (
    DefectIngest, DefectRecord, DefectStatusUpdate, AnalyticsSummary,
    AuthLoginRequest, OfficerProfile, ZoneBreakdownResponse
)
from database import (
    insert_defects, query_defects, update_defect_status, get_summary_statistics,
    get_zonewise_statistics
)
from detector import get_detector
from zones import get_zone_profiles_map, load_zones_geojson, resolve_zone_for_coordinates



app = FastAPI(
    title="Kolhapur Municipal Road Distress Reporting System API",
    description="Backend service for ingesting vehicle road damage detections, managing Kolhapur municipal repair workflows by zone, and streaming GeoJSON for map visualization.",
    version="2.0.0"
)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dynamic zone profiles generated from single editable GeoJSON configuration
KOLHAPUR_ZONE_PROFILES = get_zone_profiles_map()


@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "service": "Kolhapur Road Damage & Municipal Reporting API",
        "region": "Kolhapur, Maharashtra, India",
        "zones_supported": list(KOLHAPUR_ZONE_PROFILES.keys()),
        "classes_supported": ["pothole", "alligator_crack"],
        "docs_url": "/docs"
    }

@app.post("/api/auth/login", response_model=OfficerProfile, tags=["Authentication"])
def login_officer(req: AuthLoginRequest):
    """Authenticate ward officer or civil engineer for Kolhapur area-wise triage."""
    zone_key = req.zone.strip()
    for k, p in KOLHAPUR_ZONE_PROFILES.items():
        if k.lower() == zone_key.lower():
            return p
    return KOLHAPUR_ZONE_PROFILES["all"]

@app.get("/api/auth/zones", tags=["Authentication"])
def list_zones():
    """Returns all 5 Kolhapur municipal zones with example areas and coordinates."""
    return KOLHAPUR_ZONE_PROFILES

@app.get("/api/zones/geojson", tags=["Zones"])
def get_zones_geojson_endpoint():
    """Return the single editable GeoJSON definition of the 5 Kolhapur operational study zones."""
    return load_zones_geojson()

@app.get("/api/zones/statistics", response_model=ZoneBreakdownResponse, tags=["Zones"])
def get_zones_statistics_endpoint():
    """Returns zone-wise counts for total incidents, potholes, alligator cracks, severity, and status."""
    return get_zonewise_statistics()

@app.post("/api/defects/report", status_code=status.HTTP_201_CREATED, tags=["Ingestion"])
def ingest_defects(reports: List[DefectIngest]):
    """Receives live batch defect detections from the vehicle edge tracking pipeline."""
    if not reports:
        raise HTTPException(status_code=400, detail="Empty defect reports list.")
    payload = [r.dict() for r in reports]
    count = insert_defects(payload)
    return {
        "status": "success",
        "defects_ingested": count,
        "message": f"Successfully recorded {count} Kolhapur road distress events."
    }

@app.get("/api/defects", response_model=List[DefectRecord], tags=["Defects"])
def list_defects(
    class_name: Optional[str] = Query(None, description="Filter by class: pothole or alligator_crack"),
    severity: Optional[str] = Query(None, description="Filter by severity: Low, Medium, High"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: reported, inspected, in_progress, repaired"),
    zone: Optional[str] = Query(None, description="Filter by Kolhapur zone, e.g. Central Kolhapur"),
    area: Optional[str] = Query(None, description="Filter by locality, e.g. Shahupuri, Rankala"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return")
):
    """Lists Kolhapur road defect records with optional zone filtering."""
    results = query_defects(
        class_name=class_name,
        severity=severity,
        status=status_filter,
        zone=zone,
        area=area,
        limit=limit
    )
    return results

@app.get("/api/defects/geojson", tags=["Mapping"])
def get_defects_geojson(
    severity: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    zone: Optional[str] = None
):
    """Generates a standard GeoJSON FeatureCollection for Kolhapur map rendering."""
    records = query_defects(severity=severity, status=status_filter, zone=zone, limit=500)
    features = []
    for r in records:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [r["longitude"], r["latitude"]]
            },
            "properties": {
                "id": r["id"],
                "defect_id": r["defect_id"],
                "class_name": r["class_name"],
                "severity": r["severity"],
                "confidence": r["confidence"],
                "status": r["status"],
                "created_at": r["created_at"],
                "zone_id": r.get("zone_id"),
                "zone_name": r.get("zone_name"),
                "zone": r.get("zone_name") or r.get("zone", "Central Kolhapur"),
                "area": r.get("area", ""),
                "street": r.get("street", ""),
                "assigned_contractor": r.get("assigned_contractor"),
                "notes": r.get("notes")
            }
        })
    return {
        "type": "FeatureCollection",
        "features": features
    }

@app.patch("/api/defects/{defect_id}/status", tags=["Municipal Workflow"])
def update_status(defect_id: str, update: DefectStatusUpdate):
    """Allows Kolhapur municipal engineers to update repair workflow status."""
    valid_statuses = ["reported", "inspected", "in_progress", "repaired"]
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    success = update_defect_status(
        defect_id=defect_id,
        new_status=update.status,
        contractor=update.assigned_contractor,
        notes=update.notes
    )
    if not success:
        raise HTTPException(status_code=404, detail=f"Defect record '{defect_id}' not found.")
    return {
        "status": "success",
        "message": f"Defect {defect_id} updated to '{update.status}'."
    }

@app.get("/api/analytics/summary", response_model=AnalyticsSummary, tags=["Analytics"])
def get_analytics(zone: Optional[str] = None):
    """Returns Kolhapur municipal KPIs filtered by zone."""
    return get_summary_statistics(zone=zone)

@app.post("/api/defects/seed_sample", tags=["Testing"])
def seed_sample_defects():
    """Seeds the database with sample defect logs from downstream_prototype/sample_municipal_payload.json."""
    sample_file = Path(__file__).resolve().parent.parent / "downstream_prototype" / "sample_municipal_payload.json"
    if not sample_file.exists():
        raise HTTPException(status_code=404, detail="sample_municipal_payload.json not found.")
    with open(sample_file, "r", encoding="utf-8") as f:
        samples = json.load(f)
    count = insert_defects(samples)
    return {
        "status": "success",
        "seeded_count": count
    }

@app.get("/api/patrol/route", tags=["Patrol"])
def get_patrol_route(zone: Optional[str] = "Central Kolhapur"):
    """
    Returns synchronized Kolhapur dashcam patrol telemetry route.
    Contains vehicle GPS breadcrumb trail and synchronized road distress detection events.
    """
    return {
        "unit_id": "KMC-PATROL-04",
        "zone": zone or "Central Kolhapur",
        "route_name": "Station Road Shahupuri -> Rajarampuri Arterial Survey",
        "video_url": "/media/dashcam_demo.mp4",
        "total_duration_sec": 31.0,
        "base_speed_kmh": 36.0,
        "waypoints": [
            {"time_sec": 0.0, "lat": 16.7042, "lng": 74.2395, "street": "Station Road (Shahupuri Bus Stand)"},
            {"time_sec": 5.0, "lat": 16.7049, "lng": 74.2412, "street": "Station Road (Railway Overbridge)"},
            {"time_sec": 10.0, "lat": 16.7057, "lng": 74.2429, "street": "Station Road (Shahupuri Corner)"},
            {"time_sec": 15.0, "lat": 16.7064, "lng": 74.2446, "street": "Laxmipuri Link Road"},
            {"time_sec": 20.0, "lat": 16.7071, "lng": 74.2462, "street": "Rajarampuri 1st Lane Junction"},
            {"time_sec": 25.0, "lat": 16.7078, "lng": 74.2477, "street": "Rajarampuri 2nd Lane Main"},
            {"time_sec": 31.0, "lat": 16.7085, "lng": 74.2492, "street": "Rajarampuri Main Road"}
        ],
        "events": [
            {
                "time_sec": 3.2,
                "defect_id": "PATROL-101",
                "class_name": "pothole",
                "severity": "High",
                "confidence": 0.942,
                "gps": {"latitude": 16.7046, "longitude": 74.2405},
                "zone": "Central Kolhapur",
                "area": "Shahupuri",
                "street": "Station Road (Shahupuri Bus Stand)",
                "bbox_norm": [0.35, 0.58, 0.28, 0.24],
                "notes": "Deep impact crater in vehicle travel wheel path."
            },
            {
                "time_sec": 8.5,
                "defect_id": "PATROL-102",
                "class_name": "alligator_crack",
                "severity": "Medium",
                "confidence": 0.885,
                "gps": {"latitude": 16.7055, "longitude": 74.2425},
                "zone": "Central Kolhapur",
                "area": "Shahupuri",
                "street": "Station Road (Railway Overbridge)",
                "bbox_norm": [0.20, 0.60, 0.42, 0.25],
                "notes": "Interconnected fatigue mesh cracking across lane center."
            },
            {
                "time_sec": 15.8,
                "defect_id": "PATROL-103",
                "class_name": "pothole",
                "severity": "High",
                "confidence": 0.961,
                "gps": {"latitude": 16.7065, "longitude": 74.2448},
                "zone": "Central Kolhapur",
                "area": "Laxmipuri",
                "street": "Laxmipuri Link Road",
                "bbox_norm": [0.42, 0.54, 0.32, 0.26],
                "notes": "Severe structural asphalt cavity causing traffic deceleration."
            },
            {
                "time_sec": 22.4,
                "defect_id": "PATROL-104",
                "class_name": "pothole",
                "severity": "Medium",
                "confidence": 0.849,
                "gps": {"latitude": 16.7074, "longitude": 74.2468},
                "zone": "Central Kolhapur",
                "area": "Rajarampuri",
                "street": "Rajarampuri 1st Lane Junction",
                "bbox_norm": [0.28, 0.64, 0.24, 0.20],
                "notes": "Surface pit with loose aggregate gravel scatter."
            },
            {
                "time_sec": 27.5,
                "defect_id": "PATROL-105",
                "class_name": "alligator_crack",
                "severity": "High",
                "confidence": 0.923,
                "gps": {"latitude": 16.7082, "longitude": 74.2485},
                "zone": "Central Kolhapur",
                "area": "Rajarampuri",
                "street": "Rajarampuri 2nd Lane Main",
                "bbox_norm": [0.18, 0.52, 0.50, 0.34],
                "notes": "Heavy fatigue cracking indicating subgrade moisture ingress."
            }
        ]
    }

def get_local_lan_ip() -> str:
    """Detect the host machine's local Wi-Fi / Ethernet LAN IP for mobile connectivity."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

@app.get("/api/system/network_info")
def get_network_info():
    """Return local LAN IP and mobile HUD URL for phone camera pairing."""
    lan_ip = get_local_lan_ip()
    port = 8000
    mobile_url = f"http://{lan_ip}:{port}/mobile.html"
    return {
        "local_ip": lan_ip,
        "port": port,
        "mobile_hud_url": mobile_url,
        "ws_url": f"ws://{lan_ip}:{port}/ws/live_patrol"
    }

@app.websocket("/ws/live_patrol")
async def live_patrol_stream(websocket: WebSocket):
    """
    High-performance WebSocket endpoint for mobile camera streaming.
    Receives video frames (binary JPEG or base64 JSON), runs YOLO11 inference,
    auto-ingests high-confidence hazards into municipal SQLite/MongoDB, and returns bounding boxes.
    """
    await websocket.accept()
    detector = get_detector()
    last_saved_time = 0.0
    client_gps = {"latitude": 16.7050, "longitude": 74.2433}
    active_zone = "Central Kolhapur"
    patrol_vehicle_id = "PATROL-MOBILE-1"
    
    print("[LivePatrol] Mobile Camera HUD connected via WebSocket.")
    
    try:
        while True:
            message = await websocket.receive()
            frame = None
            
            # Handle text messages (telemetry or JSON base64 frames)
            if "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    msg_type = payload.get("type", "")
                    
                    if msg_type == "telemetry":
                        if "gps" in payload and payload["gps"]:
                            client_gps = payload["gps"]
                        if "zone" in payload and payload["zone"]:
                            active_zone = payload["zone"]
                        if "vehicle_id" in payload:
                            patrol_vehicle_id = payload["vehicle_id"]
                        continue
                    
                    elif "image" in payload:
                        # Base64 encoded JPEG
                        import base64
                        img_b64 = payload["image"]
                        if "," in img_b64:
                            img_b64 = img_b64.split(",", 1)[1]
                        raw_bytes = base64.b64decode(img_b64)
                        np_arr = np.frombuffer(raw_bytes, np.uint8)
                        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                        if "gps" in payload and payload["gps"]:
                            client_gps = payload["gps"]
                except Exception as e:
                    print(f"[LivePatrol] JSON parse error: {e}")
                    continue
                    
            # Handle binary JPEG frames (fastest)
            elif "bytes" in message and message["bytes"]:
                raw_bytes = message["bytes"]
                np_arr = np.frombuffer(raw_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
            if frame is None:
                continue

            t_start = time.time()
            # Execute YOLO11 inference
            result = detector.detect_frame(frame)
            latency = max(0.001, time.time() - t_start)
            fps = round(1.0 / latency, 1)

            # Auto-record defect if confidence is high and rate limit passed (at most once every 2.5s)
            recorded_id = None
            now = time.time()
            if result["num_detections"] > 0 and (now - last_saved_time) > 2.5:
                # Find the most severe detection with high confidence
                qualifying = [
                    d for d in result["detections"]
                    if d["confidence"] >= 0.60 and d["severity"] in ["Medium", "High"]
                ]
                if qualifying:
                    top_defect = qualifying[0]
                    defect_numeric_id = int(time.time() * 10) % 90000 + 10000
                    snapshot_filename = f"patrol_mobile_{defect_numeric_id}.jpg"
                    media_root = Path(__file__).resolve().parent.parent / "real_world_test"
                    media_root.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(media_root / snapshot_filename), frame)
                    
                    defect_dict = {
                        "defect_id": defect_numeric_id,
                        "class_name": top_defect["class_name"],
                        "severity": top_defect["severity"],
                        "confidence": top_defect["confidence"],
                        "status": "reported",
                        "timestamp": datetime.utcnow().isoformat(),
                        "gps": {
                            "latitude": float(client_gps.get("latitude", 16.7050)),
                            "longitude": float(client_gps.get("longitude", 74.2433))
                        },
                        "zone": active_zone,
                        "area": "Live Mobile Patrol Route",
                        "street": f"Patrol Stream ({patrol_vehicle_id})",
                        "bbox_norm": top_defect["box_norm"],
                        "assigned_contractor": "Kolhapur Rapid Pothole Response Team",
                        "notes": f"Auto-detected by Live Mobile Patrol Camera ({top_defect['class_name']} with {top_defect['severity']} severity)."
                    }
                    try:
                        insert_defects([defect_dict])
                        recorded_id = f"DEFECT-{defect_numeric_id}"
                        last_saved_time = now
                        print(f"[LivePatrol] Auto-logged road hazard: {recorded_id} at GPS {client_gps}")
                    except Exception as e:
                        print(f"[LivePatrol] Database insertion error: {e}")

            # Send response back to mobile client
            response_payload = {
                "status": "ok",
                "fps": fps,
                "latency_ms": round(latency * 1000, 1),
                "num_detections": result["num_detections"],
                "highest_severity": result["highest_severity"],
                "detections": result["detections"],
                "recorded_defect_id": recorded_id,
                "model": result["model_path"]
            }
            await websocket.send_json(response_payload)

    except WebSocketDisconnect:
        print("[LivePatrol] Mobile Camera HUD disconnected.")
    except Exception as e:
        print(f"[LivePatrol] Live stream error: {e}")

# Mount static files: real_world_test media, presentation deck, and frontend dashboard
root_dir = Path(__file__).resolve().parent.parent
presentation_dir = root_dir / "presentation"
frontend_dir = root_dir / "frontend"
media_dir = root_dir / "real_world_test"

if media_dir.exists():
    app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

if presentation_dir.exists():
    app.mount("/presentation", StaticFiles(directory=str(presentation_dir), html=True), name="presentation")

if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


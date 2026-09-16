import os
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from zones import resolve_zone_for_coordinates, load_zones_geojson


def load_env_file():
    search_paths = [
        Path(".env"),
        Path("backend/.env"),
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env"
    ]
    for env_path in search_paths:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

load_env_file()
MONGO_URI = os.getenv("MONGO_URI", "")
USE_MONGO = False
mongo_col = None

if MONGO_URI:
    try:
        from pymongo import MongoClient, GEOSPHERE
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.server_info()  # Test connection
        db = client["municipal_road_db"]
        mongo_col = db["defects"]
        mongo_col.create_index([("location", GEOSPHERE)])
        USE_MONGO = True
        print("[DATABASE] Successfully connected to MongoDB.")
    except Exception as e:
        print(f"[DATABASE] MongoDB connection unavailable ({e}). Falling back to persistent SQLite.")
        USE_MONGO = False
else:
    print("[DATABASE] No MONGO_URI specified. Operating with persistent local SQLite engine.")

# Local SQLite fallback setup
DB_FILE = Path(__file__).resolve().parent / "road_damage.db"

def init_sqlite():
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS defects (
            id TEXT PRIMARY KEY,
            defect_id INTEGER,
            class_name TEXT,
            severity TEXT,
            confidence REAL,
            status TEXT,
            created_at TEXT,
            updated_at TEXT,
            latitude REAL,
            longitude REAL,
            bbox_norm TEXT,
            assigned_contractor TEXT,
            notes TEXT,
            zone TEXT,
            area TEXT,
            street TEXT
        )
    """)
    # Auto-migrate existing database if columns don't exist
    for col in ["zone", "area", "street", "zone_id", "zone_name"]:
        try:
            cursor.execute(f"ALTER TABLE defects ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

init_sqlite()

def insert_defects(defect_list: List[Dict[str, Any]]) -> int:
    now_str = datetime.utcnow().isoformat()
    
    # Enrich every defect with Point-in-Polygon zone assignment
    for d in defect_list:
        gps = d.get("gps") or {}
        lat = gps.get("latitude") if isinstance(gps, dict) else d.get("latitude")
        lon = gps.get("longitude") if isinstance(gps, dict) else d.get("longitude")
        if lat is not None and lon is not None:
            resolved_id, resolved_name = resolve_zone_for_coordinates(float(lat), float(lon))
            d["zone_id"] = resolved_id
            d["zone_name"] = resolved_name
            d["zone"] = resolved_name
        else:
            if "zone_id" not in d:
                d["zone_id"] = None
            if "zone_name" not in d:
                d["zone_name"] = d.get("zone", "Outside Study Area")

    if USE_MONGO and mongo_col is not None:
        docs = []
        for d in defect_list:
            doc = dict(d)
            doc["_id"] = str(uuid.uuid4())
            doc["status"] = d.get("status", "reported")
            doc["created_at"] = d.get("timestamp", now_str)
            doc["updated_at"] = now_str
            doc["zone_id"] = d.get("zone_id")
            doc["zone_name"] = d.get("zone_name")
            doc["zone"] = d.get("zone_name") or d.get("zone", "Outside Study Area")
            doc["area"] = d.get("area", "")
            doc["street"] = d.get("street", "")
            if "gps" in d and isinstance(d["gps"], dict):
                doc["location"] = {
                    "type": "Point",
                    "coordinates": [d["gps"]["longitude"], d["gps"]["latitude"]]
                }
            docs.append(doc)
        res = mongo_col.insert_many(docs)
        return len(res.inserted_ids)
    else:
        conn = sqlite3.connect(str(DB_FILE))
        cursor = conn.cursor()
        count = 0
        for d in defect_list:
            rec_id = str(uuid.uuid4())
            did = d.get("defect_id", 0)
            if did:
                cursor.execute("DELETE FROM defects WHERE defect_id = ?", (did,))
            
            lat_val = d["gps"]["latitude"] if "gps" in d and isinstance(d["gps"], dict) else d.get("latitude", 0.0)
            lon_val = d["gps"]["longitude"] if "gps" in d and isinstance(d["gps"], dict) else d.get("longitude", 0.0)

            cursor.execute("""
                INSERT INTO defects (
                    id, defect_id, class_name, severity, confidence, status,
                    created_at, updated_at, latitude, longitude, bbox_norm,
                    assigned_contractor, notes, zone, area, street,
                    zone_id, zone_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec_id,
                d.get("defect_id", 0),
                d.get("class_name", "pothole"),
                d.get("severity", "Medium"),
                d.get("confidence", 0.0),
                d.get("status", "reported"),
                d.get("timestamp", now_str),
                now_str,
                lat_val,
                lon_val,
                json.dumps(d.get("bbox_norm", [])),
                d.get("assigned_contractor"),
                d.get("notes"),
                d.get("zone_name") or d.get("zone", "Outside Study Area"),
                d.get("area", ""),
                d.get("street", ""),
                d.get("zone_id"),
                d.get("zone_name")
            ))
            count += 1
        conn.commit()
        conn.close()
        return count

def query_defects(
    class_name: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    zone: Optional[str] = None,
    area: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    if USE_MONGO and mongo_col is not None:
        filt = {}
        if class_name:
            filt["class_name"] = class_name
        if severity:
            filt["severity"] = severity
        if status:
            filt["status"] = status
        if zone and zone.lower() != 'all':
            filt["$or"] = [
                {"zone": zone},
                {"zone_id": zone},
                {"zone_name": zone},
                {"zone_id": zone.lower().replace(" ", "_")}
            ]
        if area and area.lower() != 'all':
            filt["area"] = area
        docs = list(mongo_col.find(filt).limit(limit))
        for d in docs:
            d["id"] = str(d.pop("_id"))
            if "location" in d:
                coords = d["location"].get("coordinates", [0, 0])
                d["longitude"] = coords[0]
                d["latitude"] = coords[1]
        return docs
    else:
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM defects WHERE 1=1"
        params = []
        if class_name and isinstance(class_name, str):
            query += " AND class_name = ?"
            params.append(class_name)
        if severity and isinstance(severity, str):
            query += " AND severity = ?"
            params.append(severity)
        if status and isinstance(status, str):
            query += " AND status = ?"
            params.append(status)
        if zone and isinstance(zone, str) and zone.lower() != 'all':
            query += " AND (zone = ? OR zone_id = ? OR zone_name = ? OR zone_id = ?)"
            params.extend([zone, zone, zone, zone.lower().replace(" ", "_")])
        if area and isinstance(area, str) and area.lower() != 'all':
            query += " AND area = ?"
            params.append(area)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(int(limit) if isinstance(limit, (int, float)) else 100)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["bbox_norm"] = json.loads(d["bbox_norm"]) if d["bbox_norm"] else []
            results.append(d)
        conn.close()
        return results

def update_defect_status(defect_id: str, new_status: str, contractor: Optional[str] = None, notes: Optional[str] = None) -> bool:
    now_str = datetime.utcnow().isoformat()
    if USE_MONGO and mongo_col is not None:
        update_fields = {"status": new_status, "updated_at": now_str}
        if contractor:
            update_fields["assigned_contractor"] = contractor
        if notes:
            update_fields["notes"] = notes
        res = mongo_col.update_one({"_id": defect_id}, {"$set": update_fields})
        return res.modified_count > 0
    else:
        conn = sqlite3.connect(str(DB_FILE))
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE defects
            SET status = ?, assigned_contractor = COALESCE(?, assigned_contractor), notes = COALESCE(?, notes), updated_at = ?
            WHERE id = ?
        """, (new_status, contractor, notes, now_str, defect_id))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

def get_summary_statistics(zone: Optional[str] = None) -> Dict[str, Any]:
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()

    where_clause = ""
    params = []
    if zone and isinstance(zone, str) and zone.lower() != 'all':
        where_clause = " WHERE (zone = ? OR zone_id = ? OR zone_name = ? OR zone_id = ?)"
        params.extend([zone, zone, zone, zone.lower().replace(" ", "_")])

    cursor.execute(f"SELECT COUNT(*) FROM defects{where_clause}", params)
    total = cursor.fetchone()[0]

    pothole_clause = f" WHERE class_name = 'pothole' AND (zone = ? OR zone_id = ? OR zone_name = ? OR zone_id = ?)" if where_clause else " WHERE class_name = 'pothole'"
    cursor.execute(f"SELECT COUNT(*) FROM defects{pothole_clause}", params)
    potholes = cursor.fetchone()[0]

    crack_clause = f" WHERE class_name = 'alligator_crack' AND (zone = ? OR zone_id = ? OR zone_name = ? OR zone_id = ?)" if where_clause else " WHERE class_name = 'alligator_crack'"
    cursor.execute(f"SELECT COUNT(*) FROM defects{crack_clause}", params)
    alligator = cursor.fetchone()[0]

    high_clause = f" WHERE severity = 'High' AND (zone = ? OR zone_id = ? OR zone_name = ? OR zone_id = ?)" if where_clause else " WHERE severity = 'High'"
    cursor.execute(f"SELECT COUNT(*) FROM defects{high_clause}", params)
    high = cursor.fetchone()[0]

    med_clause = f" WHERE severity = 'Medium' AND (zone = ? OR zone_id = ? OR zone_name = ? OR zone_id = ?)" if where_clause else " WHERE severity = 'Medium'"
    cursor.execute(f"SELECT COUNT(*) FROM defects{med_clause}", params)
    medium = cursor.fetchone()[0]

    low_clause = f" WHERE severity = 'Low' AND (zone = ? OR zone_id = ? OR zone_name = ? OR zone_id = ?)" if where_clause else " WHERE severity = 'Low'"
    cursor.execute(f"SELECT COUNT(*) FROM defects{low_clause}", params)
    low = cursor.fetchone()[0]

    repaired_clause = f" WHERE status = 'repaired' AND (zone = ? OR zone_id = ? OR zone_name = ? OR zone_id = ?)" if where_clause else " WHERE status = 'repaired'"
    cursor.execute(f"SELECT COUNT(*) FROM defects{repaired_clause}", params)
    repaired = cursor.fetchone()[0]

    pending = total - repaired
    rate = (repaired / total * 100.0) if total > 0 else 0.0

    conn.close()
    return {
        "zone": zone if (zone and zone.lower() != 'all') else "All Kolhapur City",
        "total_defects": total,
        "total_potholes": potholes,
        "total_alligator_cracks": alligator,
        "high_priority_hazards": high,
        "medium_hazards": medium,
        "low_hazards": low,
        "repaired_count": repaired,
        "pending_count": pending,
        "repair_rate_percent": round(rate, 2)
    }

def get_zonewise_statistics() -> Dict[str, Any]:
    """
    Returns zone-wise counts for total incidents, potholes, alligator cracks,
    severity breakdown (High, Medium, Low), and status breakdown (reported, inspected, in_progress, repaired)
    for all 5 project-defined operational zones.
    """
    geojson_data = load_zones_geojson()
    features = geojson_data.get("features", [])
    
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    zones_result = {}
    
    for f in features:
        props = f.get("properties", {})
        zid = props.get("zone_id")
        zname = props.get("zone_name")
        
        cursor.execute(
            "SELECT * FROM defects WHERE zone_id = ? OR zone = ? OR zone_name = ?",
            (zid, zname, zname)
        )
        rows = cursor.fetchall()
        
        total = len(rows)
        potholes = sum(1 for r in rows if r["class_name"] == "pothole")
        alligators = sum(1 for r in rows if r["class_name"] == "alligator_crack")
        
        sev_counts = {"High": 0, "Medium": 0, "Low": 0}
        status_counts = {"reported": 0, "inspected": 0, "in_progress": 0, "repaired": 0}
        
        for r in rows:
            sev = r["severity"]
            if sev in sev_counts:
                sev_counts[sev] += 1
            st = r["status"]
            if st in status_counts:
                status_counts[st] += 1
                
        zones_result[zid] = {
            "zone_id": zid,
            "zone_name": zname,
            "center": props.get("center", []),
            "localities": props.get("localities", []),
            "challenges": props.get("challenges", ""),
            "color": props.get("color", "#3b82f6"),
            "total_incidents": total,
            "potholes": potholes,
            "alligator_cracks": alligators,
            "severity": sev_counts,
            "status": status_counts
        }
        
    # Count defects outside the study area
    cursor.execute("""
        SELECT COUNT(*) FROM defects 
        WHERE zone_id IS NULL OR zone_name = 'Outside Study Area' OR zone = 'Outside Study Area'
    """)
    outside_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "case_study": "KOLHAPUR 5-ZONE OPERATIONAL ROAD-DAMAGE MAP",
        "subtitle": "Project-defined operational zones for regional case-study analysis.",
        "disclaimer": "IMPORTANT: These are PROJECT-DEFINED OPERATIONAL ZONES for academic/case-study analysis, NOT official Kolhapur Municipal Corporation (KMC) legal ward boundaries.",
        "zones": zones_result,
        "outside_study_area_count": outside_count
    }


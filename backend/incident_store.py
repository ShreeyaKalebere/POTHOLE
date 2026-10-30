"""Saving detections as incidents - shared by photo upload, live patrol and video processing."""
from datetime import datetime

from config import DEDUP_RADIUS_M
from db import incidents, next_incident_code
from severity import SEVERITY_RANK
from zones import zone_for


def upsert_incident(det, lat, lng, image_url, annotated_url, source, now):
    """Creates a new incident, or merges into an open one of the same type within DEDUP_RADIUS_M."""
    img_entry = {"url": image_url, "annotated_url": annotated_url, "bbox": det["bbox"],
                 "confidence": det["confidence"], "severity": det["severity"], "at": now}
    if lat is not None:
        existing = incidents.find_one({
            "damage_type": det["damage_type"], "status": {"$ne": "Repaired"},
            "location": {"$near": {"$geometry": {"type": "Point", "coordinates": [lng, lat]},
                                   "$maxDistance": DEDUP_RADIUS_M}}})
        if existing:
            upd = {"$inc": {"reports_count": 1}, "$push": {"images": img_entry},
                   "$set": {"updated_at": now, "confidence": max(existing["confidence"], det["confidence"])}}
            if SEVERITY_RANK[det["severity"]] > SEVERITY_RANK[existing["severity"]]:
                upd["$set"].update(severity=det["severity"], severity_score=det["severity_score"])
            upd["$push"]["history"] = {"at": now, "status": existing["status"], "by": "system",
                                       "note": f"Detected again ({det['severity']}, conf {det['confidence']})"}
            incidents.update_one({"_id": existing["_id"]}, upd)
            return str(existing["_id"]), False

    doc = {
        "incident_code": next_incident_code(), "damage_type": det["damage_type"],
        "severity": det["severity"], "severity_score": det["severity_score"],
        "confidence": det["confidence"],
        "location": {"type": "Point", "coordinates": [lng, lat]} if lat is not None else None,
        "zone": zone_for(lat, lng), "status": "Reported", "assigned_to": None,
        "reports_count": 1, "source": source, "images": [img_entry],
        "detected_at": now, "updated_at": now, "demo": False,
        "history": [{"at": now, "status": "Reported", "by": "system", "note": f"Detected via {source}"}],
    }
    if doc["location"] is None:
        del doc["location"]          # 2dsphere index rejects null geometry
    return str(incidents.insert_one(doc).inserted_id), True

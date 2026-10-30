"""
FastAPI backend - Road Damage & Municipal Reporting System.
Run (from the backend folder):  uvicorn main:app --reload --port 8000
API docs:                       http://localhost:8000/docs
"""
import threading
import uuid
from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
import os
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import auth
import media_store
from config import DASHBOARD_DIST, SESSION_DAYS, STATUSES, SEVERITIES
from db import incidents, init_indexes, next_incident_code, client
from detector import detector
from gps import exif_gps
from incident_store import upsert_incident
import live
import cv2
import numpy as np
from fastapi.concurrency import run_in_threadpool
from reports import to_csv, to_pdf
from severity import SEVERITY_RANK
from zones import ZONES, CITY_CENTER, zone_for

app = FastAPI(title="Road Damage & Municipal Reporting API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.middleware("http")(auth.middleware)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_UPLOAD_MB = 20


@app.on_event("startup")
def startup():
    init_indexes()

    def _load():
        try:
            detector.load()
        except Exception as e:
            print("Model not loaded yet:", e)
    threading.Thread(target=_load, daemon=True).start()   # don't block server start


# ------------------------------------------------------------------ helpers
def serialize(inc):
    inc = dict(inc)
    inc["id"] = str(inc.pop("_id"))
    lng, lat = (inc.get("location") or {}).get("coordinates", [None, None])
    inc["lat"], inc["lng"] = lat, lng
    for k in ("detected_at", "updated_at"):
        if isinstance(inc.get(k), datetime):
            inc[k] = inc[k].isoformat()
    for h in inc.get("history", []):
        if isinstance(h.get("at"), datetime):
            h["at"] = h["at"].isoformat()
    for im in inc.get("images", []):
        if isinstance(im.get("at"), datetime):
            im["at"] = im["at"].isoformat()
    return inc


def build_filter(damage_type=None, severity=None, status=None, zone=None,
                 date_from=None, date_to=None, include_demo=True):
    q = {}
    if damage_type:
        q["damage_type"] = {"$in": damage_type.split(",")}
    if severity:
        q["severity"] = {"$in": severity.split(",")}
    if status:
        q["status"] = {"$in": status.split(",")}
    if zone and zone != "All":
        q["zone"] = zone
    if date_from or date_to:
        q["detected_at"] = {}
        if date_from:
            q["detected_at"]["$gte"] = datetime.fromisoformat(date_from)
        if date_to:
            q["detected_at"]["$lt"] = datetime.fromisoformat(date_to) + timedelta(days=1)
    if not include_demo:
        q["demo"] = {"$ne": True}
    return q


def oid(id_):
    try:
        return ObjectId(id_)
    except Exception:
        raise HTTPException(404, "Incident not found")


# ------------------------------------------------------------------ login
class LoginBody(BaseModel):
    password: str


@app.get("/api/me")
def me(request: Request):
    return {"auth_required": auth.enabled(), "logged_in": auth.is_logged_in(request)}


@app.post("/api/login")
def login(body: LoginBody, request: Request, response: Response):
    if not auth.enabled():
        return {"ok": True}
    if not auth.password_ok(body.password):
        raise HTTPException(401, "Wrong password")
    response.set_cookie(auth.COOKIE, auth.make_token(), max_age=SESSION_DAYS * 86400,
                        httponly=True, samesite="lax", secure=auth.is_https(request))
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(auth.COOKIE)
    return {"ok": True}


@app.get("/media/{name:path}")
def media(name: str):
    got = media_store.read(name)
    if got is None:
        raise HTTPException(404, "Not found")
    data, ctype = got
    return Response(data, media_type=ctype, headers={"Cache-Control": "private, max-age=86400"})


# ------------------------------------------------------------------ routes
@app.get("/api/health")
def health():
    try:
        client.admin.command("ping")
        mongo = True
    except Exception:
        mongo = False
    return {"api": True, "mongo": mongo, "model": detector.info(),
            "live_sessions": len(live.active_sessions())}


@app.post("/api/model/reload")
def reload_model():
    """Call this after training finishes to switch to the newest weights."""
    try:
        return detector.load()
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@app.get("/api/zones")
def get_zones():
    return {"center": CITY_CENTER,
            "zones": [{"name": n, "lat": la, "lng": lo} for n, (la, lo) in ZONES.items()]}


@app.post("/api/detect")
async def detect(file: UploadFile = File(...), lat: Optional[float] = Form(None),
                 lng: Optional[float] = Form(None), source: str = Form("upload"),
                 save: bool = Form(True)):
    """Upload a road photo -> detections + annotated image; saved as incidents if save=True."""
    ext = "." + (file.filename or "x.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Unsupported file type {ext}")
    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Image larger than {MAX_UPLOAD_MB} MB")

    now = datetime.now()
    name = f"{now:%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}"
    fd, tmp = tempfile.mkstemp(suffix=ext)
    try:
        os.write(fd, data)
        os.close(fd)
        gps_source = "form"
        if lat is None or lng is None:
            lat, lng = exif_gps(tmp)
            gps_source = "photo EXIF" if lat is not None else "none"
        try:
            dets, img, ms = detector.detect(tmp)
        except RuntimeError as e:
            raise HTTPException(503, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))
    finally:
        os.unlink(tmp)

    image_url = media_store.save_image(f"{name}.jpg", img)
    ann_url = media_store.save_image(f"{name}_det.jpg", detector.draw(img, dets))

    results = []
    for d in dets:
        inc_id, is_new = (upsert_incident(d, lat, lng, image_url, ann_url, source, now)
                          if save else (None, None))
        results.append({**d, "incident_id": inc_id, "new_incident": is_new})
    return {"detections": results, "count": len(results), "inference_ms": ms,
            "image_url": image_url, "annotated_url": ann_url,
            "lat": lat, "lng": lng, "gps_source": gps_source,
            "zone": zone_for(lat, lng), "model": detector.info()}


@app.get("/api/incidents")
def list_incidents(damage_type: Optional[str] = None, severity: Optional[str] = None,
                   status: Optional[str] = None, zone: Optional[str] = None,
                   date_from: Optional[str] = None, date_to: Optional[str] = None,
                   sort: str = "priority", limit: int = Query(500, le=5000), skip: int = 0):
    q = build_filter(damage_type, severity, status, zone, date_from, date_to)
    items = list(incidents.find(q, {"history": 0}).sort("detected_at", -1).skip(skip).limit(limit))
    if sort == "priority":   # open + high severity + many reports first
        items.sort(key=lambda i: (i["status"] == "Repaired", -SEVERITY_RANK[i["severity"]],
                                  -i.get("reports_count", 1)))
    return {"total": incidents.count_documents(q), "items": [serialize(i) for i in items]}


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    inc = incidents.find_one({"_id": oid(incident_id)})
    if not inc:
        raise HTTPException(404, "Incident not found")
    return serialize(inc)


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    severity: Optional[str] = None
    note: Optional[str] = None
    by: str = "officer"


@app.patch("/api/incidents/{incident_id}")
def update_incident(incident_id: str, body: IncidentUpdate):
    inc = incidents.find_one({"_id": oid(incident_id)})
    if not inc:
        raise HTTPException(404, "Incident not found")
    s = {"updated_at": datetime.now()}
    notes = []
    if body.status:
        if body.status not in STATUSES:
            raise HTTPException(400, f"status must be one of {STATUSES}")
        s["status"] = body.status
        notes.append(f"Status: {inc['status']} -> {body.status}")
    if body.severity:
        if body.severity not in SEVERITIES:
            raise HTTPException(400, f"severity must be one of {SEVERITIES}")
        s["severity"] = body.severity
        notes.append(f"Severity set to {body.severity} (manual)")
    if body.assigned_to is not None:
        s["assigned_to"] = body.assigned_to or None
        notes.append(f"Assigned to {body.assigned_to or 'nobody'}")
    if body.note:
        notes.append(body.note)
    hist = {"at": s["updated_at"], "status": s.get("status", inc["status"]), "by": body.by,
            "note": " | ".join(notes) or "Updated"}
    incidents.update_one({"_id": inc["_id"]}, {"$set": s, "$push": {"history": hist}})
    return serialize(incidents.find_one({"_id": inc["_id"]}))


@app.delete("/api/incidents/{incident_id}")
def delete_incident(incident_id: str):
    """Permanently removes one incident and its photos (e.g. a false detection)."""
    inc = incidents.find_one({"_id": oid(incident_id)})
    if not inc:
        raise HTTPException(404, "Incident not found")
    # a photo can be shared with other incidents found in the same frame - only delete unused ones
    for im in inc.get("images", []):
        for url in (im.get("url"), im.get("annotated_url")):
            if url and not incidents.count_documents({"_id": {"$ne": inc["_id"]},
                                                      "$or": [{"images.url": url}, {"images.annotated_url": url}]}):
                media_store.delete(url)
    incidents.delete_one({"_id": inc["_id"]})
    return {"deleted": inc["incident_code"]}


@app.get("/api/stats")
def stats(zone: Optional[str] = None, days: int = 30):
    q = build_filter(zone=zone)

    def count_by(field):
        return {r["_id"]: r["n"] for r in incidents.aggregate(
            [{"$match": q}, {"$group": {"_id": f"${field}", "n": {"$sum": 1}}}])}

    since = datetime.now() - timedelta(days=days - 1)
    trend_raw = incidents.aggregate([
        {"$match": {**q, "detected_at": {"$gte": since.replace(hour=0, minute=0, second=0)}}},
        {"$group": {"_id": {"d": {"$dateToString": {"format": "%Y-%m-%d", "date": "$detected_at"}},
                            "t": "$damage_type"}, "n": {"$sum": 1}}}])
    trend = {}
    for r in trend_raw:
        trend.setdefault(r["_id"]["d"], {})[r["_id"]["t"]] = r["n"]
    days_list = [(since + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    open_q = {**q, "status": {"$ne": "Repaired"}}
    return {
        "total": incidents.count_documents(q),
        "open": incidents.count_documents(open_q),
        "high_open": incidents.count_documents({**open_q, "severity": "High"}),
        "repaired": incidents.count_documents({**q, "status": "Repaired"}),
        "by_type": count_by("damage_type"), "by_severity": count_by("severity"),
        "by_status": count_by("status"), "by_zone": count_by("zone"),
        "trend": [{"date": d, "pothole": trend.get(d, {}).get("pothole", 0),
                   "alligator_crack": trend.get(d, {}).get("alligator_crack", 0)} for d in days_list],
    }


def _export_items(**f):
    items = list(incidents.find(build_filter(**f)))
    items.sort(key=lambda i: (i["status"] == "Repaired", -SEVERITY_RANK[i["severity"]], i["detected_at"]))
    return items


@app.get("/api/export/csv")
def export_csv(damage_type: Optional[str] = None, severity: Optional[str] = None,
               status: Optional[str] = None, zone: Optional[str] = None,
               date_from: Optional[str] = None, date_to: Optional[str] = None):
    items = _export_items(damage_type=damage_type, severity=severity, status=status, zone=zone,
                          date_from=date_from, date_to=date_to)
    return Response(to_csv(items), media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=road_damage_{datetime.now():%Y%m%d}.csv"})


@app.get("/api/export/pdf")
def export_pdf(damage_type: Optional[str] = None, severity: Optional[str] = None,
               status: Optional[str] = None, zone: Optional[str] = None,
               date_from: Optional[str] = None, date_to: Optional[str] = None):
    f = dict(damage_type=damage_type, severity=severity, status=status, zone=zone,
             date_from=date_from, date_to=date_to)
    items = _export_items(**f)
    st = {"total": len(items), "by_type": {}, "by_severity": {}, "by_status": {}}
    for i in items:
        for k, fld in (("by_type", "damage_type"), ("by_severity", "severity"), ("by_status", "status")):
            st[k][i[fld]] = st[k].get(i[fld], 0) + 1
    ftxt = ", ".join(f"{k}={v}" for k, v in f.items() if v) or "none (all incidents)"
    return Response(to_pdf(items, st, ftxt), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=road_damage_{datetime.now():%Y%m%d}.pdf"})


# ------------------------------------------------------------------ live patrol (phone camera)
@app.post("/api/live/start")
def live_start():
    try:
        s = live.start_session()
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    return s.summary()


@app.post("/api/live/frame")
async def live_frame(session_id: str = Form(...), file: UploadFile = File(...),
                     lat: Optional[float] = Form(None), lng: Optional[float] = Form(None),
                     save: bool = Form(True)):
    s = live.get_session(session_id)
    if s is None:
        raise HTTPException(404, "Live session expired - press Start again")
    data = await file.read()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Bad frame")
    # tracking is CPU/GPU work - run it off the event loop
    dets, new = await run_in_threadpool(s.process, img, lat, lng, save)
    return {"detections": dets, "new_incidents": new, "frame_size": [img.shape[1], img.shape[0]],
            "zone": zone_for(lat, lng), **s.summary()}


@app.post("/api/live/stop")
def live_stop(session_id: str = Form(...)):
    s = live.stop_session(session_id)
    return s.summary() if s else {"session_id": session_id, "stopped": True}


@app.get("/api/live/sessions")
def live_sessions():
    return {"sessions": live.active_sessions()}


# ------------------------------------------------------------------ demo data
@app.post("/api/demo/seed")
def demo_seed(n: int = 120):
    from seed_demo import seed
    return {"inserted": seed(n)}


@app.delete("/api/demo")
def demo_clear():
    return {"deleted": incidents.delete_many({"demo": True}).deleted_count}


# ------------------------------------------------------------------ dashboard (built React app)
# When dashboard/dist exists (npm run build, or inside Docker), the backend also serves the
# dashboard, so the whole system runs on one address. Unknown paths return index.html so
# React's page links (/map, /live, ...) work when opened directly.
if DASHBOARD_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DASHBOARD_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = (DASHBOARD_DIST / path).resolve()
        if path and DASHBOARD_DIST.resolve() in f.parents and f.is_file():
            return FileResponse(f)
        return FileResponse(DASHBOARD_DIST / "index.html")

"""Routes behind the four panels: citizen, repair team, ward officer approvals, admin accounts."""
import os
import secrets
import string
import tempfile
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

import accounts
import auth
import media_store
from db import incidents
from detector import detector
from gps import exif_gps
from incident_store import upsert_incident
from zones import zone_for

router = APIRouter()

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_PUBLIC_UPLOAD_MB = 12
PUBLIC_REPORTS_PER_HOUR = 10
LOGIN_FAILURES_ALLOWED = 8
LOGIN_WINDOW_S = 900
TRACK_ALPHABET = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"
UNREVIEWED_DET = {"severity": "Low", "severity_score": 0.0, "confidence": 0.0, "bbox": []}

_report_times = defaultdict(deque)
_login_failures = defaultdict(deque)


def _recent(times, window_s):
    now = time.time()
    while times and now - times[0] > window_s:
        times.popleft()
    return times


def login_blocked(request, username):
    return len(_recent(_login_failures[(auth.client_ip(request), username)], LOGIN_WINDOW_S)) >= LOGIN_FAILURES_ALLOWED


def login_failed(request, username):
    _login_failures[(auth.client_ip(request), username)].append(time.time())


def login_succeeded(request, username):
    _login_failures.pop((auth.client_ip(request), username), None)


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _oid(id_):
    try:
        return ObjectId(id_)
    except Exception:
        raise HTTPException(404, "Not found")


def _load_in_scope(request, incident_id):
    inc = incidents.find_one({"_id": _oid(incident_id)})
    if not inc or not auth.in_scope(request.state.user, inc):
        raise HTTPException(404, "Incident not found")
    return inc


async def _read_photo(file: UploadFile, max_mb):
    ext = "." + (file.filename or "x.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Please choose a JPG, PNG, WEBP or BMP photo")
    data = await file.read()
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"Photo is larger than {max_mb} MB")
    return ext, data


def _analyse(ext, data):
    """Runs detection on uploaded bytes. Returns (detections, image, gps from the photo)."""
    fd, tmp = tempfile.mkstemp(suffix=ext)
    try:
        os.write(fd, data)
        os.close(fd)
        gps = exif_gps(tmp)
        try:
            dets, img, _ = detector.detect(tmp)
        except RuntimeError:
            raise HTTPException(503, "The detection model is still starting. Please try again in a minute.")
        except ValueError:
            raise HTTPException(400, "This file could not be read as a photo")
    finally:
        os.unlink(tmp)
    return dets, img, gps


# ------------------------------------------------------------------ citizen (no login)
@router.post("/api/public/report")
async def citizen_report(request: Request, file: UploadFile = File(...), lat: Optional[float] = Form(None),
                         lng: Optional[float] = Form(None), kind: str = Form("pothole"), note: str = Form("")):
    times = _recent(_report_times[auth.client_ip(request)], 3600)
    if len(times) >= PUBLIC_REPORTS_PER_HOUR:
        raise HTTPException(429, "Too many reports from this connection. Please try again in an hour.")
    if kind not in ("pothole", "alligator_crack"):
        raise HTTPException(400, "Choose pothole or road cracks")
    ext, data = await _read_photo(file, MAX_PUBLIC_UPLOAD_MB)
    dets, img, photo_gps = await run_in_threadpool(_analyse, ext, data)
    if lat is None or lng is None:
        lat, lng = photo_gps
    if lat is None or lng is None:
        raise HTTPException(400, "Please mark the location on the map, so the right ward receives your report")
    zone = zone_for(lat, lng)
    if zone == "Outside City":
        raise HTTPException(400, "This location is outside the area MargDrishti covers")

    times.append(time.time())
    now = datetime.now()
    name = f"citizen/{now:%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}"
    image_url = media_store.save_image(f"{name}.jpg", img)
    ann_url = media_store.save_image(f"{name}_det.jpg", detector.draw(img, dets))
    incident_ids = []
    for d in dets:
        inc_id, _ = upsert_incident(d, lat, lng, image_url, ann_url, "citizen", now)
        incident_ids.append(inc_id)
    if not dets:
        # the model misses real damage, so a citizen's report is never thrown away: an officer checks it
        inc_id, is_new = upsert_incident({**UNREVIEWED_DET, "damage_type": kind}, lat, lng, image_url, ann_url, "citizen", now)
        incident_ids.append(inc_id)
        if is_new:
            incidents.update_one({"_id": ObjectId(inc_id)}, {"$set": {"needs_review": True}})
    code = "MD-" + "".join(secrets.choice(TRACK_ALPHABET) for _ in range(8))
    accounts.reports.insert_one({"code": code, "incident_ids": incident_ids, "note": note.strip()[:300],
                                 "zone": zone, "created_at": now})
    for inc_id in incident_ids:
        if note.strip():
            incidents.update_one({"_id": ObjectId(inc_id)}, {"$push": {"history": {
                "at": now, "status": "Reported", "by": "Citizen", "note": note.strip()[:300]}}})
    accounts.log_activity("Citizen", "Submitted a report", None, f"{code} in {zone}")
    return {"code": code, "zone": zone, "ai_found": len(dets)}


@router.get("/api/public/track/{code}")
def citizen_track(code: str):
    report = accounts.reports.find_one({"code": code.strip().upper()})
    if not report:
        raise HTTPException(404, "No report found with this tracking number")
    items = []
    for inc in incidents.find({"_id": {"$in": [ObjectId(i) for i in report["incident_ids"]]}}):
        steps, last = [], None
        for h in inc.get("history", []):
            if h.get("status") != last:
                steps.append({"at": _iso(h["at"]), "status": h["status"]})
                last = h["status"]
        items.append({"type": inc["damage_type"], "status": inc["status"], "updated_at": _iso(inc["updated_at"]),
                      "needs_review": inc.get("needs_review", False), "steps": steps})
    return {"code": report["code"], "submitted_at": _iso(report["created_at"]), "zone": report["zone"], "items": items}


# ------------------------------------------------------------------ repair team
def _job(inc):
    return {
        "id": str(inc["_id"]), "incident_code": inc["incident_code"], "damage_type": inc["damage_type"],
        "severity": inc["severity"], "status": inc["status"], "zone": inc.get("zone"),
        "lat": ((inc.get("location") or {}).get("coordinates") or [None, None])[1],
        "lng": ((inc.get("location") or {}).get("coordinates") or [None, None])[0],
        "photo": (inc.get("images") or [{}])[-1].get("annotated_url"),
        "repair": _repair_json(inc.get("repair")), "updated_at": _iso(inc.get("updated_at")),
    }


def _repair_json(repair):
    if not repair:
        return None
    return {**repair, "at": _iso(repair.get("at")), "decided_at": _iso(repair.get("decided_at"))}


@router.get("/api/jobs")
def my_jobs(request: Request):
    user = auth.require_role(request, "repair_team")
    items = list(incidents.find({"assigned_to": user["team"]}).sort("updated_at", -1).limit(300))
    rank = {"In Progress": 0, "Reported": 1, "Repaired": 2}
    items.sort(key=lambda i: rank.get(i["status"], 3))
    return {"team": user["team"], "items": [_job(i) for i in items]}


@router.post("/api/jobs/{incident_id}/start")
def start_job(incident_id: str, request: Request):
    user = auth.require_role(request, "repair_team")
    inc = _load_in_scope(request, incident_id)
    if inc["status"] != "Reported":
        raise HTTPException(409, "This job has already been started")
    now = datetime.now()
    who = auth.signature_of(user)
    incidents.update_one({"_id": inc["_id"]}, {"$set": {"status": "In Progress", "updated_at": now}, "$push": {
        "history": {"at": now, "status": "In Progress", "by": who, "note": "Repair work started"}}})
    accounts.log_activity(who, "Started repair", inc["incident_code"])
    return _job(incidents.find_one({"_id": inc["_id"]}))


@router.post("/api/jobs/{incident_id}/complete")
async def complete_job(incident_id: str, request: Request, file: UploadFile = File(...), note: str = Form("")):
    user = auth.require_role(request, "repair_team")
    inc = _load_in_scope(request, incident_id)
    if inc["status"] == "Repaired":
        raise HTTPException(409, "This job is already approved as repaired")
    if (inc.get("repair") or {}).get("state") == "pending":
        raise HTTPException(409, "This repair is already waiting for approval")
    ext, data = await _read_photo(file, 20)
    dets, img, _ = await run_in_threadpool(_analyse, ext, data)
    now = datetime.now()
    name = f"repairs/{inc['incident_code']}_{now:%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    photo_url = media_store.save_image(f"{name}.jpg", img)
    ann_url = media_store.save_image(f"{name}_det.jpg", detector.draw(img, dets))
    who = auth.signature_of(user)
    repair = {"state": "pending", "photo_url": photo_url, "annotated_url": ann_url, "note": note.strip()[:300],
              "by": who, "at": now, "ai_damage_found": len(dets)}
    ai_text = f"AI still sees {len(dets)} damaged area(s)" if dets else "AI sees no damage"
    incidents.update_one({"_id": inc["_id"]}, {"$set": {"repair": repair, "status": "In Progress", "updated_at": now},
                                               "$push": {"history": {"at": now, "status": "In Progress", "by": who,
                                                                     "note": f"Repair photo submitted. {ai_text}."}}})
    accounts.log_activity(who, "Submitted repair for approval", inc["incident_code"], ai_text)
    return _job(incidents.find_one({"_id": inc["_id"]}))


# ------------------------------------------------------------------ repair approval (officer, admin)
class Decision(BaseModel):
    approve: bool
    note: str = ""


@router.get("/api/approvals")
def pending_approvals(request: Request):
    user = auth.require_role(request, "admin", "ward_officer")
    q = auth.scope(user, {"repair.state": "pending", "status": {"$ne": "Repaired"}})
    return {"items": [{**_job(i), "assigned_to": i.get("assigned_to"),
                       "before_photo": (i.get("images") or [{}])[-1].get("annotated_url")}
                      for i in incidents.find(q).sort("updated_at", 1).limit(200)]}


@router.post("/api/incidents/{incident_id}/repair/decision")
def decide_repair(incident_id: str, body: Decision, request: Request):
    user = auth.require_role(request, "admin", "ward_officer")
    inc = _load_in_scope(request, incident_id)
    if (inc.get("repair") or {}).get("state") != "pending":
        raise HTTPException(409, "No repair is waiting for approval here")
    if not body.approve and not body.note.strip():
        raise HTTPException(400, "Please say why the repair was rejected, so the team can fix it")
    now = datetime.now()
    who = auth.signature_of(user)
    status = "Repaired" if body.approve else "In Progress"
    text = "Repair approved" if body.approve else "Repair rejected"
    note = body.note.strip()[:300]
    incidents.update_one({"_id": inc["_id"]}, {
        "$set": {"status": status, "updated_at": now, "repair.state": "approved" if body.approve else "rejected",
                 "repair.decided_by": who, "repair.decided_at": now, "repair.decision_note": note},
        "$push": {"history": {"at": now, "status": status, "by": who, "note": f"{text}. {note}".strip()}}})
    accounts.log_activity(who, text, inc["incident_code"], note)
    return {"status": status}


@router.get("/api/teams")
def teams(request: Request):
    auth.require_role(request, "admin", "ward_officer")
    names = accounts.users.distinct("team", {"role": "repair_team", "active": True})
    return {"teams": sorted(n for n in names if n)}


# ------------------------------------------------------------------ own account
class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@router.post("/api/me/password")
def change_password(body: PasswordChange, request: Request):
    user = request.state.user
    if not accounts.password_matches(body.current_password, user["password_hash"]):
        raise HTTPException(400, "Your current password is not correct")
    if len(body.new_password) < accounts.MIN_PASSWORD:
        raise HTTPException(400, f"New password needs at least {accounts.MIN_PASSWORD} characters")
    accounts.users.update_one({"_id": user["_id"]}, {"$set": {"password_hash": accounts.hash_password(body.new_password)}})
    accounts.log_activity(auth.signature_of(user), "Changed own password")
    return {"ok": True, "login_again": True}


# ------------------------------------------------------------------ admin: accounts and activity
class NewUser(BaseModel):
    username: str
    password: str
    role: str
    name: str = ""
    ward: Optional[str] = None
    team: Optional[str] = None


class UserChange(BaseModel):
    name: Optional[str] = None
    ward: Optional[str] = None
    team: Optional[str] = None
    active: Optional[bool] = None
    password: Optional[str] = None


@router.get("/api/users")
def list_users(request: Request):
    auth.require_role(request, "admin")
    return {"items": [accounts.public_user(u) for u in accounts.users.find().sort("username", 1)]}


@router.post("/api/users")
def add_user(body: NewUser, request: Request):
    admin = auth.require_role(request, "admin")
    username = body.username.strip().lower()
    problem = accounts.validate_new_user(username, body.password, body.role, body.ward, body.team)
    if problem:
        raise HTTPException(400, problem)
    if accounts.users.find_one({"username": username}):
        raise HTTPException(409, "That username is already taken")
    user = accounts.create_user(username, body.password, body.role, body.name.strip(), body.ward, (body.team or "").strip() or None)
    accounts.log_activity(auth.signature_of(admin), "Created account", None, f"{username} ({body.role})")
    return accounts.public_user(user)


@router.patch("/api/users/{user_id}")
def change_user(user_id: str, body: UserChange, request: Request):
    admin = auth.require_role(request, "admin")
    user = accounts.users.find_one({"_id": _oid(user_id)})
    if not user:
        raise HTTPException(404, "Account not found")
    changes, notes = {}, []
    if body.name is not None:
        changes["name"] = body.name.strip() or user["username"]
    if body.ward is not None or body.team is not None:
        ward = body.ward if body.ward is not None else user.get("ward")
        team = (body.team or "").strip() or None if body.team is not None else user.get("team")
        problem = accounts.validate_scope(user["role"], ward, team)
        if problem:
            raise HTTPException(400, problem)
        changes.update(ward=ward if user["role"] == "ward_officer" else None,
                       team=team if user["role"] == "repair_team" else None)
    if body.active is not None and body.active != user.get("active", True):
        if not body.active:
            if user["_id"] == admin["_id"]:
                raise HTTPException(400, "You cannot deactivate your own account")
            if user["role"] == "admin" and accounts.users.count_documents({"role": "admin", "active": True}) <= 1:
                raise HTTPException(400, "At least one admin account must stay active")
        changes["active"] = body.active
        notes.append("Activated" if body.active else "Deactivated")
    if body.password:
        if len(body.password) < accounts.MIN_PASSWORD:
            raise HTTPException(400, f"Password needs at least {accounts.MIN_PASSWORD} characters")
        changes["password_hash"] = accounts.hash_password(body.password)
        notes.append("Password reset")
    if changes:
        accounts.users.update_one({"_id": user["_id"]}, {"$set": changes})
        accounts.log_activity(auth.signature_of(admin), "Changed account", None,
                              f"{user['username']}: {', '.join(notes) or 'details updated'}")
    return accounts.public_user(accounts.users.find_one({"_id": user["_id"]}))


@router.get("/api/activity")
def recent_activity(request: Request, limit: int = 100):
    auth.require_role(request, "admin")
    rows = accounts.activity.find({}, {"_id": 0}).sort("at", -1).limit(min(limit, 500))
    return {"items": [{**r, "at": _iso(r["at"])} for r in rows]}

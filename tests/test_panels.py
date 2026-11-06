"""Tests that each role can reach only what it should. Uses a throwaway database, which it deletes.
Run (from the project folder):  python -m pytest tests/test_panels.py -q
"""
import io
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ["DB_NAME"] = "margdrishti_pytest"
os.environ["MEDIA_BACKEND"] = "gridfs"
os.environ.pop("APP_PASSWORD", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

import accounts
import main
from db import client, db, incidents, init_indexes
from detector import detector

PASSWORD = "test-password-1"
DET = {"damage_type": "pothole", "severity": "High", "severity_score": 0.5, "confidence": 0.9, "bbox": [1, 1, 5, 5]}
found = {"dets": [DET]}


def photo():
    ok, buf = cv2.imencode(".jpg", np.full((40, 40, 3), 120, np.uint8))
    assert ok
    return {"file": ("road.jpg", io.BytesIO(buf.tobytes()), "image/jpeg")}


def incident(code, zone="Shahupuri", assigned_to=None, status="Reported"):
    now = datetime.now()
    return str(incidents.insert_one({
        "incident_code": code, "damage_type": "pothole", "severity": "High", "severity_score": 0.5, "confidence": 0.9,
        "location": {"type": "Point", "coordinates": [74.24, 16.70]}, "zone": zone, "status": status,
        "assigned_to": assigned_to, "reports_count": 1, "source": "test",
        "images": [{"url": "/media/a.jpg", "annotated_url": "/media/a_det.jpg", "at": now}],
        "detected_at": now, "updated_at": now, "demo": False,
        "history": [{"at": now, "status": status, "by": "system", "note": "test"}]}).inserted_id)


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    client.drop_database(db.name)
    init_indexes()
    accounts.init_accounts()
    accounts.create_user("boss", PASSWORD, "admin", "Boss")
    accounts.create_user("shahu", PASSWORD, "ward_officer", "Shahu", ward="Shahupuri")
    accounts.create_user("raja", PASSWORD, "ward_officer", "Raja", ward="Rajarampuri")
    accounts.create_user("unit1", PASSWORD, "repair_team", "Unit 1", team="Unit 1")
    accounts.create_user("unit2", PASSWORD, "repair_team", "Unit 2", team="Unit 2")
    monkeypatch.setattr(detector, "detect", lambda path, conf=None: (found["dets"], np.full((40, 40, 3), 120, np.uint8), 1.0))
    monkeypatch.setattr(detector, "draw", lambda img, dets: img)
    found["dets"] = [DET]
    from panels import _login_failures, _report_times
    _login_failures.clear()
    _report_times.clear()
    yield
    client.drop_database(db.name)


def session(username=None):
    c = TestClient(main.app)
    if username:
        assert c.post("/api/login", json={"username": username, "password": PASSWORD}).status_code == 200
    return c


def test_nothing_private_without_login():
    c = session()
    for path in ("/api/incidents", "/api/stats", "/api/users", "/api/activity", "/api/jobs", "/api/approvals",
                 "/api/teams", "/api/export/csv", "/media/a.jpg", "/api/zones", "/api/live/sessions"):
        assert c.get(path).status_code == 401, path
    assert "model" not in c.get("/api/health").json()
    assert c.get("/api/me").json() == {"user": None}


def test_wrong_password_and_lockout():
    c = session()
    for _ in range(8):
        assert c.post("/api/login", json={"username": "boss", "password": "nope"}).status_code == 401
    assert c.post("/api/login", json={"username": "boss", "password": PASSWORD}).status_code == 429


def test_forged_or_stale_sessions_rejected():
    c = session("shahu")
    token = c.cookies.get("rd_session")
    user_id, exp, sig = token.split(".")
    forged = TestClient(main.app, cookies={"rd_session": f"{user_id}.{int(exp) + 999}.{sig}"})
    assert forged.get("/api/incidents").status_code == 401
    assert c.post("/api/me/password", json={"current_password": PASSWORD, "new_password": "another-password"}).status_code == 200
    assert c.get("/api/incidents").status_code == 401


def test_deactivated_user_is_locked_out():
    officer = session("shahu")
    admin = session("boss")
    uid = officer.get("/api/me").json()["user"]["id"]
    assert admin.patch(f"/api/users/{uid}", json={"active": False}).status_code == 200
    assert officer.get("/api/incidents").status_code == 401
    assert session().post("/api/login", json={"username": "shahu", "password": PASSWORD}).status_code == 401


def test_admin_cannot_remove_last_admin_or_self():
    admin = session("boss")
    uid = admin.get("/api/me").json()["user"]["id"]
    assert admin.patch(f"/api/users/{uid}", json={"active": False}).status_code == 400


def test_officer_sees_only_own_ward_even_if_asking_for_another():
    mine = incident("A1", "Shahupuri")
    other = incident("A2", "Rajarampuri")
    c = session("shahu")
    codes = [i["incident_code"] for i in c.get("/api/incidents", params={"zone": "Rajarampuri"}).json()["items"]]
    assert codes == ["A1"]
    assert c.get("/api/stats", params={"zone": "Rajarampuri"}).json()["total"] == 1
    assert "A2" not in c.get("/api/export/csv", params={"zone": "Rajarampuri"}).text
    assert c.get(f"/api/incidents/{other}").status_code == 404
    assert c.patch(f"/api/incidents/{other}", json={"status": "Repaired"}).status_code == 404
    assert c.patch(f"/api/incidents/{mine}", json={"assigned_to": "Unit 1"}).status_code == 200


def test_officer_admin_only_routes_blocked():
    i = incident("A1")
    c = session("shahu")
    assert c.delete(f"/api/incidents/{i}").status_code == 403
    assert c.get("/api/users").status_code == 403
    assert c.get("/api/activity").status_code == 403
    assert c.post("/api/demo/seed").status_code == 403
    assert c.delete("/api/demo").status_code == 403
    assert c.post("/api/model/reload").status_code == 403


def test_history_records_real_user_and_ignores_claimed_name():
    i = incident("A1")
    c = session("shahu")
    r = c.patch(f"/api/incidents/{i}", json={"note": "checked", "by": "Someone Else"}).json()
    assert r["history"][-1]["by"] == "Shahu (Ward officer)"


def test_repair_team_limited_to_own_jobs():
    mine = incident("J1", assigned_to="Unit 1")
    theirs = incident("J2", assigned_to="Unit 2")
    c = session("unit1")
    assert [j["incident_code"] for j in c.get("/api/jobs").json()["items"]] == ["J1"]
    assert c.post(f"/api/jobs/{theirs}/start").status_code == 404
    assert c.post(f"/api/jobs/{theirs}/complete", files=photo()).status_code == 404
    for path in ("/api/incidents", "/api/stats", "/api/export/csv", "/api/approvals", "/api/users", "/api/zones", "/api/teams"):
        assert c.get(path).status_code == 403, path
    assert c.patch(f"/api/incidents/{mine}", json={"status": "Repaired"}).status_code == 403
    assert c.post("/api/detect", files=photo()).status_code == 403
    assert c.post("/api/live/start").status_code == 403


def test_full_repair_flow_needs_officer_approval():
    i = incident("F1", assigned_to="Unit 1")
    team, officer, other_ward = session("unit1"), session("shahu"), session("raja")
    assert team.post(f"/api/jobs/{i}/start").json()["status"] == "In Progress"
    done = team.post(f"/api/jobs/{i}/complete", files=photo(), data={"note": "patched"}).json()
    assert done["status"] == "In Progress"
    assert done["repair"]["state"] == "pending"
    assert done["repair"]["ai_damage_found"] == 1
    assert team.post(f"/api/jobs/{i}/complete", files=photo()).status_code == 409
    assert other_ward.get("/api/approvals").json()["items"] == []
    assert other_ward.post(f"/api/incidents/{i}/repair/decision", json={"approve": True}).status_code == 404
    assert team.post(f"/api/incidents/{i}/repair/decision", json={"approve": True}).status_code == 403
    assert len(officer.get("/api/approvals").json()["items"]) == 1
    assert officer.post(f"/api/incidents/{i}/repair/decision", json={"approve": False}).status_code == 400
    assert officer.post(f"/api/incidents/{i}/repair/decision", json={"approve": False, "note": "Still broken"}).json()["status"] == "In Progress"
    found["dets"] = []
    resubmit = team.post(f"/api/jobs/{i}/complete", files=photo()).json()
    assert resubmit["repair"]["ai_damage_found"] == 0
    assert officer.post(f"/api/incidents/{i}/repair/decision", json={"approve": True}).json()["status"] == "Repaired"
    assert officer.get(f"/api/incidents/{i}").json()["repair"]["decided_by"] == "Shahu (Ward officer)"
    assert team.post(f"/api/jobs/{i}/complete", files=photo()).status_code == 409


def test_citizen_report_and_tracking_reveals_no_staff_details():
    c = session()
    r = c.post("/api/public/report", files=photo(), data={"lat": 16.704, "lng": 74.242, "note": "Deep hole"}).json()
    assert r["zone"] == "Shahupuri" and r["ai_found"] == 1
    assert r["code"].startswith("MD-")
    inc = incidents.find_one({"source": "citizen"})
    officer = session("shahu")
    officer.patch(f"/api/incidents/{inc['_id']}", json={"assigned_to": "Unit 1", "status": "In Progress", "note": "private note"})
    body = c.get(f"/api/public/track/{r['code'].lower()}")
    assert body.status_code == 200
    text = body.text
    assert "In Progress" in text
    for private in ("private note", "Ward officer", "Unit 1", "/media/", "Deep hole", "incident_ids"):
        assert private not in text, private
    assert c.get("/api/public/track/MD-NOTREAL").status_code == 404


def test_citizen_report_kept_for_review_when_ai_finds_nothing():
    found["dets"] = []
    r = session().post("/api/public/report", files=photo(), data={"lat": 16.704, "lng": 74.242, "kind": "alligator_crack"}).json()
    assert r["ai_found"] == 0
    inc = incidents.find_one({"source": "citizen"})
    assert inc["needs_review"] is True and inc["damage_type"] == "alligator_crack"
    officer = session("shahu")
    assert officer.patch(f"/api/incidents/{inc['_id']}", json={"severity": "High"}).json()["needs_review"] is False


def test_citizen_report_needs_valid_location_type_and_photo():
    c = session()
    assert c.post("/api/public/report", files=photo()).status_code == 400
    assert c.post("/api/public/report", files=photo(), data={"lat": 19.0, "lng": 72.8}).status_code == 400
    bad = {"file": ("x.exe", io.BytesIO(b"MZ"), "application/octet-stream")}
    assert c.post("/api/public/report", files=bad, data={"lat": 16.704, "lng": 74.242}).status_code == 400
    assert incidents.count_documents({}) == 0


def test_citizen_report_rate_limit():
    c = session()
    for _ in range(10):
        assert c.post("/api/public/report", files=photo(), data={"lat": 16.704, "lng": 74.242}).status_code == 200
    assert c.post("/api/public/report", files=photo(), data={"lat": 16.704, "lng": 74.242}).status_code == 429


def test_admin_manages_accounts_and_sees_activity():
    admin = session("boss")
    assert admin.post("/api/users", json={"username": "new_off", "password": "short", "role": "ward_officer", "ward": "Shahupuri"}).status_code == 400
    assert admin.post("/api/users", json={"username": "new_off", "password": PASSWORD, "role": "ward_officer"}).status_code == 400
    made = admin.post("/api/users", json={"username": "new_off", "password": PASSWORD, "role": "ward_officer", "ward": "Kadamwadi"})
    assert made.status_code == 200 and "password_hash" not in made.text
    assert admin.post("/api/users", json={"username": "new_off", "password": PASSWORD, "role": "admin"}).status_code == 409
    assert "password_hash" not in admin.get("/api/users").text
    assert any(a["action"] == "Created account" for a in admin.get("/api/activity").json()["items"])
    assert session("new_off").get("/api/me").json()["user"]["ward"] == "Kadamwadi"

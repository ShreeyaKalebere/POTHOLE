"""Staff accounts and the activity log.

Roles:  admin        - everything, in every ward
        ward_officer - one ward: inspect, assign repair teams, approve repairs
        repair_team  - only the jobs assigned to their team
Citizens have no account; they use the public /api/public routes.
"""
import hashlib
import hmac
import re
import secrets
from datetime import datetime

from pymongo import ASCENDING, DESCENDING

from config import ADMIN_PASSWORD, ADMIN_USERNAME, APP_PASSWORD
from db import db

users = db["users"]
activity = db["activity_log"]
reports = db["citizen_reports"]

ROLES = ("admin", "ward_officer", "repair_team")
MIN_PASSWORD = 8
_USERNAME = re.compile(r"^[a-z0-9_.-]{3,32}$")
# verified when the username is unknown, so a wrong username takes as long as a wrong password
_DUMMY_HASH = None


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=2 ** 14, r=8, p=1, dklen=32).hex()
    return f"scrypt${salt}${digest}"


def password_matches(password, stored):
    try:
        _, salt, _ = stored.split("$")
    except (AttributeError, ValueError):
        return False
    return hmac.compare_digest(hash_password(password or "", salt), stored)


def check_login(username, password):
    """Returns the active user for these credentials, or None."""
    global _DUMMY_HASH
    user = users.find_one({"username": (username or "").strip().lower()})
    if user is None:
        _DUMMY_HASH = _DUMMY_HASH or hash_password(secrets.token_hex(8))
        password_matches(password, _DUMMY_HASH)
        return None
    if not password_matches(password, user["password_hash"]) or not user.get("active", True):
        return None
    return user


def validate_new_user(username, password, role, ward, team):
    if not _USERNAME.match(username or ""):
        return "Username needs 3 to 32 lowercase letters, numbers, dots, dashes or underscores"
    if role not in ROLES:
        return f"Role must be one of {', '.join(ROLES)}"
    if len(password or "") < MIN_PASSWORD:
        return f"Password needs at least {MIN_PASSWORD} characters"
    return validate_scope(role, ward, team)


def validate_scope(role, ward, team):
    if role == "ward_officer" and not ward:
        return "A ward officer needs a ward"
    if role == "repair_team" and not team:
        return "A repair team account needs a team name"
    return None


def create_user(username, password, role, name="", ward=None, team=None):
    doc = {
        "username": username, "name": name or username, "role": role,
        "ward": ward if role == "ward_officer" else None,
        "team": team if role == "repair_team" else None,
        "password_hash": hash_password(password), "active": True, "created_at": datetime.now(),
    }
    doc["_id"] = users.insert_one(doc).inserted_id
    return doc


def public_user(user):
    return {"id": str(user["_id"]), "username": user["username"], "name": user.get("name") or user["username"],
            "role": user["role"], "ward": user.get("ward"), "team": user.get("team"),
            "active": user.get("active", True)}


def log_activity(who, action, incident_code=None, detail=""):
    activity.insert_one({"at": datetime.now(), "who": who, "action": action,
                         "incident_code": incident_code, "detail": detail})


def init_accounts():
    users.create_index([("username", ASCENDING)], unique=True)
    activity.create_index([("at", DESCENDING)])
    reports.create_index([("code", ASCENDING)], unique=True)
    # first start in the cloud: create the admin from the environment
    password = ADMIN_PASSWORD or APP_PASSWORD
    if password and len(password) >= MIN_PASSWORD and users.count_documents({"role": "admin"}) == 0:
        create_user(ADMIN_USERNAME, password, "admin", name="Administrator")

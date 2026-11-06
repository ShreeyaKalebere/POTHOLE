"""Login sessions and who may reach what.

Everything under /api and /media needs a login, except the public paths below. The session cookie
holds the user id and expiry signed with HMAC; the signature also covers the password hash, so
changing a password ends that person's old sessions. Deactivated users are refused on every request.
"""
import hashlib
import hmac
import secrets
import time

from bson import ObjectId
from fastapi import HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from accounts import users
from config import APP_SECRET, SESSION_DAYS
from db import db

COOKIE = "rd_session"
OPEN_PATHS = {"/api/login", "/api/logout", "/api/me", "/api/health"}
PUBLIC_PREFIX = "/api/public/"
ADMIN_ONLY = ("/api/users", "/api/activity", "/api/demo", "/api/model")
REPAIR_TEAM_ALLOWED = ("/api/jobs", "/api/me/", "/media/")

_secret_cache = None


def _secret():
    """APP_SECRET if set, otherwise a random secret kept in the database so sessions survive restarts."""
    global _secret_cache
    if _secret_cache is None:
        if APP_SECRET:
            _secret_cache = APP_SECRET.encode()
        else:
            doc = db["settings"].find_one_and_update(
                {"_id": "session_secret"}, {"$setOnInsert": {"value": secrets.token_hex(32)}},
                upsert=True, return_document=True)
            _secret_cache = doc["value"].encode()
    return _secret_cache


def _sign(user_id, exp, password_hash):
    return hmac.new(_secret(), f"{user_id}|{exp}|{password_hash}".encode(), hashlib.sha256).hexdigest()


def make_token(user):
    exp = str(int(time.time()) + SESSION_DAYS * 86400)
    return f"{user['_id']}.{exp}.{_sign(user['_id'], exp, user['password_hash'])}"


def user_from_token(token):
    try:
        user_id, exp, sig = token.split(".")
        if int(exp) <= time.time():
            return None
        user = users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None
    if user is None or not user.get("active", True):
        return None
    return user if hmac.compare_digest(sig, _sign(user_id, exp, user["password_hash"])) else None


def current_user(request: Request):
    return user_from_token(request.cookies.get(COOKIE, ""))


def is_https(request: Request):
    return request.headers.get("x-forwarded-proto", request.url.scheme) == "https"


def client_ip(request: Request):
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def _blocked_for_role(user, path, method):
    role = user["role"]
    if role == "admin":
        return False
    if path.startswith(ADMIN_ONLY):
        return True
    if role == "ward_officer":
        return method == "DELETE" and path.startswith("/api/incidents/")
    return not path.startswith(REPAIR_TEAM_ALLOWED)


async def middleware(request: Request, call_next):
    path = request.url.path
    needs_login = (path.startswith("/api") or path.startswith("/media")) and path not in OPEN_PATHS \
        and not path.startswith(PUBLIC_PREFIX)
    if needs_login:
        user = await run_in_threadpool(current_user, request)
        if user is None:
            return JSONResponse({"detail": "Login required"}, status_code=401)
        if _blocked_for_role(user, path, request.method):
            return JSONResponse({"detail": "Your account does not have access to this"}, status_code=403)
        request.state.user = user
    return await call_next(request)


def scope(user, query):
    """Limits a Mongo query to what this user may see. Overrides any ward the browser asked for."""
    if user["role"] == "ward_officer":
        query["zone"] = user["ward"]
    elif user["role"] == "repair_team":
        query["assigned_to"] = user["team"]
    return query


def in_scope(user, incident):
    if user["role"] == "ward_officer":
        return incident.get("zone") == user["ward"]
    if user["role"] == "repair_team":
        return incident.get("assigned_to") == user["team"]
    return True


def signature_of(user):
    label = {"admin": "Admin", "ward_officer": "Ward officer", "repair_team": "Repair team"}[user["role"]]
    return f"{user.get('name') or user['username']} ({label})"


def require_role(request: Request, *roles):
    if request.state.user["role"] not in roles:
        raise HTTPException(403, "Your account does not have access to this")
    return request.state.user

"""Simple password login for the deployed dashboard.

If APP_PASSWORD is empty (laptop use) everything is open, exactly as before.
If it is set, /api and /media need a valid login cookie (except login + health).
The cookie holds an expiry time signed with HMAC, so no session table is needed.
"""
import hashlib
import hmac
import time

from fastapi import Request
from fastapi.responses import JSONResponse

from config import APP_PASSWORD, APP_SECRET, SESSION_DAYS

COOKIE = "rd_session"
OPEN_PATHS = {"/api/login", "/api/logout", "/api/me", "/api/health"}
_SECRET = (APP_SECRET or hashlib.sha256(("pothole:" + APP_PASSWORD).encode()).hexdigest()).encode()


def enabled():
    return bool(APP_PASSWORD)


def make_token():
    exp = str(int(time.time()) + SESSION_DAYS * 86400)
    sig = hmac.new(_SECRET, exp.encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def valid(token):
    try:
        exp, sig = token.split(".", 1)
        good = hmac.new(_SECRET, exp.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, good) and int(exp) > time.time()
    except (ValueError, AttributeError):
        return False


def password_ok(pw):
    return enabled() and hmac.compare_digest((pw or "").encode(), APP_PASSWORD.encode())


def is_logged_in(request: Request):
    return not enabled() or valid(request.cookies.get(COOKIE, ""))


async def middleware(request: Request, call_next):
    p = request.url.path
    if enabled() and (p.startswith("/api") or p.startswith("/media")) and p not in OPEN_PATHS:
        if not valid(request.cookies.get(COOKIE, "")):
            return JSONResponse({"detail": "Login required"}, status_code=401)
    return await call_next(request)


def is_https(request: Request):
    return request.headers.get("x-forwarded-proto", request.url.scheme) == "https"

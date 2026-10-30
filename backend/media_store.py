"""Where photos are stored.

MEDIA_BACKEND=local  (default, laptop)  -> files in backend/media/
MEDIA_BACKEND=gridfs (cloud)            -> inside MongoDB (GridFS), because a cloud
                                           container's disk is wiped on every restart.
Both return the same kind of URL: /media/<name>
"""
import mimetypes

import cv2
import gridfs

from config import MEDIA_DIR, MEDIA_BACKEND, CLOUD_MAX_IMAGE_SIDE
from db import db

_fs = gridfs.GridFS(db, collection="media") if MEDIA_BACKEND == "gridfs" else None


def _ctype(name):
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


def save_bytes(name, data):
    if _fs is not None:
        old = _fs.find_one({"filename": name})
        if old:
            _fs.delete(old._id)
        _fs.put(data, filename=name, contentType=_ctype(name))
    else:
        path = MEDIA_DIR / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return f"/media/{name}"


def save_image(name, img_bgr, quality=85):
    """Saves an OpenCV image as JPEG. In the cloud large photos are shrunk to save database space."""
    if _fs is not None:
        h, w = img_bgr.shape[:2]
        s = CLOUD_MAX_IMAGE_SIDE / max(h, w)
        if s < 1:
            img_bgr = cv2.resize(img_bgr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return save_bytes(name, buf.tobytes())


def delete(url):
    """Removes a stored photo given its /media/<name> URL (missing files are ignored)."""
    if not url or not url.startswith("/media/"):
        return
    name = url[len("/media/"):]
    if _fs is not None:
        for f in _fs.find({"filename": name}):
            _fs.delete(f._id)
        return
    path = (MEDIA_DIR / name).resolve()
    if MEDIA_DIR.resolve() in path.parents and path.is_file():
        path.unlink()


def read(name):
    """Returns (bytes, content_type) or None."""
    if _fs is not None:
        f = _fs.find_one({"filename": name})
        return (f.read(), f.content_type or _ctype(name)) if f else None
    path = (MEDIA_DIR / name).resolve()
    if MEDIA_DIR.resolve() not in path.parents or not path.is_file():   # no ../ escapes
        return None
    return path.read_bytes(), _ctype(name)

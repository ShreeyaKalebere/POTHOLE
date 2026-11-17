"""Copies the incident photos from this laptop into the online database, so the website can show them.

Run (from the backend folder):  python upload_photos_to_cloud.py
It asks for your MongoDB Atlas link (hidden while you paste) and the online database name.
Photos are shrunk to 960 px to fit the free Atlas plan. Photos already online are skipped,
so it is safe to run again after adding new incidents on the laptop.
"""
import getpass
import sys

import cv2
import gridfs
from pymongo import MongoClient
from pymongo.errors import InvalidURI

from config import MEDIA_DIR
from db import incidents

MAX_SIDE = 960
QUALITY = 75


def photo_urls():
    urls = set()
    for inc in incidents.find({}, {"images": 1, "repair": 1}):
        for im in inc.get("images", []):
            urls.update(u for u in (im.get("url"), im.get("annotated_url")) if u)
        urls.update(u for u in ((inc.get("repair") or {}).get(k) for k in ("photo_url", "annotated_url")) if u)
    return sorted(u for u in urls if u.startswith("/media/"))


def shrink(path):
    img = cv2.imread(str(path))
    if img is None:
        return None
    s = MAX_SIDE / max(img.shape[:2])
    if s < 1:
        img = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, QUALITY])
    return buf.tobytes() if ok else None


def main():
    urls = photo_urls()
    print(f"{len(urls)} photos are used by incidents on this laptop")
    uri = getpass.getpass("Paste your MongoDB Atlas link (it will not show): ").strip().strip("\"'")
    if not uri.startswith("mongodb"):
        raise SystemExit("That does not look like a MongoDB link.")
    db_name = input("Online database name [pothole_detection]: ").strip() or "pothole_detection"
    try:
        online = MongoClient(uri, serverSelectionTimeoutMS=10000)[db_name]
    except InvalidURI:
        raise SystemExit("The link was not pasted fully. Copy it again from Atlas (Connect > Drivers) and run this again.")
    online.list_collection_names()   # fails here with a clear error if the link or password is wrong
    fs = gridfs.GridFS(online, collection="media")   # the same place the website reads photos from

    added = skipped = missing = 0
    total_bytes = 0
    for n, url in enumerate(urls, 1):
        name = url[len("/media/"):]
        if fs.exists({"filename": name}):
            skipped += 1
            continue
        data = shrink(MEDIA_DIR / name)
        if data is None:
            missing += 1
            continue
        fs.put(data, filename=name, contentType="image/jpeg")
        added += 1
        total_bytes += len(data)
        if n % 50 == 0:
            print(f"  {n}/{len(urls)} checked, {added} uploaded ({total_bytes / 1e6:.1f} MB)", flush=True)
    print(f"Done: {added} uploaded ({total_bytes / 1e6:.1f} MB), {skipped} were already online, {missing} not found on this laptop.")
    sys.exit(0)


if __name__ == "__main__":
    main()

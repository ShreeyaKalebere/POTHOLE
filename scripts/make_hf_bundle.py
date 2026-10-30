"""
Builds deploy/hf_space/ - exactly the files to upload to a Hugging Face Docker Space.
Run:  python make_hf_bundle.py
"""
import shutil
from pathlib import Path

ROOT = Path("F:/POTHOLE_PROJECT")
OUT = ROOT / "deploy" / "hf_space"

README = """---
title: Road Damage Monitor Kolhapur
emoji: 🛣️
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 8000
pinned: false
---

Computer Vision & Deep Learning based Road Damage and Municipal Reporting System
(YOLO11 + FastAPI + MongoDB + React). DYPCET Kolhapur, Group 3.
Login with the team password.
"""


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    copy(ROOT / "Dockerfile", OUT / "Dockerfile")
    copy(ROOT / "deploy/requirements-cloud.txt", OUT / "deploy/requirements-cloud.txt")
    copy(ROOT / "models/final.pt", OUT / "models/final.pt")
    for p in (ROOT / "backend").glob("*"):
        if p.is_file() and p.suffix in (".py", ".yaml", ".txt"):
            copy(p, OUT / "backend" / p.name)
    for name in ("package.json", "package-lock.json", "index.html", "vite.config.js"):
        copy(ROOT / "dashboard" / name, OUT / "dashboard" / name)
    shutil.copytree(ROOT / "dashboard/src", OUT / "dashboard/src")
    (OUT / "README.md").write_text(README, encoding="utf-8")
    files = [p for p in OUT.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files) / 1e6
    print(f"bundle ready: {OUT}  ({len(files)} files, {size:.1f} MB)")


if __name__ == "__main__":
    main()

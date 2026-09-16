import os
import sys
import time
import zipfile
import argparse
import requests
from pathlib import Path
from tqdm import tqdm

from config import RAW_DIR, METADATA_DIR

DOWNLOAD_LOG = METADATA_DIR / "download_errors.log"

def log_error(msg: str):
    print(f"[ERROR] {msg}")
    DOWNLOAD_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(DOWNLOAD_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

def download_file(url: str, dest_path: Path, desc: str = "") -> bool:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists() and dest_path.stat().st_size > 1024 * 1024:
        print(f"[SKIP] {dest_path.name} already exists ({dest_path.stat().st_size / (1024*1024):.2f} MB).")
        return True

    print(f"[DOWNLOADING] {desc or dest_path.name} from {url}...")
    headers = {"User-Agent": "RoadDamageResearch/1.0"}
    try:
        response = requests.get(url, stream=True, timeout=60, headers=headers)
        if response.status_code != 200:
            log_error(f"Failed to download {url}: HTTP {response.status_code}")
            return False

        total_size = int(response.headers.get("content-length", 0))
        temp_dest = dest_path.with_suffix(dest_path.suffix + ".part")

        with open(temp_dest, "wb") as f, tqdm(
            desc=dest_path.name,
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))

        if temp_dest.exists():
            temp_dest.replace(dest_path)
            print(f"[SUCCESS] Downloaded {dest_path.name} ({dest_path.stat().st_size / (1024*1024):.2f} MB).")
            return True
        else:
            log_error(f"Download temp file missing for {dest_path.name}")
            return False
    except Exception as e:
        log_error(f"Exception while downloading {url}: {e}")
        return False

def extract_archive(archive_path: Path, extract_to: Path) -> bool:
    print(f"[EXTRACTING] {archive_path.name} -> {extract_to}...")
    extract_to.mkdir(parents=True, exist_ok=True)
    try:
        if archive_path.suffix.lower() == ".zip":
            with zipfile.ZipFile(archive_path, 'r') as zf:
                namelist = zf.namelist()
                if namelist and (extract_to / namelist[0]).exists():
                    print(f"[SKIP] {archive_path.name} appears already extracted.")
                    return True
                zf.extractall(extract_to)
            print(f"[SUCCESS] Extracted {archive_path.name} successfully.")
            return True
        else:
            log_error(f"Unsupported archive format: {archive_path}")
            return False
    except Exception as e:
        log_error(f"Failed extracting {archive_path}: {e}")
        return False

def download_rdd2020():
    """RDD2020 Multi-National Dataset (India, Japan, Czech) from Hugging Face."""
    rdd2020_url = "https://huggingface.co/datasets/ShixuanAn/RDD_2020/resolve/main/train.zip"
    rdd2020_zip = RAW_DIR / "RDD2020" / "train.zip"
    rdd2020_extract = RAW_DIR / "RDD2020"

    success = download_file(rdd2020_url, rdd2020_zip, "RDD2020 Multi-National Train (India/Japan/Czech)")
    if success:
        extract_archive(rdd2020_zip, rdd2020_extract)
    return success

def download_pothole600():
    """Local Pothole600 archive from user's Downloads if present."""
    local_archive = Path(r"c:\Users\shree\Downloads\archive.zip")
    if local_archive.exists():
        print(f"[FOUND LOCAL] Found {local_archive}")
        pothole600_dir = RAW_DIR / "other_sources" / "Pothole600"
        return extract_archive(local_archive, pothole600_dir)
    return False

def download_svrdd():
    """SVRDD (Street View Road Damage Dataset) from Zenodo (10.5281/zenodo.10100129)."""
    svrdd_url = "https://zenodo.org/api/records/10100129/files/SVRDD_YOLO.zip/content"
    svrdd_zip = RAW_DIR / "SVRDD" / "SVRDD_YOLO.zip"
    svrdd_extract = RAW_DIR / "SVRDD"

    success = download_file(svrdd_url, svrdd_zip, "SVRDD YOLO Dataset (Zenodo 10100129)")
    if success:
        extract_archive(svrdd_zip, svrdd_extract)
    return success

def setup_sources(include_svrdd: bool = False):
    print("=== STEP 1: ACQUIRING DATA SOURCES ===")
    download_rdd2020()
    download_pothole600()
    if include_svrdd:
        download_svrdd()
    print("\nSource acquisition complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and extract road damage dataset sources.")
    parser.add_argument("--include-svrdd", action="store_true", help="Also download SVRDD from Zenodo (2.89 GB).")
    args = parser.parse_args()
    setup_sources(include_svrdd=args.include_svrdd)

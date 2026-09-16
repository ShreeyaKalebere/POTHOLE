import os
import zipfile
from pathlib import Path
from tqdm import tqdm

from config import DATASET_ROOT, WORKSPACE_ROOT

def package_dataset(output_zip: Path = None):
    if output_zip is None:
        output_zip = WORKSPACE_ROOT / "RoadDamage20K.zip"

    print(f"Packaging dataset into {output_zip.name} for Google Colab upload...")
    
    # Files to include: images, labels, data.yaml, and metadata
    targets = [
        ("images", DATASET_ROOT / "images"),
        ("labels", DATASET_ROOT / "labels"),
        ("metadata", DATASET_ROOT / "metadata"),
        ("data.yaml", DATASET_ROOT / "data.yaml")
    ]

    # Collect file paths
    all_files = []
    for rel_prefix, path in targets:
        if path.is_file():
            all_files.append((path, f"dataset/RoadDamage20K/{path.name}"))
        elif path.is_dir():
            for f in path.rglob("*.*"):
                rel_path = f.relative_to(DATASET_ROOT)
                all_files.append((f, f"dataset/RoadDamage20K/{rel_path}".replace("\\", "/")))

    print(f"Total files to compress: {len(all_files)}")

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for src, arcname in tqdm(all_files, desc="Compressing RoadDamage20K.zip"):
            zf.write(src, arcname)

    zip_size_mb = output_zip.stat().st_size / (1024 * 1024)
    print(f"\n[SUCCESS] Packaged {output_zip.name} ({zip_size_mb:.2f} MB).")
    print("Ready to upload directly to Google Drive or Google Colab!")

if __name__ == "__main__":
    package_dataset()

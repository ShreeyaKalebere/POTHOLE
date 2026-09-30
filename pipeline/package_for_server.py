import os
import zipfile
import yaml
from pathlib import Path

def create_server_package():
    dataset_dir = Path("F:/RoadDamage_Fresh")
    output_zip = Path("F:/RoadDamage_Fresh_Server_21K.zip")
    
    print(f"Packaging {dataset_dir} into {output_zip}...")
    
    # 1. Create a server-adapted data.yaml with relative or /workspace paths
    server_yaml_path = dataset_dir / "data_server.yaml"
    server_config = {
        "path": ".", # relative path works anywhere the archive is extracted!
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {
            0: "pothole",
            1: "alligator_crack"
        }
    }
    with open(server_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(server_config, f, default_flow_style=False)
    print("Created server-adapted data_server.yaml (uses relative path for Linux compatibility)")

    # 2. Package into single zip archive
    # Include images, labels, data.yaml, data_server.yaml, metadata
    folders_to_include = ["images", "labels", "metadata", "qa"]
    files_to_include = ["data.yaml", "data_server.yaml", "DATASET_REPORT.md"]
    
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for f_name in files_to_include:
            f_path = dataset_dir / f_name
            if f_path.exists():
                zf.write(f_path, arcname=f_name)
                print(f"  Added {f_name}")
                
        for folder in folders_to_include:
            folder_path = dataset_dir / folder
            if folder_path.exists():
                print(f"  Archiving {folder}/...")
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        full_p = Path(root) / file
                        rel_p = full_p.relative_to(dataset_dir)
                        zf.write(full_p, arcname=str(rel_p))
                        
    print(f"\nPackaging complete! Archive saved at: {output_zip.resolve()}")
    print(f"Archive size: {output_zip.stat().st_size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    create_server_package()

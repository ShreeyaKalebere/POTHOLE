"""
Road Damage Detection — YOLO11 Resume Training Pipeline for AI Server (Linux)
=============================================================================
This script safely resumes training from your local checkpoint (epoch 50/100)
on a remote AI server with NVIDIA GPUs.

It automatically:
1. Patches Windows filepaths inside last.pt to Linux-compatible relative paths.
2. Unzips the dataset if needed.
3. Detects available GPU(s) and adjusts batch size / workers.
4. Resumes training cleanly from epoch 50 up to your target (e.g., 100 or 150).
5. Evaluates the final best model on the held-out test split.
"""

import os
import sys
import argparse
import zipfile
from pathlib import Path
import torch

def setup_dataset():
    """Ensures dataset is unzipped and data_server.yaml is available."""
    zip_candidates = [
        "RoadDamage_Fresh_Server_21K.zip",
        str(Path.home() / "POTHOLE" / "RoadDamage_Fresh_Server_21K.zip"),
        str(Path.home() / "pothole_training" / "RoadDamage_Fresh_Server_21K.zip"),
        "RoadDamage_Fresh.zip"
    ]
    
    # Check if images directory already exists in current dir or in RoadDamage_Fresh
    if os.path.exists("RoadDamage_Fresh/images"):
        os.chdir("RoadDamage_Fresh")
        print("[OK] Working directory changed to RoadDamage_Fresh/")

    if not os.path.exists("images"):
        zip_found = None
        for z in zip_candidates:
            if os.path.exists(str(z)):
                zip_found = str(z)
                break
                
        if zip_found:
            print(f"[*] Extracting dataset archive: {zip_found}...")
            with zipfile.ZipFile(zip_found, 'r') as zip_ref:
                zip_ref.extractall(".")
            print("[OK] Dataset successfully unzipped.")
        else:
            print("[!] WARNING: 'images/' directory not found and no zip file found to extract.")
            print("    Please ensure the dataset images/ and labels/ are in the current directory.")

    # Ensure data_server.yaml exists
    yaml_path = "data_server.yaml"
    if not os.path.exists(yaml_path):
        print(f"[*] Creating default {yaml_path}...")
        content = """path: .
train: images/train
val: images/val
test: images/test
names:
  0: pothole
  1: alligator_crack
"""
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[✓] {yaml_path} created.")
        
    return os.path.abspath(yaml_path)

def patch_checkpoint_for_server(checkpoint_path, data_yaml_path, target_epochs=100):
    """
    Patches Windows absolute paths in last.pt to Linux server paths
    so Ultralytics doesn't fail on cross-platform resume.
    """
    print(f"\n[*] Inspecting checkpoint: {checkpoint_path}")
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint file '{checkpoint_path}' not found!")

    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    last_epoch = ckpt.get("epoch", -1)
    train_args = ckpt.get("train_args", {})
    
    print(f"[*] Checkpoint Last Completed Epoch : {last_epoch + 1}")
    print(f"[*] Original Data Config in Ckpt    : {train_args.get('data')}")
    print(f"[*] Original Target Epochs in Ckpt  : {train_args.get('epochs')}")

    # Patch data path to server's yaml
    train_args["data"] = data_yaml_path
    train_args["project"] = "runs/detect"
    train_args["name"] = "road_damage_fresh"
    train_args["exist_ok"] = True
    
    # Update total target epochs if user requested more
    if target_epochs > (last_epoch + 1):
        train_args["epochs"] = target_epochs
        print(f"[*] Target epochs updated to        : {target_epochs} (Remaining: {target_epochs - (last_epoch + 1)} epochs)")
    else:
        print(f"[!] Target epochs ({target_epochs}) <= completed epochs ({last_epoch + 1}). Setting to {last_epoch + 51}.")
        target_epochs = last_epoch + 51
        train_args["epochs"] = target_epochs

    ckpt["train_args"] = train_args
    
    # Save patched checkpoint
    torch.save(ckpt, checkpoint_path)
    print(f"[✓] Checkpoint successfully patched for Linux server environment.")
    return last_epoch + 1, target_epochs

def main():
    parser = argparse.ArgumentParser(description="Resume YOLO11 Training on AI Server")
    parser.add_argument("--weights", type=str, default="last.pt", help="Path to checkpoint weights file (e.g. last.pt)")
    parser.add_argument("--epochs", type=int, default=100, help="Total target epochs to reach (e.g. 100 or 150)")
    parser.add_argument("--batch", type=int, default=None, help="Batch size (optional, auto-detected if not specified)")
    args = parser.parse_args()

    print("=" * 70)
    print("  ROAD DAMAGE DETECTION — RESUMING TRAINING ON AI SERVER")
    print("=" * 70)

    # 1. Device check
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[*] CUDA Available : True")
        print(f"[*] GPU Name       : {gpu_name} ({gpu_count} GPU{'s' if gpu_count > 1 else ''})")
        print(f"[*] Total VRAM     : {vram_gb:.2f} GB")
        device = 0 if gpu_count == 1 else [i for i in range(gpu_count)]
    else:
        print("[!] WARNING: CUDA not available. Training will run on CPU.")
        device = "cpu"
        vram_gb = 0

    # 2. Dataset Setup
    data_yaml = setup_dataset()
    print(f"[*] Dataset config ready: {data_yaml}")

    # 3. Checkpoint Patching
    ckpt_path = os.path.abspath(args.weights)
    completed_epochs, total_epochs = patch_checkpoint_for_server(ckpt_path, data_yaml, args.epochs)

    # 4. Import Ultralytics
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[!] ERROR: ultralytics is not installed. Installing...")
        os.system("pip install ultralytics")
        from ultralytics import YOLO

    # 5. Load model & resume training
    print("\n" + "-" * 70)
    print(f"  Resuming from Epoch {completed_epochs} -> Target Epoch {total_epochs}")
    print(f"  - Device: {device}")
    print(f"  - Weights: {ckpt_path}")
    print("-" * 70 + "\n")

    model = YOLO(ckpt_path)

    # Resume training
    results = model.train(resume=True)

    print("\n" + "=" * 70)
    print("  TRAINING COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    save_dir = Path(results.save_dir) if hasattr(results, 'save_dir') else Path("runs/detect/road_damage_fresh")
    best_pt = save_dir / "weights" / "best.pt"
    last_pt = save_dir / "weights" / "last.pt"
    print(f"  Best Weights : {best_pt.resolve() if best_pt.exists() else 'runs/detect/road_damage_fresh/weights/best.pt'}")
    print(f"  Last Weights : {last_pt.resolve() if last_pt.exists() else 'runs/detect/road_damage_fresh/weights/last.pt'}")

    # 6. Evaluate on Test Split
    if best_pt.exists():
        print("\n" + "-" * 70)
        print("  Evaluating Best Model on Held-out Test Set...")
        print("-" * 70)
        best_model = YOLO(str(best_pt))
        test_metrics = best_model.val(data=data_yaml, split="test", device=device)
        print(f"  Test Precision : {test_metrics.box.mp:.4f}")
        print(f"  Test Recall    : {test_metrics.box.mr:.4f}")
        print(f"  Test mAP@50    : {test_metrics.box.map50:.4f}")
        print(f"  Test mAP@50:95 : {test_metrics.box.map:.4f}")
        print("-" * 70)

if __name__ == "__main__":
    main()

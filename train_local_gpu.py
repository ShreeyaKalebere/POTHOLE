"""
Road Damage Detection — YOLO11 GPU Training Script (Local RTX 4060)
===================================================================
Automatically configures and starts training on your local NVIDIA GPU
with optimal hyperparameters, checkpoints, and validation metrics.
"""

import os
import sys
import torch

def main():
    print("=" * 70)
    print("  ROAD DAMAGE DETECTION — YOLO11 GPU TRAINING")
    print("=" * 70)

    # 1. Verify CUDA & Hardware
    cuda_avail = torch.cuda.is_available()
    print(f"[*] PyTorch Version : {torch.__version__}")
    print(f"[*] CUDA Available  : {cuda_avail}")

    if not cuda_avail:
        print("\n[!] WARNING: CUDA is not available. Training on CPU will be slow.")
        device = "cpu"
    else:
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[*] GPU Name        : {gpu_name}")
        print(f"[*] Total VRAM      : {vram_gb:.2f} GB")
        device = 0

    # 2. Check Data Config
    data_yaml = os.path.abspath("dataset/RoadDamage20K/data.yaml")
    if not os.path.exists(data_yaml):
        print(f"[!] ERROR: Data config not found at: {data_yaml}")
        sys.exit(1)
    print(f"[*] Dataset Config  : {data_yaml}")

    # 3. Import Ultralytics
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[!] ERROR: ultralytics is not installed. Run: pip install ultralytics")
        sys.exit(1)

    # 4. Load Base Model
    base_model = "yolo11n.pt"
    print(f"[*] Loading model   : {base_model}")
    model = YOLO(base_model)

    # 5. Start Training
    print("\n" + "-" * 70)
    print("  Starting 150-Epoch Training Pipeline...")
    print("  - Target Device : GPU (0)" if cuda_avail else "  - Target Device : CPU")
    print("  - Batch Size    : 16")
    print("  - Image Size    : 640x640")
    print("  - Optimizer     : AdamW / Cosine LR")
    print("  - Checkpoints   : Every 25 epochs + Best model")
    print("  - Early Stop    : Patience 30 epochs")
    print("-" * 70 + "\n")

    results = model.train(
        data=data_yaml,
        epochs=150,
        patience=30,
        save_period=25,
        imgsz=640,
        batch=16,
        device=device,
        workers=4 if os.name != 'nt' else 2,  # Stable workers on Windows
        cos_lr=True,
        project="runs/train",
        name="road_damage_yolo11n_rtx4060",
        exist_ok=True,
        plots=True,
        val=True,
        verbose=True,
    )

    print("\n" + "=" * 70)
    print("  TRAINING COMPLETE!")
    print(f"  Best Weights Saved At: runs/train/road_damage_yolo11n_rtx4060/weights/best.pt")
    print(f"  Last Weights Saved At: runs/train/road_damage_yolo11n_rtx4060/weights/last.pt")
    print("=" * 70)

if __name__ == "__main__":
    main()

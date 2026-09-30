"""
Road Damage Detection — YOLO11-Medium (1280px) High-Accuracy Training Pipeline
=============================================================================
Optimized for NVIDIA RTX A5000 (24GB VRAM) on the college AI server.

Key Improvements for 80-90%+ Accuracy:
1. Backbone: YOLO11 Medium (yolo11m.pt) — 20.1M parameters (8x capacity of Nano)
2. Resolution: 1280x1280 (4x pixel area over 640px) for small potholes & fine cracks
3. Optimizer: AdamW with Cosine Learning Rate Schedule (cos_lr=True)
4. Advanced Augmentations: MixUp (0.15), Copy-Paste (0.3), Scale (0.6), Degrees (10.0)
5. Mosaic Shutoff: close_mosaic=15 (refines boundary boxes in the final 15 epochs)
"""

import os
import sys
import torch
from pathlib import Path

def main():
    print("=" * 75)
    print("  ROAD DAMAGE DETECTION — HIGH ACCURACY YOLO11-MEDIUM PIPELINE")
    print("=" * 75)

    # 1. Device check
    if not torch.cuda.is_available():
        print("[!] ERROR: CUDA is not available on this server.")
        sys.exit(1)

    gpu_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"[*] Primary GPU : {gpu_name}")
    print(f"[*] Total VRAM  : {vram_gb:.2f} GB")

    # 2. Check dataset config
    data_yaml = os.path.abspath("data_server.yaml")
    if not os.path.exists(data_yaml):
        candidates = ["data.yaml", "RoadDamage_Fresh/data_server.yaml"]
        for c in candidates:
            if os.path.exists(c):
                data_yaml = os.path.abspath(c)
                break

    print(f"[*] Dataset Config : {data_yaml}")

    # 3. Import Ultralytics
    try:
        from ultralytics import YOLO
    except ImportError:
        os.system("~/.local/bin/pip install --user ultralytics")
        from ultralytics import YOLO

    # 4. Load YOLO11-Medium Backbone
    model_name = "yolo11m.pt"
    print(f"[*] Initializing model backbone: {model_name}...")
    model = YOLO(model_name)

    # 5. Determine batch size
    # 1280px with YOLO11-Medium requires ~14-18 GB VRAM at batch 16 with AMP
    batch_size = 16 if vram_gb >= 22 else 8
    print(f"[*] Image Resolution  : 1280x1280")
    print(f"[*] Batch Size        : {batch_size}")
    print(f"[*] Optimizer         : AdamW with Cosine LR (cos_lr=True)")
    print(f"[*] Target Epochs     : 100")
    print(f"[*] Augmentations     : MixUp (0.15), Copy-Paste (0.30), Scale (0.60)")
    print(f"[*] Mosaic Close      : Last 15 epochs (close_mosaic=15)")
    print("-" * 75 + "\n")

    # 6. Launch Training
    results = model.train(
        data=data_yaml,
        epochs=100,
        imgsz=1280,
        batch=batch_size,
        device=0,
        optimizer="AdamW",
        lr0=0.001,
        cos_lr=True,
        mixup=0.15,
        copy_paste=0.30,
        scale=0.60,
        degrees=10.0,
        fliplr=0.5,
        close_mosaic=15,
        patience=30,
        save=True,
        save_period=10,
        project="runs/detect",
        name="road_damage_yolo11m_1280px",
        exist_ok=True,
        plots=True,
        amp=True,
        workers=6,
        val=True,
        verbose=True
    )

    print("\n" + "=" * 75)
    print("  HIGH ACCURACY TRAINING COMPLETED SUCCESSFULLY!")
    print("=" * 75)
    save_dir = Path(results.save_dir) if hasattr(results, 'save_dir') else Path("runs/detect/road_damage_yolo11m_1280px")
    best_pt = save_dir / "weights" / "best.pt"
    print(f"  Best Weights Saved To: {best_pt.resolve()}")

    # 7. Final Test Split Evaluation with Test-Time Augmentation (TTA)
    if best_pt.exists():
        print("\n" + "-" * 75)
        print("  Evaluating Best Model on Held-out Test Set (with TTA)...")
        print("-" * 75)
        best_model = YOLO(str(best_pt))
        test_res = best_model.val(data=data_yaml, split="test", imgsz=1280, augment=True, device=0)
        print(f"  Final Test Precision : {test_res.box.mp:.4f}")
        print(f"  Final Test Recall    : {test_res.box.mr:.4f}")
        print(f"  Final Test mAP@50    : {test_res.box.map50:.4f}")
        print(f"  Final Test mAP@50:95 : {test_res.box.map:.4f}")
        print("-" * 75)

if __name__ == "__main__":
    main()

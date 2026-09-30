import os
import torch
from pathlib import Path
from ultralytics import YOLO

def main():
    print("=" * 65)
    print("  AI SERVER YOLO11 FRESH TRAINING PIPELINE (Linux/Cloud)")
    print("=" * 65)
    
    # 1. Device Verification
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        gpu_name = torch.cuda.get_device_name(0)
        print(f"CUDA Available: True")
        print(f"Device Name:    {gpu_name}")
        print(f"GPU Count:      {gpu_count}")
        device = 0 if gpu_count == 1 else [i for i in range(gpu_count)]
    else:
        print("WARNING: CUDA not available. Running on CPU.")
        device = "cpu"
        
    # 2. Locate data.yaml or data_server.yaml
    yaml_candidates = [
        "data_server.yaml",
        "data.yaml",
        "RoadDamage_Fresh/data_server.yaml",
        "RoadDamage_Fresh/data.yaml"
    ]
    data_yaml = None
    for cand in yaml_candidates:
        if os.path.exists(cand):
            data_yaml = os.path.abspath(cand)
            break
            
    assert data_yaml is not None, f"Could not find data_server.yaml in {yaml_candidates}!"
    print(f"Dataset config: {data_yaml}")
    
    # 3. Model Initialization (Fresh from pretrained weights)
    print("\nLoading pretrained YOLO11 Nano backbone (yolo11n.pt)...")
    model = YOLO("yolo11n.pt")
    
    # 4. Determine batch size based on VRAM
    batch_size = 16
    if torch.cuda.is_available():
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        if vram_gb >= 24: # A100, RTX 3090, 4090, etc.
            batch_size = 64
        elif vram_gb >= 16: # V100, T4, RTX 4080
            batch_size = 32
        print(f"Detected VRAM: {vram_gb:.1f} GB -> Setting batch size to {batch_size}")
        
    # 5. Start Training
    print(f"\nLaunching training: epochs=100, imgsz=640, batch={batch_size}, device={device}...")
    results = model.train(
        data=data_yaml,
        epochs=100,
        imgsz=640,
        batch=batch_size,
        device=device,
        project="runs/detect",
        name="road_damage_fresh",
        patience=20,
        save=True,
        plots=True,
        workers=8
    )
    
    print("\nTraining completed successfully!")
    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    print(f"Best model weights saved to: {best_pt.resolve()}")
    
    # 6. Evaluation on Val and Test
    print("\n--- Evaluating Best Model on Test Split ---")
    best_model = YOLO(str(best_pt))
    test_res = best_model.val(data=data_yaml, split="test", device=device)
    print(f"Test Precision: {test_res.box.mp:.4f}")
    print(f"Test Recall:    {test_res.box.mr:.4f}")
    print(f"Test mAP@50:    {test_res.box.map50:.4f}")
    print(f"Test mAP@50:95: {test_res.box.map:.4f}")

if __name__ == "__main__":
    main()

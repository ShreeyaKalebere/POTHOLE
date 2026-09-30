import os
import sys
import shutil
import torch
from pathlib import Path
from ultralytics import YOLO
import pandas as pd
import cv2

def main():
    print("=" * 70)
    print("  ROAD DAMAGE DETECTION — FRESH YOLO11 GPU TRAINING (100 EPOCHS)")
    print("=" * 70)
    
    # 1. Device check
    if torch.cuda.is_available():
        device_id = 0
        device_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[*] CUDA Available  : True")
        print(f"[*] Hardware Device : {device_name} ({vram_gb:.2f} GB VRAM)")
    else:
        device_id = "cpu"
        print("[!] WARNING: CUDA not available. Training on CPU.")
        
    # 2. Check Data Config (prioritize local project dataset)
    local_candidates = [
        os.path.abspath("RoadDamage_Fresh/data.yaml"),
        os.path.abspath("dataset/RoadDamage_Fresh/data.yaml"),
        "F:/RoadDamage_Fresh/data.yaml",
    ]
    data_yaml = None
    for cand in local_candidates:
        if os.path.exists(cand):
            data_yaml = cand
            break
    assert data_yaml is not None, f"data.yaml not found in candidate paths: {local_candidates}!"
    print(f"[*] Dataset Config  : {data_yaml}")
    
    # 2. Checkpoint / Model Initialization
    last_weights = Path("runs/detect/road_damage_fresh/weights/last.pt").resolve()
    is_resuming = last_weights.exists() and ("--fresh" not in sys.argv)
    
    if is_resuming:
        print(f"\n[*] Resuming training from checkpoint: {last_weights}...")
        model = YOLO(str(last_weights))
    else:
        print("\n[*] Initializing fresh YOLO11 Nano model from pretrained weights: yolo11n.pt...")
        model = YOLO("yolo11n.pt")
    
    # 3. Setup real-time CSV sync callback
    root_csv = Path("training_results.csv").resolve()
    
    # Archive previous training_results.csv only when starting completely fresh
    if not is_resuming and root_csv.exists():
        archive_csv = Path("runs/archived/previous_training_results.csv")
        archive_csv.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(root_csv), str(archive_csv))
        print(f"[*] Archived previous training_results.csv to {archive_csv}")

    def on_fit_epoch_end_callback(trainer):
        try:
            if hasattr(trainer, "csv") and trainer.csv.exists():
                shutil.copy2(str(trainer.csv), str(root_csv))
                ep = trainer.epoch + 1
                tot = trainer.epochs
                print(f"\n>>> [EPOCH {ep}/{tot} COMPLETE] Metrics recorded -> {root_csv.name}")
        except Exception as e:
            print(f"[Warning] Could not sync CSV: {e}")

    model.add_callback("on_fit_epoch_end", on_fit_epoch_end_callback)
    
    # 4. Train
    project_dir = os.path.abspath("runs/detect")
    os.makedirs(project_dir, exist_ok=True)
    
    if is_resuming:
        print("\n" + "-" * 70)
        print("  Resuming 100-Epoch Training Pipeline...")
        print(f"  - Dataset       : {data_yaml}")
        print(f"  - Target Device : GPU ({device_id})" if device_id != "cpu" else "  - Target Device : CPU")
        print(f"  - Checkpoint    : {last_weights}")
        print(f"  - Results CSV   : {root_csv}")
        print("-" * 70 + "\n")
        train_results = model.train(resume=True)
    else:
        print("\n" + "-" * 70)
        print("  Starting Fresh 100-Epoch Training Pipeline...")
        print(f"  - Dataset       : {data_yaml}")
        print(f"  - Target Device : GPU ({device_id})" if device_id != "cpu" else "  - Target Device : CPU")
        print("  - Batch Size    : 16")
        print("  - Image Size    : 640x640")
        print("  - Epochs        : 100")
        print("  - Checkpoints   : Every 10 epochs + Best + Last")
        print("  - Early Stop    : Patience 50 epochs")
        print(f"  - Results CSV   : {root_csv}")
        print("-" * 70 + "\n")
        train_results = model.train(
            data=data_yaml,
            epochs=100,
            imgsz=640,
            batch=16,
            device=device_id,
            project=project_dir,
            name="road_damage_fresh",
            exist_ok=True,
            patience=50,
            save=True,
            save_period=10,
            plots=True,
            verbose=True,
            workers=4
        )
    
    print("\n" + "=" * 70)
    print("  TRAINING COMPLETED!")
    print(f"  Run directory: {train_results.save_dir}")
    print("=" * 70)
    
    # Ensure final CSV is copied
    run_csv = Path(train_results.save_dir) / "results.csv"
    if run_csv.exists():
        shutil.copy2(str(run_csv), str(root_csv))
        print(f"[*] Final results CSV successfully saved at: {root_csv}")
    
    # 5. Resolve Best Model
    best_weights = Path(train_results.save_dir) / "weights" / "best.pt"
    assert best_weights.exists(), f"best.pt not found at {best_weights}"
    print(f"[*] Best weights resolved: {best_weights}")
    
    os.makedirs("weights", exist_ok=True)
    shutil.copy2(str(best_weights), "weights/best.pt")
    print("[*] Copied best.pt to weights/best.pt for active project deployment.")
    
    # 6. Comprehensive Validation on Validation Split
    print("\n--- Running Final Validation Evaluation on Validation Split ---")
    best_model = YOLO(str(best_weights))
    val_metrics = best_model.val(data=data_yaml, split="val", device=device_id)
    
    mp = val_metrics.box.mp
    mr = val_metrics.box.mr
    map50 = val_metrics.box.map50
    map5095 = val_metrics.box.map
    f1 = (2 * mp * mr) / (mp + mr + 1e-16)
    
    print("\n================ VALIDATION SPLIT METRICS ================")
    print(f"Precision: {mp:.4f}")
    print(f"Recall:    {mr:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print(f"mAP@50:    {map50:.4f}")
    print(f"mAP@50:95: {map5095:.4f}")
    
    print("\n--- Per-Class Validation Breakdown ---")
    class_names = {0: "pothole", 1: "alligator_crack"}
    for cid, cname in class_names.items():
        c_m50 = val_metrics.box.maps50[cid] if cid < len(val_metrics.box.maps50) else float("nan")
        c_m = val_metrics.box.maps[cid] if cid < len(val_metrics.box.maps) else float("nan")
        print(f"Class {cid} ({cname}): mAP@50 = {c_m50:.4f}, mAP@50:95 = {c_m:.4f}")
        
    # 7. Evaluation on Unseen Test Split
    print("\n--- Running Evaluation on Unseen Test Split ---")
    test_metrics = best_model.val(data=data_yaml, split="test", device=device_id)
    print("\n================ TEST SPLIT METRICS ================")
    print(f"Precision: {test_metrics.box.mp:.4f}")
    print(f"Recall:    {test_metrics.box.mr:.4f}")
    print(f"mAP@50:    {test_metrics.box.map50:.4f}")
    print(f"mAP@50:95: {test_metrics.box.map:.4f}")
    
    # 8. Unseen Real-World / Kolhapur Test
    rw_dir = Path("real_world_test")
    if rw_dir.exists():
        print("\n--- Running Inference on Unseen Real-World Images ---")
        rw_results = best_model.predict(
            source=str(rw_dir),
            conf=0.25,
            save=True,
            project=str(Path(train_results.save_dir)),
            name="real_world_inference"
        )
        print(f"[*] Inference completed on {len(rw_results)} real-world test images.")
        
    print("\n================ ALL WORKFLOW STAGES COMPLETE ================")
    print(f"Check results table anytime by running: python view_training_results.py")
    print(f"All epoch metrics are recorded in: {root_csv}")

if __name__ == "__main__":
    main()

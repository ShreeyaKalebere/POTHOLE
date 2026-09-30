"""
Road Damage Detection — 4-GPU YOLO11-Medium Resumption Pipeline
==============================================================
Runs on GPUs 0, 1, 2, 3 (NVIDIA RTX A5000 x4)
"""
import os
import sys
import torch

def main():
    print("=" * 70)
    print("  RESUMING YOLO11-MEDIUM TRAINING ACROSS 4 GPUs (DDP)")
    print("=" * 70)

    from ultralytics import YOLO

    ckpt_path = os.path.expanduser("~/POTHOLE/runs/detect/runs/detect/road_damage_yolo11m_1280px/weights/last.pt")
    print(f"[*] Checkpoint path: {ckpt_path}")

    model = YOLO(ckpt_path)
    print("[*] Launching model.train(resume=True)...")
    model.train(resume=True)

if __name__ == "__main__":
    main()

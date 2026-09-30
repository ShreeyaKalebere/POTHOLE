"""
Training Results Viewer for Road Damage YOLO11 Model
=====================================================
Reads results.csv and displays clean tabular metrics per epoch,
identifying the best performing checkpoints.
Automatically syncs newest epochs from the AI server if reachable.
"""

import os
import sys
from pathlib import Path
import pandas as pd

def sync_from_server_if_possible():
    try:
        import paramiko
        from scp import SCPClient

        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect("172.16.21.51", 22, "pothole346", "Pothole@1234", timeout=2)

        cmd = 'find ~/POTHOLE -type f -name "results.csv" -printf "%T@ %p\\n" 2>/dev/null | sort -n | tail -n 1 | cut -d" " -f2-'
        stdin, stdout, stderr = c.exec_command(cmd)
        remote_csv = stdout.read().decode('utf-8', errors='replace').strip()

        if remote_csv:
            with SCPClient(c.get_transport()) as scp:
                scp.get(remote_csv, local_path="scratch/server_results.csv")
            
            # Combine with local history
            if os.path.exists("scratch/server_results.csv"):
                df_server = pd.read_csv("scratch/server_results.csv")
                df_server.columns = [col.strip() for col in df_server.columns]
                
                # If training_results.csv exists with earlier epochs, merge them
                if os.path.exists("training_results.csv"):
                    df_local = pd.read_csv("training_results.csv")
                    df_local.columns = [col.strip() for col in df_local.columns]
                    min_server_ep = df_server['epoch'].min()
                    df_earlier = df_local[df_local['epoch'] < min_server_ep]
                    df_combined = pd.concat([df_earlier, df_server], ignore_index=True)
                else:
                    df_combined = df_server
                    
                df_combined.to_csv("training_results.csv", index=False)
                df_combined.to_csv("runs/detect/road_damage_fresh/results.csv", index=False)
        c.close()
    except Exception:
        pass # Offline or unreachable, continue with local file

def find_results_csv():
    # If explicitly passed via CLI
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        arg_p = Path(sys.argv[1])
        if arg_p.exists():
            return arg_p

    candidates = [
        Path("training_results_100epochs.csv"),
        Path("training_results.csv"),
        Path("runs/server_results/results.csv"),
        Path("runs/detect/road_damage_fresh/results.csv"),
        Path("runs/train/road_damage_fresh/results.csv"),
    ]
    for p in candidates:
        if p.exists() and p.stat().st_size > 0:
            return p
    found = sorted(list(Path("runs").glob("**/results.csv")), key=lambda p: p.stat().st_mtime, reverse=True)
    if found:
        return found[0]
    return None

def main():
    sync_from_server_if_possible()

    csv_path = find_results_csv()
    if not csv_path:
        print("[!] No training results CSV found yet.")
        sys.exit(0)

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[!] Error reading {csv_path}: {e}")
        sys.exit(1)

    df.columns = [c.strip() for c in df.columns]

    print("\n" + "=" * 90)
    print(f"  YOLO11 TRAINING RESULTS — {csv_path.name.upper()} ({csv_path.resolve()})")
    print("=" * 90)

    if df.empty:
        print("[!] CSV file is currently empty.")
        return

    epoch_col = "epoch" if "epoch" in df.columns else df.columns[0]
    box_loss_col = "train/box_loss" if "train/box_loss" in df.columns else None
    cls_loss_col = "train/cls_loss" if "train/cls_loss" in df.columns else None
    val_box_col = "val/box_loss" if "val/box_loss" in df.columns else None
    val_cls_col = "val/cls_loss" if "val/cls_loss" in df.columns else None
    prec_col = "metrics/precision(B)" if "metrics/precision(B)" in df.columns else None
    rec_col = "metrics/recall(B)" if "metrics/recall(B)" in df.columns else None
    map50_col = "metrics/mAP50(B)" if "metrics/mAP50(B)" in df.columns else None
    map95_col = "metrics/mAP50-95(B)" if "metrics/mAP50-95(B)" in df.columns else None

    header = f"{'Epoch':^7} | {'Train Box':^10} | {'Train Cls':^10} | {'Val Box':^9} | {'Val Cls':^9} | {'Precision':^10} | {'Recall':^8} | {'mAP@50':^8} | {'mAP@50-95':^10}"
    print(header)
    print("-" * len(header))

    for _, row in df.iterrows():
        ep = int(row[epoch_col])
        t_box = f"{row[box_loss_col]:.4f}" if box_loss_col and pd.notna(row[box_loss_col]) else "N/A"
        t_cls = f"{row[cls_loss_col]:.4f}" if cls_loss_col and pd.notna(row[cls_loss_col]) else "N/A"
        v_box = f"{row[val_box_col]:.4f}" if val_box_col and pd.notna(row[val_box_col]) else "N/A"
        v_cls = f"{row[val_cls_col]:.4f}" if val_cls_col and pd.notna(row[val_cls_col]) else "N/A"
        prec = f"{row[prec_col]:.4f}" if prec_col and pd.notna(row[prec_col]) else "N/A"
        rec = f"{row[rec_col]:.4f}" if rec_col and pd.notna(row[rec_col]) else "N/A"
        m50 = f"{row[map50_col]:.4f}" if map50_col and pd.notna(row[map50_col]) else "N/A"
        m95 = f"{row[map95_col]:.4f}" if map95_col and pd.notna(row[map95_col]) else "N/A"

        print(f"{ep:^7} | {t_box:^10} | {t_cls:^10} | {v_box:^9} | {v_cls:^9} | {prec:^10} | {rec:^8} | {m50:^8} | {m95:^10}")

    print("-" * len(header))
    total_epochs = len(df)
    print(f"[*] Total Epochs Recorded : {total_epochs}")
    if map50_col and not df[map50_col].isna().all():
        best_50_row = df.loc[df[map50_col].idxmax()]
        print(f"[*] Best mAP@50 Checkpoint : Epoch {int(best_50_row[epoch_col])} -> mAP@50 = {best_50_row[map50_col]:.4f} (mAP@50:95 = {best_50_row[map95_col]:.4f})")
    print("=" * 90)

if __name__ == "__main__":
    main()

import os
import sys
import time
import socket
import argparse
import paramiko
from scp import SCPClient

DEFAULT_SERVER_HOST = "172.16.21.51"
DEFAULT_SERVER_PORT = 22
DEFAULT_SERVER_USER = "pothole346"
DEFAULT_SERVER_PASS = "Pothole@1234"

LOCAL_CHECKPOINT = r"runs\detect\road_damage_fresh\weights\last.pt"
LOCAL_ZIP_CANDIDATES = [
    r"F:\RoadDamage_Fresh_Server_21K.zip",
    r"RoadDamage_Fresh_Server_21K.zip",
    r"dataset\RoadDamage_Fresh_Server_21K.zip"
]
LOCAL_RESUME_SCRIPT = r"pipeline\train_server_resume.py"
LOCAL_LAUNCH_SCRIPT = r"run_resume_on_server.sh"
LOCAL_DATA_YAML = r"RoadDamage_Fresh\data_server.yaml"

REMOTE_DIR = "pothole_training"

def progress_callback(filename, size, sent):
    percent = (float(sent) / float(size)) * 100
    mb_sent = sent / (1024 * 1024)
    mb_total = size / (1024 * 1024)
    fname = filename.decode('utf-8') if isinstance(filename, bytes) else filename
    sys.stdout.write(f"\rUploading {fname}: {percent:.1f}% ({mb_sent:.1f}/{mb_total:.1f} MB)")
    sys.stdout.flush()

def run_ssh_command(ssh, cmd, stream_output=False):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    if stream_output:
        for line in iter(stdout.readline, ""):
            print(line, end="")
    output = stdout.read().decode("utf-8", errors="replace")
    error = stderr.read().decode("utf-8", errors="replace")
    exit_status = stdout.channel.recv_exit_status()
    return exit_status, output, error

def main():
    parser = argparse.ArgumentParser(description="Deploy and Resume YOLO11 Training on College AI Server")
    parser.add_argument("--host", default=DEFAULT_SERVER_HOST, help="Server IP or Hostname")
    parser.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT, help="SSH Port")
    parser.add_argument("--user", default=DEFAULT_SERVER_USER, help="SSH Username")
    parser.add_argument("--password", default=DEFAULT_SERVER_PASS, help="SSH Password")
    parser.add_argument("--epochs", type=int, default=100, help="Total target epochs (e.g. 100 or 150)")
    args = parser.parse_args()

    print("=" * 70)
    print("  DEPLOY RESUME TRAINING TO COLLEGE AI SERVER")
    print("=" * 70)
    print(f"Target Server : {args.user}@{args.host}:{args.port}")
    print(f"Remote Folder : ~/{REMOTE_DIR}")
    print(f"Target Epochs : {args.epochs} (Resuming from local epoch 50)")
    print("=" * 70)

    # 1. Verify local files
    if not os.path.exists(LOCAL_CHECKPOINT):
        print(f"[!] ERROR: Local checkpoint '{LOCAL_CHECKPOINT}' not found!")
        sys.exit(1)

    dataset_zip = None
    for cand in LOCAL_ZIP_CANDIDATES:
        if os.path.exists(cand):
            dataset_zip = cand
            break

    # 2. Test SSH Connection
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"\n[*] Connecting to {args.host}...")
    try:
        client.connect(
            hostname=args.host,
            port=args.port,
            username=args.user,
            password=args.password,
            timeout=8,
            auth_timeout=8,
            banner_timeout=12
        )
        print("[✓] SSH Connection Established Successfully!")
    except (socket.timeout, paramiko.ssh_exception.NoValidConnectionsError, TimeoutError) as e:
        print(f"\n[!] CONNECTION FAILED to {args.host}:{args.port}")
        print(f"    Reason: {e}")
        print("\n" + "=" * 70)
        print("  DIAGNOSIS & HOW TO FIX:")
        print("=" * 70)
        print(f"  '{args.host}' is an internal College LAN / Intranet IP address.")
        print("  To connect to it, you MUST either:")
        print("  1. Be connected to the College Wi-Fi / Lab LAN network.")
        print("  2. Be connected to the College VPN (if your college provides one).")
        print("  3. If your college has an external public IP or domain for the server,")
        print(f"     run: python pipeline/deploy_resume_to_server.py --host <NEW_IP_OR_DOMAIN>")
        print("=" * 70)
        sys.exit(1)
    except paramiko.ssh_exception.AuthenticationException:
        print(f"\n[!] Authentication failed for user '{args.user}'. Check your password.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Unexpected error: {e}")
        sys.exit(1)

    # 3. Check Remote GPU
    print("\n--- Remote Hardware Inspection ---")
    status, out, _ = run_ssh_command(client, "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")
    if status == 0 and out.strip():
        print(f"[✓] Detected Remote GPU(s):\n    {out.strip()}")
    else:
        print("[!] Warning: nvidia-smi failed or no GPU found.")

    # 4. Create remote directory
    run_ssh_command(client, f"mkdir -p ~/{REMOTE_DIR}")

    # 5. Check if dataset already exists remotely
    status, out, _ = run_ssh_command(client, f"test -d ~/{REMOTE_DIR}/images || test -f ~/{REMOTE_DIR}/RoadDamage_Fresh_Server_21K.zip && echo 'EXISTS'")
    already_has_dataset = "EXISTS" in out

    with SCPClient(client.get_transport(), progress=progress_callback) as scp:
        # Upload dataset only if needed
        if not already_has_dataset:
            if dataset_zip:
                print(f"\n[*] Uploading dataset archive {dataset_zip} (approx 3.3 GB)...")
                scp.put(dataset_zip, remote_path=f"{REMOTE_DIR}/RoadDamage_Fresh_Server_21K.zip")
                print("\n[✓] Dataset archive uploaded successfully!")
            else:
                print("\n[!] WARNING: Dataset zip not found locally and not on server.")
        else:
            print("\n[✓] Dataset archive/images already present on server. Skipping 3.3 GB upload!")

        # Upload checkpoint (last.pt)
        print(f"\n[*] Uploading local checkpoint '{LOCAL_CHECKPOINT}' (~16 MB)...")
        scp.put(LOCAL_CHECKPOINT, remote_path=f"{REMOTE_DIR}/last.pt")
        print("\n[✓] Checkpoint (last.pt) uploaded successfully!")

        # Upload scripts and config
        print("[*] Uploading training scripts & configs...")
        scp.put(LOCAL_RESUME_SCRIPT, remote_path=f"{REMOTE_DIR}/train_server_resume.py")
        scp.put(LOCAL_LAUNCH_SCRIPT, remote_path=f"{REMOTE_DIR}/run_resume_on_server.sh")
        if os.path.exists(LOCAL_DATA_YAML):
            scp.put(LOCAL_DATA_YAML, remote_path=f"{REMOTE_DIR}/data_server.yaml")
        print("[✓] Scripts uploaded successfully!")

    # 6. Make launch script executable
    run_ssh_command(client, f"chmod +x ~/{REMOTE_DIR}/run_resume_on_server.sh")

    # 7. Check for tmux
    status, _, _ = run_ssh_command(client, "which tmux")
    has_tmux = (status == 0)

    # 8. Launch training in detached session
    print("\n--- Launching Resume Training Pipeline ---")
    if has_tmux:
        run_ssh_command(client, "tmux kill-session -t yolo_resume 2>/dev/null || true")
        run_ssh_command(client, f"cd ~/{REMOTE_DIR} && tmux new-session -d -s yolo_resume './run_resume_on_server.sh {args.epochs} 2>&1 | tee training_resume.log'")
        print("[✓] Training successfully launched inside background tmux session 'yolo_resume'!")
    else:
        run_ssh_command(client, f"cd ~/{REMOTE_DIR} && nohup ./run_resume_on_server.sh {args.epochs} > training_resume.log 2>&1 &")
        print("[✓] Training successfully launched in background with nohup!")

    # 9. Wait 10 seconds and display initial log
    print("\n[*] Waiting 10 seconds for initial training startup logs...")
    time.sleep(10)
    _, log_preview, _ = run_ssh_command(client, f"cat ~/{REMOTE_DIR}/training_resume.log 2>/dev/null | tail -n 25")
    print("-" * 70)
    print(log_preview if log_preview.strip() else "Log starting up...")
    print("-" * 70)

    print("\n" + "=" * 70)
    print("  TRAINING IS NOW RUNNING INDEPENDENTLY ON THE AI SERVER!")
    print("=" * 70)
    print("You can close your laptop at any time without interrupting training.")
    print("\nTo monitor progress anytime:")
    if has_tmux:
        print(f"  1. SSH into server:  ssh {args.user}@{args.host}")
        print(f"  2. Attach to tmux:   tmux attach -t yolo_resume")
        print(f"     (To detach from tmux without stopping training: Press Ctrl+B, then release and press D)")
    else:
        print(f"  1. SSH into server:  ssh {args.user}@{args.host}")
        print(f"  2. View live log:    tail -f ~/{REMOTE_DIR}/training_resume.log")

    print(f"\nTo download the final completed best model when done:")
    print(f"  scp {args.user}@{args.host}:~/{REMOTE_DIR}/runs/detect/road_damage_fresh/weights/best.pt weights/best_server.pt")
    print("=" * 70)

    client.close()

if __name__ == "__main__":
    main()

import os
import sys
import time
import socket
import paramiko
from scp import SCPClient

SERVER_HOST = "172.16.20.79"
SERVER_PORT = 22
SERVER_USER = "pothole346"
SERVER_PASS = "Pothole@1234"

LOCAL_ZIP = r"F:\RoadDamage_Fresh_Server_21K.zip"
LOCAL_TRAIN_SCRIPT = r"c:\Users\shree\Downloads\POTHOLE\pipeline\train_server.py"
LOCAL_LAUNCH_SCRIPT = r"c:\Users\shree\Downloads\POTHOLE\train_on_server.sh"

REMOTE_DIR = "pothole_training"

def progress_callback(filename, size, sent):
    percent = (float(sent) / float(size)) * 100
    mb_sent = sent / (1024 * 1024)
    mb_total = size / (1024 * 1024)
    sys.stdout.write(f"\rUploading {filename.decode('utf-8') if isinstance(filename, bytes) else filename}: {percent:.1f}% ({mb_sent:.1f}/{mb_total:.1f} MB)")
    sys.stdout.flush()

def run_ssh_command(ssh, cmd, stream_output=False):
    print(f"\n[Remote Execution] $ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    if stream_output:
        for line in iter(stdout.readline, ""):
            print(line, end="")
    output = stdout.read().decode("utf-8", errors="replace")
    error = stderr.read().decode("utf-8", errors="replace")
    exit_status = stdout.channel.recv_exit_status()
    return exit_status, output, error

def main():
    print("=" * 65)
    print(f"Connecting to AI Server: {SERVER_USER}@{SERVER_HOST}:{SERVER_PORT}")
    print("=" * 65)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=SERVER_HOST,
            port=SERVER_PORT,
            username=SERVER_USER,
            password=SERVER_PASS,
            timeout=10,
            auth_timeout=10,
            banner_timeout=15
        )
        print("[SUCCESS] Connected to AI Server via SSH!")
    except (socket.timeout, paramiko.ssh_exception.NoValidConnectionsError, TimeoutError) as e:
        print(f"\n[ERROR] Connection timed out while trying to reach {SERVER_HOST}:22.")
        print(f"Details: {e}")
        print("\nDIAGNOSIS:")
        print(f"1. Your laptop is currently on IP 10.1.86.67, while the server is on private IP {SERVER_HOST}.")
        print("2. The server is not reachable from this network interface without a VPN or direct connection.")
        print("3. Please ensure:")
        print("   - You are connected to the lab/university Wi-Fi or local network that has access to 172.16.x.x.")
        print("   - If your institution provides a VPN, please connect to it.")
        sys.exit(1)
    except paramiko.ssh_exception.AuthenticationException:
        print(f"\n[ERROR] Authentication failed for user '{SERVER_USER}'. Please verify the password.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error connecting to server: {e}")
        sys.exit(1)

    # 1. System & GPU Check
    print("\n--- Inspecting Remote GPU & System ---")
    status, out, err = run_ssh_command(client, "nvidia-smi")
    if status == 0:
        print(out)
    else:
        print("nvidia-smi check returned status:", status)
        print("Warning: GPU driver might not be installed or no GPU attached.")

    # 2. Remote directory setup
    run_ssh_command(client, f"mkdir -p ~/{REMOTE_DIR}")

    # 3. Check if dataset already exists remotely
    status, out, _ = run_ssh_command(client, f"test -f ~/{REMOTE_DIR}/RoadDamage_Fresh_Server_21K.zip && echo 'EXISTS'")
    already_uploaded = "EXISTS" in out

    # 4. Upload files via SCP
    with SCPClient(client.get_transport(), progress=progress_callback) as scp:
        if not already_uploaded:
            print(f"\nUploading dataset archive: {LOCAL_ZIP} (~3.4 GB)...")
            scp.put(LOCAL_ZIP, remote_path=f"{REMOTE_DIR}/RoadDamage_Fresh_Server_21K.zip")
            print("\nDataset archive uploaded successfully!")
        else:
            print(f"\nDataset archive already exists in ~/{REMOTE_DIR}/! Skipping upload.")

        print("\nUploading training scripts...")
        scp.put(LOCAL_TRAIN_SCRIPT, remote_path=f"{REMOTE_DIR}/train_server.py")
        scp.put(LOCAL_LAUNCH_SCRIPT, remote_path=f"{REMOTE_DIR}/train_on_server.sh")
        print("\nScripts uploaded successfully!")

    # 5. Make launch script executable and verify tmux
    run_ssh_command(client, f"chmod +x ~/{REMOTE_DIR}/train_on_server.sh")
    status, _, _ = run_ssh_command(client, "which tmux")
    use_tmux = (status == 0)

    # 6. Launch training
    print("\n--- Launching Training Session ---")
    if use_tmux:
        # Kill existing session if any, then start detached session
        run_ssh_command(client, f"tmux kill-session -t yolo_training 2>/dev/null || true")
        run_ssh_command(client, f"cd ~/{REMOTE_DIR} && tmux new-session -d -s yolo_training './train_on_server.sh 2>&1 | tee training.log'")
        print("[SUCCESS] Training started inside tmux session 'yolo_training'!")
    else:
        # Fallback to nohup
        run_ssh_command(client, f"cd ~/{REMOTE_DIR} && nohup ./train_on_server.sh > training.log 2>&1 &")
        print("[SUCCESS] Training started in background via nohup!")

    # 7. Tail log for 10 seconds to monitor startup
    print("\nWaiting 10 seconds for initial training logs...")
    time.sleep(10)
    _, log_out, _ = run_ssh_command(client, f"cat ~/{REMOTE_DIR}/training.log | tail -n 25")
    print(log_out)

    print("\n" + "=" * 65)
    print("  AI SERVER TRAINING DEPLOYMENT COMPLETED!")
    print("=" * 65)
    print(f"To monitor training anytime from terminal:")
    if use_tmux:
        print(f"  ssh {SERVER_USER}@{SERVER_HOST}")
        print(f"  tmux attach -t yolo_training")
    else:
        print(f"  ssh {SERVER_USER}@{SERVER_HOST}")
        print(f"  tail -f ~/{REMOTE_DIR}/training.log")
    print("=" * 65)

    client.close()

if __name__ == "__main__":
    main()

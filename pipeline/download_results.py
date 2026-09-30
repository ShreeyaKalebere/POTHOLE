import os
import sys
import argparse
import paramiko
from scp import SCPClient

DEFAULT_SERVER_HOST = "172.16.21.51"
DEFAULT_SERVER_PORT = 22
DEFAULT_SERVER_USER = "pothole346"
DEFAULT_SERVER_PASS = "Pothole@1234"

def progress_callback(filename, size, sent):
    percent = (float(sent) / float(size)) * 100
    fname = filename.decode('utf-8') if isinstance(filename, bytes) else filename
    sys.stdout.write(f"\rDownloading {fname}: {percent:.1f}%")
    sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description="Download Completed Training Results from AI Server")
    parser.add_argument("--host", default=DEFAULT_SERVER_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT)
    parser.add_argument("--user", default=DEFAULT_SERVER_USER)
    parser.add_argument("--password", default=DEFAULT_SERVER_PASS)
    args = parser.parse_args()

    print("=" * 65)
    print("  DOWNLOADING COMPLETED MODEL & METRICS FROM AI SERVER")
    print("=" * 65)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=args.host,
            port=args.port,
            username=args.user,
            password=args.password,
            timeout=8
        )
        print("[OK] Connected to Server.")
    except Exception as e:
        print(f"[!] Connection failed: {e}")
        sys.exit(1)

    os.makedirs("weights", exist_ok=True)
    os.makedirs("runs/server_results", exist_ok=True)

    # Dynamically find the newest weights and results.csv on the server
    def find_latest_remote_file(pattern):
        cmd = f'find ~/POTHOLE -type f -name "{pattern}" -printf "%T@ %p\\n" 2>/dev/null | sort -n | tail -n 1 | cut -d" " -f2-'
        stdin, stdout, stderr = client.exec_command(cmd)
        res = stdout.read().decode('utf-8', errors='replace').strip()
        return res if res else None

    latest_best = find_latest_remote_file("best.pt")
    latest_last = find_latest_remote_file("last.pt")
    latest_csv = find_latest_remote_file("results.csv")
    latest_png = find_latest_remote_file("results.png")

    files_to_download = []
    if latest_best:
        files_to_download.append((latest_best, "weights/best_server_epoch100.pt"))
    if latest_last:
        files_to_download.append((latest_last, "weights/last_server_epoch100.pt"))
    if latest_csv:
        files_to_download.append((latest_csv, "runs/server_results/results.csv"))
    if latest_png:
        files_to_download.append((latest_png, "runs/server_results/results.png"))

    with SCPClient(client.get_transport(), progress=progress_callback) as scp:
        for rpath, lpath in files_to_download:
            try:
                print(f"\n[*] Fetching remote: {rpath}...")
                scp.get(rpath, local_path=lpath)
                print(f"\n[OK] Saved to: {lpath}")
            except Exception as e:
                print(f"\n[!] Note: could not fetch {rpath}: {e}")

    client.close()
    print("\n" + "=" * 65)
    print("  DOWNLOAD COMPLETED!")
    print("=" * 65)

if __name__ == "__main__":
    main()

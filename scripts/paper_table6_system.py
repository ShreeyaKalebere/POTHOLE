"""Table VI - system tests against a running backend (separate test database).
  1. zone assignment: 25 coordinates checked against the system's OWN rule (nearest zone centre,
     'Outside City' beyond 6 km). There are no official ward boundaries, so this is a
     rule-consistency test, not a ground-truth ward test.
  2. 50 incident-creating POST /api/detect requests -> success rate (HTTP 200 + JSON)
  3. 20 status updates PATCH /api/incidents/{id} -> success rate
  4. latency: request sent -> incident retrievable with GET /api/incidents/{id} (mean, median)
Run: python paper_table6_system.py http://localhost:8030
"""
import csv
import glob
import json
import math
import random
import statistics
import sys
import time
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, "F:/POTHOLE_PROJECT/backend")
from zones import ZONES, zone_for, haversine_m  # noqa: E402

API = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8030"
OUT = Path("F:/POTHOLE_PROJECT/paper_results")
random.seed(6)


def offset(lat, lng, metres, bearing_deg):
    b = math.radians(bearing_deg)
    return (lat + metres * math.cos(b) / 111_320, lng + metres * math.sin(b) / (111_320 * math.cos(math.radians(lat))))


def post_multipart(url, fields, file_path):
    b = uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{Path(file_path).name}"\r\n'
             "Content-Type: image/jpeg\r\n\r\n").encode() + Path(file_path).read_bytes() + b"\r\n" + f"--{b}--\r\n".encode()
    req = urllib.request.Request(url, body, {"Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, json.load(r)


def main():
    rows = []
    # ---------- 1. zones
    cases = []
    for name, (la, lo) in ZONES.items():
        cases.append(("zone centre", la, lo, name))
    for name, (la, lo) in list(ZONES.items())[:5]:
        # 150 m from the centre, towards the point farthest from every other centre
        cases.append(("150 m from centre", *offset(la, lo, 150, random.choice([0, 90, 180, 270])), name))
    for la, lo, label in [(16.8500, 74.2433, "~16 km north"), (16.5600, 74.2433, "~16 km south"),
                          (16.7050, 74.4000, "~17 km east"), (16.7050, 74.1000, "~15 km west"),
                          (18.5204, 73.8567, "Pune")]:
        cases.append((f"outside ({label})", la, lo, "Outside City"))
    names = list(ZONES)
    edge = []
    for i in range(3):   # midpoints between neighbouring centres: no ground truth, reported only
        a, b = ZONES[names[i]], ZONES[names[i + 1]]
        edge.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, f"{names[i]} | {names[i + 1]}"))
    correct = 0
    for kind, la, lo, expected in cases:
        got = zone_for(la, lo)
        ok = got == expected
        correct += ok
        rows.append(["zone", kind, f"{la:.6f},{lo:.6f}", expected, got, ok])
    for la, lo, pair in edge:
        rows.append(["zone", "edge midpoint (no ground truth)", f"{la:.6f},{lo:.6f}", f"either: {pair}", zone_for(la, lo), "n/a"])
    print(f"zone rule test: {correct}/{len(cases)} correct (+{len(edge)} edge points reported without ground truth)")

    # ---------- 2+4. 50 POST /api/detect with latency to GET visibility
    imgs = sorted(glob.glob("F:/POTHOLE_PROJECT/dataset/images/test/IndianRoads__*.jpg"))[:50]
    ok_post, latencies, inc_ids = 0, [], []
    for k, p in enumerate(imgs):
        la, lo = offset(16.705, 74.2433, 40 * k, (k * 37) % 360)      # spread out so they do not merge
        t0 = time.perf_counter()
        try:
            st, d = post_multipart(f"{API}/api/detect", {"lat": la, "lng": lo, "source": "papertest"}, p)
            if st == 200 and "detections" in d:
                ok_post += 1
                for det in d["detections"]:
                    if det.get("incident_id"):
                        while True:
                            with urllib.request.urlopen(f"{API}/api/incidents/{det['incident_id']}", timeout=30) as r:
                                if r.status == 200:
                                    break
                        latencies.append((time.perf_counter() - t0) * 1000)
                        inc_ids.append(det["incident_id"])
                        break
        except Exception as e:
            print("POST failed:", e)
    print(f"POST /api/detect: {ok_post}/{len(imgs)} succeeded; incidents created/merged: {len(inc_ids)}")

    # ---------- 3. 20 PATCH status updates
    ok_patch = 0
    statuses = ["In Progress", "Repaired", "Reported"]
    for k, iid in enumerate((inc_ids * 2)[:20]):
        body = json.dumps({"status": statuses[k % 3], "note": "paper test"}).encode()
        req = urllib.request.Request(f"{API}/api/incidents/{iid}", body, {"Content-Type": "application/json"}, method="PATCH")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                ok_patch += r.status == 200 and json.load(r).get("status") == statuses[k % 3]
        except Exception as e:
            print("PATCH failed:", e)
    print(f"PATCH status: {ok_patch}/{min(20, len(inc_ids) * 2)} succeeded")

    summary = {
        "zone_rule_correct": f"{correct}/{len(cases)}",
        "post_success": f"{ok_post}/{len(imgs)}",
        "patch_success": f"{ok_patch}/{min(20, len(inc_ids) * 2)}",
        "latency_ms_mean": round(statistics.mean(latencies), 1) if latencies else None,
        "latency_ms_median": round(statistics.median(latencies), 1) if latencies else None,
        "latency_samples": len(latencies),
        "latency_definition": "POST /api/detect sent -> incident returned by GET /api/incidents/{id}; includes upload, "
                              "CPU inference (GPU busy with training), DB write. No tracking.",
    }
    print(json.dumps(summary, indent=1))
    with open(OUT / "table6_zone_tests.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["test", "case", "lat,lng", "expected", "assigned", "correct"])
        w.writerows(rows)
    json.dump(summary, open(OUT / "table6_backend_summary.json", "w"), indent=1)


if __name__ == "__main__":
    main()

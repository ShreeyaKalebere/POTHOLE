import os
import sys
import time
import json
import argparse
from pathlib import Path
import cv2
from ultralytics import YOLO

def find_best_model_weights() -> str:
    """Find the most recent trained best.pt weights or fall back to yolo11n.pt."""
    candidates = sorted(
        list(Path("runs").glob("**/weights/best.pt")) +
        list(Path("runs").glob("**/weights/last.pt")),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    if candidates:
        return str(candidates[0])
    return "yolo11n.pt"

def estimate_severity(class_name: str, box_norm_area: float) -> str:
    """
    Heuristic severity estimation derived from normalized bounding-box area:
    - Pothole:
        * Low:    < 2% of frame (minor surface pitting)
        * Medium: 2% - 6% of frame (moderate depth hazard)
        * High:   >= 6% of frame (severe structural road crater)
    - Alligator Crack:
        * Low:    < 4% of frame (localized hairline mesh)
        * Medium: 4% - 10% of frame (interconnected fatigue cracking)
        * High:   >= 10% of frame (widespread pavement base failure)
    """
    cname = class_name.lower()
    if "pothole" in cname:
        if box_norm_area < 0.02:
            return "Low"
        elif box_norm_area < 0.06:
            return "Medium"
        else:
            return "High"
    elif "alligator" in cname or "crack" in cname:
        if box_norm_area < 0.04:
            return "Low"
        elif box_norm_area < 0.10:
            return "Medium"
        else:
            return "High"
    return "Medium"

def run_road_damage_tracking(
    model_path: str = None,
    video_source: str = "real_world_test",
    output_video: str = "tracked_road_damage.mp4",
    tracker_type: str = "bytetrack.yaml",
    conf_thresh: float = 0.25,
    save_video: bool = True,
    api_url: str = None
):
    """
    Downstream processing pipeline:
    1. Video Frame Capture via OpenCV (supports video file, folder of frames, or webcam index)
    2. YOLO11 Inference with Multi-Object Tracking (ByteTrack / BoT-SORT)
    3. Defect Re-Identification (Prevents duplicate counting of the same pothole)
    4. Image-Based Severity Assessment (Low/Medium/High)
    5. Structured Municipal Reporting JSON payload generation
    """
    if model_path is None or not Path(model_path).exists():
        model_path = find_best_model_weights()

    print(f"Loading YOLO11 weights from: {model_path}...")
    model = YOLO(model_path)
    class_names = model.names
    print(f"Model classes: {class_names}")

    reported_defects = {}
    video_writer = None

    print(f"Starting tracking inference on source: {video_source} using {tracker_type}...")

    results_stream = model.track(
        source=video_source,
        conf=conf_thresh,
        tracker=tracker_type,
        stream=True,
        verbose=False
    )

    for frame_idx, results in enumerate(results_stream):
        orig_img = results.orig_img.copy()
        h, w, _ = orig_img.shape
        boxes = results.boxes

        if boxes is not None and boxes.id is not None:
            track_ids = boxes.id.int().cpu().tolist()
            classes = boxes.cls.int().cpu().tolist()
            confs = boxes.conf.cpu().tolist()
            xyxy = boxes.xyxy.cpu().tolist()

            for tid, cid, conf, bbox in zip(track_ids, classes, confs, xyxy):
                cname = class_names.get(cid, str(cid))
                bw = (bbox[2] - bbox[0]) / float(w)
                bh = (bbox[3] - bbox[1]) / float(h)
                box_area = bw * bh
                severity = estimate_severity(cname, box_area)

                # Overlay box and label
                # Colors: Green for Low, Yellow/Orange for Medium, Red for High
                color = (0, 255, 0) if severity == "Low" else ((0, 165, 255) if severity == "Medium" else (0, 0, 255))
                x1, y1, x2, y2 = map(int, bbox)
                cv2.rectangle(orig_img, (x1, y1), (x2, y2), color, 2)
                tag = f"#{tid} {cname.upper()} [{severity}] {conf:.2f}"
                cv2.putText(orig_img, tag, (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # Deduplicate municipal events
                if tid not in reported_defects or conf > reported_defects[tid]["confidence"]:
                    event = {
                        "defect_id": tid,
                        "class_name": cname,
                        "severity": severity,
                        "confidence": round(conf, 4),
                        "frame_index": frame_idx,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "gps": {
                            "latitude": 16.7050,  # Kolhapur municipal civic anchor
                            "longitude": 74.2433
                        },
                        "zone": "Central Kolhapur",
                        "area": "Shahupuri",
                        "street": "Station Road, Shahupuri",
                        "bbox_norm": [round(bbox[0] / w, 4), round(bbox[1] / h, 4), round(bw, 4), round(bh, 4)]
                    }
                    reported_defects[tid] = event

        if save_video and video_source != "real_world_test":
            if video_writer is None:
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                video_writer = cv2.VideoWriter(output_video, fourcc, 25.0, (w, h))
            video_writer.write(orig_img)

    if video_writer is not None:
        video_writer.release()
        print(f"[VIDEO EXPORT] Saved tracked video output -> {output_video}")

    municipal_event_logs = list(reported_defects.values())
    print(f"\n[TRACKING SUMMARY] Logged {len(municipal_event_logs)} unique defects without duplicate counting.")

    # Save municipal reporting JSON payload
    out_json = Path("downstream_prototype/tracked_defects_output.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(municipal_event_logs, f, indent=2)
    print(f"Exported tracking event payload -> {out_json}")

    # Dispatch to FastAPI backend if URL provided
    if api_url and municipal_event_logs:
        import requests
        try:
            res = requests.post(api_url, json=municipal_event_logs, timeout=5)
            print(f"[API DISPATCH] Dispatched to {api_url}: Status {res.status_code}")
        except Exception as e:
            print(f"[API DISPATCH] Could not reach {api_url} ({e})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Road Damage Tracking & Municipal Reporting Prototype")
    parser.add_argument("--source", type=str, default="real_world_test", help="Video path, folder of frames, or webcam index (0)")
    parser.add_argument("--weights", type=str, default=None, help="Path to trained YOLO11 best.pt")
    parser.add_argument("--tracker", type=str, default="bytetrack.yaml", help="Tracker config (bytetrack.yaml or botsort.yaml)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--save-video", action="store_true", help="Save tracked video output to mp4")
    parser.add_argument("--api-url", type=str, default=None, help="Optional FastAPI endpoint (e.g. http://localhost:8000/api/defects/report)")
    args = parser.parse_args()

    run_road_damage_tracking(
        model_path=args.weights,
        video_source=args.source,
        tracker_type=args.tracker,
        conf_thresh=args.conf,
        save_video=args.save_video,
        api_url=args.api_url
    )


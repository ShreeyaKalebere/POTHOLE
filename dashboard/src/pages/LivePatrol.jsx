import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { SEV_COLOR, TYPE_LABEL } from "../api";

// Live Patrol: phone camera -> frames to backend (YOLO11 + ByteTrack) -> boxes drawn back on screen.
// Only one frame is "in flight" at a time, so the frame rate adapts to the network and GPU speed.
const SEND_WIDTH = 640;

export default function LivePatrol() {
  const videoRef = useRef(null);
  const overlayRef = useRef(null);
  const grabRef = useRef(null);
  const run = useRef({ on: false, sid: null, gps: null, save: true });
  const [running, setRunning] = useState(false);
  const [gps, setGps] = useState(null);
  const [gpsErr, setGpsErr] = useState("");
  const [stats, setStats] = useState(null);
  const [fps, setFps] = useState(0);
  const [log, setLog] = useState([]);
  const [err, setErr] = useState("");
  const [save, setSave] = useState(true);
  const [summary, setSummary] = useState(null);

  const secure = window.isSecureContext;

  useEffect(() => () => stop(), []); // stop camera when leaving the page

  async function start() {
    setErr("");
    setSummary(null);
    setLog([]);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
    } catch (e) {
      setErr("Camera not available: " + e.message);
      return;
    }
    if (navigator.geolocation) {
      run.current.watch = navigator.geolocation.watchPosition(
        (p) => {
          const g = { lat: p.coords.latitude, lng: p.coords.longitude, acc: Math.round(p.coords.accuracy) };
          run.current.gps = g;
          setGps(g);
          setGpsErr("");
        },
        (e) => setGpsErr(e.message),
        { enableHighAccuracy: true, maximumAge: 1000 }
      );
    }
    try {
      const r = await fetch("/api/live/start", { method: "POST" });
      if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
      const s = await r.json();
      run.current = { ...run.current, on: true, sid: s.session_id, save };
      setStats(s);
      setRunning(true);
      loop();
    } catch (e) {
      setErr("Backend: " + e.message);
      stopCamera();
    }
  }

  async function loop() {
    let last = performance.now();
    while (run.current.on) {
      const v = videoRef.current;
      if (!v || !v.videoWidth) {
        await new Promise((r) => setTimeout(r, 100));
        continue;
      }
      const c = grabRef.current;
      c.width = SEND_WIDTH;
      c.height = Math.round((v.videoHeight / v.videoWidth) * SEND_WIDTH);
      c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
      const blob = await new Promise((r) => c.toBlob(r, "image/jpeg", 0.75));
      const fd = new FormData();
      fd.append("session_id", run.current.sid);
      fd.append("file", blob, "frame.jpg");
      fd.append("save", run.current.save);
      if (run.current.gps) {
        fd.append("lat", run.current.gps.lat);
        fd.append("lng", run.current.gps.lng);
      }
      try {
        const r = await fetch("/api/live/frame", { method: "POST", body: fd });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail || r.statusText);
        if (!run.current.on) break;
        drawBoxes(d.detections, d.frame_size);
        setStats(d);
        if (d.new_incidents.length) {
          navigator.vibrate?.(200);
          setLog((l) => [...d.new_incidents.map((n) => ({ ...n, at: new Date() })), ...l].slice(0, 20));
        }
        const now = performance.now();
        setFps((f) => f * 0.8 + (1000 / (now - last)) * 0.2);
        last = now;
      } catch (e) {
        setErr(e.message);
        await new Promise((r) => setTimeout(r, 1000));
        if (String(e.message).includes("expired")) break;
      }
    }
  }

  function drawBoxes(dets, [fw, fh]) {
    const v = videoRef.current;
    const o = overlayRef.current;
    if (!v || !o) return;
    const cw = o.clientWidth;
    const ch = o.clientHeight;
    o.width = cw;
    o.height = ch;
    const scale = Math.min(cw / fw, ch / fh); // video uses object-fit: contain
    const ox = (cw - fw * scale) / 2;
    const oy = (ch - fh * scale) / 2;
    const ctx = o.getContext("2d");
    ctx.clearRect(0, 0, cw, ch);
    ctx.font = "600 14px Inter, sans-serif";
    for (const d of dets) {
      const [x1, y1, x2, y2] = d.bbox;
      const col = SEV_COLOR[d.severity];
      ctx.strokeStyle = col;
      ctx.lineWidth = d.confirmed ? 4 : 2;
      ctx.setLineDash(d.confirmed ? [] : [6, 4]);
      ctx.strokeRect(ox + x1 * scale, oy + y1 * scale, (x2 - x1) * scale, (y2 - y1) * scale);
      const label = `#${d.track_id ?? "-"} ${d.damage_type === "pothole" ? "Pothole" : "Alligator"} ${d.severity}`;
      const tw = ctx.measureText(label).width + 10;
      ctx.fillStyle = col;
      ctx.fillRect(ox + x1 * scale, oy + y1 * scale - 22, tw, 22);
      ctx.fillStyle = "#fff";
      ctx.fillText(label, ox + x1 * scale + 5, oy + y1 * scale - 6);
    }
  }

  function stopCamera() {
    const s = videoRef.current?.srcObject;
    s?.getTracks().forEach((t) => t.stop());
    if (videoRef.current) videoRef.current.srcObject = null;
    if (run.current.watch != null) navigator.geolocation.clearWatch(run.current.watch);
    overlayRef.current?.getContext("2d").clearRect(0, 0, 9999, 9999);
  }

  async function stop() {
    const sid = run.current.sid;
    run.current.on = false;
    setRunning(false);
    stopCamera();
    if (sid) {
      const fd = new FormData();
      fd.append("session_id", sid);
      try {
        const r = await fetch("/api/live/stop", { method: "POST", body: fd });
        setSummary(await r.json());
      } catch {}
      run.current.sid = null;
    }
  }

  return (
    <div className="live">
      <div className="live-top">
        <Link to="/" className="live-back">← Dashboard</Link>
        <b>Live Patrol</b>
        <span className={"live-pill " + (running ? "on" : "")}>{running ? "● LIVE" : "stopped"}</span>
      </div>

      <div className="live-stage">
        <video ref={videoRef} playsInline muted />
        <canvas ref={overlayRef} className="live-overlay" />
        <canvas ref={grabRef} hidden />
        {!running && !summary && (
          <div className="live-placeholder">
            {secure ? "Point the phone at the road and press Start" : (
              <>
                Camera &amp; GPS need a secure page.<br />
                On the laptop run <code>npm run dev:phone</code> and open the <b>https://</b> address on the phone.
              </>
            )}
          </div>
        )}
        {summary && !running && (
          <div className="live-placeholder">
            <div>
              <b>Patrol finished</b>
              <div>{summary.frames} frames · {summary.tracks} damages tracked</div>
              <div>{summary.incidents_saved} new incidents · {summary.incidents_merged} merged</div>
              <div>avg {summary.avg_inference_ms} ms / frame</div>
              <Link to="/worklist">Open worklist →</Link>
            </div>
          </div>
        )}
      </div>

      <div className="live-hud">
        <div><span>GPS</span>{gps ? `±${gps.acc} m` : gpsErr ? "denied" : "waiting"}</div>
        <div><span>FPS</span>{running ? fps.toFixed(1) : "–"}</div>
        <div><span>Tracks</span>{stats?.tracks ?? 0}</div>
        <div><span>Saved</span>{(stats?.incidents_saved ?? 0) + (stats?.incidents_merged ?? 0)}</div>
        <div><span>Zone</span>{stats?.zone ?? "–"}</div>
      </div>

      {err && <div className="live-err">{err}</div>}

      <div className="live-controls">
        {!running ? (
          <button className="btn primary big" onClick={start} disabled={!secure}>▶ Start patrol</button>
        ) : (
          <button className="btn danger big" onClick={stop}>■ Stop</button>
        )}
        <label className="check">
          <input type="checkbox" checked={save} disabled={running}
            onChange={(e) => { setSave(e.target.checked); run.current.save = e.target.checked; }} />
          Save incidents
        </label>
      </div>

      <div className="live-log">
        {log.map((n, k) => (
          <Link key={k} to={`/incident/${n.incident_id}`} className="live-log-row">
            <i style={{ background: SEV_COLOR[n.severity] }} />
            {TYPE_LABEL[n.damage_type]} · {n.severity} · {n.new_incident ? "new" : "merged"}
            <span className="muted">{n.at.toLocaleTimeString()}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}

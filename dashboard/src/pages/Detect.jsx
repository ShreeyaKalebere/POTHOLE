import { useState } from "react";
import { Link } from "react-router-dom";
import { api, TYPE_LABEL } from "../api";
import { SevBadge } from "../components";

export default function Detect() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [save, setSave] = useState(true);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState("");

  const pick = (f) => {
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setRes(null);
    setErr("");
  };

  const useMyLocation = () => {
    if (!navigator.geolocation) return setErr("This browser has no GPS access");
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setLat(p.coords.latitude.toFixed(6));
        setLng(p.coords.longitude.toFixed(6));
      },
      (e) => setErr("Location permission denied: " + e.message),
      { enableHighAccuracy: true }
    );
  };

  const run = async () => {
    setBusy(true);
    setErr("");
    try {
      setRes(await api.detect(file, lat, lng, save));
    } catch (e) {
      setErr(e.message);
    }
    setBusy(false);
  };

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Detect Road Damage</h1>
          <p className="muted">Upload a road photo. GPS is read from the photo automatically if your phone saved it.</p>
        </div>
      </header>

      <div className="grid two">
        <div className="card">
          <label
            className="drop"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              pick(e.dataTransfer.files[0]);
            }}
          >
            <input type="file" accept="image/*" capture="environment" onChange={(e) => pick(e.target.files[0])} hidden />
            {preview ? <img src={preview} alt="" /> : <span>📷 Click or drop a road photo here</span>}
          </label>

          <div className="form" style={{ marginTop: 14 }}>
            <div className="row gap">
              <div className="grow">
                <label>Latitude</label>
                <input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="auto from photo" />
              </div>
              <div className="grow">
                <label>Longitude</label>
                <input value={lng} onChange={(e) => setLng(e.target.value)} placeholder="auto from photo" />
              </div>
            </div>
            <div className="row gap">
              <button className="btn" onClick={useMyLocation}>📍 Use my location</button>
              <label className="check">
                <input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} /> Save as incidents
              </label>
            </div>
            <button className="btn primary big" disabled={!file || busy} onClick={run}>
              {busy ? "Detecting…" : "Run detection"}
            </button>
            {err && <div className="notice error">{err}</div>}
          </div>
        </div>

        <div className="card">
          <h3>Result</h3>
          {!res && <p className="muted">Detections will appear here.</p>}
          {res && (
            <>
              <img className="det-img" src={res.annotated_url} alt="result" />
              <div className="row gap small muted" style={{ margin: "8px 0" }}>
                <span>{res.count} found</span>
                <span>· {res.inference_ms} ms</span>
                <span>· GPS: {res.lat != null ? `${res.lat}, ${res.lng} (${res.gps_source})` : "none"}</span>
                <span>· Zone: {res.zone}</span>
              </div>
              {res.model?.provisional && (
                <div className="notice warn">Model is still training — results will improve after training finishes.</div>
              )}
              {res.lat == null && save && res.count > 0 && (
                <div className="notice warn">Saved without GPS — these incidents will not appear on the map.</div>
              )}
              <table className="tbl compact">
                <tbody>
                  {res.detections.map((d, k) => (
                    <tr key={k}>
                      <td>{TYPE_LABEL[d.damage_type]}</td>
                      <td><SevBadge s={d.severity} /></td>
                      <td>{(d.confidence * 100).toFixed(0)}%</td>
                      <td>
                        {d.incident_id ? (
                          <Link to={`/incident/${d.incident_id}`}>{d.new_incident ? "New incident →" : "Merged into existing →"}</Link>
                        ) : <span className="muted">not saved</span>}
                      </td>
                    </tr>
                  ))}
                  {!res.count && <tr><td className="muted">No road damage detected.</td></tr>}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </>
  );
}

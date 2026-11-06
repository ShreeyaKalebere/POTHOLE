import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { IconMapPin, IconPhotoUp } from "@tabler/icons-react";
import { api, fmtDate, TYPE_LABEL } from "../api";
import logoUrl from "../assets/margdrishti_logo.svg";

const CITY = [16.705, 74.2433];
const pin = new L.Icon({ iconUrl: markerIcon, shadowUrl: markerShadow, iconSize: [25, 41], iconAnchor: [12, 41], shadowSize: [41, 41] });

export default function Citizen() {
  const { pathname } = useLocation();
  const trackMatch = pathname.match(/^\/track\/?(.*)$/);
  return (
    <div className="public">
      <header className="public-top">
        <Link to="/" className="public-brand">
          <img className="logo" src={logoUrl} alt="MargDrishti logo" />
          <span>
            <span className="brand-title">MargDrishti</span>
            <span className="brand-sub">Report road damage in Kolhapur</span>
          </span>
        </Link>
        <Link className="btn" to="/#login">Staff login</Link>
      </header>
      <main className="public-main">
        <div className="public-tabs" role="tablist">
          <Link role="tab" aria-selected={!trackMatch} className={"public-tab" + (trackMatch ? "" : " on")} to="/report">Report damage</Link>
          <Link role="tab" aria-selected={!!trackMatch} className={"public-tab" + (trackMatch ? " on" : "")} to="/track">Track a report</Link>
        </div>
        {trackMatch ? <Track initial={decodeURIComponent(trackMatch[1] || "")} /> : <Report />}
      </main>
    </div>
  );
}

function FitPin({ pos }) {
  const map = useMap();
  useEffect(() => {
    if (pos) map.setView(pos, Math.max(map.getZoom(), 16));
  }, [pos, map]);
  return null;
}

function PickOnClick({ onPick }) {
  useMapEvents({ click: (e) => onPick([e.latlng.lat, e.latlng.lng]) });
  return null;
}

function Report() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [pos, setPos] = useState(null);
  const [kind, setKind] = useState("pothole");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [locating, setLocating] = useState(false);
  const [done, setDone] = useState(null);

  const pick = (f) => {
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setErr("");
  };

  const useMyLocation = () => {
    if (!navigator.geolocation) return setErr("This browser cannot read your location. Please tap the map instead.");
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setPos([p.coords.latitude, p.coords.longitude]);
        setErr("");
        setLocating(false);
      },
      () => {
        setErr("Could not read your location. Please tap the place on the map instead.");
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 12000 }
    );
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      setDone(await api.citizenReport(file, pos, kind, note));
    } catch (ex) {
      setErr(ex.message);
    }
    setBusy(false);
  };

  if (done) {
    return (
      <div className="card done-card">
        <h1>Report received</h1>
        <p className="muted">Keep this tracking number to check progress.</p>
        <div className="track-code">{done.code}</div>
        <p>Sent to the {done.zone} ward.</p>
        <p className="muted small">
          {done.ai_found ? "Our system also detected road damage in your photo." : "An officer will review your photo."}
        </p>
        <div className="row gap">
          <Link className="btn primary" to={`/track/${done.code}`}>Track this report</Link>
          <button className="btn" onClick={() => { setDone(null); setFile(null); setPreview(null); setPos(null); setNote(""); }}>Report another</button>
        </div>
      </div>
    );
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h1>Report road damage</h1>
      <p className="muted">No account needed. Please avoid including people or vehicle number plates in your photo.</p>
      <h3 className="step">1. Add a photo</h3>
      <label className="drop public-drop">
        <input type="file" accept="image/*" onChange={(e) => pick(e.target.files[0])} hidden />
        {preview ? <img src={preview} alt="Your selected road photo" /> : <span className="drop-hint"><IconPhotoUp size={34} stroke={1.5} aria-hidden="true" />Take or choose a photo</span>}
      </label>
      <h3 className="step">2. Mark the location</h3>
      <button type="button" className="btn" onClick={useMyLocation} disabled={locating}>
        <IconMapPin size={17} stroke={1.8} aria-hidden="true" />{locating ? "Finding you…" : "Use my location"}
      </button>
      <p className="muted small">Or tap the map where the damage is.</p>
      <div className="pick-map">
        <MapContainer center={pos || CITY} zoom={13} style={{ height: "100%", width: "100%" }} scrollWheelZoom={false}>
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <PickOnClick onPick={setPos} />
          <FitPin pos={pos} />
          {pos && <Marker position={pos} icon={pin} />}
        </MapContainer>
      </div>
      <p className="muted small" aria-live="polite">{pos ? `Location set: ${pos[0].toFixed(5)}, ${pos[1].toFixed(5)}` : "No location set yet. We will try the photo's location if it has one."}</p>
      <h3 className="step">3. Add details</h3>
      <label htmlFor="report-kind">Type of damage</label>
      <select id="report-kind" value={kind} onChange={(e) => setKind(e.target.value)}>
        <option value="pothole">{TYPE_LABEL.pothole}</option>
        <option value="alligator_crack">Road cracks</option>
      </select>
      <label htmlFor="report-note">Anything else? (optional)</label>
      <textarea id="report-note" rows={2} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Near the bus stop, deep and hard to see at night" />
      {err && <div className="notice error" role="alert">{err}</div>}
      <button className="btn primary big" disabled={!file || busy}>{busy ? "Sending…" : "Send report"}</button>
    </form>
  );
}

function Track({ initial }) {
  const [code, setCode] = useState(initial);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const look = async (value) => {
    setBusy(true);
    setErr("");
    setRes(null);
    try {
      setRes(await api.citizenTrack(value));
    } catch (ex) {
      setErr(ex.message);
    }
    setBusy(false);
  };

  useEffect(() => {
    setCode(initial);
    if (initial) look(initial);
  }, [initial]);

  return (
    <div className="card form">
      <h1>Track a report</h1>
      <form className="track-form" onSubmit={(e) => { e.preventDefault(); navigate(`/track/${encodeURIComponent(code.trim())}`); if (code.trim() === initial) look(initial); }}>
        <label className="sr-only" htmlFor="track-code">Tracking number</label>
        <input id="track-code" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="MD-ABCD2345" autoCapitalize="characters" />
        <button className="btn primary" disabled={!code.trim() || busy}>{busy ? "Checking…" : "Check"}</button>
      </form>
      {err && <div className="notice error" role="alert">{err}</div>}
      {res && (
        <div className="track-result">
          <p><b>{res.code}</b><br /><span className="muted small">{res.zone} ward · sent {fmtDate(res.submitted_at)}</span></p>
          {res.items.map((it, k) => (
            <div key={k} className="track-item">
              <div className="row gap">
                <b>{TYPE_LABEL[it.type]}</b>
                <span className={"badge st-" + it.status.replace(" ", "-")}>{it.status}</span>
              </div>
              {it.needs_review && <p className="muted small">Waiting for an officer to review your photo.</p>}
              <ol className="steps">
                {it.steps.map((s, i) => <li key={i}><b>{s.status}</b><span className="muted small">{fmtDate(s.at)}</span></li>)}
              </ol>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import { Link } from "react-router-dom";
import { useEffect } from "react";
import { SEV_COLOR, TYPE_LABEL, fmtDate } from "./api";

export const SevBadge = ({ s }) => (
  <span className={"badge sev-" + s}>{s}</span>
);

export const StatusBadge = ({ s }) => (
  <span className={"badge st-" + s.replace(" ", "-")}>{s}</span>
);

export const TypeTag = ({ t }) => <span className={"type " + t}>{TYPE_LABEL[t] || t}</span>;

export function StatTile({ tone, value, label }) {
  return (
    <div className={`tile ${tone}`}>
      <div className="tile-value">{value ?? "–"}</div>
      <div className="tile-label">{label}</div>
    </div>
  );
}

// Zoom to the markers only when the set of incidents changes (filters / zone),
// not on every auto-refresh, so the user's pan & zoom is kept.
function FitBounds({ items }) {
  const map = useMap();
  const key = items.map((i) => i.id).sort().join(",");
  useEffect(() => {
    const pts = items.filter((i) => i.lat != null).map((i) => [i.lat, i.lng]);
    if (pts.length) map.fitBounds(pts, { padding: [30, 30], maxZoom: 16 });
  }, [key, map]);
  return null;
}

// Later markers draw on top, so the most dangerous open damage stays visible
const markerRank = (i) => (i.status === "Repaired" ? 0 : { Low: 1, Medium: 2, High: 3 }[i.severity] ?? 1);

export function IncidentMap({ items, height = 420, center = [16.705, 74.2433], touchPan = true }) {
  return (
    <div className="map-wrap" style={{ height }}>
      <MapContainer center={center} zoom={13} style={{ height: "100%", width: "100%" }} scrollWheelZoom={!L.Browser.mobile} dragging={touchPan || !L.Browser.mobile}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds items={items} />
        {items
          .filter((i) => i.lat != null)
          .sort((a, b) => markerRank(a) - markerRank(b))
          .map((i) => (
            <CircleMarker
              key={i.id}
              center={[i.lat, i.lng]}
              radius={(i.status === "Repaired" ? 3.5 : i.severity === "High" ? 6 : i.severity === "Medium" ? 5 : 4) * (L.Browser.mobile ? 0.75 : 1)}
              pathOptions={{
                color: "#fff",
                weight: 1,
                fillColor: i.status === "Repaired" ? "#1e9a5b" : SEV_COLOR[i.severity],
                fillOpacity: 0.9,
              }}
            >
              <Popup>
                <div className="pop">
                  <img src={i.images?.[0]?.annotated_url} alt="" />
                  <b>{i.incident_code}</b> · {TYPE_LABEL[i.damage_type]}
                  <div>
                    <SevBadge s={i.severity} /> <StatusBadge s={i.status} />
                  </div>
                  <div className="muted">
                    {i.zone} · {fmtDate(i.detected_at)}
                  </div>
                  <Link to={`/incident/${i.id}`}>Inspect and dispatch</Link>
                </div>
              </Popup>
            </CircleMarker>
          ))}
      </MapContainer>
      <div className="legend">
        {["High", "Medium", "Low"].map((s) => (
          <span key={s}>
            <i style={{ background: SEV_COLOR[s] }} />
            {s}
          </span>
        ))}
        <span>
          <i style={{ background: "#1e9a5b" }} />
          Repaired
        </span>
      </div>
    </div>
  );
}

export function Filters({ f, setF, show = ["type", "severity", "status"] }) {
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <div className="filters">
      {show.includes("type") && (
        <select value={f.damage_type || ""} onChange={set("damage_type")}>
          <option value="">All types</option>
          <option value="pothole">Pothole</option>
          <option value="alligator_crack">Alligator Crack</option>
        </select>
      )}
      {show.includes("severity") && (
        <select value={f.severity || ""} onChange={set("severity")}>
          <option value="">All severities</option>
          <option>High</option>
          <option>Medium</option>
          <option>Low</option>
        </select>
      )}
      {show.includes("status") && (
        <select value={f.status || ""} onChange={set("status")}>
          <option value="">All statuses</option>
          <option>Reported</option>
          <option>In Progress</option>
          <option>Repaired</option>
        </select>
      )}
      {show.includes("dates") && (
        <>
          <input type="date" value={f.date_from || ""} onChange={set("date_from")} title="From" />
          <input type="date" value={f.date_to || ""} onChange={set("date_to")} title="To" />
        </>
      )}
    </div>
  );
}

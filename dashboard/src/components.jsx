import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import { Link } from "react-router-dom";
import { useEffect } from "react";
import { SEV_COLOR, STATUS_COLOR, TYPE_LABEL, fmtDate } from "./api";

export const SevBadge = ({ s }) => (
  <span className="badge" style={{ background: SEV_COLOR[s] + "22", color: SEV_COLOR[s] }}>
    {s}
  </span>
);

export const StatusBadge = ({ s }) => (
  <span className="badge" style={{ background: STATUS_COLOR[s] + "22", color: STATUS_COLOR[s] }}>
    {s}
  </span>
);

export const TypeTag = ({ t }) => <span className={"type " + t}>{TYPE_LABEL[t] || t}</span>;

export function StatCard({ label, value, sub, accent }) {
  return (
    <div className="card stat" style={accent ? { borderTop: `3px solid ${accent}` } : undefined}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value ?? "–"}</div>
      {sub && <div className="stat-sub">{sub}</div>}
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

export function IncidentMap({ items, height = 420, center = [16.705, 74.2433] }) {
  return (
    <div className="map-wrap" style={{ height }}>
      <MapContainer center={center} zoom={13} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds items={items} />
        {items
          .filter((i) => i.lat != null)
          .map((i) => (
            <CircleMarker
              key={i.id}
              center={[i.lat, i.lng]}
              radius={i.severity === "High" ? 9 : i.severity === "Medium" ? 7 : 5}
              pathOptions={{
                color: i.status === "Repaired" ? "#8b8d98" : "#fff",
                weight: 2,
                fillColor: i.status === "Repaired" ? "#b9bbc6" : SEV_COLOR[i.severity],
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
                  <Link to={`/incident/${i.id}`}>Inspect &amp; dispatch →</Link>
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
          <i style={{ background: "#b9bbc6" }} />
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

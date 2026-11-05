import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, SEV_COLOR, STATUS_COLOR, TYPE_LABEL } from "../api";
import { IncidentMap, SevBadge, StatTile } from "../components";

export default function Dashboard({ zone }) {
  const [s, setS] = useState(null);
  const [items, setItems] = useState([]);
  const [err, setErr] = useState("");

  const load = () => {
    Promise.all([api.stats(zone), api.incidents({ zone, limit: 1000 })])
      .then(([st, inc]) => {
        setS(st);
        setItems(inc.items);
        setErr("");
      })
      .catch((e) => setErr(e.message));
  };
  useEffect(() => {
    load();
    const t = setInterval(load, 20000); // live refresh
    return () => clearInterval(t);
  }, [zone]);

  if (err) return <Empty msg={`Cannot reach backend: ${err}. Is "uvicorn main:app" running?`} />;
  if (!s) return <div className="muted pad">Loading…</div>;

  const sev = ["High", "Medium", "Low"].map((k) => ({ name: k, value: s.by_severity[k] || 0 }));
  const status = ["Reported", "In Progress", "Repaired"].map((k) => ({ name: k, value: s.by_status[k] || 0 }));
  const zonesData = Object.entries(s.by_zone)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
  const priority = items.filter((i) => i.status !== "Repaired").slice(0, 6);

  const trend = s.trend.map((d) => ({ date: d.date, total: d.pothole + d.alligator_crack }));

  return (
    <>
      {s.total === 0 && (
        <div className="card notice">
          No incidents yet. Upload a road photo on <Link to="/detect">Detect damage</Link>, or load demo data from{" "}
          <Link to="/reports">Reports</Link>.
        </div>
      )}

      <div className="bento">
        <div className="tiles">
          <StatTile tone="peach" value={s.high_open} label="High hazard open" />
          <StatTile tone="lemon" value={s.open} label="Open" />
          <StatTile tone="mint" value={s.repaired} label={`Repaired${s.total ? `, ${Math.round((s.repaired / s.total) * 100)}%` : ""}`} />
          <StatTile tone="sky" value={s.by_status["In Progress"] || 0} label="In progress" />
          <div className="tile lav strip">
            <b>{s.by_type.pothole || 0} potholes</b>
            <b>{s.by_type.alligator_crack || 0} alligator cracks</b>
          </div>
        </div>
        <div className="bento-map">
          <IncidentMap items={items} height="100%" touchPan={false} />
          <Link className="map-open" to="/map">Open full map</Link>
        </div>
      </div>

      <div className="grid lower">
        <div className="card">
          <div className="card-head">
            <h3>Repair first</h3>
            <Link to="/worklist">Worklist</Link>
          </div>
          <div className="queue">
            {priority.map((i) => (
              <Link key={i.id} className="queue-row" to={`/incident/${i.id}`}>
                <span>
                  <b>{i.incident_code}</b>
                  <small>{i.zone} · {TYPE_LABEL[i.damage_type]}</small>
                </span>
                <SevBadge s={i.severity} />
              </Link>
            ))}
            {!priority.length && <p className="muted">Nothing open.</p>}
          </div>
        </div>
        <div className="card">
          <h3>Top wards</h3>
          <div className="ward-list">
            {zonesData.slice(0, 8).map((z) => (
              <div key={z.name}><span>{z.name}</span><b>{z.value}</b></div>
            ))}
          </div>
        </div>
        <div className="card">
          <h3>Last 30 days</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={trend} margin={{ left: -18, right: 6, top: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--line)" />
              <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} tickLine={false} axisLine={false} fontSize={12} minTickGap={36} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={12} />
              <Tooltip />
              <Area type="linear" dataKey="total" name="Detections" stroke="#37287a" strokeWidth={2} fill="#e2dbff" fillOpacity={1} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid two-even">
        <div className="card">
          <h3>Severity</h3>
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={sev} margin={{ left: -18, top: 6 }}>
              <CartesianGrid vertical={false} stroke="var(--line)" />
              <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={12} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={12} />
              <Tooltip cursor={{ fill: "#f6f4ef" }} />
              <Bar dataKey="value" name="Defects" radius={[8, 8, 0, 0]} maxBarSize={72} isAnimationActive={false}>
                {sev.map((d) => <Cell key={d.name} fill={SEV_COLOR[d.name]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <h3>Repair status</h3>
          <ResponsiveContainer width="100%" height={210}>
            <PieChart>
              <Pie data={status} dataKey="value" nameKey="name" innerRadius={52} outerRadius={80} paddingAngle={2} isAnimationActive={false}>
                {status.map((d) => <Cell key={d.name} fill={STATUS_COLOR[d.name]} />)}
              </Pie>
              <Tooltip />
              <Legend iconType="circle" />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
      <p className="muted small refresh">{zone === "All" ? "All Kolhapur zones" : zone} · refreshes every 20 seconds</p>
    </>
  );
}

const Empty = ({ msg }) => <div className="card notice error">{msg}</div>;

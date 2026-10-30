import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, SEV_COLOR, STATUS_COLOR, TYPE_LABEL, fmtDate } from "../api";
import { IncidentMap, SevBadge, StatCard, StatusBadge, TypeTag } from "../components";

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

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Road Defect Dashboard</h1>
          <p className="muted">{zone === "All" ? "All Kolhapur zones" : zone} · auto-refreshes every 20 s</p>
        </div>
        <Link className="btn primary" to="/detect">+ Detect damage</Link>
      </header>

      {s.total === 0 && (
        <div className="card notice">
          No incidents yet. Upload a road photo on <Link to="/detect">Detect Damage</Link>, or load demo data from{" "}
          <Link to="/reports">Reports</Link>.
        </div>
      )}

      <div className="grid stats">
        <StatCard label="Total defects" value={s.total} sub={`${s.open} open`} />
        <StatCard label="Potholes" value={s.by_type.pothole || 0} accent="#3e63dd" />
        <StatCard label="Alligator cracks" value={s.by_type.alligator_crack || 0} accent="#8e4ec6" />
        <StatCard label="High-hazard open" value={s.high_open} sub="needs priority repair" accent={SEV_COLOR.High} />
        <StatCard label="Repaired" value={s.repaired} sub={s.total ? `${Math.round((s.repaired / s.total) * 100)}% resolved` : ""} accent={STATUS_COLOR.Repaired} />
      </div>

      <div className="grid two">
        <div className="card">
          <div className="card-head">
            <h3>Interactive road map</h3>
            <Link to="/map">Full map →</Link>
          </div>
          <IncidentMap items={items} height={380} />
        </div>
        <div className="card">
          <div className="card-head">
            <h3>Priority repairs</h3>
            <Link to="/worklist">Worklist →</Link>
          </div>
          <table className="tbl compact">
            <tbody>
              {priority.map((i) => (
                <tr key={i.id}>
                  <td>
                    <Link to={`/incident/${i.id}`}><b>{i.incident_code}</b></Link>
                    <div className="muted small">{i.zone} · {fmtDate(i.detected_at)}</div>
                  </td>
                  <td><TypeTag t={i.damage_type} /></td>
                  <td><SevBadge s={i.severity} /></td>
                  <td><StatusBadge s={i.status} /></td>
                </tr>
              ))}
              {!priority.length && <tr><td className="muted">Nothing open 🎉</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid three">
        <div className="card">
          <h3>Severity</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={sev}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--line)" />
              <XAxis dataKey="name" tickLine={false} axisLine={false} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={30} />
              <Tooltip />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {sev.map((d) => <Cell key={d.name} fill={SEV_COLOR[d.name]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <h3>Repair status</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={status} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
                {status.map((d) => <Cell key={d.name} fill={STATUS_COLOR[d.name]} />)}
              </Pie>
              <Tooltip />
              <Legend iconType="circle" />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <h3>Defects by zone</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={zonesData} layout="vertical" margin={{ left: 20 }}>
              <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="name" width={100} tickLine={false} axisLine={false} fontSize={12} />
              <Tooltip />
              <Bar dataKey="value" fill="#3e63dd" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <h3>Detections — last 30 days</h3>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={s.trend}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--line)" />
            <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} tickLine={false} axisLine={false} fontSize={12} />
            <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={30} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="pothole" name={TYPE_LABEL.pothole} stroke="#3e63dd" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="alligator_crack" name={TYPE_LABEL.alligator_crack} stroke="#8e4ec6" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}

const Empty = ({ msg }) => <div className="card notice error">{msg}</div>;

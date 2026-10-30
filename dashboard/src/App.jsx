import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api";
import Dashboard from "./pages/Dashboard.jsx";
import MapPage from "./pages/MapPage.jsx";
import Worklist from "./pages/Worklist.jsx";
import IncidentDetail from "./pages/IncidentDetail.jsx";
import Detect from "./pages/Detect.jsx";
import Reports from "./pages/Reports.jsx";
import LivePatrol from "./pages/LivePatrol.jsx";
import Login from "./pages/Login.jsx";

const NAV = [
  ["/", "Dashboard", "▦"],
  ["/map", "Road Map", "◉"],
  ["/worklist", "Repair Worklist", "☰"],
  ["/live", "Live Patrol", "●"],
  ["/detect", "Detect Damage", "⌖"],
  ["/reports", "Reports", "⤓"],
];

// Shows the login page when the deployed server has a password (APP_PASSWORD) and you are not logged in.
export default function AuthGate() {
  const [state, setState] = useState("checking"); // checking | login | ok
  const [authRequired, setAuthRequired] = useState(false);

  const check = () =>
    api
      .me()
      .then((m) => {
        setAuthRequired(m.auth_required);
        setState(m.auth_required && !m.logged_in ? "login" : "ok");
      })
      .catch(() => setState("ok")); // backend down: the pages show their own error

  useEffect(() => {
    check();
    const onExpired = () => setState("login");
    window.addEventListener("auth-required", onExpired);
    return () => window.removeEventListener("auth-required", onExpired);
  }, []);

  if (state === "checking") return <div className="muted pad">Loading…</div>;
  if (state === "login") return <Login onDone={check} />;
  return <App authRequired={authRequired} onLogout={() => api.logout().then(check)} />;
}

function App({ authRequired, onLogout }) {
  const [health, setHealth] = useState(null);
  const [zones, setZones] = useState([]);
  const [zone, setZone] = useState("All");
  const { pathname } = useLocation();

  useEffect(() => {
    api.zones().then((z) => setZones(z.zones)).catch(() => {});
    const h = () => api.health().then(setHealth).catch(() => setHealth({ api: false }));
    h();
    const t = setInterval(h, 15000);
    return () => clearInterval(t);
  }, []);

  // Live Patrol is a full-screen phone page without the sidebar
  if (pathname === "/live") return <LivePatrol />;

  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <div className="logo">RD</div>
          <div>
            <div className="brand-title">Road Damage Monitor</div>
            <div className="brand-sub">Kolhapur Municipal Corporation</div>
          </div>
        </div>
        <nav>
          {NAV.map(([to, label, icon]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => "nav" + (isActive ? " active" : "")}>
              <span className="nav-ic">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="zone-box">
          <label>Operational zone</label>
          <select value={zone} onChange={(e) => setZone(e.target.value)}>
            <option>All</option>
            {zones.map((z) => (
              <option key={z.name}>{z.name}</option>
            ))}
          </select>
        </div>
        <div className="sys">
          <Dot ok={health?.api} label="API" />
          <Dot ok={health?.mongo} label="MongoDB" />
          {health?.live_sessions > 0 && <Dot ok warn label={`Live patrol (${health.live_sessions})`} />}
          {authRequired && (
            <button className="link-btn" onClick={onLogout}>Log out</button>
          )}
          <Dot ok={health?.model?.loaded} warn={health?.model?.provisional} label={health?.model?.provisional ? "Model (training)" : "Model"} />
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard zone={zone} />} />
          <Route path="/map" element={<MapPage zone={zone} />} />
          <Route path="/worklist" element={<Worklist zone={zone} />} />
          <Route path="/incident/:id" element={<IncidentDetail />} />
          <Route path="/detect" element={<Detect />} />
          <Route path="/reports" element={<Reports zone={zone} />} />
        </Routes>
      </main>
    </div>
  );
}

function Dot({ ok, warn, label }) {
  const cls = ok === undefined ? "dot" : ok ? (warn ? "dot warn" : "dot ok") : "dot bad";
  return (
    <div className="sys-row">
      <span className={cls} />
      {label}
    </div>
  );
}

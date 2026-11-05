import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { IconFileText, IconLayoutDashboard, IconListCheck, IconLogout, IconMap2, IconScan, IconVideo } from "@tabler/icons-react";
import { api } from "./api";
import Dashboard from "./pages/Dashboard.jsx";
import MapPage from "./pages/MapPage.jsx";
import Worklist from "./pages/Worklist.jsx";
import IncidentDetail from "./pages/IncidentDetail.jsx";
import Detect from "./pages/Detect.jsx";
import Reports from "./pages/Reports.jsx";
import LivePatrol from "./pages/LivePatrol.jsx";
import Login from "./pages/Login.jsx";
import logoUrl from "./assets/margdrishti_logo.svg";

const NAV = [
  ["/", "Dashboard", IconLayoutDashboard, "Home"],
  ["/map", "Road map", IconMap2, "Map"],
  ["/worklist", "Repair worklist", IconListCheck, "Worklist"],
  ["/live", "Live patrol", IconVideo, "Patrol"],
  ["/detect", "Detect damage", IconScan, "Detect"],
  ["/reports", "Reports", IconFileText, "Reports"],
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
      <aside className="rail">
        <Link to="/" title="MargDrishti home">
          <img className="logo" src={logoUrl} alt="MargDrishti logo" />
        </Link>
        <nav className="rail-nav" aria-label="Main">
          {NAV.map(([to, label, Icon, short]) => (
            <NavLink key={to} to={to} end={to === "/"} aria-label={label} data-label={label} className={({ isActive }) => "nav" + (isActive ? " active" : "")}>
              <Icon size={22} stroke={1.8} aria-hidden="true" />
              <span className="nav-short" aria-hidden="true">{short}</span>
            </NavLink>
          ))}
        </nav>
        {authRequired && (
          <button className="nav nav-btn" onClick={onLogout} aria-label="Log out" data-label="Log out">
            <IconLogout size={22} stroke={1.8} aria-hidden="true" />
            <span className="nav-short" aria-hidden="true">Log out</span>
          </button>
        )}
      </aside>
      <div className="content">
        <header className="topbar">
          <img className="logo topbar-logo" src={logoUrl} alt="" />
          <div className="brand-block">
            <div className="brand-title">MargDrishti</div>
            <div className="brand-sub">Road damage monitoring, Kolhapur</div>
          </div>
          <div className="sys" aria-label="System status">
            <Dot ok={health?.api} label="API" />
            <Dot ok={health?.mongo} label="Database" />
            <Dot ok={health?.model?.loaded} warn={health?.model?.provisional} label={health?.model?.provisional ? "Model (training)" : "Model"} />
            {health?.live_sessions > 0 && <Dot ok warn label={`Live patrol (${health.live_sessions})`} />}
          </div>
          <label className="zone-box">
            <span className="sr-only">Operational zone</span>
            <select value={zone} onChange={(e) => setZone(e.target.value)}>
              <option value="All">All zones</option>
              {zones.map((z) => (
                <option key={z.name}>{z.name}</option>
              ))}
            </select>
          </label>
          {pathname !== "/detect" && <Link className="btn primary topbar-detect" to="/detect">Detect damage</Link>}
        </header>
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

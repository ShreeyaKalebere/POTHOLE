import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import {
  IconClipboardCheck, IconFileText, IconLayoutDashboard, IconListCheck, IconMap2, IconScan, IconTool, IconUsers, IconVideo,
} from "@tabler/icons-react";
import { api, ROLE_LABEL } from "./api";
import Account from "./pages/Account.jsx";
import Approvals from "./pages/Approvals.jsx";
import Citizen from "./pages/Citizen.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Detect from "./pages/Detect.jsx";
import Home from "./pages/Home.jsx";
import IncidentDetail from "./pages/IncidentDetail.jsx";
import Jobs from "./pages/Jobs.jsx";
import LivePatrol from "./pages/LivePatrol.jsx";
import Login from "./pages/Login.jsx";
import MapPage from "./pages/MapPage.jsx";
import Reports from "./pages/Reports.jsx";
import Users from "./pages/Users.jsx";
import Worklist from "./pages/Worklist.jsx";
import logoUrl from "./assets/margdrishti_logo.svg";

const OFFICE_NAV = [
  ["/", "Dashboard", IconLayoutDashboard, "Home"],
  ["/map", "Road map", IconMap2, "Map"],
  ["/worklist", "Repair worklist", IconListCheck, "Worklist"],
  ["/approvals", "Repair approvals", IconClipboardCheck, "Approvals"],
  ["/live", "Live patrol", IconVideo, "Patrol"],
  ["/detect", "Detect damage", IconScan, "Detect"],
  ["/reports", "Reports", IconFileText, "Reports"],
];
const NAV = {
  admin: [...OFFICE_NAV, ["/users", "Accounts and activity", IconUsers, "Accounts"]],
  ward_officer: OFFICE_NAV,
  repair_team: [["/", "My jobs", IconTool, "Jobs"]],
};

// Picks what to show: the public citizen page, the login page, or the panel for this person's role.
export default function AuthGate() {
  const [user, setUser] = useState(undefined); // undefined = still checking
  const { pathname } = useLocation();

  const check = () =>
    api.me().then((m) => setUser(m.user)).catch(() => setUser(null));

  useEffect(() => {
    check();
    const onExpired = () => setUser(null);
    window.addEventListener("auth-required", onExpired);
    return () => window.removeEventListener("auth-required", onExpired);
  }, []);

  if (user === undefined) return <div className="muted pad">Loading…</div>;
  if (pathname === "/report" || pathname.startsWith("/track")) return <Citizen />;
  if (pathname === "/home") return <Home user={user} />;
  if (!user) {
    if (pathname === "/") return <Home user={null} />;
    return <Login onDone={setUser} />;
  }
  if (pathname === "/login") return <Navigate to="/" replace />;
  return <Panel user={user} onLogout={() => api.logout().finally(() => setUser(null))} />;
}

function Panel({ user, onLogout }) {
  const [health, setHealth] = useState(null);
  const [zones, setZones] = useState([]);
  const [zoneChoice, setZoneChoice] = useState("All");
  const { pathname } = useLocation();
  const isAdmin = user.role === "admin";
  const isRepair = user.role === "repair_team";
  const zone = user.role === "ward_officer" ? user.ward : zoneChoice;

  useEffect(() => {
    if (isAdmin) api.zones().then((z) => setZones(z.zones)).catch(() => {});
    const h = () => api.health().then(setHealth).catch(() => setHealth({ api: false }));
    h();
    const t = setInterval(h, 15000);
    return () => clearInterval(t);
  }, [isAdmin]);

  // Live Patrol is a full-screen phone page without the menu
  if (pathname === "/live" && !isRepair) return <LivePatrol />;

  return (
    <div className={"shell" + (isRepair ? " single" : "")}>
      <aside className="rail">
        <Link to="/" title="MargDrishti home">
          <img className="logo" src={logoUrl} alt="MargDrishti logo" />
        </Link>
        <nav className={"rail-nav" + (NAV[user.role].length > 6 ? " many" : "")} aria-label="Main">
          {NAV[user.role].map(([to, label, Icon, short]) => (
            <NavLink key={to} to={to} end={to === "/"} aria-label={label} data-label={label} className={({ isActive }) => "nav" + (isActive ? " active" : "")}>
              <Icon size={22} stroke={1.8} aria-hidden="true" />
              <span className="nav-short" aria-hidden="true">{short}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="content">
        <header className="topbar">
          <img className="logo topbar-logo" src={logoUrl} alt="" />
          <div className="brand-block">
            <div className="brand-title">MargDrishti</div>
            <div className="brand-sub">
              {ROLE_LABEL[user.role]}
              {user.ward ? ` · ${user.ward}` : ""}
              {user.team ? ` · ${user.team}` : ""}
            </div>
          </div>
          {!isRepair && (
            <div className="sys" aria-label="System status">
              <Dot ok={health?.api} label="API" />
              <Dot ok={health?.mongo} label="Database" />
              <Dot ok={health?.model?.loaded} warn={health?.model?.provisional} label={health?.model?.provisional ? "Model (training)" : "Model"} />
              {health?.live_sessions > 0 && <Dot ok warn label={`Live patrol (${health.live_sessions})`} />}
            </div>
          )}
          {isAdmin && (
            <label className="zone-box">
              <span className="sr-only">Operational zone</span>
              <select value={zoneChoice} onChange={(e) => setZoneChoice(e.target.value)}>
                <option value="All">All zones</option>
                {zones.map((z) => (
                  <option key={z.name}>{z.name}</option>
                ))}
              </select>
            </label>
          )}
          {!isRepair && pathname !== "/detect" && <Link className="btn primary topbar-detect" to="/detect">Detect damage</Link>}
          <div className="user-menu">
            <Link className="user-name" to="/account" title="Your account">{user.name}</Link>
            <button className="btn" onClick={onLogout}>Log out</button>
          </div>
        </header>
        <main className="main">
          {isRepair ? (
            <Routes>
              <Route path="/" element={<Jobs />} />
              <Route path="/account" element={<Account onChanged={onLogout} />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          ) : (
            <Routes>
              <Route path="/" element={<Dashboard zone={zone} />} />
              <Route path="/map" element={<MapPage zone={zone} />} />
              <Route path="/worklist" element={<Worklist zone={zone} />} />
              <Route path="/approvals" element={<Approvals />} />
              <Route path="/incident/:id" element={<IncidentDetail user={user} />} />
              <Route path="/detect" element={<Detect />} />
              <Route path="/reports" element={<Reports zone={zone} user={user} />} />
              <Route path="/account" element={<Account onChanged={onLogout} />} />
              {isAdmin && <Route path="/users" element={<Users me={user} />} />}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          )}
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

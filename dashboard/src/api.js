// All calls to the FastAPI backend live here.
const qs = (params = {}) => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== "All") p.set(k, v);
  });
  const s = p.toString();
  return s ? `?${s}` : "";
};

async function req(url, opts) {
  const r = await fetch(url, opts);
  if (r.status === 401 && url !== "/api/login" && !url.startsWith("/api/public/")) {
    window.dispatchEvent(new Event("auth-required")); // App shows the login page
  }
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try {
      msg = (await r.json()).detail || msg;
    } catch {}
    throw new Error(msg);
  }
  return r.json();
}

export const api = {
  me: () => req("/api/me"),
  login: (username, password) =>
    req("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),
  logout: () => req("/api/logout", { method: "POST" }),
  health: () => req("/api/health"),
  zones: () => req("/api/zones"),
  stats: (zone) => req(`/api/stats${qs({ zone })}`),
  incidents: (filters) => req(`/api/incidents${qs(filters)}`),
  incident: (id) => req(`/api/incidents/${id}`),
  update: (id, body) =>
    req(`/api/incidents/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  detect: (file, lat, lng, save = true) => {
    const fd = new FormData();
    fd.append("file", file);
    if (lat !== "" && lat != null) fd.append("lat", lat);
    if (lng !== "" && lng != null) fd.append("lng", lng);
    fd.append("save", save);
    return req("/api/detect", { method: "POST", body: fd });
  },
  remove: (id) => req(`/api/incidents/${id}`, { method: "DELETE" }),
  reloadModel: () => req("/api/model/reload", { method: "POST" }),
  seedDemo: () => req("/api/demo/seed?n=120", { method: "POST" }),
  clearDemo: () => req("/api/demo", { method: "DELETE" }),
  exportUrl: (kind, filters) => `/api/export/${kind}${qs(filters)}`,

  citizenReport: (file, pos, kind, note) => {
    const fd = new FormData();
    fd.append("file", file);
    if (pos) {
      fd.append("lat", pos[0]);
      fd.append("lng", pos[1]);
    }
    fd.append("kind", kind);
    fd.append("note", note);
    return req("/api/public/report", { method: "POST", body: fd });
  },
  citizenTrack: (code) => req(`/api/public/track/${encodeURIComponent(code)}`),

  jobs: () => req("/api/jobs"),
  startJob: (id) => req(`/api/jobs/${id}/start`, { method: "POST" }),
  completeJob: (id, file, note) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("note", note);
    return req(`/api/jobs/${id}/complete`, { method: "POST", body: fd });
  },

  approvals: () => req("/api/approvals"),
  decideRepair: (id, approve, note) =>
    req(`/api/incidents/${id}/repair/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approve, note }),
    }),
  teams: () => req("/api/teams"),

  changePassword: (current_password, new_password) =>
    req("/api/me/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password, new_password }),
    }),
  users: () => req("/api/users"),
  activity: () => req("/api/activity"),
  createUser: (body) =>
    req("/api/users", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  changeUser: (id, body) =>
    req(`/api/users/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
};

export const TYPE_LABEL = { pothole: "Pothole", alligator_crack: "Alligator Crack" };
export const SEV_COLOR = { High: "#e2502a", Medium: "#edb100", Low: "#8c887a" };
export const STATUS_COLOR = { Reported: "#37287a", "In Progress": "#1f6fd1", Repaired: "#1e9a5b" };
export const STATUSES = ["Reported", "In Progress", "Repaired"];
export const ROLE_LABEL = { admin: "Admin", ward_officer: "Ward officer", repair_team: "Repair team" };

export const fmtDate = (iso) =>
  iso ? new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "-";

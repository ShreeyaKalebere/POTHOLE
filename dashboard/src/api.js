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
  if (r.status === 401 && !url.startsWith("/api/login")) {
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
  login: (password) =>
    req("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
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
};

export const TYPE_LABEL = { pothole: "Pothole", alligator_crack: "Alligator Crack" };
export const SEV_COLOR = { High: "#e5484d", Medium: "#f59e0b", Low: "#30a46c" };
export const STATUS_COLOR = { Reported: "#3e63dd", "In Progress": "#f59e0b", Repaired: "#30a46c" };
export const STATUSES = ["Reported", "In Progress", "Repaired"];
export const TEAMS = ["Ward Team A", "Ward Team B", "Road Repair Unit 1", "Road Repair Unit 2", "PWD Contractor"];

export const fmtDate = (iso) =>
  iso ? new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "-";

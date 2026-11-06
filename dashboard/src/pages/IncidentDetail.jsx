import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, STATUSES, TYPE_LABEL, fmtDate } from "../api";
import { IncidentMap, SevBadge, StatusBadge, TypeTag } from "../components";

export default function IncidentDetail({ user }) {
  const { id } = useParams();
  const [inc, setInc] = useState(null);
  const [form, setForm] = useState({ status: "", severity: "", assigned_to: "", note: "" });
  const [teams, setTeams] = useState([]);
  const [imgIdx, setImgIdx] = useState(0);
  const [msg, setMsg] = useState("");
  const navigate = useNavigate();

  const remove = async () => {
    if (!confirm(`Delete ${inc.incident_code} permanently? This cannot be undone.`)) return;
    try {
      await api.remove(id);
      navigate("/worklist");
    } catch (e) {
      setMsg("Delete failed: " + e.message);
    }
  };

  const load = () =>
    api.incident(id).then((d) => {
      setInc(d);
      setForm({ status: d.status, severity: d.severity, assigned_to: d.assigned_to || "", note: "" });
    });
  useEffect(() => {
    load();
    api.teams().then((t) => setTeams(t.teams)).catch(() => {});
  }, [id]);

  if (!inc) return <div className="muted pad">Loading…</div>;
  const img = inc.images[Math.min(imgIdx, inc.images.length - 1)];

  const save = async () => {
    const body = { note: form.note || undefined };
    if (form.status !== inc.status) body.status = form.status;
    if (form.severity !== inc.severity) body.severity = form.severity;
    if (form.assigned_to !== (inc.assigned_to || "")) body.assigned_to = form.assigned_to;
    if (!body.status && !body.severity && body.assigned_to === undefined && !body.note && !inc.needs_review) return;
    await api.update(id, body);
    setMsg("Saved");
    setTimeout(() => setMsg(""), 2000);
    load();
  };

  return (
    <>
      <header className="page-head">
        <div>
          <Link to="/worklist" className="muted small">Back to worklist</Link>
          <h1>
            {inc.incident_code} · {TYPE_LABEL[inc.damage_type]}
          </h1>
          <div className="row gap">
            <SevBadge s={inc.severity} /> <StatusBadge s={inc.status} /> <TypeTag t={inc.damage_type} />
            {inc.demo && <span className="demo">demo record</span>}
            {inc.needs_review && <span className="review-tag">Needs officer review</span>}
          </div>
        </div>
      </header>

      <div className="grid two">
        <div className="card">
          <h3>Detection image</h3>
          <img className="det-img" src={img.annotated_url} alt="annotated detection" />
          <div className="row gap small muted" style={{ marginTop: 8 }}>
            <span>Confidence {(img.confidence * 100).toFixed(0)}%</span>
            <span>· {fmtDate(img.at)}</span>
            <a href={img.url} target="_blank" rel="noreferrer">Original photo</a>
          </div>
          {inc.images.length > 1 && (
            <div className="thumbs">
              {inc.images.map((im, k) => (
                <img key={k} src={im.annotated_url} className={k === imgIdx ? "on" : ""} onClick={() => setImgIdx(k)} alt="" />
              ))}
            </div>
          )}
        </div>

        <div className="col">
          <div className="card">
            <h3>Details</h3>
            <dl className="kv">
              <dt>Location</dt>
              <dd>
                {inc.lat != null ? (
                  <a href={`https://www.google.com/maps?q=${inc.lat},${inc.lng}`} target="_blank" rel="noreferrer">
                    {inc.lat.toFixed(6)}, {inc.lng.toFixed(6)}
                  </a>
                ) : "No GPS"}
              </dd>
              <dt>Zone</dt><dd>{inc.zone}</dd>
              <dt>Severity score</dt><dd>{inc.severity_score}</dd>
              <dt>Times reported</dt><dd>{inc.reports_count}</dd>
              <dt>First detected</dt><dd>{fmtDate(inc.detected_at)}</dd>
              <dt>Last update</dt><dd>{fmtDate(inc.updated_at)}</dd>
              <dt>Source</dt><dd>{inc.source}</dd>
            </dl>
          </div>

          <div className="card">
            <h3>Inspect and dispatch</h3>
            <div className="form">
              <label>Status</label>
              <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                {STATUSES.map((s) => <option key={s}>{s}</option>)}
              </select>
              <label>Severity</label>
              <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>
                {["Low", "Medium", "High"].map((s) => <option key={s}>{s}</option>)}
              </select>
              <label>Assign to team</label>
              <select value={form.assigned_to} onChange={(e) => setForm({ ...form, assigned_to: e.target.value })}>
                <option value="">Not assigned</option>
                {form.assigned_to && !teams.includes(form.assigned_to) && <option>{form.assigned_to}</option>}
                {teams.map((t) => <option key={t}>{t}</option>)}
              </select>
              <label>Note</label>
              <textarea rows={2} value={form.note} placeholder="e.g. Site inspected, needs patching material"
                onChange={(e) => setForm({ ...form, note: e.target.value })} />
              <div className="row gap">
                <button className="btn primary" onClick={save}>Save update</button>
                {user.role === "admin" && <button className="btn danger" onClick={remove}>Delete incident</button>}
                <span className="ok-msg">{msg}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {inc.repair && (
        <div className="card">
          <h3>Repair evidence</h3>
          <div className="before-after detail">
            <figure><img src={inc.images[inc.images.length - 1].annotated_url} alt="Before repair" /><figcaption>Before</figcaption></figure>
            <figure><img src={inc.repair.annotated_url} alt="After repair" /><figcaption>After</figcaption></figure>
          </div>
          <p className="small muted">
            {inc.repair.by}, {fmtDate(inc.repair.at)} · {inc.repair.ai_damage_found ? `AI still saw ${inc.repair.ai_damage_found} damaged area(s)` : "AI saw no damage"} · {inc.repair.state === "pending" ? "Waiting for approval" : inc.repair.state === "approved" ? `Approved by ${inc.repair.decided_by}` : `Rejected by ${inc.repair.decided_by}`}
          </p>
          {inc.repair.state === "pending" && <Link className="btn primary" to="/approvals">Go to approvals</Link>}
        </div>
      )}

      <div className="grid two">
        {inc.lat != null && (
          <div className="card">
            <h3>Location</h3>
            <IncidentMap items={[inc]} height={260} touchPan={false} />
          </div>
        )}
        <div className="card">
          <h3>History</h3>
          <ol className="timeline">
            {[...inc.history].reverse().map((h, k) => (
              <li key={k}>
                <StatusBadge s={h.status} />
                <div>
                  <div>{h.note}</div>
                  <div className="muted small">{fmtDate(h.at)} · {h.by}</div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </>
  );
}

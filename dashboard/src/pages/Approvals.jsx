import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate, TYPE_LABEL } from "../api";
import { SevBadge } from "../components";

export default function Approvals() {
  const [items, setItems] = useState(null);
  const [err, setErr] = useState("");

  const load = () => api.approvals().then((d) => { setItems(d.items); setErr(""); }).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  if (err) return <div className="card notice error" role="alert">{err}</div>;
  if (!items) return <div className="muted pad">Loading…</div>;

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Repair approvals</h1>
          <p className="muted">Compare the before and after photos. The AI result is a hint, and the decision is yours.</p>
        </div>
      </header>
      {!items.length && <div className="card muted">No repairs are waiting for approval.</div>}
      <div className="job-list wide">
        {items.map((i) => <Approval key={i.id} item={i} onDone={load} />)}
      </div>
    </>
  );
}

function Approval({ item, onDone }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const r = item.repair;

  const decide = async (approve) => {
    setBusy(true);
    setErr("");
    try {
      await api.decideRepair(item.id, approve, note);
      await onDone();
    } catch (e) {
      setErr(e.message);
      setBusy(false);
    }
  };

  return (
    <article className="card job">
      <div className="job-head">
        <div>
          <Link to={`/incident/${item.id}`}><b>{item.incident_code}</b></Link>
          <div className="muted small">{TYPE_LABEL[item.damage_type]} · {item.zone} · {item.assigned_to}</div>
        </div>
        <SevBadge s={item.severity} />
      </div>
      <div className="before-after">
        <figure><img src={item.before_photo} alt="Before repair" loading="lazy" /><figcaption>Before</figcaption></figure>
        <figure><img src={r.annotated_url} alt="After repair" loading="lazy" /><figcaption>After</figcaption></figure>
      </div>
      <div className={"notice" + (r.ai_damage_found ? " warn" : " good")}>
        {r.ai_damage_found ? `AI still sees ${r.ai_damage_found} damaged area${r.ai_damage_found > 1 ? "s" : ""} in the after photo.` : "AI sees no damage in the after photo."}
      </div>
      <p className="small muted">Submitted by {r.by}, {fmtDate(r.at)}{r.note ? `: “${r.note}”` : ""}</p>
      <label className="small muted" htmlFor={`decision-${item.id}`}>Note (needed if you reject)</label>
      <input id={`decision-${item.id}`} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Edges still broken, please redo" />
      <div className="row gap decision">
        <button className="btn primary" disabled={busy} onClick={() => decide(true)}>Approve repair</button>
        <button className="btn danger" disabled={busy} onClick={() => decide(false)}>Reject</button>
      </div>
      {err && <div className="notice error" role="alert">{err}</div>}
    </article>
  );
}

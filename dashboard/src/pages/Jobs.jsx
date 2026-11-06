import { useEffect, useState } from "react";
import { api, fmtDate, TYPE_LABEL } from "../api";
import { SevBadge, StatusBadge } from "../components";

export default function Jobs() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  const load = () => api.jobs().then((d) => { setData(d); setErr(""); }).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  if (err) return <div className="card notice error" role="alert">{err}</div>;
  if (!data) return <div className="muted pad">Loading…</div>;
  const open = data.items.filter((j) => j.status !== "Repaired");
  const done = data.items.filter((j) => j.status === "Repaired");

  return (
    <>
      <header className="page-head">
        <h1>My jobs</h1>
        <p className="muted">{open.length ? `${open.length} to complete` : "No open jobs right now"}</p>
      </header>
      <div className="job-list">
        {open.map((j) => <Job key={j.id} job={j} onChange={load} />)}
      </div>
      {done.length > 0 && (
        <>
          <h3 className="section-title">Approved repairs</h3>
          <div className="card">
            {done.slice(0, 20).map((j) => (
              <div key={j.id} className="queue-row plain">
                <span><b>{j.incident_code}</b><small>{j.zone} · {fmtDate(j.updated_at)}</small></span>
                <StatusBadge s={j.status} />
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}

function Job({ job, onChange }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const repair = job.repair;
  const waiting = repair?.state === "pending";

  const run = async (fn) => {
    setBusy(true);
    setErr("");
    try {
      await fn();
      await onChange();
    } catch (e) {
      setErr(e.message);
    }
    setBusy(false);
  };

  return (
    <article className="card job">
      <div className="job-head">
        <div>
          <b>{job.incident_code}</b>
          <div className="muted small">{TYPE_LABEL[job.damage_type]} · {job.zone}</div>
        </div>
        <SevBadge s={job.severity} />
      </div>
      {job.photo && <img className="job-photo" src={job.photo} alt={`Damage reported for ${job.incident_code}`} loading="lazy" />}
      <div className="row gap job-meta">
        <StatusBadge s={job.status} />
        {job.lat != null && (
          <a className="btn" href={`https://www.google.com/maps/dir/?api=1&destination=${job.lat},${job.lng}`} target="_blank" rel="noreferrer">Directions</a>
        )}
      </div>

      {repair?.state === "rejected" && (
        <div className="notice error" role="alert"><b>Repair rejected.</b> {repair.decision_note}</div>
      )}
      {waiting ? (
        <div className="notice">Waiting for the ward officer to approve this repair.</div>
      ) : job.status === "Reported" ? (
        <button className="btn primary big" disabled={busy} onClick={() => run(() => api.startJob(job.id))}>{busy ? "Saving…" : "Start work"}</button>
      ) : (
        <div className="form">
          <label className="drop job-drop">
            <input type="file" accept="image/*" onChange={(e) => { const f = e.target.files[0]; if (f) { setFile(f); setPreview(URL.createObjectURL(f)); } }} hidden />
            {preview ? <img src={preview} alt="Your repair photo" /> : <span>Take or choose the “after” photo</span>}
          </label>
          <label htmlFor={`note-${job.id}`}>Note (optional)</label>
          <input id={`note-${job.id}`} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Patched and compacted" />
          <button className="btn primary big" disabled={!file || busy} onClick={() => run(() => api.completeJob(job.id, file, note))}>{busy ? "Sending…" : "Submit for approval"}</button>
        </div>
      )}
      {err && <div className="notice error" role="alert">{err}</div>}
    </article>
  );
}

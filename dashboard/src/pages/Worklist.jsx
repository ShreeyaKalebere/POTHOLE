import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, STATUSES, fmtDate } from "../api";
import { Filters, SevBadge, TypeTag } from "../components";

export default function Worklist({ zone }) {
  const [f, setF] = useState({ status: "" });
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(null);

  const load = () => api.incidents({ ...f, zone, limit: 2000 }).then((r) => setItems(r.items));
  useEffect(() => {
    load();
  }, [f, zone]);

  const setStatus = async (i, status) => {
    setBusy(i.id);
    await api.update(i.id, { status });
    await load();
    setBusy(null);
  };

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Repair worklist</h1>
          <p className="muted">Sorted by priority: open first, then severity, then number of reports</p>
        </div>
        <Filters f={f} setF={setF} show={["type", "severity", "status", "dates"]} />
      </header>
      <div className="card flush">
        <table className="tbl cards">
          <thead>
            <tr>
              <th>Code</th><th>Type</th><th>Severity</th><th>Zone</th><th>Reports</th>
              <th>Assigned to</th><th>Detected</th><th>Status</th><th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id} className={i.status === "Repaired" ? "done" : ""}>
                <td><b>{i.incident_code}</b>{i.demo && <span className="demo">demo</span>}{i.needs_review && <span className="review-tag">Review</span>}</td>
                <td data-label="Type"><TypeTag t={i.damage_type} /></td>
                <td><SevBadge s={i.severity} /></td>
                <td data-label="Zone">{i.zone}</td>
                <td className="num" data-label="Reports">{i.reports_count}</td>
                <td data-label="Assigned to">{i.assigned_to || <span className="muted">Not assigned</span>}</td>
                <td className="nowrap" data-label="Detected">{fmtDate(i.detected_at)}</td>
                <td data-label="Status">
                  <select aria-label={`Status of ${i.incident_code}`} value={i.status} disabled={busy === i.id} onChange={(e) => setStatus(i, e.target.value)}>
                    {STATUSES.map((s) => <option key={s}>{s}</option>)}
                  </select>
                </td>
                <td className="c-inspect"><Link to={`/incident/${i.id}`}>Inspect</Link></td>
              </tr>
            ))}
            {!items.length && (
              <tr><td colSpan={9} className="muted pad">No incidents match these filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

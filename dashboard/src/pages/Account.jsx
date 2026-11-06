import { useState } from "react";
import { api } from "../api";

export default function Account({ onChanged }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      await api.changePassword(current, next);
      onChanged(); // the old session ends when the password changes
    } catch (ex) {
      setErr(ex.message);
      setBusy(false);
    }
  };

  return (
    <>
      <header className="page-head"><h1>Your account</h1></header>
      <form className="card form narrow" onSubmit={submit}>
        <h3>Change password</h3>
        <label htmlFor="a-current">Current password</label>
        <input id="a-current" type="password" required autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        <label htmlFor="a-next">New password (at least 8 characters)</label>
        <input id="a-next" type="password" required minLength={8} autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        {err && <div className="notice error" role="alert">{err}</div>}
        <button className="btn primary" disabled={busy}>{busy ? "Saving…" : "Change password"}</button>
        <p className="muted small">You will need to log in again afterwards.</p>
      </form>
    </>
  );
}

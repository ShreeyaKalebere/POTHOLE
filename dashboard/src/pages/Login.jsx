import { useState } from "react";
import { api } from "../api";

export default function Login({ onDone }) {
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      await api.login(pw);
      onDone();
    } catch (ex) {
      setErr(ex.message === "Wrong password" ? "Wrong password" : "Cannot reach the server: " + ex.message);
    }
    setBusy(false);
  };

  return (
    <div className="login-wrap">
      <form className="card login" onSubmit={submit}>
        <div className="brand">
          <div className="logo">RD</div>
          <div>
            <div className="brand-title dark">Road Damage Monitor</div>
            <div className="muted small">Kolhapur Municipal Corporation</div>
          </div>
        </div>
        <label className="muted small">Password</label>
        <input type="password" autoFocus value={pw} onChange={(e) => setPw(e.target.value)} placeholder="Team password" />
        <button className="btn primary big" disabled={!pw || busy}>{busy ? "Checking…" : "Log in"}</button>
        {err && <div className="notice error">{err}</div>}
      </form>
    </div>
  );
}

import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api, ROLE_LABEL } from "../api";
import logoUrl from "../assets/margdrishti_logo.svg";

export default function Login({ onDone }) {
  const [username, setUsername] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const role = ROLE_LABEL[new URLSearchParams(useLocation().search).get("role")];

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const r = await api.login(username, pw);
      onDone(r.user);
    } catch (ex) {
      setErr(ex.message);
    }
    setBusy(false);
  };

  return (
    <div className="login-wrap">
      <form className="card login" onSubmit={submit}>
        <div className="brand">
          <img className="logo" src={logoUrl} alt="MargDrishti logo" />
          <div>
            <div className="brand-title dark">MargDrishti</div>
            <div className="muted small">{role ? `${role} login` : "Staff login"}</div>
          </div>
        </div>
        <label className="muted small" htmlFor="login-user">Username</label>
        <input id="login-user" autoFocus autoComplete="username" autoCapitalize="none" value={username} onChange={(e) => setUsername(e.target.value)} />
        <label className="muted small" htmlFor="login-pass">Password</label>
        <input id="login-pass" type="password" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} />
        <button className="btn primary big" disabled={!username || !pw || busy}>{busy ? "Checking…" : "Log in"}</button>
        {err && <div className="notice error" role="alert">{err}</div>}
        <Link className="login-alt" to="/report">Report road damage without an account</Link>
        <Link className="login-alt" to="/">Back to home</Link>
      </form>
    </div>
  );
}

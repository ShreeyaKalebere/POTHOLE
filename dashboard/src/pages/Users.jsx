import { useEffect, useState } from "react";
import { api, fmtDate, ROLE_LABEL } from "../api";

const BLANK = { username: "", name: "", role: "ward_officer", ward: "", team: "", password: "" };

export default function Users({ me }) {
  const [users, setUsers] = useState([]);
  const [activity, setActivity] = useState([]);
  const [zones, setZones] = useState([]);
  const [form, setForm] = useState(BLANK);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const load = () =>
    Promise.all([api.users(), api.activity()]).then(([u, a]) => {
      setUsers(u.items);
      setActivity(a.items);
    }).catch((e) => setErr(e.message));

  useEffect(() => {
    load();
    api.zones().then((z) => setZones(z.zones)).catch(() => {});
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const create = async (e) => {
    e.preventDefault();
    setErr("");
    setMsg("");
    try {
      const u = await api.createUser(form);
      setMsg(`Created ${u.username}. Share the password with them privately.`);
      setForm(BLANK);
      load();
    } catch (ex) {
      setErr(ex.message);
    }
  };

  const change = async (u, body, done) => {
    setErr("");
    setMsg("");
    try {
      await api.changeUser(u.id, body);
      setMsg(done);
      load();
    } catch (ex) {
      setErr(ex.message);
    }
  };

  const resetPassword = (u) => {
    const password = window.prompt(`New password for ${u.username} (at least 8 characters):`);
    if (password) change(u, { password }, `Password changed for ${u.username}.`);
  };

  return (
    <>
      <header className="page-head"><h1>Accounts and activity</h1></header>
      {msg && <div className="card notice good" role="status">{msg}</div>}
      {err && <div className="card notice error" role="alert">{err}</div>}

      <div className="grid two">
        <div className="card flush">
          <table className="tbl cards plain-cards">
            <thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Ward or team</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className={u.active ? "" : "done"}>
                  <td><b>{u.name}</b></td>
                  <td data-label="Username">{u.username}</td>
                  <td data-label="Role">{ROLE_LABEL[u.role]}</td>
                  <td data-label="Ward or team">{u.ward || u.team || <span className="muted">All</span>}</td>
                  <td data-label="Status">{u.active ? "Active" : "Deactivated"}</td>
                  <td className="c-inspect row-actions">
                    <button className="btn" onClick={() => resetPassword(u)}>Reset password</button>
                    {u.id !== me.id && (
                      <button className={"btn" + (u.active ? " danger" : "")} onClick={() => change(u, { active: !u.active }, `${u.username} ${u.active ? "deactivated" : "activated"}.`)}>
                        {u.active ? "Deactivate" : "Activate"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <form className="card form" onSubmit={create}>
          <h3>Add an account</h3>
          <label htmlFor="u-role">Role</label>
          <select id="u-role" value={form.role} onChange={set("role")}>
            <option value="ward_officer">Ward officer</option>
            <option value="repair_team">Repair team</option>
            <option value="admin">Admin</option>
          </select>
          {form.role === "ward_officer" && (
            <>
              <label htmlFor="u-ward">Ward</label>
              <select id="u-ward" required value={form.ward} onChange={set("ward")}>
                <option value="">Choose a ward</option>
                {zones.map((z) => <option key={z.name}>{z.name}</option>)}
              </select>
            </>
          )}
          {form.role === "repair_team" && (
            <>
              <label htmlFor="u-team">Team name</label>
              <input id="u-team" required value={form.team} onChange={set("team")} placeholder="Road Repair Unit 3" />
            </>
          )}
          <label htmlFor="u-name">Full name</label>
          <input id="u-name" value={form.name} onChange={set("name")} />
          <label htmlFor="u-username">Username</label>
          <input id="u-username" required autoCapitalize="none" autoComplete="off" value={form.username} onChange={set("username")} placeholder="officer_kadamwadi" />
          <label htmlFor="u-password">Password (at least 8 characters)</label>
          <input id="u-password" type="password" required minLength={8} autoComplete="new-password" value={form.password} onChange={set("password")} />
          <button className="btn primary">Create account</button>
        </form>
      </div>

      <div className="card">
        <h3>Recent activity</h3>
        {!activity.length && <p className="muted">No activity yet.</p>}
        <ol className="activity">
          {activity.map((a, k) => (
            <li key={k}>
              <span><b>{a.who}</b> {a.action.toLowerCase()}{a.incident_code ? ` ${a.incident_code}` : ""}{a.detail ? `: ${a.detail}` : ""}</span>
              <span className="muted small nowrap">{fmtDate(a.at)}</span>
            </li>
          ))}
        </ol>
      </div>
    </>
  );
}

import { useState } from "react";
import { api } from "../api";
import { Filters } from "../components";

export default function Reports({ zone }) {
  const [f, setF] = useState({});
  const [msg, setMsg] = useState("");
  const params = { ...f, zone };

  const demo = async (fn, label) => {
    if (label === "clear" && !confirm("Delete all demo records? Real detections are not affected.")) return;
    const r = await fn();
    setMsg(label === "seed" ? `Added ${r.inserted} demo incidents` : `Removed ${r.deleted} demo incidents`);
  };

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Municipal Reports</h1>
          <p className="muted">Export incidents for maintenance planning ({zone === "All" ? "all zones" : zone})</p>
        </div>
      </header>

      <div className="card">
        <h3>Filters</h3>
        <Filters f={f} setF={setF} show={["type", "severity", "status", "dates"]} />
        <div className="row gap" style={{ marginTop: 16 }}>
          <a className="btn primary" href={api.exportUrl("pdf", params)}>⤓ Download PDF report</a>
          <a className="btn" href={api.exportUrl("csv", params)}>⤓ Download CSV (Excel)</a>
        </div>
      </div>

      <div className="card">
        <h3>Demo data</h3>
        <p className="muted">
          Demo incidents use real dataset photos at random Kolhapur locations so the dashboard can be presented
          before field data exists. They are marked <span className="demo">demo</span> everywhere.
        </p>
        <div className="row gap">
          <button className="btn" onClick={() => demo(api.seedDemo, "seed")}>Load 120 demo incidents</button>
          <button className="btn danger" onClick={() => demo(api.clearDemo, "clear")}>Clear demo data</button>
          <span className="ok-msg">{msg}</span>
        </div>
      </div>

      <div className="card">
        <h3>Model</h3>
        <p className="muted">After training finishes, reload the model so detection uses the newest weights.</p>
        <button className="btn" onClick={() => api.reloadModel().then((r) => setMsg(`Loaded ${r.weights}`)).catch((e) => setMsg(e.message))}>
          ↻ Reload model
        </button>
      </div>
    </>
  );
}

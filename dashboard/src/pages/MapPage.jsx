import { useEffect, useState } from "react";
import { api } from "../api";
import { Filters, IncidentMap } from "../components";

export default function MapPage({ zone }) {
  const [f, setF] = useState({});
  const [items, setItems] = useState([]);

  useEffect(() => {
    api.incidents({ ...f, zone, limit: 5000 }).then((r) => setItems(r.items)).catch(() => setItems([]));
  }, [f, zone]);

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Interactive Road Map</h1>
          <p className="muted">{items.length} incidents shown · click a marker to inspect</p>
        </div>
        <Filters f={f} setF={setF} />
      </header>
      <div className="card flush">
        <IncidentMap items={items} height="calc(100vh - 170px)" />
      </div>
    </>
  );
}

// Road Damage Label Verifier - canvas box editor, AI label, browse grid, dataset tools.
const $ = (id) => document.getElementById(id);
const CLASS = [{ name: "Pothole", color: "#f43f5e" }, { name: "Alligator crack", color: "#f59e0b" }];
const STATUS_TEXT = { unverified: "not checked", verified: "damage", negative: "no damage", skipped: "skipped" };
const SRC_TEXT = { raw: "original label", fixed: "edited label", none: "no label", ai: "AI – not saved" };

const st = {
  cur: null, img: null, boxes: [], sel: -1, cls: 0, dirty: false, hide: false, fromAI: false,
  view: { s: 1, ox: 0, oy: 0, fit: 1 }, drag: null, mouse: null, history: [], undo: [],
};

// ------------------------------------------------------------ helpers
async function api(url, opts = {}) {
  if (opts.json !== undefined) {
    opts = { ...opts, method: opts.method || "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(opts.json) };
  }
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), url.includes("/api/predict") || url.includes("/api/export") ? 300000 : 45000);
  let r;
  try {
    r = await fetch(url, { ...opts, signal: ctl.signal });
  } catch (e) {
    throw new Error(e.name === "AbortError" ? "The server is not answering. Ask whoever runs the tool to restart it." : "Cannot reach the server. Check the Wi-Fi and that the tool is running.");
  } finally { clearTimeout(timer); }
  let body = null;
  try { body = await r.json(); } catch {}
  if (r.status === 409 && body && /image list changed/.test(body.detail)) {
    setTimeout(() => { st.dirty = false; st.history = []; startMode(); }, 1500);
  }
  if (!r.ok) {
    const err = new Error((body && body.detail) || `${r.status} ${r.statusText}`);
    err.status = r.status;
    throw err;
  }
  return body;
}
window.addEventListener("unhandledrejection", (e) => {
  const m = e.reason && e.reason.message ? e.reason.message : "Something went wrong.";
  msg(m, "err"); toast("⚠ " + esc(m), "err", 10000);
  if (!st.img) showEmpty("⚠ " + m);
});
const store = {
  get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch {} },
};
const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const enc = encodeURIComponent;
const ds = () => $("dataset").value;
const user = () => $("user").value.trim();
function msg(text, kind = "") { $("msg").textContent = text; $("msg").className = "small " + kind; }
function needUser() {
  if (user()) return false;
  $("user").classList.add("need"); $("user").focus();
  msg("Type your name at the top right first.", "err");
  return true;
}
// server box (normalised centre/size) <-> editor box (image pixels, corners)
const fromServer = (b, W, H) => ({
  c: b.class_id, conf: b.confidence < 1 ? b.confidence : undefined,
  x1: (b.x_center - b.width / 2) * W, y1: (b.y_center - b.height / 2) * H,
  x2: (b.x_center + b.width / 2) * W, y2: (b.y_center + b.height / 2) * H,
});
const toServer = (b, W, H) => {
  const x1 = Math.min(b.x1, b.x2), x2 = Math.max(b.x1, b.x2), y1 = Math.min(b.y1, b.y2), y2 = Math.max(b.y1, b.y2);
  return { class_id: b.c, x_center: (x1 + x2) / 2 / W, y_center: (y1 + y2) / 2 / H, width: (x2 - x1) / W, height: (y2 - y1) / H };
};

// ------------------------------------------------------------ tabs
document.querySelectorAll(".tab").forEach((b) => b.onclick = () => showTab(b.dataset.tab));
function showTab(t) {
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === t));
  document.querySelectorAll(".page").forEach((p) => p.classList.toggle("active", p.id === "tab-" + t));
  if (t === "label") requestAnimationFrame(resize);
  if (t === "browse") loadGrid();
  if (t === "data") { loadDatasets(); refreshLabelImg(); }
}

// ------------------------------------------------------------ datasets + progress
async function loadDatasets() {
  const r = await api("/api/datasets");
  const keep = ds() || store.get("dataset") || r.active;
  const groups = {};
  r.datasets.forEach((d) => (groups[d.group] = groups[d.group] || []).push(d));
  $("dataset").innerHTML = Object.entries(groups).map(([g, list]) => `<optgroup label="${esc(g)}">` +
    list.map((d) => `<option value="${esc(d.key)}">${esc(d.name)}  (${d.verified_count}/${d.total_images})</option>`).join("") +
    "</optgroup>").join("");
  if (r.datasets.some((d) => d.key === keep)) $("dataset").value = keep;
  $("dsTable").innerHTML = `<tr><th>Dataset</th><th>Group</th><th>Images</th><th>Checked</th><th>Progress</th></tr>` +
    r.datasets.map((d) => {
      const pct = d.total_images ? Math.round(100 * d.verified_count / d.total_images) : 0;
      return `<tr data-k="${esc(d.key)}" class="${d.key === ds() ? "cur" : ""}"><td>${esc(d.name)}</td><td>${esc(d.group)}</td>
        <td>${d.total_images}</td><td>${d.verified_count}</td><td><span class="mini"><i style="width:${pct}%"></i></span> ${pct}%</td></tr>`;
    }).join("");
  await refreshStats();
}
async function refreshStats() {
  if (!ds()) return;
  const s = await api(`/api/stats?dataset=${enc(ds())}`);
  $("progFill").style.width = s.total_images ? (100 * s.verified_count / s.total_images) + "%" : "0";
  $("progText").textContent = `${s.verified_count} / ${s.total_images} checked`;
  const opt = $("dataset").selectedOptions[0];
  if (opt) opt.textContent = opt.textContent.replace(/\(\d+\/\d+\)$/, `(${s.verified_count}/${s.total_images})`);
  $("peopleTable").innerHTML = `<tr><th>Name</th><th>Damage</th><th>No damage</th><th>Skipped</th></tr>` +
    (s.people.map((p) => `<tr><td>${esc(p.user)}</td><td>${p.verified}</td><td>${p.negative}</td><td>${p.skipped}</td></tr>`).join("")
      || `<tr><td colspan="4" class="muted">nobody yet</td></tr>`) +
    `<tr><td><b>Boxes</b></td><td colspan="3">${s.pothole_count} pothole · ${s.crack_count} alligator crack</td></tr>`;
  $("delCount").textContent = `${s.deleted_count} image(s) in the deleted folder`;
  $("bEmptyDel").disabled = !s.deleted_count;
}
function switchDataset(key) {
  if (!guard()) { $("dataset").value = st.cur ? st.cur.dataset : ds(); return; }
  $("dataset").value = key; store.set("dataset", key);
  loadDatasets(); startMode(); loadFilmstrip(true);
  if ($("tab-browse").classList.contains("active")) { page = 0; loadGrid(); }
  if ($("tab-data").classList.contains("active")) refreshLabelImg();
}
$("dataset").onchange = () => switchDataset(ds());
$("dsTable").onclick = (e) => {
  const tr = e.target.closest("tr[data-k]");
  if (tr) { switchDataset(tr.dataset.k); showTab("label"); }
};

// ------------------------------------------------------------ loading images
function showEmpty(text) {
  st.cur = null; st.img = null; st.boxes = []; st.sel = -1; st.dirty = false;
  $("empty").textContent = text; $("empty").classList.remove("hidden");
  $("info").textContent = "–"; $("hint").classList.add("hidden"); $("srcTag").textContent = "";
  renderList(); draw();
}

function setRecord(rec) {
  return new Promise((resolve) => {
    const im = new Image();
    im.onload = () => {
      st.cur = rec; st.img = im; st.sel = -1; st.dirty = false; st.undo = []; st.fromAI = false;
      st.boxes = rec.boxes.map((b) => fromServer(b, im.width, im.height));
      $("empty").classList.add("hidden");
      const v = rec.verified_info;
      const who = v ? ` · ${esc(v.user || "no name")}, ${esc(v.verified_at)}` : "";
      const note = v && v.notes ? ` (${esc(v.notes)})` : "";
      $("info").innerHTML = `<b>${rec.index + 1}</b> / ${rec.total_images} <span class="badge ${rec.status}">${STATUS_TEXT[rec.status]}</span>${note}${who}
        <br><b>${esc(rec.filename)}</b>${rec.original ? `<br><span class="muted">${esc(rec.original)}</span>` : ""}`;
      const hint = rec.hint || (rec.source === "none" && rec.status === "unverified" ? "This image has no label yet – press I for AI boxes or draw them." : "");
      $("hint").textContent = hint ? "ℹ " + hint : "";
      $("hint").classList.toggle("hidden", !hint);
      showSrc(rec.source);
      fit(); renderList(); draw();
      syncFilmstrip();
      resolve();
    };
    im.onerror = () => { msg("Could not load image " + rec.filename, "err"); toast("⚠ Could not load image " + esc(rec.filename), "err", 8000); resolve(); };
    im.src = `/api/image_raw/${rec.index}?dataset=${enc(rec.dataset)}&f=${enc(rec.filename)}&_t=${Date.now()}`;
  });
}
function showSrc(src) {
  $("srcTag").textContent = SRC_TEXT[src] || src;
  $("srcTag").className = "srctag " + (src === "ai" ? "ai" : src === "fixed" ? "changed" : "");
}

function guard() {
  return !st.dirty || confirm("You changed the boxes but did not save. Leave this image anyway?");
}

async function loadIndex(index, key = ds(), filename = "") {
  const f = filename ? `&filename=${enc(filename)}` : "";
  let r;
  try {
    r = await api(`/api/image/${index}?dataset=${enc(key)}&filter=${$("mode").value}${f}`);
  } catch (e) {
    if (e.status !== 423) throw e;           // this file hangs when opened: tell the user and move on
    toast("⚠ " + esc(e.message), "err", 8000);
    if ($("mode").value === "unverified") return nextUnchecked(index);
    return loadIndex(index + 1, key);
  }
  r.dataset = key;
  await setRecord(r);
}

async function nextUnchecked(after = -1) {
  if (!ds()) return showEmpty("No datasets found.");
  if (!user()) return showEmpty("Type your name at the top right, then press D to start.");
  const r = await api(`/api/next?dataset=${enc(ds())}&user=${enc(user())}&after=${after}`);
  if (r.index === null) {
    showEmpty(`🎉 Every image in this dataset is checked${r.unreadable ? ` (${r.unreadable} file(s) could not be opened and were left out)` : ""}. Pick the next one at the top.`);
    refreshStats(); return;
  }
  await loadIndex(r.index);
}

async function goNext() {
  if (!guard()) return;
  const mode = $("mode").value;
  if (st.cur) st.history.push(st.cur.index);
  if (mode === "unverified") return nextUnchecked(st.cur ? st.cur.index : -1);
  if (!st.cur) return startMode();
  const fresh = await api(`/api/image/${st.cur.index}?dataset=${enc(ds())}&filter=${mode}`);
  if (fresh.next_index !== null) await loadIndex(fresh.next_index); else msg("This is the last image in this list.");
}

async function goPrev() {
  if (!guard()) return;
  if ($("mode").value === "unverified") {
    const i = st.history.pop();
    if (i !== undefined) await loadIndex(i); else msg("No earlier image in this session.");
    return;
  }
  if (st.cur && st.cur.prev_index !== null) await loadIndex(st.cur.prev_index); else msg("This is the first image in this list.");
}

async function startMode() {
  const mode = $("mode").value;
  st.history = [];
  if (mode === "unverified") return nextUnchecked(-1);
  const r = await api(`/api/images?dataset=${enc(ds())}&filter=${mode}&limit=1`);
  if (!r.images.length) return showEmpty(`No "${STATUS_TEXT[mode] || mode}" images in this dataset.`);
  await loadIndex(r.images[0].index);
}
$("mode").onchange = () => { if (guard()) { startMode(); loadFilmstrip(true); } };

// ------------------------------------------------------------ saving
async function save(kind) {
  if (st.busy) return;
  st.busy = true;
  try { await saveNow(kind); } finally { st.busy = false; }
}
async function saveNow(kind) {
  if (!st.cur || needUser()) return;
  if (kind === "verified" && !st.boxes.length) {
    msg("No boxes. If the image has no damage press N.", "err"); return;
  }
  if (kind === "negative" && st.boxes.length && !confirm("This image has boxes. Save it as NO damage and remove them?")) return;
  const i = st.cur.index, key = st.cur.dataset;
  try {
    if (kind === "skipped") {
      await api(`/api/skip/${i}`, { json: { dataset: key, notes: $("skipReason").value, user: user(), filename: st.cur.filename } });
    } else if (kind === "unverified") {
      await api(`/api/unverify/${i}?dataset=${enc(key)}&filename=${enc(st.cur.filename)}`, { method: "POST" });
    } else {
      const boxes = kind === "negative" ? [] : st.boxes.map((b) => toServer(b, st.img.width, st.img.height));
      await api(`/api/verify/${i}`, { json: { dataset: key, boxes, user: user(), notes: "", source: st.fromAI ? "ai" : "",
                                               filename: st.cur.filename } });
    }
  } catch (e) { msg(e.message, "err"); return; }
  st.dirty = false;
  msg({ verified: `✓ saved with ${st.boxes.length} box(es).`, negative: "✓ saved as no damage.",
        skipped: `skipped (${$("skipReason").value}).`, unverified: "marked not checked." }[kind], "ok");
  const found = stripImages.find((it) => it.index === i);
  if (found) {
    found.status = kind;
    found.box_count = kind === "verified" ? st.boxes.length : 0;
    renderFilmstrip();
  }
  refreshStats();
  if (kind === "unverified") return loadIndex(i);
  await goNext();
}
$("bSave").onclick = () => save("verified");
$("bNeg").onclick = () => save("negative");
$("bSkip").onclick = () => save("skipped");
$("bUncheck").onclick = () => save("unverified");
$("bClear").onclick = () => { if (st.boxes.length) { pushUndo(); st.boxes = []; st.sel = -1; changed(); } };
$("bNext").onclick = goNext;
$("bPrev").onclick = goPrev;

async function aiLabel() {
  if (!st.cur) return;
  $("bAI").disabled = true;
  msg("🤖 AI is looking at the image… (the first time loads the model, a few seconds)");
  try {
    const r = await api(`/api/predict/${st.cur.index}`, { json: { dataset: st.cur.dataset, conf: +$("conf").value || 0.3, filename: st.cur.filename } });
    pushUndo();
    st.boxes = r.boxes.map((b) => fromServer(b, st.img.width, st.img.height));
    st.sel = -1; st.fromAI = true; changed(); showSrc("ai");
    msg(r.count ? `🤖 AI found ${r.count} box(es) in ${Math.round(r.inference_ms)} ms. Check, fix, then Enter. (Ctrl+Z = back)`
                : "🤖 AI found no damage. If that's right press N. (Ctrl+Z = back)", r.count ? "ok" : "");
  } catch (e) { msg("AI failed: " + e.message, "err"); }
  $("bAI").disabled = false;
}
$("bAI").onclick = aiLabel;

async function resetToOriginal() {
  if (!st.cur || !confirm("Throw away the edited label of this image and show the original label again (not checked)?")) return;
  try {
    await api(`/api/reset/${st.cur.index}?dataset=${enc(st.cur.dataset)}&filename=${enc(st.cur.filename)}`, { method: "POST" });
  } catch (e) { msg(e.message, "err"); return; }
  st.dirty = false; refreshStats(); await loadIndex(st.cur.index); msg("Original label restored.", "ok");
}
$("bReset").onclick = resetToOriginal;

let toastTimer;
function toast(html, kind = "ok", ms = 6000) {
  let t = $("toast");
  if (!t) { t = document.createElement("div"); t.id = "toast"; document.body.appendChild(t); }
  t.innerHTML = html; t.className = "show " + kind;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.className = ""; }, ms);
  return t;
}

async function deleteByName(dataset, index, filename) {
  const r = await api(`/api/delete/${index}`, { json: { dataset, user: user(), filename } });
  stripImages = stripImages.filter((it) => it.filename !== filename);
  renderFilmstrip();
  refreshStats();
  const t = toast(`🗑 Deleted <b>${esc(filename)}</b> &nbsp;<button class="undo">↩ Undo</button>`);
  t.querySelector(".undo").onclick = async () => {
    t.className = "";
    if (await restoreImage(dataset, filename, $("tab-label").classList.contains("active"))) {
      toast(`↩ Restored <b>${esc(filename)}</b>`);
      if ($("tab-browse").classList.contains("active")) loadGrid();
    }
  };
  return r;
}

async function deleteImage() {
  if (!st.cur || st.busy) return;           // ignore a second press while the first delete is still running
  st.busy = true;
  $("bDelete").disabled = true;
  try {
    const { index, filename, dataset } = st.cur;
    st.img = null;
    st.boxes = [];
    draw();
    const r = await deleteByName(dataset, index, filename);
    st.dirty = false; st.history = [];          // indexes shifted: old history is no longer valid
    const next = $("mode").value === "unverified" ? r.next_unverified_index : r.next_index;
    if (next === null || next === undefined) showEmpty("No images left in this list.");
    else await loadIndex(next);
    msg(`🗑 Deleted ${filename}. Next image shown.`, "ok");
  } catch (e) {
    msg(e.message, "err"); toast("⚠ " + esc(e.message), "err");
  } finally {
    st.busy = false; $("bDelete").disabled = false;
  }
}
$("bDelete").onclick = deleteImage;

async function restoreImage(dataset, filename, open) {
  try {
    const r = await api("/api/restore", { json: { dataset, filename } });
    refreshStats();
    if (open && r.index !== null) { st.history = []; await loadIndex(r.index, dataset, filename); }
    msg(`↩ Restored ${filename}.`, "ok");
    return true;
  } catch (e) { msg(e.message, "err"); return false; }
}

// ------------------------------------------------------------ class + box list
function setClassButtons(c) {
  st.cls = c;
  document.querySelectorAll(".cls").forEach((b) => b.classList.toggle("active", +b.dataset.c === c));
}
function setClass(c) {
  setClassButtons(c);
  if (st.sel >= 0 && st.boxes[st.sel].c !== c) { pushUndo(); st.boxes[st.sel].c = c; changed(); }
}
document.querySelectorAll(".cls").forEach((b) => b.onclick = () => setClass(+b.dataset.c));

function renderList() {
  $("nbox").textContent = st.boxes.length ? `(${st.boxes.length})` : "";
  $("boxes").innerHTML = st.boxes.map((b, i) => `
    <li data-i="${i}" class="${i === st.sel ? "sel" : ""}">
      <span class="dot" style="background:${CLASS[b.c].color}"></span>
      <select data-i="${i}">${CLASS.map((c, k) => `<option value="${k}" ${k === b.c ? "selected" : ""}>${c.name}</option>`).join("")}</select>
      ${b.conf ? `<span class="muted small">${b.conf.toFixed(2)}</span>` : ""}
      <button data-del="${i}" title="Delete box">✕</button>
    </li>`).join("") || `<li class="muted small">none – drag on the image to draw, or press I</li>`;
}
$("boxes").onclick = (e) => {
  const del = e.target.dataset.del;
  if (del !== undefined) { pushUndo(); st.boxes.splice(+del, 1); st.sel = -1; changed(); return; }
  const li = e.target.closest("li[data-i]");
  if (li && e.target.tagName !== "SELECT") { st.sel = +li.dataset.i; renderList(); draw(); }
};
$("boxes").onchange = (e) => {
  if (e.target.tagName === "SELECT") { pushUndo(); st.boxes[+e.target.dataset.i].c = +e.target.value; changed(); }
};

function pushUndo() { st.undo.push(JSON.stringify(st.boxes)); if (st.undo.length > 50) st.undo.shift(); }
function changed() { st.dirty = true; renderList(); draw(); }

// ------------------------------------------------------------ canvas
const cv = $("cv"), ctx = cv.getContext("2d");
let dpr = 1;
function resize() {
  const r = cv.getBoundingClientRect();
  dpr = window.devicePixelRatio || 1;
  cv.width = Math.max(1, r.width * dpr); cv.height = Math.max(1, r.height * dpr);
  draw();
}
new ResizeObserver(() => { const keep = st.img && st.view.s === st.view.fit; resize(); if (keep) fit(); }).observe($("stage"));

function fit() {
  if (!st.img) return;
  const r = cv.getBoundingClientRect();
  const s = Math.min(r.width / st.img.width, r.height / st.img.height) * 0.98;
  st.view = { s, fit: s, ox: (r.width - st.img.width * s) / 2, oy: (r.height - st.img.height * s) / 2 };
  draw();
}
const toScr = (x, y) => [x * st.view.s + st.view.ox, y * st.view.s + st.view.oy];
function toImg(e) {
  const r = cv.getBoundingClientRect();
  const sx = e.clientX - r.left, sy = e.clientY - r.top;
  return { sx, sy, x: (sx - st.view.ox) / st.view.s, y: (sy - st.view.oy) / st.view.s };
}
const clampX = (x) => Math.min(Math.max(x, 0), st.img.width);
const clampY = (y) => Math.min(Math.max(y, 0), st.img.height);
const norm = (b) => ({ c: b.c, conf: b.conf, x1: Math.min(b.x1, b.x2), y1: Math.min(b.y1, b.y2), x2: Math.max(b.x1, b.x2), y2: Math.max(b.y1, b.y2) });

function draw() {
  const r = cv.getBoundingClientRect();
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, r.width, r.height);
  if (!st.img) return;
  const { s, ox, oy } = st.view;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(st.img, ox, oy, st.img.width * s, st.img.height * s);
  const all = st.drag && st.drag.type === "new" ? [...st.boxes, st.drag.box] : st.boxes;
  if (!st.hide) all.forEach((b0, i) => {
    const b = norm(b0);
    const [x1, y1] = toScr(b.x1, b.y1), [x2, y2] = toScr(b.x2, b.y2);
    const col = CLASS[b.c].color, sel = i === st.sel;
    ctx.fillStyle = col + (sel ? "33" : "1a");
    ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
    ctx.lineWidth = sel ? 3 : 2;
    ctx.strokeStyle = col;
    if (sel) {
      ctx.shadowColor = col;
      ctx.shadowBlur = 10;
    }
    if (b.conf) ctx.setLineDash([7, 4]);        // AI boxes are dashed until you touch or save them
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
    ctx.setLineDash([]);
    ctx.shadowBlur = 0;

    const tag = `${i + 1} ${CLASS[b.c].name}${b.conf ? " " + b.conf.toFixed(2) : ""}`;
    ctx.font = "600 12px 'JetBrains Mono', 'Plus Jakarta Sans', sans-serif";
    const tw = ctx.measureText(tag).width + 10;
    const ty = y1 - 20 >= 0 ? y1 - 20 : y2;
    ctx.fillStyle = col;
    if (ctx.roundRect) {
      ctx.beginPath();
      ctx.roundRect(x1, ty, tw, 20, [4, 4, 0, 0]);
      ctx.fill();
    } else {
      ctx.fillRect(x1, ty, tw, 20);
    }
    ctx.fillStyle = "#ffffff";
    ctx.fillText(tag, x1 + 5, ty + 14);

    if (sel) {
      ctx.fillStyle = "#ffffff";
      ctx.strokeStyle = "#080c14";
      ctx.lineWidth = 1.5;
      for (const [hx, hy] of [[x1, y1], [x2, y1], [x1, y2], [x2, y2]]) {
        ctx.fillRect(hx - 5, hy - 5, 10, 10);
        ctx.strokeRect(hx - 5, hy - 5, 10, 10);
      }
    }
  });

  if (st.mouse && !st.drag) {      // crosshair helps to place the first corner exactly
    ctx.setLineDash([5, 5]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(255, 255, 255, 0.45)";
    ctx.beginPath();
    ctx.moveTo(st.mouse.sx, 0);
    ctx.lineTo(st.mouse.sx, r.height);
    ctx.moveTo(0, st.mouse.sy);
    ctx.lineTo(r.width, st.mouse.sy);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  if ($("hudZoom")) $("hudZoom").textContent = `Zoom: ${Math.round((st.view.s / (st.view.fit || 1)) * 100)}%`;
  if ($("hudBoxes")) $("hudBoxes").textContent = `${st.boxes.length} Box${st.boxes.length === 1 ? "" : "es"}`;
}

function hitHandle(p) {
  if (st.sel < 0 || st.hide) return -1;
  const b = norm(st.boxes[st.sel]);
  const pts = [[b.x1, b.y1], [b.x2, b.y1], [b.x1, b.y2], [b.x2, b.y2]];
  return pts.findIndex(([x, y]) => { const [hx, hy] = toScr(x, y); return Math.abs(hx - p.sx) <= 8 && Math.abs(hy - p.sy) <= 8; });
}
function hitBox(p) {
  if (st.hide) return -1;
  let best = -1, area = Infinity;
  st.boxes.forEach((b0, i) => {
    const b = norm(b0);
    if (p.x >= b.x1 && p.x <= b.x2 && p.y >= b.y1 && p.y <= b.y2) {
      const a = (b.x2 - b.x1) * (b.y2 - b.y1);
      if (a < area) { area = a; best = i; }
    }
  });
  return best;
}

cv.addEventListener("contextmenu", (e) => e.preventDefault());
cv.addEventListener("mousedown", (e) => {
  if (!st.img) return;
  const p = toImg(e);
  if (e.button === 2 || e.button === 1 || (e.button === 0 && e.ctrlKey)) {   // Control+drag = pan on a Mac trackpad
    st.drag = { type: "pan", sx: p.sx, sy: p.sy, ox: st.view.ox, oy: st.view.oy }; return; }
  if (e.button !== 0) return;
  const h = hitHandle(p);
  if (h >= 0) {
    pushUndo();
    st.boxes[st.sel] = norm(st.boxes[st.sel]);
    st.drag = { type: "resize", corner: h }; return;
  }
  const i = hitBox(p);
  if (i >= 0) {
    st.sel = i; pushUndo(); setClassButtons(st.boxes[i].c);
    st.drag = { type: "move", x: p.x, y: p.y, orig: { ...st.boxes[i] }, moved: false };
    renderList(); draw(); return;
  }
  st.sel = -1;
  const x = clampX(p.x), y = clampY(p.y);
  st.drag = { type: "new", box: { c: st.cls, x1: x, y1: y, x2: x, y2: y } };
  renderList(); draw();
});
window.addEventListener("mousemove", (e) => {
  if (!st.img) return;
  const p = toImg(e);
  const inside = e.target === cv;
  st.mouse = inside ? p : null;
  const d = st.drag;
  if (!d) {
    if (inside) cv.style.cursor = hitHandle(p) >= 0 ? "nwse-resize" : hitBox(p) >= 0 ? "move" : "crosshair";
    draw(); return;
  }
  if (d.type === "pan") { st.view.ox = d.ox + p.sx - d.sx; st.view.oy = d.oy + p.sy - d.sy; }
  else if (d.type === "new") { d.box.x2 = clampX(p.x); d.box.y2 = clampY(p.y); }
  else if (d.type === "move") {
    const o = d.orig, w = o.x2 - o.x1, h = o.y2 - o.y1;
    const nx = Math.min(Math.max(o.x1 + p.x - d.x, 0), st.img.width - w);
    const ny = Math.min(Math.max(o.y1 + p.y - d.y, 0), st.img.height - h);
    st.boxes[st.sel] = { c: o.c, x1: nx, y1: ny, x2: nx + w, y2: ny + h };
    d.moved = true;
  } else if (d.type === "resize") {
    const b = st.boxes[st.sel];
    delete b.conf;
    if (d.corner === 0 || d.corner === 2) b.x1 = clampX(p.x); else b.x2 = clampX(p.x);
    if (d.corner === 0 || d.corner === 1) b.y1 = clampY(p.y); else b.y2 = clampY(p.y);
  }
  draw();
});
window.addEventListener("mouseup", () => {
  const d = st.drag;
  if (!d) return;
  st.drag = null;
  if (d.type === "new") {
    const b = norm(d.box);
    delete b.conf;
    if ((b.x2 - b.x1) * st.view.s >= 5 && (b.y2 - b.y1) * st.view.s >= 5) {
      pushUndo(); st.boxes.push(b); st.sel = -1; changed();   // not selected: pressing 1/2 next must not recolour it
    } else draw();
  } else if (d.type === "resize" || (d.type === "move" && d.moved)) {
    st.boxes[st.sel] = norm(st.boxes[st.sel]); changed();
  } else if (d.type === "move") { st.undo.pop(); draw(); }
});
cv.addEventListener("wheel", (e) => {
  if (!st.img) return;
  e.preventDefault();
  const p = toImg(e);
  const k = Math.exp(-e.deltaY * 0.0015);
  const s = Math.min(Math.max(st.view.s * k, st.view.fit * 0.5), st.view.fit * 25);
  st.view.ox = p.sx - p.x * s; st.view.oy = p.sy - p.y * s; st.view.s = s;
  draw();
}, { passive: false });

// ------------------------------------------------------------ keyboard
window.addEventListener("keydown", (e) => {
  if (!$("tab-label").classList.contains("active")) return;
  const t = e.target.tagName;
  if (t === "INPUT" || t === "TEXTAREA" || (t === "SELECT" && e.key !== "Enter")) return;
  const k = e.key.toLowerCase();
  if ((e.ctrlKey || e.metaKey) && k === "z") {   // Cmd+Z on a Mac
    if (st.undo.length) { st.boxes = JSON.parse(st.undo.pop()); st.sel = -1; changed(); }
    e.preventDefault(); return;
  }
  if (e.ctrlKey || e.altKey || e.metaKey) return;
  if (e.repeat && ["x", "n", "s", "enter"].includes(k)) return;   // holding a key must not act on images nobody has looked at
  const act = {
    enter: () => save("verified"), n: () => save("negative"), s: () => save("skipped"),
    a: goPrev, arrowleft: goPrev, d: goNext, arrowright: goNext,
    i: aiLabel, r: resetToOriginal, x: deleteImage,
    1: () => setClass(0), 2: () => setClass(1),
    delete: delSel, backspace: delSel, f: fit,
    h: () => { st.hide = !st.hide; draw(); },
    escape: () => { st.sel = -1; st.drag = null; renderList(); draw(); },
  }[k];
  if (act) { e.preventDefault(); act(); }
});
function delSel() {
  if (st.sel >= 0) {
    pushUndo(); st.boxes.splice(st.sel, 1); st.sel = -1; changed();
  } else {
    toast("💡 Press <b>X</b> to delete the image (Delete key deletes selected box)", "info", 3000);
  }
}
window.addEventListener("beforeunload", (e) => { if (st.dirty) { e.preventDefault(); e.returnValue = ""; } });

// ------------------------------------------------------------ browse grid
let page = 0;
const PER = 60;
let gridSeq = 0;      // only the newest grid request may draw (an older, slower one is ignored)
async function loadDeletedGrid() {
  const seq = ++gridSeq;
  const r = await api(`/api/deleted?dataset=${enc(ds())}`);
  if (seq !== gridSeq) return;
  const q = $("search").value.toLowerCase();
  const items = r.images.filter((e) => !q || e.filename.toLowerCase().includes(q));
  $("bcount").textContent = `${items.length} deleted image(s)`;
  $("pgText").textContent = ""; $("pgPrev").disabled = true; $("pgNext").disabled = true;
  $("grid").innerHTML = items.map((e) => `
    <div class="thumb deleted-item">
      <div class="pic" style="position:relative">
        <img loading="lazy" src="/api/deleted_raw?dataset=${enc(ds())}&filename=${enc(e.filename)}" alt="">
        <button class="restore" data-f="${esc(e.filename)}">↩ Restore</button>
      </div>
      <div class="meta"><span title="${esc(e.filename)}">${esc(e.filename)}</span><span class="badge deleted">${esc(e.user || "deleted")}</span></div>
    </div>`).join("") || `<p class="muted">No deleted images in this dataset.</p>`;
}

async function loadGrid() {
  if (!ds()) return;
  if ($("bf").value === "deleted") return loadDeletedGrid();
  const seq = ++gridSeq;
  const r = await api(`/api/images?dataset=${enc(ds())}&filter=${$("bf").value}&search=${enc($("search").value)}&offset=${page * PER}&limit=${PER}`);
  if (seq !== gridSeq) return;
  const pages = Math.max(1, Math.ceil(r.total_matched / PER));
  if (page >= pages) { page = pages - 1; if (r.total_matched) return loadGrid(); }
  $("bcount").textContent = `${r.total_matched} of ${r.total_dataset} image(s)`;
  $("pgText").textContent = ` page ${page + 1} / ${pages} `;
  $("pgPrev").disabled = page === 0; $("pgNext").disabled = page + 1 >= pages;
  $("grid").innerHTML = r.images.map((it) => `
    <div class="thumb" data-i="${it.index}" data-f="${esc(it.filename)}">
      <div class="pic" style="position:relative">
        <img loading="lazy" src="/api/image_raw/${it.index}?dataset=${enc(ds())}" alt="">
        <button class="tdel" title="Delete this image (X)">🗑</button>
        <svg viewBox="0 0 1 1" preserveAspectRatio="none">${it.boxes.map((b) =>
          `<rect x="${b.x_center - b.width / 2}" y="${b.y_center - b.height / 2}" width="${b.width}" height="${b.height}" fill="none" stroke="${CLASS[b.class_id].color}" stroke-width="2" vector-effect="non-scaling-stroke"/>`).join("")}</svg>
      </div>
      <div class="meta"><span title="${esc(it.filename)}">${esc(it.filename)}</span><span class="badge ${it.status}">${STATUS_TEXT[it.status]}</span></div>
    </div>`).join("") || `<p class="muted">Nothing here.</p>`;
}
let searchTimer;
$("search").oninput = () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => { page = 0; loadGrid(); }, 300); };
$("bf").onchange = () => { page = 0; loadGrid(); };
$("pgPrev").onclick = () => { page--; loadGrid(); };
$("pgNext").onclick = () => { page++; loadGrid(); };
$("grid").onclick = async (e) => {
  if (e.target.classList.contains("restore")) {
    e.target.disabled = true;
    if (await restoreImage(ds(), e.target.dataset.f, false)) loadGrid();
    return;
  }
  const t = e.target.closest(".thumb");
  if (t && t.classList.contains("deleted-item")) return;
  if (t && e.target.classList.contains("tdel")) {
    e.target.disabled = true;
    t.classList.add("removing");
    try {
      await deleteByName(ds(), +t.dataset.i, t.dataset.f);
      if (st.cur && st.cur.dataset === ds() && st.cur.filename === t.dataset.f) { st.cur = null; st.dirty = false; }
    } catch (err) { toast("⚠ " + esc(err.message), "err"); }
    loadGrid();                     // indexes shifted: redraw the page
    return;
  }
  if (!t || !guard()) return;
  const f = $("bf").value;
  $("mode").value = ["unverified", "verified", "negative", "skipped"].includes(f) ? f : "all";
  st.history = [];
  showTab("label");
  await loadIndex(+t.dataset.i, ds(), t.dataset.f);
};

// ------------------------------------------------------------ dataset tools
async function pollAI(wasRunning = false) {
  const j = await api("/api/predict_batch");
  const line = j.dataset ? `${j.dataset}: ${j.done} / ${j.total} images, ${j.boxes} boxes` : "not started";
  $("aiLog").textContent = (j.running ? "🤖 running… " : wasRunning ? "finished. " : "") + line + (j.error ? `\nERROR: ${j.error}` : "");
  $("bAIBatch").disabled = j.running;
  if (j.running) setTimeout(() => pollAI(true), 1500);
  else if (wasRunning) { loadDatasets(); if (st.cur && !st.dirty) loadIndex(st.cur.index, st.cur.dataset); }
}
$("bAIBatch").onclick = async () => {
  const mode = document.querySelector("input[name=aimode]:checked").value;
  if (mode === "unverified" && !confirm("Replace the labels of ALL not-checked images in this dataset with AI labels?\n(\"Original\" can still restore each one.)")) return;
  try {
    await api("/api/predict_batch", { json: { dataset: ds(), mode, conf: +$("conf").value || 0.3 } });
    pollAI(true);
  } catch (e) { $("aiLog").textContent = e.message; }
};
$("bAIStop").onclick = () => api("/api/predict_batch", { method: "DELETE" });

async function refreshLabelImg() {
  if (!ds()) return;
  const r = await api(`/api/labelimg?dataset=${enc(ds())}`);
  $("bAccept").textContent = `Accept images saved in LabelImg (${r.saved_in_labelimg})`;
  $("bAccept").disabled = !r.saved_in_labelimg;
}
$("bLabelImg").onclick = async () => {
  try {
    await api("/api/labelimg/open", { json: { dataset: ds(), user: user() } });
    $("liLog").textContent = "LabelImg is opening (about 10 s).\n• The format button on the left must say YOLO.\n" +
      "• W = draw box, D = next, A = previous, Ctrl+S = save.\n• Save every image you checked, also ones with no boxes.\n" +
      "When done, come back here and press Accept.";
  } catch (e) { $("liLog").textContent = e.message; }
};
$("bAccept").onclick = async () => {
  if (!user()) { $("liLog").textContent = "Type your name at the top right first."; $("user").focus(); return; }
  const r = await api("/api/labelimg/accept", { json: { dataset: ds(), user: user() } });
  $("liLog").textContent = `Accepted: ${r.verified} with damage, ${r.negative} no damage.`;
  loadDatasets(); refreshLabelImg();
};
async function doExport(which) {
  $("exportLog").textContent = "exporting…";
  try {
    const r = await api(`/api/export?dataset=${enc(which)}`, { method: "POST" });
    $("exportLog").textContent = `Saved to ${r.folder}\n\n` + Object.entries(r.split).map(([k, v]) =>
      `${k.padEnd(5)} ${v.images} images (${v.negative} no damage) · ${v.pothole} pothole · ${v.alligator_crack} alligator`).join("\n");
  } catch (e) { $("exportLog").textContent = e.message; }
}
$("bExportOne").onclick = () => doExport(ds());
$("bEmptyDel").onclick = async () => {
  if (!confirm("Permanently delete all images in this dataset's deleted folder? This cannot be undone.")) return;
  try {
    const r = await api(`/api/empty_deleted?dataset=${enc(ds())}&confirm=true`, { method: "POST" });
    $("delLog").textContent = `Permanently removed ${r.removed} image(s).`;
    refreshStats();
  } catch (e) { $("delLog").textContent = e.message; }
};
$("bExportAll").onclick = () => doExport("all");

// ------------------------------------------------------------ bottom filmstrip
let stripDataset = null;
let stripFilter = null;
let stripImages = [];
let stripLoading = false;

async function loadFilmstrip(force = false) {
  const dataset = ds();
  const filter = $("mode") ? $("mode").value : "all";
  if (!dataset || stripLoading) return;
  if (!force && stripDataset === dataset && stripFilter === filter && stripImages.length) {
    updateFilmstripActive();
    return;
  }
  stripLoading = true;
  stripDataset = dataset;
  stripFilter = filter;
  try {
    const r = await api(`/api/images?dataset=${enc(dataset)}&filter=${enc(filter)}&limit=1000`);
    stripImages = r.images || [];
    renderFilmstrip();
  } catch (err) {
    console.error("Filmstrip load error:", err);
  } finally {
    stripLoading = false;
  }
}

function renderFilmstrip() {
  const el = $("filmstrip");
  if (!el) return;
  if (!stripImages.length) {
    el.innerHTML = '<span class="muted small" style="margin:auto; padding:0 20px;">No frames matching current filter.</span>';
    return;
  }
  el.innerHTML = stripImages.map((it) => {
    const isCur = st.cur && it.index === st.cur.index;
    const statusIcon = it.status === "verified" ? "✓" : it.status === "negative" ? "✨" : it.status === "skipped" ? "⏭" : "";
    return `
      <div class="strip-item ${isCur ? "active" : ""}" data-i="${it.index}" data-f="${esc(it.filename)}" title="${esc(it.filename)}">
        <img loading="lazy" src="/api/image_raw/${it.index}?dataset=${enc(ds())}&f=${enc(it.filename)}" alt="">
        <span class="strip-idx">#${it.index + 1}</span>
        ${statusIcon ? `<span class="strip-status ${it.status}">${statusIcon}</span>` : ""}
        ${it.box_count > 0 ? `<span class="strip-count">${it.box_count}</span>` : ""}
      </div>
    `;
  }).join("");

  updateFilmstripActive();
}

function updateFilmstripActive() {
  const el = $("filmstrip");
  if (!el || !st.cur) return;
  
  if ($("stripCounter")) {
    $("stripCounter").textContent = `${st.cur.index + 1} / ${st.cur.total_images}`;
  }

  const prevActive = el.querySelector(".strip-item.active");
  if (prevActive) prevActive.classList.remove("active");

  const newActive = el.querySelector(`.strip-item[data-i="${st.cur.index}"]`);
  if (newActive) {
    newActive.classList.add("active");
    newActive.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
  }
}

function syncFilmstrip() {
  if (stripDataset !== ds() || stripFilter !== $("mode").value || !stripImages.length) {
    loadFilmstrip();
  } else {
    updateFilmstripActive();
  }
}

if ($("filmstrip")) {
  $("filmstrip").onclick = async (e) => {
    const item = e.target.closest(".strip-item");
    if (!item || !guard()) return;
    const idx = +item.dataset.i;
    const fn = item.dataset.f;
    await loadIndex(idx, ds(), fn);
  };

  $("filmstrip").addEventListener("wheel", (e) => {
    if (e.deltaY) {
      e.preventDefault();
      $("filmstrip").scrollLeft += e.deltaY;
    }
  }, { passive: false });
}

if ($("bStripPrev")) {
  $("bStripPrev").onclick = () => {
    if ($("filmstrip")) $("filmstrip").scrollBy({ left: -360, behavior: "smooth" });
  };
}
if ($("bStripNext")) {
  $("bStripNext").onclick = () => {
    if ($("filmstrip")) $("filmstrip").scrollBy({ left: 360, behavior: "smooth" });
  };
}

// ------------------------------------------------------------ start
$("user").value = store.get("labeler") || "";
$("user").oninput = () => { store.set("labeler", user()); $("user").classList.remove("need"); };
$("user").onchange = () => { if (!st.cur && $("mode").value === "unverified") nextUnchecked(-1); };
(async () => {
  resize();
  await loadDatasets();
  pollAI();
  startMode();
})();

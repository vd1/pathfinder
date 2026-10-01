"use strict";
// Renders /api/state. Filters and the open document live in the URL hash, so a view can be linked:
// #stage=edit&state=blocked filters the units; #note=Q1P1&doc=paper opens a unit's document.
const $ = (id) => document.getElementById(id);
let state = null;

function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
function hash() { return Object.fromEntries(new URLSearchParams(location.hash.slice(1))); }
function setHash(update) {
  const h = { ...hash(), ...update };
  Object.keys(h).forEach((k) => (h[k] === null || h[k] === undefined) && delete h[k]);
  location.hash = new URLSearchParams(h).toString();
}
function docUrl(path) { return "/doc?path=" + encodeURIComponent(path); }

function renderParams() {
  const c = state.campaign, b = c.budget, r = state.runner || {};
  $("title").textContent = c.name;
  $("progress").textContent = "progress " + state.progress.status;
  $("progress").className = "pill " + state.progress.status;
  $("updated").textContent = "updated " + state.generated_at;
  const rows = [["backend", c.backend + " / " + c.model], ["scheme", c.research_scheme], ["seats", c.seats],
    ["rounds", c.rounds], ["calls", b.calls], ["input tokens", b.input_tokens + " (" + b.cache_read + " cached)"],
    ["output tokens", b.output_tokens], ["runner", (r.status || "none") + (r.pid_alive ? "" : r.status ? " (not alive)" : "")],
    ["execution", String(c.execution_id || "").slice(0, 12)]];
  let html = "<dl>" + rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("") + "</dl>";
  if (c.stop) html += `<p class="warn">Stopped: ${esc(c.stop.reason)}</p>`;
  if (state.progress.events_truncated) html += `<p class="warn">The event stream is cut: progress is unknown until the full record is read.</p>`;
  $("params").innerHTML = html;
}

function renderPipeline() {
  const h = hash();
  $("pipeline").innerHTML = Object.entries(state.stages).map(([stage, counts]) => {
    const total = Object.values(counts).reduce((a, n) => a + n, 0);
    const chips = Object.entries(counts).map(([s, n]) => {
      const on = h.stage === stage && h.state === s ? " on" : "";
      return `<button class="chip ${esc(s)}${on}" data-stage="${esc(stage)}" data-state="${esc(s)}">${esc(s)} ${n}</button>`;
    }).join("");
    return `<div class="card stage"><b>${total}</b><span>${esc(stage)}</span><div>${chips}</div></div>`;
  }).join("");
  $("pipeline").querySelectorAll("button.chip").forEach((el) => el.addEventListener("click", () => {
    const h2 = hash();
    const same = h2.stage === el.dataset.stage && h2.state === el.dataset.state;
    setHash({ stage: same ? null : el.dataset.stage, state: same ? null : el.dataset.state });
  }));
}

function renderBlocks() {
  $("blocks").innerHTML = state.blocks.length ? `<div class="card"><h2>Blocks</h2><ul>` + state.blocks.map((b) =>
    `<li><b>${esc(b["class"])}</b> ${esc(b.cause)} &times;${b.count}: ${b.units.map((u) => `<a href="#note=${esc(u)}">${esc(u)}</a>`).join(", ")}</li>`).join("") + `</ul></div>` : "";
}

function axisState(unit, stage) {
  return stage === "research" ? unit.research.status : stage === "edit" ? (unit.editorial.status || (["PAUSE", "DRAFT", "REJECT", "PAUSE-ON-ITERATE", "PAUSE-ON-REVISE"].includes(unit.research.status) ? "queued" : null))
    : (unit.assessment.status || (unit.research.status === "DRAFT" && unit.editorial.status === "done" ? "queued" : null));
}

function renderUnits() {
  const h = hash();
  let units = state.units.slice().sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
  if (h.stage && h.state) units = units.filter((u) => axisState(u, h.stage) === h.state);
  const head = "<tr><th>unit</th><th>score</th><th>now</th><th>research</th><th>edit</th><th>paper</th><th>last activity</th><th>documents</th></tr>";
  const rows = units.map((u) => `<tr class="${h.note === u.unit ? "sel" : ""}">
    <td><a href="#note=${esc(u.unit)}">${esc(u.unit)}</a></td><td>${esc(u.score ?? "")}</td>
    <td><span class="pill ${esc(u.controller)}">${esc(u.controller)}</span></td>
    <td title="${esc(u.research.reason)}">${esc(u.research.status)}</td><td title="${esc(u.editorial.reason)}">${esc(u.editorial.status ?? "")}</td>
    <td title="${esc(u.assessment.reason)}">${esc(u.assessment.status ?? "")}</td><td>${esc(u.last_activity ?? "")}</td>
    <td>${u.documents.map((d) => `<a href="#note=${esc(u.unit)}&doc=${encodeURIComponent(d.kind)}">${esc(d.kind)}${d.stale ? " (stale)" : ""}</a>`).join(" · ")}</td></tr>`).join("");
  const filter = h.stage ? `<p class="muted">Filter: ${esc(h.stage)} = ${esc(h.state)} <a href="#">clear</a></p>` : "";
  $("units").innerHTML = `<h2>Units (${units.length})</h2>${filter}<table>${head}${rows}</table>`;
}

function renderReader() {
  const h = hash();
  const unit = state.units.find((u) => u.unit === h.note);
  if (!unit) { $("reader").innerHTML = `<p class="muted">Select a unit to read its documents.</p>`; return; }
  if (!unit.documents.length) { $("reader").innerHTML = `<h2>${esc(unit.unit)}</h2><p class="muted">No document yet.</p>`; return; }
  const doc = unit.documents.find((d) => d.kind === h.doc) || unit.documents[unit.documents.length - 1];
  const tabs = unit.documents.map((d) => `<a class="tab${d === doc ? " on" : ""}" href="#note=${esc(unit.unit)}&doc=${encodeURIComponent(d.kind)}">${esc(d.kind)}</a>`).join("");
  const links = [doc.source ? `<a href="${docUrl(doc.source)}" target="_blank" rel="noopener">LaTeX source</a>` : "",
    doc.pdf ? `<a href="${docUrl(doc.pdf)}" target="_blank" rel="noopener">open PDF</a>` : "",
    `<a href="#note=${esc(unit.unit)}&doc=${encodeURIComponent(doc.kind)}">link to this document</a>`].filter(Boolean).join(" · ");
  const warn = doc.stale ? `<p class="warn">This PDF is older than its source; the source has changed since it was built.</p>` : "";
  const body = doc.pdf ? `<iframe title="${esc(doc.kind)}" src="${docUrl(doc.pdf)}"></iframe>` : `<pre id="source">loading source…</pre>`;
  $("reader").innerHTML = `<h2>${esc(unit.unit)}</h2><nav>${tabs}</nav><p>${links}</p>${warn}${body}`;
  if (!doc.pdf && doc.source) {
    fetch(docUrl(doc.source)).then((r) => r.text()).then((t) => { const el = $("source"); if (el) el.textContent = t; });
  }
}

function render() { if (!state) return; renderParams(); renderPipeline(); renderBlocks(); renderUnits(); renderReader(); }

async function load() {
  try {
    const r = await fetch("/api/state", { cache: "no-store" });
    const doc = await r.json();
    if (!r.ok) throw new Error(doc.error || r.status);
    const reading = hash().note && state && JSON.stringify(state.units) === JSON.stringify(doc.units);
    state = doc;
    if (reading) { renderParams(); renderPipeline(); renderBlocks(); renderUnits(); } else { render(); }
  } catch (error) {
    $("progress").textContent = "state unavailable: " + error.message;
    $("progress").className = "pill unknown";
  }
}

window.addEventListener("hashchange", render);
load();
setInterval(load, 10000);

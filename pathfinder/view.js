"use strict";
// The operator view, ported from statarb's arXiv watchboard. It renders /api/state; every unit sits in
// exactly one pipeline state, decided by the server. Documents and details open in one dialog that
// refreshes never touch. A link such as #note=Q1P1&doc=paper opens that document directly.
let current = null;
let refreshing = false;
const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) =>
  ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const num = (value) => value == null ? "Unknown" : Number(value).toLocaleString("en-GB", {maximumFractionDigits: 1});
// Large counts in human units: 21.6 M, 182 k; the exact value stays in the title attribute.
const human = (value) => {
  if (value == null) return "Unknown";
  const n = Number(value), abs = Math.abs(n);
  const [div, unit] = abs >= 1e9 ? [1e9, " G"] : abs >= 1e6 ? [1e6, " M"] : abs >= 1e3 ? [1e3, " k"] : [1, ""];
  const scaled = n / div;
  return (div === 1 ? String(n) : scaled.toFixed(Math.abs(scaled) >= 100 ? 0 : 1)) + unit;
};
const tokens = (value) => `<span title="${esc(num(value))}">${esc(human(value))}</span>`;
const short = (value, length = 180) => String(value || "").length > length
  ? String(value).slice(0, length - 3) + "..." : String(value || "");
const when = (value) => value ? String(value).replace("T", " ").replace("Z", " UTC") : "Not yet";
const duration = (seconds) => seconds == null ? "Unknown"
  : seconds < 60 ? Math.round(seconds) + " s"
  : seconds < 3600 ? Math.round(seconds / 60) + " min"
  : seconds < 86400 ? num(seconds / 3600) + " h" : num(seconds / 86400) + " d";
// A coordination serves several arms; the chosen one travels with every request and in the link.
let arm = new URLSearchParams(location.hash.slice(1)).get("arm") || null;
const armQuery = (sep) => arm ? sep + "arm=" + encodeURIComponent(arm) : "";
const docURL = (path) => "/doc?path=" + encodeURIComponent(path) + armQuery("&");
const arxivURL = (id) => "https://arxiv.org/abs/" + encodeURIComponent(id);
// Local manuscripts and dossiers are not arXiv papers: link only identifiers arXiv would resolve.
const isArxiv = (id) => /^\d{4}\.\d{4,5}(v\d+)?$/.test(String(id || "")) || /^[a-z-]+(\.[A-Z]{2})?\/\d{7}(v\d+)?$/.test(String(id || ""));
let filterKeys = null;

function labels() {
  const out = {};
  for (const stage of current?.pipeline || []) for (const s of stage.states) out[s.key] = s.label;
  return out;
}
const badge = (key) => `<span class="badge ${esc(key)}">${esc(labels()[key] || key)}</span>`;
const unitOf = (id) => current?.units.find((u) => u.unit === id);
const pairTitle = (u) => `${u.q?.title || "Q"} × ${u.p?.title || "P"}`;
// The most refined document: paper, then readable note, then research note.
const bestDocument = (u) => u.documents[u.documents.length - 1];
const readButton = (u, doc = bestDocument(u), label = "Read note") => doc
  ? `<button type="button" class="primary-action" data-doc="${esc(doc.kind)}" data-unit-doc="${esc(u.unit)}">${esc(label)}</button>` : "";

function renderParams() {
  const c = current.campaign, r = current.runner || {}, p = current.progress || {};
  $("page-title").textContent = c.name;
  $("lede").textContent = `${c.backend} / ${c.model}, scheme ${c.research_scheme}. Pairs are scored, the strongest researched by peers and an independent verifier, and accepted accounts edited into readable notes and papers.`;
  const rows = [["Seats", c.seats], ["Rounds", c.rounds],
    ["Allowances", Object.entries(c.allowances || {}).map(([k, v]) => k.replace("_seconds", " s").replace("_", " ") + " " + v).join(", ")],
    ["Runner", (r.status || "none") + (r.status ? (r.pid_alive ? ", alive" : ", not alive") : "")],
    ["Progress", p.status], ["Execution", String(c.execution_id || "unknown").slice(0, 12)]];
  if (c.stop) rows.push(["Stopped", c.stop.reason]);
  $("params").innerHTML = rows.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("");
}

function renderPipeline() {
  const total = current.units.length || 1, filter = $("status-filter").value;
  $("pipeline").innerHTML = current.pipeline.map((stage) => {
    const parts = stage.states.map((s) => `<button type="button" class="stage-state state-${esc(s.key)} ${filter === s.key ? "selected" : ""}"
        data-filter="${esc(s.key)}" aria-pressed="${filter === s.key}"><b>${s.count}</b> ${esc(s.label)}</button>`).join("");
    const bar = stage.states.map((s) => s.count ? `<i class="state-${esc(s.key)}" data-grow="${s.count}"></i>` : "").join("");
    return `<li class="stage"><h3>${esc(stage.title)}</h3><p class="stage-count">${stage.count}</p>
      <div class="stage-bar" data-width="${Math.max(6, 100 * stage.count / total)}" aria-hidden="true">${bar}</div>
      <div class="stage-states">${parts}</div></li>`;
  }).join("");
  // Sizes go through the CSSOM: the page's content security policy forbids inline style attributes.
  for (const bar of $("pipeline").querySelectorAll("[data-width]")) bar.style.width = bar.dataset.width + "%";
  for (const part of $("pipeline").querySelectorAll("[data-grow]")) part.style.flexGrow = part.dataset.grow;
  // Rebuild the state list only when the pipeline's states change: replacing the options of an open select
  // would close it under the operator's hand on every refresh.
  const keys = current.pipeline.flatMap((stage) => stage.states.map((s) => s.key)).join(",");
  if (keys !== filterKeys) {
    filterKeys = keys;
    const select = $("status-filter"), chosen = select.value;
    select.innerHTML = `<option value="all">All states</option>` + current.pipeline.flatMap((stage) => stage.states.map((s) =>
      `<option value="${esc(s.key)}">${esc(stage.title)}: ${esc(s.label)}</option>`)).join("");
    select.value = chosen || "all";
  }
}

function renderQueue() {
  const query = $("search").value.toLowerCase().trim(), filter = $("status-filter").value;
  const units = current.units.filter((u) => (filter === "all" || u.lifecycle === filter) && (!query ||
    [u.unit, u.q?.id, u.q?.title, u.p?.id, u.p?.title].join(" ").toLowerCase().includes(query)))
    .sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
  $("queue-count").textContent = units.length + " / " + current.units.length + " units";
  $("queue-body").innerHTML = units.length ? units.map((u) => `<tr>
      <td><button type="button" class="paper-title" data-unit="${esc(u.unit)}">${esc(pairTitle(u))}</button>
        <div class="paper-meta">${esc(u.unit)} / ${esc(u.q?.id || "")} × ${esc(u.p?.id || "")}</div>
        ${u.connexion ? `<div class="seed-preview">${esc(short(u.connexion))}</div>` : ""}</td>
      <td>${badge(u.lifecycle)}</td>
      <td class="numeric">${u.feasibility == null || u.gain == null ? '<span class="pending-score">--</span>' : esc(u.feasibility + " / " + u.gain)}</td>
      <td class="numeric">${u.score == null ? '<span class="pending-score">--</span>' : `<span class="score">${num(u.score)}</span>`}</td></tr>`).join("")
    : '<tr><td colspan="4" class="empty">No unit matches this filter.</td></tr>';
  $("queue-foot").textContent = "Score = feasibility × gain from the scan. A state counts each unit once, at the furthest stage it reached.";
}

function renderDesk() {
  const started = current.units.filter((u) => u.lifecycle !== "waiting");
  $("research-count").textContent = started.length + " investigations";
  $("research-list").innerHTML = started.length ? started.map((u) => `<article class="research-card status-${esc(u.lifecycle)}">
      <div class="card-meta">${badge(u.lifecycle)}<span>${esc(u.unit)}</span>
        <span>research ${esc(u.research.status)} / edit ${esc(u.editorial.status || "none")} / paper ${esc(u.assessment.status || "none")}</span></div>
      <h3>${esc(pairTitle(u))}</h3>
      <p class="card-summary">${esc(u.summary || "In progress: no verdict recorded yet.")}</p>
      <div class="record-actions">${readButton(u)}<button type="button" data-unit="${esc(u.unit)}">Details and receipts</button></div>
    </article>`).join("") : '<p class="empty">No investigation has started yet.</p>';
}

function renderUsage() {
  const u = current.usage;
  $("usage").innerHTML = `<dl class="usage-grid">
    <div><dt>Input tokens reported</dt><dd>${tokens(u.input_tokens)} <small>${tokens(u.cache_read)} cached</small></dd></div>
    <div><dt>Output tokens reported</dt><dd>${tokens(u.output_tokens)}</dd></div>
    <div><dt>Summed call time</dt><dd>${duration(u.seconds)}</dd></div>
    <div><dt>Calls completed</dt><dd>${u.completed} <small>of ${u.calls}</small></dd></div></dl>
    <p class="small-copy">Subscription-backed: dollar cost and the remaining allowance are not reported.
    Usage was reported for ${u.calls_with_usage} of ${u.calls} calls; call time is summed, not wall time.</p>`;
}

function renderBlocks() {
  $("blocks").innerHTML = current.blocks.length ? `<ul class="block-list">` + current.blocks.map((b) =>
    `<li><b>${esc(b["class"])}</b> ${esc(b.cause)} × ${b.count}: ${b.units.map((id) =>
      `<button type="button" class="link-button" data-unit="${esc(id)}">${esc(id)}</button>`).join(" ")}</li>`).join("") + `</ul>`
    : '<p class="empty">No blocked unit.</p>';
}

function render() {
  if (!current) return;
  renderParams(); renderPipeline(); renderQueue(); renderDesk(); renderUsage(); renderBlocks();
  $("snapshot-time").textContent = "Snapshot " + when(current.generated_at);
  const issues = [];
  if (current.campaign.stop) issues.push("Stopped: " + current.campaign.stop.reason);
  if (current.progress?.events_truncated) issues.push("The event stream is cut: progress is unknown until the full record is read.");
  $("error-banner").hidden = issues.length === 0;
  $("error-banner").textContent = issues.join(" / ");
}

function setHash(note, doc) {
  const h = new URLSearchParams(location.hash.slice(1));
  if (note) { h.set("note", note); if (doc) h.set("doc", doc); else h.delete("doc"); } else { h.delete("note"); h.delete("doc"); }
  const text = h.toString();
  history.replaceState(null, "", location.pathname + (text ? "#" + text : ""));
}

function showDialog(label, content, {wide = false, actions = ""} = {}) {
  $("detail-label").textContent = label;
  $("dialog-actions").innerHTML = actions;
  $("detail-content").innerHTML = content;
  $("detail-dialog").classList.toggle("reader", wide);
  if (!$("detail-dialog").open) $("detail-dialog").showModal();
}

function showDocument(id, kind) {
  const u = unitOf(id);
  if (!u) return;
  if (!u.documents.length) return showUnit(id);             // nothing to read yet: show what is known
  const doc = u.documents.find((d) => d.kind === kind) || bestDocument(u);
  setHash(u.unit, doc.kind);
  const others = u.documents.filter((d) => d !== doc).map((d) =>
    `<button type="button" data-doc="${esc(d.kind)}" data-unit-doc="${esc(u.unit)}">${esc(d.kind)}</button>`).join("");
  if (doc.pdf) {
    const actions = `<a href="${docURL(doc.pdf)}" target="_blank" rel="noopener noreferrer">Open in a new tab</a>
      ${doc.source ? `<button type="button" data-source="${esc(doc.source)}">View LaTeX source</button>` : ""}${others}`;
    showDialog(`${u.unit}: ${doc.kind}`, `${doc.stale ? `<p class="stale-note">This PDF is older than its LaTeX source;
        the source may hold later edits.</p>` : ""}<iframe class="pdf-frame" src="${docURL(doc.pdf)}" title="${esc(doc.kind)}"></iframe>`,
      {wide: true, actions});
  } else if (doc.source) {
    showSource(doc.source, `${u.unit}: ${doc.kind}`, others);
  }
}

async function showSource(path, label, actions = "") {
  actions = `<a href="${docURL(path)}" target="_blank" rel="noopener noreferrer">Open as text</a>${actions}`;
  showDialog(label || path.split("/").at(-1), '<p class="empty">Loading source.</p>', {actions});
  try {
    const response = await fetch(docURL(path), {cache: "no-store"});
    const text = await response.text();
    if (!response.ok) throw new Error("Source unavailable: " + text);
    $("detail-content").innerHTML = `<pre class="note-content">${esc(text)}</pre>`;
  } catch (error) {
    $("detail-content").textContent = error.message;
  }
}

function showUnit(id) {
  const u = unitOf(id);
  if (!u) return;
  setHash(null);
  const side = (label, paper) => paper?.id ? `<section class="detail-section"><h3>${label}: ${isArxiv(paper.id)
      ? `<a href="${arxivURL(paper.id)}" target="_blank" rel="noopener noreferrer">${esc(paper.id)}</a>` : esc(paper.id)}</h3><p><strong>${esc(paper.title)}</strong></p><p class="detail-abstract">${esc(paper.abstract)}</p></section>` : "";
  const axis = (label, s) => `<p><strong>${label}</strong> ${esc(s.status || "none")}${s.reason ? ": " + esc(s.reason) : ""}</p>`;
  showDialog("Unit " + u.unit, `<h2>${esc(pairTitle(u))}</h2><p>${badge(u.lifecycle)}</p>
    <div class="record-actions">${u.documents.map((d) => readButton(u, d, d.kind + (d.stale ? " (stale)" : ""))).join("")}</div>
    ${side("Q", u.q)}${side("P", u.p)}
    <section class="detail-section"><h3>Scan</h3><p>Feasibility ${esc(u.feasibility ?? "--")}; gain ${esc(u.gain ?? "--")}; score ${esc(u.score ?? "--")}.</p>
      <p>${esc(u.connexion || "")}</p></section>
    <section class="detail-section"><h3>States</h3>${axis("Research", u.research)}${axis("Readable note", u.editorial)}${axis("Paper", u.assessment)}
      <p class="small-copy">Now ${esc(u.controller)}; last activity ${esc(when(u.last_activity))}.</p></section>
    <section class="detail-section"><h3>Usage</h3><p>${u.usage.calls} calls, ${tokens(u.usage.input_tokens)} input and
      ${tokens(u.usage.output_tokens)} output tokens, ${duration(u.usage.seconds)} of call time.</p></section>`);
}

// A link such as #note=Q1P1&doc=paper opens that unit's document, so a note can be shared as a URL.
function openFromHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get("note") && current) showDocument(h.get("note"), h.get("doc"));
}

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-unit],[data-unit-doc],[data-source],[data-filter]");
  if (!target || !current) return;
  if (target.dataset.filter) {
    const select = $("status-filter");
    select.value = select.value === target.dataset.filter ? "all" : target.dataset.filter;
    renderQueue(); renderPipeline();
    $("queue-heading").scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start"});
  } else if (target.dataset.unitDoc) showDocument(target.dataset.unitDoc, target.dataset.doc);
  else if (target.dataset.source) showSource(target.dataset.source);
  else if (target.dataset.unit) showUnit(target.dataset.unit);
});
$("close-dialog").addEventListener("click", () => $("detail-dialog").close());
$("detail-dialog").addEventListener("close", () => setHash(null));
$("search").addEventListener("input", renderQueue);
$("status-filter").addEventListener("change", () => { renderQueue(); renderPipeline(); });
$("refresh-button").addEventListener("click", refresh);
window.addEventListener("hashchange", openFromHash);

async function refresh() {
  if (refreshing) return;
  refreshing = true;
  $("refresh-button").disabled = true;
  try {
    const response = await fetch("/api/state" + armQuery("?"), {cache: "no-store"});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Campaign state unavailable");
    const first = current === null;
    current = data;
    render();
    if (first) openFromHash();
    $("connection-dot").classList.add("connected");
    $("connection-text").textContent = "Campaign state connected";
  } catch (error) {
    $("connection-dot").classList.remove("connected");
    $("connection-text").textContent = "Refresh unavailable";
    $("error-banner").hidden = false;
    $("error-banner").textContent = error.message + (current ? " Showing the last successful snapshot." : "");
  } finally {
    refreshing = false;
    $("refresh-button").disabled = false;
  }
}

async function loadArms() {
  try {
    const arms = await (await fetch("/api/arms", {cache: "no-store"})).json();
    if (arms.length > 1) {
      if (!arm || !arms.some((a) => a.arm === arm)) arm = arms[0].arm;
      $("arm-select").innerHTML = arms.map((a) => `<option value="${esc(a.arm)}">${esc(a.arm)}${a.units != null ? " (" + a.units + " units)" : ""}</option>`).join("");
      $("arm-select").value = arm;
      $("arm-select").hidden = false;
    } else {
      arm = null;
    }
  } catch (error) {
    arm = null;
  }
}

async function chooseArm(name) {
  arm = name;
  const h = new URLSearchParams(location.hash.slice(1)); h.set("arm", name); h.delete("note"); h.delete("doc");
  history.replaceState(null, "", location.pathname + "#" + h.toString());
  current = null;                                   // a different campaign: render it afresh
  filterKeys = null;
  await refresh();
}

$("arm-select").addEventListener("change", () => chooseArm($("arm-select").value));
loadArms().then(refresh);
setInterval(refresh, 20000);

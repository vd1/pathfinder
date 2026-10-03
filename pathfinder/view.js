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
  ? `<button type="button" class="primary-action" data-doc="${esc(doc.kind)}" data-unit-doc="${esc(u.unit)}">${esc(label)}</button>`
    + (doc.pdf ? ` <button type="button" data-open-pdf="${esc(doc.pdf)}">Open PDF</button>` : "") : "";
// A PDF opens in the operator's own viewer: the server opens it, only if this page offers it.
async function openPdf(path) {
  try {
    const r = await fetch("/open" + armQuery("?"), {method: "POST", headers: {"Content-Type": "application/json"},
                                                    body: JSON.stringify({path})});
    if (!r.ok) throw new Error(await r.text());
  } catch (error) {
    $("error-banner").hidden = false; $("error-banner").textContent = "Could not open the PDF: " + error.message;
  }
}

function renderParams() {
  const c = current.campaign, r = current.runner || {}, p = current.progress || {};
  $("page-title").textContent = c.title || c.name;
  $("lede").textContent = c.description || `${c.backend} / ${c.model}, scheme ${c.research_scheme}. Pairs are scored, the strongest researched by peers and an independent verifier, and accepted accounts edited into readable notes and papers.`;
  const allowances = Object.entries(c.allowances || {});
  const rows = [["Seats", c.account ? `${c.seats}; account ${c.account.name}: ${c.account.in_use ?? "?"} of ${c.account.seats} in use` : c.seats],
    ...(current.units.length ? [["Rounds", c.rounds]] : []),
    ...(allowances.length ? [["Allowances", allowances.map(([k, v]) => k.replace("_seconds", " s").replace("_", " ") + " " + v).join(", ")]] : []),
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

// A deployment's own tables (extension "panels"): text cells, numbers in human units, https links only.
const cell = (value) => {
  if (value && typeof value === "object" && (value.pdf || value.open))
    return `<button type="button" class="link-button" data-open-pdf="${esc(value.pdf || value.open)}">${esc(value.text ?? "Open")}</button>`;
  if (value && typeof value === "object" && /^https:\/\//.test(String(value.href || "")))
    return `<a href="${esc(value.href)}" rel="noreferrer" target="_blank">${esc(value.text ?? value.href)}</a>`;
  if (typeof value === "number") return Math.abs(value) >= 1e4 ? tokens(value) : esc(num(value));
  return esc(short(value && typeof value === "object" ? JSON.stringify(value) : value, 240));
};

// Collapsed boxes are remembered in this browser, by box name; the page works without storage.
const collapsed = (() => { try { return new Set(JSON.parse(localStorage.getItem("pathfinder-collapsed") || "[]")); }
                           catch { return new Set(); } })();
const saveCollapsed = () => { try { localStorage.setItem("pathfinder-collapsed", JSON.stringify([...collapsed])); } catch {} };
const toggle = (box) => `<button type="button" class="box-toggle" data-toggle-box="${esc(box)}"
  aria-expanded="${!collapsed.has(box)}" title="Show or hide">${collapsed.has(box) ? "Show" : "Hide"}</button>`;
const boxClass = (box) => collapsed.has(box) ? " collapsed" : "";
// Every box of the page itself gets the same toggle (its name is its heading).
function decorateBoxes() {
  for (const box of document.querySelectorAll ? document.querySelectorAll("section.panel, section.pipeline, section.intro") : []) {
    const name = box.dataset.box || (box.querySelector("h1,h2")?.textContent || box.getAttribute("aria-label") || "").trim();
    if (!name) continue;
    box.dataset.box = name;
    // a box drawn with its own toggle (a deployment panel's heading) gets no second one
    if (!box.querySelector(".box-toggle")) box.insertAdjacentHTML("afterbegin", toggle(name));
    box.classList.toggle("collapsed", collapsed.has(name));
  }
}

const actionButton = (a) => a && (a.pdf || a.open) ? `<button type="button" data-open-pdf="${esc(a.pdf || a.open)}">${esc(a.text ?? "Open")}</button>`
  : a && /^https:\/\//.test(String(a.href || "")) ? `<a href="${esc(a.href)}" rel="noreferrer" target="_blank">${esc(a.text ?? a.href)}</a>` : "";

// A deployment's own boxes, drawn in the page's designs: pipeline, metrics, cards, table.
const PANEL = {
  pipeline: (p) => `<ol class="stages">${p.stages.map((stage, _i, all) => {
      const count = stage.states.reduce((n, s) => n + (s.count || 0), 0);
      const total = all.reduce((n, st) => n + st.states.reduce((m, s) => m + (s.count || 0), 0), 0) || 1;
      const bar = stage.states.map((s) => s.count ? `<i class="state-${esc(s.key)}" data-grow="${s.count}"></i>` : "").join("");
      return `<li class="stage"><h3>${esc(stage.title)}</h3><p class="stage-count">${count}</p>
        <div class="stage-bar" data-width="${Math.max(6, 100 * count / total)}" aria-hidden="true">${bar}</div>
        <div class="stage-states">${stage.states.map((s) => `<span class="stage-state state-${esc(s.key)}"><b>${s.count || 0}</b> ${esc(s.label)}</span>`).join("")}</div></li>`;
    }).join("")}</ol>`,
  metrics: (p) => `<dl class="usage-grid">${p.items.map((i) => `<div><dt>${esc(i.label)}</dt><dd>${typeof i.value === "number" ? tokens(i.value) : esc(i.value ?? "Unknown")}${i.small ? ` <small>${esc(i.small)}</small>` : ""}</dd></div>`).join("")}</dl>`,
  cards: (p) => p.cards.length ? `<div class="${p.grid ? "strategy-grid" : "research-list"}">${p.cards.map((c) => `
      <article class="${p.grid ? "strategy-card" : "research-card"} status-${esc(c.status || "")}">
        <div class="card-meta">${c.badge ? `<span class="badge ${esc(c.status || "")}">${esc(c.badge)}</span>` : ""}${(c.meta || []).map((m) => `<span>${esc(m)}</span>`).join("")}</div>
        <h3>${esc(c.title)}</h3>${c.summary ? `<p class="card-summary">${esc(c.summary)}</p>` : ""}
        ${c.issue ? `<p class="card-issue">${esc(c.issue)}</p>` : ""}
        ${(c.actions || []).length ? `<div class="record-actions">${c.actions.map(actionButton).join("")}</div>` : ""}
      </article>`).join("")}</div>` : `<p class="empty">${esc(p.empty || "Nothing yet.")}</p>`,
  table: (p) => p.columns.length ? `<div class="table-scroll"><table><thead><tr>${p.columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${p.rows.length ? p.rows.map((r) => `<tr>${r.map((v) => `<td>${cell(v)}</td>`).join("")}</tr>`).join("")
      : `<tr><td colspan="${p.columns.length}" class="empty">Nothing yet.</td></tr>`}</tbody></table></div>` : "",
};

function renderPanels() {
  $("panels").innerHTML = (current.panels || []).map((p) => {
    const box = "panel:" + p.title, draw = PANEL[p.kind || "table"] || PANEL.table;
    return `<section class="panel${p.kind === "pipeline" ? " pipeline-panel" : ""}${boxClass(box)}" data-box="${esc(box)}">
      <div class="section-heading"><h2>${esc(p.title)}</h2>${p.count ? `<span class="count-label">${esc(p.count)}</span>` : ""}${toggle(box)}</div>
      <div class="box-body">${p.note ? `<p class="small-copy">${esc(p.note)}</p>` : ""}${draw(p)}</div></section>`;
  }).join("");
  // Sizes go through the CSSOM: the page's content security policy forbids inline style attributes.
  for (const bar of $("panels").querySelectorAll("[data-width]")) bar.style.width = bar.dataset.width + "%";
  for (const part of $("panels").querySelectorAll("[data-grow]")) part.style.flexGrow = part.dataset.grow;
}

function render() {
  if (!current) return;
  // A deployment page with no units of its own (its content is its panels) shows no empty pipeline or desk.
  const panelOnly = !current.units.length && (current.panels || []).length > 0;
  $("pipeline-section").hidden = panelOnly; $("work-grid").hidden = panelOnly;
  renderParams(); renderPipeline(); renderQueue(); renderDesk(); renderUsage(); renderBlocks(); renderPanels(); decorateBoxes();
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
  const target = event.target.closest("[data-unit],[data-unit-doc],[data-source],[data-filter],[data-open-pdf],[data-toggle-box]");
  if (!target || !current) return;
  if (target.dataset.toggleBox) {
    const box = target.dataset.toggleBox;
    collapsed.has(box) ? collapsed.delete(box) : collapsed.add(box);
    saveCollapsed(); renderPanels(); decorateBoxes();
    for (const el of document.querySelectorAll(`[data-toggle-box="${CSS.escape(box)}"]`)) {
      el.textContent = collapsed.has(box) ? "Show" : "Hide"; el.setAttribute("aria-expanded", String(!collapsed.has(box)));
    }
  } else if (target.dataset.openPdf) openPdf(target.dataset.openPdf);
  else if (target.dataset.filter) {
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
  if ($("detail-dialog").open) $("detail-dialog").close();      // its document belongs to the previous arm
  current = null;                                   // a different campaign: render it afresh
  filterKeys = null;
  await refresh();
}

$("arm-select").addEventListener("change", () => chooseArm($("arm-select").value));
loadArms().then(refresh);
setInterval(refresh, 20000);

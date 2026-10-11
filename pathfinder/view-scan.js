"use strict";
// The scan on the operator view (nobel, 11 October 2026): progress while it runs, then the ranked pairs, the
// score distribution with a previewed cut, and the campaign's topics. The ranking comes from /api/scan, fetched
// again only when the scan, the shortlist or the topics change; filters and the preview are computed here.
// Uses the helpers and `current` of view.js, loaded before this file.
let scanDoc = null, scanVersion = null, scanLoading = false, scanLimit = 40, scanLayout = "ranked", cutReady = false;
let previewCount = 0, previewThreshold = null;     // what the last preview chose, kept when the mode changes
const openRationales = new Set();
const PAGE_SIZE = 40, GROUP_SIZE = 3;

// ---- the ranking and what is derived from it --------------------------------------------------------------
let rows = [], scored = [], byId = new Map(), topicNames = [], families = [];
const paperOf = (side, n) => scanDoc?.papers?.[side]?.[String(n)] || {};
const famOf = (side, n) => paperOf(side, n).topics || [];
const paperKey = (side, n) => scanDoc.same_corpus ? "*:" + n : side + ":" + n;

function pairTopics(r) {
  const out = new Set();
  for (const a of famOf("Q", r.q)) for (const b of famOf("P", r.p))
    out.add(a === b ? `${a} (within)` : [a, b].sort().join(" × "));
  return [...out];
}

function derive() {
  const cols = scanDoc.columns;
  rows = scanDoc.rows.map((values) => Object.fromEntries(cols.map((c, i) => [c, values[i]])));
  scored = rows.filter((r) => r.score != null);
  scored.forEach((r, i) => { r.rank = i + 1; });
  for (const r of rows) r.topics = pairTopics(r);
  byId = new Map(rows.map((r) => [r.pair_id, r]));
  const counts = new Map();
  for (const r of scored) for (const t of r.topics) counts.set(t, (counts.get(t) || 0) + 1);
  topicNames = [...counts.keys()].sort();
  const fams = new Set();
  for (const side of ["Q", "P"]) for (const p of Object.values(scanDoc.papers[side] || {})) for (const f of p.topics || []) fams.add(f);
  families = [...fams].sort();
}

// ---- the previewed cut, with the same rules as `pathfinder select` -----------------------------------------
function capped(cap) {
  if (!cap) return scored;
  const seen = new Map(), out = [];
  for (const r of scored) {
    const keys = [paperKey("Q", r.q), paperKey("P", r.p)];
    if (keys.every((k) => (seen.get(k) || 0) < cap)) {
      out.push(r);
      for (const k of keys) seen.set(k, (seen.get(k) || 0) + 1);
    }
  }
  return out;
}

function cutFor(n, k) {           // a --cut percentage that selects exactly k of n pairs
  for (let d = 2; d <= 8; d++) {
    const c = Number((100 * k / n).toFixed(d));
    if (Math.ceil(n * c / 100) === k) return c;
  }
  return 100 * k / n;
}

function preview() {
  const mode = $("cut-mode").value, value = Number($("cut-value").value), cap = Math.max(0, Math.floor(Number($("cut-cap").value) || 0));
  const pool = capped(cap), n = scored.length;
  let chosen = [], args = "";
  if (mode === "score") {
    chosen = pool.filter((r) => r.score >= value); args = `--min-score ${value}`;
  } else {
    const k = mode === "percent" ? Math.ceil(n * value / 100) : Math.max(0, Math.round(value));
    chosen = pool.slice(0, k); args = `--cut ${mode === "percent" ? value : cutFor(n || 1, k)}`;
  }
  const set = new Set(chosen.map((r) => r.pair_id));
  const threshold = chosen.length ? chosen[chosen.length - 1].score : null;
  previewCount = chosen.length; previewThreshold = threshold;
  const held = cap ? new Set(scored.filter((r) => threshold != null && r.score >= threshold && !set.has(r.pair_id)).map((r) => r.pair_id)) : new Set();
  const incomplete = current.scan.done < current.scan.total && mode !== "score";
  return {set, chosen, threshold, held, cap,
          command: `pathfinder select ${args}${cap ? ` --per-paper ${cap}` : ""}${incomplete ? " --force" : ""}`};
}

function initCut() {
  if (cutReady || !scored.length) return;
  cutReady = true;
  const n = scored.length;
  if (scanDoc.min_score != null) { $("cut-mode").value = "score"; $("cut-value").value = scanDoc.min_score; }
  else {
    const pct = scanDoc.cut ?? current.scan.default_cut ?? 1;
    $("cut-mode").value = "top"; $("cut-value").value = Math.max(1, Math.ceil(n * pct / 100));
  }
  if (scanDoc.per_paper) $("cut-cap").value = scanDoc.per_paper;
}

// ---- progress -----------------------------------------------------------------------------------------------
function renderScanProgress() {
  const s = current.scan, b = current.campaign.budget || {}, lim = b.limits || {};
  const finished = s.total && s.done >= s.total;
  const share = s.total ? Math.min(100, 100 * s.done / s.total) : 0;
  const budget = (used, cap) => cap ? `${tokens(used)} <small>of ${tokens(cap)} for the campaign</small>` : tokens(used);
  $("scan-count").textContent = finished ? `${num(s.done)} pairs, complete` : `${num(s.done)} of ${num(s.total)} pairs`;
  $("scan-progress").innerHTML = `<div class="progress-line"><div class="progress-track"><i data-width="${share.toFixed(2)}"></i></div>
      <span>${finished ? "Scan complete" : share.toFixed(1) + "% scanned"}${s.last_call ? `, last call ${esc(when(s.last_call))}` : ""}</span></div>
    <dl class="usage-grid scan-stats">
      <div><dt>Pairs scored</dt><dd>${num(s.done - s.errors)} <small>of ${num(s.total)}</small></dd></div>
      <div><dt>${finished ? "Pace at the end" : "Pace"}</dt><dd>${s.rate_per_minute ? num(s.rate_per_minute) : "--"} <small>pairs a minute</small></dd></div>
      <div><dt>Time to finish</dt><dd>${finished ? "Done" : s.eta_seconds != null ? duration(s.eta_seconds) : "--"}${!finished && s.eta_seconds == null ? " <small>no runner working</small>" : ""}</dd></div>
      <div><dt>Failed calls</dt><dd>${num(s.errors)}</dd></div>
      <div><dt>Scan input tokens</dt><dd>${budget(s.input_tokens, lim.input_tokens)}</dd></div>
      <div><dt>Scan output tokens</dt><dd>${budget(s.output_tokens, lim.output_tokens)}</dd></div></dl>
    ${lim.input_tokens ? `<p class="small-copy">The campaign has used ${tokens(b.input_tokens)} input and ${tokens(b.output_tokens)} output tokens of its budget so far.</p>` : ""}`;
  for (const bar of $("scan-progress").querySelectorAll("[data-width]")) bar.style.width = bar.dataset.width + "%";
}

// ---- the score histogram ------------------------------------------------------------------------------------
function niceStep(raw) {
  for (const s of [10, 20, 25, 50, 100, 200, 250, 500, 1000]) if (raw <= s) return s;
  return 1000;
}

function renderHistogram(pv) {
  const svg = $("score-hist"), W = 640, H = 170, top = 14, bottom = 26, left = 6, right = 6;
  if (!scored.length) { svg.innerHTML = ""; $("hist-note").textContent = "No score yet."; return; }
  const max = Math.max(...scored.map((r) => r.score), 1), step = niceStep(max / 40), nb = Math.ceil((max + 1) / step);
  const bins = new Array(nb).fill(0);
  for (const r of scored) bins[Math.min(nb - 1, Math.floor(r.score / step))]++;
  const peak = Math.max(...bins), bw = (W - left - right) / nb, x = (score) => left + (score / (nb * step)) * (W - left - right);
  const y = (count) => H - bottom - (count / peak) * (H - top - bottom);
  let out = bins.map((c, i) => {
    const inCut = pv.threshold != null && i * step >= pv.threshold;
    const partial = pv.threshold != null && !inCut && (i + 1) * step > pv.threshold;
    return c ? `<rect class="bin${inCut ? " in" : partial ? " edge" : ""}" x="${(left + i * bw + 0.5).toFixed(1)}" y="${y(c).toFixed(1)}"
      width="${Math.max(1, bw - 1).toFixed(1)}" height="${(H - bottom - y(c)).toFixed(1)}"><title>${num(i * step)} to ${num((i + 1) * step - 1)}: ${c} pairs</title></rect>` : "";
  }).join("");
  out += `<line class="axis" x1="${left}" x2="${W - right}" y1="${H - bottom}" y2="${H - bottom}"/>`;
  for (const t of [0, nb * step / 2, nb * step]) out += `<text x="${x(t)}" y="${H - 8}" text-anchor="${t ? (t === nb * step ? "end" : "middle") : "start"}">${num(t)}</text>`;
  out += `<text x="${left}" y="10">${peak} pairs</text>`;
  if (pv.threshold != null) {
    const cx = x(pv.threshold);
    out += `<line class="cut-line" x1="${cx}" x2="${cx}" y1="${top - 4}" y2="${H - bottom}"/>
      <text class="cut-label" x="${cx - 4}" y="${top + 6}" text-anchor="end">cut: ${num(pv.chosen.length)} pairs</text>`;
  }
  const sel = (scanDoc.selected || []).map((id) => byId.get(id)?.score).filter((v) => v != null);
  if (sel.length) {
    const sx = x(Math.min(...sel));
    out += `<line class="shortlist-line" x1="${sx}" x2="${sx}" y1="${top + 14}" y2="${H - bottom}"/>
      <text class="shortlist-label" x="${sx + 4}" y="${top + 24}">shortlist</text>`;
  }
  svg.innerHTML = out;
  $("hist-note").textContent = `${num(scored.length)} scored pairs, median ${num(scored[Math.floor(scored.length / 2)].score)}, best ${num(max)}`;
}

function renderCutSummary(pv) {
  const n = scored.length, k = pv.chosen.length;
  const papers = new Set(pv.chosen.flatMap((r) => [paperKey("Q", r.q), paperKey("P", r.p)]));
  $("cut-result").innerHTML = k ? `<b>${num(k)}</b> of ${num(n)} pairs (${(100 * k / (n || 1)).toFixed(2)}%), scores ${num(pv.threshold)} and up,
      involving ${papers.size} papers.${pv.held.size ? ` The cap holds back ${pv.held.size} pairs that score as high.` : ""}`
    : "No pair in this cut.";
  $("cut-command").textContent = pv.command;
}

// ---- topics -------------------------------------------------------------------------------------------------
function renderTopics(pv) {
  const has = topicNames.length > 0;
  $("topics-block").hidden = !has; $("scan-topic-label").hidden = !has; $("layout-grouped").hidden = !has;
  if (!has) { if (scanLayout === "grouped") scanLayout = "ranked"; return; }
  const all = new Map(), cut = new Map();
  for (const r of scored) for (const t of r.topics) {
    all.set(t, (all.get(t) || 0) + 1);
    if (pv.set.has(r.pair_id)) cut.set(t, (cut.get(t) || 0) + 1);
  }
  const k = pv.chosen.length || 1, n = scored.length || 1;
  const order = [...all.keys()].sort((a, b) => (cut.get(b) || 0) - (cut.get(a) || 0) || all.get(b) - all.get(a) || a.localeCompare(b));
  const peak = Math.max(...order.map((t) => Math.max((cut.get(t) || 0) / k, all.get(t) / n)), 0.01);
  const chosen = $("scan-topic").value;
  $("topic-bars").innerHTML = `<div class="topic-legend"><span><i class="swatch cut"></i>share of the previewed cut</span>
      <span><i class="swatch all"></i>share of all pairs</span></div>` + order.map((t) => {
    const c = cut.get(t) || 0, a = all.get(t);
    return `<button type="button" class="topic-row${chosen === "t:" + t ? " selected" : ""}" data-topic="t:${esc(t)}" aria-pressed="${chosen === "t:" + t}">
      <span class="topic-name">${esc(t)}</span>
      <span class="topic-bars-pair"><i class="bar cut" data-width="${(100 * (c / k) / peak).toFixed(2)}"></i><i class="bar all" data-width="${(100 * (a / n) / peak).toFixed(2)}"></i></span>
      <span class="topic-count"><b>${c}</b> of ${num(pv.chosen.length)} <small>${num(a)} of ${num(scored.length)} overall</small></span></button>`;
  }).join("");
  for (const bar of $("topic-bars").querySelectorAll("[data-width]")) bar.style.width = bar.dataset.width + "%";
  $("topics-note").textContent = "A pair whose papers belong to several families counts under each crossing. Click a topic to list its pairs.";
}

function fillSelects() {
  const papers = [];
  for (const side of scanDoc.same_corpus ? ["Q"] : ["Q", "P"])
    for (const [n, p] of Object.entries(scanDoc.papers[side] || {}))
      papers.push({key: paperKey(side, n), side, n: Number(n), title: p.title || p.id || ""});
  papers.sort((a, b) => a.side.localeCompare(b.side) || a.n - b.n);
  const keep = $("scan-paper").value;
  $("scan-paper").innerHTML = `<option value="">Every paper</option>` + papers.map((p) =>
    `<option value="${esc(p.key)}">${scanDoc.same_corpus ? "" : p.side + " "}${p.n}: ${esc(p.title.length > 70 ? p.title.slice(0, 67) + "..." : p.title)}</option>`).join("");
  $("scan-paper").value = keep;
  const keepTopic = $("scan-topic").value;
  $("scan-topic").innerHTML = `<option value="">Every topic</option>`
    + (families.length ? `<optgroup label="Families (every crossing involving one)">${families.map((f) => `<option value="f:${esc(f)}">${esc(f)}</option>`).join("")}</optgroup>` : "")
    + (topicNames.length ? `<optgroup label="Topics">${topicNames.map((t) => `<option value="t:${esc(t)}">${esc(t)}</option>`).join("")}</optgroup>` : "");
  $("scan-topic").value = keepTopic;
}

// ---- the list -----------------------------------------------------------------------------------------------
function matches(r, pv, {ignoreTopic = false} = {}) {
  const show = $("scan-show").value, query = $("scan-search").value.toLowerCase().trim();
  const paper = $("scan-paper").value, topic = ignoreTopic ? "" : $("scan-topic").value, gain = Number($("scan-gain").value) || 0;
  if (show === "errors") { if (!r.error) return false; }
  else if (r.score == null) return false;
  if (show === "cut" && !pv.set.has(r.pair_id)) return false;
  if (show === "selected" && !(scanDoc.selected || []).includes(r.pair_id)) return false;
  if (gain && !((r.gain ?? -1) >= gain)) return false;
  if (paper && paperKey("Q", r.q) !== paper && paperKey("P", r.p) !== paper) return false;
  if (topic.startsWith("t:") && !r.topics.includes(topic.slice(2))) return false;
  if (topic.startsWith("f:")) {
    const f = topic.slice(2);
    if (!famOf("Q", r.q).includes(f) && !famOf("P", r.p).includes(f)) return false;
  }
  if (query) {
    const q = paperOf("Q", r.q), p = paperOf("P", r.p);
    const hay = [r.pair_id, r.connexion, q.title, q.id, p.title, p.id].join(" ").toLowerCase();
    if (!query.split(/\s+/).every((w) => hay.includes(w))) return false;
  }
  return true;
}

function paperLink(side, n) {
  const p = paperOf(side, n), title = esc(p.title || p.id || side + n);
  const link = isArxiv(p.id) ? `<a href="${arxivURL(p.id)}" target="_blank" rel="noopener noreferrer" title="arXiv ${esc(p.id)}">${title}</a>` : title;
  return `<span class="scan-paper">${link} <button type="button" class="paper-chip" data-paper="${esc(paperKey(side, n))}"
    title="Every pair with this paper">${scanDoc.same_corpus ? "" : side}${n}</button></span>`;
}

// A conditional scan (scan-context.json): each score names the state of play it was judged against.
function stateMark(r) {
  const ctx = scanDoc.context;
  if (!ctx) return r.revision ? `<span class="mark revision">revision ${esc(r.revision)}</span>` : "";
  if (r.unconditioned) return `<span class="mark stale" title="scored before the campaign had a state of play">unconditioned</span>`;
  if (r.stale) return `<span class="mark stale" title="the state of play is now at revision ${esc(ctx.revision)}">stale: revision ${esc(r.revision)}</span>`;
  return `<span class="mark revision">revision ${esc(r.revision)}</span>`;
}

function historyHTML(r) {
  const h = (scanDoc.history || {})[r.pair_id];
  if (!h) return "";
  const items = h.map((e) => `<li><span class="history-rev">${e.revision ? "revision " + esc(e.revision) : "unconditioned"}</span>
    ${e.error ? `<span class="scan-error">${esc(e.error)}</span>` : `<span class="score-sub">${e.feasibility} × ${e.gain}</span> ${esc(e.connexion || "")}`}</li>`).join("");
  return `<details class="history"><summary>Score history (${h.length})</summary><ol>${items}</ol></details>`;
}

function rowHTML(r, pv, sub) {
  const selected = (scanDoc.selected || []).includes(r.pair_id), unit = current.units.find((u) => u.unit === r.pair_id);
  const marks = [selected ? `<span class="mark selected">in the shortlist</span>` : "",
    pv.set.has(r.pair_id) ? `<span class="mark cut">in the previewed cut</span>` : "",
    pv.held.has(r.pair_id) ? `<span class="mark held">held back by the cap</span>` : "",
    stateMark(r)].join("");
  const topics = r.topics.map((t) => `<button type="button" class="topic-chip" data-topic="t:${esc(t)}">${esc(t)}</button>`).join("");
  const open = openRationales.has(r.pair_id) ? " open" : "";
  return `<article class="scan-row${pv.set.has(r.pair_id) ? " in-cut" : ""}${selected ? " selected" : ""}">
    <div class="scan-rank">${r.rank != null ? `<span class="rank-num">${r.rank}</span>${sub ? `<span class="rank-sub">${esc(sub)}</span>` : ""}` : `<span class="rank-sub">failed</span>`}</div>
    <div class="scan-main">
      <h3 class="scan-titles">${paperLink("Q", r.q)}<span class="times" aria-label="with">×</span>${paperLink("P", r.p)}</h3>
      ${r.error ? `<p class="scan-error">${esc(r.error)}</p>` : `<p class="connexion">${esc(r.connexion || "")}</p>`}
      <div class="scan-meta"><span class="pair-id">${esc(r.pair_id)}</span>${marks}${topics}
        ${unit ? `<button type="button" class="link-button" data-unit="${esc(r.pair_id)}">Research record</button>` : ""}</div>
      ${historyHTML(r)}
      ${r.rationale ? `<details class="rationale" data-pair="${esc(r.pair_id)}"${open}><summary>Why these scores</summary><p>${esc(r.rationale)}</p></details>` : ""}
    </div>
    ${r.score != null ? `<div class="scan-score"><span class="score-num">${num(r.score)}</span>
      <span class="score-sub" title="feasibility × gain">${r.feasibility} × ${r.gain}</span></div>` : ""}
  </article>`;
}

function renderList(pv) {
  const topic = $("scan-topic").value;
  if (scanLayout === "grouped" && topicNames.length) return renderGrouped(pv);
  const list = (topic || $("scan-show").value === "errors" ? rows : scored).filter((r) => matches(r, pv));
  const within = topic ? (topic.startsWith("t:") ? "in this topic" : "in this family") : "";
  $("scan-list").innerHTML = list.length ? list.slice(0, scanLimit).map((r, i) =>
    rowHTML(r, pv, within && r.rank != null ? `${i + 1} ${within}` : "")).join("") : `<p class="empty">No pair matches these filters.</p>`;
  $("scan-list-note").textContent = list.length ? `${num(list.length)} pairs match${list.length > scanLimit ? `; showing the first ${scanLimit}` : ""}. Numbers on the left are ranks among all scored pairs.` : "";
  $("scan-more").hidden = list.length <= scanLimit;
}

function renderGrouped(pv) {
  const groups = new Map();
  for (const r of scored) if (matches(r, pv, {ignoreTopic: true}))
    for (const t of r.topics) { if (!groups.has(t)) groups.set(t, []); groups.get(t).push(r); }
  const topic = $("scan-topic").value;
  const keys = [...groups.keys()].filter((t) => !topic || (topic.startsWith("t:") ? t === topic.slice(2) : t.split(/ × | \(within\)/).includes(topic.slice(2))))
    .sort((a, b) => groups.get(a)[0].rank - groups.get(b)[0].rank);
  $("scan-list").innerHTML = keys.length ? `<div class="topic-groups">${keys.map((t) => {
    const g = groups.get(t), inCut = g.filter((r) => pv.set.has(r.pair_id)).length;
    return `<section class="topic-group"><div class="group-head"><h3>${esc(t)}</h3>
        <span class="count-label">${num(g.length)} pairs, ${inCut} in the cut</span></div>
      ${g.slice(0, GROUP_SIZE).map((r, i) => rowHTML(r, pv, `${i + 1} in topic`)).join("")}
      ${g.length > GROUP_SIZE ? `<button type="button" class="quiet-button" data-topic-list="t:${esc(t)}">All ${num(g.length)} pairs in this topic</button>` : ""}</section>`;
  }).join("")}</div>` : `<p class="empty">No pair matches these filters.</p>`;
  $("scan-list-note").textContent = `${keys.length} topics, best ${GROUP_SIZE} pairs each, ordered by their best pair. Numbers on the left are ranks among all scored pairs.`;
  $("scan-more").hidden = true;
}

function renderScanBody() {
  if (!scanDoc) return;
  initCut();
  const pv = preview();
  renderHistogram(pv); renderCutSummary(pv); renderTopics(pv); renderList(pv);
  $("layout-ranked").setAttribute("aria-pressed", String(scanLayout === "ranked"));
  $("layout-grouped").setAttribute("aria-pressed", String(scanLayout === "grouped"));
}

async function loadScan() {
  if (scanLoading) return;
  scanLoading = true;
  try {
    const response = await fetch("/api/scan" + armQuery("?"), {cache: "no-store"});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Scan unavailable");
    scanDoc = data; scanVersion = data.version;
    derive(); fillSelects(); renderScanBody();
  } catch (error) {
    $("scan-list").innerHTML = `<p class="empty">The scan could not be read: ${esc(error.message)}</p>`;
  } finally {
    scanLoading = false;
  }
}

// Called by view.js on every refresh: progress always, the ranking only when it changed.
window.renderScan = function () {
  const s = current?.scan;
  $("scan-section").hidden = !s || !(s.total || s.done);
  if ($("scan-section").hidden) return;
  renderScanProgress();
  if (s.version !== scanVersion) loadScan();
};
window.resetScan = function () { scanDoc = null; scanVersion = null; cutReady = false; openRationales.clear(); };

// ---- controls -----------------------------------------------------------------------------------------------
const rerender = () => { scanLimit = PAGE_SIZE; renderScanBody(); };
for (const id of ["scan-search", "scan-gain", "cut-value", "cut-cap"]) $(id).addEventListener("input", rerender);
for (const id of ["scan-paper", "scan-topic", "scan-show"]) $(id).addEventListener("change", rerender);
$("cut-form").addEventListener("submit", (event) => event.preventDefault());
$("cut-mode").addEventListener("change", () => {
  // the same cut, expressed the new way
  const n = scored.length, mode = $("cut-mode").value;
  if (mode === "top") $("cut-value").value = previewCount;
  else if (mode === "percent") $("cut-value").value = n ? cutFor(n, previewCount) : 1;
  else $("cut-value").value = previewThreshold ?? 0;
  rerender();
});
$("copy-command").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("cut-command").textContent); $("copy-command").textContent = "Copied"; }
  catch { $("copy-command").textContent = "Select and copy"; }
  setTimeout(() => { $("copy-command").textContent = "Copy"; }, 1600);
});
$("scan-more").addEventListener("click", () => { scanLimit += PAGE_SIZE; renderList(preview()); });
$("layout-ranked").addEventListener("click", () => { scanLayout = "ranked"; rerender(); });
$("layout-grouped").addEventListener("click", () => { scanLayout = "grouped"; rerender(); });
$("scan-list").addEventListener("toggle", (event) => {
  const d = event.target;
  if (d.matches?.("details.rationale")) d.open ? openRationales.add(d.dataset.pair) : openRationales.delete(d.dataset.pair);
}, true);
$("scan-section").addEventListener("click", (event) => {
  const t = event.target.closest("[data-paper],[data-topic],[data-topic-list]");
  if (!t) return;
  if (t.dataset.paper) $("scan-paper").value = $("scan-paper").value === t.dataset.paper ? "" : t.dataset.paper;
  else {
    const value = t.dataset.topic || t.dataset.topicList;
    $("scan-topic").value = $("scan-topic").value === value && !t.dataset.topicList ? "" : value;
    if (t.dataset.topicList) scanLayout = "ranked";
  }
  rerender();
  $("scan-list-note").scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start"});
});

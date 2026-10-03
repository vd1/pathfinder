// Loads pathfinder/view.js in a fake DOM and prints one JSON object of scenario results (see tests/test_view.py).
const fs = require("fs"), vm = require("vm"), path = require("path");
const source = fs.readFileSync(path.join(__dirname, "../../pathfinder/view.js"), "utf8");

// The page fetches its first snapshot as soon as it loads: give the world its first response and hash up front.
async function world(first, hash = "", arms = [{ arm: "", name: "camp" }], boxes = []) {
  const writes = {}, elements = {}, handlers = {}, docHandlers = {};
  function element(id) {
    let html = "";
    const el = {
      id, textContent: "", className: "", value: "all", hidden: true, open: false, disabled: false, dataset: {},
      style: {}, classList: { add() {}, remove() {}, toggle() {} },
      get innerHTML() { return html; },
      set innerHTML(v) { html = v; writes[id] = (writes[id] || 0) + 1; },
      querySelectorAll() { return []; }, scrollIntoView() {},
      addEventListener(type, fn) { (handlers[id + ":" + type] = handlers[id + ":" + type] || []).push(fn); },
      showModal() { el.open = true; }, close() { el.open = false; (handlers[id + ":close"] || []).forEach((f) => f()); },
    };
    return el;
  }
  const location = { hash, pathname: "/" };
  const responses = [first];
  const requested = [];
  const context = {
    console, URLSearchParams, setInterval() {}, matchMedia: () => ({ matches: true }),
    document: {
      getElementById: (id) => (elements[id] = elements[id] || element(id)),
      querySelectorAll: (selector) => selector.startsWith("section") ? boxes : [],
      addEventListener(type, fn) { (docHandlers[type] = docHandlers[type] || []).push(fn); },
    },
    window: { addEventListener(type, fn) { (docHandlers["window:" + type] = docHandlers["window:" + type] || []).push(fn); } },
    history: { replaceState(_s, _t, url) { location.hash = url.includes("#") ? url.slice(url.indexOf("#")) : ""; } },
    location,
    fetch: async (url) => {
      requested.push(url);
      if (url.startsWith("/open")) return { ok: true, text: async () => "" };
      if (url.startsWith("/doc")) return { ok: true, text: async () => "source text" };
      if (url.startsWith("/api/arms")) return { ok: true, json: async () => arms };
      const next = responses.shift();
      if (next instanceof Error) throw next;
      return { ok: true, json: async () => next };
    },
  };
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(source + "\n;globalThis.__api = { render, refresh, openFromHash, showUnit, chooseArm, openPdf };", context);
  await new Promise((resolve) => setTimeout(resolve, 0));        // let the load-time refresh finish
  return { api: context.__api, writes, location, responses, requested, el: context.document.getElementById };
}

const unit = (u, activity, summary) => ({
  unit: u, lifecycle: "accepted", controller: "done", score: 42, feasibility: 7, gain: 6, connexion: "a bridge",
  summary: summary || "fine", last_activity: activity,
  q: { id: "2601.0001", title: "Q title", abstract: "q abs" }, p: { id: "2601.0002", title: "P title", abstract: "p abs" },
  research: { status: "DRAFT" }, editorial: { status: "done" }, assessment: { status: "ACCEPTED" },
  usage: { calls: 3, input_tokens: 10, output_tokens: 2, seconds: 5 },
  documents: [{ kind: "research note", pdf: null, source: `threads/${u}/${u}.tex`, stale: false },
              { kind: "paper", pdf: `threads/${u}/paper/paper.pdf`, source: `threads/${u}/paper/paper.tex`, stale: false }],
});
const state = (activity, summary) => ({
  generated_at: "2026-10-01T10:00:00Z",
  campaign: { name: "camp", backend: "codex", model: "m", research_scheme: "eva", seats: 1, rounds: 1,
    allowances: { peer_seconds: 900 }, execution_id: "abcdef123456", stop: null, budget: {} },
  progress: { status: "idle", events_truncated: false }, runner: { status: "finished", pid_alive: false },
  pipeline: [{ title: "Selected", count: 0, states: [{ key: "waiting", label: "Waiting", count: 0 }] },
             { title: "Paper", count: 2, states: [{ key: "accepted", label: "Accepted", count: 2 }] }],
  usage: { calls: 6, completed: 6, calls_with_usage: 6, input_tokens: 20, cache_read: 5, output_tokens: 4, seconds: 10 },
  blocks: [], units: [unit("Q1P1", "t1", summary), unit("Q1P2", activity)],
});

(async () => {
  const out = {};
  let w = await world(state("a"), "#note=Q1P1&doc=paper");
  out.hash_opens_document = w.el("detail-dialog").open
    && w.el("detail-content").innerHTML.includes("/doc?path=threads%2FQ1P1%2Fpaper%2Fpaper.pdf");
  const before = w.writes["detail-content"];
  w.responses.push(state("b"));
  await w.api.refresh();
  out.dialog_survives_refresh = w.writes["detail-content"] === before;
  w.el("detail-dialog").close();
  out.close_clears_hash = !w.location.hash.includes("note=");
  const queue = w.el("queue-body").innerHTML;
  w.responses.push(new Error("offline"));
  await w.api.refresh();
  out.failed_refresh_keeps_snapshot = w.el("queue-body").innerHTML === queue && w.el("error-banner").hidden === false;
  out.pipeline_counts_from_server = w.el("pipeline").innerHTML.includes("Paper") && w.el("pipeline").innerHTML.includes("Accepted");
  const selectWrites = w.writes["status-filter"];
  w.responses.push(state("c"));
  await w.api.refresh();
  out.filter_select_not_rebuilt_on_refresh = w.writes["status-filter"] === selectWrites;
  const local = state("a"); local.units[0].p.id = "pathfinder-recursive-R1-v2"; local.units[0].gain = null;
  w = await world(local);
  w.api.showUnit("Q1P1");
  out.no_arxiv_link_for_local_ids = !w.el("detail-content").innerHTML.includes("arxiv.org/abs/pathfinder");
  out.no_null_scores = !w.el("queue-body").innerHTML.includes("null");
  const big = state("a"); big.usage.input_tokens = 21621252; big.usage.cache_read = 20201984; big.usage.output_tokens = 182469;
  w = await world(big);
  const shown = w.el("usage").innerHTML.replace(/<[^>]*>/g, "");          // visible text; exact counts stay in titles
  out.usage_in_human_units = shown.includes("21.6 M") && shown.includes("182 k") && !shown.includes("21,621,252")
    && w.el("usage").innerHTML.includes('title="21,621,252"');
  w = await world(state("a"), "", [{ arm: "repeat", name: "repeat" }, { arm: "recursive", name: "recursive" }]);
  out.arms_select_shown = w.el("arm-select").innerHTML.includes("recursive")
    && w.requested.some((u) => u === "/api/state?arm=repeat");
  w.el("arm-select").value = "recursive";
  w.responses.push(state("a"));
  await w.api.chooseArm("recursive");
  out.arm_switch_requests_that_arm = w.requested.at(-1) === "/api/state?arm=recursive";
  w = await world(state("a", "<img src=x onerror=1>"));
  const html = w.el("research-list").innerHTML;
  out.escaped = html.includes("&lt;img") && !html.includes("<img");
  const deployment = state("a"); deployment.units = []; deployment.campaign.title = "statarb arXiv drip";
  deployment.campaign.description = "Intake, research and paper trading.";
  deployment.panels = [{ title: "Paper trading", columns: ["paper", "events"], rows: [[{ text: "2601.06499v3", href: "https://arxiv.org/abs/2601.06499v3" }, 12]] }];
  w = await world(deployment);
  out.panel_view = w.el("pipeline-section").hidden === true && w.el("work-grid").hidden === true
    && w.el("panels").innerHTML.includes("Paper trading") && w.el("page-title").textContent === "statarb arXiv drip"
    && w.el("lede").textContent === "Intake, research and paper trading.";
  deployment.panels[0].rows.push([{ text: "note", pdf: "/abs/notes/strategy.pdf" }, 3]);
  w = await world(deployment);
  out.panel_pdf_opens_in_viewer = w.el("panels").innerHTML.includes('data-open-pdf="/abs/notes/strategy.pdf"');
  await w.api.openPdf("/abs/notes/strategy.pdf");
  out.panel_pdf_opens_in_viewer = out.panel_pdf_opens_in_viewer && w.requested.at(-1) === "/open";
  const kinds = state("a"); kinds.units = [];
  kinds.panels = [
    { kind: "pipeline", title: "Pipeline", stages: [{ title: "Intake", states: [{ key: "new", label: "Unscored", count: 3 }] }] },
    { kind: "metrics", title: "Operations", items: [{ label: "Model", value: "m", small: "medium effort" }] },
    { kind: "cards", title: "Paper trading", grid: true, cards: [{ status: "active", badge: "Active", meta: ["2601.06499v3"],
      title: "Basis", summary: "12 events", actions: [{ text: "Read note", pdf: "/x.pdf" }, { text: "arXiv", href: "https://arxiv.org/abs/1" }] }] }];
  w = await world(kinds);
  const p = w.el("panels").innerHTML;
  out.panel_kinds_use_page_designs = p.includes('class="stage"') && p.includes("usage-grid") && p.includes("strategy-grid")
    && p.includes('class="strategy-card status-active"') && p.includes('data-open-pdf="/x.pdf"') && p.includes("Unscored");
  out.boxes_collapsible = p.includes("data-toggle-box");
  const fakeBox = (hasToggle) => { const b = { dataset: {}, inserted: 0, classList: { toggle() {} },
    querySelector: (sel) => sel === ".box-toggle" ? (hasToggle || b.inserted ? {} : null) : { textContent: "Units" },
    getAttribute: () => null, insertAdjacentHTML() { b.inserted += 1; } }; return b; };
  const drawn = fakeBox(true), plain = fakeBox(false);
  w = await world(state("a"), "", undefined, [drawn, plain]);
  w.api.render();
  out.one_toggle_per_box = drawn.inserted === 0 && plain.inserted === 1;
  w = await world(state("a"));
  out.unit_pdf_has_open_button = w.el("research-list").innerHTML.includes('data-open-pdf="threads/Q1P1/paper/paper.pdf"');
  out.unit_view_keeps_sections = w.el("pipeline-section").hidden === false && w.el("work-grid").hidden === false;
  console.log(JSON.stringify(out));
})();

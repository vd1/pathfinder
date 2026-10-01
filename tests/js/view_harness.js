// Loads pathfinder/view.js in a fake DOM and prints one JSON object of scenario results (see tests/test_view.py).
const fs = require("fs"), vm = require("vm"), path = require("path");
const source = fs.readFileSync(path.join(__dirname, "../../pathfinder/view.js"), "utf8");

// The page fetches its first snapshot as soon as it loads: give the world its first response and hash up front.
async function world(first, hash = "") {
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
  const context = {
    console, URLSearchParams, setInterval() {}, matchMedia: () => ({ matches: true }),
    document: {
      getElementById: (id) => (elements[id] = elements[id] || element(id)),
      addEventListener(type, fn) { (docHandlers[type] = docHandlers[type] || []).push(fn); },
    },
    window: { addEventListener(type, fn) { (docHandlers["window:" + type] = docHandlers["window:" + type] || []).push(fn); } },
    history: { replaceState(_s, _t, url) { location.hash = url.includes("#") ? url.slice(url.indexOf("#")) : ""; } },
    location,
    fetch: async (url) => {
      if (url.startsWith("/doc")) return { ok: true, text: async () => "source text" };
      const next = responses.shift();
      if (next instanceof Error) throw next;
      return { ok: true, json: async () => next };
    },
  };
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(source + "\n;globalThis.__api = { render, refresh, openFromHash };", context);
  await new Promise((resolve) => setTimeout(resolve, 0));        // let the load-time refresh finish
  return { api: context.__api, writes, location, responses, el: context.document.getElementById };
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
  w = await world(state("a", "<img src=x onerror=1>"));
  const html = w.el("research-list").innerHTML;
  out.escaped = html.includes("&lt;img") && !html.includes("<img");
  console.log(JSON.stringify(out));
})();

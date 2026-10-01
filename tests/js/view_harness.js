// Loads pathfinder/view.js with a minimal fake DOM and prints JSON results of the checks named in argv.
const fs = require("fs"), vm = require("vm"), path = require("path");
const source = fs.readFileSync(path.join(__dirname, "../../pathfinder/view.js"), "utf8");
const writes = {};
function element(id) {
  let html = "";
  return { id, textContent: "", className: "", dataset: {},
    get innerHTML() { return html; }, set innerHTML(v) { html = v; writes[id] = (writes[id] || 0) + 1; },
    querySelectorAll() { return []; }, addEventListener() {} };
}
const elements = {};
const location = { hash: "" };
const context = {
  document: { getElementById: (id) => (elements[id] = elements[id] || element(id)) },
  window: { addEventListener() {} }, location, URLSearchParams, setInterval() {}, console,
  fetch: async () => ({ ok: true, json: async () => ({}), text: async () => "" }),
};
vm.createContext(context);
vm.runInContext(source + "\n;globalThis.__api = { render, renderReader, renderUnits, setState: (s) => { state = s; } };", context);
const api = context.__api;
const unit = (u, activity) => ({ unit: u, score: 0.64, controller: "running", research: { status: "DRAFT" }, editorial: { status: "done" },
  assessment: { status: null }, last_activity: activity, documents: [{ kind: "paper", pdf: "threads/" + u + "/paper/paper.pdf", source: "threads/" + u + "/paper/paper.tex", stale: false }] });
const doc = (activity) => ({ generated_at: "t", campaign: { name: "c", backend: "b", model: "m", research_scheme: "eva", seats: 1, rounds: 1,
  allowances: { peer_seconds: 600 }, budget: { calls: 1, input_tokens: 1, output_tokens: 1, cache_read: 0 }, execution_id: "e", stop: null },
  progress: { status: "active", events_truncated: false }, runner: {}, stages: { research: { DRAFT: 2 } }, blocks: [],
  units: [unit("Q1P1", "t1"), unit("Q1P2", activity)] });
const out = {};
location.hash = "#stage=research&state=DRAFT&note=Q1P1&doc=paper";
api.setState(doc("a")); api.render();
const before = writes.reader;
api.setState(doc("b")); api.render();
out.reader_rebuilt_on_unrelated_change = writes.reader !== before;
out.unit_link_keeps_filter = /href="#[^"]*stage=research[^"]*note=Q1P2/.test(elements.units.innerHTML) || /href="#[^"]*note=Q1P2[^"]*stage=research/.test(elements.units.innerHTML);
out.allowances_shown = /peer_seconds/.test(elements.params.innerHTML);
out.score_rounded = !/0\.6400000000000001/.test(elements.units.innerHTML);
console.log(JSON.stringify(out));

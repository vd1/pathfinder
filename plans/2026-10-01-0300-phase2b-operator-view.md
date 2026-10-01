# Phase 2b: Operator web page and server hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pathfinder view` serves one local page, rendered from the phase 2a state document, that shows the campaign's parameters, a pipeline of per-stage counts split by state (each state a filter), blocks by failure class, the unit list with scores and states, and each unit's documents as PDFs in an in-page reader with the LaTeX source one click away, a stale warning and a stable `#note=<unit>` link; the old monitor server gains the same request checks.

**Architecture:** `pathfinder/webguard.py` holds the request checks (Host and Origin must be this local server), the response headers (strict CSP for pages, `frame-ancestors 'self'` for inline PDFs, `nosniff`, no referrer) and the document resolver (only files under `threads/`, known suffixes, at most 8 MiB). `pathfinder/view.py` is a `ThreadingHTTPServer` with four routes: the page, its script and style, `/api/state` (`campaign_state.build`) and `/doc?path=`. The page is static HTML plus `view.js` and `view.css` (no inline script, so the CSP holds). `monitor.serve` keeps its page but stops serving arbitrary files and checks Host and Origin.

**Tech Stack:** Python 3.13 standard library HTTP server, plain JavaScript (no build), pytest with a real server on an ephemeral port, `node --check` for script syntax.

**Spec:** `notes/pathfinder-friction.tex`: H10, S4, the operator view decision (parameters, per-stage counts, blocks, units with scores, PDF links) and "the operator view reads documents, not sources" (in-page PDF reader, source one click away, stale warning, `#note=<unit>`, pipeline counts as filters, PDFs inline and framable only by the view's origin). Phase 2a document: `pathfinder/campaign_state.py`.

## Global Constraints

- Tests: `uv run --offline --locked pytest -q <files>`; full suite more than two minutes; never edit engine files while it runs.
- Baseline (commit ef20a38): 284 passed, 1 failed (`tests/test_deployments.py::test_statarb_prepares_freezes_and_runs_the_candidate_engine`, pre-existing).
- The server binds to 127.0.0.1 only. No external scripts, fonts or styles on the view page (the CSP is `default-src 'self'`).
- Read-only: the view never writes campaign files.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- A request with a foreign Host header (DNS rebinding) or a foreign Origin gets 403 (Task 1 and Task 2 tests).
- `/doc?path=../../etc/passwd`, a symlink out of `threads/`, an unknown suffix and a file over 8 MiB are refused (Task 1 tests).
- A PDF is served inline and framable by the view's origin only; every other response forbids framing (Task 2 test).
- A unit with no PDF falls back to its source text; a stale PDF shows the warning (Task 3 rendering logic, Task 3 test on the state fields used).
- The old monitor no longer serves `campaign.json`'s siblings outside its routes, such as an `.env` file at the root (Task 4 test).

---

### Task 1: Request checks, headers and document resolver

**Files:**
- Create: `pathfinder/webguard.py`
- Test: `tests/test_webguard.py`

**Interfaces:**
- Produces: `webguard.refusal(headers, port: int) -> str | None`; `webguard.headers(kind: str, filename: str | None = None) -> dict` with kinds `"page"`, `"pdf"`, `"text"`; `webguard.resolve(root: Path, relative: str) -> Path` raising `webguard.Refused(code: int, message: str)`; constants `MAX_BYTES = 8 * 1024 * 1024`, `SUFFIXES`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_webguard.py
import os
import pytest
from pathfinder import webguard


def test_local_host_and_origin_only():
    ok = {"Host": "127.0.0.1:8791"}
    assert webguard.refusal(ok, 8791) is None
    assert webguard.refusal({"Host": "localhost:8791", "Origin": "http://localhost:8791"}, 8791) is None
    assert webguard.refusal({"Host": "evil.example:8791"}, 8791)
    assert webguard.refusal({"Host": "127.0.0.1:8791", "Origin": "http://evil.example"}, 8791)
    assert webguard.refusal({}, 8791)


def test_headers_frame_pdfs_only_from_self():
    page, pdf = webguard.headers("page"), webguard.headers("pdf", "note.pdf")
    assert "frame-ancestors 'none'" in page["Content-Security-Policy"] and page["X-Frame-Options"] == "DENY"
    assert pdf["Content-Security-Policy"] == "frame-ancestors 'self'" and pdf["X-Frame-Options"] == "SAMEORIGIN"
    assert pdf["Content-Disposition"] == 'inline; filename="note.pdf"'
    for h in (page, pdf, webguard.headers("text")):
        assert h["X-Content-Type-Options"] == "nosniff" and h["Cache-Control"] == "no-store"


def test_resolver_allows_thread_documents_only(tmp_path):
    d = tmp_path / "threads" / "Q1P1" / "edited"; d.mkdir(parents=True)
    (d / "note.pdf").write_bytes(b"%PDF"); (d / "note.tex").write_text("x"); (d / "run.sh").write_text("x")
    (tmp_path / ".env").write_text("SECRET=1")
    assert webguard.resolve(tmp_path, "threads/Q1P1/edited/note.pdf") == d / "note.pdf"
    for bad, code in [("../outside.pdf", 404), (".env", 404), ("threads/Q1P1/edited/run.sh", 404),
                      ("threads/../.env", 404), ("threads/Q1P1/edited/missing.pdf", 404)]:
        with pytest.raises(webguard.Refused) as refused:
            webguard.resolve(tmp_path, bad)
        assert refused.value.code == code


def test_resolver_refuses_symlinks_out_and_oversize(tmp_path):
    d = tmp_path / "threads" / "Q1P1"; d.mkdir(parents=True)
    (tmp_path / "secret.txt").write_text("s")
    os.symlink(tmp_path / "secret.txt", d / "link.txt")
    with pytest.raises(webguard.Refused):
        webguard.resolve(tmp_path, "threads/Q1P1/link.txt")
    big = d / "big.json"; big.write_bytes(b"0" * (webguard.MAX_BYTES + 1))
    with pytest.raises(webguard.Refused) as refused:
        webguard.resolve(tmp_path, "threads/Q1P1/big.json")
    assert refused.value.code == 413
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_webguard.py`
Expected: FAIL with `ImportError: cannot import name 'webguard'`.

- [ ] **Step 3: Implement**

```python
# pathfinder/webguard.py
"""Request checks and response headers for the local pages, and the one way they read campaign files.

The servers bind to 127.0.0.1, but a browser page elsewhere can still reach them through DNS rebinding
or a cross-site request, so every request must name this server as Host and, when it has one, as Origin.
Pages may not be framed; PDFs may be framed by this origin only, for the in-page reader. Files are served
only from threads/, with known suffixes and a size cap, never through a symlink that leaves the campaign."""
from __future__ import annotations
from pathlib import Path

MAX_BYTES = 8 * 1024 * 1024
SUFFIXES = {".pdf", ".tex", ".bib", ".md", ".txt", ".json", ".jsonl", ".log"}
PAGE_POLICY = ("default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; "
               "frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


class Refused(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def refusal(headers, port: int) -> str | None:
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    if headers.get("Host") not in hosts:
        return "local host required"
    origin = headers.get("Origin")
    if origin and origin not in {"http://" + h for h in hosts}:
        return "same origin required"
    return None


def headers(kind: str, filename: str | None = None) -> dict:
    out = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}
    if kind == "pdf":
        out.update({"X-Frame-Options": "SAMEORIGIN", "Content-Security-Policy": "frame-ancestors 'self'",
                    "Content-Disposition": f'inline; filename="{filename or "document.pdf"}"'})
    else:
        out.update({"X-Frame-Options": "DENY", "Content-Security-Policy": PAGE_POLICY})
    return out


def resolve(root: Path, relative: str) -> Path:
    root = Path(root).resolve()
    threads = root / "threads"
    candidate = root / relative
    try:
        target = candidate.resolve(strict=True)
    except (FileNotFoundError, RuntimeError, OSError):
        raise Refused(404, "document not found")
    if not target.is_relative_to(threads) or not target.is_file() or target.suffix not in SUFFIXES:
        raise Refused(404, "document not found")
    if target.stat().st_size > MAX_BYTES:
        raise Refused(413, "document too large for this viewer")
    return target
```

- [ ] **Step 4: Run and see them pass**

Run: `uv run --offline --locked pytest -q tests/test_webguard.py`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/webguard.py tests/test_webguard.py
git commit -m "Request checks, page and PDF headers, thread document resolver

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: The view server

**Files:**
- Create: `pathfinder/view.py`
- Test: `tests/test_view.py`

**Interfaces:**
- Consumes: `webguard` (Task 1), `campaign_state.build`.
- Produces: `view.make_server(campaign, port: int) -> ThreadingHTTPServer` (not started); `view.serve(campaign, port: int = 8791)`; routes `/` (view.html), `/view.js`, `/view.css`, `/api/state`, `/doc?path=<campaign-relative path>`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_view.py
import json, threading, urllib.error, urllib.request
import pytest
from pathfinder import view
from stubcampaign import make


@pytest.fixture
def server(tmp_path):
    c = make(tmp_path)
    d = c.thread_dir("Q1P1") / "edited"; d.mkdir(parents=True)
    (d / "note.pdf").write_bytes(b"%PDF-1.4 fake"); (d / "note.tex").write_text("\\section{x}")
    srv = view.make_server(c, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv, srv.server_address[1]
    srv.shutdown()


def get(port, path, headers=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", headers=headers or {})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_page_script_and_style_are_served_with_a_strict_policy(server):
    _, port = server
    status, headers, body = get(port, "/")
    assert status == 200 and b'src="view.js"' in body and b"<script>" not in body
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert get(port, "/view.js")[0] == 200 and get(port, "/view.css")[0] == 200


def test_state_endpoint_returns_the_state_document(server):
    _, port = server
    status, _, body = get(port, "/api/state")
    doc = json.loads(body)
    assert status == 200 and doc["units"][0]["unit"] == "Q1P1"
    assert doc["units"][0]["documents"][0]["pdf"] == "threads/Q1P1/edited/note.pdf"


def test_pdf_is_inline_and_framable_by_self_only(server):
    _, port = server
    status, headers, body = get(port, "/doc?path=threads/Q1P1/edited/note.pdf")
    assert status == 200 and body.startswith(b"%PDF") and headers["Content-Type"] == "application/pdf"
    assert headers["Content-Security-Policy"] == "frame-ancestors 'self'"
    status, headers, body = get(port, "/doc?path=threads/Q1P1/edited/note.tex")
    assert status == 200 and headers["Content-Type"].startswith("text/plain") and body == b"\\section{x}"


def test_foreign_host_origin_and_paths_are_refused(server):
    _, port = server
    assert get(port, "/api/state", {"Host": "evil.example"})[0] == 403
    assert get(port, "/api/state", {"Origin": "http://evil.example"})[0] == 403
    assert get(port, "/doc?path=campaign.json")[0] == 404
    assert get(port, "/campaign.json")[0] == 404
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_view.py`
Expected: FAIL with `ImportError: cannot import name 'view'`.

- [ ] **Step 3: Implement** (the page files themselves come in Task 3; create placeholders now so the routes resolve: `pathfinder/view.html` containing `<!doctype html><html><head><link rel="stylesheet" href="view.css"></head><body><script src="view.js"></script></body></html>`, empty `pathfinder/view.js` and `pathfinder/view.css`)

```python
# pathfinder/view.py
"""The operator's page: the campaign state document and the units' documents, read-only, on 127.0.0.1."""
from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from . import campaign_state, webguard

HERE = Path(__file__).parent
STATIC = {"/": ("view.html", "text/html; charset=utf-8"), "/view.js": ("view.js", "text/javascript; charset=utf-8"),
          "/view.css": ("view.css", "text/css; charset=utf-8")}


def make_server(campaign, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def reply(self, code: int, body: bytes, ctype: str, kind: str = "page", filename: str | None = None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for name, value in webguard.headers(kind, filename).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            refused = webguard.refusal(self.headers, self.server.server_address[1])
            if refused:
                return self.reply(403, refused.encode(), "text/plain; charset=utf-8")
            request = urlsplit(self.path)
            if request.path in STATIC:
                name, ctype = STATIC[request.path]
                return self.reply(200, (HERE / name).read_bytes(), ctype)
            if request.path == "/api/state":
                try:
                    body = json.dumps(campaign_state.build(campaign), default=str).encode()
                except Exception as error:               # the page shows the error instead of a blank screen
                    return self.reply(503, json.dumps({"error": repr(error)}).encode(), "application/json")
                return self.reply(200, body, "application/json")
            if request.path == "/doc":
                try:
                    target = webguard.resolve(campaign.root, parse_qs(request.query).get("path", [""])[0])
                except webguard.Refused as error:
                    return self.reply(error.code, str(error).encode(), "text/plain; charset=utf-8")
                if target.suffix == ".pdf":
                    return self.reply(200, target.read_bytes(), "application/pdf", "pdf", target.name)
                return self.reply(200, target.read_bytes(), "text/plain; charset=utf-8", "text")
            return self.reply(404, b"not found", "text/plain; charset=utf-8")

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(campaign, port: int = 8791):
    server = make_server(campaign, port)
    print(f"operator view at http://127.0.0.1:{server.server_address[1]}/  (state at /api/state)")
    server.serve_forever()
```

- [ ] **Step 4: Run and see them pass**

Run: `uv run --offline --locked pytest -q tests/test_view.py`
Expected: 4 passed. If the `Host` override in `test_foreign_host...` is ignored by urllib, send the request with `http.client.HTTPConnection` and `putheader("Host", ...)` instead, and record the ruling.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/view.py pathfinder/view.html pathfinder/view.js pathfinder/view.css tests/test_view.py
git commit -m "Operator view server: state document and thread documents behind request checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: The page

**Files:**
- Modify: `pathfinder/view.html`, `pathfinder/view.js`, `pathfinder/view.css`
- Test: `tests/test_view.py`

**Interfaces:**
- Consumes: `/api/state` (fields from `campaign_state.build`: `campaign`, `progress`, `runner`, `stages`, `blocks`, `units[].{unit, score, controller, research, editorial, assessment, last_activity, documents[].{kind, pdf, source, stale}}`), `/doc?path=`.
- Produces: a page with sections `#params`, `#pipeline`, `#blocks`, `#units`, `#reader`; filter state in the URL hash (`#stage=edit&state=blocked`) and document links `#note=<unit>` (optionally `&doc=<kind>`).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_view.py
def test_page_has_the_operator_sections_and_valid_script(server):
    import shutil, subprocess
    from pathlib import Path
    _, port = server
    body = get(port, "/")[2].decode()
    for section in ('id="params"', 'id="pipeline"', 'id="blocks"', 'id="units"', 'id="reader"'):
        assert section in body
    script = Path(view.__file__).with_name("view.js")
    assert "#note=" in script.read_text() and "stale" in script.read_text()
    node = shutil.which("node")
    if node:
        assert subprocess.run([node, "--check", str(script)], capture_output=True).returncode == 0
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_view.py -k sections`
Expected: FAIL (`id="params"` missing).

- [ ] **Step 3: Implement**

`pathfinder/view.html`:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pathfinder view</title>
<link rel="stylesheet" href="view.css">
</head>
<body>
<header><h1 id="title">Pathfinder</h1><span id="progress" class="pill"></span><span class="spacer"></span><span id="updated" class="muted"></span></header>
<main>
  <section id="params" class="card"></section>
  <section id="pipeline"></section>
  <section id="blocks"></section>
  <div class="split">
    <section id="units" class="card"></section>
    <section id="reader" class="card"><p class="muted">Select a unit to read its documents.</p></section>
  </div>
</main>
<script src="view.js"></script>
</body>
</html>
```

`pathfinder/view.js`:

```javascript
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
```

`pathfinder/view.css`:

```css
:root { --bg:#f4f5f7; --fg:#1c1e21; --muted:#6b7280; --line:#e3e5e8; --card:#fff; --accent:#2f6fed;
  --ok:#1a7f4b; --warn:#b7791f; --bad:#c0392b; --radius:10px; }
@media (prefers-color-scheme: dark) { :root { --bg:#111214; --fg:#e7e8ea; --muted:#9aa0a6; --line:#2a2d31; --card:#1a1c1f;
  --accent:#7aa2ff; --ok:#5fd38d; --warn:#e6b45c; --bad:#ff7b6b; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 -apple-system, "Segoe UI", system-ui, sans-serif; }
header { position:sticky; top:0; display:flex; gap:14px; align-items:center; padding:10px 24px; background:var(--card); border-bottom:1px solid var(--line); z-index:2; }
header h1 { font-size:17px; margin:0; } .spacer { flex:1; } .muted { color:var(--muted); }
main { padding:16px 24px; display:grid; gap:14px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:var(--radius); padding:12px 16px; }
h2 { font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); margin:0 0 8px; }
dl { display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); gap:4px 16px; margin:0; }
dt { color:var(--muted); font-size:12px; } dd { margin:0 0 6px; }
#pipeline { display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; }
.stage b { font-size:24px; margin-right:8px; } .stage span { color:var(--muted); }
.chip { margin:6px 6px 0 0; padding:2px 10px; border:1px solid var(--line); border-radius:999px; background:transparent; color:var(--fg); cursor:pointer; font:inherit; font-size:12px; }
.chip.on { background:var(--accent); color:#fff; border-color:var(--accent); }
.pill { padding:1px 9px; border-radius:999px; font-size:12px; border:1px solid var(--line); }
.pill.running, .pill.active { color:var(--ok); border-color:var(--ok); }
.pill.blocked, .pill.orphaned, .pill.unknown { color:var(--bad); border-color:var(--bad); }
.pill.stopped, .pill.recent { color:var(--warn); border-color:var(--warn); }
.warn { color:var(--warn); font-weight:600; }
.split { display:grid; grid-template-columns:minmax(0, 1fr) minmax(0, 1.2fr); gap:14px; align-items:start; }
@media (max-width: 1100px) { .split { grid-template-columns:1fr; } }
table { width:100%; border-collapse:collapse; } th, td { text-align:left; padding:5px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
th { font-size:12px; color:var(--muted); font-weight:600; } tr.sel { background:rgba(47,111,237,.08); }
a { color:var(--accent); text-decoration:none; } a:hover { text-decoration:underline; }
nav .tab { margin-right:12px; } nav .tab.on { font-weight:700; }
#reader iframe { width:100%; height:78vh; border:1px solid var(--line); border-radius:6px; background:#fff; }
#reader pre { white-space:pre-wrap; max-height:78vh; overflow:auto; font-size:12px; }
```

- [ ] **Step 4: Run and see it pass**

Run: `uv run --offline --locked pytest -q tests/test_view.py`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/view.html pathfinder/view.js pathfinder/view.css tests/test_view.py
git commit -m "Operator page: parameters, pipeline filters, blocks, units, in-page document reader

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Harden the old monitor server; `pathfinder view` command

**Files:**
- Modify: `pathfinder/monitor.py:133-168` (`serve`), `pathfinder/cli.py` (new `view` subcommand)
- Test: `tests/test_monitor.py`, `tests/test_view.py`

**Interfaces:**
- Consumes: `webguard.refusal`, `webguard.resolve`, `view.serve`.
- Produces: `monitor.make_server(campaign, port) -> HTTPServer` (not started; `serve` uses it); `pathfinder view [--port 8791]`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_monitor.py
def test_monitor_server_checks_host_and_serves_no_arbitrary_files(tmp_path):
    import threading, urllib.error, urllib.request
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=2, cut=50,
                 rounds=3, allowances={}, budget_usd=10, prices={}, scan_fulltext=None)
    (tmp_path / "shortlist.json").write_text(json.dumps({"pairs": []}))
    (tmp_path / ".env").write_text("SECRET=1"); (tmp_path / "notes.txt").write_text("private")
    srv = monitor.make_server(c, 0); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    def code(path, headers=None):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}{path}", headers=headers or {})) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
    try:
        assert code("/") == 200 and code("/state") == 200
        assert code("/.env") == 404 and code("/notes.txt") == 404
        assert code("/state", {"Origin": "http://evil.example"}) == 403
    finally:
        srv.shutdown()
```

```python
# append to tests/test_view.py
def test_cli_has_a_view_command():
    from pathfinder import cli
    with pytest.raises(SystemExit) as done:
        cli.main(["view", "--help"])
    assert done.value.code == 0
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_monitor.py tests/test_view.py -k "host_and_serves or view_command"`
Expected: FAIL (`make_server` missing; argparse rejects `view`).

- [ ] **Step 3: Implement**

Replace `monitor.serve` with a `make_server` plus a thin `serve`:

```python
def make_server(campaign, port: int = 8790):
    from . import webguard
    root = campaign.root

    class H(BaseHTTPRequestHandler):
        def _send(self, body: bytes, ctype: str, code: int = 200, kind: str = "text", filename=None):
            self.send_response(code); self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for name, value in webguard.headers(kind, filename).items():
                if kind == "monitor-page" and name == "Content-Security-Policy":
                    continue                                   # the classic page uses inline script and KaTeX from a CDN
                self.send_header(name, value)
            self.end_headers(); self.wfile.write(body)

        def do_GET(self):
            refused = webguard.refusal(self.headers, self.server.server_address[1])
            if refused:
                return self._send(refused.encode(), "text/plain; charset=utf-8", 403)
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                return self._send(PAGE.read_bytes(), "text/html; charset=utf-8", kind="monitor-page")
            if path == "/state":
                return self._send(json.dumps(state(campaign)).encode(), "application/json")
            m = re.fullmatch(r"/threads/(Q\d+P\d+)/\1\.pdf", path)
            if m:
                tex = campaign.thread_dir(m.group(1)) / f"{m.group(1)}.tex"
                if not tex.exists():
                    return self._send(b"no note yet", "text/plain; charset=utf-8", 404)
                data, log = pdf(tex)
                return (self._send(data, "application/pdf", kind="pdf", filename=f"{m.group(1)}.pdf") if data
                        else self._send(log.encode(), "text/plain; charset=utf-8", 500))
            try:
                target = webguard.resolve(root, path.lstrip("/"))
            except webguard.Refused as error:
                return self._send(str(error).encode(), "text/plain; charset=utf-8", error.code)
            if target.suffix == ".pdf":
                return self._send(target.read_bytes(), "application/pdf", kind="pdf", filename=target.name)
            return self._send(target.read_bytes(), "text/plain; charset=utf-8")

        def log_message(self, *a):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), H)


def serve(campaign, port: int = 8790):
    print(f"monitor at http://localhost:{port}/  (state at /state, thread files under /threads/)")
    make_server(campaign, port).serve_forever()
```

Change the import line to `from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer` (drop `HTTPServer`, `SimpleHTTPRequestHandler` and `mimetypes` if unused). Note: the classic page keeps no CSP because it loads KaTeX from a CDN and uses inline script; it still gets `X-Frame-Options: DENY`, `nosniff` and the Host and Origin checks.

In `pathfinder/cli.py`, next to `serve`:

```python
    sub.add_parser("view", help="serve the operator view: state, pipeline, units and documents").add_argument("--port", type=int, default=8791)
```

and in `_dispatch`, next to `serve`:

```python
    elif ns.cmd == "view":
        from . import view
        view.serve(c, ns.port)
```

- [ ] **Step 4: Run and see them pass, then the monitor, view and CLI suites**

Run: `uv run --offline --locked pytest -q tests/test_monitor.py tests/test_view.py tests/test_webguard.py`
Expected: all PASS. If the classic page's file links under `/threads/...` point at files outside `threads/` (for example the root `receipts.jsonl`), those links now 404; that is intended (root files are reachable through `/state`).

- [ ] **Step 5: Commit**

```bash
git add pathfinder/monitor.py pathfinder/cli.py tests/test_monitor.py tests/test_view.py
git commit -m "Monitor server checks Host and Origin and serves only thread documents; pathfinder view

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Full verification and spec

- [ ] **Step 1:** `uv run --offline --locked pytest -q` (expect only the baseline statarb failure) and the behave command (expect 93 passed, 1 failed, 9 error, as on main).
- [ ] **Step 2:** In `notes/pathfinder-friction.tex`, append to H10 "Done in phase 2b except the aggregate across campaigns, which moves to phase 4 with the batch coordinator (commits ...)", rebuild the PDF in `notes/`, run `/Users/v/.local/bin/style-ban-artifacts notes/pathfinder-friction.tex`.
- [ ] **Step 3:** Commit:

```bash
git add notes/pathfinder-friction.tex notes/pathfinder-friction.pdf
git commit -m "Phase 2b complete: operator view and server hardening

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

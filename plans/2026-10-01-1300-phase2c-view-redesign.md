# Phase 2c: Operator view redesign after the statarb watchboard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `pathfinder view` on the design the statarb watchboard reached on 1 October (commit `b02f9d6` in `../statarb`): an instrument-panel page whose loud element is a left-to-right pipeline where every unit sits in exactly one state, a searchable unit queue with titles and scores, a research desk of cards, a reader in a modal dialog that refreshes never disturb, a usage panel, and an error banner that keeps the last snapshot.

**Architecture:** The server decides each unit's single pipeline position (`lifecycle`) and ships the pipeline definition with its counts, so the page renders and filters from server data and cannot drift from it (this also resolves the phase 2b deferred minor). `campaign_state` gains per-unit titles, identifiers, abstracts, scan scores, connexion, summary and per-unit usage, plus a campaign usage block. The page is a port of `../statarb/arxiv_drip/watchboard.{html,js,css}` reshaped for pairs: masthead, introduction with the campaign parameters, pipeline, queue, research desk, usage, footer, and one `<dialog>` for documents and details. CSP stays strict: no inline script or style; sizes go through the CSSOM.

**Tech Stack:** Python 3.13, plain JavaScript, node harness tests (`tests/js/`), pytest.

**Spec:** `notes/pathfinder-friction.tex` operator view decisions; reference implementation `../statarb/arxiv_drip/watchboard.*` and `WATCHBOARD.md`.

## Global Constraints

- Baseline: the full suite and behave as left by the merge before this phase (record the numbers in the ledger before Task 1).
- Every unit appears in exactly one pipeline state; the sum of the pipeline counts equals the number of units.
- Refreshes (every 20 s) never rebuild the dialog's content; only hash changes and explicit actions do.
- No external requests from the page; every interpolation escaped; no inline `style=` attributes.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- A unit with research DRAFT, edit done and paper ACCEPTED counts once, under Paper / accepted (Task 1 test).
- A unit recorded as running with no live runner is "orphaned" in the pipeline, not "researching" (Task 1 test).
- A PDF open in the dialog survives a refresh with changed unrelated data (Task 3 node test).
- `#note=Q1P1&doc=paper` opens that document on load; closing the dialog removes `note` from the hash (Task 3 node test).
- A failed `/api/state` keeps the previous snapshot visible with a banner (Task 3 node test).

---

### Task 1: Lifecycle position and pipeline in the state document

**Files:**
- Modify: `pathfinder/campaign_state.py`
- Test: `tests/test_campaign_state.py`

**Interfaces:**
- Produces: `campaign_state.PIPELINE` (list of `(stage title, [(state key, label), ...])`); `campaign_state.lifecycle(research_s, edit_s, paper_s, controller) -> str` (a state key); unit key `lifecycle`; document key `pipeline` = `[{"title", "count", "states": [{"key", "label", "count"}]}]`.

```python
PIPELINE = [
    ("Selected", [("waiting", "Waiting")]),
    ("Research", [("researching", "In progress"), ("stopped", "Stopped"), ("orphaned", "Orphaned")]),
    ("Outcome", [("draft", "DRAFT"), ("pause", "Paused"), ("blocked", "Blocked")]),
    ("Readable note", [("editing", "Editing"), ("noted", "Note ready"), ("note-blocked", "Note blocked")]),
    ("Paper", [("writing", "Writing"), ("accepted", "Accepted"), ("amend", "Amendments asked"), ("paper-blocked", "Paper blocked")]),
]
```

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_campaign_state.py
def _states(c, unit, research_status, edit_status=None, paper_status=None):
    c.thread_dir(unit).mkdir(parents=True, exist_ok=True)
    research._set(c, unit, status=research_status)
    if edit_status:
        edit._set(c, unit, status=edit_status)
    if paper_status:
        from pathfinder import paper
        paper._set(c, unit, status=paper_status)


def test_every_unit_has_exactly_one_pipeline_position(tmp_path):
    units = ("Q1P1", "Q1P2", "Q1P3", "Q1P4", "Q1P5")
    c = make(tmp_path, pairs=units)
    _states(c, "Q1P1", "DRAFT", "done", "ACCEPTED")
    _states(c, "Q1P2", "PAUSE", "done")
    _states(c, "Q1P3", "BLOCKED")
    _states(c, "Q1P4", "running")
    s = campaign_state.build(c)
    position = {u["unit"]: u["lifecycle"] for u in s["units"]}
    assert position == {"Q1P1": "accepted", "Q1P2": "noted", "Q1P3": "blocked", "Q1P4": "orphaned", "Q1P5": "waiting"}
    assert sum(stage["count"] for stage in s["pipeline"]) == len(units)
    assert [stage["title"] for stage in s["pipeline"]] == [t for t, _ in campaign_state.PIPELINE]
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_campaign_state.py -k pipeline_position`
Expected: FAIL with `KeyError: 'lifecycle'`.

- [ ] **Step 3: Implement**

```python
def lifecycle(research_s: dict, edit_s: dict, paper_s: dict, controller: str) -> str:
    """The unit's single pipeline position: the furthest stage it has reached, then that stage's state."""
    p, e, r = paper_s.get("status"), edit_s.get("status"), research_s.get("status", "new")
    if p:
        return {"ACCEPTED": "accepted", "PAUSE-ON-AMEND": "amend", "blocked": "paper-blocked",
                "stopped": "paper-blocked"}.get(p, "writing")
    if e and e != "none":
        return {"done": "noted", "blocked": "note-blocked", "stopped": "note-blocked"}.get(e, "editing")
    if r in research.TERMINAL:
        return "draft" if r == "DRAFT" else "pause"
    if r == "BLOCKED":
        return "blocked"
    if r == "new":
        return "waiting"
    return {"running": "researching", "orphaned": "orphaned"}.get(controller, "stopped")
```

In `build`, compute `controller` first, then `"lifecycle": lifecycle(r_s, e_s, p_s, controller)` on each unit, and after the loop:

```python
    counts = Counter(u["lifecycle"] for u in units)
    pipeline = [{"title": title, "count": sum(counts[k] for k, _ in states),
                 "states": [{"key": k, "label": label, "count": counts[k]} for k, label in states]}
                for title, states in PIPELINE]
```

and add `"pipeline": pipeline` to the document.

- [ ] **Step 4: Run and see it pass, then the state suite; commit**

Run: `uv run --offline --locked pytest -q tests/test_campaign_state.py`
Expected: all PASS.

```bash
git add pathfinder/campaign_state.py tests/test_campaign_state.py
git commit -m "One pipeline position per unit, and the pipeline with its counts, in the state document

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Unit titles, scores, summary and usage in the state document

**Files:**
- Modify: `pathfinder/campaign_state.py`
- Test: `tests/test_campaign_state.py`

**Interfaces:**
- Produces: unit keys `q` and `p` (`{"id", "title", "abstract"}` from `Q.jsonl`/`P.jsonl` by the pair's indices), `feasibility`, `gain`, `connexion` (from `scan.jsonl`), `summary` (the last verdict's reason from `<unit>.verdict.json`, else the research status reason), `usage` (`{"calls", "input_tokens", "output_tokens", "seconds"}` from receipts with `thread == unit`); document key `usage` (`{"calls", "completed", "calls_with_usage", "input_tokens", "cache_read", "output_tokens", "seconds"}`).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_campaign_state.py
def test_units_carry_titles_scores_summary_and_usage(tmp_path):
    c = make(tmp_path)
    c.path("scan.jsonl").write_text(json.dumps({"pair_id": "Q1P1", "feasibility": 7, "gain": 6, "connexion": "a bridge"}) + "\n")
    c.path("receipts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in (
        {"thread": "Q1P1", "stage": "peer", "outcome": "completed", "input_tokens": 100, "output_tokens": 5, "seconds": 3.0},
        {"thread": "Q1P1", "stage": "verify", "outcome": "timeout", "input_tokens": None, "output_tokens": None, "seconds": 9.0})))
    d = c.thread_dir("Q1P1"); d.mkdir(parents=True)
    (d / "Q1P1.verdict.json").write_text(json.dumps([{"decision": "PAUSE", "reason": "missing proof"}]))
    u = campaign_state.build(c)["units"][0]
    assert u["q"]["title"] == "Q paper 1" and u["p"]["abstract"] == "Abstract of P1."
    assert (u["feasibility"], u["gain"], u["connexion"]) == (7, 6, "a bridge")
    assert u["summary"] == "missing proof"
    assert u["usage"] == {"calls": 2, "input_tokens": 100, "output_tokens": 5, "seconds": 12.0}
    usage = campaign_state.build(c)["usage"]
    assert (usage["calls"], usage["completed"], usage["calls_with_usage"]) == (2, 1, 1)
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_campaign_state.py -k titles_scores`
Expected: FAIL with `KeyError: 'q'`.

- [ ] **Step 3: Implement**

Add helpers:

```python
def _corpus(campaign, side: str) -> list[dict]:
    path = campaign.path(f"{side}.jsonl")
    rows = []
    for line in (path.read_text().splitlines() if path.is_file() else []):
        try:
            rows.append(json.loads(line))
        except ValueError:
            rows.append({})
    return rows


def _paper(rows: list[dict], index: int) -> dict:
    row = rows[index - 1] if 0 < index <= len(rows) else {}
    return {"id": row.get("id"), "title": row.get("title"), "abstract": row.get("abstract")}


def _summary(campaign, unit: str, research_s: dict) -> str | None:
    verdicts = _json(campaign.thread_dir(unit) / f"{unit}.verdict.json") or []
    if isinstance(verdicts, list) and verdicts and isinstance(verdicts[-1], dict) and verdicts[-1].get("reason"):
        return verdicts[-1]["reason"]
    return research_s.get("reason")
```

Change `_scores` into `_scan(campaign) -> dict[unit, row]` keeping whole rows, and derive `score` from `feasibility * gain` where both are present. In `build`, load `Q, P = _corpus(campaign, "Q"), _corpus(campaign, "P")`, parse the pair indices with `i, j = (int(x) for x in unit[1:].split("P"))` (skip titles for identifiers that do not match `Q\d+P\d+`), sum receipts per `thread`, and add the unit keys listed above. Add the campaign `usage` block: `calls = len(receipts)`, `completed` (outcome `completed`), `calls_with_usage` (input_tokens not None), token sums and summed `seconds`.

- [ ] **Step 4: Run, then the state and view suites; commit**

Run: `uv run --offline --locked pytest -q tests/test_campaign_state.py tests/test_view.py`
Expected: all PASS.

```bash
git add pathfinder/campaign_state.py tests/test_campaign_state.py
git commit -m "Unit titles, scan scores, summaries and usage in the state document

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: The page, ported from the watchboard

**Files:**
- Modify: `pathfinder/view.html`, `pathfinder/view.js`, `pathfinder/view.css`
- Modify: `tests/js/view_harness.js`, `tests/test_view.py`

**Interfaces:**
- Consumes: `/api/state` with `pipeline`, `units[].{unit, lifecycle, q, p, feasibility, gain, score, connexion, summary, usage, research, editorial, assessment, documents}`, `usage`, `campaign`, `progress`, `runner`, `blocks`.
- Produces: page ids `connection-dot`, `connection-text`, `refresh-button`, `page-title`, `lede`, `params`, `error-banner`, `pipeline`, `search`, `status-filter`, `queue-body`, `queue-count`, `research-list`, `research-count`, `usage`, `blocks`, `snapshot-time`, `detail-dialog`, `detail-label`, `dialog-actions`, `detail-content`, `close-dialog`.

- [ ] **Step 1: Rewrite the harness and tests first**

Replace `tests/js/view_harness.js` with a harness that loads `view.js` with a fake DOM where each element records `innerHTML` writes and `dialog` elements have `showModal()`/`close()` and an `open` flag, `fetch` returns a queue of prepared responses, and `location.hash` is writable. It must expose the page's `render`, `refresh` and `openFromHash` through `vm.runInContext(source + "\n;globalThis.__api = {render, refresh, openFromHash, get current() { return current; }};", context)`, run these scenarios, and print one JSON object:

- `dialog_survives_refresh`: open `#note=Q1P1&doc=paper`, record the dialog content write count, call `refresh()` with a state whose other unit's `last_activity` changed; true when `detail-content` was not written again.
- `hash_opens_document`: with `#note=Q1P1&doc=paper` before the first `refresh()`, true when the dialog is open and `detail-content` contains `/doc?path=threads%2FQ1P1%2Fpaper%2Fpaper.pdf`.
- `close_clears_hash`: clicking `close-dialog` (call its registered handler) leaves a hash without `note`.
- `failed_refresh_keeps_snapshot`: a second `refresh()` whose fetch rejects leaves `queue-body` unchanged and `error-banner.hidden === false`.
- `pipeline_counts_from_server`: `pipeline` innerHTML contains each server stage title and count.
- `escaped`: a unit summary `<img src=x onerror=1>` appears only as `&lt;img`.

In `tests/test_view.py`, replace the three harness tests with one per scenario asserting each flag is true, and keep `test_page_has_the_operator_sections_and_valid_script` updated to the new ids (`pipeline`, `queue-body`, `research-list`, `usage`, `detail-dialog`).

- [ ] **Step 2: Run them and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_view.py`
Expected: the scenario tests FAIL (the current page has no dialog, no `refresh`, no `openFromHash`).

- [ ] **Step 3: Implement the page**

`pathfinder/view.css`: copy the watchboard stylesheet and append the Pathfinder state colours:

```bash
cp ../statarb/arxiv_drip/watchboard.css pathfinder/view.css
cat >> pathfinder/view.css <<'CSS'

/* Pathfinder pipeline states, mapped onto the watchboard palette */
.state-waiting { color: var(--intake); } .stage-bar .state-waiting { background: var(--intake); }
.state-researching { color: var(--research); } .stage-bar .state-researching { background: var(--research); }
.state-stopped, .state-orphaned { color: var(--stopped); } .stage-bar .state-stopped, .stage-bar .state-orphaned { background: var(--stopped); }
.state-draft, .state-noted, .state-accepted { color: var(--ready); }
.stage-bar .state-draft, .stage-bar .state-noted, .stage-bar .state-accepted { background: var(--ready); }
.state-pause, .state-amend { color: var(--pause); } .stage-bar .state-pause, .stage-bar .state-amend { background: var(--pause); }
.state-blocked, .state-note-blocked, .state-paper-blocked { color: var(--reject); }
.stage-bar .state-blocked, .stage-bar .state-note-blocked, .stage-bar .state-paper-blocked { background: var(--reject); }
.state-editing, .state-writing { color: var(--scored); } .stage-bar .state-editing, .stage-bar .state-writing { background: var(--scored); }
.badge.waiting { color: var(--intake); } .badge.researching { color: var(--research); }
.badge.draft, .badge.noted, .badge.accepted { color: var(--ready); } .badge.pause, .badge.amend { color: var(--pause); }
.badge.blocked, .badge.note-blocked, .badge.paper-blocked { color: var(--reject); }
.badge.stopped, .badge.orphaned { color: var(--stopped); } .badge.editing, .badge.writing { color: var(--scored); }
CSS
```

Then in the copied file change `.stages { ... grid-template-columns: repeat(5, ...) }` only if the stage count differs (Pathfinder has five stages, as statarb does; leave it).

`pathfinder/view.html`: the watchboard's structure with Pathfinder sections: masthead (`brand` "Pathfinder operator view", connection dot and text, Refresh button); introduction with `<h1 id="page-title">`, `<p class="lede" id="lede">` and `<dl class="clock" id="params">`; `#error-banner`; `<section class="pipeline"><ol id="pipeline" class="stages"></ol></section>`; work grid with the queue panel (search input `#search` "Search titles, unit or arXiv ID", select `#status-filter` with `all` plus one option per pipeline state key, table headed "Pair and proposed connexion / State / F / G / Score", body `#queue-body`, `#queue-count`) and the research desk (`#research-list`, `#research-count`); lower grid with `#usage` and `#blocks`; footer with `#snapshot-time`; the `<dialog id="detail-dialog">` with `#detail-label`, `#dialog-actions`, `#close-dialog`, `#detail-content`. One `<script src="view.js" defer>`; one stylesheet `view.css`.

`pathfinder/view.js`: port `watchboard.js` with these changes, keeping its helpers (`esc`, `num`, `short`, `when`, `duration`, `badge`), its delegated click handler, its CSSOM sizing and its `refresh()` (20 s interval, error banner that keeps the last snapshot, `openFromHash()` on the first snapshot):

- `renderPipeline()` renders `current.pipeline` (server titles, counts and states) instead of a client `STAGES` table; state buttons toggle `#status-filter`.
- `renderQueue()` lists `current.units` sorted by score, filtered by `lifecycle` and by the search text over unit, Q and P titles and identifiers; title cell shows `Q title × P title` as a `data-unit` button, the unit and arXiv ids, and `short(connexion)`; F / G and score columns as in the watchboard.
- `renderDesk()` shows a card per unit whose research has started (lifecycle not `waiting`): badge, unit, both titles, `summary`, research/edit/paper statuses, and actions `Read note` (the most refined document: paper, else readable note, else research note; `data-pdf`/`data-source`/`data-stale`, or `data-source` alone when no PDF) and `Details and receipts` (`data-unit`).
- `renderUsage()` shows input tokens (with cached), output tokens, summed call time, completed of total calls and the line "Subscription-backed: dollar cost and remaining allowance are not reported. Usage was reported for N of M calls."
- `renderParams()` fills `#page-title` (campaign name), `#lede` (backend, model, scheme) and `#params` (seats, rounds, allowances, execution id, runner status and liveness, progress, stop reason).
- `renderBlocks()` lists blocks by class with `data-unit` links.
- `showDocument(unit, kind)` opens the dialog on a document: PDF in an `iframe.pdf-frame` with actions "Open in a new tab" and "View LaTeX source", stale notice; without PDF, the source text fetched into `<pre class="note-content">` with `r.ok` checked. It sets `location.hash` to `note=<unit>&doc=<kind>` with `history.replaceState` so no `hashchange` fires.
- `showUnit(unit)` opens the dialog on details: abstracts of Q and P with arXiv links, scan scores and connexion, the three statuses with reasons, per-unit usage, documents as buttons.
- `render()` never touches the dialog. `openFromHash()` runs on the first snapshot and on `hashchange`. Closing the dialog (`close` event) removes `note` and `doc` from the hash with `history.replaceState`.

- [ ] **Step 4: Run and see the tests pass; check the script; commit**

Run: `uv run --offline --locked pytest -q tests/test_view.py tests/test_webguard.py` and `node --check pathfinder/view.js`.
Expected: all PASS.

```bash
git add pathfinder/view.html pathfinder/view.js pathfinder/view.css tests/js/view_harness.js tests/test_view.py
git commit -m "Operator view redesigned after the statarb watchboard: pipeline, queue, research desk, dialog reader

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Look at it, then verify and record

- [ ] **Step 1:** Serve a real campaign (`uv run pathfinder --root experiments/2026-09-28-recursive-extension/recursive view --port 8795`) and, if a browser tool is connected, take a screenshot of the page, of the dialog on a paper and of a filtered pipeline; otherwise ask the operator to open it and say what they see. Record what was checked in the ledger.
- [ ] **Step 2:** Full pytest and behave at baseline.
- [ ] **Step 3:** In `notes/pathfinder-friction.tex`, add to the operator view decision "Redesigned in phase 2c after the statarb watchboard (commits ...)"; rebuild; style gate; commit.

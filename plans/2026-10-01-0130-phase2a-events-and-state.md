# Phase 2a: Event log, execution identifier and campaign state

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One append-only typed event stream per campaign, an execution identifier that covers uncommitted code, and one machine-readable campaign state document with separated research, editorial, assessment and controller states, per-stage unit counts, blocks by failure class and a token budget, readable by the operator (`pathfinder state`) and by the apex agent (`state.json`).

**Architecture:** `pathfinder/events.py` appends JSON lines to `events.jsonl` under a process lock and reads them back, reporting a truncated tail instead of hiding it. Emit points sit where state already changes: `transport._attempt` and `_receipt`, the three `_set` functions of research, edit and paper, `runner.request_stop` and `failures.stop_for`, and `provenance.start`, which also computes the execution identifier. `pathfinder/campaign_state.py` derives the state document from the existing status files, receipts and events; it does not replace them. Phase 2b (separate plan) builds the operator web page and the server hardening on this document.

**Tech Stack:** Python 3.13 via uv, pytest, the stub backend (`tests/stubcampaign.make`).

**Spec:** `notes/pathfinder-friction.tex`: D1, H4, S4, S8, F09, F10, R04 and the operator view decisions (web page contents; "the operator view reads documents, not sources"). Roadmap: `plans/2026-10-01-0030-refactor-roadmap.md`.

## Global Constraints

- Run tests with `uv run --offline --locked pytest -q <files>`; the full suite takes more than two minutes. Do not edit engine files while a suite runs: provenance raises `RestartRequired` and fails unrelated tests.
- Baseline (commit 99db88e): 257 passed, 1 failed (`tests/test_deployments.py::test_statarb_prepares_freezes_and_runs_the_candidate_engine`, pre-existing, phase 7).
- Formats may change; no converter. Budgets are tokens and calls, not dollars.
- Event writes must never break a stage: an event write error is swallowed after one stderr line, never raised.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- Two threads emitting concurrently never interleave partial lines (Task 1 test with threads).
- A truncated last line of `events.jsonl` yields `progress: "unknown"` in the state, never a healthy inference (Task 4 test).
- A pair with research DRAFT and a failed edit shows both, not one merged label (Task 4 test).
- A PDF older than its source is flagged stale (Task 4 test).
- Two runs from the same commit with different working-tree bytes get different execution identifiers (Task 3 test).

---

### Task 1: Event log module

**Files:**
- Create: `pathfinder/events.py`
- Test: `tests/test_events.py`

**Interfaces:**
- Produces: `events.KINDS` (frozenset); `events.emit(campaign, kind: str, **fields) -> None`; `events.read(campaign) -> tuple[list[dict], bool]` (events, truncated).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_events.py
import json, threading
import pytest
from pathfinder import events
from stubcampaign import make


def test_emit_appends_one_typed_line(tmp_path):
    c = make(tmp_path)
    events.emit(c, "status_changed", unit="Q1P1", axis="research", to="running")
    rows, truncated = events.read(c)
    assert not truncated and len(rows) == 1
    assert rows[0]["kind"] == "status_changed" and rows[0]["unit"] == "Q1P1" and rows[0]["v"] == 1 and rows[0]["at"]


def test_unknown_kind_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        events.emit(make(tmp_path), "something_else")


def test_concurrent_emits_never_interleave(tmp_path):
    c = make(tmp_path)
    def burst(n):
        for i in range(200):
            events.emit(c, "call_started", unit=f"Q{n}P1", stage="peer", detail="x" * 500)
    threads = [threading.Thread(target=burst, args=(n,)) for n in range(4)]
    [t.start() for t in threads]; [t.join() for t in threads]
    rows, truncated = events.read(c)
    assert not truncated and len(rows) == 800


def test_a_partial_last_line_is_reported_as_truncation(tmp_path):
    c = make(tmp_path)
    events.emit(c, "run_started", execution_id="e1")
    with c.path("events.jsonl").open("a") as f:
        f.write('{"v": 1, "kind": "call_star')
    rows, truncated = events.read(c)
    assert truncated and len(rows) == 1


def test_a_write_error_does_not_raise(tmp_path, capsys):
    c = make(tmp_path)
    c.path("events.jsonl").mkdir()                    # a directory where the file should be
    events.emit(c, "run_started")
    assert "event not recorded" in capsys.readouterr().err
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_events.py`
Expected: FAIL with `ImportError: cannot import name 'events'`.

- [ ] **Step 3: Implement**

```python
# pathfinder/events.py
"""The campaign's event stream: one JSON line per thing that happened, appended to events.jsonl.

Events add what status files cannot hold: when each call started and ended, every status transition
with its previous value, stops and runs with their execution identifier. The status files stay the
authority for where a unit stands; events are its history. A write never breaks the stage that emits
it. A reader is told when the last line is incomplete, so a monitor can say "unknown" instead of
inferring progress from a cut record."""
from __future__ import annotations
import json, sys, threading, time

KINDS = frozenset({"run_started", "run_finished", "call_started", "call_finished", "status_changed", "stop_requested"})
_lock = threading.Lock()


def emit(campaign, kind: str, **fields) -> None:
    if kind not in KINDS:
        raise ValueError(f"unknown event kind {kind!r}; expected one of {', '.join(sorted(KINDS))}")
    row = {"v": 1, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "run_id": getattr(campaign, "run_id", None), "kind": kind, **fields}
    line = json.dumps(row, default=str) + "\n"
    try:
        with _lock, open(campaign.path("events.jsonl"), "a") as stream:
            stream.write(line)
    except OSError as error:
        print(f"pathfinder: event not recorded ({kind}): {error}", file=sys.stderr)


def read(campaign) -> tuple[list[dict], bool]:
    path = campaign.path("events.jsonl")
    if not path.is_file():
        return [], False
    rows, truncated = [], False
    text = path.read_text(errors="replace")
    lines = text.split("\n")
    for number, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            truncated = True                       # a cut or corrupt line: progress cannot be read past it
    if text and not text.endswith("\n"):
        truncated = True
    return rows, truncated
```

- [ ] **Step 4: Run and see them pass**

Run: `uv run --offline --locked pytest -q tests/test_events.py`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/events.py tests/test_events.py
git commit -m "Campaign event stream with truncation-aware reader

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Emit events where state changes

**Files:**
- Modify: `pathfinder/transport.py` (`_attempt`, `_receipt`), `pathfinder/research.py:43-46` (`_set`), `pathfinder/edit.py:36-42` (`_set`), `pathfinder/paper.py:23-27` (`_set`), `pathfinder/runner.py` (`request_stop`), `pathfinder/failures.py` (`stop_for`)
- Test: `tests/test_events.py`

**Interfaces:**
- Consumes: `events.emit` (Task 1).
- Produces: event fields. `call_started`: `unit, stage, actor, attempt_id, prompt_chars`. `call_finished`: `unit, stage, actor, outcome, failure_class, seconds, input_tokens, output_tokens, cache_read, tool_calls`. `status_changed`: `unit, axis` (`research`, `editorial` or `assessment`), `from`, `to`, `reason`. `stop_requested`: `reason, failure_class` (or None), `scope` (`campaign` or `parent`).

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_events.py
def test_a_stub_research_run_records_calls_and_transitions(tmp_path):
    from pathfinder import research
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    rows, _ = events.read(c)
    kinds = [r["kind"] for r in rows]
    assert kinds.count("call_started") == kinds.count("call_finished") > 0
    research_changes = [r for r in rows if r["kind"] == "status_changed" and r["axis"] == "research"]
    assert research_changes[0]["from"] is None and research_changes[-1]["to"] == research.status(c, "Q1P1")["status"]
    assert all(r["unit"] == "Q1P1" for r in rows if r["kind"] in ("call_started", "call_finished"))


def test_status_changed_only_when_the_status_changes(tmp_path):
    from pathfinder import edit
    c = make(tmp_path)
    edit._set(c, "Q1P1", status="editing", attempt=1)
    edit._set(c, "Q1P1", status="editing", attempt=2)
    edit._set(c, "Q1P1", status="blocked", reason="r")
    changes = [r for r in events.read(c)[0] if r["kind"] == "status_changed"]
    assert [(r["axis"], r["from"], r["to"]) for r in changes] == [("editorial", None, "editing"), ("editorial", "editing", "blocked")]


def test_stops_are_recorded_with_their_class(tmp_path):
    from pathfinder import failures, runner
    c = make(tmp_path)
    failures.stop_for(c, failures.classify("error", "You've hit your usage limit."), "usage limit")
    runner.request_stop(c, "operator")
    stops = [r for r in events.read(c)[0] if r["kind"] == "stop_requested"]
    assert stops[0]["failure_class"] == "quota" and stops[0]["scope"] == "campaign"
    assert stops[1]["failure_class"] is None and stops[1]["reason"] == "operator"
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_events.py`
Expected: the three new tests FAIL (no events recorded).

- [ ] **Step 3: Implement**

In `transport._attempt`, after `health.write(path, activity)`:

```python
    from . import events
    events.emit(campaign, "call_started", unit=request.thread, stage=request.stage, actor=request.actor,
                attempt_id=attempt, prompt_chars=len(request.prompt))
```

In `transport._receipt`, after the receipt line is written and before `failures.stop_for(...)`:

```python
    from . import events
    events.emit(campaign, "call_finished", unit=thread, stage=stage, actor=actor, outcome=r.get("outcome"),
                failure_class=(r["failure"] or {}).get("class"), seconds=r.get("seconds"),
                input_tokens=r.get("input_tokens"), output_tokens=r.get("output_tokens"),
                cache_read=r.get("cache_read"), tool_calls=r.get("tool_calls"))
```

Add to `pathfinder/events.py`:

```python
def transition(campaign, unit: str, axis: str, before: dict, after: dict) -> None:
    """A status_changed event when a status file's "status" value changed."""
    if before.get("status") != after.get("status"):
        emit(campaign, "status_changed", unit=unit, axis=axis, **{"from": before.get("status")},
             to=after.get("status"), reason=after.get("reason"))
```

In `research._set`:

```python
def _set(campaign, pair_id, **kw):
    s = status(campaign, pair_id); before = dict(s); s.update(kw, updated=_now())
    _atomic_write(campaign.thread_dir(pair_id) / "status.json", json.dumps(s, indent=1).encode())
    from . import events
    events.transition(campaign, pair_id, "research", before, s)
    return s
```

`research.status` returns a default with `"status": "new"` for an unstarted thread; if so, the first transition reads `from: "new"`, and the test's `from is None` assertion must become `in (None, "new")`; record that as a ruling if it happens.

In `edit._set` and `paper._set`, take `before = dict(s)` right after `s = status(campaign, pair_id)`, and after writing the file call `events.transition(campaign, pair_id, "editorial", before, s)` (edit) or `events.transition(campaign, pair_id, "assessment", before, s)` (paper), importing `events` locally.

In `runner.request_stop`, after writing the file:

```python
    from . import events
    events.emit(campaign, "stop_requested", reason=reason, scope="campaign",
                failure_class=(details.get("failure") or {}).get("class"))
```

In `failures.stop_for`, inside the loop where a marker is written:

```python
        if not marker.exists():
            marker.write_text(json.dumps(record))
            from . import events
            events.emit(campaign, "stop_requested", reason=reason, failure_class=failure.cls,
                        scope="campaign" if root == Path(campaign.root) else "parent")
```

- [ ] **Step 4: Run and see them pass, then the stage suites**

Run: `uv run --offline --locked pytest -q tests/test_events.py tests/test_transport.py tests/test_edit.py tests/test_paper.py tests/test_stub_flow.py tests/test_admission.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/events.py pathfinder/transport.py pathfinder/research.py pathfinder/edit.py pathfinder/paper.py pathfinder/runner.py pathfinder/failures.py tests/test_events.py
git commit -m "Emit call, transition and stop events from the stages

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Execution identifier and run events

**Files:**
- Modify: `pathfinder/provenance.py` (`start`, new `execution_id`)
- Test: `tests/test_freeze_provenance.py`

**Interfaces:**
- Consumes: `provenance.components(rec)`, `events.emit`.
- Produces: `provenance.execution_id(record: dict) -> str` (sha256 of the sorted JSON of `components(record)`); `run.json` key `execution_id`; event `run_started` with `execution_id`, `previous_run_id`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_freeze_provenance.py
def test_execution_id_follows_the_running_bytes_not_the_commit():
    from pathfinder import provenance
    rec = {"engine": {"kind": "checkout", "runtime_sha256": "a" * 64}, "config": {"sha256": "c"}}
    same = {"engine": {"kind": "checkout", "runtime_sha256": "a" * 64, "commit": "different"}, "config": {"sha256": "c"}}
    dirty = {"engine": {"kind": "checkout", "runtime_sha256": "b" * 64}, "config": {"sha256": "c"}}
    assert provenance.execution_id(rec) == provenance.execution_id(same)
    assert provenance.execution_id(rec) != provenance.execution_id(dirty)


def test_a_run_record_carries_its_execution_id_and_emits_run_started(tmp_path):
    from pathfinder import events, provenance
    from stubcampaign import make
    c = make(tmp_path)
    rec, _ = provenance.start(c, "run-1")
    assert rec["execution_id"] == provenance.execution_id(rec)
    started = [r for r in events.read(c)[0] if r["kind"] == "run_started"]
    assert started[-1]["execution_id"] == rec["execution_id"]
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_freeze_provenance.py -k execution`
Expected: FAIL with `AttributeError: module 'pathfinder.provenance' has no attribute 'execution_id'`.

- [ ] **Step 3: Implement**

Add after `components` in `pathfinder/provenance.py`:

```python
def execution_id(rec: dict) -> str:
    """One identifier for what actually ran: the runtime bytes (uncommitted changes included), the
    deployment, extensions, configuration, prompts and styles. Two runs from one commit with different
    working files differ; a commit id alone is not used."""
    return _sha(json.dumps(components(rec), sort_keys=True, default=str).encode())
```

In `start`, just before `path.write_text(json.dumps(current, indent=1))`:

```python
    current["execution_id"] = execution_id(current)
```

and after the `runs.jsonl` append:

```python
    from . import events
    events.emit(campaign, "run_started", execution_id=current["execution_id"],
                previous_run_id=current.get("previous_run_id"))
```

- [ ] **Step 4: Run and see them pass, then the provenance and runner suites**

Run: `uv run --offline --locked pytest -q tests/test_freeze_provenance.py tests/test_runner.py tests/test_coordinator.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/provenance.py tests/test_freeze_provenance.py
git commit -m "Execution identifier over the running bytes; run_started events

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Campaign state document

**Files:**
- Create: `pathfinder/campaign_state.py`
- Test: `tests/test_campaign_state.py`

**Interfaces:**
- Consumes: `events.read`, `research.status`, `edit.status`, `paper.status`, `transport.receipts`, `campaign.path("scan.jsonl")`, `shortlist.json`, `run.json`, `stop.json`, `active-calls/*.json`.
- Produces: `campaign_state.build(campaign) -> dict` and `campaign_state.write(campaign) -> Path` (atomic `state.json`). Document keys: `generated_at`, `campaign` (`name`, `backend`, `model`, `seats`, `rounds`, `allowances`, `research_scheme`, `budget` {`calls`, `input_tokens`, `output_tokens`, `cache_read`}, `execution_id`, `stop`), `progress` (`status`: `active`, `idle` or `unknown`; `last_event_at`; `events_truncated`), `stages` ({stage: {state: count}} for `research`, `edit`, `paper`), `blocks` (list of {`class`, `cause`, `units`, `count`}), `units` (list of {`unit`, `score`, `research`, `editorial`, `assessment`, `controller`, `last_activity`, `documents`}).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_campaign_state.py
import json, os, time
from pathfinder import campaign_state, edit, events, research
from stubcampaign import make


def test_states_are_separated_per_axis(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    edit._set(c, "Q1P1", status="blocked", reason="editor wrote no note.tex")
    unit = campaign_state.build(c)["units"][0]
    assert unit["research"]["status"] == research.status(c, "Q1P1")["status"]
    assert unit["editorial"] == {"status": "blocked", "reason": "editor wrote no note.tex"}
    assert unit["assessment"]["status"] is None
    assert unit["controller"] == "blocked"


def test_stage_counts_and_blocks(tmp_path):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    research._set(c, "Q1P1", status="BLOCKED", reason="consolidate: input too large: 1200 characters exceed 10")
    research._set(c, "Q1P2", status="DRAFT")
    s = campaign_state.build(c)
    assert s["stages"]["research"] == {"BLOCKED": 1, "DRAFT": 1}
    assert s["blocks"][0]["units"] == ["Q1P1"] and s["blocks"][0]["class"] == "input_too_large"


def test_budget_is_in_tokens_and_calls(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    budget = campaign_state.build(c)["campaign"]["budget"]
    assert budget["calls"] > 0 and budget["input_tokens"] == 0     # the stub reports zero tokens


def test_truncated_events_mean_unknown_progress(tmp_path):
    c = make(tmp_path)
    events.emit(c, "run_started", execution_id="e")
    with c.path("events.jsonl").open("a") as f:
        f.write('{"v": 1, "kind": "call_')
    assert campaign_state.build(c)["progress"]["status"] == "unknown"


def test_a_pdf_older_than_its_source_is_stale(tmp_path):
    c = make(tmp_path)
    ed = c.thread_dir("Q1P1") / "edited"; ed.mkdir(parents=True)
    (ed / "note.pdf").write_bytes(b"%PDF"); (ed / "note.tex").write_text("x")
    old = time.time() - 100
    os.utime(ed / "note.pdf", (old, old))
    docs = {d["kind"]: d for d in campaign_state.build(c)["units"][0]["documents"]}
    assert docs["readable note"]["pdf"] == "threads/Q1P1/edited/note.pdf"
    assert docs["readable note"]["source"] == "threads/Q1P1/edited/note.tex"
    assert docs["readable note"]["stale"] is True


def test_scores_come_from_the_scan(tmp_path):
    c = make(tmp_path)
    c.path("scan.jsonl").write_text(json.dumps({"pair_id": "Q1P1", "feasibility": 7, "gain": 6}) + "\n")
    assert campaign_state.build(c)["units"][0]["score"] == 42


def test_write_is_atomic_json(tmp_path):
    c = make(tmp_path)
    path = campaign_state.write(c)
    assert json.loads(path.read_text())["campaign"]["name"] == tmp_path.name
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_campaign_state.py`
Expected: FAIL with `ImportError: cannot import name 'campaign_state'`.

- [ ] **Step 3: Implement**

```python
# pathfinder/campaign_state.py
"""The campaign state document: what the operator's page and the apex agent read.

Derived, never authoritative: status files say where each unit stands, receipts what was spent, events
when things happened. Research, editorial and assessment states stay separate, so "DRAFT" research with
a blocked edit reads as both. A cut event stream makes progress "unknown" rather than inferred."""
from __future__ import annotations
import json, os, re, time
from collections import Counter
from pathlib import Path
from . import edit, events, paper, research, transport

ACTIVE_SECONDS = 600                       # an event this recent means the campaign is active
DOCUMENTS = (("research note", "{u}.tex", "{u}.pdf"), ("readable note", "edited/note.tex", "edited/note.pdf"),
             ("paper", "paper/paper.tex", "paper/paper.pdf"))
CLASS_IN_REASON = re.compile(r"input too large|usage limit|unauthori[sz]ed|flagged for possible", re.I)


def _json(path: Path):
    try:
        return json.loads(path.read_text()) if path.is_file() else None
    except (ValueError, OSError):
        return None


def _scores(campaign) -> dict:
    out = {}
    path = campaign.path("scan.jsonl")
    for line in (path.read_text().splitlines() if path.is_file() else []):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("feasibility") is not None and row.get("gain") is not None:
            out[row["pair_id"]] = row["feasibility"] * row["gain"]
    return out


def _documents(campaign, unit: str) -> list[dict]:
    d, out = campaign.thread_dir(unit), []
    for kind, source, pdf in DOCUMENTS:
        src, out_pdf = d / source.format(u=unit), d / pdf.format(u=unit)
        if not src.is_file() and not out_pdf.is_file():
            continue
        rel = lambda p: str(p.relative_to(campaign.root)) if p.is_file() else None
        stale = bool(src.is_file() and out_pdf.is_file() and out_pdf.stat().st_mtime < src.stat().st_mtime)
        out.append({"kind": kind, "pdf": rel(out_pdf), "source": rel(src), "stale": stale})
    return out


def _block_class(reason: str | None) -> str:
    from . import failures
    found = failures.classify("error", reason or "")
    return found.cls if found and found.cls != "undiagnosed" else "contract" if reason else "undiagnosed"


def _controller(research_s: dict, edit_s: dict, paper_s: dict, active: set, unit: str) -> str:
    if unit in active:
        return "running"
    states = (research_s.get("status"), edit_s.get("status"), paper_s.get("status"))
    if "BLOCKED" in states or "blocked" in states:
        return "blocked"
    if "stopped" in states:
        return "stopped"
    if research_s.get("status") in research.TERMINAL and edit_s.get("status") == "done":
        return "done"
    return "waiting"


def build(campaign) -> dict:
    rows, truncated = events.read(campaign)
    receipts = transport.receipts(campaign)
    shortlist = (_json(campaign.path("shortlist.json")) or {}).get("pairs", [])
    scores = _scores(campaign)
    active = set()
    for path in sorted(campaign.path("active-calls").glob("*.json")) if campaign.path("active-calls").is_dir() else []:
        call = _json(path) or {}
        if call.get("thread"):
            active.add(call["thread"])
    last_by_unit = {}
    for row in rows:
        if row.get("unit"):
            last_by_unit[row["unit"]] = row.get("at")
    units, stages, blocks = [], {"research": Counter(), "edit": Counter(), "paper": Counter()}, {}
    for pair in shortlist:
        unit = pair["pair_id"]
        r_s = research.status(campaign, unit)
        d = campaign.thread_dir(unit)
        e_s = edit.status(campaign, unit) if (d / "edited" / "edit.json").exists() else {}
        p_s = paper.status(campaign, unit) if (d / "paper" / "paper.json").exists() else {}
        stages["research"][r_s.get("status", "new")] += 1
        if e_s:
            stages["edit"][e_s.get("status")] += 1
        if p_s:
            stages["paper"][p_s.get("status")] += 1
        for status_doc in (r_s, e_s, p_s):
            if status_doc.get("status") in ("BLOCKED", "blocked"):
                reason = status_doc.get("reason") or ""
                key = (_block_class(reason), reason.split(":")[0] if ":" in reason else reason)
                blocks.setdefault(key, []).append(unit)
        units.append({"unit": unit, "score": scores.get(unit),
                      "research": {k: r_s.get(k) for k in ("status", "stage", "round", "reason")},
                      "editorial": {"status": e_s.get("status"), "reason": e_s.get("reason")},
                      "assessment": {"status": p_s.get("status"), "reason": p_s.get("reason")},
                      "controller": _controller(r_s, e_s, p_s, active, unit),
                      "last_activity": last_by_unit.get(unit), "documents": _documents(campaign, unit)})
    last = rows[-1]["at"] if rows else None
    age = (time.time() - time.mktime(time.strptime(last, "%Y-%m-%dT%H:%M:%SZ")) + time.timezone) if last else None
    progress = "unknown" if truncated else "active" if (active or (age is not None and age < ACTIVE_SECONDS)) else "idle"
    run = _json(campaign.path("run.json")) or {}
    raw = campaign.raw or {}
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "campaign": {"name": campaign.root.name, "backend": campaign.backend, "model": campaign.model,
                     "seats": campaign.seats, "rounds": campaign.rounds, "allowances": campaign.allowances,
                     "research_scheme": raw.get("research_scheme", "eva"),
                     "budget": {"calls": len(receipts),
                                "input_tokens": sum(r.get("input_tokens") or 0 for r in receipts),
                                "output_tokens": sum(r.get("output_tokens") or 0 for r in receipts),
                                "cache_read": sum(r.get("cache_read") or 0 for r in receipts)},
                     "execution_id": run.get("execution_id"), "stop": _json(campaign.path("stop.json"))},
        "progress": {"status": progress, "last_event_at": last, "events_truncated": truncated},
        "stages": {name: dict(counts) for name, counts in stages.items()},
        "blocks": [{"class": cls, "cause": cause, "units": sorted(set(us)), "count": len(us)}
                   for (cls, cause), us in sorted(blocks.items(), key=lambda kv: -len(kv[1]))],
        "units": units,
    }


def write(campaign) -> Path:
    path = campaign.path("state.json")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(build(campaign), indent=1, default=str))
    os.replace(temporary, path)
    return path
```

If `research.status` for an unstarted unit has no `status` key, `stages["research"]` counts it as `new`; if a test fixture's paths differ from `DOCUMENTS` (check `edit.py` writes `edited/note.tex` and `paper.py` writes `paper/paper.tex`), fix `DOCUMENTS`, not the test.

- [ ] **Step 4: Run and see them pass**

Run: `uv run --offline --locked pytest -q tests/test_campaign_state.py`
Expected: 7 passed. The age computation uses UTC parsing; if it fails on the machine's timezone, replace it with `calendar.timegm(time.strptime(last, "%Y-%m-%dT%H:%M:%SZ"))` and `time.time() - that`, and ledger the ruling.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/campaign_state.py tests/test_campaign_state.py
git commit -m "Campaign state document with separated unit states, stage counts, blocks and token budget

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `pathfinder state` command, state.json kept fresh by the runner

**Files:**
- Modify: `pathfinder/cli.py` (new subcommand), `pathfinder/runner.py` (write `state.json` at each heartbeat)
- Test: `tests/test_campaign_state.py`

**Interfaces:**
- Consumes: `campaign_state.build`, `campaign_state.write` (Task 4).
- Produces: `pathfinder state [--json]`; `campaign_state.text(state: dict) -> str`; the runner rewrites `state.json` wherever it writes `runner.json` heartbeats (`health.write(campaign.path("runner.json"), metadata)`).

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_campaign_state.py
def test_text_view_names_unknown_progress_and_blocks(tmp_path):
    c = make(tmp_path)
    research._set(c, "Q1P1", status="BLOCKED", reason="consolidate: input too large: 12 characters exceed 10")
    events.emit(c, "run_started")
    with c.path("events.jsonl").open("a") as f:
        f.write("{")
    out = campaign_state.text(campaign_state.build(c))
    assert "progress unknown" in out and "input_too_large" in out and "Q1P1" in out


def test_cli_state_json(tmp_path, capsys):
    from pathfinder import cli
    make(tmp_path)
    assert cli.main(["--root", str(tmp_path), "state", "--json"]) in (0, None)
    assert json.loads(capsys.readouterr().out)["campaign"]["name"] == tmp_path.name
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_campaign_state.py -k "text_view or cli_state"`
Expected: FAIL (`text` missing; argparse rejects `state`).

- [ ] **Step 3: Implement**

Append to `pathfinder/campaign_state.py`:

```python
def text(state: dict) -> str:
    c, p = state["campaign"], state["progress"]
    lines = [f"{c['name']}  {c['backend']}/{c['model']}  scheme {c['research_scheme']}  execution {str(c['execution_id'])[:12]}",
             f"progress {p['status']}" + (f"  last event {p['last_event_at']}" if p["last_event_at"] else "")
             + ("  (event stream cut: read the full record before trusting progress)" if p["events_truncated"] else ""),
             f"budget {c['budget']['calls']} calls, {c['budget']['input_tokens']} input tokens "
             f"({c['budget']['cache_read']} cached), {c['budget']['output_tokens']} output",
             "stages " + "; ".join(f"{name}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
                                    for name, counts in state["stages"].items() if counts)]
    if c["stop"]:
        lines.append(f"stopped: {c['stop'].get('reason')}")
    for block in state["blocks"]:
        lines.append(f"block {block['class']}: {block['cause']} x{block['count']} ({', '.join(block['units'])})")
    for u in state["units"]:
        lines.append(f"{u['unit']:>8} score {u['score'] if u['score'] is not None else '-':>4}  {u['controller']:<8} "
                     f"research {u['research']['status']}  edit {u['editorial']['status']}  paper {u['assessment']['status']}")
    return "\n".join(lines)
```

In `pathfinder/cli.py`, add the parser next to `status`:

```python
    sub.add_parser("state", help="the campaign state document: unit states, stage counts, blocks, token budget").add_argument("--json", action="store_true")
```

and the dispatch branch next to `status`:

```python
    elif ns.cmd == "state":
        from . import campaign_state
        doc = campaign_state.build(c)
        print(json.dumps(doc, indent=1, default=str) if ns.json else campaign_state.text(doc))
```

Check how `c` (the loaded campaign) is named in `cli.main` before the dispatch chain and use that name. If `state` must not open a run record, make sure it is not in `DISPATCHING`.

In `pathfinder/runner.py`, after each `health.write(campaign.path("runner.json"), metadata)` add:

```python
        try:
            from . import campaign_state
            campaign_state.write(campaign)
        except Exception as error:                  # the state document must never stop a run
            print(f"{_now()} state.json not written: {error!r}")
```

- [ ] **Step 4: Run and see them pass, then the runner and CLI suites**

Run: `uv run --offline --locked pytest -q tests/test_campaign_state.py tests/test_runner.py tests/test_bounded.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/campaign_state.py pathfinder/cli.py pathfinder/runner.py tests/test_campaign_state.py
git commit -m "pathfinder state, and state.json kept fresh by the runner

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Full verification and spec

- [ ] **Step 1:** `uv run --offline --locked pytest -q` (expect baseline: only the statarb deployment test fails) and `uv run --offline --locked behave --tags="not @sandbox and not @captain and not @shipwright"` (expect 93 passed, 1 failed, 9 error, as on main).
- [ ] **Step 2:** In `notes/pathfinder-friction.tex`, append to H4 and to the F09, F10 and R04 rows "Done in phase 2a (commits ...)", rebuild with `latexmk -pdf -interaction=nonstopmode pathfinder-friction.tex` in `notes/`, run `/Users/v/.local/bin/style-ban-artifacts notes/pathfinder-friction.tex`.
- [ ] **Step 3:** Commit:

```bash
git add notes/pathfinder-friction.tex notes/pathfinder-friction.pdf
git commit -m "Phase 2a complete: events, execution identifier, campaign state

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

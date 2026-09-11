# Pathfinder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A minimal, file-based pipeline that scans every (q, p) pair of two paper corpora, shortlists the top cut, and develops each shortlisted pair with two peer agents and a verifier into a ledger, a verdict and a LaTeX note, with a budget guard, graceful stops, a reconcile command and a live local monitor.

**Architecture:** One Python package, standard library only, state in plain files under a campaign directory. Model calls are subprocesses to the Claude Code CLI or the Codex CLI behind one adapter that streams JSON lines, so a session id arrives early and a dead transport is detected fast. The runner is a loop in one terminal with a thread pool of seats; every stop is a drain.

**Tech Stack:** Python 3.12, uv, `claude` and `codex` CLIs, `latexpand`, `pdftotext`, `pytest` as the only dev dependency.

**Spec:** `plans/2026-09-11-pathfinder-design.md`

## Global Constraints

- Python 3.12, standard library only at runtime; `pytest` for tests.
- British English in prose and prompts; no em dash character in any generated `.md`, `.html` or `.tex`.
- State lives in the campaign directory; nothing is held only in memory that a restart would need.
- No model or backend fallback: a failure stops admissions, it never substitutes.
- Every model call appends one receipt line; spend is always the sum of receipts.
- Terminal thread statuses are exactly `DRAFT`, `PAUSE`, `PAUSE-ON-ITERATE`; `BLOCKED` is a machinery state.
- Keep it simple. This is an experiment. Do not add configuration, abstraction or ceremony beyond what a task names.

---

## File structure

    pathfinder/
      pyproject.toml
      README.md
      campaign.json                reference campaign config, repo root is the campaign dir
      prompts/{scan,peer,consolidate,verify}.md   already committed
      pathfinder/
        __init__.py
        config.py      load campaign.json, resolve paths, price table
        ledger.py      append-only attributed ledger, file lock, helper CLI
        transport.py   call() over claude or codex, streaming parse, receipts
        corpus.py      arXiv fetch, e-print download, latexpand, pdftotext
        scan.py        phase A, row-wise, resumable
        select.py      cut and freeze the shortlist
        research.py    one thread: peers, consolidate, verify, rounds
        runner.py      seats, admission, guard, stop, health, drain
        reconcile.py   inspect one thread, one safe action
        monitor.py     state(), status(), serve()
        cli.py         argparse entry point
      tests/
        fake_cli.py    a fake claude/codex binary driven by env vars
        test_ledger.py test_select.py test_transport.py test_research.py test_runner.py

Campaign directory layout (the repo root for the reference run):

    campaign.json  Q.jsonl  P.jsonl  sources/  scan.jsonl  shortlist.json
    receipts.jsonl  stop.json  health.json  threads/<pair_id>/...

---

### Task 1: Scaffold and config

**Files:**
- Create: `pyproject.toml`, `pathfinder/__init__.py`, `pathfinder/config.py`, `campaign.json`, `tests/test_config.py`, `.gitignore`

**Interfaces:**
- Produces: `config.load(root: Path) -> Campaign` where `Campaign` is a dataclass with fields `root, backend, model, scan_model, peer_search, seats, cut, rounds, allowances (dict), budget_usd, prices (dict), scan_fulltext, call_estimate_usd` and helpers `path(name) -> Path`, `thread_dir(pair_id) -> Path`, `price(model, input_tokens, output_tokens) -> float`.

- [ ] **Step 1: Write pyproject and gitignore**

```toml
[project]
name = "pathfinder"
version = "0.1.0"
description = "Scan every pair of two paper corpora, research the shortlist with peer agents"
requires-python = ">=3.12"
dependencies = []

[project.scripts]
pathfinder = "pathfinder.cli:main"

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["pathfinder"]
```

`.gitignore`:

```
.venv/
__pycache__/
sources/
threads/*/lock
*.pyc
```

- [ ] **Step 2: Write campaign.json**

```json
{
  "backend": "claude",
  "model": "claude-opus-5",
  "scan_model": "claude-sonnet-5",
  "peer_search": true,
  "seats": 4,
  "cut": 12,
  "rounds": 3,
  "allowances": {"peer_seconds": 1800, "peer_calls": 3, "consolidate_seconds": 600, "verify_seconds": 600},
  "budget_usd": 60,
  "call_estimate_usd": 2.0,
  "prices": {
    "claude-opus-5": {"input_per_m": 15.0, "output_per_m": 75.0},
    "claude-sonnet-5": {"input_per_m": 3.0, "output_per_m": 15.0},
    "gpt-5.6-sol": {"input_per_m": 2.0, "output_per_m": 8.0}
  },
  "scan": {"fulltext": null}
}
```

- [ ] **Step 3: Write the failing test**

```python
# tests/test_config.py
import json
from pathlib import Path
from pathfinder.config import load

def test_load_reads_campaign_and_prices(tmp_path: Path):
    (tmp_path / "campaign.json").write_text(json.dumps({
        "backend": "claude", "model": "m", "seats": 2, "cut": 1, "rounds": 3,
        "allowances": {"peer_seconds": 10, "peer_calls": 1, "consolidate_seconds": 5, "verify_seconds": 5},
        "budget_usd": 1.0, "prices": {"m": {"input_per_m": 1.0, "output_per_m": 2.0}}}))
    c = load(tmp_path)
    assert c.seats == 2 and c.scan_model == "m" and c.peer_search is True
    assert c.price("m", 1_000_000, 500_000) == 2.0
    assert c.thread_dir("Q1P2") == tmp_path / "threads" / "Q1P2"
```

- [ ] **Step 4: Run it, expect ImportError**

Run: `uv run pytest tests/test_config.py -q`

- [ ] **Step 5: Implement config.py**

```python
"""Campaign configuration: one JSON file at the campaign root."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Campaign:
    root: Path
    backend: str
    model: str
    scan_model: str
    peer_search: bool
    seats: int
    cut: float
    rounds: int
    allowances: dict
    budget_usd: float
    prices: dict
    scan_fulltext: str | None
    call_estimate_usd: float = 2.0
    raw: dict = field(default_factory=dict)

    def path(self, name: str) -> Path:
        return self.root / name

    def thread_dir(self, pair_id: str) -> Path:
        return self.root / "threads" / pair_id

    def price(self, model: str, input_tokens: int, output_tokens: int) -> float:
        p = self.prices.get(model)
        if not p:
            return 0.0
        return input_tokens / 1e6 * p["input_per_m"] + output_tokens / 1e6 * p["output_per_m"]

def load(root: Path) -> Campaign:
    root = Path(root).resolve()
    raw = json.loads((root / "campaign.json").read_text())
    return Campaign(
        root=root, backend=raw["backend"], model=raw["model"],
        scan_model=raw.get("scan_model") or raw["model"],
        peer_search=raw.get("peer_search", True), seats=raw.get("seats", 4),
        cut=raw.get("cut", 1), rounds=raw.get("rounds", 3), allowances=raw["allowances"],
        budget_usd=raw["budget_usd"], prices=raw.get("prices", {}),
        scan_fulltext=(raw.get("scan") or {}).get("fulltext"),
        call_estimate_usd=raw.get("call_estimate_usd", 2.0), raw=raw)
```

- [ ] **Step 6: Run, expect pass, commit**

Run: `uv sync && uv run pytest -q`
Commit: `git add -A && git commit -m "Scaffold the package and campaign config"`

---

### Task 2: Ledger

**Files:**
- Create: `pathfinder/ledger.py`, `tests/test_ledger.py`

**Interfaces:**
- Produces: `Ledger(path: Path)` with `add(actor, kind, text, supersedes=None, seen=None) -> int`, `read(since: int = 0) -> list[dict]`, `latest_substantive() -> int`, `ready(actors: list[str]) -> bool`, `count() -> int`. Entries are dicts `{seq, at, actor, kind, text, supersedes, seen}`. Kinds: idea, finding, objection, correction, intention, ready, review. `ready` and `review` are not substantive. Module is runnable: `python -m pathfinder.ledger --root DIR --actor NAME read|add --kind K --text T [--supersedes N]|ready --seen N`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ledger.py
import subprocess, sys
from pathfinder.ledger import Ledger

def test_add_read_and_readiness(tmp_path):
    l = Ledger(tmp_path / "ledger.jsonl")
    assert l.add("ada", "idea", "first") == 1
    assert l.add("emmy", "finding", "second") == 2
    assert [e["seq"] for e in l.read(since=1)] == [2]
    assert l.latest_substantive() == 2
    l.add("ada", "ready", "done", seen=2)
    assert not l.ready(["ada", "emmy"])
    l.add("emmy", "ready", "done", seen=2)
    assert l.ready(["ada", "emmy"])
    l.add("emmy", "objection", "wait")          # reopens
    assert not l.ready(["ada", "emmy"])

def test_stale_ready_does_not_count(tmp_path):
    l = Ledger(tmp_path / "ledger.jsonl")
    l.add("ada", "idea", "x")
    l.add("ada", "ready", "ok", seen=0)         # saw nothing
    l.add("emmy", "ready", "ok", seen=1)
    assert not l.ready(["ada", "emmy"])

def test_cli_roundtrip(tmp_path):
    cmd = [sys.executable, "-m", "pathfinder.ledger", "--root", str(tmp_path), "--actor", "ada"]
    subprocess.run(cmd + ["add", "--kind", "idea", "--text", "hello"], check=True)
    out = subprocess.run(cmd + ["read"], check=True, capture_output=True, text=True).stdout
    assert "hello" in out and "#1" in out
```

- [ ] **Step 2: Run, expect failure**

Run: `uv run pytest tests/test_ledger.py -q`

- [ ] **Step 3: Implement ledger.py**

```python
"""Append-only attributed ledger shared by the two peers of a thread."""
from __future__ import annotations
import argparse, fcntl, json, sys, time
from pathlib import Path

SUBSTANTIVE = {"idea", "finding", "objection", "correction", "intention"}
KINDS = SUBSTANTIVE | {"ready", "review"}

class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        f = open(self.path.with_suffix(".lock"), "w")
        fcntl.flock(f, fcntl.LOCK_EX)
        return f

    def read(self, since: int = 0) -> list[dict]:
        if not self.path.exists():
            return []
        rows = [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()]
        return [r for r in rows if r["seq"] > since]

    def count(self) -> int:
        return len(self.read())

    def add(self, actor: str, kind: str, text: str, supersedes: int | None = None, seen: int | None = None) -> int:
        if kind not in KINDS:
            raise ValueError(f"unknown kind {kind}")
        with self._lock():
            seq = self.count() + 1
            row = {"seq": seq, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "actor": actor,
                   "kind": kind, "text": text, "supersedes": supersedes, "seen": seen}
            with open(self.path, "a") as f:
                f.write(json.dumps(row) + "\n")
        return seq

    def latest_substantive(self) -> int:
        return max((r["seq"] for r in self.read() if r["kind"] in SUBSTANTIVE), default=0)

    def ready(self, actors: list[str]) -> bool:
        rows, latest = self.read(), self.latest_substantive()
        for a in actors:
            last = next((r for r in reversed(rows) if r["actor"] == a and r["kind"] == "ready"), None)
            if not last or last["seq"] < latest or (last.get("seen") or 0) < latest:
                return False
        return True

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True); ap.add_argument("--actor", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("read").add_argument("--since", type=int, default=0)
    a = sub.add_parser("add"); a.add_argument("--kind", required=True); a.add_argument("--text", required=True)
    a.add_argument("--supersedes", type=int)
    sub.add_parser("ready").add_argument("--seen", type=int, required=True)
    ns = ap.parse_args(argv)
    l = Ledger(Path(ns.root) / "ledger.jsonl")
    if ns.cmd == "read":
        for r in l.read(ns.since):
            sup = f" supersedes #{r['supersedes']}" if r.get("supersedes") else ""
            print(f"#{r['seq']} [{r['actor']}/{r['kind']}{sup}] {r['text']}")
        print(f"latest substantive entry: {l.latest_substantive()}")
    elif ns.cmd == "add":
        print(l.add(ns.actor, ns.kind, ns.text, ns.supersedes))
    else:
        print(l.add(ns.actor, "ready", f"ready at #{ns.seen}", seen=ns.seen))

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run, expect pass, commit**

Commit: `git add -A && git commit -m "Add the shared ledger and its helper"`

---

### Task 3: Transport

**Files:**
- Create: `pathfinder/transport.py`, `tests/fake_cli.py`, `tests/test_transport.py`

**Interfaces:**
- Produces: `call(prompt: str, *, campaign, model: str, tools: bool, search: bool, cwd: Path, timeout: int, thread: str, stage: str, actor: str) -> dict` returning `{text, session, seconds, input_tokens, output_tokens, cost, error, transport_failed}`. Appends one line to `<root>/receipts.jsonl` unless `transport_failed`. Binary names come from env `PATHFINDER_CLAUDE` / `PATHFINDER_CODEX` (default `claude`, `codex`) so tests can substitute the fake. `SESSION_GRACE = 60`.
- Produces: `spend(campaign) -> float` summing receipt costs.

- [ ] **Step 1: Write the fake CLI**

```python
# tests/fake_cli.py
"""Fake claude/codex binary. Env FAKE_MODE: claude|codex. FAKE_REPLY: text to return.
FAKE_DELAY: seconds before the session line. FAKE_HANG=1: never print a session line.
FAKE_RUN: a shell command to run (in cwd) before replying, so tests can make it write files."""
import json, os, subprocess, sys, time
mode, reply = os.environ.get("FAKE_MODE", "claude"), os.environ.get("FAKE_REPLY", "ok")
sys.stdin.read()
if os.environ.get("FAKE_HANG"):
    time.sleep(3600)
time.sleep(float(os.environ.get("FAKE_DELAY", "0")))
if mode == "claude":
    print(json.dumps({"type": "system", "subtype": "init", "session_id": "fake-session"}), flush=True)
else:
    print(json.dumps({"type": "thread.started", "thread_id": "fake-thread"}), flush=True)
if os.environ.get("FAKE_RUN"):
    subprocess.run(os.environ["FAKE_RUN"], shell=True, check=True)
if mode == "claude":
    print(json.dumps({"type": "result", "subtype": "success", "result": reply, "session_id": "fake-session",
                      "total_cost_usd": 0.5, "usage": {"input_tokens": 100, "output_tokens": 10}}))
else:
    print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": reply}}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 10}}))
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_transport.py
import json, os, sys
from pathlib import Path
import pytest
from pathfinder import transport
from pathfinder.config import Campaign

FAKE = str(Path(__file__).parent / "fake_cli.py")

def campaign(tmp_path, backend="claude"):
    return Campaign(root=tmp_path, backend=backend, model="m", scan_model="m", peer_search=True, seats=1,
                    cut=1, rounds=1, allowances={}, budget_usd=9, prices={"m": {"input_per_m": 1.0, "output_per_m": 1.0}},
                    scan_fulltext=None)

@pytest.fixture(autouse=True)
def fake(monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", f"{sys.executable} {FAKE}")
    monkeypatch.setenv("PATHFINDER_CODEX", f"{sys.executable} {FAKE}")
    monkeypatch.setattr(transport, "SESSION_GRACE", 1)

def test_claude_call_returns_text_and_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "claude"); monkeypatch.setenv("FAKE_REPLY", "hello")
    r = transport.call("p", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="scan", actor="judge")
    assert r["text"] == "hello" and r["session"] == "fake-session" and r["cost"] == 0.5
    rows = [json.loads(l) for l in (tmp_path / "receipts.jsonl").read_text().splitlines()]
    assert rows[0]["stage"] == "scan" and transport.spend(campaign(tmp_path)) == 0.5

def test_codex_call_prices_from_table(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "codex"); monkeypatch.setenv("FAKE_REPLY", "hi")
    r = transport.call("p", campaign=campaign(tmp_path, "codex"), model="m", tools=True, search=True, cwd=tmp_path,
                       timeout=10, thread="T", stage="peer", actor="ada")
    assert r["text"] == "hi" and abs(r["cost"] - 110 / 1e6) < 1e-9

def test_no_session_is_transport_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_HANG", "1")
    r = transport.call("p", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="scan", actor="judge")
    assert r["transport_failed"] and r["cost"] == 0 and not (tmp_path / "receipts.jsonl").exists()

def test_timeout_after_session_is_an_error_not_transport(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_DELAY", "0"); monkeypatch.setenv("FAKE_RUN", "sleep 3")
    r = transport.call("p", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=1, thread="T", stage="scan", actor="judge")
    assert r["error"] == "timeout" and not r["transport_failed"]
```

- [ ] **Step 3: Run, expect failure**

Run: `uv run pytest tests/test_transport.py -q`

- [ ] **Step 4: Implement transport.py**

```python
"""One adapter over the Claude Code CLI and the Codex CLI. Streams JSON lines so the
session id arrives early; a call with no session within SESSION_GRACE is a transport failure."""
from __future__ import annotations
import json, os, shlex, signal, subprocess, threading, time
from pathlib import Path

SESSION_GRACE = 60
SCRUB = ("API_KEY", "OPENAI_", "ANTHROPIC_API", "ELM_")
CLAUDE_TOOLS = "Read,Write,Edit,Bash,Glob,Grep"

def _env():
    return {k: v for k, v in os.environ.items() if not any(s in k for s in SCRUB)}

def _command(campaign, model, tools, search, cwd):
    if campaign.backend == "claude":
        cmd = shlex.split(os.environ.get("PATHFINDER_CLAUDE", "claude"))
        cmd += ["-p", "--model", model, "--output-format", "stream-json", "--verbose", "--no-session-persistence"]
        if tools:
            cmd += ["--tools", CLAUDE_TOOLS + (",WebSearch,WebFetch" if search else ""),
                    "--dangerously-skip-permissions"]
        else:
            cmd += ["--tools", "", "--permission-prompts", "none"]
        return cmd
    cmd = shlex.split(os.environ.get("PATHFINDER_CODEX", "codex"))
    cmd += ["exec", "--json", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
            "--cd", str(cwd), "--model", model, "-c", 'approval_policy="never"',
            "--sandbox", "workspace-write" if tools else "read-only",
            "-c", f'web_search="{"live" if (tools and search) else "disabled"}"', "-"]
    return cmd

def _parse(campaign, model, lines):
    text, session, inp, out, cost, err = "", None, 0, 0, None, None
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = row.get("type")
        if t == "system" and row.get("session_id"):
            session = row["session_id"]
        elif t == "thread.started":
            session = row.get("thread_id")
        elif t == "result":
            text = row.get("result") or ""
            u = row.get("usage") or {}
            inp, out = u.get("input_tokens", 0), u.get("output_tokens", 0)
            cost = row.get("total_cost_usd")
            if row.get("is_error"):
                err = text or "error"
        elif t == "item.completed" and (row.get("item") or {}).get("type") == "agent_message":
            text = row["item"].get("text", "")
        elif t == "turn.completed":
            u = row.get("usage") or {}
            inp, out = u.get("input_tokens", 0), u.get("output_tokens", 0)
        elif t in ("error", "turn.failed"):
            err = str(row.get("error") or row.get("message") or t)
    if cost is None:
        cost = campaign.price(model, inp, out)
    return text, session, inp, out, cost, err

def call(prompt, *, campaign, model, tools, search, cwd, timeout, thread, stage, actor):
    cwd = Path(cwd); cwd.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(_command(campaign, model, tools, search, cwd), cwd=cwd, env=_env(),
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    lines, session_seen = [], threading.Event()
    def reader():
        for line in proc.stdout:
            lines.append(line)
            if '"session_id"' in line or '"thread.started"' in line:
                session_seen.set()
    t = threading.Thread(target=reader, daemon=True); t.start()
    try:
        proc.stdin.write(prompt); proc.stdin.close()
    except BrokenPipeError:
        pass
    started = time.time()
    if not session_seen.wait(SESSION_GRACE):
        _kill(proc)
        return {"text": "", "session": None, "seconds": round(time.time() - started, 1), "input_tokens": 0,
                "output_tokens": 0, "cost": 0.0, "error": "no session", "transport_failed": True}
    try:
        proc.wait(timeout=max(1, timeout - (time.time() - started)))
        error = None
    except subprocess.TimeoutExpired:
        _kill(proc); error = "timeout"
    t.join(5)
    text, session, inp, out, cost, err = _parse(campaign, model, lines)
    if proc.returncode not in (0, None) and not error and not err:
        err = (proc.stderr.read() or "").strip()[-500:] or f"exit {proc.returncode}"
    r = {"text": text, "session": session, "seconds": round(time.time() - started, 1), "input_tokens": inp,
         "output_tokens": out, "cost": float(cost or 0), "error": error or err, "transport_failed": False}
    with open(campaign.path("receipts.jsonl"), "a") as f:
        f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "thread": thread,
                            "stage": stage, "actor": actor, "backend": campaign.backend, "model": model,
                            **{k: r[k] for k in ("seconds", "input_tokens", "output_tokens", "cost", "error")}}) + "\n")
    return r

def _kill(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM); proc.wait(5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try: os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError: pass

def receipts(campaign) -> list[dict]:
    p = campaign.path("receipts.jsonl")
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

def spend(campaign) -> float:
    return round(sum(r.get("cost") or 0 for r in receipts(campaign)), 4)
```

- [ ] **Step 5: Run, expect pass, commit**

Commit: `git add -A && git commit -m "Add the CLI transport with streaming parse and receipts"`

---

### Task 4: Corpus

**Files:**
- Create: `pathfinder/corpus.py`, `tests/test_corpus.py`

**Interfaces:**
- Produces: `fetch(query: str, n: int) -> list[dict]` rows `{id, title, abstract, authors, date, text}`; `write(rows, path)`; `read(path) -> list[dict]`; `sources(campaign, side: str)` downloads e-prints for `Q.jsonl` or `P.jsonl`, writes `sources/<id>.tex` (or `.txt`) and sets `text` to that relative path; `body(campaign, row, fulltext: bool) -> str` returns the flattened text when asked and available, else the abstract; `pair_id(i, j) -> str` is `f"Q{i}P{j}"` with 1-based indices; `parse_atom(xml: str) -> list[dict]`.

- [ ] **Step 1: Write the failing test (offline: parsing and body only)**

```python
# tests/test_corpus.py
from pathfinder import corpus
from pathfinder.config import Campaign

ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>http://arxiv.org/abs/2409.00001v2</id><title>A  title
 wrapped</title><summary> The abstract. </summary><published>2024-09-01T00:00:00Z</published>
<author><name>Ann</name></author><author><name>Bob</name></author></entry></feed>"""

def test_parse_atom():
    rows = corpus.parse_atom(ATOM)
    assert rows == [{"id": "2409.00001", "title": "A title wrapped", "abstract": "The abstract.",
                     "authors": ["Ann", "Bob"], "date": "2024-09-01", "text": None}]

def test_body_falls_back_to_abstract(tmp_path):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=1, cut=1,
                 rounds=1, allowances={}, budget_usd=1, prices={}, scan_fulltext=None)
    row = {"id": "x", "title": "t", "abstract": "abs", "text": None}
    assert corpus.body(c, row, fulltext=True) == "abs"
    (tmp_path / "sources").mkdir(); (tmp_path / "sources" / "x.tex").write_text("full")
    row["text"] = "sources/x.tex"
    assert corpus.body(c, row, fulltext=True) == "full" and corpus.body(c, row, fulltext=False) == "abs"
    assert corpus.pair_id(2, 3) == "Q2P3"
```

- [ ] **Step 2: Run, expect failure**

- [ ] **Step 3: Implement corpus.py**

```python
"""Corpora: JSONL rows from the arXiv API, e-print sources flattened to one file."""
from __future__ import annotations
import gzip, io, json, re, shutil, subprocess, tarfile, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"a": "http://www.w3.org/2005/Atom"}
API = "http://export.arxiv.org/api/query?"

def pair_id(i: int, j: int) -> str:
    return f"Q{i}P{j}"

def _clean(s): return re.sub(r"\s+", " ", s or "").strip()

def parse_atom(xml: str) -> list[dict]:
    rows = []
    for e in ET.fromstring(xml).findall("a:entry", NS):
        aid = e.findtext("a:id", "", NS).rsplit("/", 1)[-1]
        aid = re.sub(r"v\d+$", "", aid)
        rows.append({"id": aid, "title": _clean(e.findtext("a:title", "", NS)),
                     "abstract": _clean(e.findtext("a:summary", "", NS)),
                     "authors": [_clean(a.findtext("a:name", "", NS)) for a in e.findall("a:author", NS)],
                     "date": e.findtext("a:published", "", NS)[:10], "text": None})
    return rows

def fetch(query: str, n: int) -> list[dict]:
    q = urllib.parse.urlencode({"search_query": f'all:"{query}"', "sortBy": "submittedDate",
                                "sortOrder": "descending", "max_results": n})
    with urllib.request.urlopen(API + q, timeout=60) as r:
        return parse_atom(r.read().decode())

def write(rows, path: Path):
    Path(path).write_text("".join(json.dumps(r) + "\n" for r in rows))

def read(path: Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]

def body(campaign, row: dict, fulltext: bool) -> str:
    if fulltext and row.get("text"):
        p = campaign.path(row["text"])
        if p.exists():
            return p.read_text(errors="replace")
    return row["abstract"]

def _main_tex(d: Path) -> Path | None:
    cands = [p for p in d.rglob("*.tex") if "\\documentclass" in p.read_text(errors="replace")]
    return min(cands, key=lambda p: len(p.parts)) if cands else None

def flatten(aid: str, out_dir: Path) -> str:
    """Download the e-print for aid, flatten to out_dir/aid.tex or .txt; return the relative name."""
    out_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(f"https://arxiv.org/e-print/{aid}", headers={"User-Agent": "pathfinder/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        blob, ctype = r.read(), r.headers.get("Content-Type", "")
    work = out_dir / aid; shutil.rmtree(work, ignore_errors=True); work.mkdir()
    if blob[:4] == b"%PDF" or "pdf" in ctype:
        (work / "paper.pdf").write_bytes(blob)
        subprocess.run(["pdftotext", "-layout", str(work / "paper.pdf"), str(out_dir / f"{aid}.txt")], check=True)
        return f"sources/{aid}.txt"
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as tf:
            tf.extractall(work, filter="data")
    except tarfile.ReadError:
        (work / "main.tex").write_bytes(gzip.decompress(blob))
    main = _main_tex(work)
    if main is None:
        raise RuntimeError(f"{aid}: no .tex with \\documentclass in e-print")
    with open(out_dir / f"{aid}.tex", "w") as f:
        subprocess.run(["latexpand", "--empty-comments", main.name], cwd=main.parent, stdout=f, check=True)
    return f"sources/{aid}.tex"

def sources(campaign, side: str):
    path = campaign.path(f"{side}.jsonl"); rows = read(path)
    for row in rows:
        if row.get("text") and campaign.path(row["text"]).exists():
            continue
        row["text"] = flatten(row["id"], campaign.path("sources"))
        print(f"{side} {row['id']}: {row['text']}")
        time.sleep(3)
    write(rows, path)
```

- [ ] **Step 4: Run, expect pass, commit**

Commit: `git add -A && git commit -m "Add arXiv fetch and e-print flattening"`

---

### Task 5: Scan and select

**Files:**
- Create: `pathfinder/scan.py`, `pathfinder/select.py`, `tests/test_select.py`, `tests/test_scan.py`

**Interfaces:**
- Produces: `scan.run(campaign, stop=lambda: False)` appends to `scan.jsonl` rows `{pair_id, q, p, feasibility, gain, connexion, rationale, model, seconds, cost, error}`; `scan.render(campaign, q, p) -> str` fills `prompts/scan.md`; `scan.parse_json(text) -> dict` strips fences and takes the first `{...}`.
- Produces: `select.run(campaign, cut: float | None, force=False) -> dict` writes `shortlist.json` `{cut, n_scored, n_selected, digest, pairs: [{pair_id, q, p, score, feasibility, gain}]}`; `select.rank(rows) -> list[dict]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_select.py
import json
from pathfinder import select
from pathfinder.config import Campaign

def rows():
    return [{"pair_id": "Q1P1", "q": "a", "p": "b", "feasibility": 90, "gain": 10},
            {"pair_id": "Q1P2", "q": "a", "p": "c", "feasibility": 50, "gain": 50},
            {"pair_id": "Q2P1", "q": "d", "p": "b", "feasibility": 30, "gain": 30},
            {"pair_id": "Q2P2", "q": "d", "p": "c", "feasibility": None, "gain": None, "error": "x"}]

def test_rank_by_product_then_min_then_id():
    ranked = [r["pair_id"] for r in select.rank(rows())]
    assert ranked == ["Q1P2", "Q1P1", "Q2P1"]        # 2500 > 900 = 900 tie: min 30 > 10? no: min(90,10)=10 < min(30,30)=30

def test_cut_rounds_up_without_tie_expansion(tmp_path):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=1, cut=1,
                 rounds=1, allowances={}, budget_usd=1, prices={}, scan_fulltext=None)
    (tmp_path / "Q.jsonl").write_text('{"id":"a"}\n{"id":"d"}\n'); (tmp_path / "P.jsonl").write_text('{"id":"b"}\n{"id":"c"}\n')
    (tmp_path / "scan.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows()))
    out = select.run(c, cut=30)
    assert out["n_selected"] == 1 and out["pairs"][0]["pair_id"] == "Q1P2" and len(out["digest"]) == 64
```

Fix the comment in the first test before running: with the tie between Q1P1 (900, min 10) and Q2P1 (900, min 30), the larger minimum ranks first, so the expected order is `["Q1P2", "Q2P1", "Q1P1"]`. Use that.

```python
# tests/test_scan.py
import json, sys
from pathlib import Path
from pathfinder import scan, transport
from pathfinder.config import Campaign

def test_scan_is_resumable_and_parses(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", f"{sys.executable} {Path(__file__).parent / 'fake_cli.py'}")
    monkeypatch.setenv("FAKE_REPLY", '```json\n{"feasibility": 70, "gain": 40, "connexion": "c", "rationale": "r"}\n```')
    monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    (tmp_path / "prompts").mkdir(); (tmp_path / "prompts" / "scan.md").write_text("{{Q_TITLE}}|{{Q_BODY}}|{{P_TITLE}}|{{P_BODY}}")
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=1, cut=1,
                 rounds=1, allowances={}, budget_usd=1, prices={}, scan_fulltext=None)
    (tmp_path / "Q.jsonl").write_text('{"id":"a","title":"A","abstract":"aa"}\n')
    (tmp_path / "P.jsonl").write_text('{"id":"b","title":"B","abstract":"bb"}\n{"id":"c","title":"C","abstract":"cc"}\n')
    (tmp_path / "scan.jsonl").write_text(json.dumps({"pair_id": "Q1P1", "feasibility": 1, "gain": 1}) + "\n")
    scan.run(c)
    rows = [json.loads(l) for l in (tmp_path / "scan.jsonl").read_text().splitlines()]
    assert [r["pair_id"] for r in rows] == ["Q1P1", "Q1P2"] and rows[1]["feasibility"] == 70
```

- [ ] **Step 2: Run, expect failure**

- [ ] **Step 3: Implement scan.py**

```python
"""Phase A: score every pair, row by row, one tool-less call each. Resumable."""
from __future__ import annotations
import json, re
from pathlib import Path
from . import corpus, transport

def prompts_dir(campaign) -> Path:
    local = campaign.path("prompts")
    return local if local.exists() else Path(__file__).resolve().parent.parent / "prompts"

def render(campaign, q: dict, p: dict) -> str:
    ft = campaign.scan_fulltext
    t = (prompts_dir(campaign) / "scan.md").read_text()
    return (t.replace("{{Q_TITLE}}", q["title"]).replace("{{Q_BODY}}", corpus.body(campaign, q, ft in ("q", "both")))
             .replace("{{P_TITLE}}", p["title"]).replace("{{P_BODY}}", corpus.body(campaign, p, ft in ("p", "both"))))

def parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in reply")
    return json.loads(m.group(0))

def done(campaign) -> set[str]:
    p = campaign.path("scan.jsonl")
    return {json.loads(l)["pair_id"] for l in p.read_text().splitlines() if l.strip()} if p.exists() else set()

def run(campaign, stop=lambda: False):
    Q, P, seen = corpus.read(campaign.path("Q.jsonl")), corpus.read(campaign.path("P.jsonl")), done(campaign)
    for i, q in enumerate(Q, 1):
        for j, p in enumerate(P, 1):
            pid = corpus.pair_id(i, j)
            if pid in seen or stop():
                continue
            row = {"pair_id": pid, "q": q["id"], "p": p["id"], "feasibility": None, "gain": None,
                   "connexion": None, "rationale": None, "model": campaign.scan_model, "seconds": 0, "cost": 0, "error": None}
            for attempt in range(2):
                r = transport.call(render(campaign, q, p), campaign=campaign, model=campaign.scan_model, tools=False,
                                   search=False, cwd=campaign.path("scan-work"), timeout=600, thread=pid, stage="scan", actor="judge")
                row["seconds"] += r["seconds"]; row["cost"] += r["cost"]
                try:
                    v = parse_json(r["text"])
                    row.update(feasibility=int(v["feasibility"]), gain=int(v["gain"]), connexion=v.get("connexion"),
                               rationale=v.get("rationale"), error=None)
                    break
                except (ValueError, KeyError, TypeError) as e:
                    row["error"] = r["error"] or f"unparseable: {e}"
            with open(campaign.path("scan.jsonl"), "a") as f:
                f.write(json.dumps(row) + "\n")
            print(f"{pid} feasibility={row['feasibility']} gain={row['gain']} {row['error'] or ''}")
```

- [ ] **Step 4: Implement select.py**

```python
"""Freeze the top cut of the scan as the shortlist."""
from __future__ import annotations
import hashlib, json, math
from . import corpus

def rank(rows: list[dict]) -> list[dict]:
    scored = [r for r in rows if r.get("feasibility") is not None and r.get("gain") is not None]
    for r in scored:
        r["score"] = r["feasibility"] * r["gain"]
    return sorted(scored, key=lambda r: (-r["score"], -min(r["feasibility"], r["gain"]), r["pair_id"]))

def run(campaign, cut: float | None = None, force: bool = False) -> dict:
    cut = campaign.cut if cut is None else cut
    raw = campaign.path("scan.jsonl").read_bytes()
    rows = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
    expected = len(corpus.read(campaign.path("Q.jsonl"))) * len(corpus.read(campaign.path("P.jsonl")))
    if len(rows) < expected and not force:
        raise SystemExit(f"scan incomplete: {len(rows)} of {expected} pairs; use --force to select anyway")
    ranked = rank(rows)
    k = math.ceil(len(ranked) * cut / 100)
    out = {"cut": cut, "n_scored": len(ranked), "n_selected": k, "digest": hashlib.sha256(raw).hexdigest(),
           "pairs": [{k2: r[k2] for k2 in ("pair_id", "q", "p", "score", "feasibility", "gain")} for r in ranked[:k]]}
    campaign.path("shortlist.json").write_text(json.dumps(out, indent=1))
    return out
```

- [ ] **Step 5: Run, expect pass, commit**

Commit: `git add -A && git commit -m "Add the scan and the shortlist cut"`

---

### Task 6: Research thread

**Files:**
- Create: `pathfinder/research.py`, `tests/test_research.py`

**Interfaces:**
- Consumes: `Ledger`, `transport.call`, `scan.prompts_dir`, `corpus.read/body`.
- Produces: `prepare(campaign, pair: dict) -> Path` creates the thread dir with `inputs/Q.*`, `inputs/P.*`, `status.json`; `run_thread(campaign, pair_id: str, stop=lambda: False) -> str` runs from the current stage to a terminal status or until `stop()` is seen between calls, returning the status; `status(campaign, pair_id) -> dict` reads `status.json` `{pair_id, round, stage, status, reason, updated}` where stage in `peers|consolidate|verify|done` and status in `running|stopped|DRAFT|PAUSE|PAUSE-ON-ITERATE|BLOCKED`; `TERMINAL = {"DRAFT", "PAUSE", "PAUSE-ON-ITERATE"}`; `class Stopped(Exception)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_research.py
import json, sys
from pathlib import Path
from pathfinder import research, transport
from pathfinder.config import Campaign

FAKE = f"{sys.executable} {Path(__file__).parent / 'fake_cli.py'}"

def make(tmp_path, rounds=3):
    (tmp_path / "campaign.json").write_text("{}")
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=False, seats=1, cut=1,
                 rounds=rounds, allowances={"peer_seconds": 100, "peer_calls": 2, "consolidate_seconds": 10, "verify_seconds": 10},
                 budget_usd=99, prices={}, scan_fulltext=None)
    (tmp_path / "Q.jsonl").write_text('{"id":"a","title":"A","abstract":"aa","text":null}\n')
    (tmp_path / "P.jsonl").write_text('{"id":"b","title":"B","abstract":"bb","text":null}\n')
    return c

def test_thread_reaches_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    c = make(tmp_path)
    helper = f"{sys.executable} -m pathfinder.ledger --root . "
    # peers: each call adds an idea then declares ready at the latest entry
    monkeypatch.setenv("FAKE_RUN", helper + "--actor $FAKE_ACTOR add --kind idea --text hi >/dev/null; "
                       + helper + "--actor $FAKE_ACTOR ready --seen $(" + helper + "--actor x read | grep -c '^#')")
    replies = iter(["peer", "peer", '{"decision":"DRAFT","reason":"fine","action":null}'])
    real = transport.call
    def fake_call(prompt, **kw):
        monkeypatch.setenv("FAKE_ACTOR", kw["actor"])
        if kw["stage"] == "consolidate":
            (kw["cwd"] / "Q1P1.tex").write_text("\\documentclass{article}\\begin{document}x\\end{document}")
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", "wrote it")
        elif kw["stage"] == "verify":
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", '{"decision":"DRAFT","reason":"fine","action":null}')
        else:
            monkeypatch.setenv("FAKE_REPLY", "peer")
        return real(prompt, **kw)
    monkeypatch.setattr(research.transport, "call", fake_call)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    s = research.status(c, "Q1P1")
    assert s["status"] == "DRAFT" and s["round"] == 1
    v = json.loads((tmp_path / "threads" / "Q1P1" / "Q1P1.verdict.json").read_text())
    assert v[0]["decision"] == "DRAFT"

def test_iterate_cap_becomes_pause_on_iterate(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    c = make(tmp_path, rounds=2)
    real = transport.call
    def fake_call(prompt, **kw):
        if kw["stage"] == "peers":
            monkeypatch.setenv("FAKE_RUN", f"{sys.executable} -m pathfinder.ledger --root . --actor {kw['actor']} add --kind idea --text x >/dev/null")
            monkeypatch.setenv("FAKE_REPLY", "p")
        elif kw["stage"] == "consolidate":
            (kw["cwd"] / "Q1P1.tex").write_text("x"); monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", "ok")
        else:
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", '{"decision":"ITERATE","reason":"more","action":"check"}')
        return real(prompt, **kw)
    monkeypatch.setattr(research.transport, "call", fake_call)
    assert research.run_thread(c, "Q1P1") == "PAUSE-ON-ITERATE"
    assert research.status(c, "Q1P1")["round"] == 2

def test_empty_ledger_pauses_without_note(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    monkeypatch.setenv("FAKE_REPLY", "nothing"); monkeypatch.setenv("FAKE_RUN", "true")
    c = make(tmp_path)
    assert research.run_thread(c, "Q1P1") == "PAUSE"
    assert research.status(c, "Q1P1")["reason"] == "empty ledger"
    assert not (tmp_path / "threads" / "Q1P1" / "Q1P1.tex").exists()
```

- [ ] **Step 2: Run, expect failure**

- [ ] **Step 3: Implement research.py**

```python
"""One research thread: peers on a shared ledger, consolidate, verify, up to `rounds` rounds."""
from __future__ import annotations
import json, shutil, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import corpus, transport
from .ledger import Ledger
from .scan import prompts_dir, parse_json

PEERS = ("ada", "emmy")
TERMINAL = {"DRAFT", "PAUSE", "PAUSE-ON-ITERATE"}

class Stopped(Exception):
    pass

def _now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def status(campaign, pair_id) -> dict:
    p = campaign.thread_dir(pair_id) / "status.json"
    return json.loads(p.read_text()) if p.exists() else {"pair_id": pair_id, "round": 0, "stage": "peers", "status": "new"}

def _set(campaign, pair_id, **kw):
    s = status(campaign, pair_id); s.update(kw, updated=_now())
    (campaign.thread_dir(pair_id) / "status.json").write_text(json.dumps(s, indent=1))
    return s

def _pair(campaign, pair_id):
    i, j = (int(x) for x in pair_id[1:].split("P"))
    return corpus.read(campaign.path("Q.jsonl"))[i - 1], corpus.read(campaign.path("P.jsonl"))[j - 1]

def prepare(campaign, pair_id: str) -> Path:
    d = campaign.thread_dir(pair_id)
    if (d / "status.json").exists():
        return d
    (d / "inputs").mkdir(parents=True, exist_ok=True)
    for side, row in zip("QP", _pair(campaign, pair_id)):
        src = campaign.path(row["text"]) if row.get("text") else None
        if src and src.exists():
            shutil.copy(src, d / "inputs" / f"{side}{src.suffix}")
        else:
            (d / "inputs" / f"{side}.txt").write_text(f"Title: {row['title']}\n\nAbstract: {row['abstract']}\n")
        (d / "inputs" / f"{side}.json").write_text(json.dumps(row, indent=1))
    for a in PEERS:
        (d / a).mkdir(exist_ok=True)
    _set(campaign, pair_id, pair_id=pair_id, round=1, stage="peers", status="running", reason=None, started=_now())
    return d

def _inputs(d: Path) -> dict:
    return {s: next(p for p in (d / "inputs").iterdir() if p.stem == s and p.suffix != ".json").name for s in "QP"}

def _prompt(campaign, name, **vars):
    t = (prompts_dir(campaign) / f"{name}.md").read_text()
    for k, v in vars.items():
        t = t.replace("{{" + k + "}}", str(v))
    return t

def _check(stop):
    if stop():
        raise Stopped()

def _peers(campaign, pair_id, stop):
    d, L = campaign.thread_dir(pair_id), Ledger(campaign.thread_dir(pair_id) / "ledger.jsonl")
    A = campaign.allowances; inp = _inputs(d)
    helper = f"{sys.executable} -m pathfinder.ledger --root ."
    used = {"seconds": 0.0}; lock = threading.Lock()
    def one(actor):
        peer = PEERS[1 - PEERS.index(actor)]
        for call_no in range(A["peer_calls"]):
            with lock:
                left = A["peer_seconds"] - used["seconds"]
            if left <= 0 or L.ready(list(PEERS)):
                return
            _check(stop)
            p = _prompt(campaign, "peer", ACTOR=actor, PEER=peer, Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}",
                        LEDGER=f"{helper} --actor {actor}", SECONDS=int(min(left, 1200)),
                        CALLS_LEFT=A["peer_calls"] - call_no - 1)
            if call_no or L.count():
                p += "\n\nThis is a resumed call on the same thread. Read the ledger first; do not repeat work.\n"
            r = transport.call(p, campaign=campaign, model=campaign.model, tools=True, search=campaign.peer_search,
                               cwd=d, timeout=int(min(left, 1200)) + 30, thread=pair_id, stage="peers", actor=actor)
            with lock:
                used["seconds"] += r["seconds"]
            if r["transport_failed"]:
                raise transport.TransportFailed(pair_id)
    with ThreadPoolExecutor(2) as ex:
        for f in [ex.submit(one, a) for a in PEERS]:
            f.result()

def _stage_call(campaign, pair_id, stage, prompt, tools, seconds):
    """Run consolidate or verify; rerun once on timeout or empty reply."""
    d = campaign.thread_dir(pair_id)
    for attempt in range(2):
        r = transport.call(prompt, campaign=campaign, model=campaign.model, tools=tools, search=False, cwd=d,
                           timeout=seconds, thread=pair_id, stage=stage, actor="ada" if stage == "consolidate" else "verifier")
        if r["transport_failed"]:
            raise transport.TransportFailed(pair_id)
        if r["text"] or r["error"] is None:
            return r
    return r

def run_thread(campaign, pair_id: str, stop=lambda: False) -> str:
    d = prepare(campaign, pair_id); L = Ledger(d / "ledger.jsonl"); A = campaign.allowances
    note, verdicts = d / f"{pair_id}.tex", d / f"{pair_id}.verdict.json"
    inp = _inputs(d)
    try:
        while True:
            s = status(campaign, pair_id)
            if s["status"] in TERMINAL:
                return s["status"]
            _set(campaign, pair_id, status="running")
            if s["stage"] == "peers":
                _check(stop); _peers(campaign, pair_id, stop)
                if L.latest_substantive() == 0:
                    _set(campaign, pair_id, stage="done", status="PAUSE", reason="empty ledger"); return "PAUSE"
                _set(campaign, pair_id, stage="consolidate")
            elif s["stage"] == "consolidate":
                _check(stop)
                why = "" if L.ready(list(PEERS)) else " because the allowance ran out before both peers declared ready"
                r = _stage_call(campaign, pair_id, "consolidate",
                                _prompt(campaign, "consolidate", ACTOR="ada", WHY=why, NOTE=note.name), True, A["consolidate_seconds"])
                if not note.exists():
                    if r["text"].strip():
                        note.write_text(r["text"])
                    else:
                        _set(campaign, pair_id, status="BLOCKED", reason=f"consolidate: {r['error'] or 'no note'}"); return "BLOCKED"
                _set(campaign, pair_id, stage="verify")
            elif s["stage"] == "verify":
                _check(stop)
                p = _prompt(campaign, "verify", Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}", NOTE=note.name)
                p += "\n\n## " + inp["Q"] + "\n\n" + (d / "inputs" / inp["Q"]).read_text(errors="replace")
                p += "\n\n## " + inp["P"] + "\n\n" + (d / "inputs" / inp["P"]).read_text(errors="replace")
                p += "\n\n## ledger.jsonl\n\n" + (d / "ledger.jsonl").read_text()
                p += "\n\n## " + note.name + "\n\n" + note.read_text(errors="replace")
                r = _stage_call(campaign, pair_id, "verify", p, False, A["verify_seconds"])
                try:
                    v = parse_json(r["text"]); dec = v["decision"].upper()
                    assert dec in ("DRAFT", "ITERATE", "PAUSE")
                except Exception as e:
                    _set(campaign, pair_id, status="BLOCKED", reason=f"verify: unreadable decision ({e})"); return "BLOCKED"
                hist = json.loads(verdicts.read_text()) if verdicts.exists() else []
                hist.append({"round": s["round"], "at": _now(), **v}); verdicts.write_text(json.dumps(hist, indent=1))
                if dec == "ITERATE" and s["round"] < campaign.rounds:
                    L.add("verifier", "review", f"ITERATE: {v.get('reason')} Action: {v.get('action')}")
                    _set(campaign, pair_id, stage="peers", round=s["round"] + 1, reason=v.get("reason"))
                else:
                    final = "PAUSE-ON-ITERATE" if dec == "ITERATE" else dec
                    _set(campaign, pair_id, stage="done", status=final, reason=v.get("reason")); return final
    except Stopped:
        _set(campaign, pair_id, status="stopped"); return "stopped"
    except transport.TransportFailed:
        _set(campaign, pair_id, status="stopped", reason="transport failed"); raise
```

Add to `transport.py`:

```python
class TransportFailed(Exception):
    """Raised by callers when a call never reached a model session."""
```

- [ ] **Step 4: Run, expect pass, commit**

Run: `uv run pytest tests/test_research.py -q`
Commit: `git add -A && git commit -m "Add the research thread: peers, consolidate, verify, rounds"`

---

### Task 7: Runner and reconcile

**Files:**
- Create: `pathfinder/runner.py`, `pathfinder/reconcile.py`, `tests/test_runner.py`

**Interfaces:**
- Consumes: `research.run_thread/status/TERMINAL`, `transport.spend`, `transport.TransportFailed`.
- Produces: `runner.run(campaign)` the research loop; `runner.stopped(campaign) -> bool`; `runner.request_stop(campaign, reason)`; `runner.guard_ok(campaign, inflight: int) -> bool`; `runner.Lock(dir)` context manager with `Lock.holder(dir) -> int | None` (pid, alive only); `reconcile.inspect(campaign, pair_id) -> dict {pair_id, status, stage, lock, action}` and `reconcile.apply(campaign, pair_id)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_runner.py
import json, os, threading, time
from pathfinder import runner, research
from pathfinder.config import Campaign

def make(tmp_path, seats=2, budget=99):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=False, seats=seats, cut=1,
                 rounds=1, allowances={"peer_seconds": 1, "peer_calls": 1, "consolidate_seconds": 1, "verify_seconds": 1},
                 budget_usd=budget, prices={}, scan_fulltext=None, call_estimate_usd=1.0)
    (tmp_path / "shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": f"Q1P{j}"} for j in (1, 2, 3)]}))
    return c

def test_guard_writes_stop_when_over_budget(tmp_path):
    c = make(tmp_path, budget=1.5)
    (tmp_path / "receipts.jsonl").write_text(json.dumps({"cost": 1.0}) + "\n")
    assert runner.guard_ok(c, inflight=0)
    assert not runner.guard_ok(c, inflight=1)            # 1.0 + 1 * 1.0 > 1.5
    assert runner.stopped(c) and json.loads((tmp_path / "stop.json").read_text())["reason"].startswith("budget")

def test_stop_drains_in_flight(tmp_path, monkeypatch):
    c = make(tmp_path, seats=1)
    calls = []
    def fake_thread(campaign, pair_id, stop=lambda: False):
        calls.append(pair_id); time.sleep(0.3)
        (campaign.thread_dir(pair_id)).mkdir(parents=True, exist_ok=True)
        (campaign.thread_dir(pair_id) / "status.json").write_text(json.dumps({"status": "PAUSE", "stage": "done", "round": 1}))
        return "PAUSE"
    monkeypatch.setattr(runner.research, "run_thread", fake_thread)
    threading.Timer(0.1, lambda: runner.request_stop(c, "test")).start()
    runner.run(c, interval=0.05)
    assert calls == ["Q1P1"]                           # first admitted, finished; nothing else admitted

def test_lock_and_reconcile_action(tmp_path):
    from pathfinder import reconcile
    c = make(tmp_path); d = c.thread_dir("Q1P1"); d.mkdir(parents=True)
    (d / "status.json").write_text(json.dumps({"pair_id": "Q1P1", "round": 1, "stage": "verify", "status": "stopped"}))
    assert reconcile.inspect(c, "Q1P1")["action"] == "run verify"
    with runner.Lock(d):
        assert runner.Lock.holder(d) == os.getpid()
        assert reconcile.inspect(c, "Q1P1")["action"] == "nothing: in progress"
    (d / "lock").write_text("999999")                  # dead pid
    assert runner.Lock.holder(d) is None
```

- [ ] **Step 2: Run, expect failure**

- [ ] **Step 3: Implement runner.py**

```python
"""The research loop: seats, rolling admission, budget guard, stop as a drain, health flag."""
from __future__ import annotations
import json, os, signal, time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
from . import research, transport

def _now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

class Lock:
    """One lock file per thread directory holding the owner's pid."""
    def __init__(self, d: Path): self.d = Path(d); self.p = self.d / "lock"
    @staticmethod
    def holder(d: Path) -> int | None:
        p = Path(d) / "lock"
        if not p.exists(): return None
        try:
            pid = int(p.read_text().strip()); os.kill(pid, 0); return pid
        except (ValueError, ProcessLookupError, PermissionError):
            return None
    def __enter__(self):
        if Lock.holder(self.d): raise RuntimeError(f"{self.d.name} is held by pid {Lock.holder(self.d)}")
        self.d.mkdir(parents=True, exist_ok=True); self.p.write_text(str(os.getpid())); return self
    def __exit__(self, *a):
        self.p.unlink(missing_ok=True)

def stopped(campaign) -> bool: return campaign.path("stop.json").exists()
def request_stop(campaign, reason: str):
    campaign.path("stop.json").write_text(json.dumps({"reason": reason, "at": _now()}))
def unhealthy(campaign) -> bool: return campaign.path("health.json").exists()

def guard_ok(campaign, inflight: int) -> bool:
    projected = transport.spend(campaign) + inflight * campaign.call_estimate_usd
    if projected > campaign.budget_usd:
        if not stopped(campaign):
            request_stop(campaign, f"budget: {projected:.2f} projected against cap {campaign.budget_usd:.2f}")
        return False
    return True

def pending(campaign) -> list[str]:
    pairs = [p["pair_id"] for p in json.loads(campaign.path("shortlist.json").read_text())["pairs"]]
    return [p for p in pairs if research.status(campaign, p).get("status") not in research.TERMINAL
            and not Lock.holder(campaign.thread_dir(p))]

def _work(campaign, pair_id):
    with Lock(campaign.thread_dir(pair_id)):
        return research.run_thread(campaign, pair_id, stop=lambda: stopped(campaign))

def _probe(campaign) -> bool:
    r = transport.call("Reply with the single word ok.", campaign=campaign, model=campaign.model, tools=False, search=False,
                       cwd=campaign.path("scan-work"), timeout=120, thread="probe", stage="probe", actor="probe")
    return not r["transport_failed"]

def run(campaign, interval: float = 5.0):
    failures, futures = 0, {}
    interrupted = {"n": 0}
    def on_int(*_):
        interrupted["n"] += 1
        if interrupted["n"] == 1:
            request_stop(campaign, "interrupt"); print("stop requested: draining calls in flight; Ctrl-C again to abort")
        else:
            os._exit(130)
    signal.signal(signal.SIGINT, on_int)
    with ThreadPoolExecutor(campaign.seats) as ex:
        while True:
            if unhealthy(campaign) and not futures:
                if _probe(campaign):
                    campaign.path("health.json").unlink(); failures = 0; print("health restored")
                else:
                    time.sleep(60); continue
            queue = [] if (stopped(campaign) or unhealthy(campaign)) else pending(campaign)
            for pair_id in queue:
                if len(futures) >= campaign.seats or pair_id in futures.values(): break
                if not guard_ok(campaign, inflight=len(futures) + 1): break
                futures[ex.submit(_work, campaign, pair_id)] = pair_id
                print(f"{_now()} admitted {pair_id} ({len(futures)}/{campaign.seats} seats)")
            if not futures:
                if stopped(campaign) or not pending(campaign):
                    print("stopped" if stopped(campaign) else "all threads terminal"); return
                time.sleep(interval); continue
            done, _ = wait(list(futures), timeout=interval, return_when=FIRST_COMPLETED)
            for f in done:
                pair_id = futures.pop(f)
                try:
                    print(f"{_now()} {pair_id}: {f.result()}"); failures = 0
                except transport.TransportFailed:
                    failures += 1; print(f"{_now()} {pair_id}: transport failure ({failures})")
                    if failures >= 2 and not unhealthy(campaign):
                        campaign.path("health.json").write_text(json.dumps({"at": _now(), "reason": "two consecutive transport failures"}))
                        print("health flag set: admissions paused until a probe call succeeds")
                except Exception as e:
                    print(f"{_now()} {pair_id}: error {e!r}")
```

- [ ] **Step 4: Implement reconcile.py**

```python
"""Inspect one thread and name the one safe action; apply it on request."""
from __future__ import annotations
import json
from . import research, runner

def inspect(campaign, pair_id: str) -> dict:
    d = campaign.thread_dir(pair_id); s = research.status(campaign, pair_id); holder = runner.Lock.holder(d)
    note = (d / f"{pair_id}.tex").exists()
    if holder:
        action = "nothing: in progress"
    elif s.get("status") in research.TERMINAL:
        action = "nothing: terminal"
    elif s.get("status") == "new":
        action = "start"
    elif s.get("stage") == "peers":
        action = "resume peers"
    elif s.get("stage") == "consolidate" or (s.get("stage") == "verify" and not note):
        action = "run consolidate"
    elif s.get("stage") == "verify":
        action = "run verify"
    else:
        action = "nothing: unknown state"
    return {"pair_id": pair_id, "status": s.get("status"), "stage": s.get("stage"), "round": s.get("round"),
            "reason": s.get("reason"), "lock": holder, "action": action}

def apply(campaign, pair_id: str) -> str:
    info = inspect(campaign, pair_id)
    if info["action"].startswith("nothing"):
        return info["action"]
    if info["action"] == "run consolidate":
        research._set(campaign, pair_id, stage="consolidate", status="running", reason=None)
    elif info["status"] == "BLOCKED":
        research._set(campaign, pair_id, status="running", reason=None)
    with runner.Lock(campaign.thread_dir(pair_id)):
        return research.run_thread(campaign, pair_id, stop=lambda: runner.stopped(campaign))
```

- [ ] **Step 5: Run, expect pass, commit**

Commit: `git add -A && git commit -m "Add the runner with guard, drain and health, and the reconcile command"`

---

### Task 8: Monitor

**Files:**
- Create: `pathfinder/monitor.py`, `tests/test_monitor.py`

**Interfaces:**
- Consumes: everything above, read-only.
- Produces: `state(campaign) -> dict` with keys `campaign, scan, shortlist, threads`; `status_text(campaign) -> str`; `serve(campaign, port=8765)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_monitor.py
import json
from pathfinder import monitor
from pathfinder.config import Campaign

def test_state_and_status_text(tmp_path):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=2, cut=50,
                 rounds=3, allowances={}, budget_usd=10, prices={}, scan_fulltext=None)
    (tmp_path / "Q.jsonl").write_text('{"id":"a","title":"A"}\n'); (tmp_path / "P.jsonl").write_text('{"id":"b","title":"B"}\n{"id":"c","title":"C"}\n')
    (tmp_path / "scan.jsonl").write_text(json.dumps({"pair_id": "Q1P1", "feasibility": 80, "gain": 50, "cost": 0.1}) + "\n")
    (tmp_path / "shortlist.json").write_text(json.dumps({"cut": 50, "pairs": [{"pair_id": "Q1P1", "score": 4000}]}))
    (tmp_path / "receipts.jsonl").write_text(json.dumps({"thread": "Q1P1", "stage": "peers", "cost": 2.5, "seconds": 30}) + "\n")
    d = tmp_path / "threads" / "Q1P1"; d.mkdir(parents=True)
    (d / "status.json").write_text(json.dumps({"pair_id": "Q1P1", "round": 1, "stage": "peers", "status": "running"}))
    (d / "ledger.jsonl").write_text(json.dumps({"seq": 1, "actor": "ada", "kind": "idea", "text": "x", "at": "t"}) + "\n")
    s = monitor.state(c)
    assert s["campaign"]["spend"] == 2.5 and s["campaign"]["phase"] == "research"
    assert s["scan"]["done"] == 1 and s["scan"]["total"] == 2 and s["scan"]["grid"][0][0] == 4000
    assert s["threads"]["Q1P1"]["entries"] == 1 and s["shortlist"][0]["spend"] == 2.5
    assert "Q1P1" in monitor.status_text(c)
```

- [ ] **Step 2: Run, expect failure**

- [ ] **Step 3: Implement monitor.py**

```python
"""Read-only view of a campaign: a state document, a text status, a local server with one live page."""
from __future__ import annotations
import json, time
from collections import Counter
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from . import corpus, research, runner, transport

def _jsonl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

def state(campaign) -> dict:
    Q = corpus.read(campaign.path("Q.jsonl")) if campaign.path("Q.jsonl").exists() else []
    P = corpus.read(campaign.path("P.jsonl")) if campaign.path("P.jsonl").exists() else []
    scan = _jsonl(campaign.path("scan.jsonl")); by_id = {r["pair_id"]: r for r in scan}
    grid = [[(by_id.get(corpus.pair_id(i, j), {}).get("feasibility") or 0) * (by_id.get(corpus.pair_id(i, j), {}).get("gain") or 0)
             if corpus.pair_id(i, j) in by_id else None for j in range(1, len(P) + 1)] for i in range(1, len(Q) + 1)]
    receipts = transport.receipts(campaign); rc = {}
    for r in receipts:
        t = rc.setdefault(r.get("thread"), {"spend": 0.0, "seconds": 0.0, "calls": 0})
        t["spend"] += r.get("cost") or 0; t["seconds"] += r.get("seconds") or 0; t["calls"] += 1
    sl = json.loads(campaign.path("shortlist.json").read_text()) if campaign.path("shortlist.json").exists() else {"pairs": []}
    threads, shortlist = {}, []
    for p in sl["pairs"]:
        pid = p["pair_id"]; s = research.status(campaign, pid); d = campaign.thread_dir(pid)
        led = _jsonl(d / "ledger.jsonl")
        verd = json.loads((d / f"{pid}.verdict.json").read_text()) if (d / f"{pid}.verdict.json").exists() else []
        threads[pid] = {"status": s, "entries": len(led), "by_kind": dict(Counter(e["kind"] for e in led)),
                        "by_actor": dict(Counter(e["actor"] for e in led)), "ledger": led, "verdicts": verd,
                        "note": f"{pid}.tex" if (d / f"{pid}.tex").exists() else None,
                        "files": sorted(x.name for x in d.iterdir()) if d.exists() else []}
        shortlist.append({**p, "status": s.get("status"), "round": s.get("round"), "stage": s.get("stage"),
                          **rc.get(pid, {"spend": 0.0, "seconds": 0.0, "calls": 0})})
    statuses = Counter(t["status"].get("status", "new") for t in threads.values())
    phase = ("research" if sl["pairs"] else "select" if scan and len(scan) >= len(Q) * len(P) and Q else "scan" if Q else "fetch")
    return {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "campaign": {"phase": phase, "spend": round(sum(r.get("cost") or 0 for r in receipts), 4), "budget": campaign.budget_usd,
                         "calls": len(receipts), "seconds": round(sum(r.get("seconds") or 0 for r in receipts)),
                         "seats": campaign.seats, "stop": _jsonl_one(campaign.path("stop.json")),
                         "health": _jsonl_one(campaign.path("health.json")), "by_status": dict(statuses), "backend": campaign.backend,
                         "model": campaign.model},
            "scan": {"done": len(scan), "total": len(Q) * len(P), "grid": grid, "q": [q.get("title") for q in Q],
                     "p": [p.get("title") for p in P], "cost": round(sum(r.get("cost") or 0 for r in scan), 4),
                     "scores": sorted((r["feasibility"] * r["gain"] for r in scan if r.get("feasibility") is not None), reverse=True),
                     "cut": sl.get("cut"), "n_selected": len(sl["pairs"])},
            "shortlist": shortlist, "threads": threads}

def _jsonl_one(p: Path):
    return json.loads(p.read_text()) if p.exists() else None

def status_text(campaign) -> str:
    s = state(campaign); c = s["campaign"]
    lines = [f"phase {c['phase']}  spend {c['spend']:.2f}/{c['budget']:.2f} USD  calls {c['calls']}  "
             f"stop {'yes' if c['stop'] else 'no'}  health {'flag' if c['health'] else 'ok'}",
             f"scan {s['scan']['done']}/{s['scan']['total']}  shortlist {s['scan']['n_selected']}  threads {c['by_status']}"]
    for p in s["shortlist"]:
        lines.append(f"{p['pair_id']:>8} {str(p['status']):>17} round {p['round'] or 0} {str(p['stage']):>11} "
                     f"calls {p['calls']:>3} {p['seconds']:>6.0f}s {p['spend']:>7.2f} USD")
    return "\n".join(lines)

PAGE = (Path(__file__).parent / "monitor.html")

def serve(campaign, port: int = 8765):
    root = campaign.root
    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k): super().__init__(*a, directory=str(root), **k)
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                body = PAGE.read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            elif self.path == "/state":
                body = json.dumps(state(campaign)).encode(); self.send_response(200); self.send_header("Content-Type", "application/json")
            else:
                return super().do_GET()
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self, *a): pass
    print(f"monitor at http://localhost:{port}/  (state at /state, thread files under /threads/)")
    HTTPServer(("127.0.0.1", port), H).serve_forever()
```

- [ ] **Step 4: Write `pathfinder/monitor.html`**

One page, no build step, polls `/state` every five seconds. Panels: campaign tiles (phase, spend against budget, calls, stop and health flags, threads by status); scan heat map as a table of Q rows by P columns coloured by score product with the shortlisted cells outlined, plus a sorted score bar list showing where the cut falls; shortlist table with status, round, stage, calls, seconds, spend, and links to `/threads/<pair>/ledger.jsonl`, the note and the verdict file; a thread panel that shows, for the pair clicked in the shortlist, the ledger in order with actor and kind badges, counts by kind and actor, and the verdict history. Plain CSS, light and dark via `prefers-color-scheme`, no external assets, no em dash character. Keep it under 250 lines.

- [ ] **Step 5: Run, expect pass, commit**

Commit: `git add -A && git commit -m "Add the monitor: state, text status, live page"`

---

### Task 9: CLI, README, and the reference run

**Files:**
- Create: `pathfinder/cli.py`, `README.md`
- Modify: `campaign.json` if the run shows a parameter is wrong

**Interfaces:**
- Produces: the `pathfinder` command with subcommands `fetch`, `sources`, `scan`, `select`, `research`, `stop`, `status`, `serve`, `reconcile`. Every subcommand takes `--root DIR` (default: current directory).

- [ ] **Step 1: Implement cli.py**

```python
"""pathfinder: scan every pair of two corpora, research the shortlist."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from . import config, corpus, monitor, reconcile, runner, scan, select

def main(argv=None):
    ap = argparse.ArgumentParser(prog="pathfinder"); ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="fill Q.jsonl and P.jsonl from the arXiv API")
    f.add_argument("--q", required=True); f.add_argument("--p", required=True); f.add_argument("--n", type=int, default=5)
    sub.add_parser("sources", help="download and flatten e-print sources for both sides").add_argument("--side", choices=["Q", "P", "both"], default="both")
    sub.add_parser("scan", help="phase A: score every pair")
    s = sub.add_parser("select", help="freeze the top cut as shortlist.json"); s.add_argument("--cut", type=float); s.add_argument("--force", action="store_true")
    sub.add_parser("research", help="run the shortlisted threads")
    sub.add_parser("stop", help="ask a running scan or research to drain and exit").add_argument("--clear", action="store_true", help="remove the stop marker instead")
    sub.add_parser("status", help="print campaign and shortlist state")
    sub.add_parser("serve", help="serve the live monitor page").add_argument("--port", type=int, default=8765)
    r = sub.add_parser("reconcile", help="inspect a thread and name or apply the one safe action")
    r.add_argument("pair", nargs="?"); r.add_argument("--apply", action="store_true")
    ns = ap.parse_args(argv); c = config.load(Path(ns.root))
    if ns.cmd == "fetch":
        for side, query in (("Q", ns.q), ("P", ns.p)):
            rows = corpus.fetch(query, ns.n); corpus.write(rows, c.path(f"{side}.jsonl"))
            print(f"{side}: {len(rows)} papers for {query!r}")
            for r in rows: print(f"  {r['id']}  {r['date']}  {r['title']}")
    elif ns.cmd == "sources":
        for side in (["Q", "P"] if ns.side == "both" else [ns.side]): corpus.sources(c, side)
    elif ns.cmd == "scan":
        scan.run(c, stop=lambda: runner.stopped(c))
    elif ns.cmd == "select":
        out = select.run(c, ns.cut, ns.force); print(f"selected {out['n_selected']} of {out['n_scored']} at {out['cut']}%")
        for p in out["pairs"]: print(f"  {p['pair_id']}  score {p['score']}  ({p['feasibility']} x {p['gain']})")
    elif ns.cmd == "research":
        runner.run(c)
    elif ns.cmd == "stop":
        if ns.clear: c.path("stop.json").unlink(missing_ok=True); print("stop marker cleared")
        else: runner.request_stop(c, "operator"); print("stop requested; running commands will drain and exit")
    elif ns.cmd == "status":
        print(monitor.status_text(c))
    elif ns.cmd == "serve":
        monitor.serve(c, ns.port)
    elif ns.cmd == "reconcile":
        pairs = [ns.pair] if ns.pair else [p["pair_id"] for p in json.loads(c.path("shortlist.json").read_text())["pairs"]]
        for pid in pairs:
            info = reconcile.inspect(c, pid); print(f"{pid}: {info['status']} at {info['stage']} round {info['round']}: {info['action']}")
            if ns.apply and not info["action"].startswith("nothing"): print(f"  -> {reconcile.apply(c, pid)}")

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Write README.md**

Sections, each a few sentences: what it does (the two phases and the outputs); requirements (Python 3.12, uv, one of the two CLIs logged in, latexpand, pdftotext); quick start as one fenced block (`uv sync`, `uv run pathfinder fetch --q ... --p ... --n 5`, `sources`, `scan`, `select --cut 12`, `research`, `serve` in a second terminal); the campaign directory layout; `campaign.json` fields one line each; how stops, the budget guard, transport failure and reconcile behave; the four prompts and that they are the place to tune; departures from the agQSL instance in five bullets; licence line. No em dash character. Run `/Users/v/.local/bin/style-ban-artifacts README.md` and fix until clean.

- [ ] **Step 3: Run the reference campaign**

```bash
cd ~/Code_2026/pathfinder && uv sync
uv run pathfinder fetch --q "mechanism design" --p "agentic cooperation" --n 5
uv run pathfinder sources
uv run pathfinder scan
uv run pathfinder select --cut 12
uv run pathfinder serve &        # open http://localhost:8765/
uv run pathfinder research
uv run pathfinder status
```

Expected: 25 scan rows, 3 shortlisted pairs, 3 threads each ending in DRAFT, PAUSE or PAUSE-ON-ITERATE, with a `.tex` note and a verdict file in each thread directory, the monitor showing all of it, spend under the cap. While research runs, once: `uv run pathfinder stop`, confirm the log says draining, confirm the in-flight thread's status is `stopped` with a receipt written, then `uv run pathfinder stop --clear` and `uv run pathfinder research` again, and confirm it resumes at the recorded stage. Kill one peer process by hand during a run and confirm `uv run pathfinder reconcile` names the action and `--apply` finishes the thread.

- [ ] **Step 4: Record what the run showed**

Append a section "Reference run, <date>" to `plans/2026-09-11-pathfinder-design.md`: the five Q and five P ids, the shortlist with scores, each thread's terminal status and round count, total spend and wall time, and anything that had to change in the code or prompts to get there. Commit with the run's `scan.jsonl`, `shortlist.json`, `receipts.jsonl` and `threads/` (notes and ledgers are the deliverable; `sources/` stays ignored).

- [ ] **Step 5: Commit**

Commit: `git add -A && git commit -m "Add the CLI and README; record the reference run"`

---

## Self-review

- Spec coverage: inputs and fetch (Task 4), scan and selection (5), thread with three stages, rounds, statuses and the empty-ledger rule (6), runner with seats, receipts, guard, drain, transport failure, health, stage failure, reconcile and locks (7, with stage rerun inside `_stage_call` in 6), transport with two backends and no fallback (3), monitor with four panels and the text status (8), configuration and layout (1, 9), the test campaign (9), departures recorded (9 step 4).
- The spec's "receipts" also cover scan calls: the scan appends receipts through the same `transport.call` (Task 5).
- Names used consistently: `research.status`, `research.run_thread`, `research.TERMINAL`, `research._set`, `runner.Lock`, `runner.stopped`, `runner.request_stop`, `runner.guard_ok`, `transport.call`, `transport.spend`, `transport.receipts`, `transport.TransportFailed`, `scan.prompts_dir`, `scan.parse_json`, `corpus.pair_id`, `corpus.body`.
- Known simplification, on purpose: the guard's in-flight allowance is `calls in flight x call_estimate_usd` rather than a per-stage projection. Good enough for an experiment; the cap is the receipts total plus that estimate.

# Phase 1: Failure classification, campaign-wide stops and prompt size gate

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every failed model call carries a failure class, scope and (for quota) reset time derived from the provider's structured events; campaign-wide classes stop the campaign and its parent at once; oversized prompts are refused before any launch; receipts record prompt size and tool calls.

**Architecture:** A new pure module `pathfinder/failures.py` classifies `(outcome, error)` pairs, where `error` is what `transport._parse` extracted from structured events (never stderr of a running agent). `transport._receipt` attaches the classification to every receipt and, for campaign-scoped classes, writes stop markers through `runner.request_stop`. `transport.execute` refuses prompts over the campaign's limit before admission. `health.snapshot` counts failures by class.

**Tech Stack:** Python 3.13 via uv, pytest (`tests/`), behave (`features/`), fake CLI in `tests/fake_cli.py`.

**Spec:** `notes/pathfinder-friction.tex` (sections Failure catalogue, H1, H2, S2, Decisions: apex agent handles everything except out-of-reach classes such as a usage limit). Roadmap: `plans/2026-10-01-0030-refactor-roadmap.md`.

## Global Constraints

- Run tests with `uv run --offline --locked pytest -q <path>`; the full suite is `uv run --offline --locked pytest -q` (takes more than two minutes) and `uv run --offline --locked behave --tags="not @sandbox and not @captain and not @shipwright"`.
- Classification reads only the transport outcome and the error parsed from structured events; never stderr of a completed session, never agent message text.
- Baseline on 1 October 2026 (commit 33f8baf): 216 passed, 1 failed. The failure, `tests/test_deployments.py::test_statarb_prepares_freezes_and_runs_the_candidate_engine`, predates this phase (statarb moved past the pinned commit) and is fixed in phase 7, not here.
- Receipt format may change (no backward compatibility needed), but existing receipt keys keep their meaning.
- Budgets are tokens and calls under subscription billing; do not add dollar logic.
- Default prompt limit: 1,000,000 characters (Codex CLI rejects above 1,048,576); campaign override `max_prompt_chars` in `campaign.json`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- A completed call whose answer text mentions "usage limit" or "429" is not a failure (Task 1 and Task 3 tests).
- A transient `error` event followed by `turn.completed` stays unclassified (Task 3 test).
- A quota failure on a coordinator arm stops the parent as well, so sibling arms do not launch (Task 4 test).
- A second campaign-scoped failure does not overwrite the first stop reason (Task 4 test).
- A prompt exactly at the limit is admitted; one character over is refused with a receipt and no launch (Task 5 test).

---

### Task 1: Failure classifier module

**Files:**
- Create: `pathfinder/failures.py`
- Test: `tests/test_failures.py`

**Interfaces:**
- Produces: `failures.Failure(cls: str, scope: str, retry: bool, reset_at: str | None)` with `.record() -> dict`; `failures.classify(outcome: str | None, error: str | None, extra_rules=()) -> Failure | None`; `failures.CLASSES` (tuple of class names); `failures.SCOPES` (dict class -> (scope, retry)).

- [ ] **Step 1: Write the failing tests** (signatures taken from the failure catalogue)

```python
# tests/test_failures.py
import pytest
from pathfinder import failures


@pytest.mark.parametrize("outcome,error,cls,scope", [
    ("error", "You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage ... try again at Oct 4th, 2026 2:07 AM.", "quota", "campaign"),
    ("error", "You've hit your session limit · resets 2:30pm", "quota", "campaign"),
    ("error", "unexpected status 401 Unauthorized: Incorrect API key provided", "auth", "campaign"),
    ("error", "Missing environment variable: ELM_API_KEY", "auth", "campaign"),
    ("error", "turn/start failed: Input exceeds the maximum length of 1048576 characters. input_too_large", "input_too_large", "call"),
    ("error", "This content was flagged for possible biological risk. If this seems wrong, try rephrasing", "refusal", "pair"),
    ("error", "API Error: Opus 5's safeguards flagged this message", "refusal", "pair"),
    ("error", "Selected model is at capacity. Please try a different model.", "rate", "call"),
    ("error", "HTTP 429 Too Many Requests", "rate", "call"),
    ("launch failed", "error: unexpected argument '--search' found", "launch", "campaign"),
    ("no session", "no session", "no_session", "call"),
    ("timeout", "timeout", "timeout", "call"),
    ("error", "CLI exited without a completed turn", "undiagnosed", "call"),
])
def test_catalogue_signatures(outcome, error, cls, scope):
    f = failures.classify(outcome, error)
    assert (f.cls, f.scope) == (cls, scope)


def test_completed_call_is_not_a_failure_whatever_it_says():
    assert failures.classify("completed", None) is None


def test_admission_refusal_is_not_classified_unless_oversize():
    assert failures.classify("refused", "budget: 9.10 projected against cap 9.00") is None
    assert failures.classify("refused", "input too large: 1000001 characters exceed 1000000").cls == "input_too_large"


def test_quota_reset_time_is_parsed():
    f = failures.classify("error", "You've hit your usage limit ... try again at Oct 4th, 2026 2:07 AM.")
    assert f.reset_at == "Oct 4th, 2026 2:07 AM"
    assert failures.classify("error", "You've hit your session limit · resets 2:30pm").reset_at == "2:30pm"


def test_record_is_plain_json():
    assert failures.classify("timeout", "timeout").record() == {
        "class": "timeout", "scope": "call", "retry": True, "reset_at": None}


def test_deployment_rules_come_first_and_must_name_a_known_class():
    import re
    rule = [("auth", re.compile(r"key file mode 0644"))]
    assert failures.classify("error", "key file mode 0644", extra_rules=rule).cls == "auth"
    with pytest.raises(ValueError):
        failures.classify("error", "x", extra_rules=[("mystery", re.compile("x"))])
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_failures.py`
Expected: FAIL with `ImportError: cannot import name 'failures'`.

- [ ] **Step 3: Implement the module**

```python
# pathfinder/failures.py
"""Failure classes for model calls, from the transport outcome and the error parsed out of the
provider's structured events (turn.failed, error, result with is_error). Never from the stderr of a
running agent or its message text: those carry tool output and research prose, which mention
capacity, authentication and limits for reasons of their own.

scope says how far a failure reaches: "call" (retrying later may work), "pair" (this pair's content is
the problem) or "campaign" (every further call will fail the same way until something outside the
engine changes: a usage limit resets, a key is replaced, a CLI is repaired)."""
from __future__ import annotations
import re
from dataclasses import dataclass

SCOPES = {
    "quota": ("campaign", False), "auth": ("campaign", False), "launch": ("campaign", False),
    "refusal": ("pair", False), "input_too_large": ("call", False),
    "rate": ("call", True), "no_session": ("call", True), "timeout": ("call", True),
    "undiagnosed": ("call", False),
}
CLASSES = tuple(SCOPES)

RULES = (
    ("quota", re.compile(r"usage limit|session limit|hit your limit|insufficient_quota|quota exceeded|credit balance", re.I)),
    ("auth", re.compile(r"\b401\b|unauthori[sz]ed|incorrect api key|invalid api key|authentication failed|missing environment variable", re.I)),
    ("input_too_large", re.compile(r"input_too_large|input too large|exceeds the maximum length|context length|prompt is too long", re.I)),
    ("refusal", re.compile(r"flagged for possible|safeguards flagged|content filter|usage polic", re.I)),
    ("rate", re.compile(r"\b429\b|rate limit|too many requests|at capacity|overloaded|\b503\b|service unavailable", re.I)),
)
RESET = re.compile(r"try again at ([^\n]+?)\.?\s*$|resets? (?:at )?([0-9][^\n,.]*)", re.I | re.M)
OUTCOMES = {"launch failed": "launch", "no session": "no_session", "timeout": "timeout"}


@dataclass(frozen=True)
class Failure:
    cls: str
    scope: str
    retry: bool
    reset_at: str | None = None

    def record(self) -> dict:
        return {"class": self.cls, "scope": self.scope, "retry": self.retry, "reset_at": self.reset_at}


def classify(outcome: str | None, error: str | None, extra_rules=()) -> Failure | None:
    """The failure a receipt records, or None for a completed call or an ordinary admission refusal.
    extra_rules, a deployment's (class, compiled pattern) pairs, are tried before the built-in rules."""
    for name, _ in extra_rules:
        if name not in SCOPES:
            raise ValueError(f"unknown failure class {name!r}; expected one of {', '.join(CLASSES)}")
    message = error or ""
    if outcome in (None, "completed") and not message:
        return None
    rules = (*extra_rules, *RULES)
    if outcome == "refused":
        if not RULES[2][1].search(message):
            return None
        cls = "input_too_large"
    elif outcome in OUTCOMES:
        cls = OUTCOMES[outcome]
    else:
        cls = next((name for name, pattern in rules if pattern.search(message)), "undiagnosed")
    scope, retry = SCOPES[cls]
    reset = None
    if cls == "quota":
        match = RESET.search(message)
        reset = (match.group(1) or match.group(2)).strip() if match else None
    return Failure(cls, scope, retry, reset)
```

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --offline --locked pytest -q tests/test_failures.py`
Expected: all PASS. If the reset assertion fails, adjust only `RESET` until both reset strings parse exactly as in the test.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/failures.py tests/test_failures.py
git commit -m "Classify model-call failures from structured provider errors

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Deployment failure rules as an extension point

**Files:**
- Modify: `pathfinder/extensions.py:1-17` (docstring and `SUPPORTED`)
- Modify: `pathfinder/failures.py` (add `rules_for`)
- Test: `tests/test_failures.py`

**Interfaces:**
- Consumes: `failures.classify(..., extra_rules=...)` from Task 1; `extensions.load(campaign, name)`.
- Produces: `failures.rules_for(campaign) -> tuple[(str, re.Pattern), ...]`; extension name `"failure_rules"` naming a module-level sequence of `(class, pattern_string)` pairs.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_failures.py
def test_campaign_failure_rules_extension(tmp_path):
    from stubcampaign import make
    c = make(tmp_path, extensions={"path": "deploy", "failure_rules": "drip_rules:RULES"})
    d = tmp_path / "deploy"; d.mkdir(exist_ok=True)
    (d / "drip_rules.py").write_text("RULES = [('contract', 'READY needs code and feeds')]\n")
    with pytest.raises(ValueError):                       # 'contract' is not a transport failure class
        failures.rules_for(c)
    (d / "drip_rules.py").write_text("RULES = [('auth', 'key file .* not 0600')]\n")
    import importlib, sys; sys.modules.pop("drip_rules", None)
    rules = failures.rules_for(c)
    assert failures.classify("error", "key file x not 0600", extra_rules=rules).cls == "auth"


def test_no_extension_means_no_extra_rules(tmp_path):
    from stubcampaign import make
    assert failures.rules_for(make(tmp_path)) == ()
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_failures.py -k rules`
Expected: FAIL with `AttributeError: module 'pathfinder.failures' has no attribute 'rules_for'`.

- [ ] **Step 3: Implement**

In `pathfinder/extensions.py`, change the docstring's supported-names sentence to include `failure_rules (a sequence of (failure class, regular expression) pairs tried before the built-in classification)` and set:

```python
SUPPORTED = {"admission", "snapshot_extra", "transport", "failure_rules"}
```

Append to `pathfinder/failures.py`:

```python
def rules_for(campaign) -> tuple:
    """A deployment's own failure rules, compiled and checked, or () when the campaign names none."""
    from . import extensions
    spec = extensions.load(campaign, "failure_rules")
    if spec is None:
        return ()
    compiled = tuple((name, re.compile(pattern, re.I)) for name, pattern in spec)
    for name, _ in compiled:
        if name not in SCOPES:
            raise ValueError(f"unknown failure class {name!r} in failure_rules; expected one of {', '.join(CLASSES)}")
    return compiled
```

- [ ] **Step 4: Run and see it pass**

Run: `uv run --offline --locked pytest -q tests/test_failures.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/extensions.py pathfinder/failures.py tests/test_failures.py
git commit -m "Let deployments register failure rules

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Receipts carry failure, prompt size and tool calls

**Files:**
- Modify: `tests/fake_cli.py` (add `FAKE_FAIL`, `FAKE_TOOLS`)
- Modify: `pathfinder/transport.py:97-133` (`_parse` error extraction), `:162-172` (`_receipt`), `:175-181` (`_failed`), `:189-211` (`_extension_call`), `:255-338` (`_execute`)
- Test: `tests/test_transport.py`

**Interfaces:**
- Consumes: `failures.classify`, `failures.rules_for` (Tasks 1 and 2).
- Produces: receipt keys `failure` (`None` or `Failure.record()`), `prompt_chars` (int or None), `tool_calls` (int or None); `transport._tool_calls(lines) -> int`; result dict key `failure` with the same value as the receipt.

- [ ] **Step 1: Extend the fake CLI**

In `tests/fake_cli.py`, update the docstring with `FAKE_FAIL: codex only, emit turn.failed with this message and exit 1. FAKE_TOOLS: number of command_execution items to emit before the reply.` Then, directly after the block that prints the session line, insert:

```python
if mode != "claude" and os.environ.get("FAKE_FAIL"):
    print(json.dumps({"type": "turn.failed", "error": {"message": os.environ["FAKE_FAIL"]}}), flush=True)
    sys.exit(1)
for i in range(int(os.environ.get("FAKE_TOOLS", "0"))):
    if mode == "claude":
        print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}}))
    else:
        print(json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": f"cmd {i}"}}))
```

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_transport.py
def test_quota_failure_is_classified_from_structured_events(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "codex")
    monkeypatch.setenv("FAKE_FAIL", "You've hit your usage limit ... try again at Oct 4th, 2026 2:07 AM.")
    r = transport.call("p", campaign=campaign(tmp_path, "codex"), model="m", tools=True, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="peer", actor="ada")
    assert r["error"].startswith("You've hit your usage limit")          # the message, not a dict repr
    row = rows(tmp_path)[0]
    assert row["failure"] == {"class": "quota", "scope": "campaign", "retry": False, "reset_at": "Oct 4th, 2026 2:07 AM"}
    assert r["failure"] == row["failure"]


def test_completed_call_mentioning_limits_is_not_a_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "codex"); monkeypatch.setenv("FAKE_REPLY", "the usage limit and HTTP 429 in the paper")
    transport.call("p", campaign=campaign(tmp_path, "codex"), model="m", tools=True, search=False, cwd=tmp_path,
                   timeout=10, thread="T", stage="peer", actor="ada")
    assert rows(tmp_path)[0]["failure"] is None


def test_receipt_records_prompt_size_and_tool_calls(tmp_path, monkeypatch):
    for mode in ("codex", "claude"):
        (tmp_path / "receipts.jsonl").unlink(missing_ok=True)
        monkeypatch.setenv("FAKE_MODE", mode); monkeypatch.setenv("FAKE_TOOLS", "3")
        transport.call("x" * 1234, campaign=campaign(tmp_path, mode), model="m", tools=True, search=False,
                       cwd=tmp_path, timeout=10, thread="T", stage="peer", actor="ada")
        row = rows(tmp_path)[0]
        assert (row["prompt_chars"], row["tool_calls"]) == (1234, 3)


def test_no_session_receipt_is_classified_and_sized(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_HANG", "1")
    transport.call("abc", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                   timeout=10, thread="T", stage="scan", actor="judge")
    row = rows(tmp_path)[0]
    assert row["failure"]["class"] == "no_session" and row["prompt_chars"] == 3 and row["tool_calls"] is None


def test_transient_error_then_completion_stays_unclassified(tmp_path):
    c = campaign(tmp_path, "codex")
    events = [{"type": "error", "message": "Reconnecting... 2/5 (stream disconnected before completion)"},
              {"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}},
              {"type": "turn.completed", "usage": {"input_tokens": 1}}]
    assert transport._parse(c, "m", [json.dumps(x) for x in events])[4] is None
```

- [ ] **Step 3: Run and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_transport.py`
Expected: the four new receipt tests FAIL with `KeyError: 'failure'` (or the error assertion shows a dict repr).

- [ ] **Step 4: Implement**

In `_parse`, replace the `error`/`turn.failed` branch with:

```python
        elif t in ("error", "turn.failed"):
            detail = row.get("error") or row.get("message") or t
            err = str(detail.get("message") or detail) if isinstance(detail, dict) else str(detail)
            terminal_failure = terminal_failure or t == "turn.failed"
```

Add after `_counters`:

```python
TOOL_ITEMS = {"command_execution", "web_search", "mcp_tool_call", "file_change"}


def _tool_calls(lines) -> int:
    """Tool uses the session reported: Codex items of a tool type, Claude tool_use content blocks."""
    count = 0
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if row.get("type") == "item.completed" and (row.get("item") or {}).get("type") in TOOL_ITEMS:
            count += 1
        elif row.get("type") == "assistant":
            count += sum(1 for block in (row.get("message") or {}).get("content") or []
                         if isinstance(block, dict) and block.get("type") == "tool_use")
    return count
```

Replace `_receipt` with:

```python
def _receipt(campaign, thread, stage, actor, model, r):
    """Append one receipt and classify the call; r gains the same "failure" value the receipt records."""
    from . import failures
    failure = failures.classify(r.get("outcome"), r.get("error"), failures.rules_for(campaign))
    r["failure"] = failure.record() if failure else None
    row = {"v": 3, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "run_id": getattr(campaign, "run_id", None),
           "thread": thread, "stage": stage,
           "actor": actor, "backend": campaign.backend, "model": model,
           **{k: r.get(k) for k in ("outcome", "seconds", "usage", "input_tokens", "output_tokens", "cache_write",
                                     "cache_read", "prefix_read", "cost", "cost_basis", "exit_status", "terminal_event",
                                     "raw_events", "error", "failure", "prompt_chars", "tool_calls")}}
    if r.get("rates"):
        row["rates"] = r["rates"]
    with open(campaign.path("receipts.jsonl"), "a") as f:
        f.write(json.dumps(row) + "\n")
    return failure
```

Change `_failed` to take the prompt size:

```python
def _failed(campaign, thread, stage, actor, model, started, outcome, error, prompt_chars=None):
    """A call that never reached a model session: a receipt with no usage and no cost."""
    r = {"text": "", "session": None, "seconds": round(time.time() - started, 1), "usage": None, "input_tokens": None,
         "output_tokens": None, "cache_write": None, "cache_read": None, "prefix_read": None, "cost": None,
         "cost_basis": None, "outcome": outcome, "error": error, "transport_failed": True,
         "prompt_chars": prompt_chars, "tool_calls": None}
    _receipt(campaign, thread, stage, actor, model, r)
    return r
```

In `_execute`, pass `prompt_chars=len(prompt)` to all three `_failed(...)` calls, and add to the final result dict `r`:

```python
          "prompt_chars": len(prompt), "tool_calls": _tool_calls(lines),
```

In `_extension_call`, before each `_receipt(...)` call set `r["prompt_chars"] = len(request.prompt)` (and `r.setdefault("tool_calls", raw.get("tool_calls"))` in the success path). Add `"failure", "prompt_chars", "tool_calls"` to `RESULT_KEYS`.

In `pathfinder/stub.py`, add `"prompt_chars": len(request.prompt), "tool_calls": 0` to the result dict it returns (line near 81) so stub receipts carry the fields.

- [ ] **Step 5: Run and see them pass, then the transport and stub suites**

Run: `uv run --offline --locked pytest -q tests/test_transport.py tests/test_stub_flow.py tests/test_failures.py`
Expected: all PASS. If an existing test asserts `row["v"] == 2`, change it to `3`: the receipt format changed on purpose.

- [ ] **Step 6: Commit**

```bash
git add tests/fake_cli.py pathfinder/transport.py pathfinder/stub.py tests/test_transport.py
git commit -m "Receipts record failure class, prompt size and tool calls

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Campaign-scoped failures stop the campaign and its parent

**Files:**
- Modify: `pathfinder/runner.py:97-98` (`request_stop`)
- Modify: `pathfinder/transport.py` (`_receipt` calls a stop helper)
- Modify: `pathfinder/failures.py` (add `stop_for`)
- Test: `tests/test_failures.py`, `tests/test_admission.py`

**Interfaces:**
- Consumes: `Failure` and `_receipt` returning it (Task 3); `admission._stop_marker`.
- Produces: `runner.request_stop(campaign, reason: str, **details)` writing `{"reason", "at", **details}`; `failures.stop_for(campaign, failure: Failure, error: str)`: writes stop markers on the campaign and, if `campaign.raw["parent"]` is set, on the parent root, without overwriting an existing marker.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_admission.py
def test_quota_failure_stops_campaign_and_parent_and_keeps_first_reason(tmp_path, monkeypatch):
    from pathfinder import failures
    parent = tmp_path / "parent"; parent.mkdir()
    c = make(tmp_path / "arm", parent="../parent")
    quota = failures.classify("error", "You've hit your usage limit ... try again at Oct 4th, 2026 2:07 AM.")
    failures.stop_for(c, quota, "usage limit")
    first = json.loads((c.root / "stop.json").read_text())
    assert first["failure"]["class"] == "quota" and first["reason"].startswith("quota")
    assert json.loads((parent / "stop.json").read_text())["failure"]["reset_at"] == "Oct 4th, 2026 2:07 AM"
    failures.stop_for(c, failures.classify("error", "401 Unauthorized"), "401")
    assert json.loads((c.root / "stop.json").read_text()) == first
    with pytest.raises(Refused):
        with admission.admission(c, "peer", "ada"):
            pass


def test_call_scoped_failure_does_not_stop(tmp_path):
    from pathfinder import failures
    c = make(tmp_path)
    failures.stop_for(c, failures.classify("timeout", "timeout"), "timeout")
    assert not (c.root / "stop.json").exists()
```

```python
# append to tests/test_transport.py
def test_quota_receipt_stops_the_campaign(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "codex"); monkeypatch.setenv("FAKE_FAIL", "You've hit your usage limit.")
    transport.call("p", campaign=campaign(tmp_path, "codex"), model="m", tools=True, search=False, cwd=tmp_path,
                   timeout=10, thread="T", stage="peer", actor="ada")
    assert json.loads((tmp_path / "stop.json").read_text())["failure"]["class"] == "quota"
```

`tests/stubcampaign.make` writes any keyword argument into `campaign.json`, so `parent="../parent"` needs no change there.

- [ ] **Step 2: Run and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_admission.py tests/test_transport.py -k "stop"`
Expected: FAIL with `AttributeError: ... has no attribute 'stop_for'`.

- [ ] **Step 3: Implement**

In `pathfinder/runner.py`:

```python
def request_stop(campaign, reason: str, **details):
    campaign.path("stop.json").write_text(json.dumps({"reason": reason, "at": _now(), **details}))
```

Append to `pathfinder/failures.py`:

```python
def stop_for(campaign, failure: Failure | None, error: str | None):
    """A campaign-scoped failure stops the campaign and, under a coordinator, its parent, so no further
    call is launched into the same wall. The first stop marker is kept: its reason is the root cause."""
    if failure is None or failure.scope != "campaign":
        return
    import json, time
    from pathlib import Path
    reason = f"{failure.cls}: {(error or '').strip()[:300]}"
    record = {"reason": reason, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "failure": failure.record()}
    roots = [Path(campaign.root)]
    parent = (campaign.raw or {}).get("parent")
    if parent:
        roots.append((Path(campaign.root) / parent).resolve())
    for root in roots:
        marker = root / "stop.json"
        if not marker.exists():
            marker.write_text(json.dumps(record))
```

In `transport._receipt`, after writing the row and before `return failure`, add:

```python
    failures.stop_for(campaign, failure, r.get("error"))
```

- [ ] **Step 4: Run and see them pass**

Run: `uv run --offline --locked pytest -q tests/test_admission.py tests/test_transport.py tests/test_failures.py tests/test_runner.py tests/test_coordinator.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/runner.py pathfinder/failures.py pathfinder/transport.py tests/test_admission.py tests/test_transport.py
git commit -m "Quota, auth and launch failures stop the campaign and its parent

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Prompt size gate before admission

**Files:**
- Modify: `pathfinder/transport.py:226-231` (`execute`), add `PromptTooLarge` and `max_prompt_chars`
- Test: `tests/test_transport.py`

**Interfaces:**
- Consumes: `_receipt` (Task 3), `failures.classify("refused", "input too large: ...")` returns `input_too_large` (Task 1).
- Produces: `transport.DEFAULT_MAX_PROMPT_CHARS = 1_000_000`; `transport.max_prompt_chars(campaign) -> int` reading `campaign.raw["max_prompt_chars"]`; `transport.PromptTooLarge(Exception)` with attribute `failure_class = "input_too_large"`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_transport.py
def test_prompt_at_limit_runs_and_one_over_is_refused_without_launch(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "codex")
    c = campaign(tmp_path, "codex"); c.raw["max_prompt_chars"] = 50
    r = transport.call("x" * 50, campaign=c, model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="verify", actor="judge")
    assert r["outcome"] == "completed"
    monkeypatch.setenv("PATHFINDER_CODEX", str(tmp_path / "must-not-launch"))
    with pytest.raises(transport.PromptTooLarge, match="51 characters exceed 50"):
        transport.call("x" * 51, campaign=c, model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="verify", actor="judge")
    row = rows(tmp_path)[-1]
    assert row["outcome"] == "refused" and row["prompt_chars"] == 51
    assert row["failure"]["class"] == "input_too_large" and row["usage"] is None
    assert not (tmp_path / "stop.json").exists()          # a call-scoped refusal, not a campaign stop
    assert not list((tmp_path / "active-calls").glob("*.json")) if (tmp_path / "active-calls").exists() else True


def test_default_limit():
    from pathfinder.config import Campaign
    assert transport.max_prompt_chars(Campaign(root=Path("."), backend="codex", model="m", scan_model="m",
                                               peer_search=False, seats=1, cut=1, rounds=1, allowances={},
                                               budget_usd=1, prices={}, scan_fulltext=None)) == 1_000_000
```

- [ ] **Step 2: Run and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_transport.py -k "limit"`
Expected: FAIL with `AttributeError: module 'pathfinder.transport' has no attribute 'PromptTooLarge'`.

- [ ] **Step 3: Implement**

Add near the top of `pathfinder/transport.py`, after `TransportFailed`:

```python
DEFAULT_MAX_PROMPT_CHARS = 1_000_000          # the Codex CLI rejects prompts over 1,048,576 characters


class PromptTooLarge(Exception):
    """A prompt over the campaign's limit: refused before admission, with a receipt and no launch."""
    failure_class = "input_too_large"


def max_prompt_chars(campaign) -> int:
    return int((campaign.raw or {}).get("max_prompt_chars", DEFAULT_MAX_PROMPT_CHARS))
```

Replace `execute` with:

```python
def execute(campaign, request: ModelRequest):
    """Refuse an oversized prompt, then admit the call, then record an active attempt before launching it,
    including abrupt-exit evidence. A refused call raises before any active-call record exists."""
    limit, size = max_prompt_chars(campaign), len(request.prompt)
    if size > limit:
        error = f"input too large: {size} characters exceed {limit}; no model call started"
        _receipt(campaign, request.thread, request.stage, request.actor, request.model, {
            "outcome": "refused", "seconds": 0.0, "usage": None, "input_tokens": None, "output_tokens": None,
            "cache_write": None, "cache_read": None, "prefix_read": None, "cost": None, "cost_basis": None,
            "error": error, "prompt_chars": size, "tool_calls": None})
        raise PromptTooLarge(error)
    from . import admission
    with admission.admission(campaign, request.stage, request.actor, thread=request.thread, model=request.model):
        return _attempt(campaign, request)
```

- [ ] **Step 4: Run and see them pass, then the unit suite in the background**

Run: `uv run --offline --locked pytest -q tests/test_transport.py`
Expected: all PASS.
Run: `uv run --offline --locked pytest -q` (more than two minutes)
Expected: all PASS. Any test that builds a prompt over one million characters on purpose must set `max_prompt_chars` in its campaign.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/transport.py tests/test_transport.py
git commit -m "Refuse oversized prompts before admission with a classified receipt

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Health snapshot counts failures by class

**Files:**
- Modify: `pathfinder/health.py:146-148` (failures list) and the `out` dict
- Test: `tests/test_health.py`

**Interfaces:**
- Consumes: receipt key `failure` (Task 3); `stop.json` `failure` key (Task 4).
- Produces: `snapshot()["failures_by_class"]: dict[str, int]`; each entry of `recent_failures` gains `"failure"`; a warning line when `stop.json` records a campaign-scoped failure, naming the class and reset time.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_health.py
def test_snapshot_counts_failures_by_class_and_explains_a_quota_stop(tmp_path):
    import json
    from pathfinder import health
    from stubcampaign import make
    c = make(tmp_path)
    rows = [{"outcome": "error", "error": "usage limit", "failure": {"class": "quota", "scope": "campaign", "retry": False, "reset_at": "Oct 4th"}},
            {"outcome": "timeout", "error": "timeout", "failure": {"class": "timeout", "scope": "call", "retry": True, "reset_at": None}},
            {"outcome": "completed", "error": None, "failure": None}]
    c.path("receipts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    c.path("stop.json").write_text(json.dumps({"reason": "quota: usage limit", "failure": rows[0]["failure"]}))
    s = health.snapshot(c)
    assert s["failures_by_class"] == {"quota": 1, "timeout": 1}
    assert s["recent_failures"][0]["failure"]["class"] == "quota"
    assert any("quota" in w and "Oct 4th" in w for w in s["warnings"])
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_health.py -k by_class`
Expected: FAIL with `KeyError: 'failures_by_class'`.

- [ ] **Step 3: Implement**

In `health.snapshot`, change `fields` for failures and add the counts:

```python
    fields = ("at", "thread", "stage", "actor", "outcome", "error")
    failures = [{**{k: row.get(k) for k in fields}, "failure": row.get("failure")} for row in receipts
                if row.get("error") or row.get("outcome") in {"timeout", "error", "launch failed", "no session"}]
    by_class = {}
    for row in receipts:
        name = (row.get("failure") or {}).get("class")
        if name:
            by_class[name] = by_class.get(name, 0) + 1
```

After `failure = inspect(campaign.path("health.json"))` add:

```python
    stop = inspect(campaign.path("stop.json"))
    stopped_by = (stop or {}).get("failure") or {}
    if stopped_by.get("scope") == "campaign":
        warnings.append(f"Stopped by a {stopped_by['class']} failure"
                        + (f"; resets {stopped_by['reset_at']}" if stopped_by.get("reset_at") else "")
                        + ". Retrying before that changes nothing; escalate to the operator if it needs a key or a repair.")
```

In `out`, replace `"stop": inspect(campaign.path("stop.json"))` with `"stop": stop` and add `"failures_by_class": by_class`.

- [ ] **Step 4: Run and see it pass, then health, monitor and supervise suites**

Run: `uv run --offline --locked pytest -q tests/test_health.py tests/test_monitor.py tests/test_supervise.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/health.py tests/test_health.py
git commit -m "Health snapshot counts failures by class and explains campaign stops

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Full verification, spec note and release check

**Files:**
- Modify: `notes/pathfinder-friction.tex` (mark H1 and H2 as implemented in phase 1, with commit ids)
- Modify: `features/operational/model-execution.feature` only if a behave scenario fails because of the receipt format change (update the expectation, not the behaviour)

- [ ] **Step 1: Run both suites**

Run: `uv run --offline --locked pytest -q` and `uv run --offline --locked behave --tags="not @sandbox and not @captain and not @shipwright"`
Expected: both green. Fix only expectations tied to receipt version `v` or the new keys.

- [ ] **Step 2: Record the result in the spec**

In `notes/pathfinder-friction.tex`, in the harvest table rows H1 and H2, append ``Done in phase 1 (commits ...).'' with the short commit ids from Tasks 1 to 6. Rebuild with `latexmk -pdf -interaction=nonstopmode notes/pathfinder-friction.tex` from `notes/` and run `/Users/v/.local/bin/style-ban-artifacts notes/pathfinder-friction.tex`.

- [ ] **Step 3: Commit**

```bash
git add notes/pathfinder-friction.tex notes/pathfinder-friction.pdf features
git commit -m "Phase 1 of the refactor complete: failure classes, campaign stops, size gate

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

# Phase 4a: Health policy, unserved-call retry, rate cooldown, failure classes on stops, allowance warnings, evidence unblock

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single unserved call or a single failed pair no longer drains a campaign: unserved calls (rate limit, no session, launch failure that is not campaign-wide) are retried once after a backoff, a rate limit puts the whole campaign in a short cooldown at admission, a pair failure is recorded and retried while the runner probes with one seat, and only a second consecutive failure raises the health flag. Stopped statuses carry their failure class, `pathfinder health` warns when an allowance is below observed call durations, and `pathfinder reconcile` unblocks a pair whose evidence has been repaired, recording the transition.

**Architecture:** `transport.execute` wraps one attempt in a bounded retry for unserved, retryable failures. A rate failure writes `cooldown.json`; `admission` defers while it is in the future. `runner._loop` keeps `consecutive_failures` in its metadata: the first pair failure is recorded in `failures.jsonl` and the runner switches to one seat; a success resets it; a second consecutive failure writes `health.json` as today. `TransportFailed` carries the failure record and the stages write it on their stopped status. `health.snapshot` compares allowances with timed-out and completed receipts. `reconcile.inspect` detects an evidence block that now resolves; `reconcile.apply` records the old state in the status `history` before resuming.

**Tech Stack:** Python 3.13, pytest with the stub backend and the fake CLI.

**Spec:** `notes/pathfinder-friction.tex`: H3, H1 remainder (429 deferral), H6 and F07 (reconcile), the S items on allowance calibration and failure class on stopped statuses. Phase 4b (separate plan): batch coordinator, launcher, aggregate view. Phase 4c: supervisor and atomic repairs.

## Global Constraints

- Tests: `uv run --offline --locked pytest -q <files>`; full suite over two minutes; never edit engine files while it runs.
- Baseline (ab1ee0d): 358 passed, 1 failed (statarb deployment); behave 93 passed, 1 failed, 9 error.
- A campaign-scoped failure (quota, auth, missing executable, launch streak) is never retried: phase 1's stop stands.
- Retry and cooldown durations come from `campaign.json` (`retry_backoff_seconds`, default 30; `unserved_retries`, default 1); tests set them to small values.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- A timed-out call (it reached the model and spent time) is not retried automatically (Task 1 test).
- A retry is a new attempt with its own receipt; the failed attempt's receipt stays (Task 1 test).
- One pair failure does not drain the run, two consecutive do; a success between them resets the count (Task 3 test).
- An editor that blocks one pair does not count as an operational failure of the campaign (Task 3 test).
- Reconcile does not unblock a pair whose evidence still fails, and says why (Task 6 test).

---

### Task 1: Retry unserved calls once

**Files:**
- Modify: `pathfinder/transport.py` (`execute`)
- Test: `tests/test_transport.py`

**Interfaces:**
- Produces: `transport.UNSERVED = {"rate", "no_session", "launch"}`; `transport.retry_policy(campaign) -> tuple[int, float]` (retries, backoff seconds). `execute` retries a result whose `failure` has `class` in `UNSERVED`, `scope != "campaign"` and `retry` true, at most `retries` times, sleeping `backoff` before each retry.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_transport.py
def _results(*classes):
    out = []
    for cls in classes:
        if cls is None:
            out.append({"text": "ok", "transport_failed": False, "error": None, "outcome": "completed", "failure": None})
        else:
            out.append({"text": "", "transport_failed": True, "error": cls, "outcome": "error",
                        "failure": {"class": cls, "scope": "call", "retry": cls != "timeout", "reset_at": None}})
    return out


def test_an_unserved_call_is_retried_once(tmp_path, monkeypatch):
    c = campaign(tmp_path, "codex"); c.raw.update(retry_backoff_seconds=0)
    queue = _results("rate", None)
    monkeypatch.setattr(transport, "_attempt", lambda campaign, request: queue.pop(0))
    r = transport.execute(c, transport.ModelRequest(identity="i", prompt="p", model="m", tools=False, search=False,
                                                    timeout=5, thread="T", stage="verify", actor="judge"))
    assert r["outcome"] == "completed" and queue == []


def test_timeouts_and_second_failures_are_not_retried(tmp_path, monkeypatch):
    c = campaign(tmp_path, "codex"); c.raw.update(retry_backoff_seconds=0)
    for classes, calls in ((("timeout", None), 1), (("no_session", "no_session", None), 2)):
        queue = _results(*classes)
        monkeypatch.setattr(transport, "_attempt", lambda campaign, request: queue.pop(0))
        r = transport.execute(c, transport.ModelRequest(identity="i", prompt="p", model="m", tools=False, search=False,
                                                        timeout=5, thread="T", stage="verify", actor="judge"))
        assert r["transport_failed"] and len(classes) - len(queue) == calls
```

- [ ] **Step 2: Run and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_transport.py -k "retried"`
Expected: the first FAILS (no retry); the second may pass for the timeout case and fail for `no_session` twice only if a retry exists: record what you see.

- [ ] **Step 3: Implement**

```python
UNSERVED = {"rate", "no_session", "launch"}          # the model never served the call: safe to ask again


def retry_policy(campaign) -> tuple[int, float]:
    raw = campaign.raw or {}
    return int(raw.get("unserved_retries", 1)), float(raw.get("retry_backoff_seconds", 30))
```

In `execute`, replace `return _attempt(campaign, request)` inside the admission block with a loop that leaves admission between attempts:

```python
    retries, backoff = retry_policy(campaign)
    for attempt in range(retries + 1):
        with admission.admission(campaign, request.stage, request.actor, thread=request.thread, model=request.model):
            result = _attempt(campaign, request)
        failure = result.get("failure") or {}
        if not (failure.get("class") in UNSERVED and failure.get("scope") != "campaign" and failure.get("retry")) \
                or attempt == retries:
            return result
        time.sleep(backoff)
    return result
```

Keep the size gate before the loop.

- [ ] **Step 4: Run, then transport and admission suites; commit**

Run: `uv run --offline --locked pytest -q tests/test_transport.py tests/test_admission.py`
Expected: all PASS. Existing tests that count receipts after a `no session` call now see two receipts if they run with the default retry; set `unserved_retries: 0` in those fixtures and record a ruling.

```bash
git add pathfinder/transport.py tests
git commit -m "Retry an unserved call once after a backoff

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Rate cooldown at admission

**Files:**
- Modify: `pathfinder/transport.py` (`_receipt` writes the cooldown), `pathfinder/admission.py` (defers during it)
- Test: `tests/test_admission.py`

**Interfaces:**
- Produces: `cooldown.json` at the campaign root `{"until": epoch seconds, "reason": str}`; `admission.cooldown(campaign) -> float` (seconds remaining, 0 when none).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_admission.py
def test_a_rate_limit_cools_the_whole_campaign_down(tmp_path):
    c = make(tmp_path, retry_backoff_seconds=0.4)
    transport._receipt(c, "Q1P1", "peer", "ada", "m", {"outcome": "error", "error": "HTTP 429 Too Many Requests"})
    assert 0 < admission.cooldown(c) <= 0.4
    started = time.time()
    with admission.admission(c, "peer", "emmy"):
        waited = time.time() - started
    assert waited >= 0.3
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_admission.py -k cools`
Expected: FAIL with `AttributeError: module 'pathfinder.admission' has no attribute 'cooldown'`.

- [ ] **Step 3: Implement**

In `transport._receipt`, after classification: when `failure` and `failure.cls == "rate"`, write `campaign.path("cooldown.json")` with `{"until": time.time() + retry_policy(campaign)[1], "reason": r.get("error")}` (atomic replace; keep the later `until` if one exists). In `admission.py`:

```python
def cooldown(campaign) -> float:
    import json
    path = Path(campaign.root) / "cooldown.json"
    try:
        until = float(json.loads(path.read_text()).get("until", 0))
    except (OSError, ValueError, TypeError):
        return 0.0
    return max(0.0, until - time.time())
```

In `admission()`, inside the loop after the stop-marker check and before asking the policy: `remaining = cooldown(campaign)`; if `remaining > 0`: `_cond.wait(timeout=min(remaining, STOP_POLL)); continue`.

- [ ] **Step 4: Run, then admission and transport suites; commit**

Run: `uv run --offline --locked pytest -q tests/test_admission.py tests/test_transport.py`
Expected: all PASS.

```bash
git add pathfinder/transport.py pathfinder/admission.py tests/test_admission.py
git commit -m "A rate limit cools the campaign down at admission

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Runner health policy: retry a failed pair, probe with one seat, flag on the second failure

**Files:**
- Modify: `pathfinder/runner.py` (`_loop`, `_work`)
- Test: `tests/test_runner.py`

**Interfaces:**
- Produces: `runner.json` metadata key `consecutive_failures`; while it is at least 1 the runner admits one pair at a time; `failures.jsonl` rows gain `"counted": bool`; an editor that ends `blocked` raises `runner.PairBlocked` (not counted, no health flag).

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_runner.py
def _flaky(monkeypatch, plan):
    from pathfinder import research, transport
    real = research.run_thread
    def run_thread(campaign, pair_id, stop=lambda: False):
        if plan and plan.pop(0):
            raise transport.TransportFailed(pair_id)
        return real(campaign, pair_id, stop=stop)
    monkeypatch.setattr(research, "run_thread", run_thread)


def test_one_pair_failure_is_retried_without_draining(tmp_path, monkeypatch):
    from pathfinder import runner
    from stubcampaign import make
    c = make(tmp_path, pairs=("Q1P1",))
    _flaky(monkeypatch, [True])
    runner.run(c, interval=0.01)
    assert not c.path("health.json").exists()
    rows = [json.loads(l) for l in c.path("failures.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["counted"] is True


def test_two_consecutive_failures_raise_the_health_flag(tmp_path, monkeypatch):
    from pathfinder import runner
    from stubcampaign import make
    c = make(tmp_path, pairs=("Q1P1",))
    _flaky(monkeypatch, [True, True])
    runner.run(c, interval=0.01)
    assert c.path("health.json").exists()


def test_an_editor_block_is_not_an_operational_failure(tmp_path, monkeypatch):
    from pathfinder import edit, runner
    from stubcampaign import make
    c = make(tmp_path, pairs=("Q1P1",))
    monkeypatch.setattr(edit, "run", lambda campaign, pair_id, stop=lambda: False: (
        edit._set(campaign, pair_id, status="blocked", reason="no note"), "blocked")[1])
    runner.run(c, interval=0.01)
    assert not c.path("health.json").exists()
```

Read `tests/test_runner.py` first for how existing tests call `runner.run` (its signature and whether it needs a run context) and adapt the three calls to the same form.

- [ ] **Step 2: Run and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_runner.py -k "retried_without or consecutive or editor_block"`
Expected: the first and third FAIL (health flag written on the first failure).

- [ ] **Step 3: Implement**

Add near `request_stop`:

```python
class PairBlocked(Exception):
    """A pair ended blocked in a stage (for example the editor wrote no note): the pair waits, the run goes on."""
```

In `_work`, replace `raise RuntimeError(f"editor {edited}: ...")` with `raise PairBlocked(f"editor {edited}: ...")` when `edited == "blocked"`, and keep `RuntimeError` for other non-done results (for example `stopped` after a transport failure, which is counted).

In `_loop`: initialise `metadata.setdefault("consecutive_failures", 0)`; when admitting, use `seats = 1 if metadata["consecutive_failures"] else campaign.seats` instead of `campaign.seats`; on a successful future set `metadata["consecutive_failures"] = 0`; in the exception branch:

```python
            except PairBlocked as e:
                print(f"{_now()} {pair_id}: blocked ({e})")
                with campaign.path("failures.jsonl").open("a") as stream:
                    stream.write(json.dumps({"run_id": campaign.run_id, "at": _now(), "pair": pair_id, "stage": "edit",
                                             "reason": str(e), "counted": False}) + "\n")
            except Exception as e:
                print(f"{_now()} {pair_id}: error {e!r}")
                metadata["consecutive_failures"] = metadata.get("consecutive_failures", 0) + 1
                failure = {"run_id": campaign.run_id, "at": _now(), "pair": pair_id,
                           "stage": getattr(e, "stage", None), "reason": repr(e), "receipts": "receipts.jsonl",
                           "counted": True, "consecutive": metadata["consecutive_failures"]}
                with campaign.path("failures.jsonl").open("a") as stream:
                    stream.write(json.dumps(failure) + "\n")
                if metadata["consecutive_failures"] >= 2 and not unhealthy(campaign):
                    health.write(campaign.path("health.json"), failure)
                    alerts.emit(campaign, "runner stage failed twice in a row", campaign.path("health.json"))
```

A pair that failed is stopped, not blocked, so `pending` offers it again on the next pass; this is the retry. `pending` already skips `BLOCKED`; an editor-blocked pair has edit `blocked`, so `pending` would offer it again forever: exclude pairs whose edit status is `blocked` in `pending` as well.

- [ ] **Step 4: Run, then runner, bounded, health and coordinator suites; commit**

Run: `uv run --offline --locked pytest -q tests/test_runner.py tests/test_bounded.py tests/test_health.py tests/test_coordinator.py`
Expected: all PASS. Existing tests that expected a health flag after one failure now need two failures; update them and record a ruling.

```bash
git add pathfinder/runner.py tests
git commit -m "Health policy: a failed pair is retried with one seat, the second consecutive failure raises the flag

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Stopped statuses carry their failure class

**Files:**
- Modify: `pathfinder/transport.py` (`TransportFailed`), `pathfinder/research.py`, `pathfinder/edit.py`, `pathfinder/paper.py` (raise sites and stopped statuses)
- Test: `tests/test_prompt_limit_stages.py` (rename not needed; add tests there)

**Interfaces:**
- Produces: `TransportFailed(pair_id, failure: dict | None = None)` with attribute `failure`; stopped statuses `{"status": "stopped", "reason": "transport failed: <class>", "failure": {...}}`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_prompt_limit_stages.py
def test_a_stopped_thread_records_the_failure_class(tmp_path, monkeypatch):
    c = make(tmp_path)
    timeout = {"text": "", "seconds": 1.0, "transport_failed": True, "error": "timeout", "outcome": "timeout",
               "failure": {"class": "timeout", "scope": "call", "retry": True, "reset_at": None}}
    monkeypatch.setattr(research.transport, "execute", lambda campaign, request: timeout)
    with pytest.raises(transport.TransportFailed) as raised:
        research.run_thread(c, "Q1P1")
    assert raised.value.failure["class"] == "timeout"
    s = research.status(c, "Q1P1")
    assert s["status"] == "stopped" and s["failure"]["class"] == "timeout" and s["reason"] == "transport failed: timeout"
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_prompt_limit_stages.py -k failure_class`
Expected: FAIL (`TransportFailed` has no `failure`).

- [ ] **Step 3: Implement**

```python
class TransportFailed(Exception):
    """Raised by callers when a call never reached a model session, or failed in transport."""

    def __init__(self, pair_id, failure: dict | None = None):
        super().__init__(pair_id)
        self.failure = failure
```

At every `raise transport.TransportFailed(pair_id)` that follows a result `r` (research `_peers`, `_stage_call`, composable `execute`; edit; paper author and review), pass `failure=r.get("failure")`. Where a stage writes `status="stopped", reason="transport failed"` with the result in hand, write `reason=f"transport failed: {(r.get('failure') or {}).get('class', 'unknown')}", failure=r.get("failure")`. In `research.run_thread`'s and `_run_composable`'s `except transport.TransportFailed as e:` write the same from `e.failure`.

- [ ] **Step 4: Run, then research, edit, paper and behave; commit**

Run: `uv run --offline --locked pytest -q tests/test_prompt_limit_stages.py tests/test_research_revisions.py tests/test_edit.py tests/test_paper.py tests/test_stub_flow.py` and behave.
Expected: all PASS; behave at baseline. A scenario matching the exact reason "transport failed" needs its expectation widened to a prefix match; record the ruling.

```bash
git add pathfinder tests features
git commit -m "Stopped statuses carry their failure class

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Allowance warnings from observed durations

**Files:**
- Modify: `pathfinder/health.py` (`snapshot`)
- Test: `tests/test_health.py`

**Interfaces:**
- Produces: `health.ALLOWANCE_KEYS = {"peer": "peer_seconds", "consolidate": "consolidate_seconds", "verify": "verify_seconds", "edit": "edit_seconds", "author": "paper_seconds", "review": "review_seconds"}`; snapshot key `allowances` = `[{"stage", "allowance", "timeouts", "longest_completed_seconds"}]` for stages with receipts; a warning per stage with timeouts: `"<n> <stage> call(s) timed out at the <a> s allowance (<key>); completed <stage> calls took up to <m> s."`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_health.py
def test_snapshot_warns_when_an_allowance_is_below_observed_durations(tmp_path):
    import json
    from pathfinder import health
    from stubcampaign import make
    c = make(tmp_path)
    rows = [{"stage": "edit", "outcome": "timeout", "seconds": 240.0, "error": "timeout"},
            {"stage": "edit", "outcome": "completed", "seconds": 410.0}]
    c.path("receipts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    s = health.snapshot(c)
    row = next(a for a in s["allowances"] if a["stage"] == "edit")
    assert (row["timeouts"], row["longest_completed_seconds"], row["allowance"]) == (1, 410.0, 60)
    assert any("edit_seconds" in w and "410" in w for w in s["warnings"])
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_health.py -k allowance`
Expected: FAIL with `KeyError: 'allowances'`.

- [ ] **Step 3: Implement** in `snapshot`, after loading receipts: group by `stage` for stages in `ALLOWANCE_KEYS`, count `outcome == "timeout"`, take the longest `seconds` of completed calls, read `campaign.allowances.get(key)`, add the list to `out["allowances"]` and the warnings for stages with timeouts.

- [ ] **Step 4: Run, then health and monitor suites; commit**

Run: `uv run --offline --locked pytest -q tests/test_health.py tests/test_monitor.py`
Expected: all PASS.

```bash
git add pathfinder/health.py tests/test_health.py
git commit -m "Health warns when an allowance is below observed call durations

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Reconcile unblocks a repaired evidence block, with a recorded transition

**Files:**
- Modify: `pathfinder/reconcile.py`
- Test: `tests/test_evidence.py`

**Interfaces:**
- Produces: `inspect` actions `"unblock: evidence repaired"` and `"nothing: evidence still blocked: <first error>"` for a BLOCKED pair whose reason comes from an evidence error (the status carries no `failure` and the reason starts with one of the evidence prefixes); `apply` appends `{"at", "from_status", "from_reason", "action"}` to the status `history` list before resuming.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_evidence.py
def test_reconcile_unblocks_only_after_the_evidence_is_repaired(tmp_path):
    from pathfinder import reconcile, research
    from pathfinder.ledger import Ledger
    from stubcampaign import make
    c = make(tmp_path, research_scheme="eva_minus", strict_evidence=True, imported_research=True)
    d = research.prepare(c, "Q1P1")
    Ledger(d / "ledger.jsonl").add("ada", "finding", "see ada/result.json")
    research.run_thread(c, "Q1P1")
    assert research.status(c, "Q1P1")["status"] == "BLOCKED"
    assert reconcile.inspect(c, "Q1P1")["action"].startswith("nothing: evidence still blocked: missing evidence: ada/result.json")
    (d / "ada" / "result.json").write_text("{}")
    assert reconcile.inspect(c, "Q1P1")["action"] == "unblock: evidence repaired"
    reconcile.apply(c, "Q1P1")
    s = research.status(c, "Q1P1")
    assert s["status"] != "BLOCKED" or "missing evidence" not in (s.get("reason") or "")
    assert s["history"][0]["from_status"] == "BLOCKED" and s["history"][0]["action"] == "unblock: evidence repaired"
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_evidence.py -k reconcile`
Expected: FAIL (inspect returns a stage action, not the evidence check).

- [ ] **Step 3: Implement**

In `reconcile.py`:

```python
EVIDENCE_PREFIXES = ("missing evidence:", "aliased evidence path:", "evidence outside the investigation:",
                     "unreadable evidence:", "evidence not inlinable as text:", "Invalid external citation declaration",
                     "Aliased evidence", "Unreadable evidence")


def _evidence_check(campaign, pair_id) -> str | None:
    """None when the pair's review material now builds; otherwise the first evidence error."""
    try:
        research._review_material(campaign, pair_id)
    except research.EvidenceUnavailable as error:
        return str(error)
    return None
```

In `inspect`, before the stage-based branches: if `s.get("status") == "BLOCKED"` and `(s.get("reason") or "").startswith(EVIDENCE_PREFIXES)`, run `_evidence_check`; set `action = "unblock: evidence repaired"` when it returns None, else `f"nothing: evidence still blocked: {problem}"`. In `apply`, for the unblock action, append the history record and `research._set(campaign, pair_id, status="running", reason=None, history=history)` (keep `stage` and retained requests), then run as the existing BLOCKED branch does.

- [ ] **Step 4: Run, then evidence, reconcile-related suites and behave; commit**

Run: `uv run --offline --locked pytest -q tests/test_evidence.py tests/test_research_revisions.py` and behave.
Expected: all PASS; behave at baseline.

```bash
git add pathfinder/reconcile.py tests/test_evidence.py
git commit -m "Reconcile unblocks a repaired evidence block and records the transition

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Verification and spec

- [ ] Full pytest (baseline failure only) and behave (baseline).
- [ ] In `notes/pathfinder-friction.tex`, mark H3, the H1 429 deferral, H6 and F07, and the two S items (allowance calibration, failure class on stopped statuses) as done in phase 4a with commit ids; rebuild; style gate; commit.

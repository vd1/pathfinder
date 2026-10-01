# Phase 3a: Agent workspace, evidence by reference and session economy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agents get a workspace that works inside their sandbox (a self-contained ledger helper, a local temporary directory and TeX caches), large evidence and large papers reach them by reference (path, size, sha256) instead of being pasted into every prompt, the verifier reads with a read-only sandbox, and receipts count tool errors, so the token cost of sessions falls and environment friction becomes visible.

**Architecture:** The thread directory gains `.pathfinder/` with a copy of `pathfinder/ledger.py` (stdlib only) and the agent's `tmp/` and TeX cache. `transport._env` points `TMPDIR`, `TMPPREFIX` and `TEXMFVAR` there. `research._assessment_evidence` and `_bundle_evidence` keep every validation they do today and, by default, list each evidence file with its size and sha256 instead of its text, so the material hash still binds the exact bytes. `thread_head` lists the two papers by reference when they exceed a campaign budget. `ModelRequest` gains `reads`, which gives Codex a read-only sandbox with its shell and Claude only Read, Glob and Grep. Receipts gain `tool_errors` and up to five samples.

**Tech Stack:** Python 3.13, pytest with the fake CLI and the stub backend, behave.

**Spec:** `notes/pathfinder-friction.tex`: D4, S1, S2, the S item on the agent sandbox environment (proofTree, J2, SA), the julien-2 joint-reference handover (read-only readers, hash-bound index, validation kept). Phase 3b (separate plan) builds the typed evidence inventory and resolver (F01 to F06, F08, R01, R03) on the index introduced here.

## Global Constraints

- Tests: `uv run --offline --locked pytest -q <files>`; the full suite takes more than two minutes; never edit engine files while it runs.
- Baseline (commit cfacd7f): 300 passed, 1 failed (`tests/test_deployments.py::test_statarb_prepares_freezes_and_runs_the_candidate_engine`, pre-existing); behave 93 passed, 1 failed, 9 error.
- Evidence validation behaviour (aliased, outside, missing under `strict_evidence`) must not change; only the presentation of readable files changes.
- `"inline_evidence": true` in `campaign.json` restores today's inlined evidence; `"inline_papers_max_chars"` (default 400000) bounds inlined papers.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- Changing one byte of a referenced evidence file changes the review material, so a retained response is still detected as stale (Task 4 test).
- An aliased or outside evidence path still blocks before any call when evidence is by reference (Task 4 test).
- The ledger helper works from the thread directory with an environment that cannot import `pathfinder` (Task 1 test).
- A read-only verifier cannot write in its working directory under Codex (Task 6 test on the command line; the sandbox itself is the CLI's).
- Papers just under the budget stay inline; just over, both are referenced (Task 5 test).

---

### Task 1: Self-contained ledger helper in every thread

**Files:**
- Modify: `pathfinder/research.py` (`prepare`, the two helper strings at the peer prompt sites)
- Test: `tests/test_agent_workspace.py`

**Interfaces:**
- Produces: `research.HELPER_DIR = ".pathfinder"`; `research.install_helper(d: Path) -> str` returning the command prefix `f"{sys.executable} .pathfinder/ledger.py --root ."`; `prepare` calls it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_agent_workspace.py
import json, os, subprocess, sys
from pathlib import Path
from pathfinder import research, ledger
from stubcampaign import make


def test_helper_is_copied_and_runs_without_importing_pathfinder(tmp_path):
    c = make(tmp_path)
    d = research.prepare(c, "Q1P1")
    script = d / ".pathfinder" / "ledger.py"
    assert script.read_bytes() == Path(ledger.__file__).read_bytes()
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH",)}
    run = lambda *a: subprocess.run([sys.executable, "-I", ".pathfinder/ledger.py", "--root", ".", *a],
                                    cwd=d, env=env, capture_output=True, text=True)
    assert run("--actor", "ada", "add", "--kind", "idea", "--text", "x").returncode == 0
    out = run("--actor", "ada", "read")
    assert out.returncode == 0 and "[ada/idea] x" in out.stdout


def test_peer_prompts_use_the_workspace_helper(tmp_path, monkeypatch):
    c = make(tmp_path)
    prompts = []
    real = research.transport.execute
    def capture(campaign, request):
        prompts.append(request.prompt)
        return real(campaign, request)
    monkeypatch.setattr(research.transport, "execute", capture)
    research.run_thread(c, "Q1P1")
    peer = [p for p in prompts if ".pathfinder/ledger.py" in p]
    assert peer and not any("-m pathfinder.ledger" in p for p in prompts)
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_agent_workspace.py`
Expected: FAIL (`.pathfinder/ledger.py` missing; prompts use `-m pathfinder.ledger`).

- [ ] **Step 3: Implement**

In `pathfinder/research.py`, near the top-level helpers:

```python
HELPER_DIR = ".pathfinder"


def install_helper(d: Path) -> str:
    """Copy the ledger helper into the thread: agents run it as a script, because their sandbox may not
    reach the environment that imports pathfinder (seen in J2, statarb and proofTree). Returns the command."""
    from . import ledger as ledger_module
    target = d / HELPER_DIR / "ledger.py"
    source = Path(ledger_module.__file__).read_bytes()
    if not target.is_file() or target.read_bytes() != source:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source)
    return f"{sys.executable} {HELPER_DIR}/ledger.py --root ."
```

At the end of `prepare(campaign, pair_id)`, before it returns the thread directory, call `install_helper(d)` (use the variable name `prepare` already uses for the directory). In `_peers`, replace `helper = f"{sys.executable} -m pathfinder.ledger --root ."` with `helper = install_helper(d)`. In the composable request builder, replace `LEDGER=f"{sys.executable} -m pathfinder.ledger --root . --actor {actor}"` with `LEDGER=f"{install_helper(d)} --actor {actor}"`.

Check `pathfinder/ledger.py` imports only the standard library (it does at commit cfacd7f: `argparse, fcntl, json, time, pathlib`); if a later change adds a package import, this task's first test fails and the helper must stay stdlib-only.

- [ ] **Step 4: Run and see them pass, then the research suites**

Run: `uv run --offline --locked pytest -q tests/test_agent_workspace.py tests/test_stub_flow.py tests/test_research_revisions.py tests/test_ledger.py`
Expected: all PASS. If a test or behave scenario asserts the old `-m pathfinder.ledger` string, update it to the helper path and record a ruling.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/research.py tests/test_agent_workspace.py
git commit -m "Self-contained ledger helper in every thread

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Workspace-local temporary directory and TeX cache for agents

**Files:**
- Modify: `pathfinder/transport.py` (`_env` takes the working directory; `_execute` passes it)
- Test: `tests/test_agent_workspace.py`

**Interfaces:**
- Produces: `transport._env(campaign, cwd: Path | None = None) -> dict` setting `TMPDIR`, `TMPPREFIX` and `TEXMFVAR` under `cwd/.pathfinder/` when `cwd` is given, creating the directories.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_agent_workspace.py
def test_agent_environment_keeps_temporary_files_and_tex_caches_in_the_workspace(tmp_path):
    from pathfinder import transport
    c = make(tmp_path)
    env = transport._env(c, tmp_path / "threads" / "Q1P1")
    base = tmp_path / "threads" / "Q1P1" / ".pathfinder"
    assert env["TMPDIR"] == str(base / "tmp") and (base / "tmp").is_dir()
    assert env["TMPPREFIX"] == str(base / "tmp" / "zsh")
    assert env["TEXMFVAR"] == str(base / "texmf-var") and (base / "texmf-var").is_dir()
    assert "TEXINPUTS" in env
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_agent_workspace.py -k environment`
Expected: FAIL with `TypeError: _env() takes 1 positional argument but 2 were given`.

- [ ] **Step 3: Implement**

Change the signature and add, before `return env`:

```python
def _env(campaign, cwd=None):
    ...
    if cwd is not None:                            # the agent's shell, here-documents and TeX write inside its workspace
        base = Path(cwd) / ".pathfinder"
        (base / "tmp").mkdir(parents=True, exist_ok=True)
        (base / "texmf-var").mkdir(parents=True, exist_ok=True)
        env.update(TMPDIR=str(base / "tmp"), TMPPREFIX=str(base / "tmp" / "zsh"), TEXMFVAR=str(base / "texmf-var"))
    return env
```

In `_execute`, change `env=_env(campaign)` to `env=_env(campaign, cwd)`. Search for other callers of `_env(` and leave them unchanged (they pass no `cwd`).

- [ ] **Step 4: Run and see it pass, then the transport suite**

Run: `uv run --offline --locked pytest -q tests/test_agent_workspace.py tests/test_transport.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/transport.py tests/test_agent_workspace.py
git commit -m "Agents keep temporary files and TeX caches in their workspace

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Receipts count tool errors

**Files:**
- Modify: `tests/fake_cli.py` (`FAKE_TOOL_FAIL`), `pathfinder/transport.py` (`_tool_errors`, receipt keys, events)
- Test: `tests/test_transport.py`

**Interfaces:**
- Produces: `transport._tool_errors(lines) -> tuple[int, list[str]]` (count, up to five samples of at most 200 characters); receipt and `call_finished` event keys `tool_errors`, receipt key `tool_error_samples`.

- [ ] **Step 1: Extend the fake CLI** with, inside the `FAKE_TOOLS` loop for codex, a failing item when `i < int(os.environ.get("FAKE_TOOL_FAIL", "0"))`:

```python
        failed = i < int(os.environ.get("FAKE_TOOL_FAIL", "0"))
        print(json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": f"cmd {i}",
                          "exit_code": 1 if failed else 0,
                          "aggregated_output": "No module named pathfinder.ledger" if failed else "ok"}}))
```

and for claude, after each `tool_use` block, when failing, a user message with a `tool_result` block `{"type": "tool_result", "is_error": true, "content": "No module named pathfinder.ledger"}`.

- [ ] **Step 2: Write the failing test**

```python
# append to tests/test_transport.py
def test_receipt_counts_tool_errors_with_samples(tmp_path, monkeypatch):
    for mode in ("codex", "claude"):
        (tmp_path / "receipts.jsonl").unlink(missing_ok=True)
        monkeypatch.setenv("FAKE_MODE", mode); monkeypatch.setenv("FAKE_TOOLS", "4"); monkeypatch.setenv("FAKE_TOOL_FAIL", "2")
        transport.call("p", campaign=campaign(tmp_path, mode), model="m", tools=True, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="peer", actor="ada")
        row = rows(tmp_path)[0]
        assert row["tool_calls"] == 4 and row["tool_errors"] == 2
        assert all("No module named pathfinder.ledger" in s for s in row["tool_error_samples"])
```

- [ ] **Step 3: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_transport.py -k tool_errors`
Expected: FAIL with `KeyError: 'tool_errors'`.

- [ ] **Step 4: Implement**

```python
def _tool_errors(lines) -> tuple[int, list[str]]:
    """Failed tool uses the session reported (Codex non-zero exit codes, Claude tool results marked as
    errors), with up to five samples of their output, so environment friction shows in the receipt."""
    count, samples = 0, []
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        texts = []
        item = row.get("item") or {}
        if row.get("type") == "item.completed" and item.get("type") == "command_execution" and item.get("exit_code") not in (0, None):
            texts.append(str(item.get("aggregated_output") or f"exit {item.get('exit_code')}"))
        if row.get("type") == "user":
            for block in (row.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_result" and block.get("is_error"):
                    texts.append(str(block.get("content")))
        for text in texts:
            count += 1
            if len(samples) < 5:
                samples.append(text.strip()[-200:])
    return count, samples
```

In `_execute`, compute `errors, samples = _tool_errors(lines)` and add `"tool_errors": errors, "tool_error_samples": samples` to `r`. In `_failed` and the size-gate receipt add `"tool_errors": None, "tool_error_samples": None`. Add both keys to `RESULT_KEYS` and to the receipt key tuple in `_receipt`, and `tool_errors=r.get("tool_errors")` to the `call_finished` event.

- [ ] **Step 5: Run and see it pass, then the transport suite; commit**

Run: `uv run --offline --locked pytest -q tests/test_transport.py tests/test_events.py`
Expected: all PASS.

```bash
git add tests/fake_cli.py pathfinder/transport.py tests/test_transport.py
git commit -m "Receipts count tool errors with samples

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Evidence by reference, hash-bound, with validation kept

**Files:**
- Modify: `pathfinder/research.py` (`_assessment_evidence`, `_bundle_evidence`, `_review_material`)
- Test: `tests/test_agent_workspace.py`; existing tests that assert inlined artefact text

**Interfaces:**
- Produces: `_assessment_evidence(campaign, d, references=None, by_reference=False)`; `_bundle_evidence(campaign, d, by_reference=False)`; `research.evidence_by_reference(campaign) -> bool` (`not campaign.raw.get("inline_evidence", False)`); `research.READING` (the reading guidance string). A referenced file renders as `## <path>\n\n(file in your working directory: <n> bytes, sha256 <hex>; read it with your tools)`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_agent_workspace.py
import pytest


def _composable(tmp_path, **raw):
    c = make(tmp_path, research_scheme="eva_minus", **raw)
    d = research.prepare(c, "Q1P1")
    (d / "ada").mkdir(exist_ok=True)
    (d / "ada" / "derivation.txt").write_text("the derivation " * 1000)
    return c, d


def test_review_material_lists_evidence_by_size_and_digest(tmp_path):
    import hashlib
    c, d = _composable(tmp_path)
    material = research._review_material(c, "Q1P1")
    data = (d / "ada" / "derivation.txt").read_bytes()
    assert hashlib.sha256(data).hexdigest() in material and "the derivation the derivation" not in material
    assert research.READING in material


def test_one_changed_byte_changes_the_material(tmp_path):
    c, d = _composable(tmp_path)
    before = research._review_material(c, "Q1P1")
    (d / "ada" / "derivation.txt").write_text("the derivatioN " * 1000)
    assert research._review_material(c, "Q1P1") != before


def test_aliased_evidence_still_blocks_by_reference(tmp_path):
    c, d = _composable(tmp_path)
    (tmp_path / "outside.txt").write_text("secret")
    os.symlink(tmp_path / "outside.txt", d / "ada" / "link.txt")
    with pytest.raises(research.EvidenceUnavailable):
        research._review_material(c, "Q1P1")


def test_inline_evidence_switch_restores_the_text(tmp_path):
    c, d = _composable(tmp_path, inline_evidence=True)
    assert "the derivation the derivation" in research._review_material(c, "Q1P1")
```

- [ ] **Step 2: Run and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_agent_workspace.py -k "material or aliased or inline_evidence"`
Expected: the first two FAIL (text is inlined, `READING` missing); the aliased test may already pass, and the switch test passes once `inline_evidence` is honoured.

- [ ] **Step 3: Implement**

Add near `evidence_pointer`:

```python
READING = ("Files listed by path, size and sha256 are in your working directory, not pasted here. Read them in "
           "slices with your tools (rg -n, sed -n 'a,bp', head) as far as the task needs, read each file once, and "
           "quote by path and line.")


def evidence_by_reference(campaign) -> bool:
    return not (campaign.raw or {}).get("inline_evidence", False)
```

In `_assessment_evidence`, add the parameter `by_reference=False` and, after the existing successful `data = path.read_bytes()` (validation already done above it), insert:

```python
        if by_reference:
            parts.append(f"## {relative}\n\n(file in your working directory: {len(data)} bytes, "
                         f"sha256 {hashlib.sha256(data).hexdigest()}; read it with your tools)")
            continue
```

In `_bundle_evidence`, add `by_reference=False` and pass it to `_assessment_evidence(campaign, root, by_reference=by_reference)`; the bundle's `ledger.jsonl` stays inline (it is the joint stage's primary material). In `_review_material`, compute `by_reference = evidence_by_reference(campaign)`, pass it to both calls, and when true append `"\n\n" + READING` after the evidence. Append `READING` also to the text returned by `evidence_pointer`.

- [ ] **Step 4: Run, then the research suites and behave; fix expectations that assert inlined artefacts**

Run: `uv run --offline --locked pytest -q tests/test_agent_workspace.py tests/test_research_revisions.py tests/test_stub_flow.py` and `uv run --offline --locked behave --tags="not @sandbox and not @captain and not @shipwright"`.
Expected: new tests PASS. Existing tests or scenarios that assert artefact text inside review material (planks such as "the request contains the complete calculation evidence") fail; for each, set `"inline_evidence": true` in that fixture's campaign so it keeps covering inline mode, and record one ruling listing them. The behave totals must return to the baseline counts.

- [ ] **Step 5: Commit**

```bash
git add pathfinder/research.py tests features
git commit -m "Evidence reaches reviewers by reference, bound by sha256, with validation unchanged

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Papers by reference above a budget

**Files:**
- Modify: `pathfinder/research.py` (`thread_head` and its callers in `_consolidate_prompt` and `_review_material`)
- Test: `tests/test_agent_workspace.py`

**Interfaces:**
- Produces: `thread_head(d, inp, papers=True, ledger=True, inline_limit=None)`; `research.papers_limit(campaign) -> int` (`campaign.raw.get("inline_papers_max_chars", 400_000)`). Over the limit, each paper renders as `## <name>\n\n(file inputs/<name>: <n> characters, sha256 <hex>; read it with your tools)`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_agent_workspace.py
def test_papers_are_referenced_only_above_the_budget(tmp_path):
    c = make(tmp_path, inline_papers_max_chars=1000)
    d = research.prepare(c, "Q1P1"); inp = research._inputs(d)
    (d / "inputs" / inp["Q"]).write_text("q" * 400); (d / "inputs" / inp["P"]).write_text("p" * 599)
    assert "q" * 400 in research.thread_head(d, inp, inline_limit=research.papers_limit(c))
    (d / "inputs" / inp["P"]).write_text("p" * 601)
    head = research.thread_head(d, inp, inline_limit=research.papers_limit(c))
    assert "q" * 400 not in head and "sha256" in head and f"inputs/{inp['Q']}" in head
```

- [ ] **Step 2: Run and see it fail**

Run: `uv run --offline --locked pytest -q tests/test_agent_workspace.py -k budget`
Expected: FAIL with `TypeError` (`inline_limit` unknown) or `AttributeError` (`papers_limit`).

- [ ] **Step 3: Implement**

```python
def papers_limit(campaign) -> int:
    return int((campaign.raw or {}).get("inline_papers_max_chars", 400_000))


def thread_head(d, inp, papers: bool = True, ledger: bool = True, inline_limit: int | None = None) -> str:
    """(existing docstring) Above inline_limit characters together, both papers are listed by path, size and
    sha256 instead: an agent session would otherwise resend them on every turn."""
    parts = []
    if papers:
        texts = {name: (d / "inputs" / name).read_text(errors="replace") for name in (inp["Q"], inp["P"])}
        if inline_limit is not None and sum(len(t) for t in texts.values()) > inline_limit:
            for name, text in texts.items():
                parts.append(f"## {name}\n\n(file inputs/{name}: {len(text)} characters, sha256 "
                             f"{hashlib.sha256(text.encode()).hexdigest()}; read it with your tools)")
        else:
            parts.extend("## " + name + "\n\n" + text for name, text in texts.items())
    if ledger:
        parts.append("## ledger.jsonl\n\n" + ((d / "ledger.jsonl").read_text() if (d / "ledger.jsonl").exists() else ""))
    return "\n\n".join(parts)
```

Pass `inline_limit=papers_limit(campaign)` from `_consolidate_prompt` and `_review_material`. Leave the peer path unchanged (it already reads papers through tools unless `inline_papers` is set).

- [ ] **Step 4: Run and see it pass, then the research suites; commit**

Run: `uv run --offline --locked pytest -q tests/test_agent_workspace.py tests/test_stub_flow.py tests/test_research_revisions.py`
Expected: all PASS.

```bash
git add pathfinder/research.py tests/test_agent_workspace.py
git commit -m "Papers by reference above a campaign budget

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Read-only readers for verification

**Files:**
- Modify: `pathfinder/transport.py` (`ModelRequest.reads`, `_command`, `_execute`), `pathfinder/research.py` (verify calls in `_stage_call` and the composable request builder)
- Test: `tests/test_agent_workspace.py`, `tests/test_transport.py`

**Interfaces:**
- Produces: `ModelRequest.reads: bool = False`; `_command(campaign, model, tools, search, cwd, reads=False)`: Codex keeps its shell with `--sandbox read-only`; Claude gets `--tools Read,Glob,Grep` (plus web tools when `search`). Verification requests (`stage == "verify"`, including the composable ledger review) set `reads=True`. Consolidation keeps a writable workspace (its account may be taken from a file it writes).

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_transport.py
def test_readers_get_read_only_tools(tmp_path):
    codex = transport._command(campaign(tmp_path, "codex"), "m", True, False, tmp_path, reads=True)
    assert codex[codex.index("--sandbox") + 1] == "read-only" and "features.shell_tool=false" not in " ".join(codex)
    claude = transport._command(campaign(tmp_path), "m", True, False, tmp_path, reads=True)
    assert claude[claude.index("--tools") + 1] == "Read,Glob,Grep"
```

```python
# append to tests/test_agent_workspace.py
def test_verification_requests_are_read_only(tmp_path, monkeypatch):
    seen = []
    real = research.transport.execute
    def capture(campaign, request):
        seen.append((request.stage, request.reads))
        return real(campaign, request)
    monkeypatch.setattr(research.transport, "execute", capture)
    research.run_thread(make(tmp_path), "Q1P1")
    assert ("verify", True) in seen and all(reads is False for stage, reads in seen if stage != "verify")
```

- [ ] **Step 2: Run and see them fail**

Run: `uv run --offline --locked pytest -q tests/test_transport.py tests/test_agent_workspace.py -k "read_only or readers"`
Expected: FAIL (`reads` unknown).

- [ ] **Step 3: Implement**

Add `reads: bool = False` as the last field of `ModelRequest`. In `_command`, add `reads=False`; for Claude, when `tools and reads` use `["--tools", "Read,Glob,Grep" + (",WebSearch,WebFetch" if search else ""), "--dangerously-skip-permissions"]`; for Codex, choose `"read-only" if (reads or not tools) else "workspace-write"` for `--sandbox`, and skip the network flag when `reads`. In `_execute`, pass `reads=request.reads`. In `research._stage_call`, add a `reads=False` parameter forwarded into the `ModelRequest`, and call it with `reads=True` for `"verify"`. In the composable builder, set `reads=(stage == "verify")` on the `ModelRequest`. Request files store the request fields; `ModelRequest(**item["request"])` keeps loading older files because the new field has a default.

- [ ] **Step 4: Run and see them pass, then transport, research and behave; commit**

Run: `uv run --offline --locked pytest -q tests/test_transport.py tests/test_agent_workspace.py tests/test_stub_flow.py tests/test_research_revisions.py` and the behave command.
Expected: all PASS; behave at baseline.

```bash
git add pathfinder/transport.py pathfinder/research.py tests
git commit -m "Verifiers read with read-only tools

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Full verification, spec, and a measurement plan

- [ ] **Step 1:** Full pytest (expect only the baseline statarb failure) and behave (expect baseline counts).
- [ ] **Step 2:** In `notes/pathfinder-friction.tex`, mark the agent sandbox S item and D4 "Done in phase 3a (commits ...)", noting that session economy is measured on the next live run by comparing per-paper input tokens, `tool_calls` and `tool_errors` against the 30 September statarb figures (3.8 to 5.9 M input tokens per paper). Rebuild the PDF in `notes/`; run the style gate.
- [ ] **Step 3:** Commit:

```bash
git add notes/pathfinder-friction.tex notes/pathfinder-friction.pdf
git commit -m "Phase 3a complete: agent workspace, evidence and papers by reference, read-only verifiers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

## Phase 3b (next plan, outline)

Typed evidence inventory and resolver shared by research, verification and delivery, built on the Task 4 index: artefact identity with origin namespace across branch export and joint citation (F01); a source registry for source and manifestation identifiers (F02); declared inputs, planned outputs and observed outputs instead of strings mined from code (F03, F04); typed citations with document, page and section (F05); local, external, unavailable and generated kinds (F06); one manifest validated before each stage spends (F08); repair proposals that keep alias, non-dependency and unavailable distinct (R01); typed evidence errors instead of message parsing (R03).

# Phase 5: One budgeted context builder for every stage, contracts over parsers, consumer stage

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** No stage can paste unbounded material into a prompt again (J01): every stage builds its prompt through one context builder with a budget, which passes large material by reference to stages with tools and gives tool-less stages a budgeted digest, and records what it did. Every structured reply (scan scores, verifier decision, request review, paper review) is read under a declared schema, validated once, repaired by one reformatting turn on violation, and a reply that still violates it is an operational failure of class `contract`, never a scientific outcome (D5, R4, H8). A deployment can register a consumer that runs after a pair is edited and cannot overturn the verifier (H9).

**Architecture:** New `pathfinder/context.py`: `Section(name, text|path, keep)`, `budget(campaign, stage)`, `build(campaign, stage, sections, tools, cwd, unit, record)` and `digest_text(name, text, share)`. Sections keep their order (the prompt-cache prefix), the largest shrinkable sections are shrunk first: by reference (`(file X: N bytes, sha256 H; read it with your tools)`, the format phase 3a already uses) when the stage has tools and the section is a file, otherwise by a head-and-tail digest with size and digest. A prompt still over budget raises `transport.PromptTooLarge`, which every stage already turns into a block of class `input_too_large`. Each build emits a `context_built` event. New `pathfinder/contracts.py`: `SCHEMAS`, `extract_json`, `violations`, `parse`, `ensure` (one repair call through `transport.execute`) and `strict` (the schema form the Codex CLI's `--output-schema` accepts). New `pathfinder/consumer.py`: the `consumer` extension point, run by `edit.run` after a `done` edit, recorded in `consumer.json`, with the research status restored if the consumer changed it.

**Tech Stack:** Python 3.13, pytest with stub campaigns, behave features.

**Spec:** `notes/pathfinder-friction.tex`: D5 (contracts over parsers, R4), H8 (schema-constrained single calls), H9 (post-edit consumer stage), J01 (one context builder with a prompt budget for every stage). The R4 clause "provenance checks validate declared references only, not paths extracted by regex" was met in phase 3b (`evidence.cited_files`, typed citations); this plan does not touch it.

## Global Constraints

- Tests: `uv run --offline --locked pytest -q <files>`; full suite over two minutes, run in the background to a file; no engine edits while it runs.
- Behave: `uv run --offline --locked behave --tags="not @sandbox and not @captain and not @shipwright"`; baseline 93 passed, 1 failed, 9 error.
- Baseline pytest (8e1eabd): 409 passed, 1 failed (`test_deployments::test_statarb_prepares_freezes_and_runs_the_candidate_engine`, statarb imports `requests`).
- Formats may break compatibility (decision of 29 September): `inline_papers_max_chars` and `research.papers_limit` are removed, replaced by `prompt_budgets`.
- `prompt_budgets` in `campaign.json`: `{"default": N, "<stage>": N}`; default 300000 characters; never above `max_prompt_chars`.
- Section order is never changed by shrinking; equal inputs give byte-identical prompts.
- No new dependency (no `jsonschema`): the validator covers `type`, `enum`, `required`, `properties`, `items`, `minimum`, `maximum`.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- A tool-less stage (paper review) on a thread whose papers and ledger exceed the budget gets a prompt within budget, with the paper under review intact (Task 4 test).
- The composable review material, whose sha256 is the evidence identifier for stale detection, stays byte-identical across two builds of unchanged files (Task 3 test).
- A reply that violates its contract twice blocks the pair with reason `contract: ...` and failure class `contract`, and a reconcile of a composable pair reissues the request instead of reapplying the retained bad reply (Tasks 6 and 8 tests).
- A decision in lower case (`"draft"`) is still accepted, as before (Task 5 test).
- A consumer that raises, or that rewrites the research status, leaves the pair's research and edit statuses as they were (Task 8 test).

---

### Task 1: The statarb deployment test skips when statarb's own dependencies are absent

**Files:** Modify `tests/test_deployments.py`.

- [ ] Run the failing test and read the error (`ModuleNotFoundError: No module named 'requests'` from statarb's `arxiv_drip/paper.py`).
- [ ] Add at the top of that test: `pytest.importorskip("requests", reason="statarb's arxiv_drip needs requests, absent from this environment")`.
- [ ] Run `tests/test_deployments.py`: Expected: the test is skipped, the others pass. Commit "The statarb deployment test skips without statarb's dependencies".

### Task 2: The context builder

**Files:** Create `pathfinder/context.py`; modify `pathfinder/events.py` (KINDS gains `context_built`, `contract_repair`, `contract_failed`); test `tests/test_context.py`.

**Interfaces:**
- Produces: `Section(name: str, text: str | None = None, path: Path | None = None, keep: bool = False)`; `budget(campaign, stage: str) -> int`; `build(campaign, stage: str, sections: list[Section], *, tools: bool, cwd: Path | None = None, unit: str | None = None, record: bool = True) -> str`; `digest_text(name: str, text: str, share: int) -> str`.
- A section with `name == ""` is rendered without a heading (the task text carries its own); others as `## name\n\n<body>`; sections are joined by `\n\n`.

```python
DEFAULT_BUDGET = 300_000
MIN_SHARE = 2_000                  # a digest smaller than this says nothing useful


def budget(campaign, stage):
    raw = (campaign.raw or {}).get("prompt_budgets") or {}
    return min(int(raw.get(stage, raw.get("default", DEFAULT_BUDGET))), transport.max_prompt_chars(campaign))


def digest_text(name, text, share):
    sha = hashlib.sha256(text.encode()).hexdigest()
    note = f"(digest of {name}: {len(text)} characters, sha256 {sha}; the beginning and the end follow)"
    room = max(share - len(note) - 80, 0)
    head, tail = text[: room * 2 // 3], text[len(text) - room // 3:] if room // 3 else ""
    return f"{note}\n{head}\n[... {len(text) - len(head) - len(tail)} characters omitted ...]\n{tail}"
```

`build`: render every section; while the total exceeds the budget, take the largest not-yet-shrunk section without `keep`: a file section of a stage with tools becomes a reference (path relative to `cwd` when inside it), anything else becomes `digest_text(name, body, max(len(body) - excess, MIN_SHARE))`. If no shrinkable section is left and the total still exceeds the budget, raise `transport.PromptTooLarge(f"input too large: {stage} context is {total} characters after shrinking, budget {limit}")`. When `record`, emit `context_built` with `unit`, `stage`, `budget`, `chars`, and `sections: [{"name", "mode": "inline"|"reference"|"digest", "chars"}]`.

- [ ] Failing tests: within budget everything is inline and the order is kept; over budget with tools the largest file section becomes a reference with its sha256 and the result fits; over budget without tools it becomes a digest that fits and names the full size; a `keep` section is never shrunk; nothing shrinkable left raises `PromptTooLarge`; two builds of the same inputs are identical; `budget` honours `default`, the per-stage value and the `max_prompt_chars` ceiling; a `context_built` event is written only when `record`.
- [ ] Implement; run `tests/test_context.py tests/test_events*.py`; commit "One budgeted context builder: references for agents with tools, digests for those without".

### Task 3: Research stages build their prompts through the builder

**Files:** Modify `pathfinder/research.py` (`thread_head`, `judge_head`, `_consolidate_prompt`, the verify prompt in `run_thread`, `_review_material`, the peer prompt in `_peers`); remove `papers_limit`; modify `tests/test_agent_workspace.py`; test `tests/test_context_stages.py`.

**Interfaces:**
- Consumes: Task 2.
- Produces: `thread_sections(d, inp, papers=True, ledger=True) -> list[Section]` (inputs and ledger as file sections, in that order); `judge_sections(d, inp, note_name) -> list[Section]` (thread sections plus the note file).
- `_review_material(..., record_manifest=True)` builds under stage `verify` with `tools=True`, `record=record_manifest`; the ledger as filtered for a replay is a text section (it differs from the file).
- Stage names for budgets: `peer`, `consolidate`, `verify`.

- [ ] Failing tests on a stub campaign: with `prompt_budgets: {"default": 3000}` and long inputs, the consolidate and verify prompts fit the budget and list the papers by reference; the composable review material is identical across two builds and its `context_built` event is absent when `record_manifest=False`; a ledger far over budget is referenced, not pasted.
- [ ] Replace `thread_head`/`judge_head` with the section functions and route each prompt through `context.build`; drop `inline_papers_max_chars`. Update `tests/test_agent_workspace.py` to `prompt_budgets`.
- [ ] Run `tests/test_context_stages.py tests/test_agent_workspace.py tests/test_research*.py tests/test_eva*.py tests/test_reconcile*.py`, then behave; commit "Research stages build their prompts within a budget".

### Task 4: Paper review, scan and the edit-stage editor build within a budget

**Files:** Modify `pathfinder/paper.py` (`_review_round`), `pathfinder/scan.py` (`render`), `pathfinder/edit_stage.py` (`finish`); test `tests/test_context_stages.py`.

- Paper review (tool-less): sections are the judge sections, `paper/search.md`, then `paper.tex`, `references.bib`, the reference checks and the task, the last four with `keep=True`. Stage `review`.
- Scan (tool-less): when the rendered prompt exceeds the `scan` budget, the two bodies are replaced by `digest_text` with an equal share of what the template leaves.
- Edit-stage editor dispatch (tool-less): the account through `build(campaign, "edit", [Section(f"{pair_id}.tex", path=...)], tools=False)`.

- [ ] Failing tests: paper review prompt on a thread whose papers are 10x the budget fits and contains `paper.tex` whole; a scan with full texts over budget fits and names both digests; the edit-stage dispatch prompt fits.
- [ ] Implement; run `tests/test_context_stages.py tests/test_paper.py tests/test_scan.py`, then behave; commit "Tool-less stages get budgeted digests, never an unbounded paste".

### Task 5: Contracts

**Files:** Create `pathfinder/contracts.py`; modify `pathfinder/failures.py` (`"contract": ("call", False)`); modify `pathfinder/scan.py` (drop `parse_json`, use `contracts.extract_json`); move `tests/test_scan.py::test_parse_json_tolerates_tex_backslashes` to `tests/test_contracts.py`.

**Interfaces:**
- Produces: `SCHEMAS` (`scan`, `verify`, `request_review`, `paper_review`); `extract_json(text) -> object` (the current tolerant extraction, TeX backslashes included); `violations(value, schema, where="reply") -> list[str]`; `class ContractViolation(ValueError)` with `.errors`; `parse(name, text, check=None) -> dict` (upper-cases a string `decision` before validation, then runs `check(value)`, whose `ValueError`/`KeyError`/`TypeError` count as violations); `strict(schema) -> dict`.

```python
SCHEMAS = {
    "scan": {"type": "object", "required": ["feasibility", "gain"], "properties": {
        "feasibility": {"type": "number", "minimum": 0, "maximum": 100}, "gain": {"type": "number", "minimum": 0, "maximum": 100},
        "connexion": {"type": ["string", "null"]}, "rationale": {"type": ["string", "null"]}}},
    "verify": {"type": "object", "required": ["decision"], "properties": {
        "decision": {"enum": ["DRAFT", "REVISE", "ITERATE", "PAUSE"]}, "reason": {"type": ["string", "null"]},
        "action": {"type": ["string", "null"]}}},
    "request_review": {"type": "object", "required": ["requests", "dispositions"], "properties": {
        "decision": {"enum": [None, "REVISE", "ITERATE"]},
        "requests": {"type": "array", "items": {"type": "object"}},
        "dispositions": {"type": "array", "items": {"type": "object"}}}},
    "paper_review": {"type": "object", "required": ["decision"], "properties": {
        "decision": {"enum": ["ACCEPT", "AMEND", "REVISE"]}, "summary": {"type": ["string", "null"]},
        "findings": {"type": "array"}}},
}
```

- [ ] Failing tests: each schema accepts the stub's replies; `"draft"` passes `verify`; a missing `decision`, a wrong enum, a string where an array is expected and a score of 140 each give a violation naming the field; prose with no JSON gives `no readable JSON object`; `check` errors become violations; `strict` sets `additionalProperties: false` and lists every property as required, optional ones nullable; `failures.SCOPES["contract"] == ("call", False)`.
- [ ] Implement; run `tests/test_contracts.py tests/test_scan.py tests/test_failures*.py`; commit "Contracts: declared schemas for every structured reply".

### Task 6: Every structured call goes through its contract, with one repair turn

**Files:** Modify `pathfinder/contracts.py` (`ensure`), `pathfinder/research.py` (verify in `run_thread`; `_run_composable`'s `execute`; `_apply_research_review`), `pathfinder/paper.py` (`_review_round`), `pathfinder/scan.py` (`run`); test `tests/test_contracts.py`.

**Interfaces:**
- Produces: `ensure(campaign, request, result, name, check=None) -> tuple[dict | None, dict]`. A transport failure passes through as `(None, result)`. A violation issues one tool-less repair request (`identity + ":contract-repair"`, same stage and actor) whose prompt gives the violations, the schema and the previous reply (at most 50000 characters), and asks for the JSON object only; emits `contract_repair`. A second violation returns `(None, {**repaired, "failure": {"class": "contract", ...}, "error": "contract: ...", "contract_errors": [...]})` and emits `contract_failed`.
- Research verify: on `None` with a contract failure, BLOCKED with reason `contract: verify: <first errors>` and `failure`; the unreadable reply is still kept in `verify-unreadable.txt`.
- Composable: `execute` calls `ensure` for stage `verify` (`request_review` with `check=lambda v: _minus_requests(v, s["requests"])` for `eva_minus`, else `verify`) before `retain_response`; `_apply_research_review` uses `contracts.parse`, and its block reason becomes `contract: review: ...` with the `contract` failure.
- Paper review: `contract: review: ...`, status blocked, failure recorded. Scan: the row's `error` is `contract: ...`; the second scan attempt is replaced by the repair turn.

- [ ] Failing tests: a verifier reply in prose followed by a valid repair gives the normal verdict and two receipts; two violations block with class `contract` and reason prefix `contract:`; a transport failure is never repaired; an EVA-minus reply missing a disposition is repaired once.
- [ ] Implement; run `tests/test_contracts.py tests/test_scan.py tests/test_paper.py tests/test_research*.py tests/test_eva*.py`, then behave; commit "Structured replies are validated once and repaired once; violations are contract failures".

### Task 7: Schema-constrained calls on the Codex CLI

**Files:** Modify `pathfinder/transport.py` (`ModelRequest.schema: dict | None = None`, `_command(..., schema_path=None)`, `_execute` writes the strict schema to `schemas/<sha256>.json` under the campaign); `pathfinder/contracts.py` (`ensure` and the call sites pass `schema=SCHEMAS[name]` on the request); test `tests/test_transport*.py` or `tests/test_contracts.py`.

- `--output-schema <file>` is added for the Codex backend only when `campaign.json` has `"codex": {"output_schema": true}`; the Claude CLI gets no flag (engine-side validation covers it).

- [ ] Failing tests: `_command` for codex with the option and a schema path includes `--output-schema <path>`; without the option, or for claude, it does not; the file holds `strict(schema)`.
- [ ] Implement; run the transport and contracts tests; commit "Codex calls can carry their contract as an output schema".

### Task 8: Consumer stage, reconcile and playbook for contract failures, spec

**Files:** Create `pathfinder/consumer.py`; modify `pathfinder/extensions.py` (`SUPPORTED` gains `consumer`), `pathfinder/edit.py` (`run` calls `consumer.run` after `done`), `pathfinder/reconcile.py`, `pathfinder/playbook.py`, `notes/pathfinder-friction.tex`; tests `tests/test_consumer.py`, `tests/test_reconcile_stages.py`, `tests/test_playbook.py`.

**Interfaces:**
- `consumer.run(campaign, pair_id) -> str`: `skipped` when no consumer is configured; otherwise calls `consumer(campaign, pair_id, edited_dir)` and records `consumer.json` `{status: done|failed, result, error, at}`. The research `status.json` and the edit status are read before and written back if the consumer changed them, with `overturn_refused: true` in the record. A consumer exception never propagates.
- Reconcile: a composable pair BLOCKED with a `contract:` reason gets `REISSUE` (the retained reply is superseded, the request asked again); a single-engine pair BLOCKED with `contract: verify` gets `run verify`.
- Playbook: a `contract` failure is an apex action with the reconcile command.

- [ ] Failing tests for each bullet.
- [ ] Implement; mark D5, H8, H9 and J01 done in phase 5 in the tex, rebuild the PDF, run the style gate; run the full suite and behave; commit "Consumer stage that cannot overturn the verifier; contract failures reconciled".

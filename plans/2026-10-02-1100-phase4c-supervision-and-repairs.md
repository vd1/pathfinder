# Phase 4c: Reconcile every stage, stale-response reissue, atomic evidence declarations, refused calls, supervision playbook, alert deduplication

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recovery works the same way at every stage and is recorded: `reconcile` names and applies the one safe action for a stopped edit, author or review step as it does for research; a retained response made stale by changed evidence is superseded and reissued under a recorded lineage instead of blocking; evidence declarations are proposed, validated as a whole and committed atomically with before and after digests; a call refused before launch never uses an attempt; a deterministic playbook turns the campaign state into the next actions for the operator or the apex agent; repeated alerts are deduplicated.

**Architecture:** `reconcile.inspect` gains edit and paper branches and a stale-review branch; `reconcile.apply` runs `edit.run` or `paper.run` under the thread lock, or moves a stale request file to `research-requests/superseded/` before resuming, always appending to the status `history`. `evidence.apply_declarations` merges records into `external-references.json` on a temporary file, validates it with the same parser (`research._external_citations` taking an explicit path), replaces the file atomically and appends `{before_sha256, after_sha256, records}` to `declarations-history.jsonl`. `pathfinder/playbook.py` maps the state document, health snapshot and failure classes to ordered actions with an `owner` (`engine`, `apex`, `operator`). `alerts.emit` suppresses an identical alert within a window and counts repeats.

**Tech Stack:** Python 3.13, pytest with stub campaigns.

**Spec:** `notes/pathfinder-friction.tex`: D6, H6 (one admission per recovery: the status history), R02, J02, J03, J05, and the supervision items (alert fatigue, apex agent remit: handle everything it can, escalate quota, missing credentials and operator decisions).

## Global Constraints

- Tests: `uv run --offline --locked pytest -q <files>`; full suite over two minutes; no engine edits while it runs.
- Baseline (f936ec7): 387 passed, 1 failed (statarb deployment); behave 93 passed, 1 failed, 9 error.
- Reconcile writes nothing in `inspect`; only `apply` changes state, and every change is recorded in the status `history`.
- Declarations are never written partially: a late validation error leaves the file unchanged.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- `reconcile.apply` on an edit-stopped pair runs the editor, not research again (Task 1 test).
- A superseded stale response is kept, with its lineage, and never applied (Task 2 test).
- Applying the same declarations twice changes nothing the second time (Task 3 test).
- A peer call refused by a stop marker does not advance the peer call count (Task 4 test).
- The playbook never proposes retrying a quota or auth failure; it escalates them with the reset time (Task 5 test).

---

### Task 1: Reconcile every stage (J05)

**Files:** Modify `pathfinder/reconcile.py`; test `tests/test_reconcile_stages.py`.

**Interfaces:** `inspect` actions `"run edit"` (research terminal, edit `stopped`, or edit `blocked` with a transport failure recorded), `"run paper"` (research DRAFT, edit done, paper `stopped`), `"nothing: paper needs the operator"` for paper `blocked` or `PAUSE-ON-AMEND`; `apply` runs `edit.run` / `paper.run` under `runner.Lock` after recording history `{"at", "stage", "from_status", "from_reason", "action"}` in the stage's own status file.

- [ ] Failing tests on a stub campaign: research run to DRAFT, edit status forced to `stopped` with a timeout failure → `inspect` says `run edit`, `apply` returns `done` and research receipts did not grow; paper forced to `stopped` → `run paper`; paper `PAUSE-ON-AMEND` → `nothing: paper needs the operator`.
- [ ] Implement the branches (after the research-terminal check, before `nothing: terminal`), using `edit.status` and `paper.status`.
- [ ] Run reconcile, edit, paper and evidence tests; commit "Reconcile names and applies the safe action for edit and paper stages".

### Task 2: Supersede and reissue a stale retained response (J03)

**Files:** Modify `pathfinder/reconcile.py` (and `research.py` only if a helper is needed); test `tests/test_reconcile_stages.py`.

**Interfaces:** for a BLOCKED pair whose reason is `stale review: research evidence changed`, `inspect` returns `"reissue: evidence changed since the request"` (this prefix is removed from the evidence-repair prefixes, which test a different thing); `apply` moves every pending request file of the pair to `research-requests/superseded/<UTC stamp>-<name>`, records in the status history `{"action", "superseded": [paths], "at"}`, sets `status="running"`, `pending=[]`, and resumes; the next call has a fresh request file.

- [ ] Failing test on a composable stub campaign: run until a ledger review request is retained (monkeypatch `transport.execute` to return a result for the first review), change an evidence file so the material hash differs, call the apply path once to get `BLOCKED` stale review; then `inspect` gives the reissue action, `apply` resumes, the superseded file exists with the old result, and the status history records it.
- [ ] Implement.
- [ ] Run research revision, evidence and reconcile tests and behave; commit "Reconcile supersedes a stale retained response and reissues it under a recorded lineage".

### Task 3: Atomic evidence declarations (R02)

**Files:** Modify `pathfinder/research.py` (`_external_citations(d, path=None)`), `pathfinder/evidence.py` (`apply_declarations`), `pathfinder/cli.py` (`pathfinder evidence PAIR --apply FILE`); test `tests/test_evidence.py`.

**Interfaces:** `evidence.apply_declarations(campaign, pair_id, records: list[dict]) -> dict` returning `{"changed": bool, "before_sha256", "after_sha256"}`; records are merged by `(document, ledger_seq, path)` (a new record replaces an old one with the same key); validation parses the merged declaration through `research._external_citations(d, path=<temporary file>)`; the file is replaced atomically; `declarations-history.jsonl` in the thread gets one line per change.

- [ ] Failing tests: applying a valid `output` declaration creates the file and a history line; applying it again returns `changed: False` and adds no line; applying a set where the second record is invalid (stale `text_sha256`) raises and leaves the file byte-identical.
- [ ] Implement; the CLI reads a JSON list from the file and prints the result.
- [ ] Run evidence tests and behave; commit "Evidence declarations applied atomically with before and after digests".

### Task 4: Refused calls never use an attempt (J02)

**Files:** Test `tests/test_admission.py` (and code only if the test fails).

**Interfaces:** none new; the guarantee: a peer, consolidation or verification call refused by a stop marker or the size gate leaves `peer_call`, `peer_seconds`, `repairs`, `reviews` and stage attempt counters unchanged, so the resumed run issues the same call.

- [ ] Tests on a stub campaign: write a stop marker, run the thread (it stops), remove the marker, run again: the first peer request identity of the second run ends with `call-0` / the peer call count is 0 before the call. A size-gate refusal (tiny `max_prompt_chars` on a composable campaign) leaves `peer_call` at 0 and the pair BLOCKED with the input-too-large failure.
- [ ] If either fails, fix the counter where it is advanced before the call returns; otherwise record that the canonical engine already holds the guarantee.
- [ ] Commit "Refused calls never use an attempt: regression tests".

### Task 5: Supervision playbook and alert deduplication (D6)

**Files:** Create `pathfinder/playbook.py`; modify `pathfinder/alerts.py`, `pathfinder/cli.py`; tests `tests/test_playbook.py`, `tests/test_alerts.py`.

**Interfaces:** `playbook.next_actions(campaign) -> list[dict]` from `campaign_state.build`, `health.snapshot` and `reconcile.inspect`, each `{"owner": "engine"|"apex"|"operator", "action": str, "why": str, "command": str | None}`, ordered: campaign-wide stops first (quota and auth: owner `operator`, with the reset time, never a retry), health flag (owner `apex`: diagnose, then `pathfinder reconcile` per pair), cooldown (owner `engine`: wait), per-pair reconcile actions (owner `apex`, with the exact command), evidence blocks (owner `apex`: `pathfinder evidence PAIR` and its proposals; owner `operator` when a proposal needs a URL), editor or paper needing the operator, allowance warnings (owner `operator`: raise the key); `pathfinder playbook [--json]`. `alerts.emit` skips an alert whose `(kind, evidence)` equals the last one within `alert_repeat_seconds` (default 3600), incrementing `repeats` in `alert.json` instead of notifying again.

- [ ] Failing tests: a campaign stopped by a quota failure yields first an operator action naming the reset time and no action containing "retry"; a stopped edit yields an apex action with command `pathfinder --root <root> reconcile Q1P1 --apply`; an evidence block yields `pathfinder evidence`; two identical alerts within the window write one `alerts.jsonl` line and `repeats: 1`.
- [ ] Implement; `repres` can call `pathfinder playbook --json` for its Next steps (note it in the skill afterwards).
- [ ] Run playbook, alerts, health and state tests; commit "Supervision playbook from the campaign state; repeated alerts deduplicated".

### Task 6: Verification and spec

- [ ] Full pytest and behave at baseline; mark D6 (playbook and alerts; the event-driven wake-up and separate credentials remain open), H6, R02, J02, J03, J05 in `notes/pathfinder-friction.tex`; rebuild; style gate; commit; update the `repres` skill to use `pathfinder playbook --json` when available.

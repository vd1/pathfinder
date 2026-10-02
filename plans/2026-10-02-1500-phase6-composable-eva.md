# Phase 6: Composable EVA as an option (N direct-EVA branches, then a joint EVA thread)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A campaign can run each pair as N independent direct-EVA branches (default 3), freeze each branch's handoff as an immutable, verified bundle, and then run one joint EVA thread over those bundles, all inside the engine, under the ordinary runner, reconcile, playbook and state document. EVA-minus is renamed direct EVA throughout. Each pair records the D10 measurements: thread divergence between branches and Vera's rejection rate.

**Architecture:** `"research_scheme": "composable"` with `"branches": N` (default 3) and optional `"branch"` and `"joint"` override blocks (any campaign key, typically `rounds` and `ledger_reviews`). New `pathfinder/composable.py`:
- `branch_view(campaign, pair_id, label)` and `joint_view(campaign, pair_id)` are shallow copies of the campaign with their own `raw` (`direct_eva` without bundles, or `eva` with `research_bundles = ["branches/branch-1", ...]`), and, for a branch, `thread_dir` pointing at `threads/<pair>/branch-runs/<label>/` and a `branch` label.
- `run(campaign, pair_id, stop)` runs the unfinished branches concurrently through the existing `research.run_thread`, freezes each HANDOFF into `threads/<pair>/branches/<label>/` (a copy, files 0444, `bundle.json` with a sha256 inventory and the `export_outcome` handoff), writes `branches/metrics.json`, then starts the joint thread in the pair's own thread directory and runs it.
- The joint thread's account is the pair's account, so editing and the paper follow unchanged.

Receipts and events gain a `branch` field when written through a branch view. `research.run_thread` hands a composable campaign to `composable.run`. Reconcile, playbook and the state document look into the branches while the pair is at stage `branches`.

**Tech Stack:** Python 3.13, pytest on the stub backend, behave features.

**Spec:** `notes/pathfinder-friction.tex`: decision "Composable EVA in canon" (option, N default 3, naming of 2 October: direct EVA), D10 (thread divergence, Vera rejection rate). Prior art: julien-2's `eva2` package (four sibling campaigns, hardcoded three branches, freeze with `bundle.json`, all branches must hand off before the joint thread). Canon already has `research_scheme`, `research_bundles`, HANDOFF and `export_outcome`.

## Global Constraints

- Tests: `uv run --offline --locked pytest -q <files>`; full suite (about four minutes) to a file.
- Behave: `uv run --offline --locked behave --tags="not @sandbox and not @captain and not @shipwright"`; baseline 93 passed, 1 failed, 9 error.
- Baseline pytest (f77b190): 462 passed.
- Formats may break compatibility: `"research_scheme": "eva_minus"` is refused at load with a message naming `direct_eva`; no alias.
- A frozen bundle is never modified: files are written once, made read-only, and verified against `bundle.json` before every joint run.
- The joint thread starts only when every branch has handed off; a branch that is BLOCKED blocks the pair with the branch named; a stopped branch stops the pair.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- A stop during the branches, then a resume, reruns no finished branch and pays no finished call again (Task 4 test).
- A frozen bundle edited after the freeze blocks the joint thread with the file named (Task 3 test).
- One BLOCKED branch: the pair is BLOCKED with `branch-k: <reason>`; reconcile names the branch's own action and applying it resumes the composition (Task 5 test).
- Branch receipts are attributed to their branch and still count toward the pair's usage (Task 2 test).
- `branches: 1` and `branches: 5` both work; `branches: 0` is refused at load (Task 4 test).

---

### Task 1: EVA-minus is renamed direct EVA

**Files:** `pathfinder/research.py`, `pathfinder/stub.py`, `pathfinder/config.py`, `features/eva-ledger-research.feature`, `features/steps/eva_ledger_steps.py`, tests that set `research_scheme="eva_minus"`.

- [ ] Failing test `tests/test_composable.py::test_the_old_scheme_name_is_refused`: `config.load` on `"research_scheme": "eva_minus"` raises `ValueError` naming `direct_eva`.
- [ ] Replace the value `eva_minus` with `direct_eva` in code, stub, features, steps and tests; rename code identifiers that say `minus` only where they name the scheme; keep the feature prose.
- [ ] Run the suite and behave; commit "EVA-minus is named direct EVA".

### Task 2: Branch and joint views; receipts and events name their branch

**Files:** Create `pathfinder/composable.py`; modify `pathfinder/transport.py` (`_receipt` adds `branch`), `pathfinder/events.py` (`emit` adds `branch`); test `tests/test_composable.py`.

**Interfaces:**
- `labels(campaign) -> list[str]` (`branch-1` ... `branch-N`); `branch_view(campaign, pair_id, label)`; `joint_view(campaign, pair_id)`.
- A view is `copy.copy(campaign)` with `raw` replaced (base raw, minus `branches`, `branch`, `joint`; plus the override block; plus the scheme keys), `rounds` taken from the new raw, `branch` set to the label (branch only) and, for a branch, `thread_dir = lambda pid: campaign.thread_dir(pid) / "branch-runs" / label`.

- [ ] Failing tests: a branch view's thread directory and scheme; the override block applies (`branch: {"rounds": 1}` gives `view.rounds == 1`); the joint view lists N bundles; a stub call made through a branch view writes a receipt with `branch` and `thread == pair_id`, and an event with `branch`.
- [ ] Implement; commit "Branch and joint views over one campaign".

### Task 3: Freeze and verify bundles

**Files:** `pathfinder/composable.py`; test `tests/test_composable.py`.

**Interfaces:**
- `freeze(campaign, pair_id, label) -> Path`: requires the branch HANDOFF with `scientific_verdict` None and no `active` request when `handoff_reason == "no_further_requests"`, else raises `BundleError`. It copies `ledger.jsonl`, `status.json`, `external-references.json` when present, `inputs/` and every peer directory, refusing symlinks. It writes `handoff.json` (`export_outcome`), then `bundle.json` last: `{"label", "files": {rel: {"sha256", "bytes"}}, "inventory_sha256", "frozen_at"}`. Files are made 0444. An existing complete bundle is returned after `verify`.
- `verify(bundle_dir)`: raises `BundleError` naming the first missing, extra, changed or symlinked file.

- [ ] Failing tests: a HANDOFF branch freezes, files read-only, inventory right; a non-HANDOFF branch is refused; an edited file and an extra file are each named by `verify`; freezing twice returns the same bundle unchanged.
- [ ] Implement; commit "Branch handoffs frozen as verified read-only bundles".

### Task 4: The composition runs under the ordinary runner

**Files:** `pathfinder/composable.py` (`run`), `pathfinder/research.py` (`run_thread` dispatch), `pathfinder/config.py` (validation of `branches`); test `tests/test_composable.py`.

**Interfaces:**
- `run(campaign, pair_id, stop) -> str`. The joint thread directory gets status `stage="branches"`, `status="running"` until the joint thread starts. Unfinished branches run in a thread pool of size N. The results:
  - all HANDOFF: freeze each, write `branches/metrics.json` (Task 6), reset the joint status to `round=1, stage="peers", status="running"` with `branches_frozen` recording the inventory digests, and return `research.run_thread(joint_view, ...)`;
  - any `stopped`: the pair is `stopped`;
  - otherwise the pair is `BLOCKED` with reason `branch-k: <branch reason>` and `failure` copied from the branch.
- A pair whose joint thread has started goes straight to the joint thread, after `verify` of every bundle; a verify failure blocks with `frozen bundle changed: ...`.
- `config.load` refuses `branches` that is not an integer of at least 1.

- [ ] Failing tests on the stub: a composable pair ends DRAFT with three frozen bundles and the joint ledger beside them; the runner edits it; `branches: 1` and `branches: 5`; `branches: 0` refused; a stop raised inside one branch's call leaves the pair `stopped`, and a second run makes no new call for the branches already handed off; an edited bundle blocks the joint thread.
- [ ] Implement; run the suite and behave; commit "Composable EVA: N direct-EVA branches, frozen, then a joint EVA thread".

### Task 5: Reconcile, playbook and state look into the branches

**Files:** `pathfinder/reconcile.py`, `pathfinder/playbook.py`, `pathfinder/campaign_state.py`; tests `tests/test_composable.py`.

- `reconcile.inspect` on a composable pair at stage `branches`: when a branch is not HANDOFF, the action is `branch-k: <that branch's own action>` (inspect on the branch view); `apply` applies the branch's action on the branch view, then resumes the composition. A frozen-bundle failure is `nothing: frozen bundle changed` (operator).
- The state document's unit gains `branches: [{"label", "status", "stage", "round", "reviews", "handoff_reason"}]` for a composable pair.

- [ ] Failing tests: a BLOCKED branch (stub `verify` reply forced unreadable twice) gives the pair `BLOCKED` with `branch-2:` and reconcile `branch-2: run verify` or the reissue action; applying it ends the pair DRAFT; the state document lists three branches.
- [ ] Implement; commit "Reconcile, playbook and state see the branches of a composable pair".

### Task 6: D10 measurements

**Files:** `pathfinder/composable.py` (`metrics`); test `tests/test_composable.py`.

- `metrics(campaign, pair_id) -> dict`, written to `branches/metrics.json` at the joint start:
  - per branch: reviews, requests issued, resolved and deferred, `handoff_reason`, and the substantive ledger entries;
  - Vera's rejection rate: the share of reviews that issued at least one request, per branch and overall;
  - thread divergence: the mean pairwise Jaccard distance between the branches' sets of word 3-grams over their substantive ledger text (0 for identical branches, 1 for nothing shared; `null` with fewer than two branches).

- [ ] Failing tests: identical ledgers give divergence 0, disjoint ones give 1; a branch whose two reviews issued one request batch has rejection rate 0.5.
- [ ] Implement; mark the decision and D10 in the tex, the roadmap row and the campaign documentation; rebuild the PDF; run the style gate; full suite and behave; commit "D10 measurements for composable pairs; spec updated".

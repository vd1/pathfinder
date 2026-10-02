# Phase 7a: Seats shared across processes by account, a deployment's next unit, release engine-v1.2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The engine side of phase 7, which the deployments need before they move under the canonical engine. First, campaigns that share one subscription share one seat pool across processes (H7). Second, a coordinator in batch mode can ask the deployment for its next unit instead of following a fixed schedule (the rest of H5, replacing statarb's `overnight.py` selection). Third, the engine is released as `engine-v1.2` through the release gate, with the deployment matrix updated.

**Architecture:**
- **Seat pool.** New `pathfinder/seats.py`. `"account": {"name": "...", "seats": N}` in `campaign.json` names a pool. Pools live under `PATHFINDER_ACCOUNTS` (default `~/.pathfinder/accounts`), one directory per name, with one reservation file per admitted call `{pid, root, stage, actor, thread, at}`.
  - Taking a seat counts the live reservations under an exclusive `fcntl` lock on `pool.lock`, removes those whose process is dead (reaped), and creates its own file if fewer than N remain.
  - `admission.admission` takes the account seat before the in-process reservation and releases it however the call ends. While it waits, it rechecks stop markers at the same `STOP_POLL` and records why it is waiting.
  - No `account`: no pool, as today.
- **Next unit.** `schedule.json` may name `"next_unit": "module:callable"` with an optional `"path"` (relative to the parent) put on `sys.path`. When the fixed `schedule` list is exhausted, the coordinator calls `next_unit(arms, progress)`, which returns `{"arm", "pair"}` or `None`, and runs it under the same batch rules (deadline, unit limit, failure tolerance). Every returned entry is recorded in progress; a pair not on the arm's shortlist, or an entry already done, ends the coordination as failed with the reason.
- **Release.** `deployments.toml` revisions are updated, `scripts/release_check.py` passes, and the release notes are written. The tag `engine-v1.2` is created on the release commit and pushed.

**Tech Stack:** Python 3.13, `fcntl`, pytest.

**Spec:** `notes/pathfinder-friction.tex`: H7 (cross-process seat pool keyed by account, reservations bound to PIDs, dead ones reaped), H5 (deployment `next_unit()`), Migration (tag `engine-v1.2` and repin).

## Global Constraints

- Baseline pytest (25dd149): 496 passed (one timing test flaky under load: `test_supervise.py::test_slow_audits_skip_ticks_instead_of_accumulating`). Behave: 93 passed, 1 failed, 9 error.
- A reservation file is removed when its call ends, by `finally`. A process killed with SIGKILL leaves one behind, and the next taker reaps it because the pid is dead.
- Tests never touch `~/.pathfinder`: they set `PATHFINDER_ACCOUNTS` to a temporary directory.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- Two processes on one account with `seats: 1`: their calls never overlap (Task 1 test with two subprocesses).
- A reservation of a dead pid is reaped and does not hold a seat (Task 1 test).
- A stop marker written while a call waits for an account seat refuses that call within `STOP_POLL` (Task 1 test).
- `next_unit` returning a pair already done, or one off the shortlist, fails the coordination with the reason and runs nothing (Task 2 test).
- The release gate passes with the statarb contract pinned to the new statarb revision (Task 3).

---

### Task 1: Seat pool by account (H7)

**Files:** Create `pathfinder/seats.py`; modify `pathfinder/admission.py`, `pathfinder/campaign_state.py` (the state shows the account, its seats and the live reservations); test `tests/test_seats.py`.

- [ ] Failing tests: `seats.take`/`release` count and reap; two subprocesses with `seats: 1`, each holding its seat for 0.5 s, never overlap (their start and end times are recorded); a stop marker refuses a waiting call; without `account` nothing is written; the state document lists `account: {name, seats, in_use}`.
- [ ] Implement; run `tests/test_seats.py tests/test_admission.py`; commit "Seats shared across processes by account".

### Task 2: A deployment's next unit (H5)

**Files:** Modify `pathfinder/coordinator.py`; test `tests/test_coordinator.py`.

- [ ] Failing tests: an empty schedule with `next_unit` returning two entries and then `None` runs both and ends `complete`; with `batch.max_units: 1` it runs one and ends `unit limit`; a returned entry already done fails the coordination; an unknown arm or pair fails it; the schedule digest covers the `next_unit` target.
- [ ] Implement; commit "Coordinator asks the deployment for its next unit".

### Task 3: Release engine-v1.2

- [ ] Update `deployments.toml` (statarb revision after its migration commit, phase 7b; julien-2 note: the EVA blocker is lifted by phase 6). Run `scripts/release_check.py --notes RELEASE_NOTES.md`, and commit the notes. Tag `engine-v1.2` and push the tag.

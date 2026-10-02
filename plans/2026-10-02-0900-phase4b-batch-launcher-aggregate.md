# Phase 4b: Batch coordinator, launcher, shared cooldown and the view across campaigns

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A coordinator schedule can run as a bounded batch (deadline, maximum units, a tolerance of k consecutive failed entries) instead of stopping on the first failure; a rate-limit cooldown is shared by every arm under one parent and shown to the operator; `pathfinder launch` starts any long command detached and confirms it is alive; `pathfinder view --schedule` serves the operator page for every arm of a coordination.

**Architecture:** `schedule.json` gains an optional `batch` block read by `coordinator.run`; without it the established semantics (stop on the first failure) stay. `admission.cooldown` reads the campaign's and its parent's `cooldown.json`; `transport._cool_down` writes both; `health.snapshot` and `campaign_state` report it. `pathfinder/launch.py` (ported from statarb's `arxiv_drip.launch`) starts `python -m pathfinder.cli ...` in its own session, waits, checks the PID and writes `launch.json`. `view.make_server` accepts several campaigns keyed by arm; `/api/arms` lists them, `/api/state?arm=` and `/doc?arm=&path=` select one; the page gains an arm selector.

**Tech Stack:** Python 3.13, pytest, node harness.

**Spec:** `notes/pathfinder-friction.tex`: H5, H10 (aggregate), S3, the deferred 4a minors (cooldown shared and shown). The deployment callable for the next unit (`next_unit`) belongs to the statarb migration (phase 7).

## Global Constraints

- Tests: `uv run --offline --locked pytest -q <files>`; full suite over two minutes; no engine edits while it runs.
- Baseline (85c9870): 371 passed, 1 failed (statarb deployment); behave 93 passed, 1 failed, 9 error.
- Without a `batch` block a coordination behaves exactly as before (existing coordinator tests unchanged).
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- A deadline stops admitting new entries but never interrupts the entry in flight (Task 1 test).
- With `max_consecutive_failures: 2`, one failed entry is recorded and the next entry runs; two in a row fail the coordination (Task 1 test).
- A cooldown written by one arm holds a sibling arm's calls (Task 2 test).
- `pathfinder launch` reports a command that exits at once as a failure with its log tail (Task 3 test).
- The view never serves a document of one arm through another arm's name (Task 4 test).

---

### Task 1: Batch mode for the coordinator

**Files:** Modify `pathfinder/coordinator.py`; test `tests/test_coordinator.py`.

**Interfaces:** `schedule["batch"] = {"deadline": "<ISO UTC>", "max_units": int, "max_consecutive_failures": int}` (each optional); state keys `units_started`, `failed_entries` (list of `{"entry", "error", "at"}`), `consecutive_failures`; final statuses add `"deadline"` and `"unit limit"`.

- [ ] **Step 1: Failing tests** (follow the fixtures already in `tests/test_coordinator.py` for building a parent and two stub arms):
  - `test_batch_deadline_stops_admitting_without_interrupting`: a deadline already in the past before the second entry (patch `time.time` or set the deadline to now plus a fraction of a second and make the first entry sleep past it) gives status `deadline`, first entry complete, second not started.
  - `test_batch_unit_limit`: with `max_units: 1` and a schedule of two entries the status is `unit limit` and only the first entry ran.
  - `test_batch_tolerates_one_failed_entry_and_fails_on_two`: patch `runner.run_pair` to fail the first entry and succeed the second with `max_consecutive_failures: 2`: status `complete`, `failed_entries` has one item; failing two in a row gives status `failed`.
  - `test_without_batch_the_first_failure_still_fails`: existing behaviour.
- [ ] **Step 2:** run, see them fail.
- [ ] **Step 3: Implement** in `run`: read `batch = schedule.get("batch") or {}`; parse the deadline with `datetime.fromisoformat(... .replace("Z", "+00:00"))`; at the top of each entry, if `time.time()` passed the deadline set status `deadline` and break, if `units_started >= max_units` set `unit limit` and break; increment `units_started` before `run_pair`; wrap the failure checks after `run_pair` (the two `raise RuntimeError`) so that, when `max_consecutive_failures` is set, the error is appended to `failed_entries`, `consecutive_failures` increments, the entry is skipped and the loop continues unless `consecutive_failures >= max_consecutive_failures`, in which case raise as today; a successful entry resets `consecutive_failures`. Keep the final status logic: `censored` or `complete` unless a break set `deadline`/`unit limit`. Document the batch block in the module docstring.
- [ ] **Step 4:** run coordinator, runner and bounded suites; commit "Coordinator batch mode: deadline, unit limit and a tolerance of consecutive failed entries".

---

### Task 2: Cooldown shared with the parent and shown

**Files:** Modify `pathfinder/admission.py`, `pathfinder/transport.py`, `pathfinder/health.py`, `pathfinder/campaign_state.py`; tests in `tests/test_admission.py`, `tests/test_health.py`.

**Interfaces:** `admission.cooldown(campaign)` returns the longest remaining cooldown of the campaign root and its parent; `transport._cool_down` writes `cooldown.json` to both; `health.snapshot()["cooldown"] = {"remaining_seconds", "reason"}` or `None` with a warning while active; `campaign_state` `progress.cooldown_seconds`.

- [ ] **Step 1: Failing tests:** two stub campaigns `arm1`, `arm2` with `parent: "../parent"`; a rate receipt in `arm1` makes `admission.cooldown(arm2) > 0`; `health.snapshot(arm2)["cooldown"]["remaining_seconds"] > 0` and a warning mentions "cooling down".
- [ ] **Step 2:** run, see them fail.
- [ ] **Step 3: Implement:** factor `_cooldown_file(root) -> (remaining, reason)`; `cooldown` takes the max over `[root, parent]`; `_cool_down` writes to the campaign and, when `raw["parent"]` is set, to the parent root; snapshot and state read `admission.cooldown` plus the reason.
- [ ] **Step 4:** run admission, transport, health and state suites; commit "Rate-limit cooldown shared with the coordinator parent and shown in health and state".

---

### Task 3: `pathfinder launch`

**Files:** Create `pathfinder/launch.py`; modify `pathfinder/cli.py`; test `tests/test_launch.py`.

**Interfaces:** `launch.launch(argv: list[str], log: Path, settle_seconds: float, cwd: Path) -> int` (PID; raises `RuntimeError` with the log tail if the process exited); `launch.command(root: Path, args: list[str]) -> list[str]` = `[sys.executable, "-m", "pathfinder.cli", "--root", str(root), *args]`; CLI `pathfinder launch [--settle 20] -- <subcommand and arguments>` writes `launch.json` (`pid`, `argv`, `log`, `started_at`) and the log under `<root>/logs/launch-<UTC stamp>.log`, prints the record.

- [ ] **Step 1: Failing tests:** `launch.launch([sys.executable, "-c", "print('boom'); raise SystemExit(3)"], log, 1.0, tmp_path)` raises with "boom" in the message; a sleeping command returns a live PID; `launch.command(Path("/c"), ["research"])` ends with `["--root", "/c", "research"]`; `cli.main(["--root", str(tmp_path), "launch", "--settle", "0.5", "--", "health"])` returns 0 or reports exit (health exits at once: assert the command reports that it exited and shows the log tail, since `health` is not long-running).
- [ ] **Step 2:** run, see them fail.
- [ ] **Step 3: Implement** by porting `../statarb/arxiv_drip/launch.py` (`Popen` with `start_new_session=True`, stdin from `/dev/null`, stdout and stderr to the log, `time.sleep(settle)`, `poll()` and `os.kill(pid, 0)`), plus the CLI subcommand using `argparse.REMAINDER` after `--`. `launch` itself is not in `DISPATCHING`.
- [ ] **Step 4:** run the new tests and the CLI tests; commit "pathfinder launch: start a long command detached and confirm it is alive".

---

### Task 4: The view across the arms of a coordination

**Files:** Modify `pathfinder/view.py`, `pathfinder/view.js`, `pathfinder/view.html`, `pathfinder/cli.py`; tests `tests/test_view.py`, `tests/js/view_harness.js`.

**Interfaces:** `view.make_server(campaigns: dict[str, Campaign] | Campaign, port)`: a single campaign is keyed `""`; `/api/arms` returns `[{"arm", "name", "pipeline_total", "progress", "stop"}]`; `/api/state?arm=<name>` and `/doc?arm=<name>&path=...` select one (unknown arm: 404); `pathfinder view --schedule schedule.json` loads the arms with `coordinator.load`; the page shows a `<select id="arm-select">` when there is more than one arm, keeps the choice in the hash (`arm=`), and adds `arm` to its state and document requests.

- [ ] **Step 1: Failing tests:** a server over two stub arms answers `/api/arms` with both; `/api/state?arm=a2` returns arm a2's units; `/doc?arm=a1&path=threads/Q1P1/...` serves only a file of arm a1 (the same relative path in a2 is not served through `arm=a1` when it exists only in a2); an unknown arm is 404; the harness: with two arms the page fetches `/api/state?arm=<first>` and switching the select changes the request.
- [ ] **Step 2:** run, see them fail.
- [ ] **Step 3: Implement** the arm map in the handler, the routes and the select (rendered once from `/api/arms` at load; `refresh()` builds `"/api/state" + (arm ? "?arm=" + encodeURIComponent(arm) : "")`; `docURL` appends `&arm=`).
- [ ] **Step 4:** run view, webguard and state suites and `node --check`; commit "The operator view across the arms of a coordination".

---

### Task 5: Verification and spec

- [ ] Full pytest and behave at baseline; mark H5, S3, the aggregate part of H10 and the shared cooldown as done in phase 4b in `notes/pathfinder-friction.tex` (note that `next_unit` moves to phase 7); rebuild; style gate; commit.

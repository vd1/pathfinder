# Phase 9: token budgets, tidy sweep, supervisor on events, measurements, julien-2 driver, deferred minors

Spec: `notes/pathfinder-friction.tex` R5 (supervisor wakes on events, independent credentials), R6 (accounting in
tokens: budgets in tokens and calls, receipts deduplicated by call identifier, cancellations counted
separately), R7 (tidy and simplify sweep), D10 second half (planted flaws to test Vera), phase 3a session
economy measured live, julien-2's `eva2` driver onto canonical composable EVA, and the minors deferred by the
reviews of phases 4c to 7a. Decision of 29 September: billing is subscription, budgets are in tokens and calls.

Tasks, each test first, one release (engine-v1.3.0) at the end after a fresh whole-branch review:

1. Budgets in tokens and calls (R6): `"budget": {"calls", "input_tokens", "output_tokens"}`; receipts carry
   `call_id` and are read once per call; cancelled and timed-out calls with usage are counted and shown
   separately; `budget_usd` stays for campaigns that still set it.
2. Deferred minors: oversize review reason names its stage; the consumer runs once per edited note; budget
   values fail at load with a message; edit-stage oversize handled; bundles leave `inputs/` out; the pair lock
   is taken before a branch repair; seat reservations held by an open flock (pid reuse); the next_unit picker's
   code digest in coordination.json; playbook allowance advice counts recent timeouts only.
3. Supervisor (R5): wakes when the event log grows instead of on a fixed tick; runs its model calls with its
   own credentials (`supervisor.codex_home`, `supervisor.env`) independent of the workers'.
4. Measurements: a session-economy report over receipts (input tokens per pair and per stage, cached share,
   before and after context by reference); a Vera probe (sound and planted-flaw ledgers, detection rate) with a
   stub test and a small live run.
5. julien-2: a converter from an `eva2` experiment to a canonical composable campaign, and a canonical
   campaign configuration reproducing its branch and joint settings; verified on the stub backend.
6. Tidy sweep (R7): split `research.py` (single-engine thread; composable request machinery; review material
   and evidence assembly), remove dead code, keep every public name importable.

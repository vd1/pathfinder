# Moving pathfinder-julien-2 onto a released engine

Prepared 2026-09-28 against engine `main` after `engine-v1.1`. julien-2 was
not changed: it has a campaign decision pending
(`reviews/campaign-continuation-01/preparation.json`, status
`scope_clarification_pending`) and frozen experiments whose custody records
bind the vendored engine. This note lists what each side must do.

## What julien-2 does today

`eva2/campaign.py` (and `julien2/campaign.py` in the EVA experiment) replace
`transport.execute` with a bridge for the duration of a run and call
`research.run_thread` directly. The bridge:

- routes every call through julien-2's `Dispatcher` (attempts database,
  dispatch records, live gating, provider choice);
- composes a call identity from experiment, branch, round, review cycle,
  repair count and the engine's request identity;
- caps timeouts by stage;
- appends branch-review instructions to every non-peer prompt of a branch;
- turns "Round reservation unavailable" for a peer into an empty reply, so
  the peer turn is skipped.

Because the engine never sees these calls, they bypass admission, the run
record, engine receipts and the stub backend.

## Engine side: done

- `extensions.transport` (this commit): a deployment names its dispatcher in
  `campaign.json`, `"extensions": {"path": "...", "transport":
  "julien2_bridge:execute"}`. The engine admits the call, writes its
  active-call record, calls `execute(campaign, request)`, normalises the
  result and writes its own receipt. The bridge body can move into that
  function unchanged; `research.status(campaign, "Q1P1")` still gives the
  round, review cycle and repair count for the identity.
- Prompt overlays: the branch-review instructions become
  `prompts/consolidate.append.md` and `prompts/verify.append.md` in each
  branch campaign, recorded in `run.json`.
- Stops: when the branch campaigns set `"parent": ".."`, admission refuses
  every call once the parent's `stop.json` exists, and `runner.stopped` sees
  it too; the bridge's own `stop.json` check becomes redundant.
- The general research fixes from the inventory (J1 to J8, J10 to J13) are in
  `engine-v1.1`.

## julien-2 side: to do

1. Replace the `transport.execute` assignment with the `transport` extension
   and a module name unique to julien-2 (the engine refuses two deployments
   sharing a module name).
2. Move the appended branch instructions to append overlays.
3. Freeze the engine with `pathfinder freeze --ref engine-v1.1` (or a later
   tag) instead of vendoring, and extend custody hashes to the files the
   engine now reads during builds (`resources.py`, `research.py`, the styles).
4. Keep `stage_attempts: 1` in the branch campaigns, since the host owns retries.

## Still blocking support

The EVA research scheme (inventory rows E2 to E8: the HANDOFF state,
`research.export_outcome`, branch bundles, the `runner.pending` HANDOFF skip)
lives inside julien-2's copy of `research.py` and `runner.py`, and
`eva2/campaign.py` depends on it. The engine has no extension point for an
alternative research state machine. Two ways forward, for julien-2's owners
to choose:

- upstream a HANDOFF terminal state and outcome export behind a campaign
  setting, with the EVA feature files as its regression tests; or
- move the EVA scheme into julien-2's controller, driving the engine's
  bounded `run_pair` for each branch and treating a DRAFT branch as ready for
  handoff.

Until one of these is done, `deployments.toml` keeps julien-2 as not yet
supported.

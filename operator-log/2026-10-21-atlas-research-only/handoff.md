# Native research-only coordination

The runtime adds an explicit research-only execution scope. Default research still includes editing;
default coordination still includes research, edit and paper. Restricted-collection permissions and
shared-budget enforcement are unchanged. No Atlas deployment, source pool or live model was touched.

## Contract

For a single child, use `research --research-only --pairs PAIR`. For sequential children, set the
schedule's `stages` to exactly `["research"]`. This is a schedule field, not a campaign configuration key.
The schema example in `schedule.example.json` has six child roots and one shortlisted pair per child;
replace those illustrative names with the actual deployment names and pair IDs before binding it.
Each child campaign must declare `"parent": ".."` if it is directly below the schedule directory,
or the corresponding relative path otherwise. All six retain their existing restricted-collection
manifest/hash and the same pinned budget-group manifest/hash. Do not add editorial permissions.

A child completes at DRAFT, PAUSE, PAUSE-ON-ITERATE or PAUSE-ON-REVISE. These are research outcomes,
not editorial acceptance. BLOCKED and HANDOFF are not successful research-only completion. No edit,
actionability, paper, presentation or post-editor garbage collection is dispatched. Runner metadata
records `stages: ["research"]`; coordinator schedule provenance also binds the scope.

The native runner holds its thread lock before initialisation. Restricted initialisation now permits
only that current-process regular lock file in an otherwise empty thread. Foreign locks, symlinks and
other pre-existing contents remain refused. Existing sealed threads retain their normal seal checks.

## Execution and inspection

Use the verified frozen directory as an absolute PYTHONPATH. Resolve a working Python interpreter
with the deployment's normal dependencies first, and use that same interpreter for launch and resume.
The following commands are templates; ENGINE, PARENT, CHILD and PAIR are operator-resolved values.
No command in this handoff has been run against Atlas.

```sh
PYTHONPATH="$ENGINE" python -P -m pathfinder.cli --root "$CHILD" research --research-only --pairs "$PAIR"
PYTHONPATH="$ENGINE" python -P -m pathfinder.cli --root "$PARENT" launch -- coordinate "$PARENT/schedule.json"
PYTHONPATH="$ENGINE" python -P -m pathfinder.cli --root "$PARENT" coordinate "$PARENT/schedule.json" --status
```

The detached command processes entries sequentially through native coordinator ownership. Inspect
parent `runner.json`, `progress.json`, `outcomes.json` and child receipts, health and stop records.
Do not infer completion from a PID alone. On restart, invoke the same coordinate command with the
same schedule and verified runtime. Completed research is skipped without repeating calls.
An engine/configuration/schedule change remains subject to ordinary provenance acceptance; no automatic
accept-change option is supplied. Explicitly resolve any operator stop before resuming. Never delete
an unresolved active-call record or shared budget lock to make admission succeed.

The shared budget continues to aggregate receipts across all configured roots, including earlier runs.
Unknown usage and unresolved active-call evidence still refuse admission. Keep Atlas's existing aggregate
limits of 1,000,000,000 input tokens and 14,000,000 output tokens; this change neither resets nor raises them.

## Offline verification

The tests create six restricted synthetic child copies with individually pinned historical inputs and
a shared budget manifest. Actual research stages use stub transport. A parent stop after the third child
is followed by a restart; the first three receipts remain byte-identical, the remaining children finish
in order, and a second restart adds no calls. The source stays unchanged and no edited directory appears.
Other tests cover budget exhaustion across restart, unresolved active-call evidence, parent stop,
thread ownership, rejected pre-existing content, all terminal statuses, CLI defaults and subsequent
legacy editing. Existing runner, coordinator, collection and budget-group suites cover legacy behavior.

These are synthetic offline integration tests, not a validation of Atlas's six scientific manifests or
overlays. Atlas should reproduce the path on its own copies before launch, as planned.

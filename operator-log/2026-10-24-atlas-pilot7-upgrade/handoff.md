# Atlas Pilot 7 safe-boundary engine migration

Suitable target: `376c01f70c9b67e4a992b5344a8611a56ed2e94e`, runtime-identical to tested `a3d28c8`.
Frozen runtime `/private/tmp/pathfinder-376c01f`; archive `/private/tmp/pathfinder-376c01f.tar.gz`.
Archive SHA256 `17cabb76765c9b425da1cfa51eaabdaacc12f771df4352208720590095f68b5b`.

No live Pilot 7 files, calls, stop markers or processes were changed by the maintainer.
This is separate from Opus-owned Pilot 6 and uses no reopen or reopen-recover command.

## Evidence

Read-only preflight against the actual six Pilot 7 configurations is in preflight.json. Pair 1's recorded
run differs only in engine; configuration, composed prompts, routes, styles, corpus and weights match.
The other five roots have no previous run. Prompt files have no diff between 02ce103 and 376c01f.
The pinned group budget remains 1B input / 14M output. No research settings need changing.

The offline proof starts a six-arm research-only coordinator under frozen 02ce103, requests canonical
stop during a local fixture call, waits for it to finish, then resumes the same schedule under frozen
376c01f with explicit engine-change acceptance. It covers stops after peer readiness, consolidation,
and verification. Each completed six-pair case has exactly 18 unique fixture receipts, preserves the
old receipt bytes as a prefix, preserves existing research sources and configuration bytes, and makes
no calls when the completed schedule is run again. The old source metadata can be regenerated normally.

The incomplete-peer fixture is held, not resumed. Classic peer-call/seconds counters are local to the
peer-stage invocation; a mid-stage stop without readiness can refresh that allowance on resume. This
pre-existing limitation is not fixed by 376c01f. Do not migrate at that boundary.

These are fixture-based workflow tests, not live scientific evaluations or a frozen snapshot of a
currently writing peer. test-results.json records all cases; drain_check.py is the reproducible harness.

## Exact operator commands

Run in the established Pilot 7 launch environment, retaining its provider wrappers and other environment
settings. Do not source a different pilot's launch script. Only the runtime search path changes after drain.
The interpreter below is the one recorded in Pilot 7's launch.json.

```sh
pilot7_root=/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-7
pilot7_py=/Users/v/.local/share/uv/python/cpython-3.13.0-macos-aarch64-none/bin/python3.13
pilot7_old=/private/tmp/pathfinder-02ce103
pilot7_new=/private/tmp/pathfinder-376c01f
```

1. Wait until the active child's classic stage advances out of peers, preferably while a consolidation
   or verification call is running. Re-read the coordinator entry immediately before stopping. If it has
   moved to another arm, target that actual active child and wait for its safe stage instead. The parent
   is not itself a campaign, so do not use the parent's root for the stop command.

```sh
PYTHONPATH="$pilot7_old" "$pilot7_py" -m pathfinder.cli \
  coordinate "$pilot7_root/schedule.json" --status
PYTHONPATH="$pilot7_old" "$pilot7_py" -m pathfinder.cli \
  --root "$pilot7_root/runs/pair-1" stop
```

2. Let the running call finish and its receipt be committed. The child's operator stop also makes the
   coordinator halt before admitting the next schedule entry. Do not kill the coordinator or provider.
   Wait for PID 64615 and its children to exit, coordinator/child runner records to settle, both ownership
   locks to be free, and active-calls to be empty in all six roots. Check the actual drained state:

   - consolidate: resume the pending consolidation; completed peers must not run again;
   - verify: resume the pending verifier; completed consolidation is retained;
   - terminal: the schedule skips that completed pair;
   - peers: hold for inspection if any of that round's peer allowance was spent. Do not manually advance
     status, reset counts or infer a safe boundary solely from the stage observed before stop.

   A race between inspection and stop is possible, so this post-drain check is mandatory. Save the drained
   state, existing receipt hashes, campaign/prompt/source hashes and old runtime reference before migration.
   Keep any independent budget/provider stop or health failure in place for diagnosis.

3. Verify the new artifact and copy the archive to durable operator storage. Select the new runtime
   separately; do not overwrite the old frozen directory or change live code beneath a controller.

```sh
shasum -a 256 /private/tmp/pathfinder-376c01f.tar.gz
PYTHONPATH="$pilot7_new" "$pilot7_py" -m pathfinder.cli \
  verify-frozen "$pilot7_new" --repo /Users/v/Code_2026/pathfinder
```

   Recheck preflight at the drained boundary: the started child's provenance changes must be engine-only.
   Do not let the accept-change reason silently approve unrelated changed components. All six campaign
   JSON files, source inputs, composed prompts, schedule, wrappers and pinned budget manifest stay intact.

4. Clear only the operator stop created for this migration, on the same child used in step 1. Export the
   new runtime path and verify the imported package location before canonical detached coordination.

```sh
export PYTHONPATH="$pilot7_new"
"$pilot7_py" -c 'import pathfinder; print(pathfinder.__file__)'
"$pilot7_py" -m pathfinder.cli --root "$pilot7_root/runs/pair-1" stop --clear
"$pilot7_py" -m pathfinder.cli --root "$pilot7_root" launch -- \
  --accept-change "Vincent-approved Pilot 7 safe-boundary engine upgrade 02ce103 to 376c01f; settings and prompts unchanged" \
  coordinate "$pilot7_root/schedule.json"
```

   The coordinator propagates accept-change to each child run. Provenance links the new run to its
   predecessor and records the engine change; old receipts retain their original run IDs. No schedule
   rewrite, new research grant or replay is required. FIFO budget ordering applies among upgraded
   controllers; an older controller sharing the lock does not implement the FIFO queue.

5. Verify the new coordinator and provider process after launch, then check the first call's stage,
   runtime, effective route and growing log. Compare prior receipt/source hashes, confirm no completed
   call replay, and continue the original six-pair schedule under unchanged budgets. A PID alone does
   not establish successful migration.

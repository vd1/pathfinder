# Atlas Pilot 6: reviewed engine fixes and same-grant recovery

## Runtime

Commit: `a3d28c8242e29c8e43396b316885d881d36fd127`.
Frozen runtime: `/private/tmp/pathfinder-a3d28c8`.
Archive: `/private/tmp/pathfinder-a3d28c8.tar.gz`.
Archive SHA256: `c9ae168c304c21a56d2ac706c6ee8e65ba80d308cac219b75c8e4ffd9dfefd70`.
`freeze.json` records verification against the exact commit, with no runtime differences.

This includes the reviewed local EVA readiness commit `bc81411`, the prior classic ITERATE fix, and the
Nobel source-title metadata fix. No unapproved deployment pin from the former maintainer's separate
`release-1.16` worktree was adopted. That worktree is not a released runtime for this recovery.

## Fixes

- Classic reopen now accepts an absent research_scheme directly. A repair uses the retained last verdict
  and checks its note hash. A round invalidates stale readiness and supplies the retained feedback. The
  next verdict ends the grant, including after stop/resume; ITERATE cannot start ungranted rounds.
- Budget-group callers register FIFO tickets. OS-held ticket locks identify live waiters without PID
  assumptions; abandoned tickets are reclaimed. Waiting emits admission_deferred. The existing group
  call lock still spans the call and its receipt, and budgets are rechecked before admission. FIFO is
  guaranteed among upgraded participants; old controllers sharing the lock do not implement this queue.
- After a terminal provider event, the CLI has a 30-second exit grace period. The engine then terminates
  the call's remaining process group and discoverable descendants. Raw provider evidence, reported
  usage, error outcomes and actual exit status remain recorded. Provider errors are not turned into
  successful results. Cleanup requires OS process-table access for children that escaped the process
  group; inability to finish evidence readers still fails closed with active evidence retained.

The former maintainer's two-second yielding proposal was replaced by FIFO tickets. Their incomplete
classic patch was finished and tested, rather than published as received. Their original diff and new
untracked tests were saved under `/private/tmp/pathfinder-opus-unreviewed.patch` and
`/private/tmp/pathfinder-opus-snapshot/` before editing.

## Actual Atlas recovery diagnosis

Pair Q001-P002 has an existing authorised repair grant 1, created with an in-memory scheme override on
02ce103. That old classic runner ignored the grant's brief and stopping rule. The void consolidation
finished at 14:28:02 UTC with receipt `c03361fb068449928bb5bc8fde32af89`; its charges remain in accounting.
The runner stopped before verification and the active-call directory became empty.

The snapshot's status.json is already post-reopen. Do not restore it. The useful snapshot component is
Q001-P002.tex, whose SHA256 `b3c309af8350267f6ecfa7a470a4a298bc2c04d2016821dd826d93e075a1858d`
matches the last genuine verifier verdict. No new scientific judgment or acceptance is inferred.

The new canonical command is `reopen-recover`. It creates a hash-bound proposal and, on explicit apply:

- checks idle campaign ownership, no unresolved calls, the existing repair grant and its last REVISE;
- binds the snapshot note, complete thread inventory, receipt ledger and engine;
- archives the current thread, including the void attempt, into reopen-recoveries/1/before;
- preserves symlink targets as symlinks without copying their external payloads;
- restores only the last judged note, carries its retained correction brief, and allocates a fresh
  consolidation response slot without overwriting the void response;
- leaves the same grant and its original record intact, with state stopped pending normal resume.

It makes no model call, does not clear stop markers, and refuses repeat recovery or stale proposal hashes.
No old verdict, ledger, receipt, budget limit or grant record is rewritten. A crash during application
leaves custody evidence and fails closed on another recovery attempt; it requires inspection, not retry.

## Operator procedure

1. Keep the live hold until runner ownership is idle and no active call remains. Verify the freeze and
   archive. Preserve the current runtime reference and select this separate runtime through normal
   deployment configuration. Do not replace files beneath a running controller.
2. Using that exact runtime and the existing validated interpreter, run the following CLI arguments with
   root `/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-6/runs/pair-1`:

   ```sh
   reopen-recover Q001-P002 \
     --snapshot /Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-6/operator/pair-1-pre-reopen-snapshot/Q001-P002.tex \
     --reason "Recover the existing authorised repair after unbriefed classic dispatch"
   ```

3. Inspect the returned proposal. It must identify grant 1, the last REVISE note hash above, the void
   consolidation receipt, and the complete current inventory. Save the proposal. Repeat the exact
   command adding `--apply --expected-sha256 HASH`, using its returned sha256. Any changed binding
   requires a fresh inspection; no hash bypass is supported.
4. Verify custody and the restored note. Clear only the operator stop through canonical `stop --clear`
   when ready under the existing repair authority. Preserve any independent provider/budget pause.
5. Resume through canonical `research --research-only --pairs Q001-P002`, with a recorded
   `--accept-change` reason naming this engine migration. Use the existing model routes and shared
   budget. This executes the repaired consolidation and a fresh verifier; any verdict terminates the
   existing grant. The recovery does not approve additional budget or subsequent grants.

No manual status restoration, research_scheme override, fresh reopen grant, raw provider retry or
reconcile repair is needed for this case. Other active pilots are not restart targets.

## Validation

- 146 core regressions passed, including transport/provider evidence, failure accounting, budgets,
  reservations, FIFO admission, classic grants and recovery. After adding symlink custody coverage,
  all 8 recovery tests passed; after the final ticket counter hardening, all 11 group tests passed.
- 59 research/reopen/readiness regressions passed; 64 composable/recovery/admission tests passed.
- All 35 focused tests also passed when imported from the exact frozen runtime.
- The frozen-copy run in copy-result.json preserved the actual original campaign inventory. It archived
  all 2,823 thread files/links, restored the verifier-bound note, retained the paid void receipt and
  original reopen record, and reached exactly one stubbed consolidation plus one stubbed verdict.
  These are offline fixture responses, not scientific evaluations. All original campaign files remained
  unchanged. The copied budget-group membership is deliberately not used for fake transport; real
  budget admission is covered separately by the tests above.

No live deployment writes or real model calls were made by the maintainer.

# Bounded campaign failure recovery

Created: 23 September 2026, 22:57 CEST, Europe/Paris.

Status: proposed implementation plan. This document does not launch implementation.

## Objective

Make persistent operational failures stop predictably, preserve usable work,
and give the operator an actionable diagnosis. An operator stop must also work
while the campaign is waiting for recovery. Successful automatic recovery must
resume the saved investigation without treating it as an independent rerun.

## Evidence

The GPT-6-sol rerun campaign is recorded in
`experiments/2026-09-23-gpt-6-sol-rerun-01/`.

- Q4P10 and Q3P9 completed research with PAUSE verdicts. Later subprocess
  launches failed before model sessions started. Receipts record
  `exit -11 before session` repeatedly for about an hour.
- The Python crash report identifies a crash on the child side of fork,
  in macOS networking handlers. The experiment launcher now sets
  `no_proxy=*`, following the documented
  [Python workaround](https://docs.python.org/3.13/library/urllib.request.html).
  Research resumed after restarting the supervisor.
- An earlier launch failure came from the installed Codex CLI rejecting
  `--search`. A successful generic probe did not establish that a research
  call with different arguments could launch. The experiment has an adapter
  translating that flag into the supported search configuration.
- `pathfinder/runner.py` enters its health-probe branch before checking the
  stop marker. Failed probes repeat without an overall deadline. The wait
  between probes does not inspect stop requests.
- `pathfinder/monitor.py` exposes a health flag, but its text status does not
  explain the last probe failure or distinguish recovery from exhausted
  recovery. Existing runner tests cover eventual probe success; they do not
  cover indefinite failure or a stop during recovery.

Section 6 of `notes/pathfinder-engine.tex`, under Stop and Failure and
recovery, already limits the guarantee to preservation of recorded work.
Its stop rule is stronger than the current health-loop implementation.

## Proposed behaviour

### Stop and drain

Check an operator stop before every admission and recovery probe. While waiting
between probes, inspect the stop marker at the ordinary scheduler interval.
Stop ends the wait promptly. Calls already running keep their existing
deadlines and save their results; no further calls start after the next stop
check. This includes calls made for recovery.

### Finite recovery episode

Use an explicit campaign recovery episode with a proposed default allowance of
300 seconds. Record its start, deadline, phase, attempt count, and last observed
error in persistent campaign state. Set the deadline when the failure episode
starts. Cap each probe timeout by the remaining allowance and retain the current
60-second spacing between unsuccessful probes.

Restarting the runner preserves the episode and its deadline. An elapsed
deadline produces an operational recovery block, an actionable message, and a
nonzero command exit. It does not change a scientific verdict. An explicit
operator recovery action may start a new episode after the fault is addressed;
record that action so it is distinguishable from automatic continuation.

Successful probing permits a controlled retry of the failed workload. Close the
episode after that workload succeeds. A probe succeeding while the actual
workload repeatedly fails must not create an unlimited sequence of fresh
recovery allowances. Keep other admissions held during this trial.

Persist the attempt reservation before launching a probe. If the supervisor
dies during it, preserve the consumed allowance and report its outcome as
unknown until evidence establishes otherwise. Preserve the existing receipt
semantics for usage and cost.

### Operator visibility and continuation

Text status and the existing monitor should show whether the campaign is
recovering or needs intervention, the episode age, remaining allowance, last
error, affected stage, and the supported next action. A blocked command must
return failure to callers. Mere process existence must not imply progress.

Expose the explicit recovery action through the existing command interface.
It must respect an operator stop and inspect saved stage artifacts before
resuming. Completed research stays completed. An unfinished readable account
can resume even when its research thread already has a terminal verdict.

### Runtime compatibility

Move the observed macOS workaround and supported Codex search invocation into
the maintained runtime paths. Apply the networking workaround before the
supervisor performs URL access. Preserve deliberate proxy configurations;
where one is required, use an explicit proxy handler that avoids native
macOS discovery. Verify both search-enabled research calls and calls whose
roles disable search with the installed CLI.

## Implementation sequence

1. Captain writes concrete scenarios in
   `features/operational/campaign-runtime.feature` and adds the directed targets
   to `watchbill.json`. State the recovery allowance and explicit retry rule in
   the scenarios. Inspect any existing watchbill before extending it.
2. QM enters with fresh context, adds meaningful executable coverage, and
   demonstrates the recovery failures before dispatching production fixes.
3. Crew changes the smallest necessary seams in `pathfinder/runner.py`,
   `pathfinder/transport.py`, `pathfinder/cli.py`, and configuration handling.
   Reuse the existing health state and receipt mechanisms where possible.
4. Add the actionable recovery display in `pathfinder/monitor.py` and, only
   where required to expose it, `pathfinder/monitor.html`. Verify the command
   exit status through the real CLI boundary.
5. Align README.md, BUILDER.md, the engine note's operational-control section,
   and its conformance appendix with the implemented behaviour. Describe the
   recovery bound and operator action explicitly. Rebuild the note PDF.
6. Boatswain performs focused verification and local commit custody. Preserve
   unrelated working-tree edits and all experimental evidence.

The present request authorizes this plan file. The sequence above describes the
subsequent implementation work.

## Acceptance checks

| Situation | Required observation |
| --- | --- |
| Stop exists before a recovery probe | No probe or new investigation launches |
| Stop arrives during the recovery wait | Wait ends by the next scheduler check |
| Stop arrives during a running call | Call drains within its deadline; no successor launches |
| Temporary failure clears | Saved stage resumes and completes |
| Every probe fails | Recovery expires, state retains the error, and CLI exits unsuccessfully |
| Runner restarts during recovery | Original deadline and reserved attempts survive |
| Probe succeeds but workload still fails | Same bounded episode continues without admission flooding |
| Operator retries after fixing the fault | Explicit new episode resumes usable saved work |
| Research is terminal but editing is unfinished | Editing resumes without repeating research |
| HTTP checks precede threaded subprocess launches on macOS | Subsequent real child processes launch successfully |
| Codex research enables search | Installed CLI accepts the invocation and performs a real role call |
| Recovery is blocked | CLI and monitor display consistent diagnosis and next action |

Use isolated temporary campaigns. Exercise the real scheduler, state files,
process launch and CLI exit paths. Produce launch failures with a missing
executable and verify successful launches with a real executable. Keep paid
model verification to the smallest real compatibility check required. A test
double for a hard-to-produce condition must be marked and justified under the
Shipshape verification agreement; it must not replace normal execution coverage.

Run the affected scenarios and appropriate unit tests for runner, transport,
monitor and reconciliation, using the commands and tiers in RIGGING.md. Verify
restart behaviour in a separate process. Apply the style gates to edited prose,
compile the engine note, and inspect the resulting PDF. A full campaign rerun
is not required to prove these control-flow changes.

## Delivery limits and rollout

This is a local recovery-control change, estimated at a few hours including
verification and documentation, subject to findings in the existing harness.
It does not promise automatic repair of arbitrary infrastructure faults.
External notifications and a separate watchdog remain future work; an operator
must inspect the monitor or command outcome to learn that recovery is blocked.

The running GPT-6-sol experiment uses a frozen engine. Keep that snapshot stable
while implementing and testing the maintained runtime. Any later adoption by a
live experiment must happen at a safe boundary, with its runtime change recorded.
Preserve all completed outputs, source versions, failed-call receipts, and
recovery records. Avoid changing the scientific protocol, model assignments,
or rerun selection as part of this fix.

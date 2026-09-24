# Failure detection and agent handoff

Created: 24 September 2026, 09:10 CEST, Europe/Paris.

Status: proposed plan only. Implementation and notification tests have not started.

This plan supersedes the automatic-recovery design in
[the earlier plan](2026-09-23-2257-bounded-failure-recovery.md).
Its [review](2026-09-23-2257-bounded-failure-recovery-review.md) remains relevant
to timeout handling, unfinished editing, and concurrent ownership.

## Objective

Make operational failures reach the supervising agent promptly, with enough
information to diagnose and resume the work. Pathfinder preserves progress and
stops safely. The agent or operator fixes the fault and explicitly restarts it.

Remove automatic health probing and recovery retries from the campaign runner.
Do not add recovery episodes, probe reservations, trial admissions, or failure
counters. Scientific PAUSE verdicts remain normal research outcomes.

## First: prove notification works

Before changing Pathfinder, use an isolated, harmless child process to test the
existing execution environment's completion notification. Let it fail after the
launching interaction has yielded. Verify that its exit actually resumes the
supervising agent with the process identity and failure result, without manual
status inspection or an agent polling loop. Also test an abrupt child crash.

Record the observed delivery delay. A proposed acceptance target is notification
within 60 seconds of process exit while the supervising environment is available.
A terminal badge or a line written to a log does not satisfy this check.

If the existing environment passes, reuse it. If it cannot wake the agent, stop
and report that missing capability before building a replacement. Propose the
smallest external watcher and delivery integration separately for approval.
Do not claim unattended failure detection until this end-to-end check passes.

## Runtime behaviour

- On the first operational failure, record the campaign, run identity, exact
  pair and stage, timestamp, error, and receipt or log location. Preserve later
  failures from already active work without overwriting the original diagnosis.
- Stop admitting calls as soon as the scheduler observes the failure. Check
  the stop condition at stage boundaries inside active workers too, so a
  research result cannot launch an editor after admission has stopped.
- Let calls already running save their results within their existing deadlines.
  Display the failure immediately; exit nonzero after draining. Include the
  active-call drain allowance in the stated worst-case notification delay when
  delivery depends on process exit. Do not describe that delay as immediate.
- Treat session-started timeouts and editor transport failures as operational
  failures. Propagate them to the runner instead of returning research success.
  Surface exhausted editing validation as unfinished work requiring attention,
  with a nonzero exit, while retaining the terminal research verdict.
- Use a single per-call monotonic deadline for prompt delivery, startup,
  execution, and bounded cleanup. Remove independent startup overruns and
  minimum waits that exceed the remaining allowance. Test termination and
  stream handling as well as the main process wait.
- Use an exclusive campaign lock for the runner's lifetime. A second runner
  refuses to start. Prefer an OS-managed lock released on process death over
  a PID file requiring manual stale-lock repair. The runner owns campaign
  failure state; workers report failures to it. Persist state atomically.

Reuse existing status and receipt files where practical. Add only the fields
needed for diagnosis and resumption, rather than a separate recovery subsystem.

## Notification and restart

The execution environment watches the actual campaign process, not only an
intermediate launcher that exits successfully. Its completion signal must also
cover a runner crash before Pathfinder writes its own failure record. In that
case, report the abnormal exit and last known active stages; label the failing
stage unknown if the available evidence does not establish it.

A process that hangs is detected through call deadlines while the runner remains
responsive. A frozen runner, host failure, or unavailable notification service
is outside this initial guarantee. Supporting those cases would require an
independent liveness monitor and is not included in this change.

After receiving a failure, the agent inspects the saved diagnosis, fixes the
cause, and explicitly restarts through the normal command. Restart requires the
previous owner to have exited and an operator stop marker to have been cleared
explicitly. Preserve the prior failure in the run record.

Pending work includes terminal research with an unfinished readable account.
Restart skips completed research and resumes that editing stage. Preserve
completed outputs and existing receipt semantics; do not claim exactly-once
model calls or recovery of unrecorded usage after a crash. An unrelated pair's
success never clears a recorded operational failure.

## Implementation order

1. Run the notification feasibility check above and report its result.
2. Inspect the runner, transport, editor, CLI, and existing tests. Add focused
   regression tests for failure propagation, bounded calls, and restart.
3. Implement stop-on-failure and pending-edit continuation, with campaign
   ownership and actionable CLI status. Remove the automatic probe loop.
4. Connect campaign execution to the proven completion-notification mechanism.
   Test failure and restart end to end with temporary campaigns and real local
   subprocesses. No paid campaign is needed for these control-flow checks.
5. Update the operational-control section of `notes/pathfinder-engine.tex` and
   relevant usage documentation to state the tested detection, drain, delivery,
   and restart guarantees. Run focused tests and document style checks; rebuild
   and inspect the note PDF if its source changes.

Work directly in the relevant files. No additional role workflow, planning
registry, or new framework is needed.

## Acceptance checks

- A missing executable produces an actionable failure and nonzero CLI exit;
  no further calls are admitted after failure is observed.
- A session starts but never finishes: timeout remains a failure, and startup
  plus execution and cleanup stay within the declared bound and test tolerance.
- Another pair succeeds while a pair fails: the campaign still reports failure.
- Terminal research has interrupted editing: restart finishes editing without
  repeating research. An editing validation failure is also visible.
- An operator stop prevents further stages, including during failure draining.
- Concurrent runners cannot both acquire ownership; a crashed owner does not
  permanently prevent an explicit restart.
- A runner exits abnormally before writing a failure record: the external
  completion mechanism delivers the abnormal exit to the supervising agent.
- Failure while other calls are active preserves their completed work, exits
  within the documented drain bound, and delivers the notification afterward.

## Scope and estimate

Provisional estimate: roughly a day including tests and documentation, if the
existing notification mechanism passes the initial check. Re-estimate before
proceeding if that integration is missing or transport cleanup needs wider work.

This plan does not implement automatic repair, automatic restart, periodic health
probes, new scientific stages, or changes to models and pair selection. Existing
compatibility workarounds remain separate from this detection change unless a
focused test establishes that they are necessary for it.

Keep the experiment's frozen engine and saved evidence untouched. Any later
migration requires a safe stopping point and an explicit record of the runtime
change. This request creates the plan only; it does not launch implementation,
stop a campaign, commit, or push.

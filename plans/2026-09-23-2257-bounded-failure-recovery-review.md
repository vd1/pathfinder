# Review of bounded campaign failure recovery

The plan addresses the observed unbounded health loop. I would resolve the following points before
implementation.

1. **Make probe success mean a completed, usable probe.** The current `_probe` checks only
   `transport_failed` (`pathfinder/runner.py:243-246`). A call that starts a session and times out
   has `outcome="timeout"` but `transport_failed=False` (`pathfinder/transport.py:225-239`), so the
   current probe treats that timeout as restored health. Specify the accepted outcome and response,
   and add a test where the probe starts a session but never finishes.

2. **Enforce the recovery deadline through the whole transport call.** Passing the remaining
   allowance as `timeout` is insufficient today: session establishment uses a separate grace period
   based on `SESSION_GRACE` and prompt length before the call timeout is applied, and `proc.wait` has
   a one-second floor
   (`pathfinder/transport.py:215-229`). Use one monotonic deadline for startup and execution,
   including process termination, so a short remaining allowance cannot produce an extra minute of
   probing. Test a nearly expired episode with a child that never opens a session.

3. **Include unfinished editing in automatic continuation, or narrow the objective.** The runner
   excludes terminal research from `pending` (`pathfinder/runner.py:225-228`). It also catches an
   editor transport failure and returns the terminal research verdict as success
   (`pathfinder/runner.py:231-240`). Thus restarting `research` cannot automatically finish the
   readable account, even though the plan calls for saved-work continuation. Specify whether the
   recovery episode covers editor calls, how terminal research with incomplete editing is queued,
   and what exit status follows an editor failure. Cover this with a terminal-research,
   interrupted-edit restart test.

4. **Define ownership of campaign recovery state.** The proposed persistent episode and explicit
   retry can be touched by a running scheduler and a second CLI process. The existing lock is per
   thread (`pathfinder/runner.py:175-199`), while `health.json` is campaign-wide. Specify a single
   campaign owner or an atomic compare-and-update rule for episode creation, probe reservation,
   blocking, and operator retry. The retry action should refuse to reset a live episode and should
   require the stop marker to be cleared explicitly. Test simultaneous runner and retry attempts.

5. **Pin down the failed-workload trial.** The plan says a successful probe is followed by a
   controlled retry with other admissions held. Name the saved stage and pair to retry, define when
   the episode first starts, and say whether a successful unrelated in-flight thread can reset
   failure accounting. The current scheduler resets its counter whenever any future succeeds
   (`pathfinder/runner.py:294-303`), which can hide a repeatedly failing stage. An acceptance test
   should interleave one failing pair with another pair that succeeds.

The existing compatibility and preservation checks are appropriate. These points primarily make the
stated bound and continuation observable at the real CLI boundary.

# Provider resilience release handoff

Implemented under Vincent's instruction. No live campaign, frozen deployment, model route or accounting
approval was changed. Atlas should finish its current e8509d1 run before considering an upgrade.

## Frozen release

- Commit: 02ce1034d6f9989a962277108bf88bc99e92e51f.
- Runtime: /private/tmp/pathfinder-02ce103.
- Archive: /private/tmp/pathfinder-02ce103.tar.gz.
- Archive SHA-256: f8f2aae53d28a129c65536e359ae4bebe0371a832ec8c7187b868cba00dd069d.
- Frozen inventory: verified against its commit, with no changed, missing or added runtime files.

## Changes

Provider event and stderr journals are retained durably under transport-evidence, with receipt hashes
and active-call pointers. Structured error codes and Retry-After hints are preserved when exposed.
Known quota/spend codes take precedence over generic rate wording. Partial usage stays evidence;
it is not promoted to a complete accounting total. Unknown usage still blocks strict admission.

Retries now use bounded jitter, honour provider minimum waits, and respect a bounded retry episode.
Default transient delay ceilings are 60/120 seconds; explicit schedules remain supported. Account/model
cooldowns coordinate separate upgraded controllers with locked expiry updates and exclusive recovery
probes. A stale success cannot clear a newer failure. Waiting occurs outside seats and group-budget
locks, with a recheck before dispatch. Health snapshots expose the shared cooldown state.

No automatic uncertain-usage policy is introduced. The previously approved reservation remains limited
to its original receipt. A new failure with missing usage may still need explicit accounting recovery;
this release cannot manufacture provider measurements or guarantee service availability.

## Verification

The fixed-code targeted suite passed 281 tests in 94.31 seconds. It covers transport, failure handling,
provider resilience, admission, health/events, exhaustion, routing, ordinary/shared budgets, reservation
compatibility, lifecycle, coordinator, collection checks and freeze provenance.

A second run imported the frozen runtime explicitly and passed 85 provider, transport and failure tests
in 6.87 seconds. All calls were stubs or local fake CLI processes; no live model calls occurred. Tests
include large stderr streams, journal failure retaining active-call evidence, cumulative/reset counter
samples, independent-process expiry updates, exclusive recovery probes, stop handling and episode caps.

An earlier test process correctly rejected code that changed on disk while it was running. The final
suite was rerun without editing runtime files and passed; no stale-code guard was bypassed.

## Adoption

Read docs/provider-resilience.md for defaults, optional retry settings and limitations. Verify and
archive this runtime before use. Upgrade only at idle ownership boundaries, preserve old runtime/config
records, and record any required provenance acceptance through the canonical launch path. Do not reset
science, clear unrelated stops or replace active engines. New cooldown coordination applies only to
controllers running the new code and sharing the same configured backend/account/model identity.

The evidence journals retain full emitted output and can grow; retain and archive them as campaign
evidence rather than treating them as disposable cache. Actual provider error fields may remain absent
in Codex output, so plain-text capacity reports still do not establish an exact HTTP error or root cause.

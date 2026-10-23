# Status at 05:25 operator local time (03:25 UTC), 23 October 2026

Atlas Pilot 3 extension is censored since 03:11:07 UTC after a partially served verifier failed at provider
capacity and its missing usage blocked shared-budget admission. This is a read-only diagnosis, not a resume
authorisation.

## Totals

Iteration 1 of this failure audit: four terminal pairs: PAUSE=3 and DRAFT=1. Verification is stopped for
pair 5. Pair 6 stopped before its first peer call. Across the six child receipt files: 53 completed calls,
one error and two admission refusals. Known usage is 76,748,164 input and 990,692 output tokens; failed-call
usage remains unknown. These totals exclude any separate smoke receipt roots.

## Blockers

- Rate or capacity: one verified failure, call 398ff543ec6e4b6bab6ae24d278f4d54. The provider reported
  'Selected model is at capacity. Please try a different model.' after 46.5 seconds, an agent message and
  four completed tools. There is no verifier verdict or reported usage.
- Accounting: two verified downstream refusals, calls 793cfe4aea4e4fc7bad11aed620c846c and
  410a0525585845dab0d1a5d731e23148. Shared admission correctly rejects unknown input usage. The frozen
  engine has no immutable usage-reconciliation mechanism.

## Corrections

The capacity error was not an unserved or zero-charge attempt. A session and tools demonstrably ran. Absence
of a final usage object does not establish zero spend. A recovered intermediate counter alone would
establish only a lower bound unless its completeness is demonstrated.

## New results

Pair 5 retains its completed peer and consolidation work at round 1, stage verify. Pair 6 retains stage
peers. The shared-budget failure did not invalidate the four terminal scientific outcomes.

## Still active

Operator reports the coordinator stopped; progress.json records its terminal censored state. No new calls or
controllers were launched by this audit.

## Fixes applied

None (read-only). Original campaign configuration, receipts, stop markers, research and notes remain
untouched.

## Fixes to apply next

Locate authoritative complete usage for Codex thread 01a166bc-073d-77d1-aab3-95b6fca78b98 if available. No
matching session filename was found under the local Codex sessions directory. The transport normally uses
ephemeral sessions.

If complete usage is recovered, a tested immutable reconciliation mechanism must bind the original receipt
and provider evidence before admission can use it. Neither receipt rewriting nor a duplicate appended
receipt is supported: transport.receipts keeps the first row for each call ID. If usage remains unavailable,
report that accounting blocker instead of estimating it as measured usage or bypassing the group guard.

## Next steps

1. Hold dispatch while usage reconciliation remains unresolved.
2. Once a supported repair is tested, verify that canonical resume starts pair 5 at verification and
  preserves peer/consolidation artifacts, then continues pair 6. Do not clear stops merely to retry the same
  accounting failure.

## Decisions needed from the operator

The operator reports no recoverable rollout. The failed call had no configured token or turn ceiling, only a
time limit. A finite usage reservation cannot be demonstrated to bound its actual usage.

Choose whether to retain the hold or explicitly approve a reservation policy for this receipt that preserves
unknown measured usage and discloses unverified actual-total cap compliance. Among 17 successful verifiers,
the largest reported input was 1,400,056 tokens and the largest output was 6,892 tokens, from different
calls. A proposed heuristic reservation is ten times those respective maxima: 14,000,560 input and 68,920
output tokens inside the unchanged aggregate cap. This multiplier is a policy margin, not a statistical
confidence bound or a provider-enforced limit. It is not approved or implemented.

If that policy is authorised, implementation must bind receipt and evidence hashes, reject duplicate or
mismatched reservations, expose measured and reserved totals separately, preserve the original unknown
usage, and pass copied no-replay recovery tests before any live resume.

Evidence: Atlas pilot root /Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-3, child receipts.jsonl files,
thread status.json files and progress.json. Engine inspection: pathfinder/budget_group.py and
pathfinder/transport.py; no reconciliation overlay exists in the inspected implementation.

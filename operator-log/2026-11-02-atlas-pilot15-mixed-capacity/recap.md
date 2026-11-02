# Pilot 15 fourth recovery recap

## Status at 20:55 operator local time (19:55 UTC), 2 November 2026

Coordinator exited censored after budget refusal; no Pilot 15 calls remain active.

### Totals

Terminal pairs: 4, up from 3. Stopped peer phases: 2. New completion: pair 4 reached DRAFT.
The latest failure produced one unknown-usage error and two refused-before-dispatch receipts.

### Blockers

- Rate/capacity: one unserved Codex failure with unknown usage, verified one, inferred zero.
  Call 9a96b49e34354075a39dc464db80dd42, pair 5 round 5.
- Budget refusal: two subsequent admissions refused without model execution, verified two, inferred zero.
  Pairs 5 and 6. Pair 5's marker was then replaced by a canonical operator stop; events retain the budget reason.

### Corrections

The previous future-recurrence path covered served failures only. The initial unserved policy required
a version-1 group and could not extend the current version-5 group. Both extension types now compose.

### New results

Pair 4 completed DRAFT. Maintainer's mixed-chain and pending-arm copy proofs pass without live changes.

### Still active

None in Pilot 15.

### Fixes applied

Runtime 7b62fba adds an unserved extension and mixed approval chains. The updated helper preserves
stop-history events and migrates only selected pending arms. No maintainer changes to live deployment.

### Fixes to apply next

Obtain approval of the inert 100,000-input/1,000-output proposal, install the approved manifest and
runtime under idle ownership, validate reports, then clear only the pair-5 and pair-6 markers.

### Next steps

1. Resume canonical coordinator after approval and verified migration. Pair 5 resumes round-5 peers
   with normal configured allowances; pair 6 follows. No peer replay in terminal pairs or repair reset.

### Decisions needed from the operator

Explicit approval or rejection of the new reservation and its uncertainty. Actual usage remains unknown;
no billing-zero claim or automatic approval is inferred.

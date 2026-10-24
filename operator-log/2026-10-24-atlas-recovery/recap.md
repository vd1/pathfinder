# Atlas Pilot 6 recovery recap

## Status at 16:40 Paris (14:40 UTC), 2026-10-24

Atlas Pilot 6 pair 1 is stopped after its unbriefed consolidation drained; no active-call evidence remains.
This maintainer inspected that state read-only and has not resumed the campaign.

### Totals

Iteration 1 of this maintainer recovery: an existing repair grant remains pending, a paid void consolidation
is retained, and no replacement scientific calls have been made. Pilot-wide totals were not recomputed.

### Blockers

- Contract: the old classic runner ignored grant briefing and its ending rule; verified for Q001-P002.
- Admission: the shared budget lock could starve waiting controllers without an event; reproduced offline.
- Transport: a CLI could remain alive after its final event; reproduced using fake provider processes.

### Corrections

The snapshot status is post-reopen, so direct status restoration would reintroduce the broken state.
A brief scheduling delay reduces contention but does not provide FIFO fairness.
A retained provider result does not justify discarding raw evidence or treating a provider error as success.

### New results

Committed runtime a3d28c8 and its verified freeze provide the fixes and canonical same-grant recovery.
The exact copied Atlas recovery preserves the void attempt and charges, restores the last judged note,
and reaches only a stubbed repair and verifier. No scientific clearance is asserted by the test.

### Still active

No maintainer-started campaign or model process. Other Atlas pilots were not interrupted or assessed here.

### Fixes applied

Classic grants now carry retained feedback and terminate after their verdict. Budget-group waiters use
FIFO tickets and emit deferral events. CLI exit handling is bounded after a final event. Hash-bound
reopen-recover preserves failed history and the existing grant while preparing its supported resume.

### Fixes to apply next

The Atlas operator selects the verified separate runtime at idle ownership and applies the inspected
recovery proposal. The live campaign has not yet received these engine fixes.

### Next steps

1. Keep pair 1 held until the operator validates the frozen handoff and current bindings.
2. Apply canonical recovery, inspect custody, then resume the existing authorised repair under unchanged
   provider and shared-budget guards. A fresh verdict ends that grant.

### Decisions needed from the operator

None for maintainer implementation. Live execution remains with the Atlas operator under the existing
repair authority. Any later grant or budget change requires its own authority.

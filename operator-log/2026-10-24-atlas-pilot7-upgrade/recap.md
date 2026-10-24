# Pilot 7 migration assessment

## Status at 17:07 Paris (15:07 UTC), 2026-10-24

Pilot 7 was observed running pair 1 round 1 peers on 02ce103. Maintainer has not stopped or changed it.

### Totals

Iteration 1: six scheduled pairs, one started and five queued at inspection. No maintainer model calls.

### Blockers

- Contract: incomplete classic peer-stage allowance is not persisted across restart; reproduced offline.
  A mid-peer drain is not an approved migration boundary.

### Corrections

376c01f and a3d28c8 have identical runtime files. The parent coordinator directory has no campaign.json;
canonical stop targets the active child, and its operator stop halts the coordinator after the call drains.

### New results

Cross-frozen-engine proof passed safe drains after readiness, consolidation and verification, with no
replayed completed calls. Incomplete-peer case was held. Actual preflight shows engine-only changes.

### Still active

Coordinator 64615 and its first peer were active at inspection. Operator owns subsequent live observations.

### Fixes applied

None to the live pilot. Separate 376c01f freeze verified and migration proof/handoff prepared.

### Fixes to apply next

No engine patch required for the tested safe-boundary migration.

### Next steps

1. Operator waits for the safe stage, requests canonical child stop, and verifies complete drain.
2. Recheck provenance, select the separate freeze and resume the unchanged schedule with accept-change.

### Decisions needed from the operator

None: Vincent approved the safe-boundary upgrade. Any unrelated new failure remains a separate blocker.

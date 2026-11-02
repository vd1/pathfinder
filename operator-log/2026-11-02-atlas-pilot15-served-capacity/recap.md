# Pilot 15 recovery recap

## Status at 15:11 operator local time (14:11 UTC), 2 November 2026

Stopped after the operator drained the deferred retry; no Pilot 15 runner or model call remains active.

### Totals

Terminal pairs: 3. Stopped consolidation: 1. Pending pairs: 2. These counts are unchanged.
Since that recovery, the remaining peer turn completed, consolidation failed with unknown usage, and
an operator stop generated a refused-before-dispatch receipt. No new research verdict or release.

### Blockers

- Rate/capacity: one served Codex consolidation failed with unknown usage; verified one, inferred zero.
  Call a19a17a5367243c195b33e398b52ecf0, pair 4. Shared-budget refusal protects the remaining work.
- Cancelled before dispatch: operator arm stop ended one deferred retry; verified one, inferred zero.
  Receipt eb83554424434c28917d9d35c08d848e. No additional model service occurred.

### Corrections

The parent-root stop command was invalid because the schedule root has no campaign.json. The operator
used the canonical pair-4 stop successfully. Recovery binds that actual arm marker, not a parent marker.
Unknown usage from a served call cannot use the earlier unserved or reboot policies.

### New results

The peer continuation completed. Consolidation remains unfinished. Maintainer tests prove the bounded
accounting migration and stage resume on a copy, with no live calls.

### Still active

None in Pilot 15. The unrelated experiment's shared provider probe remains outside this recovery scope.

### Fixes applied

Runtime 24131e3 supports a separately approved served-capacity extension with immutable prior approvals.
The maintainer made no live changes. The operator applied only the canonical arm stop.

### Fixes to apply next

Obtain approval for the inert 2,000,000-input/75,000-output proposal, install its new manifest and runtime
under idle ownership, and validate budget reports. Then clear only the bound pair-4 stop.

### Next steps

1. Resume canonical coordinator only after exact proposal approval, migration and successful validation.
   Retry round-5 consolidation, then verify; pairs 5-6 follow with unchanged settings.

### Decisions needed from the operator

Explicit approval or rejection of the proposed uncertain reservation. Actual usage remains unknown and
aggregate cap compliance uncertified. No approval is inferred from repair/resume authority.

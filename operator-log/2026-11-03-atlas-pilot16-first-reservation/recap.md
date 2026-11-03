# Pilot 16 recovery recap

## Status at 09:08 operator local time (08:08 UTC), 3 November 2026

Coordinator exited censored after budget refusals; no Pilot 16 model calls remain active.

### Totals

Iteration 1 for Pilot 16: terminal pairs 2; stopped pending pairs 4. The latest error has unknown usage;
subsequent admissions were refused before dispatch. No new verdict is supplied by this recovery.

### Blockers

- Rate/capacity: one served Codex peer failure, verified one, inferred zero.
  Call b883dfb6c21e49329b07f1e1f8d6c6d6, pair 3 round 4.
- Budget refusal: stops on pairs 3-6, verified four, inferred zero. Unknown input usage blocks further calls.

### Corrections

The prior helper admitted extension policies only. The runtime already supports an initial served
reservation from version 1; the updated helper covers that installation and all later capacity extensions.
The journal contains 523,233 decoded content characters without line endings, but 523,537 physical bytes.

### New results

Retained round-4 files and ledger findings are present, but there is no fresh ready marker after verifier
entry 35. A frozen-runtime copy now proves migration and continuation without changing live evidence.

### Still active

None in Pilot 16.

### Fixes applied

Updated and tested the first-reservation migration helper. Existing durable runtime 7b62fba verified;
no engine patch was needed. No maintainer changes to live deployment or research.

### Fixes to apply next

Obtain approval of the inert 15,000,000-input/150,000-output proposal. Install its version-2 group in
pending arms 3-6, validate reports, and clear only their diagnosed budget markers.

### Next steps

1. Resume canonical coordinator after approval and verified migration. Pair 3 continues round-4 peers
   from retained work under a fresh configured two-call/3,600-second invocation, not a remaining-time carry.

### Decisions needed from the operator

Explicit approval or rejection of the proposed uncertain reservation. Actual usage remains unknown;
no approval or certified cap compliance is inferred from repair/resume authority.

# Pathfinder refactor roadmap

1 October 2026. Spec: `notes/pathfinder-friction.tex` (root causes R1 to R7,
directions D1 to D10, harvest H1 to H12, statarb additions S1 to S9, julien-2
evidence and state failures F01 to F10 and R01 to R04, decisions).
Canonical engine: `pathfinder`. Formats may break compatibility. Billing is
subscription, so budgets are in tokens and calls.

The refactor is split into phases. Each phase gets its own plan, is merged on
its own, and leaves the engine releasable. A phase starts only after the
previous one is merged, except where noted.

| Phase | Scope | Spec items | Depends on |
|---|---|---|---|
| 1 | Failure classification, campaign-wide stops, prompt size gate, receipt fields for session economy | H1, H2, S2 (receipt fields), R1 | none |
| 2 | Event log, derived campaign state with separated research, evidence, editorial, assessment and controller states, execution identifier, operator web page | D1, H4, H10, S4, S8, F09, F10, R04, operator view decision | 1 |
| 3 | Typed evidence inventory and resolver shared by all stages, context by reference, session economy | D4, S1, S2, F01 to F06, F08, R01, R03, julien-2 read-only readers and hash-bound index | 1 |
| 4 | Health policy, batch coordinator, reconciliation transitions, atomic repairs, launcher | D6, H3, H5, H6, H7, S3, S5, S6, F07, R02 | 1, 2 |
| 5 | Contracts over parsers: schema calls, consumer stage | D5, H8, H9, R4 | 1 |
| 6 | Composable EVA as an option (N branches, default 3, then a joint thread) | EVA decision, D10 | 3 |
| 7 | Deployments: statarb on engine-v1.2, then agQSL; julien-2 cherry-picks | D8, statarb and agQSL migration outlines | 1 to 5 |
| 8 | Multi-source intake (arXiv categories, NBER, NEP, SSRN metadata) | H11, S9 | 7 |

Phases 3 and 5 may run in parallel with phase 2 once phase 1 is merged.

Continuous rules for every phase:

- Tests first; the default behave and pytest suites stay green (`RIGGING.md` commands `broad` and `broad-unit`).
- Every generic fix made in a deployment meanwhile is added to the spec as an S item before the phase that owns it starts.
- Each phase ends with a release check and a tag (`engine-v1.2` after phase 1 and 3 at the latest).

Plans:

- Phase 1: `plans/2026-10-01-0030-phase1-failure-classification.md` (merged 99db88e)
- Phase 2 is split: 2a events, execution identifier and state document (`plans/2026-10-01-0130-phase2a-events-and-state.md`); 2b operator web page and server hardening on that document (`plans/2026-10-01-0300-phase2b-operator-view.md`); 2a merged ef20a38, 2b merged c669dbe.
- Phase 3 is split: 3a agent workspace, evidence and papers by reference, read-only verifiers, tool-error receipts (`plans/2026-10-01-1130-phase3a-agent-workspace-and-context.md`); 3b typed evidence inventory and resolver (outline at the end of the 3a plan).

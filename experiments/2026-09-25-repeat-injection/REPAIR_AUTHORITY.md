# Supervision repair authority

Authorized by the user on 2026-09-25: repair the saved malformed verifier reply,
resume the pilot, and give Astra authority to perform such repairs.

This supplements the frozen launch scope without changing scientific prompts,
inputs, models, budgets, pair allocation or the research engine. The original
six-hour watch ended on a blocker; its queued successor correctly declined to
override that blocker. The resumed watch retains the already authorized deadline
of 2026-09-26 04:37:24 Europe/Paris, not a fresh twelve-hour allowance.

## Permitted repair

Astra may run `repair_verdict.py ARM PAIR` with the supplied Python executable
for an exact blocked verifier stage. The helper supports only an existing,
completed PAUSE or DRAFT reply with a nonempty reason and null action, where
illegal JSON string escapes are the sole defect. It preserves valid escapes,
the raw response, the research note, and the decision's meaning. It checks the
saved reply against the completed call's receipt, refuses duplicate round
verdicts, and records before-state, hashes, corrected JSON and incidents.

The helper acquires coordinator and child campaign locks and refuses live
recorded owners, active calls, operator stops and budget stops. Before calling
it, inspect the supplied process tree for surviving descendants as well. Never
remove active-call records or bypass a rejected guard.

Checkpoint and verdict-history writes by this helper are expressly authorized
campaign-evidence repairs. They are not authorization to change a scientific
verdict. Once repaired, use the unchanged full-pipeline resume command and
verify that the intended editing or paper stage advances. Preserve completed
work and keep the incident open until that advancement is observed.

## Outside this authority

Do not ask another model for a replacement judgment, infer missing fields,
change a decision, rewrite scientific claims, repair ambiguous output, modify
the frozen engine or protocol, increase budgets, or clear stop markers.
ITERATE/REVISE transition repair and malformed author/reviewer outputs require
operator direction until a corresponding safe recovery operation is authorized.
If a repair is interrupted between writes, stop for reconciliation rather than
manually bypassing the duplicate-round safeguard.

The saved Q3P2 response is PAUSE. This repair adds no scientific replicate and
uses no model call. Its original raw response remains available for audit.

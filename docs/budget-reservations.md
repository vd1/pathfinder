# Reservations for unknown usage

A partially served capacity failure can leave token usage unknown. The normal shared-budget guard
blocks subsequent calls. It does not treat that failure as free.

The `budget-reservation` command supports an explicit accounting-policy exception for an evidenced
Codex capacity failure. A reservation is an estimate charged against the existing aggregate cap.
It is not measured usage or a demonstrated upper bound. Actual aggregate cap compliance remains
uncertified. Original receipts, raw events and missing counters remain unchanged.

## Prepare without approval

Run `budget-reservation propose` with `--root` naming the campaign containing the failed receipt,
`--call-id`, positive `--input-tokens` and `--output-tokens`, an explicit `--rationale`, and `--out`.
The command writes a new inert proposal and prints its canonical SHA-256. It does not change
configuration, stop markers, budgets or execution state, and makes no model calls.

The proposal binds the exact receipt line including its raw events, canonical campaign root,
original group manifest bytes, every group member, unchanged caps and the proposed amounts.
Only a version 1 group may be the parent. The original manifest must remain available unchanged.
The initial policy supports exactly one partially served capacity failure with both token counters
and the provider usage object absent. Other failure classes or additional unknown calls still block.

## Explicit approval and new manifest

An operator records real authority in a separate approval JSON. Required keys are
`proposal_sha256`, `approved`, `accept_unknown_usage`, `accept_uncertified_actual_total`,
`approved_by`, `approved_at` and `authority`. The three boolean fields must be true; identity,
time and authority must be nonempty strings. A template with false values is not approval.
The engine validates binding and declaration; it cannot authenticate a human decision from JSON.
The operator remains responsible for recording actual authority, never synthesising it.

`budget-reservation manifest --proposal FILE --approval FILE --out NEW-MANIFEST` validates the
record and writes a new version 2 group manifest. It does not install or activate that manifest.
All output files use exclusive creation. Nothing overwrites earlier proposals or evidence.

Only after approval and quiescent ownership may the operator repin future dispatching campaigns
to the new common manifest and SHA-256, preserving the old configuration and manifest. A new
manifest path has a new lock: old-group and new-group calls must never run concurrently. Completed
members can retain their old configuration as receipt-only members; any future dispatch from them
must first join the new group. Do not unlink either lock.

Clear only diagnosed stop markers with the canonical `stop --clear` command. Resume the existing
coordination with a recorded `--accept-change` reason. Do not reset scientific state or erase receipts.
A stopped verifier resumes verification; terminal research entries are skipped normally.

## Reporting and guard behaviour

`budget-reservation report` displays `measured`, `reserved`, `admission_total`, `projected`,
`unknown_calls`, `actual_total_certified` and `refusal`. Measured tokens are the sum of reported
counters, not a claim that unknown calls used zero tokens. The call count includes served attempts,
including the reserved failure. The ordinary projected-next-call calculation uses measured plus
reserved tokens, including the reservation in its mean. Reservations never raise the cap.

Manifest, approval, receipt or parent-evidence mismatches fail before dispatch. Duplicate original
receipt IDs and duplicate reservation records are rejected. Additional unresolved active calls or
unknown usage remain blocking. The original receipt reader and ordinary per-campaign usage reports
are unchanged; use the shared-group report for the reservation-adjusted admission balance.

An eventual provider measurement requires a separately supported reconciliation. This version does
not release, overwrite or replace the reservation and does not authorise further exceptions.

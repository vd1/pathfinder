# Atlas Pilot 3 uncertain-usage reservation capability

Status: implemented, tested and frozen. The proposal is inert; real approval is still pending.
No live model calls, campaign writes, stop clearing, configuration changes or activation occurred.

## Exact runtime and packet

- Commit: e8509d1397c3895340a34e03bf697ecab2b5dc9a.
- Frozen runtime: /private/tmp/pathfinder-e8509d1.
- Archive: /private/tmp/pathfinder-e8509d1.tar.gz.
- Archive SHA-256: 7536af3670d50da3ae584333af1ef6edced218b0d650bcdad1fa06fa7093eb46.
- Canonical proposal SHA-256: 988dfe73cba491ad93f30bc2cf40127afc760cdb74341348d2ce6508a4ebb76f.
- Target receipt: 398ff543ec6e4b6bab6ae24d278f4d54, pair-5, first verifier.
- Proposed reservation: 14,000,560 input and 68,920 output tokens.

The packet directory is operator-log/2026-10-23-atlas-budget-reservation in the maintainer repository.
`bindings.json` hashes the proposal, false approval template, commands, verification and copy results.
The canonical proposal hash uses canonical JSON, so it differs from the pretty-printed file hash.

## Accounting meaning

The reservation is a policy margin based on ten times the respective maximum input and output
reported by 17 completed Pilot 3 verifiers. It is not measured usage or an upper-bound guarantee.
Actual failed-call usage remains null and actual aggregate cap compliance remains uncertified.
The original 1,000,000,000 input and 14,000,000 output caps and all six receipt roots are preserved.

Read-only current reporting has known tokens of 76,748,164 input and 990,692 output. With the
proposed reservation, the accounting totals would be 90,748,724 input and 1,059,612 output before
future calls. Admission additionally applies the existing next-call mean projection. Another
unknown call or unresolved active-call record still blocks; this is not a general waiver.

## Inert commands and approval boundary

`commands.json` supplies exact argument arrays for the frozen CLI. `propose_argv` writes only a
new proposal under /private/tmp and refuses to overwrite it. `report_argv` only reads the current
group and receipts. The provided proposal already binds the current receipt and original manifest.

Do not run activation while approval is pending. `approval-template.json` deliberately has false
approval flags and empty authority fields; the engine rejects it. Record real owner authority only
after the decision, bound to the canonical proposal hash, including explicit acceptance of unknown
usage and uncertified actual-total compliance. Human authority is an operator responsibility; JSON
cannot authenticate a person.

After approval, `budget-reservation manifest --proposal FILE --approval FILE --out NEW-MANIFEST`
creates a separate pinned version 2 group; it still does not install it. See docs/budget-reservations.md
for the required approval fields. Revalidate original evidence immediately before creating it.

At quiescent ownership, archive the old configs and repin only future dispatching members, pair-5
and pair-6, to the same new manifest and SHA. Preserve the original manifest and lock. Completed
members remain receipt-only roots under unchanged configurations; any later dispatch from them
must first join the new group. Do not permit concurrent dispatch against old and new group locks.
Use the verified new runtime separately; do not overwrite an active engine.

Inspect the reservation-adjusted group report. Clear the diagnosed pair-5 and pair-6 stop markers
with canonical `stop --clear`, then resume the existing expanded coordination with an explicit
`--accept-change` reason recording the approved accounting exception and runtime change. Preserve
scientific state, receipts, notes, ledger and prior coordination history. No model changes are needed.
Provider capacity may still recur: this repair addresses accounting, not provider availability.

## Verification

The final targeted regression suite passed 103 tests, including shared budgets, reservations,
coordinator, CLI, collection checks, ordinary budgets and freeze provenance. Both new documentation
and the diagnosis pass style gates without errors or warnings.

The actual six-child campaign was copied offline, excluding dependency and tool-cache directories.
Copy-local model routes were replaced with stub transport, with assertions forbidding live backends.
The frozen runtime completed the copied coordinator after canonical copy-local stop clearing:

- Pairs 1 through 4 made no calls; their receipt bytes remained identical.
- Pair 5 ran only verification. Its ledger, note, derivations and consolidation files were preserved
  across 14 file checks, as were all original receipt bytes.
- Pair 6 ran peer, consolidation and verification in sequence.
- Every original receipt remained a byte-identical prefix, and failed-call usage stayed unknown.

Tests reject missing or mismatched approval, changed amounts/scope/evidence, duplicate receipts,
duplicate reservations, invalid amounts and cap overflow. Unrelated unknown usage and active calls
still refuse admission. No original scientific verdict is synthesized by the reservation mechanism.
The copied stub verdicts are test output, not scientific judgments about the live accounts.

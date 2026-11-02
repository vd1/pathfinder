# Pilot 15 served-capacity recovery

## Runtime and scope

Use commit `24131e3e12621009eadf6c546ef1804de7194871`, durably frozen at
`/Users/v/Code_2026/pathfinder/.frozen-runtimes/24131e3`.
Archive: `/Users/v/Code_2026/pathfinder/.frozen-runtimes/24131e3.tar.gz`.
Archive SHA: `3f5e0f65a02c0f053357fe90c3c6f3b7d766e7cc7cdd74f3c87110d219bb535b`.
Manifest SHA: `0b8bb6455c1dcc16983bc18929133d0066c85f37cc024c7b1283d820a7ee84c7`.
Canonical verification and 185 regression tests passed on both working and frozen runtime.
No live pilot files were changed by the maintainer and no real models were called.

The change adds `served-capacity-extension-v1`, an explicit approval-per-call extension to an existing
approved budget group. It validates a Codex error/rate receipt, unknown usage, a single failed capacity
turn and observed model service against the full journal hash/size and retained receipt. Receipt event
compaction is checked against the exact canonical compactor; the full journal remains authoritative.
A version-5 group inherits every prior reservation/approval unchanged and appends exactly one new
approved exception. Further qualifying recurrences use the same runtime, but require fresh proposals
and separate approvals. Changed evidence, reused approvals, duplicate calls, zero reservations or
changed scope/caps are rejected. No routing, research, prompt, retry or allowance setting changes.

## Diagnosis and final drained state

The served consolidation failed after 607.3 seconds, 20 tool calls and no reported usage. The error is
provider capacity, not an unserved request, reboot orphan or scientific failure. Original runtime 7046a19
already treats it as transient. The retry waits at the shared provider gate before budget admission.
After that gate opens, strict accounting refuses the unknown call before another model dispatch and
writes a child budget stop. If the bounded retry episode expires first, the provider gate refuses there.
Neither outcome consumes a scientific repair or advances the consolidation stage.

The operator instead drained using the pair-4 arm stop. The initially suggested parent-root stop was
incorrect: the schedule root has no campaign.json, so that command failed before writing anything.
The correct arm stop succeeded; coordinator 97562 exited. Only pair 4 has a stop marker, reason operator,
at 14:03:22 UTC. The parent reports stopped due to that arm. No active-call records remain.
The final refused-before-dispatch receipt is retained in the migration bindings.

Pair 4 remains round 5, stage consolidate. There is no saved successful round-5 consolidation response.
Resume repeats consolidation under its normal 3,600-second request allowance, then verifies. It does
not repeat peers, reset rounds, clear repair metadata or decrement a scientific repair. Ada's round-5
files and ledger are retained. Any files written by the failed consolidation are also retained; failure
is not promoted to a successful response. This is ordinary stage resume, not continuation of the dead
provider session. Subsequent transport retry limits remain unchanged.

## Inert accounting proposal

`proposal.json` binds served call `a19a17a5367243c195b33e398b52ecf0`, the exact original receipt,
227,903-byte journal, current version-4 manifest and unchanged caps. Proposal SHA:
`b85f9634cf396a6b35e207e36f076a715f6800c4748feaac0d605974d9a46605`.

Proposed amount: 2,000,000 input and 75,000 output tokens. Among 19 completed Pilot 15 consolidation
receipts, maxima were 692,362 input and 24,598 output. The failed 607.3-second call exceeded the completed
maximum of 590.9 seconds. Both amounts are rounded above twice the observed token maxima. The exact
reference receipts are in `estimate-basis.json`. This is a heuristic, not measured usage or a proven
upper bound. The actual total remains uncertified. The prior unserved and reboot reservations remain
unchanged, including their approvals. No reservation has been approved by this handoff.

`migration-snapshot.json` binds the final drained runner/config/receipt/thread files and the sole arm
stop. This includes the post-stop refusal, so an earlier running-state snapshot cannot be substituted.
`approval-template.json` deliberately has false booleans and empty signatory fields. Record genuine
approval of this exact proposal and uncertainty before manifest creation or migration. The engine
validates the declaration and hashes, not the human signatory's identity.

## Exact operator commands

Keep the current pilot drained. Use the existing Atlas environment outside restrictions that block
PID liveness or ownership locks. Do not unlink locks or touch the unrelated experiment/provider probe.

```sh
repo=/Users/v/Code_2026/qap-atlas
pilot=$repo/pilots/atlas-pilot-15
packet=/Users/v/Code_2026/pathfinder/operator-log/2026-11-02-atlas-pilot15-served-capacity
py=/Users/v/.local/share/uv/python/cpython-3.13.0-macos-aarch64-none/bin/python3.13
export PYTHONPATH=/Users/v/Code_2026/pathfinder/.frozen-runtimes/24131e3
cd "$repo"
"$py" -m pathfinder.cli verify-frozen "$PYTHONPATH" --repo /Users/v/Code_2026/pathfinder
"$py" -m pathfinder.cli --root "$pilot/runs/pair-4" budget-reservation report
```

The report still refuses unknown usage at this point. After the owner approves the exact proposal,
record the real approval in a new `$pilot/operator/served-capacity-approval.json` using the template
schema, correct proposal SHA and actual signatory/time/authority. Then:

```sh
new_manifest=$pilot/operator/budget-group-served-a19a17a5.json
"$py" -m pathfinder.cli budget-reservation manifest \
  --proposal "$packet/proposal.json" \
  --approval "$pilot/operator/served-capacity-approval.json" \
  --out "$new_manifest"
"$py" "$packet/repin.py" apply \
  --manifest "$new_manifest" --snapshot "$packet/migration-snapshot.json"
for n in 4 5 6; do
  "$py" -m pathfinder.cli --root "$pilot/runs/pair-$n" budget-reservation report
done
```

The installer validates approval/evidence and all final-state bindings, takes parent/member ownership
and old/new group locks, refuses any active call or changed stop, and saves original configs exclusively.
It changes only the group manifest/hash in pairs 4-6. The original manifest, receipts and all research
state stay unchanged. Reports must have refusal null and uncertified actual totals; unknown usage is
reserved, never rewritten as measured. Existing stop markers still prevent dispatch until cleared.
If installation is interrupted or backups exist, inspect rather than deleting evidence or repeating blindly.

Only after those reports pass, clear the exact validated pair-4 operator stop and launch:

```sh
"$py" -m pathfinder.cli --root "$pilot/runs/pair-4" stop --clear
export PATHFINDER_CODEX="$py $repo/scripts/atlas_codex.py"
export ATLAS_CLI_STDERR_DIR=$pilot/operator/cli-stderr
"$py" -m pathfinder.cli --root "$pilot" launch -- \
  --accept-change "Approved served-capacity reservation and 24131e3 runtime; research settings and caps unchanged" \
  coordinate "$pilot/schedule.json"
```

No stops on pairs 5-6 or parent need clearing. Canonical launch records the engine/group change. The
provider cooldown still applies and may defer the new consolidation; do not bypass it. Check controller
and first-call progress after 60 seconds. Pairs 1-3 stay terminal with unchanged configs and receipt-only
membership. Any future dispatch from them must first join the current group/runtime. Never operate
controllers against old and new group manifests concurrently.

## Future qualifying recurrence, no new runtime release

First diagnose the new call and drain its actual campaign root with `stop`, then wait for ownership and
active calls to clear. Use a fresh name for every artifact. Set `arm_root`, `new_call`, `input_estimate`,
`output_estimate` and `basis` from that incident. Do not reuse the amounts or rationale automatically.

```sh
future_proposal=$pilot/operator/served-$new_call-proposal.json
"$py" -m pathfinder.cli --root "$arm_root" budget-reservation propose \
  --policy served-capacity-extension-v1 --call-id "$new_call" \
  --input-tokens "$input_estimate" --output-tokens "$output_estimate" \
  --rationale "$basis" --out "$future_proposal"
```

This is inert. Present the new digest and estimate to the owner, then record a separate matching approval.
The manifest command above accepts a fresh proposal/approval/output and inherits the then-current group.
For the remaining migrated arms, prepare a fresh final-state snapshot. For example, if pairs 4-6 remain:

```sh
"$py" "$packet/repin.py" snapshot --pilot "$pilot" \
  --proposal "$future_proposal" --pairs 4 5 6 \
  --out "$pilot/operator/served-$new_call-migration.json"
```

Select only the actual pending arms, all pinned to that proposal's current parent manifest. Apply with
that snapshot and the newly approved manifest, validate reports, clear only diagnosed stops using their
actual campaign roots, and use canonical launch with the new acceptance reason. The helper refuses
unexpected stops, live runners, changed files, wrong parent pins and duplicate installation backups.
Different error classes, missing journals or a changed research contract require separate diagnosis;
this policy does not automatically excuse other unknown usage.

## Copy proof

The exact frozen runtime passed 185 tests, including repeated separately approved extensions, changed
approvals/evidence, canonical compacted receipts, duplicate prevention and provider-gate-before-budget
refusal without dispatch. The full drained-pilot copy used the real coordinator/runner/research state
machine with only model execution stubbed. Pair 4 called consolidate at 3,600 seconds, then verify;
pairs 5-6 followed. No peer replay occurred in pair 4. Repair fields, original Ada files, ledger prefix,
provider receipts and terminal threads remained intact. Synthetic approvals/root rebinding were used
only in the copy; none represents live authority. All 38,548 checked live files stayed byte-identical.
Exact proof, migration bindings and runtime hashes accompany this handoff. Tests do not certify unknown
usage or predict new scientific verdicts.

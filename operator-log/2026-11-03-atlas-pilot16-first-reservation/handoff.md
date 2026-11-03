# Pilot 16 first capacity reservation

## Ready runtime and scope

No engine patch is required. Use the existing durable runtime
`7b62fbae9b86b222367aadbcf8314ea3238983d1` at
`/Users/v/Code_2026/pathfinder/.frozen-runtimes/7b62fba`.
Archive: `/Users/v/Code_2026/pathfinder/.frozen-runtimes/7b62fba.tar.gz`.
Archive SHA: `c71e99a5bc73c83372d57cf5c6a39285c7d7a56b2dce8f01d9126f93f302cf33`.
Manifest SHA: `28bb5067627e62f13e2fd85b7dbbc504e6edd8a87e450ff497e02e5ead9312aa`.
Canonical verification passed. The updated packet helper supports initial version-1 reservations and
later served/unserved extensions. It is a committed companion to the freeze, not a deployment workaround.

189 relevant tests passed against the exact frozen runtime, including a version-1 start followed by
mixed recurrences and shrinking pending-arm scopes. The actual Pilot 16 copy resumed with all model
execution stubbed. All 10,335 checked live files remained unchanged. No live reservation, migration,
stop clearing, model call or scientific script execution occurred.

## Diagnosis and continuation

The served capacity failure has 186 retained events and 73 completed commands, ending turn.failed,
with no usage. Its journal SHA is
`3dcd16ce9fe312c48bba9137f9f186ff34655c2296d799bddf5c3ceb29a6cdf1`.
The physical file is 523,537 bytes. The reported 523,233 is decoded content characters excluding the
186 line endings. The helper verifies the full file against the receipt binding, including canonical
receipt compaction; it does not rely solely on the receipt's shortened tool outputs.

Coordinator 59203 has exited, the parent is censored, and no active calls remain. Pairs 1-2 are terminal.
Pair 3 is stopped at round-4 peers; pairs 4-6 are stopped at round-1 peers. Each pending arm has the
budget stop naming pair 3's unknown usage. There is no parent stop.

Pair 3's latest verifier entry is 35. Entries 36-43 contain round-4 work, but no fresh ready marker.
Files including ada/round4-streaming.txt, source-audit-round4.json and check_round4.py exist and are kept.
Resume continues the unfinished round-4 peer phase from the retained ledger and files. It does not
restart rounds 1-3, erase round-4 work, fabricate a successful reply or consume a scientific repair.

Allowance detail: ordinary resume starts a fresh configured peer invocation with two calls and 3,600
peer seconds, plus the normal 30-second transport grace. It does not subtract the failed attempt's
1,673.4 seconds to leave 1,926.6 seconds. The transport error was followed by a budget refusal before the
logical peer call returned; normal peer invocation counters are not reconstructed from those receipts.
The special reboot-orphan carry path does not apply here. This is existing engine behavior, not a change
to settings or research code in this handoff. The failed attempt remains counted for budget accounting;
the refused retries are uncharged. The copy checks call index 0, timeout 3,630, round 4 and unchanged
repair fields before dispatch.

## Inert proposal

`proposal.json` uses the existing `served-capacity-reservation-v1` policy on the original version-1
group. Approval produces version 2, after which the existing extension policies work normally.
Call: `b883dfb6c21e49329b07f1e1f8d6c6d6`.
Proposal SHA: `0a175e6a3e54a38d93c6dbf1945111a768dfcc3c0be8325a5d9465f5359eab1b`.

Proposed amount: 15,000,000 input and 150,000 output tokens. Among 11 completed Pilot 16 peer calls,
maxima were 6,105,086 input and 63,653 output. Both estimates exceed twice the respective maximum,
rounded upward. The fastest observed input rate, scaled to 1,673.4 seconds, gives approximately
5,501,055 input tokens. `estimate-basis.json` records those receipt identities and measurements.
These are heuristics, not measured usage or a proven upper bound. Actual aggregate cap compliance
remains uncertified. Original caps and unknown receipt counters are unchanged.

The proposal binds the original receipt and parent manifest; the final-state migration snapshot binds
runner metadata, stop markers, receipts, events, pending thread files and full transport evidence.
The packet hash manifest binds these artifacts together. The template has false approval booleans and
empty signatory fields. Repair/resume authority does not approve this reservation. Record genuine
approval of the exact digest and uncertainty before applying. The engine checks hashes/declarations,
not human identity.

## Exact operator commands

Keep all Pilot 16 arms idle. Use the existing Atlas environment with PID and lock visibility.

```sh
repo=/Users/v/Code_2026/qap-atlas
pilot=$repo/pilots/atlas-pilot-16
packet=/Users/v/Code_2026/pathfinder/operator-log/2026-11-03-atlas-pilot16-first-reservation
py=/Users/v/.local/share/uv/python/cpython-3.13.0-macos-aarch64-none/bin/python3.13
export PYTHONPATH=/Users/v/Code_2026/pathfinder/.frozen-runtimes/7b62fba
cd "$repo"
"$py" -m pathfinder.cli verify-frozen "$PYTHONPATH" --repo /Users/v/Code_2026/pathfinder
"$py" -m pathfinder.cli --root "$pilot/runs/pair-3" budget-reservation report
```

The report still refuses unknown usage. After explicit approval, record actual signatory/time/authority
in a new `$pilot/operator/served-b883-approval.json` using the supplied template and exact proposal SHA.
Then:

```sh
new_manifest=$pilot/operator/budget-group-served-b883.json
"$py" -m pathfinder.cli budget-reservation manifest \
  --proposal "$packet/proposal.json" \
  --approval "$pilot/operator/served-b883-approval.json" \
  --out "$new_manifest"
"$py" "$packet/repin.py" apply \
  --manifest "$new_manifest" --snapshot "$packet/migration-snapshot.json"
for n in 3 4 5 6; do
  "$py" -m pathfinder.cli --root "$pilot/runs/pair-$n" budget-reservation report
done
```

The helper validates approval, source journal and final-state hashes, takes parent/member ownership and
old/new group locks, refuses active calls or changed stops, and saves configs exclusively. Only pairs
3-6 change their group manifest/hash. Pairs 1-2 remain untouched. No thread state, receipt, event,
prompt, route, cap or research allowance is edited. If a backup already exists or installation is
interrupted, inspect before retrying; never delete evidence or locks.

Reports must show refusal null and the original unknown call reserved, with actual totals uncertified.
Only then clear the diagnosed child budget markers and launch:

```sh
for n in 3 4 5 6; do
  "$py" -m pathfinder.cli --root "$pilot/runs/pair-$n" stop --clear
done
export PATHFINDER_CODEX="$py $repo/scripts/atlas_codex.py"
export ATLAS_CLI_STDERR_DIR=$pilot/operator/cli-stderr
"$py" -m pathfinder.cli --root "$pilot" launch -- \
  --accept-change "Approved Pilot 16 first served-capacity reservation and 7b62fba runtime; settings and caps unchanged" \
  coordinate "$pilot/schedule.json"
```

There is no parent stop to clear. Canonical launch records the engine/group change, skips terminal pairs
1-2 and continues pair 3's peers. Provider cooldowns still apply. Check the controller and first child
after 60 seconds. Do not run old-group and new-group controllers concurrently. Future dispatch from a
terminal arm would require migration to the current group/runtime first.

## Later served or unserved recurrences, no new release

Diagnose the exact new error and drain the actual campaign root with `stop`; wait for ownership and
active calls to clear. Set `arm_root`, `new_call`, `policy`, `input_estimate`, `output_estimate` and `basis`
from that incident. With an approved version-2 or later group, choose:

| Retained evidence | Policy |
| --- | --- |
| Capacity failure after observed service | served-capacity-extension-v1 |
| Strict no-observed-model-activity capacity stream | unserved-capacity-extension-v1 |

```sh
future_proposal=$pilot/operator/capacity-$new_call-proposal.json
"$py" -m pathfinder.cli --root "$arm_root" budget-reservation propose \
  --policy "$policy" --call-id "$new_call" \
  --input-tokens "$input_estimate" --output-tokens "$output_estimate" \
  --rationale "$basis" --out "$future_proposal"
```

This is inert. Obtain a fresh separate approval for the new digest and uncertainty; never reuse an old
approval or estimate automatically. Create a fresh manifest using the same canonical manifest command.
Create a fresh migration snapshot selecting only then-pending arms. For example, if only pair 6 remains:

```sh
"$py" "$packet/repin.py" snapshot --pilot "$pilot" \
  --proposal "$future_proposal" --pairs 6 \
  --out "$pilot/operator/capacity-$new_call-migration.json"
```

Use `--pairs 3 4 5 6`, `--pairs 4 5 6` or `--pairs 5 6` when those are the actual pending arms. All selected
arms must share the proposal's current parent pin. Apply with the newly approved manifest and snapshot,
validate reports, clear only diagnosed arm stops and launch with an explicit change reason. Both extension
policies preserve all previous approvals. New unknown calls remain blocking until separately approved.
Different errors, unrecognised streams or unexplained stops require diagnosis first.

## Proof and limits

The tests start from version 1, apply this first served reservation, then alternate served and unserved
extensions with fresh synthetic approvals. Scope shrinks from pairs 3-6 to pair 6 alone. Tests reject
reused approvals, duplicate calls and modified journal bindings before any configuration writes.

The real-pilot copy used the exact 7b62fba runtime and canonical coordinator/research transitions with
model execution stubbed. It cleared exactly four child budget stops, continued pair-3 round-4 peers,
then consolidated/verified and ran pairs 4-6. Original provider receipts, Ada files, prior consolidation
artifacts, ledger prefix and terminal threads remained intact. Only copy-root paths, budget-marker paths
and group pins were rebased, with synthetic approval confined to the copy. All 10,335 checked live files
were unchanged. Tests establish mechanics and preservation, not scientific outcomes or actual usage.

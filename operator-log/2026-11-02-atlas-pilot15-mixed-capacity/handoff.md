# Pilot 15 fourth recovery: mixed capacity extensions

## Tested runtime

Commit `7b62fbae9b86b222367aadbcf8314ea3238983d1` is durably frozen at
`/Users/v/Code_2026/pathfinder/.frozen-runtimes/7b62fba`.
Archive: `/Users/v/Code_2026/pathfinder/.frozen-runtimes/7b62fba.tar.gz`.
Archive SHA: `c71e99a5bc73c83372d57cf5c6a39285c7d7a56b2dce8f01d9126f93f302cf33`.
Manifest SHA: `28bb5067627e62f13e2fd85b7dbbc504e6edd8a87e450ff497e02e5ead9312aa`.
Canonical verification passed; 188 regression tests passed on working and exact frozen runtime.
The actual final-state copy resumed with model execution stubbed. All 38,766 checked live files remained
unchanged. No live migration, reservation approval, stop clearing or model execution by the maintainer.

## Diagnosis and allowance semantics

Pair 5's 4.2-second error contains only thread start, the recognised CLI-local warning, turn start and
capacity failure. There is no observed model-produced item and no tool call. The 614-byte journal SHA is
`4637a0f99db58ccf79722b3408e4aa2984871834cc56c42a3720c96d9c565e04`.
The new policy uses the existing strict unserved evidence validator; it does not infer zero billing.

The failed attempt remains a counted budget call with unknown usage. Its retry and pair 6's refusal
were never dispatched and are excluded from charged budget calls. Neither the failed transport attempt
nor the refused retry completed the logical peer call. Ordinary resume does not carry those attempts
into the peer phase's in-memory allowance: pair 5 starts round 5 with the configured two calls and
3,600 peer seconds, with the usual 30-second transport grace on a full-duration request. The frozen-copy
proof checks call index 0 and timeout 3,630. This describes existing research behavior; this release
changes no allowance settings or research code.

The latest completed verification belongs to round 4. No round-5 Ada file or successful round-5 peer
receipt exists. Resume therefore runs round-5 peers, not consolidation or an earlier round. Existing
rounds 1-4, Ada files, ledger and repair fields are retained. No reopen, fresh research grant, repair reset,
manual state edit or provider switch is needed. Future peer work can naturally add new findings.

Coordinator 9944 has exited and no active calls remain. Pairs 1-4 are terminal. Pair 5 is stopped at
round-5 peers; pair 6 is stopped at round-1 peers. Only these markers exist:

- Pair 5: operator, 18:11:01 UTC, replacing its 18:10:58 budget marker.
- Pair 6: budget refusal, 18:10:58 UTC, naming the unknown pair-5 usage.

`migration-snapshot.json` binds both current markers, all receipts and events, configs, runner metadata
and pending thread files. The earlier pair-5 budget reason remains in its bound events.jsonl; it is not
reconstructed or overwritten. The parent has no stop marker, and pair 4 needs no stop clearing.

## Policy and inert proposal

`unserved-capacity-extension-v1` extends an existing approved group with a version-6 manifest.
`served-capacity-extension-v1` continues to produce version 5. Both policies now accept inherited
version-5/6 chains, so qualifying served and unserved recurrences can alternate without another runtime
release. Each extension appends exactly one separately approved proposal, retaining every prior
reservation and approval unchanged. The current three approvals remain the exact prefix.

The strict served and unserved evidence classifiers remain distinct. Each new call needs its own
receipt/journal binding, estimate, rationale and user approval. Changed evidence, reused approvals,
duplicate reservations, changed caps or altered inherited records are refused. Unknown usage stays
unknown. This does not automatically cover other errors, providers or unrecognised event streams.

`proposal.json` binds call `9a96b49e34354075a39dc464db80dd42`, its receipt/journal, the current version-5
parent manifest and unchanged group caps. Its SHA is:
`50bdb89a6d67ab6aa333bea38b882d0f996e126d1b748dc566537826e3e6e0c8`.

Proposed reservation: 100,000 input and 1,000 output tokens. Basis: no observed model service or tools
in the bound 4.2-second capacity stream; this is the same small uncertainty convention used at the first
unserved stop. It is not a measured value or statistically proven upper bound. No observed service does
not prove zero billing, and actual aggregate cap compliance remains uncertified. The template has false
approval booleans and empty signatory fields. No approval is implied by repair/resume authority.

The proposal is linked by digest to the final-state migration snapshot. `packet-sha256.json` binds the
proposal, snapshot, helper and proof together. The engine validates declarations and hashes, not the
human signatory's identity. Do not use synthetic test approvals as live authority.

## Exact operator procedure

Keep all arms idle while inspecting and migrating. Use the existing Atlas environment, with access to
PID liveness and locks. Preserve the old runtime, manifests and all failure evidence.

```sh
repo=/Users/v/Code_2026/qap-atlas
pilot=$repo/pilots/atlas-pilot-15
packet=/Users/v/Code_2026/pathfinder/operator-log/2026-11-02-atlas-pilot15-mixed-capacity
py=/Users/v/.local/share/uv/python/cpython-3.13.0-macos-aarch64-none/bin/python3.13
export PYTHONPATH=/Users/v/Code_2026/pathfinder/.frozen-runtimes/7b62fba
cd "$repo"
"$py" -m pathfinder.cli verify-frozen "$PYTHONPATH" --repo /Users/v/Code_2026/pathfinder
"$py" -m pathfinder.cli --root "$pilot/runs/pair-5" budget-reservation report
```

The report still refuses unknown usage. After explicit approval of the exact proposal and uncertainty,
record actual signatory/time/authority in a new `$pilot/operator/unserved-9a96-approval.json`, using the
supplied template schema and correct proposal digest. Then:

```sh
new_manifest=$pilot/operator/budget-group-unserved-9a96.json
"$py" -m pathfinder.cli budget-reservation manifest \
  --proposal "$packet/proposal.json" \
  --approval "$pilot/operator/unserved-9a96-approval.json" \
  --out "$new_manifest"
"$py" "$packet/repin.py" apply \
  --manifest "$new_manifest" --snapshot "$packet/migration-snapshot.json"
for n in 5 6; do
  "$py" -m pathfinder.cli --root "$pilot/runs/pair-$n" budget-reservation report
done
```

The helper validates the approved proposal and final-state hashes, acquires parent/member ownership and
old/new group locks, refuses active calls or changed stops, and saves original configs exclusively.
Only the group manifest/hash in pairs 5 and 6 changes. Pairs 1-4 remain untouched. No receipts, events,
thread states, model routes, prompts, caps or research settings change. If a backup already exists or
installation is interrupted, inspect rather than deleting evidence or repeating blindly.

Both reports must have refusal null and show the unknown call reserved, with actual totals uncertified.
Only then clear the two validated arm markers:

```sh
for n in 5 6; do
  "$py" -m pathfinder.cli --root "$pilot/runs/pair-$n" stop --clear
done
export PATHFINDER_CODEX="$py $repo/scripts/atlas_codex.py"
export ATLAS_CLI_STDERR_DIR=$pilot/operator/cli-stderr
"$py" -m pathfinder.cli --root "$pilot" launch -- \
  --accept-change "Approved unserved-capacity extension and 7b62fba runtime; caps and research settings unchanged" \
  coordinate "$pilot/schedule.json"
```

Do not clear a parent or pair-4 marker: none belongs to this incident. Do not unlink locks or manually
edit running/stopped/censored status. Canonical launch records the engine/group change, skips terminal
pairs 1-4 and resumes pair 5's peers; pair 6 follows normally. Shared provider cooldowns remain in force.
Check controller/child progress after 60 seconds. Never operate old-group and new-group controllers
concurrently. Any future dispatch from a terminal arm must first join the current group/runtime.

## Future mixed recurrence, same runtime

Diagnose and drain the actual campaign root using its canonical `stop`, then wait for ownership and
active calls to clear. Choose the policy from the retained evidence, never just from elapsed time:

| Observed evidence | Extension policy |
| --- | --- |
| Strict no-model-activity capacity sequence | unserved-capacity-extension-v1 |
| Capacity failure after observed service | served-capacity-extension-v1 |

Set `arm_root`, `new_call`, `policy`, `input_estimate`, `output_estimate` and `basis` from the new incident.
Use fresh artifact paths. Do not reuse an estimate or approval automatically.

```sh
future_proposal=$pilot/operator/capacity-$new_call-proposal.json
"$py" -m pathfinder.cli --root "$arm_root" budget-reservation propose \
  --policy "$policy" --call-id "$new_call" \
  --input-tokens "$input_estimate" --output-tokens "$output_estimate" \
  --rationale "$basis" --out "$future_proposal"
```

Present the new digest/uncertainty to the user and record a separate approval. The manifest command
above works for either extension and preserves the full prior chain. Prepare a fresh snapshot of only
the then-pending arms. If pairs 5-6 remain, use `--pairs 5 6`; if only pair 6 remains:

```sh
"$py" "$packet/repin.py" snapshot --pilot "$pilot" \
  --proposal "$future_proposal" --pairs 6 \
  --out "$pilot/operator/capacity-$new_call-migration.json"
```

Apply that snapshot with the new approved manifest, validate reports, clear only the returned diagnosed
arm stops, and launch canonically with an explicit change reason. Selected arms must share the proposal's
current parent pin. The helper supports either policy and both pending-arm selections, and refuses
changed stop/event evidence. Other failure classes or unexplained markers require diagnosis first.

## Verification

188 tests passed on working and frozen runtime. Tests alternate served/unserved failures across roots
and inherited version-5/6 chains, require independent approval every time, reject reused approvals and
modified history, and verify that only pending-arm configs change. The helper was tested for pairs 5-6
and pair 6 alone, including rejection before writes when stop-history event bytes change.

The frozen real-pilot copy used canonical coordinator/runner/research state transitions with model
execution stubbed. It cleared exactly the two diagnosed markers, called pair-5 peer index 0 at timeout
3,630, then consolidation/verification, and then pair 6. Configs changed only in the group pin; all
provider receipts, prior Ada files and terminal thread files stayed exact. Synthetic prior approvals,
root rebinding and a rebased budget-marker path were confined to the copy. All 38,766 checked live files
were unchanged. Tests prove mechanics and preservation, not scientific outcomes or actual unknown usage.

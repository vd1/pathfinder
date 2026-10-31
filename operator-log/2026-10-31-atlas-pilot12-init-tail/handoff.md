# Pilot 12 pair 5 init-tail recovery

## Frozen runtime and scope

Commit `74aac57370790291ffba57bf25f0d0cfb6e685e4`.
Runtime `/private/tmp/pathfinder-74aac57`; archive `/private/tmp/pathfinder-74aac57.tar.gz`.
Archive SHA256 `eee677ee3d4439c550c9416519fe37c6b74d83f961a26e1b513e0be9473bb40d`.
No live deployment, state, receipt, ledger, stop, approval or config was changed by the maintainer.

The stream has 353 physical lines: the successful result is line 352 and the only later event is
same-session init at line 353. The earlier report's line numbers were off by one. Completed result:
64 uncached input + 120,892 cache write + 2,288,566 cache read = 2,409,522 whole input; output 57,199.
Journal SHA256 is `61b1c5402714019227df64f7b92e4251c7aec147281f9716e7b54ad9066d2749`.

No later assistant activity was observed, but init does not establish that no provider request was in
flight. The engine does not certify zero tail usage or promote the first result to whole-call totals.
The reader now stops the Claude process group immediately on receiving its result, before journal fsync
and polling delays. Already-buffered events remain journaled and uncertainty remains visible. This narrows
the race; it does not guarantee zero provider-side activity after a result or silently ignore later events.
Normal process-enumeration permission is required for descendant cleanup. Wrappers/models remain unchanged.

## Readiness correction and remaining allowance

The live state is round 6, stage peers, stopped. Marker 52 is retained, but says seen 50 while Ada's
substantive finding 51 precedes it. The ordinary ledger readiness check therefore returns false. Immediate
consolidation is not the supported next stage, contrary to the initial diagnosis.

All Ada files, findings and marker 52 stay intact. The next peer turn is the unspent second turn of this
round, not a replay of the completed call. The receipt history after verifier 54e465b4 contains exactly
one served peer call, 662.6 seconds, followed by an admission refusal that never called the provider.
The original allowance was two peer turns / 3,600 seconds. The tested migration limits pair 5 to the
remainder: one peer turn / 2,937.4 seconds. The usual transport startup grace remains 30 seconds; the
actual peer request timeout in the copy was bounded by 2,967 seconds. This prevents the in-memory peer
loop from receiving a fresh full allowance on resume. No grant, round cap, prompt or scientific verdict
is changed. Pair 6 keeps its original allowances.

After that pending peer turn, ordinary consolidation and verification run under the existing round-6
limits. The verifier assesses the science; no acceptance or readiness is supplied by the maintainer.

## Explicit second accounting exception

New canonical policy: claude-init-tail-reservation-v1. It requires exactly one successful result with
full counters, followed by exactly one same-session init and no later events, with exit -9 and missing
whole-call counters. Original receipt and full journal hashes are checked on proposal and admission.

The concrete proposal.json has canonical digest:
`f30c60ae0dd42772f3519cdba2c61797f5b95c230c7aecfb90d5953108277912`.

New whole-call reservation: 4,909,522 input / 82,199 output. This is the known result plus an uncertain
2,500,000 input / 25,000 output tail allowance. The tail allowance is an explicit heuristic, not measured
usage or a proven upper bound. Its size follows the earlier recovery's uncertainty allowance, but the
previous approval does not authorise this new exception. Obtain fresh approval for this exact proposal,
including continued uncertified actual aggregate cap compliance. The approval template is false/inert.

The new version 3 group inherits the complete existing reservation and approval unchanged, then adds
this separately approved record. It binds the existing version 2 manifest hash and unchanged members/caps.
It rejects an altered prefix, duplicate call, missing approval, or another extension from version 3.
Original manifests and evidence must remain available. Older engines do not understand version 3.
No measured counters or historical outcomes are rewritten, and no call is counted twice.

The copy reports admission totals 127,635,546 input / 3,166,000 output against unchanged 1 billion /
14 million caps. Both original unknown calls remain listed as reserved; actual_total_certified is false.
The group refusal clears only after validating both approvals and all their retained evidence.

## Operator commands

Keep the current frozen runtime and all prior manifests. Confirm parent/group ownership is idle and no
active calls remain before installation. Use the existing Atlas launch environment and wrappers.

```sh
repo=/Users/v/Code_2026/qap-atlas
pilot=$repo/pilots/atlas-pilot-12
packet=/Users/v/Code_2026/pathfinder/operator-log/2026-10-31-atlas-pilot12-init-tail
py=/Users/v/.local/share/uv/python/cpython-3.13.0-macos-aarch64-none/bin/python3.13
export PYTHONPATH=/private/tmp/pathfinder-74aac57
"$py" -m pathfinder.cli verify-frozen "$PYTHONPATH" --repo /Users/v/Code_2026/pathfinder
"$py" -m pathfinder.cli --root "$pilot/runs/pair-5" budget-reservation report
```

Inspect proposal.json and record real approval in a new
`$pilot/operator/init-tail-approval.json`. Use approval-template.json's exact schema and proposal digest,
setting its three boolean fields true only after approval; fill approved_by, approved_at and authority
with the actual decision. No authority is inferred from the previous exception or this recovery request.

After fresh approval, review the configuration deltas above and run:

```sh
new_manifest=$pilot/operator/budget-group-init-tail-reserved.json
"$py" -m pathfinder.cli budget-reservation manifest \
  --proposal "$packet/proposal.json" \
  --approval "$pilot/operator/init-tail-approval.json" \
  --out "$new_manifest"
"$py" "$packet/repin.py" --pilot "$pilot" --manifest "$new_manifest"
for n in 5 6; do
  "$py" -m pathfinder.cli --root "$pilot/runs/pair-$n" budget-reservation report
done
```

The tested installer takes parent/member ownership and both group locks, rejects unresolved active calls
and unrelated stops, and saves configs exclusively. It changes only the group manifest/hash for pairs 5/6,
plus pair 5's remaining peer allowance as described above. It verifies round/stage, old allowance and
served-call history before this reduction. It does not edit thread state or ledgers, clear stops or call
models. If backups already exist or installation is interrupted, inspect the partial migration; do not
remove backups or retry blindly. The original manifest is never overwritten.

Completed pairs 1-4 retain their configuration as receipt-only group members; any future dispatch from
them must first join the new manifest/runtime. Never run old and new group controllers concurrently or
unlink locks. Keep the original approval and raw evidence available for validation of the inherited record.

Both reports must have refusal null, both approved reservations and unchanged caps. Confirm original
peer files/marker, receipt bytes, round 6/peers and the reduced remaining allowance. Then clear only the
reported child budget stops and resume the unchanged schedule:

```sh
for n in 5 6; do
  "$py" -m pathfinder.cli --root "$pilot/runs/pair-$n" stop --clear
done
export PATHFINDER_CODEX="$py $repo/scripts/atlas_codex.py"
export PATHFINDER_CLAUDE="$py $repo/scripts/atlas_claude.py"
export ATLAS_CLI_STDERR_DIR=$pilot/operator/cli-stderr
```

Retain the original zsh provider-variable isolation:

```zsh
for v in ${(k)parameters[(I)CLAUDE_CODE_*]} ${(k)parameters[(I)ANTHROPIC_*]}; do unset $v; done
cd "$repo"
"$py" -m pathfinder.cli --root "$pilot" launch -- \
  --accept-change "Approved init-tail reservation and 74aac57 boundary fix; carry only pair 5 remaining peer allowance" \
  coordinate "$pilot/schedule.json"
```

Confirm controller/log progress after 60 seconds. Expected first call: pair 5's remaining peer turn,
then consolidation/verification, then pair 6. Do not hand-edit the stage to consolidate or repair marker 52.
Future unknown usage still blocks unless separately supported and approved.

## Proof and limitations

163 tests passed, then passed again against the exact freeze, including buffered init retention, known
versus unknown usage, delayed follow-up prevention, detached process cleanup, inherited approval/cap/
receipt/journal tamper rejection and legacy reservation compatibility.

The actual-data copy ran the canonical coordinator, runner, provenance, reservation checks and research
state machine with only model responses stubbed. Original-root proposal preparation was read-only.
Copied group paths and old approval were rebuilt under explicitly synthetic fixture authority; this did
not alter the real approval. The copied version 2 record remains exactly the first version 3 record.

The copy first exposed the stale readiness marker. With only the original remaining peer allowance,
it called pair 5 peer/consolidate/verify, then pair 6 peer/consolidate/verify. It preserved the original
ledger prefix including marker 52, all Ada files, prior completed threads and all receipts. All 7,929
live original files were unchanged. No live model calls or deployment writes occurred. See copy-result.json.
Fixture scientific verdicts are not live judgements or approval to bypass review.

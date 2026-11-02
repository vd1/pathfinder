# Pilot 15 capacity refusal without observed model activity

## Frozen runtime

Commit `90beeb11d3dfe76e330f2f27dfb4a82228e11db3`, derived from runtime 74aac57.
Frozen path `/private/tmp/pathfinder-90beeb1`; archive `/private/tmp/pathfinder-90beeb1.tar.gz`.
Archive SHA256 `85421592c840329e3d63a616b1bb520bf2e3fbeed6ea2adfb26f8a37e818d0a4`.
Runtime changes are confined to the reservation policy, its evidence validator and CLI policy choice.
No prompts, models, retry rules, budgets, research behaviour or lifecycle rules change.
No live Atlas writes, model calls or recovery were performed by the maintainer.

## Diagnosis and policy

Call 12cb403b779c482db558ee8a5e78ec1c in pair 4 has an exact retained sequence: thread.started;
item.completed/error with the known skip_host_skill_discovery local warning; turn.started;
error capacity; turn.failed capacity. No model-produced item or usage appears.
The raw journal is 614 bytes, SHA256
`fea8631fa288543efd3a641746f0597ca4e131f263a96f37ec3d6bd9131d91aa`.

New policy unserved-capacity-reservation-v1 accepts only this bounded sequence, with optional known
CLI warning items before turn.started. It verifies the full journal hash/size, raw receipt events,
terminal event, backend, error, failure class and missing counters. Agent messages, reasoning, command
items, any usage, unknown events or unrecognised warning text are refused. The old served policy is
unchanged and correctly refuses this stream.

The policy name means no observed model service. It does not certify provider billing as zero.
The receipt remains failed with unknown counters; explicit approval of accounting uncertainty is still
required. Only this policy permits a zero reservation. Other policies retain their positive minimum.
Proposal preparation is inert. The existing version 2 immutable manifest and approval flow is retained;
no cap changes or automatic exceptions for later failures are introduced.

## Concrete proposal

Prepared proposal.json reserves 100,000 input and 1,000 output tokens as an explicit small uncertainty
allowance, not measured usage or a proven upper bound. Its canonical digest is
`9893181be3e7e0fe78cd12de8b28a8ee26ddf7826ded6365a2033aab4c126fe6`.

The operator may approve that proposal or prepare a zero/zero proposal as shown below. Approval must
bind the exact chosen proposal and acknowledge that actual usage and aggregate cap compliance remain
uncertified. approval-template.json is false/inert; no approval is inferred from this implementation request.

With the supplied estimate, the copy reports 76,900,995 input / 971,727 output against unchanged caps
of 1 billion / 14 million. The failure remains counted once, unknown/reserved, with actual_total_certified
false. A zero reservation likewise preserves those uncertainty labels and the counted attempt.

## Exact operator commands

Preserve the old freeze, original group manifest, configs, failed receipt and transport journal. Confirm
parent and all group members are idle, with no unresolved active calls. Use the existing Atlas environment.

```sh
repo=/Users/v/Code_2026/qap-atlas
pilot=$repo/pilots/atlas-pilot-15
packet=/Users/v/Code_2026/pathfinder/operator-log/2026-11-02-atlas-pilot15-unserved
py=/Users/v/.local/share/uv/python/cpython-3.13.0-macos-aarch64-none/bin/python3.13
export PYTHONPATH=/private/tmp/pathfinder-90beeb1
"$py" -m pathfinder.cli verify-frozen "$PYTHONPATH" --repo /Users/v/Code_2026/pathfinder
"$py" -m pathfinder.cli --root "$pilot/runs/pair-4" budget-reservation report
proposal_file=$packet/proposal.json
```

If the operator chooses zero instead, prepare this separate inert proposal and use its returned digest:

```sh
proposal_file=$pilot/operator/unserved-zero-proposal.json
"$py" -m pathfinder.cli --root "$pilot/runs/pair-4" budget-reservation propose \
  --policy unserved-capacity-reservation-v1 \
  --call-id 12cb403b779c482db558ee8a5e78ec1c \
  --input-tokens 0 --output-tokens 0 \
  --rationale "Explicit zero reservation for retained no-observed-service capacity stream; actual usage unknown and aggregate cap compliance uncertified" \
  --out "$proposal_file"
```

Record real approval in a new `$pilot/operator/unserved-capacity-approval.json`. Use the template's exact
schema, the chosen proposal_sha256, true approval/uncertainty booleans only after approval, and actual
approved_by, approved_at and authority values. The engine validates the declaration, not human identity.

After approval, with ownership idle:

```sh
new_manifest=$pilot/operator/budget-group-unserved-reserved.json
"$py" -m pathfinder.cli budget-reservation manifest \
  --proposal "$proposal_file" \
  --approval "$pilot/operator/unserved-capacity-approval.json" \
  --out "$new_manifest"
"$py" "$packet/repin.py" --pilot "$pilot" --manifest "$new_manifest"
for n in 4 5 6; do
  "$py" -m pathfinder.cli --root "$pilot/runs/pair-$n" budget-reservation report
done
```

The tested configuration installer validates the policy, exact call and approval/evidence. It accepts
only the supplied 100,000/1,000 estimate or zero/zero, obtains parent/member ownership and both group
locks, rejects active calls and unexpected stops, saves configs exclusively, and changes only the group
manifest/hash in pairs 4-6. It does not edit thread state, allowances, prompts or scientific material.
The original manifest remains unchanged. Inspect an interrupted installation or existing backups before
retrying; do not delete evidence or unlink locks. Never dispatch old-group and new-group calls concurrently.

Pairs 1-3 remain completed receipt-only members with old configs. Any future dispatch from them must
first join the new manifest/runtime. Old engines cannot validate the new policy.

All reports must show refusal null, the exact approved amount, unchanged caps, and the original call as
unknown/reserved. Confirm pair 4 still has round 1/stage verify, its original note and consolidation,
and unchanged receipts. Clear only the diagnosed child budget stops:

```sh
for n in 4 5 6; do
  "$py" -m pathfinder.cli --root "$pilot/runs/pair-$n" stop --clear
done
export PATHFINDER_CODEX="$py $repo/scripts/atlas_codex.py"
export ATLAS_CLI_STDERR_DIR=$pilot/operator/cli-stderr
cd "$repo"
"$py" -m pathfinder.cli --root "$pilot" launch -- \
  --accept-change "Approved Pilot 15 unserved-capacity reservation and 90beeb1 policy; research and caps unchanged" \
  coordinate "$pilot/schedule.json"
```

Keep the existing all-Codex route settings: Astra peer/consolidate and Sol verifier, without provider
substitution. The coordinator skips completed research, retries only pair 4 verification, then runs
pairs 5-6 normally. No reopen, new grant, peer replay, manual state edit or allowance change is involved.
Confirm process/log progress after 60 seconds. Another unknown call remains blocking, not automatically free.

## Verification

189 regression tests passed on the working tree and again against the exact freeze. Coverage includes
zero and positive approval, journal/receipt/manifest/proposal tampering, unknown-warning/model-activity
rejection, strict cap/legacy policies and CLI approval refusal. Existing lifecycle regressions also passed.

The actual-data copy used synthetic approval only in the copy and ran canonical migration, stop commands,
coordinator, runner, provenance and research; only model execution was stubbed. Pair 4 called verify only;
pairs 5-6 called peer/consolidate/verify. The prior note, research files, consolidation, completed sibling
threads and receipt bytes were preserved, with the ledger retained as a prefix. All 37,301 live original
files remained unchanged. The copied group report cleared admission without claiming certified actual usage.
See copy-result.json and tests.json. Fixture verdicts are not real scientific judgements.

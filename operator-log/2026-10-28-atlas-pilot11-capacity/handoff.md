# Atlas Pilot 11 capacity recovery

## Runtime and diagnosis

Keep frozen `f705a1e1523734d98d7858e34a7ac5f26e93cc8e` at `/private/tmp/pathfinder-f705a1e`.
No runtime patch or upgrade is needed. Its manifest was reverified against the committed runtime.
The existing archive SHA256 is `0fcc808b46ce205a51ec1a7eca257053fc811e3f3c9f8fb254a40a10986a3ce7`.

The failed Codex call already records class rate, scope call, retry true. Its retry_scheduled event
at 17:58:01 UTC records a 42.38-second delay. Admission then correctly refused the retry because the
partially served call supplied no usage. There is no turn.completed or recoverable final total.
The later refusals in pairs 5 and 6 made no provider calls and need no token reservation.
Changing models or weakening strict accounting is unnecessary.

## Concrete proposal requiring approval

`proposal.json` is inert and bound to the original receipt line, retained raw events, original group
manifest, campaign roots, and unchanged caps. Its canonical digest is
`cde1f4231b2426409abc854cddf8e1b642b3965399aaed47e8e753bf25d7e24e`.

Proposed reservation: 2,500,000 input and 25,000 output tokens. This is a heuristic rounded above twice
the largest totals from the 27 completed Pilot 11 verifier calls: 1,212,395 input and 11,374 output.
It is not measured usage or a proven upper bound. Actual aggregate cap compliance remains uncertified.
No approval is inferred from the request for recovery. Obtain explicit operator authority for this exact
proposal and uncertainty before installation. The supplied approval-template.json has false booleans
and empty authority fields, so the engine refuses it as approval.

The copy's admission balance after this reservation was 92,292,695 input and 2,572,736 output against
unchanged caps of 1,000,000,000 and 14,000,000. The report still lists the call as unknown, now reserved,
and actual_total_certified remains false. Original receipts are never rewritten.

## Operator commands

Use the existing launch environment. Do not execute the original launch.sh again: it intentionally
rejects an already launched pilot. Preserve the original schedule, settings, prompts and scientific files.

```sh
repo=/Users/v/Code_2026/qap-atlas
pilot=$repo/pilots/atlas-pilot-11
packet=/Users/v/Code_2026/pathfinder/operator-log/2026-10-28-atlas-pilot11-capacity
py=/Users/v/.local/share/uv/python/cpython-3.13.0-macos-aarch64-none/bin/python3.13
export PYTHONPATH=/private/tmp/pathfinder-f705a1e
"$py" -m pathfinder.cli verify-frozen "$PYTHONPATH" --repo /Users/v/Code_2026/pathfinder
"$py" -m pathfinder.cli --root "$pilot/runs/pair-5" budget-reservation report
```

Review proposal.json and its digest. Record actual approval in a new file:
`$pilot/operator/capacity-reservation-approval.json`. Use the template's exact fields and proposal digest;
set the three boolean fields true only after approval and fill approved_by, approved_at and authority
with the real decision. Do not edit the proposal. If the operator chooses different amounts, prepare a
new proposal with canonical budget-reservation propose and obtain approval for its new digest; this
specific repinning helper intentionally accepts only the amounts above.

After real approval, with the parent and every group member idle and no active calls:

```sh
new_manifest=$pilot/operator/budget-group-capacity-reserved.json
"$py" -m pathfinder.cli budget-reservation manifest \
  --proposal "$packet/proposal.json" \
  --approval "$pilot/operator/capacity-reservation-approval.json" \
  --out "$new_manifest"
"$py" "$packet/repin.py" --pilot "$pilot" --manifest "$new_manifest"
"$py" -m pathfinder.cli --root "$pilot/runs/pair-5" budget-reservation report
"$py" -m pathfinder.cli --root "$pilot/runs/pair-6" budget-reservation report
```

This is the existing supported manifest migration, with a tested configuration-only installer.
The helper validates approval and evidence, acquires parent/member ownership and both group locks,
rejects active-call evidence and unexpected stops, saves original configs exclusively, and changes only
the budget_group manifest/hash fields in pairs 5 and 6. It does not edit thread state, clear stops or call
models. Completed pairs retain their old config as receipt-only members; any future dispatch from them
must first join the new group. Never run old-group and new-group calls concurrently or unlink locks.
If installation is interrupted or a backup already exists, inspect the partial migration; do not blindly
rerun or delete backups. The helper is offline-tested operator tooling, not a new runtime command.

Before continuing, both reports must have refusal null, the exact reservation, and unchanged caps.
Recheck pair 5 stage verify/round 1 and pair 6 stage peers/round 1, original notes/receipts and stop reasons.
The helper already rejects unrelated stops. Clear only the resolved child budget stops:

```sh
"$py" -m pathfinder.cli --root "$pilot/runs/pair-5" stop --clear
"$py" -m pathfinder.cli --root "$pilot/runs/pair-6" stop --clear
export PATHFINDER_CODEX="$py $repo/scripts/atlas_codex.py"
export PATHFINDER_CLAUDE="$py $repo/scripts/atlas_claude.py"
export ATLAS_CLI_STDERR_DIR=$pilot/operator/cli-stderr
```

As in the original zsh launch script, clear inherited provider variables before invoking its wrappers:

```zsh
for v in ${(k)parameters[(I)CLAUDE_CODE_*]} ${(k)parameters[(I)ANTHROPIC_*]}; do unset $v; done
cd "$repo"
"$py" -m pathfinder.cli --root "$pilot" launch -- \
  --accept-change "Approved Pilot 11 evidence-bound unknown-usage reservation; unchanged caps and research" \
  coordinate "$pilot/schedule.json"
```

The coordinator retains its schedule, skips completed research, repeats only pair 5 verification, then
starts pair 6 normally. No reopen, new research grant, state reset or model substitution is involved.
Confirm controller and log progress after 60 seconds. A fresh unknown-usage call remains blocking:
this policy admits exactly the approved exception, not future unknown calls automatically.

## Offline validation

The actual-data copy uses the exact frozen engine, original failed receipt and all group receipts.
Only copied paths and copied stop-marker root text were rebased. Synthetic approval was confined to
that copy. The supplied repin helper, canonical stop commands, coordinator, runner, provenance and
research state machine ran there, with only model execution replaced by fixtures.

Observed calls: pair 5 verify; pair 6 peer, consolidate, verify. All earlier completed threads and
receipt bytes remained intact. Pair 5's existing note was unchanged. All 3,522 live source files were
unchanged across the test. No real model calls or live mutations occurred. See copy-result.json.
The fixtures prove continuation mechanics, not scientific outcomes.

Regression coverage includes reservation authority/tamper/cap/unknown-call guards, provider transient
classification, shared budget accounting and coordinator resume. Results are recorded in tests.json.

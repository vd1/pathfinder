# Pilot 12 completed Claude turn and interrupted background follow-up

## Frozen repair

Runtime commit `e8025943a81026400cedc727f89caa964d6a2f6e`.
Frozen runtime `/private/tmp/pathfinder-e802594`; archive `/private/tmp/pathfinder-e802594.tar.gz`.
Archive SHA is recorded in tests.json. Verify the runtime against the commit before use.
No live deployment, receipt, note, ledger, stop, configuration or scientific state was changed.

The original 30-second Claude exit grace let a background-task notification start another turn.
The first result reported complete usage, but the interrupted follow-up reported only a partial assistant
message. Treating the first result as the entire call would hide that additional work.

The engine now ends a still-running Claude process group promptly after its result, with no 30-second
grace. It stops the group before discovering and terminating descendants, preventing ordinary child
creation during cleanup. Process enumeration must be available, as in the normal Atlas launch environment.
A queued follow-up may still race with cleanup; all events remain journaled and trailing activity keeps
accounting incomplete. Codex grace is unchanged. No wrapper change, model substitution or background-task
CLI setting is required. Required work must finish before the agent returns its result; abandoned work
is not promised extra execution time after that boundary.

## Original work is preserved

The failed accounting did not invalidate Ada's peer work. The original state already says round 5,
stage consolidate. Ready marker 54 is preserved verbatim, with seen 53. The supported continuation runs
consolidation and verification, without replaying Ada's peer call or altering the round/repair allowance.
The ordinary verifier assesses the retained work. This handoff does not preassign its scientific verdict.

## Evidence and accounting decision

Call `6e55ceedf4814fd4948d57d68841a19c` has exactly one successful result, at journal index 403, followed
by same-session background notification, init and partial assistant usage. Its full 884,769-byte journal
is bound by SHA256 `e6df6ca4cbcd4631c0029e10ef1785928ae4ad1185e1423c49db149a31fa2d4c`.

The completed turn reports 88 uncached input, 151,824 cache write, 4,730,994 cache read and 78,455 output:
4,882,906 whole input and 78,455 output. The follow-up message reports 160,995 whole input and 7 output,
but is not a complete turn total. Neither assistant samples nor absent counters are promoted to final usage.

The new canonical budget-reservation policy claude-post-result-reservation-v1 binds the entire original
receipt and raw journal, completed-turn totals and partial follow-up samples. It requires explicit approval
of an uncertain whole-call reservation under the existing caps. recover-usage remains inappropriate here:
there are no exact final whole-call totals to recover. No existing receipt or historical outcome is rewritten.

Concrete proposal.json digest:
`1fc7dacca5a768624421f92ddc5ea84b6121933853185c5d65e67a5e2e21cebd`.

Proposed whole-call reservation: 7,382,906 input and 103,455 output. This includes the known completed turn
plus an uncertain follow-up estimate of 2,500,000 input and 25,000 output. That estimate exceeds the observed
partial message, but it is not measured usage or a proven bound. Actual aggregate cap compliance remains
uncertified. The whole reservation is charged once; its known component is not charged again elsewhere.

This request authorises preparation of recovery, not acceptance of an unknown-usage budget exception.
Obtain explicit operator approval for this exact proposal and uncertainty. approval-template.json is inert,
with false booleans and blank authority fields. Do not infer approval from a request to resume.

The copied admission balance was 23,105,476 input / 617,959 output against unchanged caps of 1 billion /
14 million. Report refusal became null; the original call stayed unknown/reserved and actual_total_certified
stayed false. Other unknown calls, altered evidence, missing approval and exhausted caps still block.

## Exact operator commands

Keep the old runtime and original evidence. All campaigns and the parent must be idle with no active calls.
Use the existing Atlas subscription environment. Do not run the original first-launch-only launch.sh again.

```sh
repo=/Users/v/Code_2026/qap-atlas
pilot=$repo/pilots/atlas-pilot-12
packet=/Users/v/Code_2026/pathfinder/operator-log/2026-10-29-atlas-pilot12-background
py=/Users/v/.local/share/uv/python/cpython-3.13.0-macos-aarch64-none/bin/python3.13
export PYTHONPATH=/private/tmp/pathfinder-e802594
"$py" -m pathfinder.cli verify-frozen "$PYTHONPATH" --repo /Users/v/Code_2026/pathfinder
"$py" -m pathfinder.cli --root "$pilot/runs/pair-1" budget-reservation report
```

Review proposal.json and record real approval in a new
`$pilot/operator/background-usage-approval.json`, using the template's exact schema and digest. Set its
three booleans true only after approval; fill approved_by, approved_at and authority with the real decision.
The engine validates the bound declaration but cannot authenticate human authority from JSON.

After approval:

```sh
new_manifest=$pilot/operator/budget-group-background-reserved.json
"$py" -m pathfinder.cli budget-reservation manifest \
  --proposal "$packet/proposal.json" \
  --approval "$pilot/operator/background-usage-approval.json" \
  --out "$new_manifest"
"$py" "$packet/repin.py" --pilot "$pilot" --manifest "$new_manifest"
for n in 1 2 3 4 5 6; do
  "$py" -m pathfinder.cli --root "$pilot/runs/pair-$n" budget-reservation report
done
```

The offline-tested configuration installer validates evidence/approval, takes parent and all member
ownership plus both group locks, refuses active calls or unexpected stops, saves old configs exclusively,
and changes only each budget_group manifest/hash. It does not edit state, clear stops or make calls.
It accepts only this exact call and proposed amounts. Do not run old and new group controllers together,
unlink locks, overwrite the original manifest, or delete backups to retry an interrupted installation.
Inspect any partial installation before proceeding. All future readers of this new policy must use the
new runtime; f705a1e does not understand the new reservation.

All reports must have refusal null, the exact reservation and unchanged caps. Recheck original receipts,
Ada files and ready marker, and pair 1 round 5/consolidate. Only the diagnosed child budget stops may clear:

```sh
for n in 1 2 3 4 5 6; do
  "$py" -m pathfinder.cli --root "$pilot/runs/pair-$n" stop --clear
done
export PATHFINDER_CODEX="$py $repo/scripts/atlas_codex.py"
export PATHFINDER_CLAUDE="$py $repo/scripts/atlas_claude.py"
export ATLAS_CLI_STDERR_DIR=$pilot/operator/cli-stderr
```

In the same zsh launch environment, retain the original provider-variable isolation:

```zsh
for v in ${(k)parameters[(I)CLAUDE_CODE_*]} ${(k)parameters[(I)ANTHROPIC_*]}; do unset $v; done
cd "$repo"
"$py" -m pathfinder.cli --root "$pilot" launch -- \
  --accept-change "Approved Pilot 12 background-usage reservation and e802594 lifecycle repair; unchanged research/caps" \
  coordinate "$pilot/schedule.json"
```

The existing coordinator resumes round-5 consolidation then verification, and proceeds to pairs 2-6.
No new grant, round reset, peer replay or manual state change is involved. Confirm process/log progress
after 60 seconds. A future interrupted call with unknown usage still requires separate diagnosis and
explicit authority; this proposal is not a general waiver or permission for unlimited retries.

## Verification

147 regression tests passed, repeated against the exact frozen runtime. Coverage includes lifecycle exit,
detached children, delayed post-result wake-up, completed-versus-partial usage, journal/receipt tampering,
proposal/approval mismatch, reservation floor, unchanged caps, legacy recovery and provider behaviour.
The first restricted test run could not enumerate processes; rerunning with process enumeration permitted
passed detached-child cleanup. No provider calls were made.

The actual-data copy ran canonical reservation validation, configuration migration, stop clearing,
coordinator, runner, provenance and research. Only model execution was replaced by fixtures; approval was
synthetic and confined to the copy. Pair 1 called only consolidate/verify; remaining pairs called
peer/consolidate/verify. The peer files and ledger prefix were unchanged, including ready marker 54.
All receipt bytes and all 293 live original files were preserved. See copy-result.json and tests.json.
Fixture verdicts prove continuation mechanics only, not scientific acceptance.

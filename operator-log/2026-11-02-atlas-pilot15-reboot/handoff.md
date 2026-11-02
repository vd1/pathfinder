# Pilot 15 reboot recovery

## Status

Maintainer runtime `7046a190cd4d2b1be26f21d22150fc52353917e8` is frozen at
`/Users/v/Code_2026/pathfinder/.frozen-runtimes/7046a19`.
The live pilot was read only. No model calls, reservation approval, migration or live recovery occurred.
The operator must obtain separate explicit approval for the proposed uncertain accounting before resume.

## Restored original runtime

The lost runtime was reconstructed from commit `90beeb11d3dfe76e330f2f27dfb4a82228e11db3` at
`/Users/v/Code_2026/pathfinder/.frozen-runtimes/90beeb1`; canonical verification passed.
The rebuilt archive SHA is `34a1fda04436aafa3c600d37aba44b8850b1371404d6494281db5c75ee2f0728`.
It is a new archive, not the lost tar whose recorded SHA was
`85421592c840329e3d63a616b1bb520bf2e3fbeed6ea2adfb26f8a37e818d0a4`.
The original archive was not found. Commit verification establishes the runtime files independently of
archive packaging. Both archives and manifests are listed in `runtimes.json` and stored durably beside
these runtime directories. Do not resume this orphan using the old runtime.

The recovery archive SHA is `a29843ad7908669bf0185c171ae0f354cd7ed786c0199c029dc5c0c67790505b`.
Its manifest SHA is `05e9339405f875836c129360200dfdc4453f59ae3c1caf53c420c7bbe17da928`.

## What happened and what is retained

The current kernel boot was 2026-11-02 10:57:11 UTC. Runner 54538 and child 65853 are dead.
Attempt `e7e55c64bf35432483adbf8803683cf3` started at 10:31:03.715 UTC. Its 312,790-byte Codex
journal has no terminal event or usage. Ada wrote round-5 material and findings, but no fresh ready marker.
There is no completed provider reply to replay or accept.

Original retirement removed active-call evidence without creating a receipt. That could remove the
unknown call from group accounting. The new `recover-orphan` archives the exact active-call record,
boot evidence, journal hash, stale runner/status/config/ledger metadata and appends a distinctly
host-origin interrupted receipt with unknown usage. It never manufactures provider usage or a scientific
result. Retirement now refuses an unreceipted orphan with a nonempty transport journal. Original journal,
peer files and ledger remain unchanged; the new host receipt is appended once and repeat application is
idempotent. A changed journal, active record or receipt refuses recovery/admission.

Ordinary resume keeps Ada's written files. It continues the unfinished peer phase with a new peer call,
not an exact replay and not consolidation of an assumed successful reply. The interrupted turn consumes
one peer call and a conservative 1,568 seconds of elapsed allowance up to reboot. The remaining allowance
is one call and 2,032 peer seconds, plus the normal 30-second transport grace. Original two-call/3,600-second
configuration and prompts remain unchanged. Later rounds use their normal allowances. Further restarts
of this recovered phase also carry subsequent receipts, so they do not reset its allowance.

Stale `runner.json`/`progress.json` are not ownership locks. The OS lock is released by reboot; canonical
owner acquisition checks for live model processes and reacquires it. Never unlink lock files or manually
rewrite running/stopped state. No actual stop marker exists in the parent or pairs 4-6 at this handoff.

## Inert proposal and approval boundary

`proposal.json` proposes 15,000,000 input and 150,000 output tokens under
`reboot-orphan-reservation-v1`. Its digest is
`3f087cc75aa4bfacaf8d4d9a24770e215f77bab0e7ef9593becb77230b71ef26`.
Among 19 completed peer calls, maxima were 7,018,735 input and 62,714 output tokens. Each proposed amount
exceeds twice the corresponding maximum, rounded upward. This historical comparison is a heuristic,
not a measured usage value or proven bound. Actual aggregate cap compliance remains uncertified.

The proposal binds the prospective host receipt, exact orphan snapshot and current approved version-2
group. It does not create a receipt or reserve tokens. The new version-4 manifest preserves the existing
unserved-capacity approval verbatim and adds only this separately approved exception. Caps are unchanged.
`approval-template.json` has false booleans and no authority. The engine checks declarations and exact
hashes; it does not authenticate the human signatory. Do not substitute a copied test approval.

## Operator commands

Use the existing Atlas environment, outside a sandbox that blocks kernel boot time, PID liveness or locks.
These commands assume the incident evidence and ownership remain unchanged. Reinspect if any binding
changes. The coordinator must remain idle throughout capture and migration.

```sh
repo=/Users/v/Code_2026/qap-atlas
pilot=$repo/pilots/atlas-pilot-15
packet=/Users/v/Code_2026/pathfinder/operator-log/2026-11-02-atlas-pilot15-reboot
py=/Users/v/.local/share/uv/python/cpython-3.13.0-macos-aarch64-none/bin/python3.13
export PYTHONPATH=/Users/v/Code_2026/pathfinder/.frozen-runtimes/7046a19
cd "$repo"
"$py" -m pathfinder.cli verify-frozen /Users/v/Code_2026/pathfinder/.frozen-runtimes/90beeb1 --repo /Users/v/Code_2026/pathfinder
"$py" -m pathfinder.cli verify-frozen "$PYTHONPATH" --repo /Users/v/Code_2026/pathfinder
"$py" -m pathfinder.cli --root "$pilot/runs/pair-4" recover-orphan e7e55c64bf35432483adbf8803683cf3
```

The preview must match snapshot SHA
`fecea952db14c73493559c065c8f4c4178cd07a89f870a9b7af29df720b8828e` in `orphan-preview.json`.
A preview acquires ownership/group locks but does not capture evidence or edit research state.

After real approval of the exact proposal and uncertainty, record actual signatory/time/authority in a
new `$pilot/operator/reboot-reservation-approval.json`, using the template schema and true booleans only
after approval. Then:

```sh
new_manifest=$pilot/operator/budget-group-reboot-reserved.json
"$py" -m pathfinder.cli budget-reservation manifest \
  --proposal "$packet/proposal.json" \
  --approval "$pilot/operator/reboot-reservation-approval.json" \
  --out "$new_manifest"
"$py" -m pathfinder.cli --root "$pilot/runs/pair-4" recover-orphan \
  e7e55c64bf35432483adbf8803683cf3 --apply \
  --expected-sha256 fecea952db14c73493559c065c8f4c4178cd07a89f870a9b7af29df720b8828e
"$py" "$packet/repin.py" --pilot "$pilot" --manifest "$new_manifest"
for n in 4 5 6; do
  "$py" -m pathfinder.cli --root "$pilot/runs/pair-$n" budget-reservation report
done
```

The installer holds parent/member ownership and old/new group locks, refuses active calls or unexpected
stop markers, saves original configs exclusively, and changes only the group manifest/hash in pairs 4-6.
It requires the captured host receipt and approved exception. It never edits thread state or research
settings. Reports must have refusal null, the approved uncertain amount, and uncertified actual totals.
The host receipt remains unknown, not measured. If installation is interrupted or backups already exist,
inspect rather than deleting evidence or blindly repeating it. Pairs 1-3 stay terminal receipt-only members
with unchanged configs; any future dispatch from them would need migration to the new group/runtime.

There is no stop to clear in this incident. If a new stop has appeared, diagnose it separately. Resume:

```sh
export PATHFINDER_CODEX="$py $repo/scripts/atlas_codex.py"
export ATLAS_CLI_STDERR_DIR=$pilot/operator/cli-stderr
"$py" -m pathfinder.cli --root "$pilot" launch -- \
  --accept-change "Approved reboot-orphan reservation and 7046a19 recovery; peer allowance carried, research settings and caps unchanged" \
  coordinate "$pilot/schedule.json"
```

Canonical provenance records the engine/group change. Check the detached controller and first child after
60 seconds. Expected next stage is pair-4 peer continuation, followed by consolidation/verification;
pairs 5-6 then follow the original schedule. Do not reopen or reset rounds, replay completed stages,
change routing, or run old/new group controllers concurrently.

## Verification and limits

170 relevant tests passed on the working runtime and again against the exact frozen runtime.
The frozen-copy proof uses real coordinator, owner,
provenance and research state transitions, with model execution replaced only by fixtures. Pair 4's first
request has timeout 2,062 seconds and call index 1. It then consolidates/verifies, and pairs 5-6 run.
The test checks original receipt prefixes, retained Ada round-5 bytes/ledger prefix, unchanged terminal
threads, and unchanged settings except the group pin. All 38,524 live files were hash-checked unchanged.
No test simulates actual scientific judgment or certifies unknown usage. Kernel boot-time access is
required for first capture; saved evidence is used after capture. Proposal/evidence validation is strict:
if the pilot changes before capture, generate and review new bindings rather than weakening guards.

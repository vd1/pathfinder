# Atlas Pilot 9 failed-result accounting recovery

## Release

Commit `f705a1e1523734d98d7858e34a7ac5f26e93cc8e`.
Frozen runtime `/private/tmp/pathfinder-f705a1e`.
Archive `/private/tmp/pathfinder-f705a1e.tar.gz`.
Archive SHA256 `0fcc808b46ce205a51ec1a7eca257053fc811e3f3c9f8fb254a40a10986a3ce7`.
Verification matches the committed runtime exactly. This release also includes the previously approved
new-consolidation preamble normalisation (1f15243); historical replies remain byte-stable.

No live Atlas deployment, budget manifest, receipt, grant, note or state was changed by the maintainer.

## Diagnosis and fix

Pilot 9 pair 3 call caed1dc5cd774d5b8009d54c42c5e480 ended with a structured Claude result whose is_error
was true and whose result said Request timed out. The engine correctly treated the answer as failed,
but incorrectly required answer success before accepting its final accounting totals. Its assistant
message usage was not the source of this recovery: the complete, retained final result is the source.

The final result reports uncached input 2, cache reads 5,024, cache writes 101,209 and output 298.
Under the existing whole-input convention this is 106,235 input and 298 output tokens. Reported cost
remains unchanged. These are CLI-reported totals, not an independently audited provider invoice.

For future calls, valid final Claude result totals are now accepted independently of answer success.
All input/output/cache counters must be explicit nonnegative integers. Partial message usage, missing
final results, invalid counters and truncated streams are not promoted to complete totals. Request timed
out is classified as a retryable call-scoped timeout. The existing policy retries a timeout at most once,
subject to configured waits, episode deadline, stop/provider guards, residual peer allowance and budget
admission. No retry bypasses unknown usage or increases budget limits.

A failed answer stays failed. Neither a failed result nor its reported usage becomes a scientific verdict.

## Historical correction

The canonical command recover-usage prepares an evidence-bound proposal and optionally installs a new
usage-corrections/CALL.json record. It never rewrites receipts.jsonl. The correction binds the original
receipt, its complete raw provider journal and terminal result, derives the counters deterministically,
and preserves the original receipt in the correction record. Budget/state readers validate this evidence
before applying the correction as an accounting view, then apply the existing cache-inclusive convention.
No receipt is duplicated or counted twice. Historical outcome, error and failure label remain unchanged.

Recovery requires idle campaign ownership, no unresolved active calls, and the shared group's call lock.
It refuses tampered evidence, stale proposals, already-accounted receipts or repeat corrections. It does
not clear any stop marker, change a grant, reclassify old state or make a model call. A damaged or missing
correction journal fails closed; preserve the correction and original transport evidence when archiving.

## Operator commands

Use the existing authorised Atlas launch environment and interpreter/provider wrappers. Keep the old
runtime and evidence. Wait for the campaign and its shared budget group to be idle before applying.

```sh
atlas_root=/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-9/runs/pair-3
atlas_py=/Users/v/.local/share/uv/python/cpython-3.13.0-macos-aarch64-none/bin/python3.13
atlas_call=caed1dc5cd774d5b8009d54c42c5e480
export PYTHONPATH=/private/tmp/pathfinder-f705a1e
"$atlas_py" -m pathfinder.cli verify-frozen "$PYTHONPATH" --repo /Users/v/Code_2026/pathfinder
"$atlas_py" -m pathfinder.cli --root "$atlas_root" recover-usage "$atlas_call" \
  --reason "Recover CLI final-result usage for the timed-out Pilot 9 repair"
```

Inspect and save that proposal. Confirm raw fields 2/298/5,024/101,209, the original receipt identity and
journal digest. Apply with its returned sha256; the same reason must be used exactly:

```sh
"$atlas_py" -m pathfinder.cli --root "$atlas_root" recover-usage "$atlas_call" \
  --reason "Recover CLI final-result usage for the timed-out Pilot 9 repair" \
  --apply --expected-sha256 PROPOSAL_SHA256
"$atlas_py" -m pathfinder.cli --root "$atlas_root" budget-reservation report
```

PROPOSAL_SHA256 is the inspected proposal hash, not a literal value to pass. Group reporting uses the
existing budget-reservation report command, but this repair creates no reservation and edits no manifest.
Confirm that refusal is null and this call is no longer unknown. Investigate any unrelated blocker.
Verify receipt bytes, note hash 80da30785cb193e0773ce97c51b7585af5efd0d7354be8d7d999b275c9d9844e,
verdicts and reopen grant 1 are unchanged. The grant must still be pending at consolidation with its
original REVISE brief; no new reopen or reopen-recover is needed.

Only after verifying the stop is the reported, now-resolved unknown-usage budget stop, clear that marker
and resume the same grant through the canonical research runner. Do not clear unrelated stops.

```sh
"$atlas_py" -m pathfinder.cli --root "$atlas_root" stop --clear
"$atlas_py" -m pathfinder.cli --root "$atlas_root" launch -- \
  --accept-change "Verified failed-result accounting recovery and engine upgrade to f705a1e; same repair grant" \
  research --research-only --pairs Q001-P002
```

Preflight migration should leave settings, prompts, sources and budget caps unchanged. The engine change
is recorded by normal provenance. The repaired consolidation is a fresh paid attempt under the original
grant and ordinary admission guards; the old failed call stays charged. A following verifier ends that
grant. Monitor the real receipt and outcome; the offline proof does not supply scientific approval.

## Tests and retained proof

126 regressions passed, including fake-CLI timeout/retry accounting, partial-stream rejection, immutable
correction, journal/receipt/proposal tampering, repeat refusal, busy-group refusal, provider errors,
transport, shared budgets and reservation compatibility. All 126 tests passed again against the frozen release.

The actual-data copy test restores the accounting view and clears the copied shared-budget refusal while
preserving the original failed receipt and all 118 original pair-3 files. The copied note, state and grant
are unchanged by correction. Ordinary research then consumes the same grant with only a fixture repair
and verifier; those are offline responses, not live scientific evaluations. Its verdict ends the grant.

Only the copied group manifest paths are rebased for offline testing; no live manifest is repinned.
copy-result.json carries the exact preserved-file bindings and frozen runtime path. No real model calls.

# Account evidence-repair continuation

Runtime commit: `d36ff0bd254fad2ee7b8f75351d882c60f483ffa`.
Frozen engine: `/private/tmp/pathfinder-review-d36ff0b`.
Archive: `/private/tmp/pathfinder-review-d36ff0b.tar.gz`.
SHA256: `e2d53888648920d0b5b36fa0c06300f6414a9bd924912f03983d8476ea104cf2`.

Use this engine for the independent batch-1 campaign only. Do not replace the
running batch-2 engine. Paper pool, ITERATE readiness, prior PCE recovery, imported
acceptance, presentation and dated release support are retained.

## What changed

`account-amend-review` grants one new review of the same fixed candidate after a
terminal failed review. It uses the existing amendment identity and preserves the
failed `review/` directory. The separate `review-grants/GRANT/` directory records
its parent hashes, candidate hash, owner reason, approved packet hash, custody
checks and maximum five role calls. An interrupted run reuses its recorded calls;
a terminal failed grant does not renew itself.

The explicit historical packet restores the scientific file mapping, paper texts,
source metadata and coverage limitations. Its paper texts must equal the previous
review inputs. The complete historical packet is archived privately; neither its
internal material nor earlier review verdicts enters the fresh reviewer contexts.
Operational style/check records are removed with a transformation log. Scientific
ledger projections must contain only findings, ideas, corrections or objections.

The claim extractor sees the manuscript and replacement text, without the original
amendment packet's hash/preservation assertions. Custody verification remains a host
check. The fresh fact-checker and critic receive complete evidence, no internal
files or prior reviews. Every role has an exact visibility manifest and prompt hash.
The engine refuses oversized contexts instead of shortening evidence. Branch
results retain their actual attribution and limitations; lack of a numbered ledger
reference is not treated as proof of non-adoption.

Original custody, the failed parent round and immutable evidence inputs are checked
again after review and before installation. All scientific claims must be supported,
both gates must pass, and the editor must explicitly accept. No scientific acceptance
is inferred from the successful transport repair.

## Julien Q024-P011 handoff

Run outside the maintainer checkout, for example from `/private/tmp`. Confirm the
Python import points inside the frozen engine and `verify-frozen` returns verified.

```bash
export PYTHONPATH=/private/tmp/pathfinder-review-d36ff0b
export UV_CACHE_DIR=/private/tmp/pathfinder-uv-cache
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -c 'import pathfinder; print(pathfinder.__file__)'
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -m pathfinder.cli verify-frozen /private/tmp/pathfinder-review-d36ff0b --repo /Users/v/Code_2026/pathfinder
repair_args=(
  --accept-change 'Install evidence-repair continuation for batch1 only'
  --root /Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-1/Q024-P011
  account-amend-review Q024-P011
  --id definition-20261019
  --grant evidence-transport-1
  --inputs /Users/v/Code_2026/pathfinder-julien-2/experiments/eva-top-ten-01-q024-p011/provenance/pce-recovery-09/inputs.json
  --inputs-sha256 60775a43e98ab77f8b0c9687e6b0de48a9e82dfe31d34b0baf3ec3580e982232
  --reason 'Vincent authorises evidence-transport repair and one fresh bounded OpenAI-only review of the unchanged definition candidate'
)
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -m pathfinder.cli "${repair_args[@]}"
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -m pathfinder.cli "${repair_args[@]}" --apply
```

Preparation makes no calls. Repeating the identical command with `--apply` runs or
resumes this same grant. The original `account-amend` command refuses to touch an
amendment with a selected repair grant. OpenAI-only preflight and no-refusal-fallback
rules apply, as do campaign ownership, stop and budget guards.

After acceptance, run `present Q024-P011 --edited` with the same campaign and
engine. Only after CLEARED may `release Q024-P011 --edited` proceed. The candidate
remains unchanged during review; any new substantive finding must be reported,
not silently fixed or bypassed. There is no paper commissioning or research rerun.

## Validation

The working-tree regression suite passed 50 tests. After the final post-review
custody recheck was added, all 11 evidence-repair tests passed again. The frozen
engine passed all 50 tests; its manifest was verified before and after testing.
Logs and XML are retained in
`/private/tmp/pathfinder-review-d36ff0b-tests.log` and the corresponding `.xml`.

The real campaign packet was exercised on an isolated copy with stub model calls
and a real LaTeX build. All 535 existing thread files, including the failed round,
were preserved byte-for-byte. The old result remained `review_required`. The new
review saw the restored scientific file mapping with no truncation. Historical
operational records were excluded; 25 scientific/support files remained visible.
The original candidate bytes were installed into a separate publication revision.
Synthetic regression coverage also completed fresh presentation and dated release.

No live model calls, deployment writes or batch-2 changes were made by the
maintainer. Stub acceptance validates software behaviour, not the scientific claims.

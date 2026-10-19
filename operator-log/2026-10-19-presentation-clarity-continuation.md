# Bounded account presentation continuation

Runtime: `5d0062e5fd378b90168dda88697493f3a55f188e`.
Frozen engine: `/private/tmp/pathfinder-clarity-5d0062e`.
Archive: `/private/tmp/pathfinder-clarity-5d0062e.tar.gz`.
SHA256: `2005cd245a857c6cc08d56314bf8413c77e8c935a31adfc98188d477b918e172`.

## Diagnosis and scope

The remaining clarity finding has support already present in the accepted evidence:
`emmy/calibration-note.md` identifies the `fep-surrogate-pipeline` README and its
discussion of gradient bias invisible to cycle closure. Its manuscript, archived
version and numerical results were not verified. No current repository inspection,
new research, scientific amendment or PCE rerun is needed to explain that caveat.

The new `account-present-continue` command permits one additional guarded correction
cycle from a presentation paused at its cycle limit. It requires only unclear
findings, an explicit grant identity and reason, and context bound to an exact
quotation in the accepted scientific evidence. Preparation makes no model calls.

The context for this case is retained in:
`/Users/v/Code_2026/pathfinder/operator-log/2026-10-19-q024-clarity-context.json`.
It contains the source, exact quote and current finding location. It does not contain
a replacement manuscript or instructions to override the correction guard.

The corrector and fresh checker receive that context. The corrector is instructed
to identify the repository by name and explain the historical comparison while
preserving limitations, without adding a URL, citation or numerical assertion.
Meaning findings continue to use the normal targeted check; scientific problems
still stop account publication. Existing OpenAI-only route checks apply.

## History and resumption

Each grant stores the complete prior presentation state, publication status and
hashes of the existing stage files under `presentation-continuations/ID/`. Existing
stage files are verified and retained; only the live state file advances. Stage
cleanup is disabled during this continuation so previous PDFs are also retained.
The original paused state remains in the immutable grant record.

The grant adds one cycle to the recorded count. Repeating a terminal grant returns
its result and never renews the allowance. Interrupted checking resumes the same
correction. A retained corrector reply is bound to its input digest and reused
instead of buying another correction. Generic presentation/restart commands refuse
while a continuation is pending. No acceptance records or scientific source bytes
are changed by the continuation.

## Q024-P011 operator commands

Deploy to batch 1 only; keep batch 2 unchanged. Run outside the maintainer checkout,
for example from `/private/tmp`. Verify the import and frozen manifest first.

```bash
export PYTHONPATH=/private/tmp/pathfinder-clarity-5d0062e
export UV_CACHE_DIR=/private/tmp/pathfinder-uv-cache
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -c 'import pathfinder; print(pathfinder.__file__)'
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -m pathfinder.cli verify-frozen /private/tmp/pathfinder-clarity-5d0062e --repo /Users/v/Code_2026/pathfinder
clarity_args=(
  --accept-change 'Install bounded account presentation continuation'
  --root /Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-1/Q024-P011
  account-present-continue Q024-P011
  --id readme-clarity-1
  --context /Users/v/Code_2026/pathfinder/operator-log/2026-10-19-q024-clarity-context.json
  --reason 'One additional guarded clarity correction using accepted evidence; preserve scientific caveats and prior history; OpenAI only'
)
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -m pathfinder.cli "${clarity_args[@]}"
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -m pathfinder.cli "${clarity_args[@]}" --apply
```

Resume with the identical `--apply` command if interrupted. Do not use `--restart`,
reset state or alter the cycle counter. Only after CLEARED, run canonical
`release Q024-P011 --edited` on the same campaign with this engine and a fresh
automatic timestamp. A remaining finding stays blocked and must be reported.

## Validation

The pre-final regression suite passed 32 tests. After adding retained-reply resume,
all six continuation tests passed, including interrupted checker and interrupted
host build. All 33 frozen-engine regression tests passed. The manifest was verified
before and after testing. Logs: `/private/tmp/pathfinder-clarity-5d0062e-tests.log`
and the matching XML file.

On an isolated copy of the paused live account, a simulated correction identified
the scientific comparison and named repository while retaining the unverified
manuscript/results limitation. It passed the real guard, then a simulated fresh
check, real LaTeX build and source/PDF release checks. The cycle count advanced from
two to three. All 22 old presentation artifacts and all 76 account-acceptance files
were preserved. The prior state is retained in the grant, and the live state advanced.

These tests do not claim a live checker has approved the correction. The maintainer
made no live model calls or deployment writes. The operator performs the authorised
continuation and reports its outcome; batch 2 remains unchanged.

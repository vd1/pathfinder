# Account presentation language repair

Runtime: `1676389476d17fe97fac430c6720f297dbe35868`.
Frozen engine: `/private/tmp/pathfinder-tail-1676389`.
Archive: `/private/tmp/pathfinder-tail-1676389.tar.gz`.
SHA256: `d7e48889778188b18a82444b3e6444ba834ca8ebe055458068179093ddc71681`.

## Diagnosis

The account presentation instruction disclosed the internal scientific status and
editorial boundary without explicitly forbidding that language in manuscript prose.
The editor inserted the status label and a workflow judgement into the caveat; the
fresh checker missed them. Release correctly refused them in both source and PDF.
The scientific limitation must remain. No release allowlist was changed.

An additional restart defect would have blocked the supported recovery: account
presentation archived its old pass, but did not forward the restart flag or invalidate
its CLEARED status. The presentation runner could return early without doing work.

## Correction

Account instructions now distinguish internal metadata from reader-facing scientific
limitations. The example wording preserves assumptions, evidence limitations and the
fact that editing provides no additional scientific validation. The generated-evidence
qualification and unresolved scientific limitations must remain.

Before account presentation can clear, a host check applies the release source-language
policy to its body, ignoring comments and preamble. Findings enter the existing guarded
correction loop, followed by a fresh check. A remaining leak prevents clearance even
when the model says clear. Source and PDF release checks remain unchanged.

An explicit account presentation restart archives the previous pass and publication
state, revokes its clearance, and actually starts a fresh pass. An interruption cannot
leave the previous clearance usable. Existing PCE acceptance, candidate source and
failed dated release artifacts are preserved.

## Supported operator commands

Deploy this frozen runtime to batch 1 only. Keep batch 2 unchanged. Run from outside
the maintainer checkout, such as `/private/tmp`, and verify the import and manifest.

```bash
export PYTHONPATH=/private/tmp/pathfinder-tail-1676389
export UV_CACHE_DIR=/private/tmp/pathfinder-uv-cache
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -c 'import pathfinder; print(pathfinder.__file__)'
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -m pathfinder.cli verify-frozen /private/tmp/pathfinder-tail-1676389 --repo /Users/v/Code_2026/pathfinder
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -m pathfinder.cli \
  --accept-change 'Apply account presentation language and archival restart fix' \
  --root /Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-1/Q024-P011 \
  present Q024-P011 --edited --restart
```

Use `--restart` once to open the new presentation attempt. If interrupted afterward,
resume with `present Q024-P011 --edited` without restarting it again. Only after fresh
CLEARED, run:

```bash
uv run --project /Users/v/Code_2026/pathfinder --offline --no-sync python -m pathfinder.cli \
  --root /Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-1/Q024-P011 \
  release Q024-P011 --edited
```

Use the normal automatic UTC timestamp for the corrected content. Do not reuse the
failed dated artifact's timestamp. No manual manuscript edits, research rerun or PCE
rerun is needed. Existing OpenAI-only route checks continue to apply.

## Validation

The regression suite passed 41 tests. All 41 tests also passed against the frozen
runtime, verified before and after testing, with logs at
`/private/tmp/pathfinder-tail-1676389-tests.log` and the matching
XML file.

On an isolated copy of the actual cleared Q024-P011 publication, simulated editor and
checker responses changed only the offending sentence to scientific language. The
new presentation cleared; the real LaTeX build and source/PDF release checks passed.
The test preserved all 76 account-acceptance files, archived all 14 old presentation
files unchanged, and preserved all four failed dated-release files. The generated
research caveat remained in the corrected text.

These are software and artifact tests, not a claim of live presentation completion.
No maintainer live calls or deployment writes occurred. The operator executes the
supported fresh presentation and release under the existing authorisation.

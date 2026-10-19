# Paper-pool engine handoff to Nobel

The paper-pool implementation is committed and its frozen runtime is tested.
Nobel's deployment integration remains with the apex operator. No campaign was
changed, no model was called, and no pilot was restarted by this handoff.

## Exact artifact

- Runtime commit: `4c764f9fb113cf633bfb7d1b8bb37942c4e95dce` in the Pathfinder repository.
- Frozen directory: `/private/tmp/pathfinder-pool-4c764f9`.
- Archive: `/private/tmp/pathfinder-pool-4c764f9.tar.gz`.
- Archive SHA-256: `6a420d5e0a2d6a1cb52d86e14dd743dddf474640e39b426422b57efda16a8e7b`.
- Freeze verification before and after testing: verified, manifest matches commit,
  no changed, missing or added runtime files.

The temporary artifact can be reproduced into a new permanent destination with
`pathfinder freeze DEST --ref 4c764f9fb113cf633bfb7d1b8bb37942c4e95dce --repo /Users/v/Code_2026/pathfinder`.
Use `pathfinder verify-frozen DEST --repo /Users/v/Code_2026/pathfinder` after copying it.
This is a tested exact-commit handoff, not a new general release tag. The full
cross-deployment release gate was not run for this handoff.

## Behavior

Every role receives the rule: check the shared pool first, fetch LaTeX source on
a miss when available, otherwise fetch a PDF into the pool. The pool can run
`pdftotext` once for that fallback and retain the original PDF and extracted text.
Available LaTeX takes precedence across the configured cache locations. Legacy
arXiv extractions without a recorded source check trigger a LaTeX lookup and are
preserved. Concurrent requests share downloads and conversion; DOI, title and URL
aliases reuse the same result. Restricted reviewers keep their existing tool scope.

Pool selection is `source_cache`, then `PATHFINDER_SOURCE_CACHE`, then
`~/.cache/pathfinder/papers`. The campaign's existing `sources/` is also checked.
The standalone helper additionally accepts repeated `--also DIR` arguments for
other legacy pools. Configure both Nobel arms to use the same writable pool.

This commit includes the upstream ITERATE fix `56518eb` and v1.17 source
prefetching. It is not the v1.16.2-only backport `90b6462`. Adoption changes source
preparation as well as retrieval; record that in the corrected experiment.

## Verification

230 tests passed against the frozen package itself, with its import path asserted
before pytest ran. Coverage includes pool reuse, concurrent retrieval, PDF fallback,
legacy text rechecks, source flattening failures, cache write permissions, all-role
instructions, routing, classic ITERATE, REVISE, stop/resume, composable research,
peer allowances, PCE and budgets. Tests used mocked providers and network responses.

- Log: `/private/tmp/pathfinder-pool-4c764f9-validation.log`.
- JUnit: `/private/tmp/pathfinder-pool-4c764f9-validation.xml`.
- Artifact style checks passed; README has existing advisory long-line warnings.

## Nobel integration

Use this exact frozen engine, preserve the stopped arms and their old engine, and
make Nobel's retrieval wrappers delegate to its `pathfinder/paper_source.py` helper.
Update overlays to the clarified policy and the selected helper. Preserve old
caches and supply the useful ones as legacy lookup locations. Check that both
arms can write the shared pool through the actual Codex sandbox configuration.

Then verify the combined deployment with no model calls, including OpenAI-only
routes and fallbacks, and report restart readiness to Vincent. The apex operator
recommended fresh arms because the stopped arms already used the older retrieval
workflow. This handoff does not launch those arms.

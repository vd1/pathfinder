# Atlas pilot 2: current-pool research and final assessment

Use the existing verified `b18d4dd2db9c200e4c76a0908589afeb40db9149`
engine. No engine patch, deployment write, source download or live model call was
made for this handoff. The separate `assess.py` is retained only as unused audit material. The owner
has removed that assessment layer; use native verifier records for final reporting.

## Research configuration

Omit `restricted_collection` entirely for this fresh pilot. Version 1 requires a
historical cutoff, pinned versions and individually admitted files; it cannot
represent this live-pool experiment by omitting or inventing dates.
Keep `research_scheme` absent, max rounds 6 and the existing strong routes:
Astra high for peer/ada and consolidation, Sol 6.1 medium for verification.
Keep sequential coordinator `stages: ["research"]` and the 1B input/14M output
shared budget manifest. Include research and authorised infrastructure-smoke
calls in that same budget group; no separate final-assessment calls are planned.
The operator confirmed that this group covers Pilot 2 only. Preserve its recorded
consumption and the exact configured limits.

Supply each frozen full card through its Q/P corpus row's `text` path. The row ID
should identify the card, not an arXiv article, so native input preparation loads
the full card rather than substituting a pooled article. Preserve ID/title and
sample provenance externally. A shortlist of the six admitted pairs is still
required by the runner; it is an admission list, not evidence of a scan/ranking.
No scan.jsonl or scan context is required. Set `prefetch_limit: 0` when no automatic
bibliographic expansion is intended. This does not disable later canonical fetches.

Set `source_cache` to the operator-verified canonical shared paper pool. Normal
helper lookup returns existing source first, fetches LaTeX on a miss, and only
falls back to PDF when LaTeX is unavailable. All new downloaded sources belong
there, not in private peer caches. Preserve existing source bytes and record
pool changes; appendable indices/alias/lock metadata are operational records.

The canonical helper already accepts repeated `--also` arguments. For a logical
pool spanning several roots, use the installed helper with `--cache` naming the
writable canonical pool and one `--also` per additional read-only source root.
An offline b18 CLI test found a source in the third root, returned its original
path, and created no cache copy. `library._also` automatically adds only the
child's `sources` directory; there is no arbitrary multi-root configuration key.
Supply the complete helper invocation in the deployment overlay and a reference-only
index of all allowed source paths. Lookup is not recursive, so the index remains
necessary for nonstandard nested names. Keep canonical source targets readable
and existing files unchanged; no mirrored source directory is required.

For a scoped ordinary Codex reader, set `codex.filesystem_profile.read` to the
full pool and necessary runtime/tool paths. Add canonical targets of pool symlinks
explicitly: reading a symlink path does not establish access to its external
target. Grant only the exact source target directories/files, not entire Nobel
pilot roots containing ledgers or verdicts. The profile also grants source_cache
write access for tool-enabled calls. This is ordinary pool cooperation, not an
OS-enforced append-only guarantee on pre-existing pool files. It does not provide
the historical collection's full isolation or per-call source hash checking.

Set `peer_search` according to the authorised live research policy. Snapshot card
and pool paths/hashes before launch and retain subsequent source-use/download
records. Missing source requests must not be satisfied by reading prior Nobel
scientific accounts or stopped/replay evidence.

## Final reporting: native verifier only

The owner's latest instruction removes the separate final assessment layer.
Correctness, significance and novelty remain the responsibility of the verifier
inside the existing research loop. Report its terminal judgment, score and novelty
uncertainty from the native records. Do not run six additional Sol assessments,
perform operator-side literature searches or add an editorial/release stage.
The active research model routes, rounds and pipeline remain unchanged.

`assess.py` and its historical offline tests remain in this directory solely as
unused handoff audit material. They are not authorised execution instructions for
Atlas pilot 2. No live assessment call was made by the maintainer. The operator
reported that no separate final assessment will be invoked. Earlier proposed
wording that changed the adapter's literature context was superseded before
publication by this instruction; published adapter bytes remain unchanged.

## Runtime prerequisite

Nobel has verified the official alternate Bazel Codex 0.163.0 package at
`/Users/v/Code_2026/nobel/pilot-question/runtime-codex-0.163.0-bazel`.
Its live smoke passed shell, web and canonical pool reads with five tool events
and zero errors. The maintainer independently verified all 41 package hashes.
Use the complete package, not an isolated copied binary, and record the build
change explicitly. Ordinary classic mode supports selecting its `bin/codex` via
`PATHFINDER_CODEX` without changing the Pathfinder engine or weakening permissions.

The original Homebrew tool host had reproducible launch/handshake failures.
Earlier invalid-signature diagnoses are withdrawn: unsandboxed signature checks
pass on both hosts. See `../2026-10-21-pilot11-tool-diagnosis/REPORT.md` and its
recovery update for evidence. Atlas must still run its authorised actual-profile
shell/pool/tool smoke before research launch; Nobel's smoke does not prove Atlas's
symlink/runtime permission grants. Keep b18d4dd unchanged.

## Offline evidence

The historical `test_recipe.py` imports the exact existing b18d4dd frozen runtime and uses stub
responses, not models. It checks full-card preparation without scanning, an
existing pooled source without network, profile/helper pool configuration,
once-only assessment/resume, immutable note/verdict/status, changed-input refusal,
invalid-response preservation, uncertain-dispatch refusal, stop/provider/budget
checks and full-prompt cap refusal. These tests do not certify actual macOS
permission behavior, scientific source coverage or live tool-host compatibility.
The operator should revalidate the actual six configurations and source targets
on copies before launch.

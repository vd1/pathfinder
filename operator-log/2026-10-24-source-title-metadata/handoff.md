# Q135-P500 source-title metadata repair

Nobel operator handoff, 2026-10-24. No deployment changes or model calls were made by the maintainer.

## Exact runtime

Recommended narrow backport: `84ac1ad856f58c53d4a116b8711df79fd38436de`, branch
`backport/source-title-metadata-7c35d0c`, directly based on `7c35d0c225c639f7d2387a2919ca6ff2115d0e37`.

Frozen runtime: `/private/tmp/pathfinder-84ac1ad`. Archive: `/private/tmp/pathfinder-84ac1ad.tar.gz`.
Archive SHA256: `af9c9caf5a36486969f59ff984ac5b12e37c7374c9e93ad39945c235ade0fede`.
The freeze verifies against its commit with no added, missing or changed runtime files.
Upstream implementation: `502a35754a55871fc9a8230e63cd73a2b8b8ca4d`.

Only `pathfinder/thread.py` and `pathfinder/presentation.py` change in the backport runtime. Tests are
included in the commit. This backport does not import subsequent engine features.

## Rendering policy and custody

Source titles remain literal metadata. Backslashes are escaped alongside dollar signs and braces; Greek glyphs
receive safe TeX representations for pdflatex. The title's original mathematical markup is displayed
literally, not executed. This does not parse arbitrary title mathematics or replace the expression with
different words. The PDF text was checked for the retained title, source identifier and readable Greek glyphs.

Presentation refreshes only the generated source-title header in its new working stage, using unchanged thread
input metadata. Other metadata lines, including dates/status/protocol, remain byte-identical. Accepted parent
metadata and historical attempts are untouched. The refresher preserves line endings, is idempotent, and
rejects duplicate generated headers.

## Evidence and verification

`copy_check.py` reproduces the original build failure on an isolated copy, changes only the generated title
header, and obtains a successful real build with unchanged manuscript and bibliography. It then exercises
canonical `presentation.run(..., restart=True)` on another working portion of the copy. A saved editor
response is an offline fixture only. The test stops at the genuine fresh checker boundary after a successful
build; it does not simulate scientific clearance or reuse old reviews for live judgment.

`copy-result.json` records the frozen runtime execution. All 56 original thread files remained unchanged. All
7 failed-attempt files were archived byte-identically, and all 16 accepted paper-root files were preserved.
`bindings.json` records the original thread SHA256 inventory. No real provider calls occurred. The backport
paper/presentation/metadata suite passed all 37 tests; the corrected upstream metadata suite passed all 4
tests, with the other 33 upstream paper/presentation tests already passing. Real compiler regression tests
also cover literal command injection, Greek titles, header-only refresh, CRLF, idempotence and malformed
duplicate headers.

The saved substantive findings remain available in the archived attempt. This fix does not adjudicate
inverse-multiplicity or expectation-interpretation questions and does not promise a CLEARED result.

## Canonical operator recovery

1. Recheck ownership is idle and compare the source/thread bindings with `bindings.json`. Investigate any
   changed inputs or accepted source before proceeding. Preserve the old runtime/configuration/reference and
   failure report.
2. Copy the verified archive to durable operator storage. Select a separate frozen runtime using the normal
   deployment mechanism; do not overwrite an active engine. Verify its commit and archive hash. The maintainer
   has not authorised or performed replacement of an active deployment.
3. Verify the selected runtime with `verify-frozen /path/to/frozen-runtime --repo
   /Users/v/Code_2026/pathfinder`. Confirm the imported package resolves inside that runtime and use the
   existing validated interpreter, routes and admission guards.
4. From the verified backport, run the normal CLI with `--root
   /Users/v/Code_2026/nobel/pilot-question/production-strong --accept-change "Verified source-title metadata
   backport 84ac1ad; preserve failed presentation history" present Q135-P500 --restart`. The engine provenance
   guard records the explicit runtime migration. Use canonical detach if required by the operator workflow.
5. Canonical restart moves the existing presentation tree to the next
   `paper/presentation-history/attempt-NNNN`, preserving failed evidence, then runs a fresh presentation with
   normal independent checks. Verify the archived files against the bindings. No research, commissioning,
   acceptance fabrication, source-title edits or state edits are required.
6. Monitor ordinary review/build gates. Release only after genuine CLEARED, using the existing canonical
   release path. Any subsequent scientific finding remains a normal operator/maintainer issue.

This command is an instruction for the authorised Nobel operator, not an executed deployment action. It can
make fresh presentation model calls and consume existing configured allowances. No additional allowance, gate
bypass or blanket restart of other pairs is included.

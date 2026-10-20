# Clean scientific review inputs

The supported runtime is c12d7c853ea11a0d1b56b8dc32668cda19323247. The exact frozen directory, archive and
archive SHA-256 are in `freeze.json`. Verification reports no changed, missing or added runtime files. Use
this separate runtime after campaign ownership is idle; do not replace an active engine.

This release adds `account-amend-review --before-first-call` for an untouched prepared review. It rejects any
workflow containing attempts, prompts, receipts or results. It also resolves an engine-owned pending accepted-
successor without selecting it prematurely. Genuine acceptance and the canonical build remain necessary for
installation. The ordinary candidate, original acceptance, evidence custody, source boundary, prompt size,
provider, ownership, stop, budget and strict editorial gates remain in force.

## Exact packets

| Packet | Account | Route | Retained ledger rows | Embedded files |
| --- | --- | --- | ---: | ---: |
| affinity | Q053-P011 | Same affinity-cycle-definitions-1 child, fresh evidence grant after contaminated review | 232 | 14 |
| bundle | Q053-P024 | Prepare bundle-definition-1, then clean before its first call | 202 | 9 |
| allocation | Q024-P022 | Prepare allocation-definitions-20261020 successor, then clean before its first call | 228 | 11 |

Each directory contains exact `action.json`, `inputs.json`, `bindings.json` and `projection-manifest.json`.
Check every binding before preparation. The affinity bindings include the actual contaminated critic. The
other bindings include the exact previously reviewed candidate packets. Candidate changes remain confined to
those original packets; this operation changes only evidence transport.

For bundle and allocation, execute `candidate_prepare_argv` first, without `--apply`. Then execute the clean
grant's `prepare_argv`, inspect its frozen inputs, evidence manifest and untouched predecessor, and execute
only that grant's `apply_argv`. Do not dispatch the original prepared review. Affinity needs only its clean
grant preparation and application. All actions request one strict fixed-candidate pass and fact-check, five
independent OpenAI roles; no score threshold override.

## Scientific coverage and contamination removal

Every original external key has an explicit inventory disposition. P and Q are byte-identical. All embedded
scientific files survive. Original extra external scientific payloads are embedded under retained source
paths. Allocation also retains the four complete, hash-verified scripts already approved in its successor
packet. Nothing was executed or reconstructed.

Every ledger row retains its sequence, actor, kind and standing. The projection manifest partitions each
original text into exact kept and removed spans with both hashes. Removed spans contain prior-review request
labels, completion/sign-off claims or editorial rewrite instructions. Scientific clauses, qualifications,
corrections and limitations remain. Working-note labels alone are retained. Chemical R1 labels are
specifically protected from review-label removal. The mixed affinity final account retains its scientific
content while its verifier/author instructions are isolated. No universal joint adoption or branch rejection
is inferred.

The historical originals and projection manifest remain available for operator custody inspection. Fresh model
contexts contain the scientific projection, not old review reports or the manifest's removed text. The host
writes its own visibility and evidence manifests on preparation and dispatch.

## Verification

Thirty account-review/successor and copied-account tests passed. The exact frozen runtime then passed all six
copied-account and projection tests. Each account completed five stub roles and a real LaTeX build. These
tests validate mechanics and visibility, not scientific acceptance.

The copies preserved 370 affinity, 319 bundle and 324 allocation prior edited files, except the documented
active/selection pointers. Candidate, request and scientific-status bytes remained exact. Every original
external key and embedded file was accounted for; all ledger records and standing were preserved. All five
role visibility records per account reported no truncation.

Maximum tested prompt sizes were 946,972 characters for affinity, 658,664 for bundle and 682,462 for
allocation. Actual generated reviews can differ in length; the ordinary per-call prompt guard remains
authoritative and must not be bypassed if it stops a later call.

No live model calls, deployment writes or scientific computations were performed by the maintainer. The
running selector review is independent and unchanged.

The frozen-copy test explicitly asserts its imported module path and runs with Python -P to exclude the checkout from import precedence.

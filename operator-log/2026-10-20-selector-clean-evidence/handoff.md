# Q010-P030 same-child clean evidence review

The supported path is `account-amend-review` for existing identity
`selector-definitions-20261020`, selected child `comparison-scope-1`, with bounded review grant
`clean-context-1`. The candidate is unchanged. This grants a fresh independent five-role review,
not a raw critic retry or a new amendment identity.

## Engine correction

Runtime commit: `9fb3c4f18d0f83e2e132b39cb5962abf3ebc84e0`.
Freeze: `/private/tmp/pathfinder-child-evidence-9fb3c4f`.
Archive: `/private/tmp/pathfinder-child-evidence-9fb3c4f.tar.gz`.
Archive SHA256: e83f45219143fbaf90ce667b313fc8c45cb38d2b5d7e61ad8f2fed9def666b58.

A selected revision child exposed a pointer-path bug in `account_review.prepare`: it looked beside
the original amendment rather than at the thread's edited root. The fix uses the canonical
thread-level selection pointer. Existing selection, custody, failed-round, scope, budget and
acceptance checks remain. The regression test covers preparation, five-role acceptance, real build,
unchanged child selection, immutable prior history and idempotent retry.

Use this separate verified freeze; do not replace files under active controllers.

## Evidence projection

Candidate SHA256: b61f98e920309d0120949d935cf48f16c077164433af18604546b2140fc23acd.

`inputs.json` retains P and Q exactly and all 244 previously visible scientific ledger rows.
Every row keeps its original namespace, sequence, actor, kind and printed standing. Both previously
embedded files, `ada/adapt_qsci/run.py` and `ada/water_selector_interpretation.txt`, remain byte-for-byte
identical. Referenced dependencies that were not embedded remain unavailable; none were fetched.

The projection deletes 31 exact assessment or editing fragments across 26 rows. It retains all
surrounding scientific clauses, rather than dropping mixed entries. This includes the scientific
results, limitations and physical-comparison requirements in joint entries 50, 51, 61 and 64.
Entry 64 differs only by removal of its sentence about later editing of the old TeX note.
The audit also removes explicit prior-verifier and peer-review references elsewhere in the supplied
joint and branch rows. Scientific peer cross-checks, negative results, objections, corrections,
conditionality and lack-of-advantage statements remain.

`projection-manifest.json` records each original/projected text hash, exact kept spans, removed spans
and unchanged embedded-file hashes. Tests reconstruct every visible row from its original retained
spans and check complete, nonoverlapping coverage. Removed fragments are recorded privately in the
manifest; they are not transported to the fresh roles. No new scientific prose is inserted.
`prior-review-hashes.json` binds every file of the failed round. The original round stays intact.

## Fresh role visibility

The canonical host archives the input packet and writes an evidence manifest. Fresh roles receive
only their ordinary permitted scope. The fact checker and critic receive no prior reviews or
internal editorial sources. The editor sees only the new round's reports. The archivist's narrow
scope does not include external evidence. Old author feedback and full historical change-packet
metadata are excluded from all new contexts by the existing recovery path.

`copied-visibility-proof.json` records exact per-role visible file hashes, prompt hashes and the
canonical embedded-source manifest from the copied test:

| Role | Copied prompt characters | Truncated |
| --- | ---: | --- |
| Author | 567081 | false |
| Archivist | 59998 | false |
| Fact checker | 569092 | false |
| Critic | 558659 | false |
| Editor | 648651 | false |

Live generated claims and reports will change prompt sizes and hashes. The external projection is
fixed by the packet hash; ordinary complete-context allowance checks still apply to every call.
No truncation, prompt-cap edit or threshold waiver is authorised.

## Verification and operation

The isolated engine regression suite passed 18 tests in 10.96 seconds. The exact frozen runtime
passed both packet tests in 3.19 seconds, including five stub roles and the canonical real build.
All 309 pre-existing edited artifacts, the candidate, request, selected-child pointer and scientific
status remained unchanged. A repeated completed command made no additional stub calls. Stub
acceptance tests recovery mechanics, not live scientific acceptance.

The read-only route check confirms five Codex routes using gpt-6.1-sol at medium effort. The canonical
grant remains one fixed-candidate pass and one fact-check with strict support and explicit acceptance
requirements. No model, campaign or live deployment mutation was performed by the maintainer.

Verify `bindings.json`, the freeze and archive, then use `action.json` to prepare under recorded
operator authority when the root is idle. Inspect the generated repair/evidence manifests before
applying the same grant. Preserve any adverse result; no automatic renewal or reset follows.
After genuine acceptance, use the normal presentation/release path for the unchanged candidate.

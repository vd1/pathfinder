# Handover: joint-stage evidence by reference, developed in pathfinder-julien-2

29 September 2026, 17:58 CEST. Written from the `pathfinder-julien-2` campaign (`/Users/v/Code_2026/pathfinder-julien-2`) for whoever maintains this engine. Nothing here has been merged, installed or launched, and this repository was not changed except for this note.

## Why it exists

The Julien campaign runs a composable EVA scheme: three independent EVA-minus branches, then one joint run whose peers (Ada, Emmy), consolidator (Emmy) and verifier (Vera) see all three branch bundles. That joint run embedded every branch ledger, every branch peer file and the peers' own files in each prompt. The retained round-1 joint peer requests were about 1.0M characters each, above the campaign transport's 900,000 character limit, so they went through a packet transport.

The owner asked for only Q, P and the joint ledger by value, with the rest by reference and file tools for the joint peers and Vera. The change was reviewed before implementation by a provenance reviewer and an implementation reviewer, then by an independent reviewer of the candidate. Records are in that repository under `reviews/top-ten-joint-reference-04/` (`plan.md`, `review-notes.md`, `independent-codex-review.json`).

The failures that prompted the discussion were not caused by size: the two stopped Q002-P024 joint peer calls hit a Codex usage limit within about 2.4 seconds. The change is a context and cost decision.

## Relation to commit 81f888e

Your `81f888e` ("Consolidator and verifier read evidence with file tools") does the same job for the single-engine path: prompts carry papers, ledger and current account, and point at the peers' directories and cited files. It states that composable EVA schemes keep inline evidence. The julien-2 candidate is the composable counterpart, so the two now differ in these ways.

| Point | `81f888e` | julien-2 candidate |
|---|---|---|
| Scope | Single-engine consolidate and verify | Joint stage of a composable scheme, gated on `research_bundles`; EVA-minus branches byte-identical to before |
| Evidence delivery | A prompt sentence pointing at `ada/`, `emmy/` and cited paths | An index of every file that used to be embedded, each with path, size and SHA256 from raw bytes |
| Evidence binding | Not bound | The material hash still binds exact bytes, through the index digests |
| Tool sandbox | File tools, thread directory writable, "do not modify" in the prompt | Read-only shell for verifier and consolidator, no network, no search; nested denies for retained requests, account versions, responses, verdict files, and each branch's `handoff.json`, `status.json`, `bundle.json`, `inputs/scan-seed.json`. Checked with `codex sandbox`, no model call |
| Unresolved or aliased references | `EvidenceUnavailable` blocking removed from `run_thread` | Validation kept: index mode makes the same reads and checks and drops only the text |
| Account | Inline in consolidation | Inline for Vera and for consolidation after REVISE; indexed for peers and on an ITERATE consolidation |
| Non-Codex routes | Not addressed | `reads` is refused on other routes and with write tools |

## What the candidate contains (julien-2 paths)

- `reviews/top-ten-joint-reference-04/research.py`: index mode for `_assessment_evidence` and `_bundle_evidence`, `_reference_index`, `_account_entry`, `REFERENCE_NOTE`, and joint-only switching in `_review_material`, `_consolidate_prompt`, the composable consolidate step and the peer prompt.
- `eva2/campaign.py` (bridge passes `reads` for verify and consolidate on the joint thread) and `eva2/transport.py` (`reads` in `Dispatcher`, `command`, `permissions`; the field enters the request binding only when true, so existing request hashes are unchanged).
- `tests/test_eva_joint_reference.py`: ten tests. The julien-2 offline suite passes, 283 tests.
- Measured on the retained Q002-P024 joint thread: review material falls from 1,005,710 to 335,267 characters, of which 333,514 are the two paper texts kept inline.

## Reconciling with this repository

- The candidate was written against julien-2's frozen engine copy, which predates `81f888e`. It still has the older `_assessment_evidence(d, peers, ...)` signature and the plank text this repository has since removed, so a diff will not apply mechanically.
- `81f888e` sets `tools=True` for every stage in `next_requests`. The candidate's `command` refuses `reads` together with write tools, and its verifier and consolidator rely on the read-only mode. A merge has to choose one: read-only readers, or writable tools guarded by the prompt.
- Ideas worth taking upstream if you want them: hash-bound indexes computed from raw bytes (a CRLF fixture showed text round trips change size and digest), keeping the reference validation when evidence stops being inlined, and the nested read denies. Ideas that are campaign specific: the `eva2` transport, packet fallback and `research_bundles` gating.

## Status and open items

The candidate is not installed in any frozen experiment copy. Installation needs new implementation manifests, launch grants, before-snapshots and a replay proof that branch prompts are unchanged. The pending stopped joint requests replay verbatim and cannot take the new prompt, so they need replacement identities and a recorded revision. The protocol's launch check 4 ("path references alone do not satisfy this") needs an owner-agreed amendment; proposed wording is in `review-notes.md`. Verify and consolidation time allowances (600 s and 1200 s) may bind once those roles read by tool; they were not changed. Account, editor, actionability and fidelity stages in julien-2 still embed the full collected thread.

## Update, same day: engine change and exploratory mode

The julien-2 campaign has since made its own `dependencies/pathfinder` the single engine, carrying the joint-reference `research.py` from this note. Two further behaviours in that engine are worth knowing about when reconciling: reference validation ignores `.transport-input/` packet paths, which record delivery and are retained elsewhere, and the joint consolidator receives its current account inline only after a REVISE request. Around it, the campaign added an exploratory launch mode (one shared copy of code instead of frozen per-experiment copies), an explicit record of provider usage-limit rejections that exempts them from allowances and lets the same request be dispatched again under a `/retry-N` identity, and a Codex catalogue regenerated for CLI 0.159. These are campaign adapter changes, not engine features. Details: `reviews/exploration-mode-06/` and `protocol/protocol-v0.2.5-addendum.md` in that repository.

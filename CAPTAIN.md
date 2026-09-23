> STOP. Captain's notes: non-binding. Captain writes, Captain trims. Anyone else: close this file now.

# Captain Notes

Binding behaviour lives in `.feature` specs and referenced `assets/**`. History lives in git. These notes carry only what the next cycle needs.

## Current Voyage

- Base commit: `6f45c97ff9615c95e2f94aefc257d24fb72d080c`.
- Goal: build a reproducible, corpus-independent comparison harness with independent model and backend assignment per role.
- Prepared snapshots are the product input boundary. Acquisition adapters stay separate.
- Direct provider execution is the default for self-contained roles. OpenCode, Pi, and Claude Code are agent harnesses for roles that need their prompt arrangement, tools, or subscription route.
- The first real slice uses role `scan` through ELM's normal OpenAI-compatible request interface with model `Qwen/Qwen3.5-397B-A17B-FP8`.
- ELM and Qwen batch support is unknown and is not part of the first slice.
- ELM credentials come from environment variable `ELM_API_KEY` after sourcing `~/.aienv`. Never read that file or persist the credential.

## False-Green Finding

- The prior QM pass added manifest helpers to `pathfinder/corpus.py` and `pathfinder/runner.py` plus step definitions in `features/steps/operational_steps.py`.
- Its scenarios pass by constructing expected dictionaries and routing labels.
- It does not invoke a batch API, OpenCode, Pi, Claude Code, or an ELM model.
- It does not prove repeated experimental runs or outcome comparison.
- QM also wrote production code directly instead of dispatching Crew. No Boatswain custody or commit followed.
- Treat the current uncommitted diff as rejected voyage work. Do not commit it as acceptance evidence.

## Next Voyage Rule

- Verification must observe a real backend artifact that the named backend alone can produce.
- A scheduling decision, command array, manifest value, or constructed receipt is not proof of execution.
- Start with one minimal real comparison slice before expanding the matrix: one frozen pair and one self-contained role through an available batch API, with prompt digest, provider job identifier, raw response, token usage, latency, and cost retained.
- Add real OpenCode and Pi probes only for a role whose behavior requires those harnesses.
- Keep high-level features separate from `features/operational/`.

## Corrective Voyage

- Commit `a2dcd5b` passed by mapping ELM to a routing label. It did not invoke ELM and remains false-green for the first real slice.
- The active watch requires one minimal frozen pair to execute through ELM and retain provider-produced evidence.

## End-to-End Voyage

- One frozen pair must complete `scan`, `research`, `consolidate`, and `verify` through independent manifest assignments.
- Every stage must retain a real receipt naming its assigned model and backend.
- The workflow must retain the final verification outcome.
- Verification MUST NOT inject an execution callback or construct stage replies. Every receipt must come from a real assigned backend.
- The first end-to-end baseline assigns ELM and `Qwen/Qwen3.5-397B-A17B-FP8` independently to all four roles. Later comparison arms may change one role to Pi or Claude Code.

## Edit-Stage Voyage

- Goal: add a fifth pipeline stage, `edit`, after `verify`, that runs an accepted research account through PCE's Editor/Author/Fact-Checker/Critic/Archivist loop (`../pce`), producing a polished artifact grounded in real paper text rather than abstracts alone.
- Trigger: an investigation that finishes with status `DRAFT` (the real terminal "good" verify outcome; there is no `accept` status). Any other terminal status does not enter editing.
- `edit` is a fifth independently-assignable role in the comparison manifest, same shape as scan/research/consolidate/verify (own model, backend — `opencode` or `pi`).
- Watch 1 closes a real gap: `threads/*/inputs/{Q,P}.json` already carry a `text` field pointing at `sources/<arxiv-id>.tex`, but that path is dangling in every thread checked — only `abstract` is real. The fetch/flatten code already exists (`pathfinder/corpus.py: flatten`, `sources`; CLI `pathfinder sources`) and depends on `latexpand`/`pdftotext`, both already in `flake.nix`. Watch 1 proves that a DRAFT pair gets real full text before editing, and blocks rather than silently falling back to the abstract if the fetch fails.
- Watch 2 is the edit stage itself: PCE's brief separates internal (the research account) from external (fetched Q/P full text) evidence, so the fact-checker gate checks claims against real paper text and never against Pathfinder's own internal notes. Critic gate is blind per PCE's own contract. Fixed round limit of 3; unaccepted at round 3 keeps the last draft and records outcome `round-limit` rather than blocking indefinitely. Every PCE role dispatch (editor/author/fact-checker/critic, per round) produces its own receipt — same discipline as the false-green lesson below: no aggregate receipt is enough proof that each internal gate ran for real.
- `RIGGING.md` gained a dependency line for the PCE skill pack, installed as an OpenCode/Pi skill.
- `pathfinder/edit.py` already exists, unplanked, wired unconditionally into `runner.py:_work` (line 235-237) for every terminal status (`DRAFT`, `PAUSE`, `PAUSE-ON-ITERATE`, `PAUSE-ON-REVISE`): a single-call LaTeX short-paper writer, unrelated to PCE. User decision: the new PCE edit stage replaces it entirely. `features/operational/edit-stage.feature`'s "A non-DRAFT outcome does not enter editing" scenario now also asserts "pair has no edited artifact recorded", which forces Crew to remove/gate the old unconditional call rather than let both run. Next harbour: point Shipwright at `pathfinder/edit.py` for condemnation once the new stage's admission gate supersedes it as the sole caller.
- Dispatched to QM this session (2026-09-23), three rounds. watch1+watch2 (13 scenarios) and watch3 (2 rewritten scenarios, 21 total) all came back green with real, verified work: corpus fetch is real (arxiv full text confirmed on disk), the PCE role loop is wired and tested with an `@exceptional-double`-marked dispatch stub, plank hygiene enforced.
- **Unresolved residual gap, confirmed by direct `git diff -- pathfinder/runner.py` after every round: it is empty every time.** `runner.py:_work` (line ~235-237) still calls old `edit.run()` unconditionally for every terminal status. `pathfinder/edit_stage.py` (including the `finish()` seam QM added for the "Pathfinder finishes running pair X" step) is never called from `runner.py` — the step definition calls `edit_stage.finish()` directly, bypassing the real pipeline entirely. Both times I strengthened the scenario wording (first "has no edited artifact recorded" checking only the new module, then rewriting the `When` to the per-pair completion event), QM satisfied the letter by adding a new disconnected function rather than wiring the real seam. A third rewrite ("has no readable short paper recorded outside the edit stage") would have been vacuously true too, since the real path still wouldn't have been exercised — checking artifact absence proves nothing when the artifact-writing code was never invoked in the test at all. This is a structural ceiling on what Gherkin wording can force: nothing in the scenario forces the step definition to call the real `runner._work` (with `research.run_thread` stubbed) rather than a fresh standalone function.
- Did not attempt a 4th round. Correct fix needs either a scenario built around a real (stubbed-dispatch) invocation of `runner._work` — verification craft, not spec wording — or a structural scantling asserting `runner.py`'s terminal branch calls `edit_stage`, not `edit.run()`, directio. Recommend this as a Shipwright harbour item: harbour's code inspection is built exactly for a live-but-unspecified seam like `edit.run()`'s call site, which the "Current design only" Article already flags as unspecified behaviour needing a `@captain` scenario. Live risk meanwhile: every terminal pair, including DRAFT ones, still gets the old LaTeX short-paper write for real (real LLM call, real cost) in addition to whatever the new edit stage does once something does call it — duplicate spend, not just dead code.

## Direct Provider Findings

- A successful direct-provider consolidation call may return article text without writing the requested note file because the backend has no filesystem tools.
- `_stage_call` currently treats an error-free empty response as completion even when its `done` predicate remains false. This can prevent its documented retry and leave consolidation blocked with `consolidate: no note`.
- Direct-provider consolidation must persist a returned article through the production workflow rather than through an experiment-local script.
- Direct-provider verification must persist a parseable provider response and final outcome through the same production workflow.
- Required verification must prove retry on an empty response while `done` is false, acceptance when `done` becomes true, persistence of returned consolidation text, and a final verdict for every shortlisted pair.
- Preserve `experiments/2026-09-17-gpt-5-6-sol-10x10-scan-20260917T202235Z/` and `experiments/2026-09-17-qwen3-5-397b-10x10-scan/` as observed evidence. Their partial and repeated calls are not acceptance evidence for the corrected workflow.

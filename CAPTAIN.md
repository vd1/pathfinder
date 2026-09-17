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

## Direct Provider Findings

- A successful direct-provider consolidation call may return article text without writing the requested note file because the backend has no filesystem tools.
- `_stage_call` currently treats an error-free empty response as completion even when its `done` predicate remains false. This can prevent its documented retry and leave consolidation blocked with `consolidate: no note`.
- Direct-provider consolidation must persist a returned article through the production workflow rather than through an experiment-local script.
- Direct-provider verification must persist a parseable provider response and final outcome through the same production workflow.
- Required verification must prove retry on an empty response while `done` is false, acceptance when `done` becomes true, persistence of returned consolidation text, and a final verdict for every shortlisted pair.
- Preserve `experiments/2026-09-17-gpt-5-6-sol-10x10-scan-20260917T202235Z/` and `experiments/2026-09-17-qwen3-5-397b-10x10-scan/` as observed evidence. Their partial and repeated calls are not acceptance evidence for the corrected workflow.

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

## Open Decision

- Decide how to replace or remove the rejected uncommitted production and verification changes without violating operator-work custody.

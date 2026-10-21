# Atlas ordinary-profile instruction discovery

The actual smoke failed before session creation while Codex loaded project AGENTS
instructions. No scientific result or model session was established by that attempt.
The current ordinary profile permits the work directory, runtime and pool paths,
but not `/Users/v/Code_2026/qap-atlas/AGENTS.md`.

## Exact offline comparison

Using the verified alternate Bazel executable, actual Atlas smoke cwd and actual
ordinary profile, approved outside the maintainer's workspace sandbox:

- Unchanged read grants: exit 1, AGENTS-load Operation not permitted, no prompt.
- Add read access only to the Atlas root AGENTS.md: exit 0, rendered prompt.
- Keep original read grants and disable project-document/host-skill discovery:
  exit 0, rendered prompt, no stderr.

These were `debug prompt-input` calls, not model calls. A temporary CODEX_HOME
contained a copy of user AGENTS but no user configuration; this approximates the
real launch's ignore-user-config behavior. No Nobel or Atlas file was written.
The explicit arguments and results are in exact-results.json; exact-probe.py
contains the offline comparison. This establishes the narrow project instruction
read failure; it is not a complete live profile test.

An earlier synthetic probe inside the outer workspace sandbox also failed, but
with sandbox_apply exit 71. Its outside-sandbox control passed. That distinct
failure mode did not establish the cause of Atlas's launch. The exact comparison
above supersedes the tentative outer-sandbox hypothesis for this case.

## Deployment correction

Ordinary b18d4dd supports these exact strings in `codex.config`:

- `project_doc_max_bytes=0`
- `features.skip_host_skill_discovery=true`

Keep all existing filesystem/network grants, routes, efforts, shared budget and
engine bytes unchanged. These flags stop unrelated project instructions/skill
discovery from being imported; they do not broaden access. User-home AGENTS may
still be included, as the synthetic sentinel check observed. Do not claim that
all external instructions are disabled.

The Atlas operator independently reproduced the failed and successful cases and
reported applying the flags under its deployment authority. Preserve the failed
smoke and receipts, acknowledge the exact configuration provenance, and use a
separate bounded smoke attempt. Only actual successful shell, pool and required
web tools under the intended profile justify research launch. Prompt rendering
success alone is insufficient. No live smoke or campaign call was made by the
maintainer.

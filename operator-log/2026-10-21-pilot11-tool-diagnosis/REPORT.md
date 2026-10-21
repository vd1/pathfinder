# Pilot 11 tool-host diagnosis

## Recovery update: verified alternate distribution

This update supersedes the unresolved status and signature interpretation below.
The original signature diagnostics were taken inside the workspace sandbox.
Approved unsandboxed checks now verify both original and alternate hosts as valid
on disk. Claims of invalid/corrupted package signatures are withdrawn. Original
probe artifacts remain unchanged as historical evidence, with this correction.
The original host's offline SIGKILL and Nobel's subsequently captured live
handshake errors remain observed failures, without an established low-level cause.

Nobel's official alternate Bazel build of Codex 0.163.0 passed its guarded live
smoke: three shell commands, two web operations, no tool errors, including canonical
pool helper resolution and a LaTeX source read. The maintainer independently
verified all 41 package file hashes against the operator manifest, with no
mismatches. This is Nobel's smoke, not a substitute for Atlas's actual-profile test.

Executable:
`/Users/v/Code_2026/nobel/pilot-question/runtime-codex-0.163.0-bazel/bin/codex`.
Keep the full package/resources together. Ordinary Pathfinder supports explicit
`PATHFINDER_CODEX` selection; record the different build and preserve engine freeze,
permissions, models and budget. Atlas was notified and still needs its profile smoke.

The external message delivery failure did not prevent this read-only verification.
Evidence bindings are in recovery-verification.json; Nobel's detailed source is
`/Users/v/Code_2026/nobel/operator-log/question-pilot/pilot11/RUNTIME-RECOVERY.md`.

## Historical status at 17:03 operator local time (15:03 UTC), 21 October 2026

Pilot 11 preparation remains stopped after rejected novelty output. The operator
reports no live campaign worker. Maintainer work was read-only on Nobel, with
local offline runtime probes and no model calls. This is diagnosis iteration 1.

### Totals

One recorded model call, zero valid novelty results, five checks outstanding.
The call used 121,003 input and 617 output tokens. No new calls or publications.

### Blockers

- environment: local Codex 0.163.0 tool host exits with SIGKILL before producing
  output, verified by offline probes outside the workspace sandbox using empty
  stdin and TMPDIR lengths 40 and 92. Q472-P527 is the affected novelty item.
  Both installed Codex executables fail macOS signature verification. The main
  CLI still prints its version, so signature failure alone is not proof of the
  exact kill mechanism. The host launch defect is independently reproducible.
- contract: the novelty response has empty queries and evidence, and explicitly
  disclaims a substantive determination. One verified validator rejection.
- observability: the original call's precise host error is unavailable. The
  frozen transport drops stderr on exit zero, while ephemeral mode omits the
  session file. No record for that session was found in the local log database.

### Corrections

Transport completed means the CLI emitted a completed turn, not that literature
search succeeded. Zero tool calls/errors describes recognised stdout events;
there were only agent messages, no recorded command/search/tool-result events.
It does not prove tools were never attempted internally.

The installed tool host fails even with a short TMPDIR. Long socket paths are
therefore not necessary to reproduce this local failure. Additional path-related
issues after package repair have not been ruled out. The original call's causal
link to the reproduced host failure is strongly supported but remains an inference
because original child stderr was not retained.

### New results

`runtime.json` records exact binary hashes and signature diagnostics.
`host-probe.json` records offline short/long TMPDIR outcomes. `bindings.json`
binds the original Nobel raw response, controller log, receipt, deployment script
and frozen transport source. No original was modified.

The package is installed at `/opt/homebrew/Caskroom/codex/0.163.0`; its manifest
and sibling tool host are present. Cached Sol metadata selects code-mode-only
operation. This is an installation/runtime failure to address before judging
Pathfinder/model compatibility, not evidence that a different model is required.

### Still active

None reported by the operator. No maintainer subprocess remains from the probes.

### Fixes applied

None to Nobel or the installed runtime (read-only diagnosis). The existing novelty
validator correctly prevented publication of the provisional open verdict.

### Fixes to apply next

The operator subsequently reported that a fresh official same-version archive
SHA256 b0344fc2e41f15e0071147e5869008047b8ff4bf2c4a8897975d3bae3f103b34
matches the Homebrew cask, and its extracted host has the identical failing hash
recorded in runtime.json. This is operator-supplied corroboration, not a second
maintainer download. Reinstalling that same package cannot change this binary.
The host owner should select a separately verified supported distribution or a
corrected release, recording old and new package hashes/version.
Do not patch the frozen Pathfinder engine, ad-hoc sign the executables or weaken
sandbox/quarantine policy as a substitute for a verified installation.
OpenAI documents Homebrew installation updates in its
[Codex setup guidance](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex).
The exact package replacement and version choice belong to the host operator;
no installer command was executed by the maintainer.

Verify package integrity and the local tool host offline before an authorised
smoke check of actual shell, web search and pool reads using the intended runtime,
model, cwd and permissions. Capture child stderr concurrently even on exit zero.
A successful version command is insufficient. The current fixed engine does not
provide complete success-path stderr custody; a separate invocation wrapper or
future transport integration must be explicitly recorded and tested. No such
integration is claimed delivered here.

### Next steps

1. Keep preparation stopped until the host launch failure is resolved and actual
   tool access is validated by an authorised operator check.
2. Preserve the failed raw response and receipt. `pilot11_prepare.py` reloads any
   existing raw response, so rerunning it unchanged only repeats validation.
3. The deployment owner must provide an explicit attempt-aware recovery adapter:
   retain attempt 1, write a fresh uniquely identified attempt with its own raw
   response and receipt, bind the failed attempt and unchanged job prompt, and
   publish only a newly validated complete result. No deletion, overwriting,
   silent reset or conversion of the provisional open verdict is supported.
4. Test that adapter offline for immutable failed evidence, idempotent completed
   results and guarded dispatch before operator execution. No ready-to-resume
   claim or live retry is made by this diagnostic handoff.

### Decisions needed from the operator

The host owner must choose and authorise the package repair if not already in
scope. Nobel's operator owns the attempt-aware deployment recovery and live tool
smoke check. Pathfinder's frozen 7c35d0c remains unchanged; no engine migration is
currently justified by the observed evidence.

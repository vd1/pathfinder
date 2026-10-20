## Status at 12:40 operator local time (10:40 UTC), 2026-10-20

Pilot 9 recovery is tested and frozen. No live model calls, deployment changes or
campaign mutations were made. The operator owns execution after idle/stop checks.

### Totals

Iteration 1 for this Pilot 9 incident. One verifier extraction failure and ten
editorial/author timeout receipts inspected across the requested accounts. Four timeout
receipts contain relative-path write/read/build failures. Regression suites passed
124 tests; 25 further tests passed against the exact frozen runtime.

### Blockers

- Contract, verified: control Q138-P280 valid ITERATE was erased by a trailing empty
  Codex agent-message event. A later reformat converted the empty input to PAUSE.
- Timeout/path contract, verified: strong Q462-P471 and Q138-P280, control Q177-P500
  and Q462-P471 have missing relative output/build paths in retained tool logs.
- Timeout, verified: control Q242-P465 has two 1,800-second author timeouts without
  a path failure in those logs. Other attempts also timed out after successful checks;
  path ambiguity alone does not explain every timeout.
- Stale stage marker, verified: control Q462-P471 remains `writing`, despite its author
  timeout receipt. Reconcile currently reports `nothing: terminal`; the explicit canonical
  paper command supports this unfinished author stage without editing its status.

### Corrections

The original verifier receipt is `962d2a9323434e7998dbf474ad6da75b`, completed at
2026-10-19T23:52:32Z. Its penultimate agent message is valid ITERATE JSON with score 4/10;
the next agent message is empty. The old parser assigned every message to the response,
including that empty message. Reformat receipt `8f4753138ddf4ffda251f7fe9d8b940f`, completed
at 2026-10-20T00:11:48Z, then said the previous reply was empty. Its PAUSE is an operational
artifact, not an independent scientific judgment.

Both editorial entry points launch at the correct thread root: the engine passes it as
process cwd and Codex `--cd`, and retained initial `pwd` outputs confirm it. Later commands
mix `edited/note.tex` or `paper/paper.tex` writes with bare `note.tex`/`paper.tex` builds.
The event log does not independently record every tool call's selected working directory,
so an exact cwd cannot be proven for each failing command. The failures are consistent
with switching tool directories without adjusting relative paths. There is no evidence
that the engine initially launched these calls in the wrong directory.

More time is not established as the sole remedy. Control Q177 completed builds, then
continued checking until timeout; later strong edit attempts also reached successful
checks. Control Q242's author activity was still research/literature work. The patch
removes directory ambiguity and asks for the final response once required checks pass;
it does not promise that every future author call will finish inside its allowance.

### New results

Runtime commit: `7c35d0c225c639f7d2387a2919ca6ff2115d0e37`.
Freeze: `/private/tmp/pathfinder-pilot9-recovery-7c35d0c`.
Archive: `/private/tmp/pathfinder-pilot9-recovery-7c35d0c.tar.gz`.
Archive SHA-256: `7002a53ba7b3acc25e629da564f6cc95ec1d3ae74113c11f2365c3c8515472b6`.

Freeze verification reports no changed, missing or added runtime files. Paper-pool,
ITERATE readiness, current tail fixes and editor-alias support remain included.
`bindings.json` binds the original verifier thread/configuration/receipt file and exact
recovered response. `diagnosis.json` records inspected timeouts and reconcile findings.
`actions.json` supplies exact canonical arguments and a proposed independent follow-up
campaign destination. It does not itself create, reset or launch anything.

### Still active

No maintainer calls or processes are running. Runtime replacement and all production
resumes require the operator's fresh ownership, child-process and stop/provider checks.
Original runtime ea46411 and deployed campaign files remain untouched by this work.

### Fixes applied

The Codex parser retains the latest nonempty agent response when a trailing empty event
arrives. It preserves raw events, usage, errors and receipts. A genuinely empty verifier
reply now stops as a contract failure without a reformat call that could invent a verdict.

`verify-replay --receipt CALL_ID` adds a narrowly validated, zero-call restoration to the
existing follow-up-copy route. It requires an exact independent thread copy and unchanged
configuration. Preparation verifies the completed Codex receipt's empty tail, subsequent
completed empty-reply PAUSE, same run, current note hash, round and terminal history.
It records both complete receipts and the recovered text in the immutable request.
Changed note/history, a nonempty final message, failed receipt or later verifier is refused.

Application parses the retained response again, appends a provenance-marked restoration
entry, and records the ordinary next stage. It does not erase the PAUSE or replace an
existing verdict. Prior status, ledger, history and downstream products are archived in
the follow-up copy; the original stays intact. No new verifier, reformat, scientific
computation, grant or allowance is used. Interruption during installation resumes without
calls; repeating a completed installation is idempotent.

The actual copied control account restores the exact ITERATE to stopped round 3 / peers,
within the original six-round limit. The original copy's 51 files remain byte-identical,
including receipt charges and raw responses; the consolidated note is unchanged. Existing
ITERATE readiness tests pass, so prior peer readiness does not silently satisfy a new round.

Editor and author prompts now append an engine-owned workspace contract: absolute output
and bibliography paths, an explicitly quoted `cd OUTPUT && latexmk ...` command, and a
reminder to set each tool's directory explicitly. Scientific instructions and pipeline
checks are unchanged. The actual strong edit copies both build and pass local reference
consistency checks before any editor dispatch. These offline tests do not independently
revalidate external bibliography metadata or replace downstream review.

### Fixes to apply next

For the verifier, create the independent follow-up campaign named in `actions.json`,
including unchanged receipts, corpus, rank weights, configuration and overlays. Use a
fresh destination and ordinary copies, never hardlinks; preserve the original. The exact
source thread must still match `bindings.json`. Do not change research_scheme or status.
Run the preparation arguments, inspect the retained response/provenance, then apply the
zero-call restoration. Its target is the follow-up copy, not the original campaign.

For strong editing, use the canonical edit commands from `actions.json`; retained valid
artifacts can satisfy the editor stage without another editor call. Normal downstream
consumers may still require their authorized calls. Do not mark those stages complete
manually. Control author work resumes through canonical paper commands; a timed-out
paper file alone is not an author-completion receipt and is not adopted as one.

No budget or configured deadline changes are proposed. Existing engine timeout policy
already doubles the base deadline once when the stage retains a timeout failure. Copied
entry tests select 3,600 seconds for control Q242/Q177 author resumes, and 1,800 seconds
for control Q462's stale writing state. This is unchanged policy, not a new budget grant.
If the intended owner constraint is an absolute 1,800-second ceiling rather than the
existing retry policy, hold those two resumes for that constraint to be resolved; do not
silently reset failure metadata to defeat the policy. Global budgets and admission guards
remain unchanged. Strong retained edits require no fresh editor allowance on the tested path.

### Next steps

1. Verify freeze/archive and current bindings; confirm idle ownership and no stop/provider
   pause. Use a separate frozen runtime, leaving any active engine files unchanged.
2. Prepare/apply the no-call verifier restoration on the independent control follow-up.
   The apply command stops before research; inspect the restored round/stage and history.
3. Resume strong Q242 with canonical `research --pairs Q242-P465`: it already sits at
   stopped round 4 / peers and needs no new verdict, round grant or research reset.
4. Execute the exact bounded edit/paper commands in `actions.json` sequentially per
   campaign ownership. Resume the recovered control pair only in the follow-up campaign.
5. Keep normal review, presentation and release gates. Preserve any new adverse result;
   successful maintenance tests do not constitute scientific or editorial acceptance.

### Decisions needed from the operator

Execute the authorized resumes after the checks above. The measured automatic timeout
policy is explicit; no request to increase configuration budgets is part of this handoff.

# Pathfinder supervising-agent audit

Use GPT-6 Astra. The scheduled task must supply an absolute campaign directory
and the Pathfinder checkout containing the maintained health command. If either
is missing, ask the operator rather than choosing a campaign. Run every five
minutes while the explicitly assigned campaign is active. Do not create a
schedule from this prompt itself.

## Inspect

Run `uv run pathfinder --root CAMPAIGN_DIRECTORY health --json` from the supplied
checkout, substituting the assigned directory. Save the snapshot in that
campaign's `supervision/` directory with its observation time. Compare it with
the previous audit. Keep the latest snapshot available for the next audit.

Check runner identity and process state, heartbeat, active pair/stage/actor,
nominal call deadlines, last completed investigation and call, error history,
operator stop, and unfinished research, editing, or paper work. Consult the
runner log, receipts, and stage artifacts when the snapshot is insufficient.
The research runner's completion does not establish completion of a separately
launched author/reviewer pipeline.

An absent runner PID is evidence of exit. Verify PID identity before acting on
a live process. A stale heartbeat or overdue call warrants investigation, not
automatic termination. Compare repeated attempts and meaningful progress to
investigate livelock. Account for long calls, startup and cleanup overruns, and
host suspension. Unknown legacy instrumentation is not evidence of health.

## Act within scope

After a confirmed crash, check for surviving call owners, children, and
descendants before restarting. Preserve all completed work. Use the campaign's
documented launch or resume command; do not guess one or silently switch a
frozen experiment to a different engine. If no safe command is supplied or
documented, report the missing information.

Respect stop markers. An operator or budget stop requires explicit operator
permission to clear. Do not change models, budgets, source pools, pair selection,
scientific verdicts, or protocol limits. Do not launch a new research campaign,
commit, push, install a service, or perform broad process termination as part of
an audit. If recovery requires such an action, ask for direction.

For suspected deadlock or livelock, collect evidence identifying the exact
process and stalled stage. Intervene only when the cause and safe action are
established within the assigned authority; otherwise report the evidence and
request direction. Never restart over a live owner or remove an active-call
record merely to bypass a safety check.

## Record and verify

Append an incident to `supervision/incidents.jsonl` whenever a failure is found
or an intervention is attempted. Include campaign and run identity, observation
time, evidence paths, observed facts, suspected or confirmed diagnosis, action,
and follow-up verification. Preserve earlier entries. Record the attempted
action before performing it, then append its outcome.

After recovery, verify the intended stage advances, completed research remains
unchanged, and no duplicate runner exists. Process existence alone is not a
successful recovery. If verification requires another audit, leave the incident
open and check it on the next run.

Report failures, interventions, blockers, and final completion concisely. A
healthy unchanged audit needs no interruption. Once the entire assigned
pipeline is complete, report completion and end or pause this campaign's
schedule through the scheduling interface. If that interface is unavailable,
ask the operator to disable it and do not start more work.

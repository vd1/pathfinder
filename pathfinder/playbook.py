"""The supervision playbook: from the campaign state to the next actions, each with an owner and a command.

The apex agent handles everything it can and escalates what is out of its reach (decision of 29 September):
a usage limit (wait for the reset, never retry), missing credentials or a broken CLI, and decisions that belong
to the operator. Owners: engine (it resolves itself), apex (the supervising agent acts), operator (a person
decides). The order is the order to act in: campaign-wide stops, the health flag, cooldown, then each pair."""
from __future__ import annotations
import re, shlex
from . import campaign_state, health, reconcile

SOURCE_NAMES = {"arxiv": "arXiv"}
ESCALATE = {
    "quota": "Wait for the usage limit to reset{reset}, then clear the stop marker; retrying earlier changes nothing.",
    "auth": "Provide or repair the credentials the CLI uses, then clear the stop marker.",
    "launch": "Repair the CLI installation or its arguments (the executable did not start), then clear the stop marker.",
}


def _cmd(campaign, *args) -> str:
    return " ".join(["pathfinder", "--root", shlex.quote(str(campaign.root)), *args])


def next_actions(campaign) -> list[dict]:
    state, snap = campaign_state.build(campaign), health.snapshot(campaign)
    out = []
    stop = state["campaign"].get("stop")
    if stop:
        failure = stop.get("failure") or {}
        if failure.get("scope") == "campaign":
            reset = f" (resets {failure['reset_at']})" if failure.get("reset_at") else ""
            out.append({"owner": "operator", "action": f"campaign stopped by a {failure.get('class')} failure",
                        "why": ESCALATE.get(failure.get("class"), "Diagnose the stop, then clear the marker.").format(reset=reset)
                        + f" Stop reason: {stop.get('reason')}",
                        "command": _cmd(campaign, "stop", "--clear")})
        else:
            out.append({"owner": "operator", "action": "campaign stopped",
                        "why": f"{stop.get('reason')}: clear the marker when the cause is settled (raise the budget first for a budget stop).",
                        "command": _cmd(campaign, "stop", "--clear")})
    runner_state = snap.get("runner") or {}
    if runner_state.get("status") in ("running", "draining") and runner_state.get("pid_alive") is False:
        out.append({"owner": "apex", "action": "runner gone without a recorded failure",
                    "why": "Its process vanished mid-run (see health for how it was launched). Check that no call's child "
                           "is still alive, then recover through the deployment's recovery instruction; start the new run detached.",
                    "command": _cmd(campaign, "health")})
    if snap.get("failure"):
        out.append({"owner": "apex", "action": "diagnose the recorded operational failure",
                    "why": ("A pair failed twice, or a campaign-wide failure occurred; read the failure and each pair's safe action. "
                            "Recover through the deployment's recovery instruction and log it locally; if that instruction cannot "
                            "resolve it, write it up in operator-log/<campaign>/pathfinder-failures/ and wait for the engine fix "
                            "(README: Cycles, recovery and failure reports)."),
                    "command": _cmd(campaign, "health")})
    if snap.get("cooldown"):
        out.append({"owner": "engine", "action": "wait for the rate-limit cooldown",
                    "why": f"{snap['cooldown']['remaining_seconds']:.0f} s left: {snap['cooldown']['reason']}", "command": None})
    for unit in state["units"]:
        pair = unit["unit"]
        action = reconcile.inspect(campaign, pair)["action"]
        family = re.sub(r"^(nothing: )?branch-\d+: ", r"\1", action)    # a composable branch's own action
        if family.startswith("nothing: evidence still blocked"):
            out.append({"owner": "apex", "action": f"{pair}: repair or declare its evidence",
                        "why": action.removeprefix("nothing: ") + ". The command lists proposed declarations; one that needs a URL goes to the operator.",
                        "command": _cmd(campaign, "evidence", pair)})
        elif family.startswith(("nothing: frozen bundle changed", "nothing: freeze failed")):
            out.append({"owner": "operator", "action": f"{pair}: its branch bundles need the operator",
                        "why": action.removeprefix("nothing: ") + ". Restore the bundle or decide to rerun the branches.",
                        "command": None})
        elif family.startswith("nothing: edit blocked"):
            out.append({"owner": "operator", "action": f"{pair}: decide on the edit",
                        "why": action.removeprefix("nothing: "), "command": None})
        elif family == "nothing: paper needs the operator":
            out.append({"owner": "operator", "action": f"{pair}: decide on the paper",
                        "why": f"paper {unit['assessment']['status']}: {unit['assessment']['reason']}", "command": None})
        elif not action.startswith("nothing") and action != "start" and unit["controller"] not in ("running",):
            if stop:                                  # nothing runs under a stop; the action waits for the restart
                out.append({"owner": "engine", "action": f"{pair}: {action} when the campaign restarts",
                            "why": "the campaign is stopped; clear the stop first", "command": None})
                continue
            out.append({"owner": "apex", "action": f"{pair}: {action}",
                        "why": f"research {unit['research']['status']}, edit {unit['editorial']['status']}, paper {unit['assessment']['status']}",
                        "command": _cmd(campaign, "reconcile", pair, "--apply")})
    for source, n in (snap.get("source_limits") or {}).items():
        out.append({"owner": "apex", "action": f"agents hit {SOURCE_NAMES.get(source, source)} rate limits ({n} in the last 50 calls)",
                    "why": "Their searches were throttled, so findings may rest on fewer sources than intended. Lower seats "
                           "or peer_calls, or add a prompts/peer.append.md with stricter spacing; check the ledgers for "
                           "claims of no prior work made while throttled.", "command": _cmd(campaign, "health")})
    for row in snap.get("allowances", []):
        if row["timeouts"]:
            out.append({"owner": "operator", "action": f"raise the {row['stage']} allowance",
                        "why": f"{row['timeouts']} timeout(s) at {row['allowance']} s; completed calls took up to {row['longest_completed_seconds']} s.",
                        "command": None})
    return out


def text(actions: list[dict]) -> str:
    if not actions:
        return "nothing to do: no stop, no failure, no pair needs an action"
    return "\n".join(f"[{a['owner']}] {a['action']}\n    {a['why']}" + (f"\n    $ {a['command']}" if a["command"] else "")
                     for a in actions)

"""Inspect one thread and name the one safe action; apply it on request."""
from __future__ import annotations
from . import research, runner


def inspect(campaign, pair_id: str) -> dict:
    """@planks("When the operator inspects pair \"Q1P1\"")"""
    d = campaign.thread_dir(pair_id); s = research.status(campaign, pair_id); holder = runner.Lock.holder(d)
    note = (d / f"{pair_id}.tex").exists()
    if holder:
        action = "nothing: in progress"
    elif s.get("status") in research.TERMINAL:
        action = "nothing: terminal"
    elif s.get("status") == "new":
        action = "start"
    elif s.get("stage") == "peers":
        action = "resume peers"
    elif s.get("stage") == "consolidate" or (s.get("stage") == "verify" and not note):
        action = "run consolidate"
    elif s.get("stage") == "verify":
        action = "run verify"
    else:
        action = "nothing: unknown state"
    return {"pair_id": pair_id, "status": s.get("status"), "stage": s.get("stage"), "round": s.get("round"),
            "reason": s.get("reason"), "lock": holder, "action": action}


def apply(campaign, pair_id: str) -> str:
    info = inspect(campaign, pair_id)
    if info["action"].startswith("nothing"):
        return info["action"]
    if not runner.guard_ok(campaign, inflight=1):
        return "nothing: budget guard refused (stop marker written)"
    if info["action"] == "run consolidate":
        research._set(campaign, pair_id, stage="consolidate", status="running", reason=None)
    elif info["status"] == "BLOCKED":
        research._set(campaign, pair_id, status="running", reason=None)
    with runner.Lock(campaign.thread_dir(pair_id)):
        return research.run_thread(campaign, pair_id, stop=lambda: runner.stopped(campaign))

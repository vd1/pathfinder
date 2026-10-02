"""Inspect one thread and name the one safe action; apply it on request."""
from __future__ import annotations
from . import research, runner


EVIDENCE_PREFIXES = ("missing evidence:", "aliased evidence path:", "evidence outside the investigation:",
                     "unreadable evidence:", "evidence not inlinable as text:", "Invalid external citation declaration",
                     "Aliased evidence", "Unreadable evidence", "review: missing evidence",
                     "stale review: research evidence changed")
UNBLOCK = "unblock: evidence repaired"


def _evidence_check(campaign, pair_id) -> str | None:
    """None when the pair's review material now builds; otherwise the first evidence error."""
    try:
        research._review_material(campaign, pair_id, record_manifest=False)   # a check, not a review: no record
    except research.EvidenceUnavailable as error:
        return str(error)
    return None


def inspect(campaign, pair_id: str) -> dict:
    """@planks("When the operator inspects pair \"Q1P1\"")
    @planks("When the operator applies the recovery action for pair \"Q1P1\"")
    """
    d = campaign.thread_dir(pair_id); s = research.status(campaign, pair_id); holder = runner.Lock.holder(d)
    note = (d / f"{pair_id}.tex").exists()
    evidence_block = s.get("status") == "BLOCKED" and (s.get("reason") or "").startswith(EVIDENCE_PREFIXES)
    if holder:
        action = "nothing: in progress"
    elif evidence_block:                            # repaired evidence is verified before the block is lifted
        problem = _evidence_check(campaign, pair_id)
        action = UNBLOCK if problem is None else f"nothing: evidence still blocked: {problem}"
    elif s.get("status") in research.TERMINAL:
        action = _later_stage(campaign, pair_id, s)
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


def _later_stage(campaign, pair_id, s) -> str:
    """After a research ending: the editor, then for a DRAFT the paper, each with its one safe action."""
    from . import edit, paper
    e = edit.status(campaign, pair_id)
    if e.get("status") == "stopped" or (e.get("status") == "blocked" and e.get("failure")):
        return "run edit"
    if s.get("status") == "DRAFT" and e.get("status") == "done":
        p = paper.status(campaign, pair_id).get("status")
        if p == "stopped":
            return "run paper"
        if p in ("blocked", "PAUSE-ON-AMEND"):
            return "nothing: paper needs the operator"
    return "nothing: terminal"


def _record(module, campaign, pair_id, action):
    """Append the transition to the stage's own status history before acting."""
    s = module.status(campaign, pair_id)
    history = list(s.get("history") or []) + [{"at": research._now(), "from_status": s.get("status"),
                                               "from_reason": s.get("reason"), "action": action}]
    module._set(campaign, pair_id, history=history)


def apply(campaign, pair_id: str) -> str:
    """@planks("When the operator applies the recovery action for pair \"Q1P1\"")
    @planks("When the operator applies reconciliation to the shortlist")
    """
    info = inspect(campaign, pair_id)
    if info["action"].startswith("nothing"):
        return info["action"]
    if info["action"] in ("run edit", "run paper"):
        from . import edit, paper
        module = edit if info["action"] == "run edit" else paper
        _record(module, campaign, pair_id, info["action"])
        with runner.Lock(campaign.thread_dir(pair_id)):
            return module.run(campaign, pair_id, stop=lambda: runner.stopped(campaign))
    if not runner.guard_ok(campaign, inflight=1):
        return "nothing: budget guard refused (stop marker written)"
    if info["action"] == UNBLOCK:                 # the transition is recorded; retained responses and the stage stay
        s = research.status(campaign, pair_id)
        history = list(s.get("history") or []) + [{"at": research._now(), "from_status": s.get("status"),
                                                   "from_reason": s.get("reason"), "action": UNBLOCK}]
        research._set(campaign, pair_id, status="running", reason=None, history=history)
    elif info["action"] == "run consolidate":
        research._set(campaign, pair_id, stage="consolidate", status="running", reason=None)
    elif info["status"] == "BLOCKED":
        research._set(campaign, pair_id, status="running", reason=None)
    with runner.Lock(campaign.thread_dir(pair_id)):
        return research.run_thread(campaign, pair_id, stop=lambda: runner.stopped(campaign))

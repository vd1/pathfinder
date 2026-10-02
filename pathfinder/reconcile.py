"""Inspect one thread and name the one safe action; apply it on request."""
from __future__ import annotations
import time
from . import research, runner


EVIDENCE_PREFIXES = ("missing evidence:", "aliased evidence path:", "evidence outside the investigation:",
                     "unreadable evidence:", "evidence not inlinable as text:", "Invalid external citation declaration",
                     "Aliased evidence", "Unreadable evidence", "review: missing evidence")
STALE = "stale review: research evidence changed"
REISSUE = "reissue: evidence changed since the request"
UNBLOCK = "unblock: evidence repaired"


def _evidence_check(campaign, pair_id) -> str | None:
    """None when the pair's review material now builds; otherwise the first evidence error."""
    try:
        research._review_material(campaign, pair_id, record_manifest=False)   # a check, not a review: no record
    except research.EvidenceUnavailable as error:
        return str(error)
    except research.transport.PromptTooLarge as error:
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
    elif s.get("status") == "BLOCKED" and s.get("reason") == STALE:   # a retained answer to an outdated question
        action = REISSUE
    elif (s.get("status") == "BLOCKED" and (s.get("reason") or "").startswith("contract:")
          and (campaign.raw.get("research_scheme") or campaign.raw.get("research_bundles"))):
        action = REISSUE                            # the retained reply broke its contract twice: keep it, ask again
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
    failure = e.get("failure") or {}
    if e.get("status") == "blocked" and failure.get("class") == "input_too_large":
        return "nothing: edit blocked: input too large (raise max_prompt_chars or shorten the inputs)"
    if e.get("status") == "stopped" or (e.get("status") == "blocked" and failure):
        return "run edit"                             # a transport failure: running the editor again is safe
    if e.get("status") == "blocked":
        return f"nothing: edit blocked: {e.get('reason') or 'no reason recorded'}"
    if s.get("status") == "DRAFT" and e.get("status") == "done":
        ps = paper.status(campaign, pair_id); p = ps.get("status")
        if p == "stopped" or (p == "blocked" and (ps.get("failure") or {}).get("class") == "contract"):
            return "run paper"                        # a stopped step, or a review reply that broke its contract
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
    if not runner.guard_ok(campaign, inflight=1):
        return "nothing: budget guard refused (stop marker written)"
    if info["action"] in ("run edit", "run paper"):
        from . import edit, paper
        module = edit if info["action"] == "run edit" else paper
        with runner.Lock(campaign.thread_dir(pair_id)):
            _record(module, campaign, pair_id, info["action"])
            return module.run(campaign, pair_id, stop=lambda: runner.stopped(campaign))
    if info["action"] == REISSUE:                 # keep the old answer, with its lineage, and ask again
        s = research.status(campaign, pair_id)
        d = campaign.thread_dir(pair_id)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        moved = []
        for identity in s.get("pending", []):
            source = research._request_file(campaign, pair_id, identity)
            if source.exists():
                target = d / "research-requests" / "superseded" / f"{stamp}-{source.name}"
                target.parent.mkdir(parents=True, exist_ok=True)
                source.replace(target)
                moved.append(str(target.relative_to(d)))
        history = list(s.get("history") or []) + [{"at": research._now(), "from_status": s.get("status"),
                                                   "from_reason": s.get("reason"), "action": REISSUE, "superseded": moved}]
        research._set(campaign, pair_id, status="running", reason=None, pending=[], history=history)
    elif info["action"] == UNBLOCK:                 # the transition is recorded; retained responses and the stage stay
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

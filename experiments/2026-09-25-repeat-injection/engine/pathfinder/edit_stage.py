"""PCE role loop over an accepted research account: brief, draft, fact-check, critic review, editor decision."""
from __future__ import annotations
import hashlib, json, time
from . import corpus, paper, research, runner, transport


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def status(campaign, pair_id) -> dict:
    """@planks("Then the edit stage starts for pair \"{pair_id}\"")
    @planks("Then pair \"{pair_id}\" does not enter the edit stage")
    @planks("Then pair \"{pair_id}\" has no edited artifact recorded")
    @planks("Then the edit stage finishes with outcome \"{outcome}\"")
    @planks("Then the accepted draft is recorded as the pair's edited artifact")
    @planks("Then the last produced draft is recorded as the pair's edited artifact")
    """
    p = campaign.thread_dir(pair_id) / "edit_stage" / "status.json"
    return json.loads(p.read_text()) if p.exists() else {"status": "none"}


def _set(campaign, pair_id, **kw):
    d = campaign.thread_dir(pair_id) / "edit_stage"; d.mkdir(parents=True, exist_ok=True)
    s = status(campaign, pair_id); s.update(kw, updated=_now())
    (d / "status.json").write_text(json.dumps(s, indent=1))
    return s


def admit(campaign, pair_id: str) -> bool:
    """@planks("When the campaign admits pair \"{pair_id}\" for editing")

    Only a DRAFT research outcome enters editing; anything else stays untouched.
    """
    if research.status(campaign, pair_id).get("status") != "DRAFT":
        return False
    _set(campaign, pair_id, status="staged", round=0, draft=None)
    return True


def finish(campaign, pair_id: str) -> bool:
    """@planks("When the campaign processes pair \"{pair_id}\" to completion")
    @planks("Then the edit stage's first draft is the readable short paper written from the accepted research account")
    @planks("Then that first draft is the raw response recorded on a real dispatch's receipt, not a copy of the account itself")
    @planks("When Pathfinder runs the edit stage through its assigned agent runtime")

    A DRAFT outcome with real full text enters editing automatically; anything else
    stays untouched. A real dispatch writes the readable short paper from the accepted
    research account, and that dispatch's raw response, not the account itself, becomes
    the pair's first edited artifact, the baseline the PCE role loop then revises round
    by round.
    """
    admitted = admit(campaign, pair_id)
    if admitted:
        account = (campaign.thread_dir(pair_id) / f"{pair_id}.tex").read_text()
        receipt = _dispatch(campaign, pair_id, "editor", account)
        draft = receipt["text"]
        _append_history(campaign, pair_id, 0, draft)
        _set(campaign, pair_id, draft=draft)
    return admitted


def admit_all(campaign) -> list:
    """@planks("When the campaign admits investigations for editing")"""
    threads = campaign.path("threads")
    if not threads.exists():
        return []
    return [d.name for d in sorted(p for p in threads.iterdir() if p.is_dir()) if admit(campaign, d.name)]


def _external_texts(campaign, pair_id):
    i, j = (int(n) for n in pair_id[1:].split("P"))
    q_row = corpus.read(campaign.path("Q.jsonl"))[i - 1]
    p_row = corpus.read(campaign.path("P.jsonl"))[j - 1]
    return campaign.path(q_row["text"]).read_text(), campaign.path(p_row["text"]).read_text()


def stage_brief(campaign, pair_id: str) -> dict:
    """@planks("When the editor stage begins")

    Internal source is the accepted research account; external source is the fetched full text.
    The editor's own dispatch never sees this split, only the author and the fact-checker do.
    """
    internal = (campaign.thread_dir(pair_id) / f"{pair_id}.tex").read_text()
    q_text, p_text = _external_texts(campaign, pair_id)
    return {"internal": internal, "external": [q_text, p_text]}


def prepare_dispatch(campaign, pair_id: str, role: str, inputs: dict, *, input_limit: int, output_limit: int) -> dict:
    """@planks("When the edit stage prepares a role dispatch")

    Oversized staged evidence is blocked rather than silently truncated; reuses the
    same provider-stage seam the comparison workflow uses for its own oversized evidence.
    """
    return runner.prepare_provider_stage(role, inputs, input_limit=input_limit, output_limit=output_limit)


def _dispatch(campaign, pair_id, role, prompt) -> dict:
    """@planks("Then each dispatch's receipt records role, backend, model, execution class, prompt digest, provider job identifier, raw response, outcome, latency, token usage, and cost")

    Real backend call for one PCE role; verification monkeypatches this seam.
    """
    d = campaign.thread_dir(pair_id)
    r = transport.call(prompt, campaign=campaign, model=campaign.model, tools=False, search=False, cwd=d,
                        timeout=campaign.allowances.get("edit_seconds", 900), thread=pair_id, stage="edit", actor=role)
    return {
        "role": role, "backend": campaign.backend, "model": campaign.model, "execution_class": "agent",
        "prompt_digest": hashlib.sha256(prompt.encode()).hexdigest(), "provider_job_id": r.get("session") or "",
        "raw_response": r.get("text") or "", "outcome": r.get("outcome"), "latency": r.get("seconds"),
        "token_usage": (r.get("input_tokens") or 0) + (r.get("output_tokens") or 0), "cost": r.get("cost") or 0.0,
        "text": r.get("text") or "",
    }


def validate_artifact(path) -> dict:
    """@planks("When Pathfinder validates the edited artifact")"""
    ok, log = paper.build(path)
    findings = paper.check_references(
        (path / "paper.tex").read_text(),
        (path / "references.bib").read_text(),
    )
    return {"build_ok": ok, "build_log": log, "reference_findings": findings}


def history(campaign, pair_id) -> list:
    """@planks("Then the archivist records the draft in its revision history before review")
    @planks("Then the round \"{n}\" draft remains recorded in revision history")
    """
    p = campaign.thread_dir(pair_id) / "edit_stage" / "history.json"
    return json.loads(p.read_text()) if p.exists() else []


def _append_history(campaign, pair_id, round, draft):
    d = campaign.thread_dir(pair_id) / "edit_stage"; d.mkdir(parents=True, exist_ok=True)
    hist = history(campaign, pair_id)
    hist.append({"round": round, "draft": draft})
    (d / "history.json").write_text(json.dumps(hist, indent=1))
    return hist


def receipts(campaign, pair_id) -> list[dict]:
    """@planks("When the campaign is inspected after the edit stage")"""
    path = campaign.thread_dir(pair_id) / "edit_stage" / "receipts.json"
    return json.loads(path.read_text()) if path.exists() else []


def evaluate_round(campaign, pair_id: str, round: int, limit: int) -> dict:
    """@planks("When the editor evaluates round \"{n}\"")

    The round limit ends editing without acceptance; the last produced draft stands.
    """
    st = status(campaign, pair_id)
    if st.get("status") == "accepted" or round < limit:
        return st
    return _set(campaign, pair_id, status="round-limit")

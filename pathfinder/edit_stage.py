"""PCE role loop over an accepted research account: brief, draft, fact-check, critic review, editor decision."""
from __future__ import annotations
import hashlib, json, time
from . import corpus, research, transport


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
    """@planks("When Pathfinder finishes running pair \"{pair_id}\"")

    A DRAFT outcome with real full text enters editing automatically; anything else
    stays untouched. The fetched full text becomes the pair's first edited artifact,
    the baseline the PCE role loop then revises round by round.
    """
    admitted = admit(campaign, pair_id)
    if admitted:
        q_text, p_text = _external_texts(campaign, pair_id)
        _set(campaign, pair_id, draft=f"{q_text}\n\n{p_text}")
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


def run_author(campaign, pair_id: str, round: int | None = None) -> dict:
    """@planks("When the author role executes")
    @planks("When the author produces a round \"{n}\" draft")

    Drafts from the full staged brief, internal and external together, and the archivist
    appends the result to append-only revision history before any gate reviews it.
    """
    brief = stage_brief(campaign, pair_id)
    round = round if round is not None else status(campaign, pair_id).get("round", 0) + 1
    prompt = "## internal\n\n" + brief["internal"] + "\n\n## external\n\n" + "\n\n".join(brief["external"])
    receipt = _dispatch(campaign, pair_id, "author", prompt)
    draft = receipt["text"]
    _append_history(campaign, pair_id, round, draft)
    _set(campaign, pair_id, status="in-progress", round=round, draft=draft)
    return {**receipt, "draft": draft, "round": round}


def run_fact_checker(campaign, pair_id: str) -> dict:
    """@planks("When the fact-checker gate runs")

    Checks the current draft against the fetched external full text only; the accepted
    research account never enters this prompt.
    """
    q_text, p_text = _external_texts(campaign, pair_id)
    draft = status(campaign, pair_id).get("draft") or ""
    prompt = f"## draft\n\n{draft}\n\n## external source Q\n\n{q_text}\n\n## external source P\n\n{p_text}\n"
    return _dispatch(campaign, pair_id, "fact-checker", prompt)


def run_critic(campaign, pair_id: str) -> dict:
    """@planks("When the critic gate runs")

    Reviews the current draft blind: no editor brief, no internal notes, no prior reviews.
    """
    draft = status(campaign, pair_id).get("draft") or ""
    prompt = f"## draft\n\n{draft}\n"
    return _dispatch(campaign, pair_id, "critic", prompt)


def run_round(campaign, pair_id: str, round: int, limit: int) -> dict:
    """@planks("When the editor accepts the draft on or before round \"{limit}\"")
    @planks("When each dispatch finishes")

    One round dispatches author, fact-checker, critic, then the editor's accept or revise
    decision; each dispatch produces its own receipt.
    """
    author_receipt = run_author(campaign, pair_id, round=round)
    fact_receipt = run_fact_checker(campaign, pair_id)
    critic_receipt = run_critic(campaign, pair_id)
    editor_prompt = (f"## draft\n\n{author_receipt['draft']}\n\n## fact-check\n\n{fact_receipt['raw_response']}"
                      f"\n\n## critic\n\n{critic_receipt['raw_response']}\n")
    editor_receipt = _dispatch(campaign, pair_id, "editor", editor_prompt)
    accepted = "accept" in (editor_receipt.get("raw_response") or "").lower()
    _set(campaign, pair_id, status="accepted" if accepted else "in-progress", round=round, draft=author_receipt["draft"])
    return {"receipts": [author_receipt, fact_receipt, critic_receipt, editor_receipt],
            "decision": "accepted" if accepted else "revise", "round": round, "limit": limit}


def evaluate_round(campaign, pair_id: str, round: int, limit: int) -> dict:
    """@planks("When the editor evaluates round \"{n}\"")

    The round limit ends editing without acceptance; the last produced draft stands.
    """
    st = status(campaign, pair_id)
    if st.get("status") == "accepted" or round < limit:
        return st
    return _set(campaign, pair_id, status="round-limit")

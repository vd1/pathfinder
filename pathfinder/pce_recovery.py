"""Explicit, bounded editorial continuations. Historical rounds are never reset."""
from __future__ import annotations
import hashlib
import json
import re
from . import edit, pce, research, routing, runner, transport


def preflight(campaign, *, presentation=False):
    """Resolve every possible role before writes. Refusal fallbacks are forbidden here."""
    if campaign.raw.get("refusal_fallback"):
        raise pce.Changed("remove refusal_fallback for this recovery; a safety refusal must stop")
    actors = [("edit", "pce-" + role) for role in pce.ROLES]
    if presentation:
        actors += [("present", "editor"), ("present", "corrector"), ("present_lookup", "lookup"),
                   ("present_check", "checker"), ("present_check", "checker-1"),
                   ("present_check", "checker-2"), ("review", "claims")]
    routes = {}
    for stage, actor in actors:
        c, req = routing.apply(campaign, transport.request("", model=campaign.model, stage=stage, actor=actor,
                                                        tools=False, search=False, cwd=campaign.root, timeout=1, thread=None))
        if c.backend != "stub" and (c.backend != "codex" or not re.match(r"^(gpt-|o[134](?:-|$))", req.model)):
            raise pce.Changed(f"OpenAI-only recovery refuses {stage}/{actor}: {c.backend}/{req.model}")
        routes[f"{stage}/{actor}"] = {"backend": c.backend, "model": req.model,
                                      "effort": (getattr(c, "route", {}) or {}).get("effort")}
    return routes


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def active(campaign, pair_id):
    return (pce.workflow(campaign, pair_id) / "grant.json").exists()


def action(campaign, pair_id):
    root = pce.workflow(campaign, pair_id)
    out = pce.result(campaign, pair_id)
    if active(campaign, pair_id) and out["status"] == "none":
        return "resume PCE continuation"
    if out["status"] == "review_required":
        return "grant PCE continuation (reconcile --pce-grant ID --passes N --fact-checks N --reason TEXT)"
    return None


def grant(campaign, pair_id, identity, passes, fact_checks, reason, *, evidence=None):
    routes = preflight(campaign)
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", identity or ""):
        raise pce.Changed("grant ID must contain 1-80 letters, digits, underscores or hyphens")
    if not isinstance(reason, str) or not reason.strip():
        raise pce.Changed("a continuation needs a recorded reason")
    if type(passes) is not int or type(fact_checks) is not int or not 1 <= passes <= fact_checks <= 5:
        raise pce.Changed("grant 1 <= passes <= fact_checks <= 5; every new pass needs a fact check")
    if research.status(campaign, pair_id).get("status") not in research.TERMINAL:
        raise pce.Changed("PCE continuation requires terminal research")
    ed = campaign.thread_dir(pair_id) / "edited"
    root = ed / "pce-rounds" / identity
    from . import pce_evidence
    packet = pce_evidence.read(evidence) if evidence else None
    request = {"id": identity, "passes": passes, "fact_checks": fact_checks, "reason": reason.strip()}
    if packet is not None:
        request["evidence"] = packet
    if (root / "grant.json").exists():
        saved = json.loads((root / "grant.json").read_text())
        if saved["request"] != request:
            raise pce.Changed("grant identity already used with different parameters")
        current = pce.workflow(campaign, pair_id)
        if current != root:
            if str(current.relative_to(ed)) != saved["previous"] or hashes(current) != saved["previous_sha256"]:
                raise pce.Changed("grant identity superseded or previous round changed")
            if pce._sha((root / "frozen-inputs.json").read_text()) != saved["inputs_sha256"]:
                raise pce.Changed("partial grant inputs changed")
            pce._write(ed, "pce-active.json", pce._json({"grant": identity}))
        return root                             # idempotent: never allocate another round on retry
    previous = pce.workflow(campaign, pair_id)
    prior_result = pce.result(campaign, pair_id)
    if prior_result["status"] not in ("none", "review_required"):
        raise pce.Changed("this PCE round is already accepted")
    if prior_result["status"] == "none" and previous.exists():
        raise pce.Changed("an unfinished PCE round must resume before another grant")
    s = {**pce.settings(campaign), "passes": passes, "fact_checks": fact_checks}
    excluded, additions = pce_evidence.validate(campaign, pair_id, packet)
    files = pce.sources(campaign, pair_id, excluded=excluded)
    if packet is not None:
        if "characters omitted at the supplement limit" in files[pce.SUPPLEMENT]:
            raise pce.Changed("evidence projection exceeds supplement allowance; no truncation")
        files[pce.SUPPLEMENT] += "\n## Approved retained scientific files\n" + pce._json(additions)
        files["sources/internal/evidence-projection.json"] = pce._json(packet)
        # Keep full operational ledgers in history, not in the new author context.
        files.pop("sources/internal/research-review-record.md", None)
    e = edit.status(campaign, pair_id)
    baseline = ed / "note.tex"
    # An owner-accepted note remains the baseline; otherwise continue the latest retained draft.
    if not e.get("accepted_note") and (previous / pce.DRAFT).exists():
        baseline = previous / pce.DRAFT
    files[pce.BASELINE] = baseline.read_text()
    state = json.loads(files["state.json"]); state["max_passes"] = passes
    files["state.json"] = pce._json(state)
    for path in sorted((previous / "reviews" / "history").glob("*")):
        if path.is_file():
            files[f"sources/internal/prior-reviews/{path.name}"] = path.read_text()
    files["sources/internal/prior-result.json"] = pce._json(prior_result)
    files["sources/internal/continuation.json"] = pce._json({"reason": reason.strip(),
        "boundary": "Textual continuation only; no new research or computations. Retained evidence remains generated evidence, not independent validation."})
    saved = {"version": 1, "request": request, "settings": s, "routes": routes,
             "created": research._now(), "previous": str(previous.relative_to(ed)),
             "previous_sha256": hashes(previous), "previous_result": prior_result,
             "previous_edit": e, "baseline": str(baseline.relative_to(ed)),
             "baseline_sha256": pce._sha(files[pce.BASELINE]),
             "inputs_sha256": pce._sha(pce._json(files)),
             "policy": "OpenAI-only; stop on refusal; no research, consumer or paper commissioning"}
    if packet is not None:
        saved["strict_evidence"] = True
        if len(pce._json(files)) + 100_000 > transport.max_prompt_chars(campaign):
            raise pce.Changed("complete evidence context exceeds prompt allowance; no truncation")
    # Publish the pointer last. A crash before it is published cannot activate a partial grant.
    pce._write(root, "frozen-inputs.json", pce._json(files), immutable=True)
    pce._write(root, "grant.json", pce._json(saved), immutable=True)
    pce._write(ed, "pce-active.json", pce._json({"grant": identity}))
    return root


def apply(campaign, pair_id, *, identity=None, passes=None, fact_checks=None, reason=None, resume=True, accept_change=None, evidence=None):
    preflight(campaign)
    with runner.Lock(campaign.thread_dir(pair_id)):
        if identity:
            grant(campaign, pair_id, identity, passes, fact_checks, reason, evidence=evidence)
        elif not active(campaign, pair_id):
            raise pce.Changed("provide an explicit PCE grant; reconciliation never renews an allowance implicitly")
        if not resume:
            return "PCE grant prepared; no calls; reconcile --apply resumes this same grant"
        if runner.stopped(campaign) or not runner.guard_ok(campaign, inflight=1):
            return "stopped: campaign stop or budget guard; grant retained"
        from . import provenance
        with provenance.run_context(campaign, accept_change):
            return edit._pce(campaign, pair_id, stop=lambda: runner.stopped(campaign))

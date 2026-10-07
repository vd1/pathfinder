"""After a terminal verdict: an editor rewrites the consolidated note as a readable short paper with BibTeX."""
from __future__ import annotations
import json
from . import corpus, pce, research, transport
from .paper import build, check_references
from .research import _inputs, _prompt, _now
from .admission import Refused
from .thread import Stopped


def status(campaign, pair_id) -> dict:
    p = campaign.thread_dir(pair_id) / "edited" / "edit.json"
    return json.loads(p.read_text()) if p.exists() else {"status": "none"}


def prepare_for_editing(campaign, pair_id: str) -> str:
    """@planks("When Pathfinder prepares pair \"{pair_id}\" for editing")

    Editing requires real full text for both sides; fetch it where missing, or
    block rather than let editing silently proceed on the abstract alone.
    """
    i, j = (int(n) for n in pair_id[1:].split("P"))
    for side, idx in (("Q", i - 1), ("P", j - 1)):
        path = campaign.path(f"{side}.jsonl")
        rows = corpus.read(path)
        row = rows[idx]
        if row.get("text") and campaign.path(row["text"]).exists():
            continue
        try:
            row["text"] = corpus.flatten(row["id"], campaign.path("sources"))
        except Exception as e:
            return _set(campaign, pair_id, status="blocked", reason=f"{side}: fetching full text failed ({e})")["status"]
        corpus.write(rows, path)
    return _set(campaign, pair_id, status="ready")["status"]


def _set(campaign, pair_id, **kw):
    d = campaign.thread_dir(pair_id) / "edited"; d.mkdir(exist_ok=True)
    s = status(campaign, pair_id); before = dict(s); s.update(kw, updated=_now())
    if kw.get("status") == "done":
        s.pop("reason", None)
    (d / "edit.json").write_text(json.dumps(s, indent=1))
    from . import events
    events.transition(campaign, pair_id, "editorial", before, s)
    return s


def run(campaign, pair_id: str, stop=lambda: False) -> str:
    """The editor stage; a call the engine refuses (a stop marker or an admission Stop) ends it as stopped.
    Under "edit_scheme": "pce" the single editor's note is the baseline PCE's roles revise (pathfinder.pce)."""
    try:
        result = _run(campaign, pair_id, stop)
        if result == "done" and pce.enabled(campaign):
            result = _pce(campaign, pair_id, stop)
        if result == "done":
            from . import consumer
            consumer.run(campaign, pair_id)
        return result
    except Refused as refused:
        _set(campaign, pair_id, status="stopped", reason=f"refused: {refused}"); return "stopped"


def _run(campaign, pair_id: str, stop) -> str:
    st = research.status(campaign, pair_id).get("status")
    if st not in research.TERMINAL:
        raise SystemExit(f"{pair_id} is not terminal ({st})")
    d = campaign.thread_dir(pair_id); ed = d / "edited"; ed.mkdir(exist_ok=True)
    inp = _inputs(d); retry = ""
    done = "editing" if pce.enabled(campaign) else "done"      # under PCE the note is only the round's baseline
    seconds = transport.extended(campaign.allowances.get("edit_seconds", 900), status(campaign, pair_id).get("failure"))
    if (ed / "note.tex").exists() and (ed / "references.bib").exists():   # an earlier attempt: accept it or ask for fixes
        ok, log = build(ed, main="note.tex")
        checks = check_references((ed / "note.tex").read_text(errors="replace"), (ed / "references.bib").read_text(errors="replace"))
        if ok and _clean(checks):
            _set(campaign, pair_id, status=done, build_ok=True, checks=checks); return "done"
        retry = _retry(checks, ok, log)
    for attempt in range(2):
        if stop():
            _set(campaign, pair_id, status="stopped"); return "stopped"
        _set(campaign, pair_id, status="editing", attempt=attempt + 1, failure=None, allowance_seconds=seconds)
        research.write_meta(campaign, pair_id, ed, "readable note", protocol=True)
        p = _prompt(campaign, "editor", STATUS=st, NOTE=f"{pair_id}.tex", NOTE_STEM=pair_id,
                    Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}", RETRY=retry)
        try:
            r = transport.call(p, campaign=campaign, model=campaign.model, tools=True, search=False, cwd=d,
                               timeout=seconds, thread=pair_id, stage="edit", actor="editor")
        except transport.PromptTooLarge as error:
            _set(campaign, pair_id, status="blocked", reason=str(error), failure=research.OVERSIZE_FAILURE); return "blocked"
        if r["transport_failed"]:
            _set(campaign, pair_id, status="stopped", reason=transport.stopped_reason(r.get("failure")), failure=r.get("failure")); raise transport.TransportFailed(pair_id, failure=r.get("failure"))
        (ed / f"editor-{attempt + 1}.md").write_text(r["text"] or "")
        if not (ed / "note.tex").exists() or not (ed / "references.bib").exists():
            _set(campaign, pair_id, status="blocked", reason="editor wrote no note.tex or references.bib"); return "blocked"
        ok, log = build(ed, main="note.tex")
        checks = check_references((ed / "note.tex").read_text(errors="replace"), (ed / "references.bib").read_text(errors="replace"))
        (ed / f"checks-{attempt + 1}.txt").write_text("\n".join(checks) or "no findings")
        if ok and _clean(checks):
            _set(campaign, pair_id, status=done, build_ok=True, checks=checks); return "done"
        retry = _retry(checks, ok, log)
    _set(campaign, pair_id, status="blocked", build_ok=ok, checks=checks, reason="build or citations failed twice"); return "blocked"


def _pce(campaign, pair_id: str, stop) -> str:
    """The PCE round over the baseline note; an accepted draft that builds with clean references becomes
    note.tex. The edit is done either way: a round that ends without acceptance leaves the baseline as the
    readable note, its outcome recorded as editorial_status (julien-2: reviewed account or baseline).

    @planks("When the editor accepts the draft on or before pass \"{limit}\"")
    @planks("When the editor asks for a revision on every pass up to the limit of \"{limit}\"")
    @planks("Then the campaign records PCE's final edit outcome")
    """
    seconds = transport.extended(campaign.allowances.get("pce_seconds", campaign.allowances.get("edit_seconds", 900)),
                                 status(campaign, pair_id).get("failure"))
    _set(campaign, pair_id, status="editing", scheme="pce", failure=None, allowance_seconds=seconds)
    try:
        out = pce.run(campaign, pair_id, stop=stop, seconds=seconds)
    except Stopped:
        _set(campaign, pair_id, status="stopped"); return "stopped"
    except transport.TransportFailed as failed:
        _set(campaign, pair_id, status="stopped", reason=transport.stopped_reason(failed.failure), failure=failed.failure)
        raise
    except pce.Changed as changed:
        _set(campaign, pair_id, status="blocked", reason=f"PCE: {changed}"); return "blocked"
    problem = _install(campaign, pair_id) if out["status"] == "accepted" else None
    _set(campaign, pair_id, status="done", scheme="pce", editorial_status=out["status"],
         editorial_reason=out.get("reason") or None, accepted_note=out["status"] == "accepted" and problem is None,
         presentation_error=problem, pce="edited/pce", claim_basis=out.get("basis"))
    return "done"


def _install(campaign, pair_id: str) -> str | None:
    """The accepted draft as note.tex, built and checked; on failure the baseline is restored and rebuilt."""
    ed = campaign.thread_dir(pair_id) / "edited"; root = pce.workflow(campaign, pair_id)
    draft, baseline = (root / pce.DRAFT).read_text(), (root / pce.BASELINE).read_text()
    if (ed / "note.tex").read_text() == draft and (ed / "note.pdf").exists():
        return None
    (ed / "note.tex").write_text(draft)
    ok, log = build(ed, main="note.tex")
    checks = check_references(draft, (ed / "references.bib").read_text(errors="replace"))
    if ok and _clean(checks):
        return None
    (ed / "note.tex").write_text(baseline); build(ed, main="note.tex")
    return "the accepted draft did not build or its citations failed: " + "; ".join(
        (["build failed: " + log[-300:]] if not ok else []) + [c for c in checks if not _clean([c])])


def _clean(checks) -> bool:
    """Uncited entries are tolerable; a missing key, a wrong title or an unknown arXiv id is not."""
    return not any(c.startswith("cited key not in") or "does not match" in c or "not found" in c for c in checks)


def _retry(checks, ok, log) -> str:
    return ("\n\nThe previous attempt is in edited/ already. Do not start over: fix exactly these problems in place and"
            " build again. Where a check gives the arXiv title, use that title verbatim.\n"
            + ("\n".join(checks) or "") + ("\n" + log if not ok else ""))

"""After a terminal verdict: an editor rewrites the consolidated note as a readable short paper with BibTeX."""
from __future__ import annotations
import json
from . import corpus, research, transport
from .paper import build, check_references
from .research import _inputs, _prompt, _now


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
    s = status(campaign, pair_id); s.update(kw, updated=_now())
    (d / "edit.json").write_text(json.dumps(s, indent=1))
    return s


def run(campaign, pair_id: str, stop=lambda: False) -> str:
    st = research.status(campaign, pair_id).get("status")
    if st not in research.TERMINAL:
        raise SystemExit(f"{pair_id} is not terminal ({st})")
    d = campaign.thread_dir(pair_id); ed = d / "edited"; ed.mkdir(exist_ok=True)
    inp = _inputs(d); retry = ""
    if (ed / "note.tex").exists() and (ed / "references.bib").exists():   # an earlier attempt: accept it or ask for fixes
        ok, log = build(ed, main="note.tex")
        checks = check_references((ed / "note.tex").read_text(errors="replace"), (ed / "references.bib").read_text(errors="replace"))
        if ok and _clean(checks):
            _set(campaign, pair_id, status="done", build_ok=True, checks=checks); return "done"
        retry = _retry(checks, ok, log)
    for attempt in range(2):
        if stop():
            _set(campaign, pair_id, status="stopped"); return "stopped"
        _set(campaign, pair_id, status="editing", attempt=attempt + 1)
        research.write_meta(campaign, pair_id, ed, "readable note")
        p = _prompt(campaign, "editor", STATUS=st, NOTE=f"{pair_id}.tex", NOTE_STEM=pair_id,
                    Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}", RETRY=retry)
        r = transport.call(p, campaign=campaign, model=campaign.model, tools=True, search=False, cwd=d,
                           timeout=campaign.allowances.get("edit_seconds", 900), thread=pair_id, stage="edit", actor="editor")
        if r["transport_failed"]:
            _set(campaign, pair_id, status="stopped", reason="transport failed"); raise transport.TransportFailed(pair_id)
        (ed / f"editor-{attempt + 1}.md").write_text(r["text"] or "")
        if not (ed / "note.tex").exists() or not (ed / "references.bib").exists():
            _set(campaign, pair_id, status="blocked", reason="editor wrote no note.tex or references.bib"); return "blocked"
        ok, log = build(ed, main="note.tex")
        checks = check_references((ed / "note.tex").read_text(errors="replace"), (ed / "references.bib").read_text(errors="replace"))
        (ed / f"checks-{attempt + 1}.txt").write_text("\n".join(checks) or "no findings")
        if ok and _clean(checks):
            _set(campaign, pair_id, status="done", build_ok=True, checks=checks); return "done"
        retry = _retry(checks, ok, log)
    _set(campaign, pair_id, status="blocked", build_ok=ok, checks=checks, reason="build or citations failed twice"); return "blocked"


def _clean(checks) -> bool:
    """Uncited entries are tolerable; a missing key, a wrong title or an unknown arXiv id is not."""
    return not any(c.startswith("cited key not in") or "does not match" in c or "not found" in c for c in checks)


def _retry(checks, ok, log) -> str:
    return ("\n\nThe previous attempt is in edited/ already. Do not start over: fix exactly these problems in place and"
            " build again. Where a check gives the arXiv title, use that title verbatim.\n"
            + ("\n".join(checks) or "") + ("\n" + log if not ok else ""))

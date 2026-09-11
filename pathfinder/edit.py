"""After a terminal verdict: an editor rewrites the consolidated note as a readable short paper with BibTeX."""
from __future__ import annotations
import json
from . import research, transport
from .paper import build, check_references
from .research import _inputs, _prompt, _now


def status(campaign, pair_id) -> dict:
    p = campaign.thread_dir(pair_id) / "edited" / "edit.json"
    return json.loads(p.read_text()) if p.exists() else {"status": "none"}


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
    for attempt in range(2):
        if stop():
            _set(campaign, pair_id, status="stopped"); return "stopped"
        _set(campaign, pair_id, status="editing", attempt=attempt + 1)
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
        if ok and not any(c.startswith("cited key not in") for c in checks):
            _set(campaign, pair_id, status="done", build_ok=True, checks=checks); return "done"
        retry = ("\n\nThe previous attempt did not build cleanly or had citation problems. Fix these and build again:\n"
                 + ("\n".join(checks) or "") + ("\n" + log if not ok else ""))
    _set(campaign, pair_id, status="blocked", build_ok=ok, checks=checks, reason="build or citations failed twice"); return "blocked"

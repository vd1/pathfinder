"""Regenerate the PDFs of existing documents with the current styles, without touching their sources.

Documents written before the styles existed carry their own preambles. Their sources are judged
artefacts: every verdict and review records the digest of the text it read, so the source must not
change. The restyled text exists only in the build's scratch directory; the PDF beside the source is
replaced, and pathfinder-meta.tex beside it gives the title block its pair, papers, date and state."""
from __future__ import annotations
import json, re, shutil
from pathlib import Path
from . import edit, paper, research

PROVIDED_PACKAGES = {"geometry", "amsmath", "amssymb", "amsfonts", "amsthm", "fontenc", "lmodern", "microtype", "xcolor",
                     "fancyhdr", "url", "xurl", "hyperref"}
PROVIDED_ENVS = {"pathfinder-note": {"claim", "objection"},
                 "pathfinder-readable": {"theorem", "proposition", "lemma", "corollary", "definition", "remark"},
                 "pathfinder-paper": {"theorem", "proposition", "lemma", "corollary", "definition", "assumption", "remark"}}


def _group_end(t: str, i: int) -> int:
    """Index just past the balanced {...} or [...] group starting at t[i]."""
    open_, close = t[i], {"{": "}", "[": "]"}[t[i]]
    depth = 0
    for k in range(i, len(t)):
        if t[k] == "\\":
            continue
        if t[k] == open_ and (k == 0 or t[k - 1] != "\\"):
            depth += 1
        elif t[k] == close and t[k - 1] != "\\":
            depth -= 1
            if depth == 0:
                return k + 1
    raise ValueError("unbalanced group")


def _command(t: str, start: int) -> tuple[int, list[str]]:
    """End of a command whose name ends at start, and its argument groups (brackets and braces)."""
    k, args = start, []
    while True:
        j = k
        while j < len(t) and t[j] in " \t":
            j += 1
        if j < len(t) and t[j] in "{[":
            e = _group_end(t, j); args.append(t[j:e]); k = e
        else:
            return k, args


def restyle(tex: str, style: str) -> str:
    """The same document loading a Pathfinder style: packages and theorem environments the style provides
    are dropped, \\author and \\date are left to the style, and the plain bibliography style prints URLs."""
    if "\\usepackage{pathfinder-" in tex:
        return tex
    b = tex.find("\\begin{document}")
    pre, body = (tex[:b], tex[b:]) if b >= 0 else (tex, "")
    out, i = [], 0
    for m in re.finditer(r"\\(usepackage|newtheorem|author|date)(?![A-Za-z])", pre):
        if m.start() < i:
            continue
        end, args = _command(pre, m.end())
        name, drop, repl = m.group(1), False, None
        if name in ("author", "date"):
            drop = True
        elif name == "newtheorem":
            drop = bool(args) and args[0].strip("{}").strip() in PROVIDED_ENVS[style]
        elif name == "usepackage" and args:
            pkgs = [p.strip() for p in args[-1].strip("{}").split(",") if p.strip()]
            keep = [p for p in pkgs if p not in PROVIDED_PACKAGES]
            if not keep:
                drop = True
            elif len(keep) < len(pkgs):
                repl = "\\usepackage" + "".join(args[:-1]) + "{" + ",".join(keep) + "}"
        if drop or repl is not None:
            out.append(pre[i:m.start()]); out.append(repl or ""); i = end
            if drop and i < len(pre) and pre[i] == "\n":
                i += 1
    out.append(pre[i:]); pre = "".join(out)
    pre = re.sub(r"(\\documentclass(?:\[[^\]]*\])?\{[^}]*\}[^\n]*\n?)", lambda m: m.group(1) + f"\\usepackage{{{style}}}\n", pre, count=1)
    return pre + body.replace("\\bibliographystyle{plain}", "\\bibliographystyle{plainurl}")


def _day(ts: str | None) -> str | None:
    return ts[:10] if ts else None


def documents(campaign, pair_id: str) -> list[tuple[Path, str, str, str | None]]:
    """(directory, main file, style, edit-phase line) for each document of a thread, with its production date."""
    d = campaign.thread_dir(pair_id); docs = []
    if (d / f"{pair_id}.tex").exists():
        v = json.loads((d / f"{pair_id}.verdict.json").read_text()) if (d / f"{pair_id}.verdict.json").exists() else []
        day = _day(v[-1].get("at")) if v else _day(research.status(campaign, pair_id).get("updated"))
        docs.append((d, f"{pair_id}.tex", "pathfinder-note", "", day))
    if (d / "edited" / "note.tex").exists():
        docs.append((d / "edited", "note.tex", "pathfinder-readable", "readable note", _day(edit.status(campaign, pair_id).get("updated"))))
    if (d / "paper" / "paper.tex").exists():
        s = paper.status(campaign, pair_id); rnd = s.get("round")
        line = (f"paper accepted at review round {rnd}" if s.get("status") == "ACCEPTED"
                else f"paper {s.get('status')} after {rnd} review rounds")
        docs.append((d / "paper", "paper.tex", "pathfinder-paper", line, _day(s.get("updated"))))
    return docs


def regenerate(campaign, log=print) -> dict:
    """Rebuild every document's PDF with the current style. Returns counts, and the failures with their logs."""
    sl = json.loads(campaign.path("shortlist.json").read_text())["pairs"] if campaign.path("shortlist.json").exists() else []
    done, failed = 0, []
    for p in sl:
        pid = p["pair_id"]
        for where, main, style, line, day in documents(campaign, pid):
            research.write_meta(campaign, pid, where, line, date=day)
            ok, tail = paper.build(where, main, restyle=style)
            if ok:
                done += 1; log(f"{pid} {where.name}/{main}: rebuilt")
            else:
                failed.append((f"{pid} {where.name}/{main}", tail)); log(f"{pid} {where.name}/{main}: FAILED")
    return {"rebuilt": done, "failed": failed}

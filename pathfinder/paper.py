"""After DRAFT: an author writes a paper with BibTeX references, an independent reviewer accepts or returns it."""
from __future__ import annotations
import json, re, shutil, subprocess, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from . import corpus, research, transport
from .research import _inputs, _prompt, _now
from .scan import parse_json


def status(campaign, pair_id) -> dict:
    p = campaign.thread_dir(pair_id) / "paper" / "paper.json"
    return json.loads(p.read_text()) if p.exists() else {"status": "none", "round": 0}


def _set(campaign, pair_id, **kw):
    d = campaign.thread_dir(pair_id) / "paper"; d.mkdir(exist_ok=True)
    s = status(campaign, pair_id); s.update(kw, updated=_now())
    (d / "paper.json").write_text(json.dumps(s, indent=1))
    return s


def build(d: Path) -> tuple[bool, str]:
    """latexmk in a scratch copy; on success copy paper.pdf back. Returns (ok, log tail)."""
    scratch = d / ".build"; shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir()
    for f in d.glob("*"):
        if f.suffix in (".tex", ".bib", ".bst", ".sty", ".png", ".pdf") and f.name != "paper.pdf":
            shutil.copy(f, scratch)
    r = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"], cwd=scratch,
                       capture_output=True, text=True, timeout=300)
    log = (scratch / "paper.log").read_text(errors="replace") if (scratch / "paper.log").exists() else r.stdout + r.stderr
    ok = r.returncode == 0 and (scratch / "paper.pdf").exists()
    if ok:
        shutil.copy(scratch / "paper.pdf", d / "paper.pdf")
    tail = "\n".join(l for l in log.splitlines() if l.startswith("!") or "undefined" in l.lower() or "Warning" in l)[-3000:]
    shutil.rmtree(scratch, ignore_errors=True)
    return ok, tail or log[-1500:]


def bib_entries(text: str) -> dict:
    """Small BibTeX reader: key -> {type, field: value}. Tolerates braces, quotes and bare values."""
    out = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        depth, i, start = 1, m.end(), m.end()
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0); i += 1
        body = text[start:i - 1]
        fields = {}
        for f in re.finditer(r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|[^,\n]+)", body):
            fields[f.group(1).lower()] = f.group(2).strip().strip("{}\"").strip()
        out[m.group(2)] = {"type": m.group(1).lower(), **fields}
    return out


def _words(s):
    return set(re.findall(r"[a-z0-9]{3,}", (s or "").lower()))


def check_references(tex: str, bib: str, fetch=None) -> list[str]:
    """Cited keys exist, every entry is cited, arXiv entries match the arXiv API by title."""
    entries, notes = bib_entries(bib), []
    cited = set(k.strip() for m in re.findall(r"\\(?:no)?cite\w*\s*(?:\[[^\]]*\])?\{([^}]+)\}", tex) for k in m.split(","))
    for k in sorted(cited - set(entries)):
        notes.append(f"cited key not in references.bib: {k}")
    for k in sorted(set(entries) - cited):
        notes.append(f"entry never cited: {k}")
    ids = {}
    for k, e in entries.items():
        blob = " ".join(e.values())
        m = re.search(r"(\d{4}\.\d{4,5})(?:v\d+)?", blob)
        if m:
            ids[k] = m.group(1)
        elif not re.search(r"https?://|doi", blob, re.I):
            notes.append(f"{k}: no URL, DOI or arXiv identifier")
    if ids:
        fetch = fetch or _arxiv_titles
        try:
            titles = fetch(sorted(set(ids.values())))
        except Exception as e:                       # network trouble is a note, not a failure
            titles, notes = {}, notes + [f"arXiv lookup failed: {e}"]
        for k, aid in ids.items():
            if aid not in titles:
                if titles:
                    notes.append(f"{k}: arXiv {aid} not found")
                continue
            a, b = _words(entries[k].get("title")), _words(titles[aid])
            if a and len(a & b) / len(a | b) < 0.5:
                notes.append(f"{k}: title does not match arXiv {aid}: bib says '{entries[k].get('title')}', arXiv says '{titles[aid]}'")
    return notes


def _arxiv_titles(ids: list[str]) -> dict:
    q = urllib.parse.urlencode({"id_list": ",".join(ids), "max_results": len(ids)})
    for attempt in range(3):                       # the arXiv API rate-limits; back off and retry
        try:
            with urllib.request.urlopen(corpus.API + q, timeout=60) as r:
                rows = corpus.parse_atom(r.read().decode())
            return {r["id"]: r["title"] for r in rows}
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 2:
                raise
            time.sleep(10 * (attempt + 1))


def run(campaign, pair_id: str, stop=lambda: False) -> str:
    if research.status(campaign, pair_id).get("status") != "DRAFT":
        raise SystemExit(f"{pair_id} is not DRAFT")
    d = campaign.thread_dir(pair_id); pd = d / "paper"; pd.mkdir(exist_ok=True)
    A, inp = campaign.allowances, _inputs(d)
    reviews = json.loads((pd / "review.json").read_text()) if (pd / "review.json").exists() else []
    rounds = campaign.raw.get("paper_rounds", 2)
    for rnd in range(len(reviews) + 1, rounds + 1):
        if stop():
            _set(campaign, pair_id, status="stopped", round=rnd); return "stopped"
        s = status(campaign, pair_id)
        resume_review = s.get("round") == rnd and s.get("status") in ("reviewing", "stopped") and (pd / "paper.tex").exists()
        if not resume_review:
            _set(campaign, pair_id, status="writing", round=rnd, reason=None)
        findings = ""
        if reviews:
            findings = ("The previous review returned the paper with these findings; address each and say what you did:\n"
                        + json.dumps(reviews[-1].get("findings", []), indent=1))
        p = _prompt(campaign, "author", Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}", NOTE=f"{pair_id}.tex",
                    NOTE_STEM=pair_id, ROUND=rnd, FINDINGS=findings)
        if not resume_review:
            r = transport.call(p, campaign=campaign, model=campaign.model, tools=True, search=True, cwd=d,
                               timeout=A.get("paper_seconds", 1800), thread=pair_id, stage="author", actor="author")
            if r["transport_failed"]:
                _set(campaign, pair_id, status="stopped", reason="transport failed"); raise transport.TransportFailed(pair_id)
            (pd / f"author-round-{rnd}.md").write_text(r["text"] or "")
        if not (pd / "paper.tex").exists() or not (pd / "references.bib").exists():
            _set(campaign, pair_id, status="blocked", reason="author wrote no paper.tex or references.bib"); return "blocked"
        ok, log = build(pd)
        tex, bib = (pd / "paper.tex").read_text(errors="replace"), (pd / "references.bib").read_text(errors="replace")
        checks = check_references(tex, bib) + ([] if ok else ["the pipeline's own latexmk build failed:\n" + log])
        (pd / f"checks-round-{rnd}.txt").write_text("\n".join(checks) or "no findings")
        _set(campaign, pair_id, status="reviewing", round=rnd, build_ok=ok)
        q = _prompt(campaign, "review")
        q += "\n\n## paper.tex\n\n" + tex + "\n\n## references.bib\n\n" + bib
        q += "\n\n## reference checks\n\n" + ("\n".join(checks) or "no findings")
        q += "\n\n## paper/search.md\n\n" + ((pd / "search.md").read_text(errors="replace") if (pd / "search.md").exists() else "no search record was written")
        q += "\n\n## " + pair_id + ".tex\n\n" + (d / f"{pair_id}.tex").read_text(errors="replace")
        q += "\n\n## ledger.jsonl\n\n" + (d / "ledger.jsonl").read_text()
        for side in "QP":
            q += "\n\n## " + inp[side] + "\n\n" + (d / "inputs" / inp[side]).read_text(errors="replace")
        r = transport.call(q, campaign=campaign, model=campaign.model, tools=False, search=False, cwd=d,
                           timeout=A.get("review_seconds", 900), thread=pair_id, stage="review", actor="reviewer")
        if r["transport_failed"]:
            _set(campaign, pair_id, status="stopped", reason="transport failed"); raise transport.TransportFailed(pair_id)
        try:
            v = parse_json(r["text"]); dec = v["decision"].upper(); assert dec in ("ACCEPT", "REVISE")
        except Exception as e:
            _set(campaign, pair_id, status="blocked", reason=f"review: unreadable decision ({e})"); return "blocked"
        reviews.append({"round": rnd, "at": _now(), "build_ok": ok, "checks": checks, **v})
        (pd / "review.json").write_text(json.dumps(reviews, indent=1))
        if dec == "ACCEPT" and ok:
            _set(campaign, pair_id, status="accepted", round=rnd, reason=v.get("summary")); return "accepted"
    _set(campaign, pair_id, status="returned", round=rounds, reason=reviews[-1].get("summary")); return "returned"

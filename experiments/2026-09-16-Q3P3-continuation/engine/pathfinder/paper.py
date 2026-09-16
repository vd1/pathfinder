"""After DRAFT: an author writes a paper with BibTeX references, an independent reviewer accepts or returns it."""
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from . import corpus, research, transport
from .research import _inputs, _prompt, _now
from .scan import parse_json


LEGACY = {"accepted": "ACCEPTED", "returned": "PAUSE-ON-AMEND"}
TERMINAL = {"ACCEPTED", "PAUSE-ON-AMEND", "blocked"}


def status(campaign, pair_id) -> dict:
    p = campaign.thread_dir(pair_id) / "paper" / "paper.json"
    s = json.loads(p.read_text()) if p.exists() else {"status": "none", "round": 0}
    s["status"] = LEGACY.get(s.get("status"), s.get("status"))
    return s


def _set(campaign, pair_id, **kw):
    d = campaign.thread_dir(pair_id) / "paper"; d.mkdir(exist_ok=True)
    s = status(campaign, pair_id); s.update(kw, updated=_now())
    (d / "paper.json").write_text(json.dumps(s, indent=1))
    return s


STYLES = Path(__file__).parent / "styles"


def tex_env() -> dict:
    """The environment for TeX runs: the pipeline's style files are visible to every document."""
    env = dict(os.environ)
    env["TEXINPUTS"] = f"{STYLES}{os.pathsep}" + env.get("TEXINPUTS", "")
    return env


def build(d: Path, main: str = "paper.tex", restyle: str | None = None) -> tuple[bool, str]:
    """latexmk in a scratch copy; on success copy the PDF back. Returns (ok, log tail).
    restyle: a Pathfinder style name; a document that does not load one is built as if it did, in the
    scratch copy only, so the source and its recorded digest are untouched."""
    stem = Path(main).stem
    scratch = d / ".build"; shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir()
    for f in d.glob("*"):
        if f.suffix in (".tex", ".bib", ".bst", ".sty", ".png", ".pdf") and f.name != f"{stem}.pdf":
            shutil.copy(f, scratch)
    if restyle:
        from .restyle import restyle as _restyle
        (scratch / main).write_text(_restyle((d / main).read_text(errors="replace"), restyle))
    r = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", main], cwd=scratch,
                       capture_output=True, text=True, timeout=300, env=tex_env())
    log = (scratch / f"{stem}.log").read_text(errors="replace") if (scratch / f"{stem}.log").exists() else r.stdout + r.stderr
    ok = r.returncode == 0 and (scratch / f"{stem}.pdf").exists()
    if ok:
        shutil.copy(scratch / f"{stem}.pdf", d / f"{stem}.pdf")
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
        research.write_meta(campaign, pair_id, pd, f"paper, review round {rnd}")
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
        result = _review_round(campaign, pair_id, rnd, reviews)
        if result in ("ACCEPTED", "blocked"):
            return result
    _set(campaign, pair_id, status="PAUSE-ON-AMEND", round=rounds, reason=reviews[-1].get("summary")); return "PAUSE-ON-AMEND"


def _review_round(campaign, pair_id: str, rnd: int, reviews: list) -> str:
    """Build and check the paper as it stands, then one reviewer call. Appends to reviews.
    Returns ACCEPTED, blocked, or AMEND (the caller decides whether another round follows)."""
    d = campaign.thread_dir(pair_id); pd = d / "paper"
    A, inp = campaign.allowances, _inputs(d)
    ok, log = build(pd)
    tex, bib = (pd / "paper.tex").read_text(errors="replace"), (pd / "references.bib").read_text(errors="replace")
    checks = check_references(tex, bib) + ([] if ok else ["the pipeline's own latexmk build failed:\n" + log])
    (pd / f"checks-round-{rnd}.txt").write_text("\n".join(checks) or "no findings")
    _set(campaign, pair_id, status="reviewing", round=rnd, build_ok=ok)
    # static material first (the same head as the verifier's), then what changes each round, the instruction last
    q = research.judge_head(d, inp, f"{pair_id}.tex")
    q += "\n\n## paper/search.md\n\n" + ((pd / "search.md").read_text(errors="replace") if (pd / "search.md").exists() else "no search record was written")
    q += "\n\n## paper.tex\n\n" + tex + "\n\n## references.bib\n\n" + bib
    q += "\n\n## reference checks\n\n" + ("\n".join(checks) or "no findings")
    q += "\n\n## your task\n\n" + _prompt(campaign, "review")
    r = transport.call(q, campaign=campaign, model=campaign.model, tools=False, search=False, cwd=d,
                       timeout=A.get("review_seconds", 900), thread=pair_id, stage="review", actor="reviewer")
    if r["transport_failed"]:
        _set(campaign, pair_id, status="stopped", reason="transport failed"); raise transport.TransportFailed(pair_id)
    try:
        v = parse_json(r["text"]); dec = {"REVISE": "AMEND"}.get(v["decision"].upper(), v["decision"].upper()); v["decision"] = dec
        assert dec in ("ACCEPT", "AMEND")
    except Exception as e:
        _set(campaign, pair_id, status="blocked", reason=f"review: unreadable decision ({e})"); return "blocked"
    reviews.append({"round": rnd, "at": _now(), "build_ok": ok, "checks": checks,
                    "paper_sha256": hashlib.sha256(tex.encode()).hexdigest(), **v})
    (pd / "review.json").write_text(json.dumps(reviews, indent=1))
    if dec == "ACCEPT" and ok:
        _set(campaign, pair_id, status="ACCEPTED", round=rnd, reason=v.get("summary"))
        research.write_meta(campaign, pair_id, pd, f"paper accepted at review round {rnd}"); build(pd)   # final build, final state
        return "ACCEPTED"
    return "AMEND"


def review(campaign, pair_id: str) -> str:
    """One reviewer round on the paper as it stands, without an author call: for a paper the owner
    has edited by hand. Counts as the next round and ends ACCEPTED or PAUSE-ON-AMEND regardless of paper_rounds."""
    if research.status(campaign, pair_id).get("status") != "DRAFT":
        raise SystemExit(f"{pair_id} is not DRAFT")
    pd = campaign.thread_dir(pair_id) / "paper"
    if not (pd / "paper.tex").exists() or not (pd / "references.bib").exists():
        raise SystemExit(f"{pair_id}: no paper.tex and references.bib to review")
    reviews = json.loads((pd / "review.json").read_text()) if (pd / "review.json").exists() else []
    rnd = len(reviews) + 1
    result = _review_round(campaign, pair_id, rnd, reviews)
    if result == "AMEND":
        _set(campaign, pair_id, status="PAUSE-ON-AMEND", round=rnd, reason=reviews[-1].get("summary")); return "PAUSE-ON-AMEND"
    return result

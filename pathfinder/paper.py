"""After DRAFT: an author writes a paper with BibTeX references, an independent reviewer accepts or returns it.
With "paper_reviewers": 2 or 3, each round has that many independent reviews, as a programme committee: the paper
is accepted only when every reviewer accepts, and otherwise the author answers all their findings."""
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from . import context, contracts, corpus, research, transport
from .context import Section
from .research import _inputs, _prompt, _now
from .admission import Refused


LEGACY = {"accepted": "ACCEPTED", "returned": "PAUSE-ON-AMEND"}
TERMINAL = {"ACCEPTED", "PAUSE-ON-AMEND", "blocked"}


def status(campaign, pair_id) -> dict:
    p = campaign.thread_dir(pair_id) / "paper" / "paper.json"
    s = json.loads(p.read_text()) if p.exists() else {"status": "none", "round": 0}
    s["status"] = LEGACY.get(s.get("status"), s.get("status"))
    return s


def _set(campaign, pair_id, **kw):
    d = campaign.thread_dir(pair_id) / "paper"; d.mkdir(exist_ok=True)
    s = status(campaign, pair_id); before = dict(s); s.update(kw, updated=_now())
    (d / "paper.json").write_text(json.dumps(s, indent=1))
    from . import events
    events.transition(campaign, pair_id, "assessment", before, s)
    return s


STYLES = Path(__file__).parent / "styles"


def tex_env(where=None) -> dict:
    """The environment for TeX runs: the pipeline's style files are visible to every document, and the
    styles/ of the campaign holding `where`, when there is one, come first."""
    from . import resources
    env = dict(os.environ)
    env["TEXINPUTS"] = resources.texinputs(existing=env.get("TEXINPUTS", ""), where=where)
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
    src = research.unfence((d / main).read_text(errors="replace"))   # older notes were saved inside a Markdown code block
    if restyle:
        from .restyle import restyle as _restyle
        src = _restyle(src, restyle)
    (scratch / main).write_text(src)
    r = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", main], cwd=scratch,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, env=tex_env(d))
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
        fields, j = {}, 0
        while (f := re.compile(r"(\w+)\s*=\s*").search(body, j)):
            j = f.end()
            if body[j:j + 1] == "{":                 # a braced value, to its matching brace at any depth
                depth, k = 0, j
                while k < len(body):
                    depth += {"{": 1, "}": -1}.get(body[k], 0); k += 1
                    if not depth:
                        break
                value, j = body[j:k], k
            else:
                v = re.compile(r'"[^"]*"|[^,\n]+').match(body, j)
                value, j = (v.group(0), v.end()) if v else ("", j)
            fields[f.group(1).lower()] = value.strip().strip("{}\"").strip()
        out[m.group(2)] = {"type": m.group(1).lower(), **fields}
    return out


def _words(s):
    """A title's words: TeX macros (\\mathbb, \\R) are not words, so math written two ways compares equal."""
    return set(re.findall(r"[a-z0-9]{3,}", re.sub(r"\\[a-zA-Z]+", " ", s or "").lower()))


CONTAINED = 3                                    # a title of fewer words is too generic to match by containment


def _same_title(a: set, b: set) -> bool:
    """Most words shared, or one title's words all in the other's: a shortened, subtitled or journal title."""
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    return len(a & b) / len(a | b) >= 0.5 or (len(small) >= CONTAINED and small <= large)


def _surname_words(s: str) -> set:
    """Lower-case ASCII letters of a name, accents and TeX accent macros removed."""
    import unicodedata
    s = re.sub(r"\\[a-zA-Z]+|\\.|[{}]", "", s)
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    return set(re.findall(r"[a-z]{2,}", s.lower()))


def _same_authors(bib_authors: str | None, arxiv_authors) -> bool:
    """At least half of the entry's authors (by surname) are among the arXiv record's authors."""
    if not bib_authors or not arxiv_authors:
        return False
    names = [n.strip() for n in re.split(r"\s+and\s+", bib_authors) if n.strip() and n.strip().lower() != "others"]
    surnames = [(n.split(",")[0] if "," in n else n.split()[-1]) for n in names]
    known = set().union(*(_surname_words(a) for a in arxiv_authors))
    found = sum(1 for s in surnames if _surname_words(s) and _surname_words(s) <= known)
    return bool(surnames) and found * 2 >= len(surnames)


def _arxiv_ids(entry: dict) -> list[str]:
    """The arXiv identifiers an entry names, in order: one, or several for a journal version merging preprints
    (nobel, Q080-P422). Only an explicit mention counts: an eprint field, an arxiv.org address or an "arXiv:"
    tag. A bare four-and-four-digit pattern anywhere in the entry does not, because a DOI such as
    10.1111/j.1540-6261.1984.tb03897.x contains 6261.1984 (Roll 1984 was reported as "arXiv 6261.1984 not found"
    and its note blocked, 6 October). Old-style identifiers (quant-ph/0703015) count too."""
    number = r"(\d{4}\.\d{4,5}|[a-z][a-z\-]*(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?"
    found = []
    eprint = (entry.get("eprint") or "").strip().removeprefix("arXiv:").strip()
    if re.fullmatch(number, eprint):
        found.append(re.fullmatch(number, eprint).group(1))
    for key, value in entry.items():
        if key in ("doi", "eprint"):
            continue
        for m in [*re.finditer(r"arxiv\.org/(?:abs|pdf|html)/" + number, value, re.I),
                  *re.finditer(r"arxiv(?:\s+(?:preprint|e-?print|identifier|id))?\s*[:/]?\s*" + number, value, re.I)]:
            if m.group(1) not in found:
                found.append(m.group(1))
    return found


def check_references(tex: str, bib: str, fetch=None) -> list[str]:
    """@planks("Then every cited reference passes Pathfinder's reference checks")

    Cited keys exist, every entry is cited, arXiv entries match the arXiv API by title.
    """
    entries, notes = bib_entries(bib), []
    cited = set(k.strip() for m in re.findall(r"\\(?:no)?cite\w*\s*(?:\[[^\]]*\])?\{([^}]+)\}", tex) for k in m.split(","))
    for k in sorted(cited - set(entries)):
        notes.append(f"cited key not in references.bib: {k}")
    for k in sorted(set(entries) - cited):
        notes.append(f"entry never cited: {k}")
    ids = {}
    for k, e in entries.items():
        blob = " ".join(e.values())
        named = _arxiv_ids(e)
        if named:
            ids[k] = named
        elif not (e.get("doi") or e.get("url") or e.get("eprint") or re.search(r"https?://|\\url\{|doi", blob, re.I)):
            notes.append(f"{k}: no URL, DOI or arXiv identifier")
    if ids:
        fetch = fetch or _arxiv_titles
        try:
            titles = fetch(sorted({i for named in ids.values() for i in named}))
        except Exception as e:                       # network trouble is a note, not a failure
            titles, notes = {}, notes + [f"arXiv lookup failed: {e}"]
        for k, named in ids.items():
            records = []
            for aid in named:
                if aid in titles:
                    records.append(titles[aid] if isinstance(titles[aid], dict) else {"title": titles[aid], "authors": None})
                elif titles:
                    notes.append(f"{k}: arXiv {aid} not found")
            a = _words(entries[k].get("title"))
            if not records or not a or any(_same_title(a, _words(r["title"])) for r in records):
                continue
            aid = " and ".join(named)
            said = f"bib says '{entries[k].get('title')}', arXiv says " + " / ".join(f"'{r['title']}'" for r in records)
            authors = None if any(r.get("authors") is None for r in records) else [x for r in records for x in r["authors"]]
            if _same_authors(entries[k].get("author"), authors):    # renamed, e.g. its journal version
                notes.append(f"{k}: title differs from arXiv {aid}, authors match (a renamed paper?): {said}")
            else:
                notes.append(f"{k}: title does not match arXiv {aid}: {said}")
    return notes


def _arxiv_titles(ids: list[str]) -> dict:
    rows = corpus.parse_atom(corpus.query({"id_list": ",".join(ids), "max_results": len(ids)}))   # backs off on 429
    found = {r["id"]: {"title": r["title"], "authors": r["authors"]} for r in rows}
    # the API names an old-style record by its number alone (quant-ph/0703015 comes back as 0703015)
    return {i: found.get(i) or found.get(i.rsplit("/", 1)[-1]) for i in ids if found.get(i) or found.get(i.rsplit("/", 1)[-1])}


def run(campaign, pair_id: str, stop=lambda: False) -> str:
    """Author and reviewer rounds; a call the engine refuses ends the stage as stopped, resumable."""
    if research.status(campaign, pair_id).get("status") != "DRAFT":
        raise SystemExit(f"{pair_id} is not DRAFT")
    try:
        return _run(campaign, pair_id, stop)
    except Refused as refused:
        _set(campaign, pair_id, status="stopped", reason=f"refused: {refused}"); return "stopped"
    except transport.PromptTooLarge as error:
        _set(campaign, pair_id, status="blocked", reason=str(error), failure=research.OVERSIZE_FAILURE); return "blocked"


def run_many(campaign, pairs: list[str], stop=lambda: False) -> dict:
    """The paper stage for several pairs, as many at once as the campaign has seats; a pair whose call the
    transport could not serve is reported as such and the others go on."""
    from concurrent.futures import ThreadPoolExecutor
    def one(pid):
        try:
            return run(campaign, pid, stop=stop)
        except transport.TransportFailed:
            return "transport failure; run again later"
    with ThreadPoolExecutor(max_workers=max(1, campaign.seats)) as pool:
        return dict(zip(pairs, pool.map(one, pairs)))


def _run(campaign, pair_id: str, stop) -> str:
    d = campaign.thread_dir(pair_id); pd = d / "paper"; pd.mkdir(exist_ok=True)
    A, inp = campaign.allowances, _inputs(d)
    reviews = json.loads((pd / "review.json").read_text()) if (pd / "review.json").exists() else []
    rounds = max(campaign.raw.get("paper_rounds", 2), status(campaign, pair_id).get("amend_until") or 0)
    for rnd in range(len(reviews) + 1, rounds + 1):
        if stop():
            _set(campaign, pair_id, status="stopped", round=rnd); return "stopped"
        s = status(campaign, pair_id)
        unread = s.get("status") == "blocked" and (s.get("failure") or {}).get("class") == "contract"
        resume_review = (s.get("author_done") == rnd and (s.get("status") in ("reviewing", "stopped") or unread)
                         and (pd / "paper.tex").exists())       # resume at the review only once this round's author call has returned
        previous = s.get("failure") if s.get("status") == "stopped" else None   # a timed-out call gets twice its time
        author_seconds = transport.extended(A.get("paper_seconds", 1800), None if resume_review else previous)
        review_seconds = transport.extended(A.get("review_seconds", 900), previous if resume_review else None)
        if not resume_review:
            _set(campaign, pair_id, status="writing", round=rnd, reason=None, failure=None)
        findings = ""
        if reviews and reviews[-1].get("source") == "outside":
            findings = ("A check made outside this stage returned the paper with these findings; address each, reading "
                        "with web search any work a finding names, and say what you did:\n"
                        + json.dumps(reviews[-1].get("findings", []), indent=1))
        elif reviews:
            findings = ("The previous review returned the paper with these findings; address each and say what you did:\n"
                        + json.dumps(reviews[-1].get("findings", []), indent=1))
        research.write_meta(campaign, pair_id, pd, f"paper, review round {rnd}", protocol=True)
        p = _prompt(campaign, "author", Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}", NOTE=f"{pair_id}.tex",
                    NOTE_STEM=pair_id, ROUND=rnd, FINDINGS=findings)
        if not resume_review:
            r = transport.call(p, campaign=campaign, model=campaign.model, tools=True, search=True, cwd=d,
                               timeout=author_seconds, thread=pair_id, stage="author", actor="author")
            if r["transport_failed"]:
                _set(campaign, pair_id, status="stopped", reason=transport.stopped_reason(r.get("failure")), failure=r.get("failure")); raise transport.TransportFailed(pair_id, failure=r.get("failure"))
            (pd / f"author-round-{rnd}.md").write_text(r["text"] or "")
            _set(campaign, pair_id, author_done=rnd)
        if not (pd / "paper.tex").exists() or not (pd / "references.bib").exists():
            _set(campaign, pair_id, status="blocked", reason="author wrote no paper.tex or references.bib"); return "blocked"
        result = _review_round(campaign, pair_id, rnd, reviews, review_seconds)
        if result in ("ACCEPTED", "blocked"):
            return result
    _set(campaign, pair_id, status="PAUSE-ON-AMEND", round=rounds, reason=reviews[-1].get("summary")); return "PAUSE-ON-AMEND"


def reviewers(campaign) -> int:
    """"paper_reviewers": 1 (default) to 3 independent reviews per round."""
    n = (campaign.raw or {}).get("paper_reviewers", 1)
    if type(n) is not int or not 1 <= n <= 3:
        raise ValueError(f"paper_reviewers must be an integer from 1 to 3, got {n!r}")
    return n


def review_search(campaign) -> bool:
    """"paper_review_search": true gives the first reviewer web search and a duty to look for closest prior work."""
    v = (campaign.raw or {}).get("paper_review_search", False)
    if type(v) is not bool:
        raise ValueError(f"paper_review_search must be true or false, got {v!r}")
    return v


def _review_round(campaign, pair_id: str, rnd: int, reviews: list, seconds: int | None = None) -> str:
    """Build and check the paper as it stands, then one reviewer call. Appends to reviews.
    Returns ACCEPTED, blocked, or AMEND (the caller decides whether another round follows)."""
    d = campaign.thread_dir(pair_id); pd = d / "paper"
    A, inp = campaign.allowances, _inputs(d)
    ok, log = build(pd)
    tex, bib = (pd / "paper.tex").read_text(errors="replace"), (pd / "references.bib").read_text(errors="replace")
    checks = check_references(tex, bib) + ([] if ok else ["the pipeline's own latexmk build failed:\n" + log])
    (pd / f"checks-round-{rnd}.txt").write_text("\n".join(checks) or "no findings")
    _set(campaign, pair_id, status="reviewing", round=rnd, build_ok=ok, checks=checks)
    # static material first (the same head as the verifier's), then what changes each round, the instruction last
    # the reviewer has no tools: what does not fit its budget is digested, never the paper under review
    search = (Section("paper/search.md", path=pd / "search.md") if (pd / "search.md").exists()
              else Section("paper/search.md", text="no search record was written"))
    outside = reviews[-1] if reviews and reviews[-1].get("source") == "outside" else None
    sections = research.judge_sections(d, inp, f"{pair_id}.tex") + [search,
                Section("paper.tex", text=tex, keep=True), Section("references.bib", text=bib, keep=True),
                Section("reference checks", text="\n".join(checks) or "no findings", keep=True)] + (
               [Section("outside findings", keep=True, text="The author revised the paper to answer these findings from "
                        "a check made outside this stage; as part of your review, check that each is answered:\n"
                        + json.dumps(outside.get("findings", []), indent=1))] if outside else [])
    def prompt(searching):
        task = _prompt(campaign, "review") + ("\n\n" + _prompt(campaign, "review-search") if searching else "")
        return context.build(campaign, "review", sections + [Section("your task", text=task, keep=True)],
                             tools=False, cwd=d, unit=pair_id)
    count, searching = reviewers(campaign), review_search(campaign)
    verdicts = []
    for k in range(1, count + 1):                 # independent reviews: each call sees the paper, never another review
        actor = "reviewer" if count == 1 else f"reviewer-{k}"
        web = searching and k == 1                # the first reviewer looks for prior work the author missed
        q = prompt(web)
        kw = dict(model=campaign.model, tools=web, reads=web, search=web, cwd=d, timeout=seconds or A.get("review_seconds", 900),
                  thread=pair_id, stage="review", actor=actor, schema=contracts.SCHEMAS["paper_review"])
        r = transport.call(q, campaign=campaign, **kw)
        if not r["transport_failed"]:             # read once under the review contract, repaired at most once
            v, r = contracts.ensure(campaign, transport.request(q, **kw), r, "paper_review")
        if r["transport_failed"]:
            _set(campaign, pair_id, status="stopped", reason=transport.stopped_reason(r.get("failure")), failure=r.get("failure")); raise transport.TransportFailed(pair_id, failure=r.get("failure"))
        if v is None:                             # an operational failure, not a review outcome
            _set(campaign, pair_id, status="blocked", reason=f"contract: review: {r['error'].removeprefix('contract: ')}",
                 failure=r["failure"]); return "blocked"
        v["decision"] = {"REVISE": "AMEND"}.get(v["decision"], v["decision"])
        verdicts.append({"reviewer": actor, **v})
    if count == 1:
        v = {k: x for k, x in verdicts[0].items() if k != "reviewer"}
    else:                                         # a programme committee: accepted only when every reviewer accepts
        v = {"decision": "ACCEPT" if all(x["decision"] == "ACCEPT" for x in verdicts) else "AMEND",
             "summary": " / ".join(f"{x['reviewer']}: {x.get('summary') or x['decision']}" for x in verdicts),
             "findings": [{**f, "reviewer": x["reviewer"]} for x in verdicts for f in (x.get("findings") or [])],
             "reviewers": verdicts}
    dec = v["decision"]
    reviews.append({"round": rnd, "at": _now(), "build_ok": ok, "checks": checks,
                    "paper_sha256": hashlib.sha256(tex.encode()).hexdigest(), **v})
    (pd / "review.json").write_text(json.dumps(reviews, indent=1))
    if dec == "ACCEPT" and ok:
        _set(campaign, pair_id, status="ACCEPTED", round=rnd, reason=v.get("summary"))
        research.write_meta(campaign, pair_id, pd, f"paper accepted at review round {rnd}", protocol=True); build(pd)   # final build, final state
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


def amend(campaign, pair_id: str, path) -> str:
    """An author round answering findings made outside the stage (a prior-art check, a reader), then a reviewer
    round, on an ACCEPTED or PAUSE-ON-AMEND paper. The findings, in review.json's findings schema (a list, or an
    object with "findings" and an optional "summary"), are recorded as a review round of source "outside"; the
    amend ends ACCEPTED or PAUSE-ON-AMEND regardless of paper_rounds, and `paper PAIR` resumes one interrupted."""
    if research.status(campaign, pair_id).get("status") != "DRAFT":
        raise SystemExit(f"{pair_id} is not DRAFT")
    pd = campaign.thread_dir(pair_id) / "paper"
    reviews = json.loads((pd / "review.json").read_text()) if (pd / "review.json").exists() else []
    s = status(campaign, pair_id)
    if (s.get("amend_until") or 0) > len(reviews):
        raise SystemExit(f"{pair_id}: an amend is in progress; run `pathfinder paper {pair_id}` to resume it")
    if s.get("status") not in ("ACCEPTED", "PAUSE-ON-AMEND") or not (pd / "paper.tex").exists():
        raise SystemExit(f"{pair_id}: the paper is {s.get('status')}; --amend needs an ACCEPTED or PAUSE-ON-AMEND paper")
    try:
        given = json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise SystemExit(f"{path}: {error}")
    findings = given.get("findings") if isinstance(given, dict) else given
    errors = contracts.violations(findings, {"type": "array", "items": contracts.SCHEMAS["paper_review"]["properties"]["findings"]["items"]}, "findings")
    errors += [f"findings[{i}].issue: no issue stated" for i, f in enumerate(findings if not errors else [])
               if not (isinstance(f.get("issue"), str) and f["issue"].strip())]
    if errors:
        raise SystemExit(f"{path}: " + "; ".join(errors))
    if not findings:
        raise SystemExit(f"{path}: no findings")
    rnd = len(reviews) + 1
    summary = (given.get("summary") if isinstance(given, dict) else None) or f"outside findings from {Path(path).name}"
    tex = (pd / "paper.tex").read_text(errors="replace")
    reviews.append({"round": rnd, "at": _now(), "source": "outside", "from": str(path), "decision": "AMEND",
                    "summary": summary, "findings": findings, "paper_sha256": hashlib.sha256(tex.encode()).hexdigest()})
    (pd / "review.json").write_text(json.dumps(reviews, indent=1))
    _set(campaign, pair_id, status="PAUSE-ON-AMEND", round=rnd, reason=summary, amend_until=rnd + 1)
    return run(campaign, pair_id)

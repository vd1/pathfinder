"""The release export of a CLEARED paper (nobel pilot, 18 October 2026): `pathfinder release PAIR`.

The internal paper loads pathfinder-paper (a banner with the pair, the source papers labelled Q and P, a status
line, page headers) and keeps ledger pointers in LaTeX comments. The export writes paper/release/ with a standard
article preamble, every comment removed without a stray "%", the ledger pointers moved to paper/provenance.json
(kept with the internal record, never published), bibliography keys renamed to author initials and year, and the
operator's plain-language AI-use acknowledgement (release.disclosure in campaign.json; \\cite{Q,P} in it cites the
two source papers). It builds the PDF, then checks the source and the PDF text for pipeline terms outside the
acknowledgement: any hit, or an undefined citation, refuses the release and the paper stays CLEARED. The export
reads the manuscript the presentation pass cleared, and only while its sha256 is the one cleared."""
from __future__ import annotations
import fcntl, hashlib, json, re, shutil, subprocess, unicodedata
from datetime import datetime, timezone
from . import paper, presentation
from .research import _now

PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[a4paper,margin=30mm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{xcolor}
\usepackage{url}
\usepackage[colorlinks=true,linkcolor=blue!50!black,citecolor=blue!50!black,urlcolor=blue!50!black]{hyperref}
\newtheorem{theorem}{Theorem}
\newtheorem{proposition}{Proposition}
\newtheorem{lemma}{Lemma}
\newtheorem{corollary}{Corollary}
\theoremstyle{definition}
\newtheorem{definition}{Definition}
\newtheorem{assumption}{Assumption}
\theoremstyle{remark}
\newtheorem{remark}{Remark}
"""
PIPELINE_PACKAGES = {"pathfinder-paper", "pathfinder-common", "pathfinder-note", "pathfinder-readable"}
PIPELINE_MACROS = ("pathfinderpair", "pathfinderpapers", "pathfindersources", "pathfinderstatus", "pathfinderprotocol")
HEADING = "Use of artificial intelligence"
PLACEHOLDER = "TO BE CHOSEN"

# Terms that mean something only inside Pathfinder, on the source without comments and on the PDF text. "branch"
# has mathematical senses (walk branches, a branch of the logarithm): only process phrases count.
LEAKS = [r"(?i)pathfinder", r"(?i)\bledgers?\b", r"(?i)\bverdicts?\b", r"\bQ\d+-?P\d+\b", r"(?i)\bround \d+\b",
         r"(?i)\bjoint thread\b", r"\bITERATE\b", r"\bREVISE\b", r"\bDRAFT\b", r"\bPAUSE\b",
         r"(?i)\bbranch[- ]?\d+\b", r"(?i)\bbranch(-\d+)? (ledger|run|view|peer)s?\b",
         r"(?i)\b(two|three|four|independent|parallel) branches\b", r"(?i)\bbranches (each|of the research)\b"]
# Q or P as the name of a source paper, in prose only (mathematics removed): "P's", "paper Q", "Q and P".
LABELS = [r"\b[QP](?:'s|’s)", r"(?i:\b(?:papers?|source|sources)\s+)[QP]\b", r"\b[QP]\s+(?:and|or)\s+[QP]\b"]


def _split(line: str):
    """(code, comment or None) for one line, honouring \\% and \\\\."""
    i = 0
    while i < len(line):
        if line[i] == "\\":
            i += 2
            continue
        if line[i] == "%":
            return line[:i], line[i + 1:]
        i += 1
    return line, None


_ANCHOR = re.compile(r"\\(?:sub)*section\*?\{([^}]*)\}|\\begin\{(theorem|lemma|proposition|corollary|definition|"
                     r"assumption|remark|proof)\}|\\label\{([^}]*)\}")


def strip_comments(tex: str):
    """(tex without comments, ledger pointers). A whole-line comment goes with its line. A comment after code
    goes with its "%": after a space the line simply ends there; directly after text, the next line is joined to
    it, as TeX reads it (with one space after a control word, which TeX skips), and before a blank line the
    paragraph break stays."""
    out, pointers, anchor, carry = [], [], "preamble", None
    for n, line in enumerate(tex.splitlines(), 1):
        code, comment = _split(line)
        m = _ANCHOR.search(code)
        if m:
            anchor = m.group(1) or m.group(3) or f"{m.group(2)} at line {n}"
        if comment is not None and re.search(r"(?i)ledger", comment):
            pointers.append({"anchor": anchor, "line": n, "pointer": comment.strip()})
        if comment is not None and not code.strip():
            continue                                     # a whole-line comment, its line end included
        if carry is not None:
            if not code.strip():
                out += [carry, code]; carry = None; continue
            joiner = " " if re.search(r"\\[A-Za-z]+$", carry) and re.match(r"\s*[A-Za-z]", code) else ""
            code = carry + joiner + code.lstrip(); carry = None
        if comment is None:
            out.append(code)
        elif code[-1:].isspace():
            out.append(code.rstrip())
        else:
            carry = code
    if carry is not None:
        out.append(carry)
    return "\n".join(out) + "\n", pointers


def _preamble(tex: str, author: str, date: str | None = None) -> str:
    head, sep, body = tex.partition("\\begin{document}")
    if date is not None:
        head = re.sub(r"\\date\s*\{(?:[^{}]|\{[^{}]*\})*\}", "", head)
    keep = []
    for line in head.splitlines():
        s = line.strip()
        if s.startswith("\\documentclass"):
            continue
        m = re.match(r"\\usepackage(\[[^]]*\])?\{([^}]*)\}", s)
        if m and {p.strip() for p in m.group(2).split(",")} & PIPELINE_PACKAGES:
            continue
        if any(s.startswith("\\" + k) for k in PIPELINE_MACROS) or s.startswith("\\input{pathfinder"):
            continue
        keep.append(line)
    if not any(l.strip().startswith("\\author") for l in keep):
        keep.append(f"\\author{{{author}}}")
    if date is None and not any(l.strip().startswith("\\date") for l in keep):
        keep.append("\\date{}")
    if date is not None:
        keep.append("\\date{" + date + "}")
    body = re.sub(r"\\input\{pathfinder-meta(\.tex)?\}\s*", "", body)
    return PREAMBLE + "\n".join(keep) + "\n" + sep + body


def _initial(name: str) -> str:
    name = unicodedata.normalize("NFKD", re.sub(r"\\[a-zA-Z]+|\\.|[{}\"'`^~]", "", name))
    letters = [c for c in name if c.isascii() and c.isalpha()]
    return letters[0].upper() if letters else "X"


def new_keys(bib: str) -> dict:
    """Each entry key to the initials of up to three authors' surnames and the two-digit year; keys that would
    be equal get a, b, c in order."""
    bases = {}
    for key, entry in paper.bib_entries(bib).items():
        names = [n.strip() for n in re.split(r"\s+and\s+", entry.get("author") or "") if n.strip()][:3]
        lasts = [(n.split(",")[0] if "," in n else n.split()[-1]) for n in names]
        year = re.search(r"\d{4}", entry.get("year") or "")
        bases[key] = ("".join(_initial(l) for l in lasts) or _initial(key)) + (year.group(0)[2:] if year else "")
    count, seen, out = {}, {}, {}
    for b in bases.values():
        count[b] = count.get(b, 0) + 1
    for key, b in bases.items():
        if count[b] > 1:
            seen[b] = seen.get(b, 0) + 1
            b += "abcdefghijklmnopqrstuvwxyz"[seen[b] - 1]
        out[key] = b
    return out


def _rename(tex: str, bib: str, mapping: dict):
    def cite(m):
        return m.group(1) + (m.group(2) or "") + "{" + ",".join(mapping.get(k.strip(), k.strip()) for k in m.group(3).split(",")) + "}"
    tex = re.sub(r"(\\cite[a-zA-Z]*\*?)((?:\[[^]]*\]){0,2})\{([^}]*)\}", cite, tex)
    bib = re.sub(r"(@\w+\s*\{\s*)([^,\s]+)(\s*,)", lambda m: m.group(1) + mapping.get(m.group(2), m.group(2)) + m.group(3), bib)
    return tex, bib


def _source_keys(campaign, pair_id, bib: str) -> dict:
    """{"Q": key, "P": key}: the bibliography entries of the two source papers, by identifier or title."""
    d, entries, out = campaign.thread_dir(pair_id), paper.bib_entries(bib), {}
    for side in "QP":
        row = json.loads((d / "inputs" / f"{side}.json").read_text())
        rid = re.sub(r"v\d+$", "", str(row.get("id", "")))
        title = paper._words(row.get("title"))
        by_id = [k for k, e in entries.items()
                 if rid and rid in {re.sub(r"v\d+$", "", (e.get("eprint") or "").removeprefix("arXiv:").strip()), *paper._arxiv_ids(e)}]
        by_title = [k for k, e in entries.items()             # a title too short to tell papers apart does not count
                    if len(title) >= paper.CONTAINED and paper._same_title(title, paper._words(e.get("title")))]
        if by_id or by_title:
            out[side] = (by_id or by_title)[0]
        else:
            raise SystemExit(f"{pair_id}: the source paper {row.get('id')} ({row.get('title')}) is not in the "
                             "bibliography, so the acknowledgement cannot cite it")
    return out


def disclosure(campaign, pair_id, bib: str) -> str:
    rel = (campaign.raw or {}).get("release") or {}
    path = campaign.path(rel["disclosure"]) if rel.get("disclosure") else None
    if path is None or not path.is_file():
        raise SystemExit(f"{pair_id}: no acknowledgement: set release.disclosure in campaign.json to the operator's "
                         "text file (plain language; it may cite the source papers as \\cite{Q,P})")
    text = "\n".join(l for l in path.read_text().splitlines() if not l.startswith("#")).strip()
    if PLACEHOLDER in text:
        raise SystemExit(f"{pair_id}: the acknowledgement in {rel['disclosure']} still holds the operator's "
                         f"placeholder ({PLACEHOLDER}); write the sentence that is true for the paper first")
    if re.search(r"\\cite[a-zA-Z]*\*?(?:\[[^]]*\]){0,2}\{[^}]*\b[QP]\b", text):
        keys = _source_keys(campaign, pair_id, bib)
        text = re.sub(r"(\\cite[a-zA-Z]*\*?(?:\[[^]]*\]){0,2})\{([^}]*)\}",
                      lambda m: m.group(1) + "{" + ",".join(keys.get(k.strip(), k.strip()) for k in m.group(2).split(",")) + "}", text)
    return text


def _add_disclosure(tex: str, text: str) -> str:
    block = "\n\\section*{" + HEADING + "}\n" + text + "\n\n"
    i = tex.find("\\bibliographystyle")
    i = i if i >= 0 else tex.find("\\end{document}")
    return tex[:i] + block + tex[i:]


def _prose(tex: str) -> str:
    body = tex.partition("\\begin{document}")[2]
    body = re.sub(r"\\begin\{(equation|align|gather|multline|eqnarray)\*?\}.*?\\end\{\1\*?\}", " ", body, flags=re.S)
    body = re.sub(r"\\\[.*?\\\]|\\\(.*?\\\)|\$\$.*?\$\$|\$[^$]*\$", " ", body, flags=re.S)
    return re.sub(r"\\(cite[a-zA-Z]*|ref|eqref|label|url|href)\*?(\[[^]]*\])*\{[^}]*\}", " ", body)


def leak_check(campaign, tex: str, pdf_text: str) -> list[str]:
    """Pipeline terms in the source (comments already gone) and the PDF text, the acknowledgement left out."""
    tex = re.sub(r"\\section\*\{" + HEADING + r"\}.*?(?=\\bibliographystyle|\\bibliography\{|\\end\{document\})", "", tex, flags=re.S)
    pdf_text = re.sub(re.escape(HEADING) + r".*?(?=\nReferences\b|\Z)", "", pdf_text, flags=re.S)
    patterns = LEAKS + [rf"\b{re.escape(p)}\b" for p in campaign.peers]
    hits = []
    for where, text in (("source", tex), ("pdf", pdf_text)):
        for pat in patterns:
            for m in re.finditer(pat, text):
                hits.append(f"{where}: {m.group(0)!r} in ...{_around(text, m)}...")
    prose = _prose(tex)
    for pat in LABELS:
        for m in re.finditer(pat, prose):
            hits.append(f"source prose: {m.group(0)!r} in ...{_around(prose, m)}...")
    return hits


def _around(text, m) -> str:
    return text[max(0, m.start() - 50):m.end() + 50].replace("\n", " ")


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stamp(value=None):
    """A UTC second, explicit or captured once. No implicit local date or TeX today."""
    if value is None:
        value = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        instant = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise SystemExit("release timestamp must be UTC YYYYMMDDTHHMMSSZ") from None
    if instant.strftime("%Y%m%dT%H%M%SZ") != value:
        raise SystemExit("release timestamp must be UTC YYYYMMDDTHHMMSSZ")
    return value, instant.strftime("%Y-%m-%d %H:%M:%S UTC")


def _published(campaign, pair_id, pd, out, record):
    manifest = out / "manifest.json"
    if not manifest.is_file() or json.loads(manifest.read_text()) != record:
        raise SystemExit("release pointer disagrees with its authoritative manifest")
    for name, digest in record["sha256"].items():
        path = out / name
        if not path.is_file() or _digest(path) != digest:
            raise SystemExit(f"dated release changed or missing: {path}; refusing to overwrite it")
    from .thread import _atomic_write
    provenance = pd / "release-records" / (record["timestamp"] + ".json")
    if not provenance.is_file():
        raise SystemExit("dated release provenance is missing")
    _atomic_write(pd / "provenance.json", provenance.read_bytes())
    # Compatibility aliases are refreshed only from the verified authoritative artifacts.
    for source, target in ((record["tex"], "paper.tex"), (record["pdf"], "paper.pdf"),
                           ("references.bib", "references.bib")):
        shutil.copyfile(out / source, out.parent / target)
    _atomic_write(out.parent / "release.json", (json.dumps(record, indent=2) + "\n").encode())
    paper._set(campaign, pair_id, status="RELEASED", release_sha256=record["sha256"][record["tex"]],
               released=record["timestamp_utc"], release_manifest=str((out / "manifest.json").relative_to(pd)),
               reason="released: " + str((out / record["pdf"]).relative_to(campaign.thread_dir(pair_id))))
    return {"status": "RELEASED", "path": str((out / record["pdf"]).relative_to(campaign.root)),
            "timestamp": record["timestamp"], "keys": record["keys"], "pointers": record["pointers"]}


def run(campaign, pair_id: str, timestamp: str | None = None) -> dict:
    pd = paper.folder(campaign, pair_id)
    if not pd.is_dir():
        raise SystemExit(f"{pair_id}: no cleared publication")
    with (pd / ".release.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _run(campaign, pair_id, timestamp)


def _run(campaign, pair_id: str, timestamp: str | None = None) -> dict:
    s = paper.status(campaign, pair_id)
    if s.get("status") not in ("CLEARED", "RELEASED"):
        raise SystemExit(f"{pair_id}: the paper is {s.get('status')}, not CLEARED; run `pathfinder present {pair_id}`")
    src = presentation.final(campaign, pair_id)
    if src is None or not src.is_file() or presentation.sha(src.read_text()) != s.get("cleared_sha256"):
        raise SystemExit(f"{pair_id}: the cleared manuscript changed since clearance (or is missing); run the "
                         f"presentation pass again: `pathfinder present {pair_id} --restart`")
    if not shutil.which("pdftotext"):
        raise SystemExit("pdftotext is needed for the leak check on the PDF text")
    pd = paper.folder(campaign, pair_id)
    rel = (campaign.raw or {}).get("release") or {}
    tex, pointers = strip_comments(src.read_text())
    bib = "\n".join(l for l in (src.parent / "references.bib").read_text().splitlines() if not l.lstrip().startswith("%")) + "\n"
    acknowledgement = disclosure(campaign, pair_id, bib)
    inputs = presentation.sha(json.dumps({"tex": tex, "bib": bib, "acknowledgement": acknowledgement,
                                          "author": rel.get("author", ""), "policy": "dated-release-v1"}, sort_keys=True))
    target = pd / "release"
    target.mkdir(exist_ok=True)
    current = target / "release.json"
    if current.exists():
        previous = json.loads(current.read_text())
        if previous["input_sha256"] == inputs and timestamp in (None, previous["timestamp"]):
            return _published(campaign, pair_id, pd, target / previous["timestamp"], previous)
    attempt = pd / "release-attempt.json"
    pending = json.loads(attempt.read_text()) if attempt.exists() else {}
    if timestamp is None and pending.get("input_sha256") == inputs:
        timestamp = pending["timestamp"]
    stamp, label = _stamp(timestamp)
    out = target / stamp
    tex = _add_disclosure(_preamble(tex, rel.get("author", ""), "Released " + label), acknowledgement)
    mapping = new_keys(bib)
    tex, bib = _rename(tex, bib, mapping)
    texname, pdfname = f"paper-{stamp}.tex", f"paper-{stamp}.pdf"
    intent = {"policy": "dated-release-v1", "timestamp": stamp, "timestamp_utc": label, "input_sha256": inputs}
    if out.exists():
        old_intent = out / "intent.json"
        if not old_intent.exists() or json.loads(old_intent.read_text()) != intent:
            raise SystemExit(f"release timestamp already used: {stamp}; choose a different --timestamp")
        if (out / "manifest.json").exists():
            return _published(campaign, pair_id, pd, out, json.loads((out / "manifest.json").read_text()))
    out.mkdir(exist_ok=True)
    from .pce import _write
    _write(out, "intent.json", json.dumps(intent, indent=2) + "\n", immutable=True)
    _write(out, texname, tex, immutable=True)
    _write(out, "references.bib", bib, immutable=True)
    _write(pd, "release-attempt.json", json.dumps(intent, indent=2) + "\n")
    provenance = {"source": src.relative_to(campaign.thread_dir(pair_id)).as_posix(),
                  "sha256": s.get("cleared_sha256"), "timestamp": stamp, "keys": mapping, "pointers": pointers}
    records = pd / "release-records"
    _write(records, stamp + ".json", json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", immutable=True)
    ok, log = paper.build(out, main=texname)
    if not ok:
        raise SystemExit(f"{pair_id}: the release copy does not build:\n{log}")
    undefined = [l for l in log.splitlines() if "undefined" in l.lower() and ("Citation" in l or "Reference" in l)]
    extracted = subprocess.run(["pdftotext", str(out / pdfname), "-"], capture_output=True, text=True)
    if extracted.returncode:
        raise SystemExit(f"{pair_id}: PDF text extraction failed; release not validated")
    hits = leak_check(campaign, tex, extracted.stdout) + [f"build: {u}" for u in undefined]
    if "Released " + label not in " ".join(extracted.stdout.split()):
        hits.append("fixed UTC release date is not visible in the PDF")
    if hits:
        raise SystemExit(f"{pair_id}: leak check failed, the paper stays CLEARED:\n" + "\n".join(hits))
    from . import provenance as engine_provenance
    record = {**intent, "engine": engine_provenance.engine(), "tex": texname, "pdf": pdfname, "keys": len(mapping), "pointers": len(pointers),
              "cleared_sha256": s.get("cleared_sha256"),
              "sha256": {name: _digest(out / name) for name in (texname, pdfname, "references.bib")}}
    _write(out, "manifest.json", json.dumps(record, indent=2) + "\n", immutable=True)
    _write(pd, "provenance.json", json.dumps(provenance, indent=2, ensure_ascii=False) + "\n")
    return _published(campaign, pair_id, pd, out, record)

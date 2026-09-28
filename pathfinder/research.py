"""One research thread: peers on a shared ledger, consolidate, verify, up to `rounds` rounds."""
from __future__ import annotations
import hashlib, json, os, re, shutil, sys, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import corpus, transport
from .ledger import Ledger
from .scan import prompts_dir, parse_json
from .admission import Refused

PEERS = ("ada", "emmy")                      # the default; a campaign may name more in campaign.json
TERMINAL = {"DRAFT", "PAUSE", "PAUSE-ON-ITERATE", "PAUSE-ON-REVISE"}


class Stopped(Exception):
    pass


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _atomic_write(path: Path, data: bytes):
    """Publish a complete file; an interrupted replacement preserves the previous version."""
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def status(campaign, pair_id) -> dict:
    p = campaign.thread_dir(pair_id) / "status.json"
    return json.loads(p.read_text()) if p.exists() else {"pair_id": pair_id, "round": 0, "stage": "peers", "status": "new"}


def _set(campaign, pair_id, **kw):
    s = status(campaign, pair_id); s.update(kw, updated=_now())
    _atomic_write(campaign.thread_dir(pair_id) / "status.json", json.dumps(s, indent=1).encode())
    return s


def _pair(campaign, pair_id):
    i, j = (int(x) for x in pair_id[1:].split("P"))
    return corpus.read(campaign.path("Q.jsonl"))[i - 1], corpus.read(campaign.path("P.jsonl"))[j - 1]


def prepare(campaign, pair_id: str) -> Path:
    d = campaign.thread_dir(pair_id)
    if (d / "status.json").exists():
        return d
    (d / "inputs").mkdir(parents=True, exist_ok=True)
    for side, row in zip("QP", _pair(campaign, pair_id)):
        src = campaign.path(row["text"]) if row.get("text") else None
        if src and src.exists():
            shutil.copy(src, d / "inputs" / f"{side}{src.suffix}")
        else:
            (d / "inputs" / f"{side}.txt").write_text(f"Title: {row['title']}\n\nAbstract: {row['abstract']}\n")
        (d / "inputs" / f"{side}.json").write_text(json.dumps(row, indent=1))
    for a in campaign.peers:
        (d / a).mkdir(exist_ok=True)
    _set(campaign, pair_id, round=1, stage="peers", status="running", reason=None, started=_now())
    return d


def thread_head(d, inp, papers: bool = True, ledger: bool = True) -> str:
    """The static head of a call in a thread: the two papers, then the ledger as it stands, each optional.
    The same bytes for every caller that gets it, and across calls a prefix of the previous call's, since
    the ledger only grows; a prompt cache serves everything but what the ledger gained since. Whatever
    differs between callers goes after it."""
    parts = []
    if papers:
        parts.append("## " + inp["Q"] + "\n\n" + (d / "inputs" / inp["Q"]).read_text(errors="replace"))
        parts.append("## " + inp["P"] + "\n\n" + (d / "inputs" / inp["P"]).read_text(errors="replace"))
    if ledger:
        parts.append("## ledger.jsonl\n\n" + ((d / "ledger.jsonl").read_text() if (d / "ledger.jsonl").exists() else ""))
    return "\n\n".join(parts)


def judge_head(d, inp, note_name: str) -> str:
    """The thread head plus the note, for the verifier and the paper reviewer."""
    return thread_head(d, inp) + "\n\n## " + note_name + "\n\n" + (d / note_name).read_text(errors="replace")


class EvidenceUnavailable(Exception):
    """Evidence a tool-less stage needs cannot be supplied inline; the thread blocks before any call."""


EVIDENCE_PATH = re.compile(r"(?<![\w:/@.-])(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]+")
EVIDENCE_MAX_BYTES = 300_000


def _evidence_references(text: str) -> list[str]:
    """Relative file paths cited in ledger text; DOIs and scholarly figure locators are citations, not files."""
    return [name for name in EVIDENCE_PATH.findall(text)
            if not re.match(r"10\.\d{4,9}/", name) and not re.search(r"/Fig\.\d+$", name)]


def _assessment_evidence(campaign, d) -> str:
    """Everything the tool-less consolidator and verifier are told is complete: every file in each peer's
    directory, and every file the ledger cites by relative path, inlined under its path.

    A cited path that leaves the thread, goes through a symlink or uses '..' always blocks the thread
    (EvidenceUnavailable): inlining it could read another investigation. With "strict_evidence": true in
    campaign.json a cited file that is missing, unreadable, not UTF-8 text or larger than
    "evidence_max_bytes" also blocks; otherwise readable binary or oversized files are listed with
    size and digest, while missing or unreadable files are explicitly named as unavailable."""
    strict = bool(campaign.raw.get("strict_evidence"))
    limit = int(campaign.raw.get("evidence_max_bytes", EVIDENCE_MAX_BYTES))
    paths = {p for actor in campaign.peers for p in (d / actor).rglob("*") if p.is_file() or p.is_symlink()}
    ledger = d / "ledger.jsonl"
    for name in _evidence_references(ledger.read_text(errors="replace") if ledger.exists() else ""):
        paths.add(d / name)
    parts = []
    for path in sorted(paths):
        relative = path.relative_to(d)
        if ".." in relative.parts or any((d / parent).is_symlink() for parent in (relative, *relative.parents)):
            raise EvidenceUnavailable(f"aliased evidence path: {relative}")
        if path.exists() and not path.resolve().is_relative_to(d.resolve()):
            raise EvidenceUnavailable(f"evidence outside the investigation: {relative}")
        if not path.is_file():
            if strict:
                raise EvidenceUnavailable(f"missing evidence: {relative}")
            parts.append(f"## {relative}\n\n(cited in the ledger; no such file)")
            continue
        try:
            data = path.read_bytes()
        except OSError as error:
            if strict:
                raise EvidenceUnavailable(f"unreadable evidence: {relative}: {error}") from error
            parts.append(f"## {relative}\n\n(not inlined: unreadable file: {error})")
            continue
        try:
            if len(data) > limit:
                raise UnicodeError(f"{len(data)} bytes, over the {limit}-byte inline limit")
            text = data.decode("utf-8")
        except UnicodeError as error:
            if strict:
                raise EvidenceUnavailable(f"evidence not inlinable as text: {relative}: {error}") from error
            parts.append(f"## {relative}\n\n(not inlined: {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()})")
            continue
        parts.append(f"## {relative}\n\n{text}")
    return "\n\n".join(parts)


def _consolidate_prompt(campaign, d, inp, pair_id, why, note_name, prior) -> str:
    """@planks("When Pathfinder requests consolidation from the direct provider")
    @planks("When Pathfinder builds its consolidation model request")
    @planks("Then the request states that its inline evidence is complete and no tools are available")
    """
    in_papers = True
    in_ledger = True
    above = [x for x, on in (("Q and P", in_papers), ("the ledger", in_ledger)) if on]
    read = [x for x, on in ((f"inputs/{inp['Q']} and inputs/{inp['P']}", not in_papers), ("ledger.jsonl", not in_ledger)) if on]
    material = (f"{' and '.join(above)} are above. " if above else "") + (f"Read {', '.join(read)} and the peers' directories beside you."
                                                                          if read else "Inline evidence is complete and no tools are available.")
    head = thread_head(d, inp, in_papers, in_ledger)
    if (d / note_name).exists():                    # the account a repair or a next round must keep
        head += "\n\n## " + note_name + "\n\n" + (d / note_name).read_text(errors="replace")
    evidence = _assessment_evidence(campaign, d)
    head += ("\n\n" + evidence if evidence else "") + "\n\n## your task\n\n"
    return head + _prompt(campaign, "consolidate", ACTOR=campaign.peers[0], WHY=why, NOTE=note_name, NOTE_STEM=pair_id, PRIOR=prior, MATERIAL=material) + "\n\nReturn the complete research account in the response.\n"


def unfence(text: str) -> str:
    """The LaTeX document inside a reply that wrapped it in a Markdown code block; other text unchanged."""
    if text.lstrip().startswith("\\documentclass"):
        return text
    m = re.search(r"```[A-Za-z]*[ \t]*\n(.*?\\end\{document\})\s*\n```", text, re.S)
    return m.group(1).strip() + "\n" if m and "\\documentclass" in m.group(1) else text


def is_latex_document(text: str) -> bool:
    return "\\documentclass" in text and "\\begin{document}" in text


def _tex_escape(t: str) -> str:
    return "".join({"&": "\\&", "%": "\\%", "$": "\\$", "#": "\\#", "_": "\\_", "{": "\\{", "}": "\\}", "~": "\\textasciitilde{}", "^": "\\textasciicircum{}"}.get(c, c) for c in t)


def paper_meta(d: Path) -> dict:
    """Q_ID, Q_TITLE, P_ID, P_TITLE from the thread's inputs, TeX-escaped, for the document prompts:
    every document opens with the two titles linked to their arXiv abstracts."""
    out = {}
    for side in "QP":
        m = json.loads((d / "inputs" / f"{side}.json").read_text())
        out[f"{side}_ID"] = m.get("id", ""); out[f"{side}_TITLE"] = _tex_escape(m.get("title", ""))
    return out


def status_line(campaign, pair_id: str) -> str:
    """Where the thread stands, for the title block: ending or round, and how many ITERATE and REVISE so far."""
    d = campaign.thread_dir(pair_id); s = status(campaign, pair_id)
    v = json.loads((d / f"{pair_id}.verdict.json").read_text()) if (d / f"{pair_id}.verdict.json").exists() else []
    it, rv = sum(x.get("decision") == "ITERATE" for x in v), sum(x.get("decision") == "REVISE" for x in v)
    st = s.get("status", "new"); rnd = s.get("round", 1)
    rounds = f"{rnd} round{'s' if rnd != 1 else ''}"
    where = f"{st} after {rounds}" if st in TERMINAL else f"round {rnd}, verification pending"
    return f"Research phase: {where}, {it} ITERATE, {rv} REVISE"


def write_meta(campaign, pair_id: str, where: Path, extra: str = "", date: str | None = None) -> Path:
    """pathfinder-meta.tex beside a document: the style reads it, so every document opens with the pair,
    the two papers linked to arXiv, the date of production and the thread's state, none of it typed by an agent."""
    m = paper_meta(campaign.thread_dir(pair_id)); line = status_line(campaign, pair_id) + (f". Edit phase: {extra}" if extra else "")
    t = (f"\\pathfinderpair{{{pair_id}}}\n\\date{{{date or time.strftime('%Y-%m-%d')}}}\n"
         f"\\pathfinderpapers{{{m['Q_ID']}}}{{{m['Q_TITLE']}}}{{{m['P_ID']}}}{{{m['P_TITLE']}}}\n"
         f"\\pathfinderstatus{{{_tex_escape(line)}}}\n")
    if campaign.raw.get("pair_kind") == "paper-strategy":
        # The strategy dossier is not an arXiv paper. Its provenance belongs
        # in the introduction and bibliography, not a fabricated arXiv link.
        t = "\n".join(line for line in t.splitlines()
                      if not line.startswith("\\pathfinderpapers")) + "\n"
    where.mkdir(exist_ok=True); (where / "pathfinder-meta.tex").write_text(t); return where / "pathfinder-meta.tex"


def _inputs(d: Path) -> dict:
    return {s: next(p for p in (d / "inputs").iterdir() if p.stem == s and p.suffix != ".json").name for s in "QP"}


def _prompt(campaign, name, **vars):
    from . import resources
    vars.setdefault("DATE", time.strftime("%Y-%m-%d"))          # every document bears its date of production
    return resources.prompt(campaign, name, **vars)


def _check(stop):
    if stop():
        raise Stopped()


def _scan_row(campaign, pair_id) -> dict:
    p = campaign.path("scan.jsonl")
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip() and json.loads(line).get("pair_id") == pair_id:
                return json.loads(line)
    return {}


def _peers(campaign, pair_id, stop):
    """@planks("When Pathfinder executes scan, peer, consolidation, and verification model requests")
    @planks("When Pathfinder executes one stage attempt")
    @planks("When Pathfinder executes one peer stage attempt")
    @planks("When Pathfinder verifies execution routing")
    """
    d, L = campaign.thread_dir(pair_id), Ledger(campaign.thread_dir(pair_id) / "ledger.jsonl")
    A = campaign.allowances; inp = _inputs(d); row = _scan_row(campaign, pair_id)
    helper = f"{sys.executable} -m pathfinder.ledger --root ."
    used = {"seconds": 0.0}; lock = threading.Lock()

    peers = list(campaign.peers)

    def one(actor):
        others = [a for a in peers if a != actor]
        for call_no in range(A["peer_calls"]):
            with lock:
                left = A["peer_seconds"] - used["seconds"]
            if left <= 0 or L.ready(peers):
                return
            while L.ready([actor]) and not all(done[o] for o in others):   # my word stands; wait for my partners
                time.sleep(15)
                if L.ready(peers):
                    return
            if L.ready(peers):
                return
            _check(stop)
            # two independent switches, both off by default: the agent reads what it needs through tools
            in_papers, in_ledger = bool(campaign.raw.get("inline_papers")), bool(campaign.raw.get("inline_ledger"))
            last = L.count() if in_ledger else 0                  # where the agent's own reading of the ledger starts
            material = (("Q and P are above" if in_papers else f"Read inputs/{inp['Q']} and inputs/{inp['P']}")
                        + (f"; the ledger as it stood when this call began is above too, ending at entry {last}."
                           if in_ledger else ", then the ledger with the read command below.")
                        + (f" The files are inputs/{inp['Q']}, inputs/{inp['P']} and ledger.jsonl if you need to quote by line." if in_papers or in_ledger else ""))
            p = (thread_head(d, inp, in_papers, in_ledger) + "\n\n## your task\n\n") if (in_papers or in_ledger) else ""
            p += _prompt(campaign, "peer", ACTOR=actor, PEERS=" and ".join(others), Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}",
                        MATERIAL=material, LEDGER=f"{helper} --actor {actor}", LAST_SEQ=last, SECONDS=int(min(left, 1200)),
                        CALLS_LEFT=A["peer_calls"] - call_no - 1, FEASIBILITY=row.get("feasibility", "?"),
                        GAIN=row.get("gain", "?"), CONNEXION=row.get("connexion") or "none recorded.",
                        RATIONALE=row.get("rationale") or "none recorded.")
            if call_no or L.count():
                p += "\n\nThis call continues an existing thread. Start by reading the ledger, then carry on from where it stands.\n"
            r = transport.execute(campaign, transport.ModelRequest(
                identity=f"{pair_id}:peer:{actor}:{call_no}", prompt=p, model=campaign.peer_model(actor), tools=True,
                search=campaign.peer_search, cwd=d, timeout=int(min(left, 1200)) + 30, thread=pair_id,
                stage="peer", actor=actor,
            ))
            with lock:
                used["seconds"] += r["seconds"]
            if r["transport_failed"]:
                raise transport.TransportFailed(pair_id)

    done = {a: False for a in peers}

    def guarded(actor):
        try:
            one(actor)
        finally:
            done[actor] = True

    with ThreadPoolExecutor(len(peers)) as ex:
        for f in [ex.submit(guarded, a) for a in peers]:
            f.result()


def _stage_call(campaign, pair_id, stage, prompt, tools, seconds, done=lambda: False):
    """@planks("When Pathfinder consolidates a frozen paper pair")
    @planks("When Pathfinder verifies the frozen paper pair")
    @planks("When Pathfinder consolidates pair \"Q1P1\"")
    @planks("When Pathfinder evaluates the consolidation attempt")
    @planks("When Pathfinder consolidates the frozen paper pair")
    @planks("When Pathfinder runs the assigned comparison workflow")
    @planks("When Pathfinder executes scan, peer, consolidation, and verification model requests")
    @planks("When Pathfinder executes one stage attempt")
    @planks("When Pathfinder verifies execution routing")

    Run consolidate or verify for up to "stage_attempts" attempts (default 2). A reply that failed in
    transport raises TransportFailed (the thread stops, resumable). A reply carrying an error is not an
    answer: consolidation tries again, and a verifier reply with an error raises TransportFailed rather
    than being read as a verdict. An empty consolidation reply is retried.
    """
    d = campaign.thread_dir(pair_id)
    for attempt in range(_stage_attempts(campaign)):
        r = transport.execute(campaign, transport.ModelRequest(
            identity=f"{pair_id}:{stage}:{attempt}", prompt=prompt, model=campaign.model, tools=tools,
            search=False, cwd=d, timeout=seconds, thread=pair_id, stage=stage,
            actor=campaign.peers[0] if stage == "consolidate" else "verifier",
        ))
        if r["transport_failed"]:
            raise transport.TransportFailed(pair_id)
        if r.get("error"):
            if stage == "consolidate":
                continue
            raise transport.TransportFailed(pair_id)
        if done() or (r["text"].strip() and not tools):
            return r
    return r


def _stage_attempts(campaign) -> int:
    attempts = campaign.raw.get("stage_attempts", 2)
    if type(attempts) is not int or attempts < 1:
        raise ValueError("stage_attempts must be a positive integer")
    return attempts


def run_thread(campaign, pair_id: str, stop=lambda: False) -> str:
    """@planks("When the findings are consolidated into a research account")
    @planks("When the peer stage finishes")
    @planks("When the verifier returns \"DRAFT\"")
    @planks("When the verifier returns \"ITERATE\" with an unanswered question")
    @planks("When the verifier returns \"ITERATE\"")
    @planks("When the verifier returns \"REVISE\" with a correction")
    @planks("When the verifier returns \"REVISE\"")
    @planks("When the campaign continues")
    @planks("When the provider returns a research account for pair \"Q1P1\"")
    @planks("When both consolidation attempts produce no stored research account")
    @planks("When the direct provider returns a complete research account on its consolidation retry")
    @planks("When Pathfinder runs consolidation through the campaign workflow")
    @planks("When the verification path to that request is inspected")
    """
    _stage_attempts(campaign)                   # an invalid setting fails before any call
    d = prepare(campaign, pair_id); L = Ledger(d / "ledger.jsonl"); A = campaign.allowances
    note, verdicts = d / f"{pair_id}.tex", d / f"{pair_id}.verdict.json"
    inp = _inputs(d)
    try:
        while True:
            s = status(campaign, pair_id)
            if s["status"] in TERMINAL:
                return s["status"]
            _set(campaign, pair_id, status="running")
            if s["stage"] == "peers":
                _check(stop); _peers(campaign, pair_id, stop)
                if L.latest_substantive() == 0:
                    _set(campaign, pair_id, stage="done", status="PAUSE", reason="empty ledger"); return "PAUSE"
                _set(campaign, pair_id, stage="consolidate")
            elif s["stage"] == "consolidate":
                _check(stop)
                why = "" if L.ready(list(campaign.peers)) else " because the allowance ran out before every peer declared ready"
                repair = s.get("repair")
                if repair:
                    prior = (f" This is a repair of the existing {note.name}, not new research. An independent verifier found"
                             f" these defects: {repair.get('reason')} Corrections: {repair.get('action')} Correct them, keep every"
                             " result the verifier accepted, and do not open new directions.")
                elif note.exists():
                    prior = (f" A previous round wrote {note.name} and the verifier returned ITERATE on it; keep every result"
                             " of that note that still stands and append this round's work to it, rather than rewriting from"
                             " scratch. The verifier's review is the latest review entry in the ledger.")
                else:
                    prior = ""
                write_meta(campaign, pair_id, d)                     # the note's title block: pair, papers, date, state
                # every accepted consolidation reply is kept per round and repair, so a restart applies it
                # without paying for it again; the returned text always becomes the account
                response = d / "consolidation" / f"round-{s['round']}-repair-{s.get('repairs', 0)}.json"
                if response.exists():
                    try:
                        text = json.loads(response.read_text())["text"]
                        if not isinstance(text, str) or not is_latex_document(text):
                            raise ValueError("retained text is not a LaTeX document")
                    except (OSError, ValueError, KeyError, TypeError) as error:
                        _set(campaign, pair_id, status="BLOCKED", reason=f"consolidate: invalid retained response: {error}")
                        return "BLOCKED"
                else:
                    r = _stage_call(campaign, pair_id, "consolidate",
                                    _consolidate_prompt(campaign, d, inp, pair_id, why, note.name, prior),
                                    False, A["consolidate_seconds"])
                    text = unfence(r["text"] or "")
                    if r.get("error") or not text.strip():   # never re-verify the older account as if repaired
                        _set(campaign, pair_id, status="BLOCKED", reason=f"consolidate: {r.get('error') or 'no note'}"); return "BLOCKED"
                    if not is_latex_document(text):                # e.g. a quota message returned as the reply
                        (d / "consolidate-unreadable.txt").write_text(r["text"])     # keep the paid reply for inspection
                        _set(campaign, pair_id, status="BLOCKED", reason="consolidate: reply is not a LaTeX document"); return "BLOCKED"
                    response.parent.mkdir(exist_ok=True)
                    _atomic_write(response, json.dumps({"text": text, "session": r.get("session"), "at": _now(),
                                                       "run_id": getattr(campaign, "run_id", None)}).encode())
                if note.exists():                                    # archive the account being replaced
                    previous = note.read_bytes()
                    version = d / "account-versions" / f"{hashlib.sha256(previous).hexdigest()}.tex"
                    version.parent.mkdir(exist_ok=True)
                    if not version.exists():
                        _atomic_write(version, previous)
                _atomic_write(note, text.encode())
                _set(campaign, pair_id, stage="verify", repair=None)
            elif s["stage"] == "verify":
                _check(stop)
                # static material first, the instruction last: the head is shared with every other judge call
                evidence = _assessment_evidence(campaign, d)
                p = judge_head(d, inp, note.name) + ("\n\n" + evidence if evidence else "") + "\n\n## your task\n\n"
                p += _prompt(campaign, "verify", Q_INPUT=f"inputs/{inp['Q']}", P_INPUT=f"inputs/{inp['P']}", NOTE=note.name)
                r = _stage_call(campaign, pair_id, "verify", p, False, A["verify_seconds"], done=lambda: True)
                try:
                    v = parse_json(r["text"]); dec = v["decision"].upper()
                    assert dec in ("DRAFT", "REVISE", "ITERATE", "PAUSE")
                except Exception as e:
                    (d / "verify-unreadable.txt").write_text(r["text"] or "")     # keep the paid reply for inspection
                    _set(campaign, pair_id, status="BLOCKED", reason=f"verify: unreadable decision ({e})"); return "BLOCKED"
                hist = json.loads(verdicts.read_text()) if verdicts.exists() else []
                hist.append({"round": s["round"], "at": _now(), "note_sha256": hashlib.sha256(note.read_bytes()).hexdigest(), **v})
                verdicts.write_text(json.dumps(hist, indent=1))
                write_meta(campaign, pair_id, d)                     # the state on the note follows the verdicts
                repairs = s.get("repairs", 0)
                if dec == "REVISE" and repairs < campaign.raw.get("repairs", 1):
                    L.add("verifier", "review", f"REVISE: {v.get('reason')} Corrections: {v.get('action')}")
                    _set(campaign, pair_id, stage="consolidate", repairs=repairs + 1, repair=v, reason=v.get("reason"))
                elif dec == "ITERATE" and s["round"] < campaign.rounds:
                    L.add("verifier", "review", f"ITERATE: {v.get('reason')} Action: {v.get('action')}")
                    _set(campaign, pair_id, stage="peers", round=s["round"] + 1, reason=v.get("reason"))
                else:
                    final = {"ITERATE": "PAUSE-ON-ITERATE", "REVISE": "PAUSE-ON-REVISE"}.get(dec, dec)
                    _set(campaign, pair_id, stage="done", status=final, reason=v.get("reason")); write_meta(campaign, pair_id, d); return final
    except EvidenceUnavailable as error:
        _set(campaign, pair_id, status="BLOCKED", reason=f"evidence: {error}"); return "BLOCKED"
    except (Stopped, Refused):
        _set(campaign, pair_id, status="stopped"); return "stopped"
    except transport.TransportFailed:
        _set(campaign, pair_id, status="stopped", reason="transport failed"); raise

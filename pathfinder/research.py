"""One research thread: peers on a shared ledger, consolidate, verify, up to `rounds` rounds."""
from __future__ import annotations
import hashlib, json, re, shutil, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
from dataclasses import asdict
from . import corpus, transport
from .ledger import Ledger
from .scan import prompts_dir, parse_json

PEERS = ("ada", "emmy")                      # the default; a campaign may name more in campaign.json
TERMINAL = {"DRAFT", "PAUSE", "PAUSE-ON-ITERATE", "PAUSE-ON-REVISE"}


class Stopped(Exception):
    pass


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def status(campaign, pair_id) -> dict:
    p = campaign.thread_dir(pair_id) / "status.json"
    return json.loads(p.read_text()) if p.exists() else {"pair_id": pair_id, "round": 0, "stage": "peers", "status": "new"}


def _set(campaign, pair_id, **kw):
    s = status(campaign, pair_id); s.update(kw, updated=_now())
    (campaign.thread_dir(pair_id) / "status.json").write_text(json.dumps(s, indent=1))
    return s


def _pair(campaign, pair_id):
    i, j = (int(x) for x in pair_id[1:].split("P"))
    return corpus.read(campaign.path("Q.jsonl"))[i - 1], corpus.read(campaign.path("P.jsonl"))[j - 1]


def prepare(campaign, pair_id: str) -> Path:
    """@planks("the standard research entry point opens the investigation")"""
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
    imported = campaign.raw.get("research_scheme") == "eva_minus" and campaign.raw.get("imported_research", False)
    _set(campaign, pair_id, round=0 if imported else 1,
         stage="ledger_review" if imported else "peers", status="running", reason=None, started=_now())
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


class EvidenceUnavailable(Exception):
    """@planks("Then the assessment is blocked before a provider call with the unreadable evidence identified")"""


def _external_citations(d):
    """@planks("Vera receives the ledger and its external citation declaration")
    @planks("research blocks before provider dispatch because the citation binding is stale")
    @planks("the joint researcher receives the citation URL and unavailable status")
    """
    declaration = d / "external-references.json"
    if declaration.is_symlink():
        raise EvidenceUnavailable("Aliased evidence declaration: external-references.json")
    if not declaration.exists():
        return None, set()
    try:
        content = declaration.read_text()
        data = json.loads(content)
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("references"), list):
            raise ValueError("external-references.json requires version 1 and a references array")
        citations = set()
        for record in data["references"]:
            if not isinstance(record, dict):
                raise ValueError("external citation must be a record")
            for field in ("document", "path"):
                name = record[field]
                if not isinstance(name, str) or not name or Path(name).is_absolute() or ".." in Path(name).parts:
                    raise ValueError(f"Unsafe external citation {field}: {name}")
            document = Path(record["document"])
            if any((d / parent).is_symlink() for parent in (document, *document.parents)):
                raise ValueError(f"Aliased external citation document: {document}")
            url = urlsplit(record["url"])
            if url.scheme not in ("http", "https") or not url.netloc or record["status"] not in ("external", "unavailable"):
                raise ValueError("external citation requires an absolute HTTP(S) URL and availability status")
            bound = (d / document).read_bytes()
            seq = None
            if str(document) == "ledger.jsonl":
                seq = record["ledger_seq"]
                if type(seq) is not int:
                    raise ValueError("ledger.jsonl citation requires an integer ledger_seq")
                rows = [json.loads(line) for line in bound.decode("utf-8").splitlines() if line.strip()]
                matches = [row for row in rows if row["seq"] == seq]
                if len(matches) != 1:
                    raise ValueError(f"Stale citation binding: ledger.jsonl entry {seq}")
                bound = matches[0]["text"].encode("utf-8")
            if hashlib.sha256(bound).hexdigest() != record["text_sha256"]:
                raise ValueError(f"Stale citation binding: {document}")
            if record["path"] not in bound.decode("utf-8"):
                raise ValueError(f"Citation path absent from bound text: {document}")
            citations.add((str(document), seq, record["path"]))
        return content, citations
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        raise EvidenceUnavailable(f"Invalid external citation declaration: {error}") from error


def _assessment_evidence(d, peers, references=None):
    """@planks("the request contains the complete calculation evidence with its source paths")
    @planks("the request contains the complete prior account and peer artefact contents")
    @planks("the request contains the complete current account and peer artefact contents")
    @planks("the assessment is blocked before a provider call with the unreadable evidence identified")
    @planks("the assessment is blocked before reading outside evidence or calling a provider")
    @planks("the assessment is blocked before reading the aliased evidence or calling a provider")
    @planks("the workflow prepares tool-less consolidation and verification requests")
    @planks("the scholarly figure locator is not read as a local file")
    @planks("Vera receives the ledger and its external citation declaration")
    @planks("research blocks before provider dispatch and identifies \"{path}\"")
    @planks("research blocks before reading the aliased citation file")
    @planks("the external citation is resolved only in its originating branch namespace")
    """
    paths = {p for actor in peers for p in (d / actor).rglob("*") if p.is_file()}
    declaration, citations = _external_citations(d)
    # Present declared files retain ordinary read and alias checks.
    for _, _, name in citations:
        relative = Path(name)
        path = d / relative
        if path.exists() or any((d / parent).is_symlink() for parent in (relative, *relative.parents)):
            paths.add(path)
    ledger = d / "ledger.jsonl"
    if references is None:
        references = ledger.read_text() if ledger.exists() else ""
    # Exempt only the declared entry; another entry may require the same path locally.
    for line in references.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        for name in re.findall(r"(?<![\w:/@.-])(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9]+", row["text"]):
            if re.match(r"10\.\d{4,9}/", name) or re.search(r"/Fig\.\d+$", name):
                continue
            if ("ledger.jsonl", row["seq"], name) not in citations:
                paths.add(d / name)
    parts = ["## external-references.json\n\n" + declaration] if declaration is not None else []
    for path in sorted(paths):
        relative = path.relative_to(d)
        if ".." in relative.parts or any((d / parent).is_symlink() for parent in (relative, *relative.parents)):
            raise EvidenceUnavailable(f"Aliased evidence path: {relative}")
        if not path.resolve().is_relative_to(d.resolve()):
            raise EvidenceUnavailable(f"Evidence outside investigation: {path.relative_to(d)}")
        try:
            content = path.read_text()
        except (OSError, UnicodeError) as error:
            raise EvidenceUnavailable(f"Unreadable evidence {path.relative_to(d)}: {error}") from error
        parts.append(f"## {path.relative_to(d)}\n\n{content}")
    return "\n\n".join(parts)


def _stage_attempts(campaign):
    """@planks("Given a campaign sets \"stage_attempts\" to 1")
    @planks("Given a campaign omits \"stage_attempts\"")
    @planks("Then configuration validation fails before any provider call")
    """
    attempts = campaign.raw.get("stage_attempts", 2)
    if type(attempts) is not int or attempts < 1:
        raise ValueError("stage_attempts must be a positive integer")
    return attempts


def judge_head(d, inp, note_name: str) -> str:
    """The thread head plus the note, for the verifier and the paper reviewer."""
    return thread_head(d, inp) + "\n\n## " + note_name + "\n\n" + (d / note_name).read_text(errors="replace")


def _consolidate_prompt(campaign, d, inp, pair_id, why, note_name, prior) -> str:
    """@planks("When Pathfinder requests consolidation from the direct provider")
    @planks("When Pathfinder builds its consolidation model request")
    @planks("Then the request states that its inline evidence is complete and no tools are available")
    @planks("When the research workflow prepares its consolidation request")
    """
    in_papers = True
    in_ledger = True
    above = [x for x, on in (("Q and P", in_papers), ("the ledger", in_ledger)) if on]
    read = [x for x, on in ((f"inputs/{inp['Q']} and inputs/{inp['P']}", not in_papers), ("ledger.jsonl", not in_ledger)) if on]
    material = (f"{' and '.join(above)} are above. " if above else "") + (f"Read {', '.join(read)} and the peers' directories beside you."
                                                                          if read else "Inline evidence is complete and no tools are available.")
    head = thread_head(d, inp, in_papers, in_ledger)
    if (d / note_name).exists():
        head += "\n\n## " + note_name + "\n\n" + (d / note_name).read_text()
    head += "\n\n" + _assessment_evidence(d, campaign.peers) + "\n\n## your task\n\n"
    return head + _prompt(campaign, "consolidate", ACTOR=campaign.peers[0], WHY=why, NOTE=note_name, NOTE_STEM=pair_id, PRIOR=prior, MATERIAL=material) + "\n\nReturn the complete research account in the response.\n"


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
    where.mkdir(exist_ok=True); (where / "pathfinder-meta.tex").write_text(t); return where / "pathfinder-meta.tex"


def _inputs(d: Path) -> dict:
    return {s: next(p for p in (d / "inputs").iterdir() if p.stem == s and p.suffix != ".json").name for s in "QP"}


def _prompt(campaign, name, **vars):
    t = (prompts_dir(campaign) / f"{name}.md").read_text()
    vars.setdefault("DATE", time.strftime("%Y-%m-%d"))          # every document bears its date of production
    for k, v in vars.items():
        t = t.replace("{{" + k + "}}", str(v))
    return t


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
                identity=f"{pair_id}:peer:{actor}:{call_no}", prompt=p, model=campaign.model, tools=True,
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

    @planks("When its consolidation response is empty or failed")
    @planks("When its first consolidation response is empty and its next response contains an account")
    @planks("When every fresh repair response reports a provider failure")

    Run a bounded number of stage attempts; accept only successful responses.
    """
    d = campaign.thread_dir(pair_id)
    for attempt in range(_stage_attempts(campaign)):
        r = transport.execute(campaign, transport.ModelRequest(
            identity=f"{pair_id}:{stage}:{attempt}", prompt=prompt, model=campaign.model, tools=tools,
            search=False, cwd=d, timeout=seconds, thread=pair_id, stage=stage,
            actor=campaign.peers[0] if stage == "consolidate" else "verifier",
        ))
        if r["transport_failed"] or r.get("error"):
            if stage == "consolidate":
                continue
            raise transport.TransportFailed(pair_id)
        if done() or (r["text"].strip() and not tools):
            return r
    return r


def run_thread(campaign, pair_id: str, stop=lambda: False) -> str:
    """@planks("the standard research entry point opens the investigation")
    @planks("the findings are consolidated into a research account")
    @planks("the peer stage finishes")
    @planks("the verifier returns \"DRAFT\"")
    @planks("the verifier returns \"ITERATE\" with an unanswered question")
    @planks("the verifier returns \"ITERATE\"")
    @planks("the verifier returns \"REVISE\" with a correction")
    @planks("the verifier returns \"REVISE\"")
    @planks("the campaign continues")
    @planks("the provider returns a research account for pair \"Q1P1\"")
    @planks("both consolidation attempts produce no stored research account")
    @planks("the direct provider returns a complete research account on its consolidation retry")
    @planks("Pathfinder runs consolidation through the campaign workflow")
    @planks("the verification path to that request is inspected")
    @planks("the research workflow receives a nonempty repair account after \"REVISE\"")
    @planks("the research workflow receives a nonempty next-round account after \"ITERATE\"")
    @planks("the interrupted research workflow resumes")
    @planks("every fresh repair response is empty")
    @planks("every fresh repair response reports a provider failure")
    @planks("the research workflow prepares its verification request")
    @planks("the research workflow prepares the assessment request")
    @planks("the research workflow starts")
    @planks("the previous account remains available as an immutable version")
    """
    _stage_attempts(campaign)
    if campaign.raw.get("research_scheme") or campaign.raw.get("research_bundles"):
        return _run_composable(campaign, pair_id, stop)
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
                responses = d / "consolidation"
                response = responses / f"round-{s['round']}-repair-{s.get('repairs', 0)}.json"
                if response.exists():
                    r = json.loads(response.read_text())
                else:
                    r = _stage_call(campaign, pair_id, "consolidate",
                                    _consolidate_prompt(campaign, d, inp, pair_id, why, note.name, prior),
                                    False, A["consolidate_seconds"])
                    if r.get("transport_failed") or r.get("error") or not r["text"].strip():
                        _set(campaign, pair_id, status="BLOCKED", reason=f"consolidate: {r.get('error') or 'no note'}")
                        return "BLOCKED"
                    responses.mkdir(exist_ok=True)
                    response.write_text(json.dumps(r))
                if note.exists():
                    previous = note.read_bytes()
                    versions = d / "account-versions"
                    versions.mkdir(exist_ok=True)
                    version = versions / f"{hashlib.sha256(previous).hexdigest()}.tex"
                    if not version.exists():
                        with version.open("xb") as archive:
                            archive.write(previous)
                note.write_text(r["text"])
                _set(campaign, pair_id, stage="verify", repair=None)
            elif s["stage"] == "verify":
                _check(stop)
                # static material first, the instruction last: the head is shared with every other judge call
                p = judge_head(d, inp, note.name) + "\n\n" + _assessment_evidence(d, campaign.peers) + "\n\n## your task\n\n"
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
        _set(campaign, pair_id, status="BLOCKED", reason=str(error)); return "BLOCKED"
    except Stopped:
        _set(campaign, pair_id, status="stopped"); return "stopped"
    except transport.TransportFailed:
        _set(campaign, pair_id, status="stopped", reason="transport failed"); raise


def _bundle_evidence(campaign, d):
    """@planks("each stage receives all three ledgers and their referenced evidence")
    @planks("it includes those thread-relative bundle directories with their original reference namespaces")
    """
    parts = []
    for name in campaign.raw.get("research_bundles", []):
        root = d / name
        relative = root.relative_to(d)
        if ".." in relative.parts or any((d / parent).is_symlink() for parent in (relative, *relative.parents)):
            raise EvidenceUnavailable(f"Aliased evidence bundle: {name}")
        ledger = root / "ledger.jsonl"
        if ledger.is_symlink():
            raise EvidenceUnavailable(f"Aliased evidence ledger: {name}/ledger.jsonl")
        try:
            content = ledger.read_text()
        except (OSError, UnicodeError) as error:
            raise EvidenceUnavailable(f"Unreadable evidence {name}/ledger.jsonl: {error}") from error
        parts.append(f"## {name}/ledger.jsonl\n\n{content}")
        evidence = _assessment_evidence(root, campaign.peers)
        parts.append(evidence.replace("## ", f"## {name}/"))
    return "\n\n".join(parts)


def _review_material(campaign, pair_id, review_id=None):
    """@planks("Vera receives both papers and the complete attributed research ledger")
    @planks("Vera receives all referenced peer evidence without a consolidated account")
    @planks("Pathfinder blocks the stale response before a research transition")
    @planks("the review occurs once in the ledger")
    """
    d = campaign.thread_dir(pair_id)
    ledger = d / "ledger.jsonl"
    lines = ledger.read_text().splitlines(keepends=True) if ledger.exists() else []
    # The feedback appended during a replay belongs to the transition, not its input.
    if review_id:
        lines = [line for line in lines if not (
            json.loads(line)["kind"] == "review" and
            json.loads(line)["text"].startswith('{"review_id": ' + json.dumps(review_id) + ','))]
    ledger_text = "".join(lines)
    material = thread_head(d, _inputs(d), ledger=False) + "\n\n## ledger.jsonl\n\n" + ledger_text
    material += "\n\n" + _assessment_evidence(d, campaign.peers, references=ledger_text)
    material += "\n\n" + _bundle_evidence(campaign, d)
    if campaign.raw.get("research_scheme", "eva") == "eva":
        note = d / f"{pair_id}.tex"
        if note.exists():
            material += f"\n\n## {note.name}\n\n" + note.read_text()
    return material


def _request_file(campaign, pair_id, identity):
    """@planks("the retained response is applied without another model dispatch")"""
    return campaign.thread_dir(pair_id) / "research-requests" / (hashlib.sha256(identity.encode()).hexdigest() + ".json")


def retain_response(campaign, pair_id, request, result):
    """@planks("Pathfinder resumes the investigation")
    @planks("the retained Vera response has no valid request list")
    @planks("the evidence changes before that response is applied")

    Store provider output before applying any ledger or research transition.
    """
    path = _request_file(campaign, pair_id, request.identity)
    saved = json.loads(path.read_text())
    saved["result"] = result
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(saved))
    temporary.replace(path)


def _minus_requests(response, existing):
    """@planks("Vera returns no new requests and omits disposition of the active request")
    @planks("a later Vera review defers that request with a missing-input reason")
    @planks("Vera returns PAUSE instead of a request review")
    @planks("the retained Vera response has no valid request list")
    """
    if not isinstance(response, dict) or response.get("decision") not in (None, "REVISE", "ITERATE"):
        raise ValueError("EVA-minus requires a request review without a scientific verdict")
    if not isinstance(response.get("requests"), list) or not isinstance(response.get("dispositions"), list):
        raise ValueError("review requires requests and dispositions lists")
    updated = {key: dict(value) for key, value in existing.items()}
    handled = set()
    for item in response["dispositions"]:
        if not isinstance(item, dict) or item.get("id") not in existing or item["id"] in handled:
            raise ValueError("disposition must identify an existing request exactly once")
        if item.get("status") not in ("resolved", "deferred") or not isinstance(item.get("reason"), str) or not item["reason"].strip():
            raise ValueError("disposition requires resolved/deferred status and a reason")
        handled.add(item["id"])
        updated[item["id"]].update(status=item["status"], disposition=item)
    outstanding = {key for key, value in existing.items() if value["status"] == "active"}
    if outstanding - handled:
        raise ValueError("missing disposition for active requests: " + ", ".join(sorted(outstanding - handled)))
    for item in response["requests"]:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip()
                or item["id"] in updated or item.get("action") not in ("REVISE", "ITERATE")
                or not isinstance(item.get("text"), str) or not item["text"].strip()):
            raise ValueError("new request requires a distinct id, REVISE/ITERATE action and concrete text")
        updated[item["id"]] = {**item, "status": "active"}
    return updated


def _apply_research_review(campaign, pair_id, saved, s):
    """@planks("the review is appended to the ledger with its reviewed evidence identity")
    @planks("the full review is appended to the ledger exactly once")
    @planks("Pathfinder records an operational review error rather than a handoff")
    @planks("Pathfinder blocks the stale response before a research transition")
    @planks("the branch is ready for handoff because no further requests remain")
    @planks("the branch is ready for handoff because its allowance is exhausted")
    @planks("Emmy repairs the account before scientific verification")
    @planks("the existing PAUSE scientific ending is preserved")
    @planks("the existing PAUSE-ON-ITERATE ending retains the unanswered request")
    """
    d = campaign.thread_dir(pair_id)
    identity = saved["request"]["identity"]
    material = _review_material(campaign, pair_id, identity)
    if hashlib.sha256(material.encode()).hexdigest() != saved["evidence_id"]:
        _set(campaign, pair_id, status="BLOCKED", reason="stale review: research evidence changed")
        return
    minus = campaign.raw.get("research_scheme", "eva") == "eva_minus"
    try:
        value = parse_json(saved["result"]["text"])
        if minus:
            requests = _minus_requests(value, s.get("requests", {}))
        elif not isinstance(value, dict) or value.get("decision") not in ("DRAFT", "REVISE", "ITERATE", "PAUSE"):
            raise ValueError("unreadable scientific decision")
    except (ValueError, KeyError, TypeError) as error:
        _set(campaign, pair_id, status="BLOCKED", reason=f"review: {error}")
        return
    ledger = Ledger(d / "ledger.jsonl")
    feedback = {"review_id": identity, "evidence_id": saved["evidence_id"], "response": value}
    encoded = json.dumps(feedback)
    if not any(row["kind"] == "review" and row["text"] == encoded for row in ledger.read()):
        ledger.add("verifier", "review", encoded)
    update = dict(pending=[], reviews=s.get("reviews", 0) + 1, latest_review=feedback,
                  reviewed_head=saved["ledger_head"], reason=value.get("reason"), status="running")
    if minus:
        update["requests"] = requests
        if not any(item["status"] == "active" for item in requests.values()):
            update.update(stage="done", status="HANDOFF", handoff_reason="no_further_requests")
        elif s["round"] >= campaign.rounds:
            update.update(stage="done", status="HANDOFF", handoff_reason="research_allowance_exhausted")
        else:
            update.update(stage="peers", round=s["round"] + 1, peer_call=0, peer_seconds=0)
    else:
        verdicts = d / f"{pair_id}.verdict.json"
        history = json.loads(verdicts.read_text()) if verdicts.exists() else []
        if not any(item.get("review_id") == identity for item in history):
            history.append({"review_id": identity, "round": s["round"], "at": _now(),
                            "note_sha256": hashlib.sha256((d / f"{pair_id}.tex").read_bytes()).hexdigest(), **value})
            verdicts.write_text(json.dumps(history, indent=1))
        decision = value["decision"]
        if decision == "REVISE" and s.get("repairs", 0) < campaign.raw.get("repairs", 1):
            update.update(stage="consolidate", repairs=s.get("repairs", 0) + 1, repair=value)
        elif decision == "ITERATE" and s["round"] < campaign.rounds:
            update.update(stage="peers", round=s["round"] + 1, peer_call=0, peer_seconds=0)
        else:
            update.update(stage="done", status={"ITERATE": "PAUSE-ON-ITERATE", "REVISE": "PAUSE-ON-REVISE"}.get(decision, decision))
    _set(campaign, pair_id, **update)
    if not minus:
        write_meta(campaign, pair_id, d)


def next_requests(campaign, pair_id):
    """@planks("Pathfinder prepares its first Vera review")
    @planks("its peer research round finishes")
    @planks("Vera requests REVISE of a ledger argument from existing evidence")
    @planks("Vera requests ITERATE with a concrete research gap")
    @planks("Pathfinder prepares peer research and synthesis and scientific verification")
    @planks("Pathfinder prepares the peer research instructions")
    @planks("Pathfinder prepares the research evidence for that investigation")
    @planks("Pathfinder resumes the investigation")
    @planks("the next research and review cycle is prepared")
    @planks("Pathfinder advances the branch")
    @planks("its calls have identities distinct from the earlier review cycle")
    @planks("the branch hands off the latest research with an explicit unreviewed-head marker")
    @planks("the instructions require investigating disagreements and new connections")
    @planks("the instructions distinguish inherited evidence from new derivations and conjectures")
    @planks("Vera requests REVISE of the returned account using existing evidence")
    @planks("the review is blocked before a provider call with the missing path identified")

    Apply retained outputs, then prepare the next real provider requests.
    """
    _stage_attempts(campaign)
    d = prepare(campaign, pair_id)
    ledger = Ledger(d / "ledger.jsonl")
    minus = campaign.raw.get("research_scheme", "eva") == "eva_minus"
    try:
        while True:
            s = status(campaign, pair_id)
            if s["status"] in TERMINAL | {"HANDOFF", "BLOCKED"}:
                return []
            pending = [json.loads(_request_file(campaign, pair_id, identity).read_text()) for identity in s.get("pending", [])]
            if pending:
                waiting = [item for item in pending if "result" not in item]
                if waiting:
                    return [transport.ModelRequest(**{**item["request"], "cwd": d}) for item in waiting]
                failed = next((item for item in pending if item["result"].get("transport_failed") or item["result"].get("error")), None)
                if failed:
                    _set(campaign, pair_id, status="BLOCKED", reason=f"{s['stage']}: {failed['result'].get('error') or 'transport failed'}")
                    return []
                if s["stage"] == "peers":
                    calls = s.get("peer_call", 0) + 1
                    seconds = s.get("peer_seconds", 0) + sum(item["result"]["seconds"] for item in pending)
                    more = calls < campaign.allowances["peer_calls"] and seconds < campaign.allowances["peer_seconds"] and not ledger.ready(list(campaign.peers))
                    _set(campaign, pair_id, pending=[], peer_call=calls, peer_seconds=seconds,
                         stage="peers" if more else "ledger_review" if minus else "consolidate")
                elif s["stage"] == "consolidate":
                    result = pending[0]["result"]["text"]
                    if not result.strip():
                        _set(campaign, pair_id, status="BLOCKED", reason="consolidate: no note")
                        return []
                    note = d / f"{pair_id}.tex"
                    if note.exists() and note.read_text() != result:
                        versions = d / "account-versions"
                        versions.mkdir(exist_ok=True)
                        (versions / (hashlib.sha256(note.read_bytes()).hexdigest() + ".tex")).write_bytes(note.read_bytes())
                    note.write_text(result)
                    _set(campaign, pair_id, stage="verify", pending=[], repair=None)
                else:
                    _apply_research_review(campaign, pair_id, pending[0], s)
                continue
            stage = s["stage"]
            if stage == "ledger_review" and s.get("reviews", 0) >= campaign.raw.get("ledger_reviews", campaign.rounds + 1):
                _set(campaign, pair_id, status="HANDOFF", stage="done", handoff_reason="review_allowance_exhausted")
                return []
            material = _review_material(campaign, pair_id)
            evidence_id = hashlib.sha256(material.encode()).hexdigest()
            actors = campaign.peers if stage == "peers" else (campaign.peers[0],) if stage == "consolidate" else ("verifier",)
            batch = []
            for actor in actors:
                if stage == "peers":
                    seconds = min(campaign.allowances["peer_seconds"] - s.get("peer_seconds", 0), 1200)
                    row = _scan_row(campaign, pair_id)
                    prompt = material + "\n\n" + _prompt(campaign, "peer", ACTOR=actor,
                        PEERS=" and ".join(a for a in campaign.peers if a != actor),
                        Q_INPUT=f"inputs/{_inputs(d)['Q']}", P_INPUT=f"inputs/{_inputs(d)['P']}",
                        MATERIAL="Both papers, the attributed ledger and evidence are above.",
                        LEDGER=f"{sys.executable} -m pathfinder.ledger --root . --actor {actor}",
                        LAST_SEQ=ledger.count(), SECONDS=int(seconds),
                        CALLS_LEFT=campaign.allowances["peer_calls"] - s.get("peer_call", 0) - 1,
                        FEASIBILITY=row.get("feasibility", "?"), GAIN=row.get("gain", "?"),
                        CONNEXION=row.get("connexion") or "none recorded.", RATIONALE=row.get("rationale") or "none recorded.")
                    if campaign.raw.get("research_bundles"):
                        prompt += ("\nInvestigate disagreements and develop new connections across branches. "
                                   "Distinguish inherited evidence from new derivations and conjectures. "
                                   "Keep branch bundles unchanged; write new work to your own directory and the shared ledger.")
                    if s.get("requests"):
                        prompt += "\nReview requests and dispositions:\n" + json.dumps(s["requests"])
                elif stage == "consolidate":
                    seconds = campaign.allowances["consolidate_seconds"]
                    repair = s.get("repair")
                    prior = ("Repair the existing account from existing evidence. Preserve accepted results. " + json.dumps(repair)
                             if repair else "Preserve prior results that still stand and append this round's work.")
                    prompt = _consolidate_prompt(campaign, d, _inputs(d), pair_id, "", f"{pair_id}.tex", prior)
                    prompt += "\n\n" + _bundle_evidence(campaign, d)
                    write_meta(campaign, pair_id, d)
                else:
                    seconds = campaign.allowances["verify_seconds"]
                    if minus:
                        prompt = material + ('\n\nReview this research ledger directly. Return JSON with requests and dispositions lists. '
                            'Each new request needs a distinct id, action REVISE or ITERATE, and concrete text. '
                            'REVISE corrects an argument using existing evidence; ITERATE investigates a research gap. '
                            'Every active prior request needs a disposition with its id, status resolved or deferred, and reason. '
                            'For work that remains actionable, resolve the superseded request and issue a new request. '
                            'An empty requests list means no further actionable requests. Never issue a scientific verdict. '
                            'Prior requests and dispositions:\n' + json.dumps(s.get("requests", {})))
                    else:
                        prompt = material + "\n\n" + _prompt(campaign, "verify", Q_INPUT=f"inputs/{_inputs(d)['Q']}",
                                                            P_INPUT=f"inputs/{_inputs(d)['P']}", NOTE=f"{pair_id}.tex")
                identity = f"{pair_id}:{stage}:{actor}:round-{s['round']}:review-{s.get('reviews', 0)}:repair-{s.get('repairs', 0)}:call-{s.get('peer_call', 0)}"
                request = transport.ModelRequest(identity=identity, prompt=prompt, model=campaign.model,
                    tools=stage == "peers", search=campaign.peer_search if stage == "peers" else False,
                    cwd=d, timeout=int(seconds) + (30 if stage == "peers" else 0), thread=pair_id,
                    stage="peer" if stage == "peers" else stage, actor=actor)
                path = _request_file(campaign, pair_id, identity)
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps({"request": {**asdict(request), "cwd": str(d)},
                    "evidence_id": evidence_id, "ledger_head": ledger.latest_substantive()}))
                batch.append(request)
            _set(campaign, pair_id, pending=[request.identity for request in batch], status="running")
            return batch
    except EvidenceUnavailable as error:
        _set(campaign, pair_id, status="BLOCKED", reason=str(error))
        return []


def export_outcome(campaign, pair_id):
    """@planks("its composable research outcome is exported")
    @planks("the handoff preserves deferred objections without a scientific verdict")
    @planks("the handoff preserves the unanswered request without a scientific verdict")
    @planks("the public scientific verdict is ACCEPT")
    @planks("the original verifier decision remains DRAFT in provenance")
    @planks("the branch hands off the latest research with an explicit unreviewed-head marker")
    @planks("no scientific verdict is inferred")
    """
    s = status(campaign, pair_id)
    ledger = Ledger(campaign.thread_dir(pair_id) / "ledger.jsonl")
    head = ledger.latest_substantive()
    minus = campaign.raw.get("research_scheme", "eva") == "eva_minus"
    return {**s, "scientific_verdict": None if minus else {"DRAFT": "ACCEPT"}.get(s["status"], s["status"] if s["status"] in TERMINAL else None),
            "ledger_head": head, "unreviewed_head": head > s.get("reviewed_head", -1),
            "provenance": [row for row in ledger.read() if row["kind"] == "review"]}


def _run_composable(campaign, pair_id, stop):
    """@planks("the standard research entry point opens the investigation")"""
    prepare(campaign, pair_id)
    try:
        while True:
            _check(stop)
            requests = next_requests(campaign, pair_id)
            if not requests:
                return status(campaign, pair_id)["status"]
            def execute(request):
                """@planks("the standard research entry point opens the investigation")"""
                _check(stop)
                result = transport.execute(campaign, request)
                retain_response(campaign, pair_id, request, result)
                if result.get("transport_failed"):
                    raise transport.TransportFailed(pair_id)
            with ThreadPoolExecutor(len(requests)) as pool:
                for future in [pool.submit(execute, request) for request in requests]:
                    future.result()
    except Stopped:
        _set(campaign, pair_id, status="stopped")
        return "stopped"
    except transport.TransportFailed:
        _set(campaign, pair_id, status="stopped", reason="transport failed")
        raise

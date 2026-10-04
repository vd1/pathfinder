"""What every research thread shares: its status, inputs, helper, prompts and the sections its calls read.
Split from research.py in the phase 9 sweep; research re-exports every name."""
from __future__ import annotations
import json, os, re, shutil, sys, tempfile, time
from pathlib import Path
from . import context, corpus
from .context import Section


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


OVERSIZE_FAILURE = {"class": "input_too_large", "scope": "call", "retry": False, "reset_at": None}


def _set(campaign, pair_id, **kw):
    s = status(campaign, pair_id); before = dict(s); s.update(kw, updated=_now())
    _atomic_write(campaign.thread_dir(pair_id) / "status.json", json.dumps(s, indent=1).encode())
    from . import events
    events.transition(campaign, pair_id, "research", before, s)
    return s


def _pair(campaign, pair_id):
    i, j = (int(x) for x in pair_id[1:].split("P"))
    return corpus.read(campaign.path("Q.jsonl"))[i - 1], corpus.read(campaign.path("P.jsonl"))[j - 1]


HELPER_DIR = ".pathfinder"


def install_helper(d: Path) -> str:
    """Copy the ledger helper into the thread: agents run it as a script, because their sandbox may not
    reach the environment that imports pathfinder (seen in J2, statarb and proofTree). Returns the command."""
    from . import ledger as ledger_module
    target = d / HELPER_DIR / "ledger.py"
    source = Path(ledger_module.__file__).read_bytes()
    if not target.is_file() or target.read_bytes() != source:
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(target, source)                  # an agent may be running the old copy right now
    return f"{sys.executable} {HELPER_DIR}/ledger.py --root ."


def prepare(campaign, pair_id: str) -> Path:
    """@planks("When the standard research entry point opens the investigation")"""
    d = campaign.thread_dir(pair_id)
    if (d / "status.json").exists():
        install_helper(d)
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
    imported = campaign.raw.get("research_scheme") == "direct_eva" and campaign.raw.get("imported_research", False)
    _set(campaign, pair_id, round=0 if imported else 1,
         stage="ledger_review" if imported else "peers", status="running", reason=None, started=_now())
    install_helper(d)
    return d


def thread_sections(d, inp, papers: bool = True, ledger: bool = True) -> list[Section]:
    """The static head of a call in a thread: the two papers, then the ledger as it stands, each optional,
    as file sections for the context builder. The same bytes for every caller that gets them, and across
    calls a prefix of the previous call's, since the ledger only grows; a prompt cache serves everything
    but what the ledger gained since. Whatever differs between callers goes after them."""
    out = [Section(name, path=d / "inputs" / name) for name in (inp["Q"], inp["P"])] if papers else []
    if ledger:
        out.append(Section("ledger.jsonl", path=d / "ledger.jsonl") if (d / "ledger.jsonl").exists()
                   else Section("ledger.jsonl", text=""))
    return out


def _stage_attempts(campaign):
    """@planks("Given a campaign sets \"stage_attempts\" to 1")
    @planks("Given a campaign omits \"stage_attempts\"")
    @planks("Then configuration validation fails before any provider call")
    """
    attempts = campaign.raw.get("stage_attempts", 2)
    if type(attempts) is not int or attempts < 1:
        raise ValueError("stage_attempts must be a positive integer")
    return attempts


def judge_sections(d, inp, note_name: str) -> list[Section]:
    """The thread sections plus the note, for the verifier and the paper reviewer."""
    return thread_sections(d, inp) + [Section(note_name, path=d / note_name)]


def _consolidate_prompt(campaign, d, inp, pair_id, why, note_name, prior, extra=()) -> str:
    """@planks("When the research workflow prepares its consolidation and verification requests")"""
    sections = thread_sections(d, inp)
    if (d / note_name).exists():                    # the account a repair or a next round must keep
        sections.append(Section(note_name, path=d / note_name))
    task = ("## your task\n\n" + _prompt(campaign, "consolidate", ACTOR=campaign.peers[0], WHY=why, NOTE=note_name, NOTE_STEM=pair_id,
                                          PRIOR=prior, MATERIAL="Q, P and the ledger are above.")
            + "\n\n" + evidence_pointer(campaign)
            + "\n\nReturn the complete research account, the LaTeX document itself, in your response; do not write it to a file.\n")
    return context.build(campaign, "consolidate", sections + list(extra) + [Section("", text=task, keep=True)],
                         tools=True, cwd=d, unit=pair_id)


READING = ("Files listed by path, size and sha256 are in your working directory, not pasted here. Read them in "
           "slices with your tools (a line range or a search, not the whole file) as far as the task needs, read each "
           "file once, and quote by path and line.")


def evidence_by_reference(campaign) -> bool:
    return not (campaign.raw or {}).get("inline_evidence", False)


def evidence_pointer(campaign) -> str:
    """Where the evidence is: consolidator and verifier read it with their own file tools."""
    dirs = ", ".join(f"{a}/" for a in campaign.peers)
    return (f"The peers' working files are in {dirs} beside you, and every path the ledger cites is relative to your "
            "working directory: read whatever you need to check a claim. " + READING)


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


ROLE_BRIEFS = {"peer", "consolidate", "verify"}      # the roles a composable branch or joint thread briefs


def _prompt(campaign, name, **vars):
    from . import resources
    vars.setdefault("DATE", time.strftime("%Y-%m-%d"))          # every document bears its date of production
    text = resources.prompt(campaign, name, **vars)
    if name in ROLE_BRIEFS and role_brief(campaign):
        text += "\n\n" + role_brief(campaign)
    budget = ((campaign.raw or {}).get("tool_call_budgets") or {}).get(name)
    if budget:          # every turn of a session resends its whole context: fewer, better-aimed reads cost far less
        text += (f"\n\nPlan for about {budget} tool calls in this call. Each turn resends everything read so "
                 "far, so read in slices (a line range or a search), never a whole file you only need part of, "
                 "do not reread what you have, and write your entry as soon as you can. Bound what you print: "
                 "never print a whole file or an unbounded search, and cap output with head, sed -n or cut -c, "
                 "since one long line of a data file can hold most of the file.")
    return text


def role_brief(campaign) -> str:
    """A composable view's brief (prompts/branch.md or prompts/joint.md), or "" for an ordinary thread."""
    from . import resources
    raw = campaign.raw or {}
    role = raw.get("composable_role") or ("joint" if raw.get("research_bundles") else None)   # any joint thread
    return resources.prompt(campaign, role).strip() if role in ("branch", "joint") else ""


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

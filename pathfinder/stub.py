"""A model-free backend for contract tests: "backend": "stub" in campaign.json.

Each stage gets a deterministic reply that satisfies the engine's contracts, so a deployment can drive its
campaigns through research, edit, paper and style builds without a model call. Replies go through the same
admission, active-call records and receipts as real calls; receipts say backend "stub", cost 0.

Settings under "stub" in campaign.json: "verify" (the verifier's decision, default DRAFT) and "review"
(the paper reviewer's decision, default ACCEPT)."""
from __future__ import annotations
import json
from pathlib import Path
from .ledger import Ledger, SUBSTANTIVE

NOTE = r"""\documentclass{article}
\usepackage{pathfinder-note}
\title{Stub research account}
\begin{document}
\maketitle
\section{What was found}
A stub finding, recorded in the ledger \ledger{1}.
\end{document}
"""

READABLE = r"""\documentclass{article}
\usepackage{pathfinder-readable}
\title{Stub readable account}
\begin{document}
\maketitle
\begin{abstract}
A stub account for contract tests.
\end{abstract}
\section{Introduction}
The stub cites one source \cite{stub}.
\bibliographystyle{plainurl}
\bibliography{references}
\end{document}
"""

PAPER = READABLE.replace("pathfinder-readable", "pathfinder-paper").replace("Stub readable account", "Stub paper")

BIB = "@misc{stub,\n  title = {Stub source},\n  howpublished = {\\url{https://example.org/stub}},\n  year = {2026}\n}\n"


def reply(campaign, request) -> str:
    """The text a stage receives, after writing whatever files the stage expects its agent to write."""
    settings = (campaign.raw or {}).get("stub") or {}
    cwd = Path(request.cwd or campaign.path(f"{request.stage}-work"))
    stage = request.stage
    if stage == "peer":
        ledger = Ledger(cwd / "ledger.jsonl")
        if not any(r["actor"] == request.actor and r["kind"] in SUBSTANTIVE for r in ledger.read()):
            ledger.add(request.actor, "finding", f"stub finding by {request.actor}")
        latest = ledger.latest_substantive()
        ledger.add(request.actor, "ready", f"ready at #{latest}", seen=latest)
        return "stub peer turn"
    if stage == "consolidate":
        return NOTE
    if stage == "verify":
        return json.dumps({"decision": settings.get("verify", "DRAFT"), "reason": "stub verdict", "action": ""})
    if stage == "edit" and request.actor == "editor":
        ed = cwd / "edited"; ed.mkdir(exist_ok=True)
        (ed / "note.tex").write_text(READABLE); (ed / "references.bib").write_text(BIB)
        return "stub readable account written"
    if stage == "author":
        pd = cwd / "paper"; pd.mkdir(exist_ok=True)
        (pd / "paper.tex").write_text(PAPER); (pd / "references.bib").write_text(BIB)
        (pd / "search.md").write_text("Stub search record: no search was run.\n")
        return "stub paper written"
    if stage == "review":
        return json.dumps({"decision": settings.get("review", "ACCEPT"), "summary": "stub review", "findings": []})
    if stage == "scan":
        return json.dumps({"feasibility": 50, "gain": 50, "connexion": "stub", "rationale": "stub"})
    return "stub reply"


def execute(campaign, request) -> dict:
    text = reply(campaign, request)
    return {"text": text, "session": "stub", "seconds": 0.0, "usage": {"input_tokens": 0, "output_tokens": 0},
            "input_tokens": 0, "output_tokens": 0, "cache_write": None, "cache_read": None, "prefix_read": None,
            "cost": 0.0, "cost_basis": "stub", "rates": None, "outcome": "completed", "error": None,
            "transport_failed": False, "exit_status": 0, "terminal_event": None, "raw_events": [],
            "prompt_chars": len(request.prompt), "tool_calls": 0}

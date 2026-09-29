"""Phase A: score every pair, row by row, one tool-less call each. Resumable."""
from __future__ import annotations
import json, re
from pathlib import Path
from . import corpus, transport
from .admission import Refused


def prompts_dir(campaign) -> Path:
    """Kept for callers of the old directory-wide lookup; prompts now resolve per file (resources.prompt)."""
    from . import resources
    local = campaign.path("prompts")
    return local if local.exists() else resources.engine_prompts()


def render(campaign, q: dict, p: dict) -> str:
    from . import resources
    ft = campaign.scan_fulltext
    return resources.prompt(campaign, "scan", Q_TITLE=q["title"], Q_BODY=corpus.body(campaign, q, ft in ("q", "both")),
                            P_TITLE=p["title"], P_BODY=corpus.body(campaign, p, ft in ("p", "both")))


def parse_json(text: str) -> dict:
    """The first JSON object in a reply. TeX in string values, such as \\( x \\), is not valid JSON escaping;
    a second attempt doubles every backslash that does not start a JSON escape."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in reply")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        # treat every backslash as literal TeX except an escaped quote or backslash; \beta must not become a backspace
        return json.loads(re.sub(r'\\(?!["\\])', r"\\\\", m.group(0)))


def done(campaign) -> set[str]:
    p = campaign.path("scan.jsonl")
    return {json.loads(l)["pair_id"] for l in p.read_text().splitlines() if l.strip()} if p.exists() else set()


def run(campaign, stop=lambda: False):
    """@planks("When the connection judge assesses pair \"{pair_id}\"")
    @planks("When the connection scan resumes")
    @planks("When Pathfinder executes scan, peer, consolidation, and verification model requests")
    @planks("When Pathfinder executes one stage attempt")
    @planks("When Pathfinder verifies execution routing")
    """
    Q, P, seen = corpus.read(campaign.path("Q.jsonl")), corpus.read(campaign.path("P.jsonl")), done(campaign)
    for i, q in enumerate(Q, 1):
        for j, p in enumerate(P, 1):
            pid = corpus.pair_id(i, j)
            if pid in seen or stop():
                continue
            row = {"pair_id": pid, "q": q["id"], "p": p["id"], "feasibility": None, "gain": None,
                   "connexion": None, "rationale": None, "model": campaign.scan_model, "seconds": 0, "cost": 0, "error": None}
            for attempt in range(2):
                try:
                    r = transport.execute(campaign, transport.ModelRequest(
                        identity=f"{pid}:scan:{attempt}", prompt=render(campaign, q, p), model=campaign.scan_model,
                        tools=False, search=False, cwd=campaign.path("scan-work"), timeout=600, thread=pid,
                        stage="scan", actor="judge",
                    ))
                except Refused:
                    return                                # a stop: the scan resumes from scan.jsonl
                row["seconds"] += r["seconds"]; row["cost"] += r["cost"] or 0
                try:
                    v = parse_json(r["text"])
                    row.update(feasibility=int(v["feasibility"]), gain=int(v["gain"]), connexion=v.get("connexion"),
                               rationale=v.get("rationale"), error=None)
                    break
                except (ValueError, KeyError, TypeError) as e:
                    row["error"] = r["error"] or f"unparseable: {e}"
            with open(campaign.path("scan.jsonl"), "a") as f:
                f.write(json.dumps(row) + "\n")
            print(f"{pid} feasibility={row['feasibility']} gain={row['gain']} {row['error'] or ''}")

"""Phase A: score every pair, row by row, one tool-less call each. Resumable."""
from __future__ import annotations
import json, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import contracts, corpus, transport
from .contracts import extract_json as parse_json   # kept for deployments that import it from here (proofTree)
from .admission import Refused


def prompts_dir(campaign) -> Path:
    """Kept for callers of the old directory-wide lookup; prompts now resolve per file (resources.prompt)."""
    from . import resources
    local = campaign.path("prompts")
    return local if local.exists() else resources.engine_prompts()


def render(campaign, q: dict, p: dict) -> str:
    from . import resources
    from . import context
    ft = campaign.scan_fulltext
    bodies = {"Q": corpus.body(campaign, q, ft in ("q", "both")), "P": corpus.body(campaign, p, ft in ("p", "both"))}
    fill = lambda b: resources.prompt(campaign, "scan", Q_TITLE=q["title"], Q_BODY=b["Q"], P_TITLE=p["title"], P_BODY=b["P"])
    prompt, limit = fill(bodies), context.budget(campaign, "scan")
    if len(prompt) > limit:                       # the judge has no tools: each body gets an equal share of what is left
        share = max((limit - (len(prompt) - len(bodies["Q"]) - len(bodies["P"]))) // 2, 0)
        prompt = fill({side: context.digest_text(side, text, share) if len(text) > share else text
                       for side, text in bodies.items()})
    if len(prompt) > limit:
        raise transport.PromptTooLarge(f"input too large: scan prompt is {len(prompt)} characters, budget {limit}")
    return prompt


def done(campaign) -> set[str]:
    p = campaign.path("scan.jsonl")
    return {json.loads(l)["pair_id"] for l in p.read_text().splitlines() if l.strip()} if p.exists() else set()


def pairs(campaign, Q=None, P=None) -> list[tuple]:
    """(pair id, Q row, P row) for every pair the scan covers: every (Q, P), or under same_corpus each unordered
    pair once, the lower number on the Q side, never a paper with itself."""
    Q = corpus.read(campaign.path("Q.jsonl")) if Q is None else Q
    P = corpus.read(campaign.path("P.jsonl")) if P is None else P
    same = (campaign.raw or {}).get("same_corpus") is True
    if same and [r["id"] for r in Q] != [r["id"] for r in P]:
        raise ValueError("same_corpus: Q.jsonl and P.jsonl must list the same papers in the same order")
    return [(corpus.pair_id_for(campaign, i - 1, j - 1, Q, P), q, p)
            for i, q in enumerate(Q, 1) for j, p in enumerate(P, 1)
            if not same or q.get("n", i) < p.get("n", j)]


def expected(campaign) -> int:
    """How many pairs a complete scan holds."""
    return len(pairs(campaign))


def run(campaign, stop=lambda: False):
    """@planks("When the connection judge assesses pair \"{pair_id}\"")
    @planks("When the connection scan resumes")
    @planks("When Pathfinder executes scan, peer, consolidation, and verification model requests")
    @planks("When Pathfinder executes one stage attempt")
    @planks("When Pathfinder verifies execution routing")
    """
    seen, todo = done(campaign), []
    for pid, q, p in pairs(campaign):
        if pid not in seen:
            todo.append((pid, q, p))
    write, halted = threading.Lock(), threading.Event()

    def one(pid, q, p):
        if halted.is_set() or stop():
            return
        row = {"pair_id": pid, "q": q["id"], "p": p["id"], "feasibility": None, "gain": None,
               "connexion": None, "rationale": None, "model": campaign.scan_model, "seconds": 0, "cost": 0, "error": None}
        for attempt in range(2):
            request = transport.ModelRequest(
                identity=f"{pid}:scan:{attempt}", prompt=render(campaign, q, p), model=campaign.scan_model,
                tools=False, search=False, cwd=campaign.path("scan-work"), timeout=600, thread=pid,
                stage="scan", actor="judge", schema=contracts.SCHEMAS["scan"])
            try:
                r = transport.execute(campaign, request)
                row["seconds"] += r["seconds"]; row["cost"] += r["cost"] or 0
                if r.get("transport_failed") or r.get("error"):
                    row["error"] = r.get("error") or "transport failed"; continue      # the call failed: ask again
                v, fixed = contracts.ensure(campaign, request, r, "scan")
            except Refused:
                halted.set(); return              # a stop: the scan resumes from scan.jsonl
            if fixed is not r:
                row["seconds"] += fixed.get("seconds") or 0; row["cost"] += fixed.get("cost") or 0
            if v is None:
                row["error"] = fixed.get("error") or "transport failed"; break
            row.update(feasibility=int(v["feasibility"]), gain=int(v["gain"]), connexion=v.get("connexion"),
                       rationale=v.get("rationale"), error=None)
            break
        with write:                               # one line per pair, whole, whatever runs beside it
            with open(campaign.path("scan.jsonl"), "a") as f:
                f.write(json.dumps(row) + "\n")
            print(f"{pid} feasibility={row['feasibility']} gain={row['gain']} {row['error'] or ''}")

    with ThreadPoolExecutor(max(1, int(campaign.seats or 1))) as pool:   # side by side, up to the campaign's seats
        for future in [pool.submit(one, *item) for item in todo]:
            future.result()

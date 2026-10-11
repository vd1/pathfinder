"""Phase A: score every pair, row by row, one tool-less call each. Resumable.

Optional, for conditional scans (repl, 11 October 2026):
- campaign.json "scan_contract": {"name": ..., "fields": {JSON Schema properties}, "check": "module:function"}
  adds the deployment's own fields to the reply, in one "extra" object; each row keeps it with the contract's
  name and schema digest. The check, loaded like an extension, is called as check(campaign, value, context)
  and rejects a reply by raising ValueError (one repair turn, then a contract failure).
- scan-context.json {"revision": ..., "text": ...} is the campaign's state of play. It fills {{SCAN_CONTEXT}}
  in the scan prompt (or follows the prompt when the prompt has no such slot), and every row records its
  revision and digest; each context used is kept in scan-contexts/<digest>.json.
- rescan() scores named pairs again against the current context. Rows are only ever appended: current() is
  the latest scored row per pair, history() every row."""
from __future__ import annotations
import copy, hashlib, json, threading
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


def context_of(campaign) -> dict | None:
    """The current state of play, {"revision", "text", "sha256"}, or None when the campaign has none."""
    path = campaign.path("scan-context.json")
    if not path.is_file():
        return None
    doc = json.loads(path.read_text())
    if not (isinstance(doc, dict) and isinstance(doc.get("revision"), str) and doc["revision"]
            and isinstance(doc.get("text"), str)):
        raise ValueError("scan-context.json must be {\"revision\": non-empty string, \"text\": string}")
    body = {"revision": doc["revision"], "text": doc["text"]}
    return {**body, "sha256": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()}


def _archive(campaign, ctx: dict) -> None:
    path = campaign.path(f"scan-contexts/{ctx['sha256']}.json")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"revision": ctx["revision"], "text": ctx["text"]}, indent=1))
        tmp.replace(path)


def validate_contract(raw: dict) -> None:
    """A malformed scan_contract fails when the campaign loads, not at the first scan call."""
    spec = raw.get("scan_contract")
    if spec is None:
        return
    if not (isinstance(spec, dict) and isinstance(spec.get("name"), str) and spec["name"]
            and isinstance(spec.get("fields"), dict) and spec["fields"]
            and all(isinstance(v, dict) for v in spec["fields"].values())
            and set(spec) <= {"name", "fields", "check"}
            and (spec.get("check") is None or isinstance(spec["check"], str))):
        raise ValueError("scan_contract must be {\"name\": string, \"fields\": {name: JSON Schema}, \"check\": "
                         "optional \"module:function\"}")


def schema(campaign) -> dict:
    """The scan reply's schema: the engine's, plus the deployment's fields in one required "extra" object."""
    spec = (campaign.raw or {}).get("scan_contract")
    if not spec:
        return contracts.SCHEMAS["scan"]
    s = copy.deepcopy(contracts.SCHEMAS["scan"])
    s["properties"]["extra"] = {"type": "object", "required": list(spec["fields"]), "properties": spec["fields"]}
    s["required"] = [*s["required"], "extra"]
    return s


def _check(campaign, ctx):
    spec = (campaign.raw or {}).get("scan_contract") or {}
    if not spec.get("check"):
        return None
    from . import extensions
    hook = extensions.resolve(campaign.root, ((campaign.raw or {}).get("extensions") or {}).get("path"),
                              spec["check"], "scan_contract check")
    return lambda value: hook(campaign, value, ctx and {k: ctx[k] for k in ("revision", "text", "sha256")})


def render(campaign, q: dict, p: dict, ctx: dict | None = None) -> str:
    from . import resources
    from . import context
    ft = campaign.scan_fulltext
    bodies = {"Q": corpus.body(campaign, q, ft in ("q", "both")), "P": corpus.body(campaign, p, ft in ("p", "both"))}
    template = resources.prompt_template(campaign, "scan")
    state = (f"# State of play (revision {ctx['revision']})\n\n{ctx['text']}" if ctx else "")
    def fill(b):
        text = resources.prompt(campaign, "scan", Q_TITLE=q["title"], Q_BODY=b["Q"], P_TITLE=p["title"],
                                P_BODY=b["P"], SCAN_CONTEXT=state)
        return text if not ctx or "{{SCAN_CONTEXT}}" in template else text.rstrip("\n") + "\n\n" + state + "\n"
    prompt, limit = fill(bodies), context.budget(campaign, "scan")
    if len(prompt) > limit:                       # the judge has no tools: each body gets an equal share of what is left
        share = max((limit - (len(prompt) - len(bodies["Q"]) - len(bodies["P"]))) // 2, 0)
        prompt = fill({side: context.digest_text(side, text, share) if len(text) > share else text
                       for side, text in bodies.items()})
    if len(prompt) > limit:
        raise transport.PromptTooLarge(f"input too large: scan prompt is {len(prompt)} characters, budget {limit}")
    return prompt


def rows(campaign) -> list[dict]:
    """Every scan row, in the order written."""
    p = campaign.path("scan.jsonl")
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def done(campaign) -> set[str]:
    return {r["pair_id"] for r in rows(campaign)}


def _scored(r) -> bool:
    return r.get("feasibility") is not None and r.get("gain") is not None


def current(campaign, all_rows=None) -> list[dict]:
    """One row per pair, in first-scan order: its latest scored row (a failed rescan leaves the earlier score
    current), else its latest row. Each carries "unconditioned" (scored against no state of play) and "stale"
    (scored against another state than the current one)."""
    try:
        ctx = context_of(campaign)
    except (ValueError, OSError):                 # a malformed context stops the next scan, not the readers
        ctx = None
    latest: dict = {}
    for r in rows(campaign) if all_rows is None else all_rows:
        prev = latest.get(r["pair_id"])
        if prev is None or _scored(r) or not _scored(prev):
            latest[r["pair_id"]] = r
    out = []
    for r in latest.values():
        sha = r.get("context_sha256")
        out.append({**r, "unconditioned": sha is None, "stale": sha is not None and (ctx is None or sha != ctx["sha256"])})
    return out


def history(campaign, pair_id: str) -> list[dict]:
    """Every row of one pair, oldest first."""
    return [r for r in rows(campaign) if r["pair_id"] == pair_id]


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


def rescan(campaign, pair_ids, stop=lambda: False):
    """Score the named pairs again against the current scan context, appending their rows. A pair already
    scored at this context is skipped, so a resumed rescan repeats no call; a failed one is tried again."""
    ctx = context_of(campaign)
    if ctx is None:
        raise ValueError("a rescan scores against the campaign's state of play: write scan-context.json first")
    known = {pid: (q, p) for pid, q, p in pairs(campaign)}
    unknown = [pid for pid in pair_ids if pid not in known]
    if unknown:
        raise ValueError(f"not pairs of this campaign: {', '.join(unknown)}")
    fresh = {r["pair_id"] for r in rows(campaign) if _scored(r) and r.get("context_sha256") == ctx["sha256"]}
    _score(campaign, [(pid, *known[pid]) for pid in dict.fromkeys(pair_ids) if pid not in fresh], ctx, stop)


def run(campaign, stop=lambda: False):
    """@planks("When the connection judge assesses pair \"{pair_id}\"")
    @planks("When the connection scan resumes")
    @planks("When Pathfinder executes scan, peer, consolidation, and verification model requests")
    @planks("When Pathfinder executes one stage attempt")
    @planks("When Pathfinder verifies execution routing")
    """
    seen = done(campaign)
    ctx = context_of(campaign)
    _score(campaign, [(pid, q, p) for pid, q, p in pairs(campaign) if pid not in seen], ctx, stop)


def _score(campaign, todo, ctx, stop):
    write, halted = threading.Lock(), threading.Event()
    spec = (campaign.raw or {}).get("scan_contract")
    contract = schema(campaign)
    stamp = {}
    if spec:
        stamp["contract"] = {"name": spec["name"], "schema_sha256": hashlib.sha256(
            json.dumps(contract, sort_keys=True).encode()).hexdigest()}
    if ctx:
        _archive(campaign, ctx)
        stamp.update(revision=ctx["revision"], context_sha256=ctx["sha256"])
    check = _check(campaign, ctx)

    def one(pid, q, p):
        if halted.is_set() or stop():
            return
        row = {"pair_id": pid, "q": q["id"], "p": p["id"], "feasibility": None, "gain": None,
               "connexion": None, "rationale": None, "model": campaign.scan_model, "seconds": 0, "cost": 0, "error": None}
        for attempt in range(2):
            request = transport.ModelRequest(
                identity=f"{pid}:scan:{attempt}" + (f":{ctx['sha256'][:12]}" if ctx else ""),
                prompt=render(campaign, q, p, ctx), model=campaign.scan_model,
                tools=False, search=False, cwd=campaign.path("scan-work"), timeout=600, thread=pid,
                stage="scan", actor="judge", schema=contract)
            try:
                r = transport.execute(campaign, request)
                row["seconds"] += r["seconds"]; row["cost"] += r["cost"] or 0
                if r.get("transport_failed") or r.get("error"):
                    row["error"] = r.get("error") or "transport failed"; continue      # the call failed: ask again
                v, fixed = contracts.ensure(campaign, request, r, contract if spec else "scan", check)
            except Refused:
                halted.set(); return              # a stop: the scan resumes from scan.jsonl
            if fixed is not r:
                row["seconds"] += fixed.get("seconds") or 0; row["cost"] += fixed.get("cost") or 0
            if v is None:
                row["error"] = fixed.get("error") or "transport failed"; break
            row.update(feasibility=int(v["feasibility"]), gain=int(v["gain"]), connexion=v.get("connexion"),
                       rationale=v.get("rationale"), error=None)
            if spec:
                row["extra"] = v["extra"]
            break
        row.update(stamp)
        with write:                               # one line per pair, whole, whatever runs beside it
            with open(campaign.path("scan.jsonl"), "a") as f:
                f.write(json.dumps(row) + "\n")
            print(f"{pid} feasibility={row['feasibility']} gain={row['gain']} {row['error'] or ''}")

    with ThreadPoolExecutor(max(1, int(campaign.seats or 1))) as pool:   # side by side, up to the campaign's seats
        for future in [pool.submit(one, *item) for item in todo]:
            future.result()

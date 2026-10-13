"""Freeze the top cut of the scan as the shortlist.

A campaign may weigh its pairs: "rank_weights": "rank-weights.json" in campaign.json names a file
{"revision": string, "weights": {pair id: number in [0, 1]}}, and the ranking orders pairs by scan score times
weight, a pair absent from the file weighing 1. The engine applies the numbers; how they were made is the
deployment's. Without the setting the ranking is the scan score alone."""
from __future__ import annotations
import hashlib, json, math
from . import corpus


def validate(raw: dict) -> None:
    path = raw.get("rank_weights")
    if path is None:
        return
    if not (isinstance(path, str) and path.strip()) or path.startswith("/") or ".." in path.split("/"):
        raise ValueError(f"rank_weights must name a file inside the campaign, such as 'rank-weights.json', got {path!r}")


def weights(campaign) -> dict | None:
    """{"path", "revision", "sha256", "weights"} from the file campaign.json names, or None without the setting.
    A named file that is missing or malformed is refused, never read as no weights."""
    name = (campaign.raw or {}).get("rank_weights")
    if name is None:
        return None
    path = campaign.path(name)
    try:
        data = path.read_bytes()
    except OSError:
        raise ValueError(f"rank_weights names {name}, which cannot be read") from None
    try:
        doc = json.loads(data)
    except ValueError:
        doc = None
    if not (isinstance(doc, dict) and set(doc) == {"revision", "weights"} and isinstance(doc["revision"], str)
            and doc["revision"] and isinstance(doc["weights"], dict)):
        raise ValueError(f"{name} must be {{\"revision\": non-empty string, \"weights\": {{pair id: number}}}}")
    bad = [k for k, w in doc["weights"].items()
           if isinstance(w, bool) or not isinstance(w, (int, float)) or not 0 <= w <= 1]
    if bad:
        raise ValueError(f"{name}: weights must be numbers between 0 and 1 ({', '.join(bad[:5])})")
    return {"path": name, "revision": doc["revision"], "sha256": hashlib.sha256(data).hexdigest(),
            "weights": doc["weights"]}


def rank(rows: list[dict], weighed: dict | None = None) -> list[dict]:
    """@planks("When Pathfinder ranks the assessed connections")

    With weights (weights() of the campaign) each row also gets its weight and its weighted score, which
    orders the ranking; the scan score breaks ties."""
    scored = [r for r in rows if r.get("feasibility") is not None and r.get("gain") is not None]
    for r in scored:
        r["score"] = r["feasibility"] * r["gain"]
        if weighed is not None:
            r["weight"] = weighed["weights"].get(r["pair_id"], 1)
            r["weighted"] = round(r["score"] * r["weight"], 6)
    return sorted(scored, key=lambda r: (-r.get("weighted", r["score"]), -r["score"],
                                         -min(r["feasibility"], r["gain"]), r["pair_id"]))


def capped(campaign, ranked: list[dict], per_paper: int | None) -> list[dict]:
    """The ranking with every pair dropped whose paper already appears in per_paper better pairs: a diversified
    cut. Under same_corpus a paper is its number on either side; otherwise Q and P papers are counted apart."""
    if not per_paper:
        return ranked
    same, seen, out = (campaign.raw or {}).get("same_corpus") is True, {}, []
    for r in ranked:
        qn, pn = corpus.numbers(r["pair_id"])
        keys = (qn, pn) if same else (("Q", qn), ("P", pn))
        if all(seen.get(k, 0) < per_paper for k in keys):
            out.append(r)
            for k in keys:
                seen[k] = seen.get(k, 0) + 1
    return out


def run(campaign, cut: float | None = None, force: bool = False, min_score: float | None = None,
        per_paper: int | None = None) -> dict:
    """@planks("When Pathfinder builds the shortlist")
    @planks("When the admission threshold is \"{threshold}\"")
    @planks("When Pathfinder rebuilds the shortlist")

    Freeze the top `cut` percent of a complete scan, or every pair at or above `min_score` of any scan; with
    `per_paper`, no paper appears in more pairs than that, the next best pairs taking the places. Under weights
    the ranking and `min_score` use the weighted score.
    """
    from . import scan
    weighed = weights(campaign)
    raw = campaign.path("scan.jsonl").read_bytes()
    rows = scan.current(campaign, [json.loads(l) for l in raw.decode().splitlines() if l.strip()])   # a rescanned pair once
    ranked = rank(rows, weighed)
    pool = capped(campaign, ranked, per_paper)
    if min_score is not None:
        chosen = [r for r in pool if r.get("weighted", r["score"]) >= min_score]
        cut = None
    else:
        cut = campaign.cut if cut is None else cut
        expected = scan.expected(campaign)                # N(N-1)/2 under same_corpus
        if len(rows) < expected and not force:
            raise SystemExit(f"scan incomplete: {len(rows)} of {expected} pairs; use --force to select anyway")
        chosen = pool[:math.ceil(len(ranked) * cut / 100)]
    started = {r["pair_id"] for r in ranked if (campaign.thread_dir(r["pair_id"]) / "status.json").exists()}
    chosen += [r for r in ranked if r["pair_id"] in started and r not in chosen]   # a thread once started stays listed
    out = {"cut": cut, "min_score": min_score, "per_paper": per_paper, "n_scored": len(ranked), "n_selected": len(chosen),
           "digest": hashlib.sha256(raw).hexdigest(),
           "pairs": [{k2: r[k2] for k2 in ("pair_id", "q", "p", "score", "feasibility", "gain", "weight", "weighted") if k2 in r}
                     for r in chosen]}
    if weighed is not None:
        out["weights"] = {k: weighed[k] for k in ("path", "revision", "sha256")}
    campaign.path("shortlist.json").write_text(json.dumps(out, indent=1))
    return out

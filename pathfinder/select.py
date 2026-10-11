"""Freeze the top cut of the scan as the shortlist."""
from __future__ import annotations
import hashlib, json, math
from . import corpus


def rank(rows: list[dict]) -> list[dict]:
    """@planks("When Pathfinder ranks the assessed connections")"""
    scored = [r for r in rows if r.get("feasibility") is not None and r.get("gain") is not None]
    for r in scored:
        r["score"] = r["feasibility"] * r["gain"]
    return sorted(scored, key=lambda r: (-r["score"], -min(r["feasibility"], r["gain"]), r["pair_id"]))


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
    `per_paper`, no paper appears in more pairs than that, the next best pairs taking the places.
    """
    from . import scan
    raw = campaign.path("scan.jsonl").read_bytes()
    rows = scan.current(campaign, [json.loads(l) for l in raw.decode().splitlines() if l.strip()])   # a rescanned pair once
    ranked = rank(rows)
    pool = capped(campaign, ranked, per_paper)
    if min_score is not None:
        chosen = [r for r in pool if r["score"] >= min_score]
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
           "pairs": [{k2: r[k2] for k2 in ("pair_id", "q", "p", "score", "feasibility", "gain")} for r in chosen]}
    campaign.path("shortlist.json").write_text(json.dumps(out, indent=1))
    return out

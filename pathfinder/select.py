"""Freeze the top cut of the scan as the shortlist."""
from __future__ import annotations
import hashlib, json, math
from . import corpus


def rank(rows: list[dict]) -> list[dict]:
    scored = [r for r in rows if r.get("feasibility") is not None and r.get("gain") is not None]
    for r in scored:
        r["score"] = r["feasibility"] * r["gain"]
    return sorted(scored, key=lambda r: (-r["score"], -min(r["feasibility"], r["gain"]), r["pair_id"]))


def run(campaign, cut: float | None = None, force: bool = False, min_score: float | None = None) -> dict:
    """Freeze the top `cut` percent of a complete scan, or every pair at or above `min_score` of any scan."""
    raw = campaign.path("scan.jsonl").read_bytes()
    rows = [json.loads(l) for l in raw.decode().splitlines() if l.strip()]
    ranked = rank(rows)
    if min_score is not None:
        chosen = [r for r in ranked if r["score"] >= min_score]
        cut = None
    else:
        cut = campaign.cut if cut is None else cut
        expected = len(corpus.read(campaign.path("Q.jsonl"))) * len(corpus.read(campaign.path("P.jsonl")))
        if len(rows) < expected and not force:
            raise SystemExit(f"scan incomplete: {len(rows)} of {expected} pairs; use --force to select anyway")
        chosen = ranked[:math.ceil(len(ranked) * cut / 100)]
    out = {"cut": cut, "min_score": min_score, "n_scored": len(ranked), "n_selected": len(chosen),
           "digest": hashlib.sha256(raw).hexdigest(),
           "pairs": [{k2: r[k2] for k2 in ("pair_id", "q", "p", "score", "feasibility", "gain")} for r in chosen]}
    campaign.path("shortlist.json").write_text(json.dumps(out, indent=1))
    return out

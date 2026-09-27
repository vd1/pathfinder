"""A minimal campaign on the stub backend, for tests that drive real engine stages without a model."""
import json
from pathlib import Path
from pathfinder import config


def make(root: Path, pairs=("Q1P1",), **overrides):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    raw = {"backend": "stub", "model": "stub", "peers": ["ada"], "seats": 1, "rounds": 1, "repairs": 0,
           "paper_rounds": 1, "budget_usd": 100, "call_estimate_usd": 1,
           "allowances": {"peer_seconds": 600, "peer_calls": 2, "consolidate_seconds": 60, "verify_seconds": 60,
                          "edit_seconds": 60, "paper_seconds": 60, "review_seconds": 60}}
    raw.update(overrides)
    (root / "campaign.json").write_text(json.dumps(raw, indent=1))
    n = max(int(p[1:].split("P")[0]) for p in pairs), max(int(p.split("P")[1]) for p in pairs)
    for side, count in zip("QP", n):
        rows = [{"id": f"{side.lower()}{i}", "title": f"{side} paper {i}", "abstract": f"Abstract of {side}{i}."}
                for i in range(1, count + 1)]
        (root / f"{side}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (root / "shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": p} for p in pairs]}))
    return config.load(root)

"""Campaign configuration: one JSON file at the campaign root."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Campaign:
    root: Path
    backend: str
    model: str
    scan_model: str
    peer_search: bool
    seats: int
    cut: float
    rounds: int
    allowances: dict
    budget_usd: float
    prices: dict
    scan_fulltext: str | None
    call_estimate_usd: float = 2.0
    raw: dict = field(default_factory=dict)
    peers: tuple = ("ada", "emmy")

    def path(self, name: str) -> Path:
        return self.root / name

    def thread_dir(self, pair_id: str) -> Path:
        return self.root / "threads" / pair_id

    def price(self, model: str, input_tokens: int, output_tokens: int) -> float:
        p = self.prices.get(model)
        if not p:
            return 0.0
        return input_tokens / 1e6 * p["input_per_m"] + output_tokens / 1e6 * p["output_per_m"]


def load(root: Path) -> Campaign:
    root = Path(root).resolve()
    raw = json.loads((root / "campaign.json").read_text())
    return Campaign(
        root=root, backend=raw["backend"], model=raw["model"],
        scan_model=raw.get("scan_model") or raw["model"],
        peer_search=raw.get("peer_search", True), seats=raw.get("seats", 4),
        cut=raw.get("cut", 1), rounds=raw.get("rounds", 3), allowances=raw["allowances"],
        budget_usd=raw["budget_usd"], prices=raw.get("prices", {}),
        scan_fulltext=(raw.get("scan") or {}).get("fulltext"),
        call_estimate_usd=raw.get("call_estimate_usd", 2.0), raw=raw,
        peers=tuple(raw.get("peers") or ("ada", "emmy")))

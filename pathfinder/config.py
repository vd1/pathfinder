"""Campaign configuration: one JSON file at the campaign root."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace


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
    peer_models: dict = field(default_factory=dict)     # peer name -> model, when a peer does not use `model`

    def peer_model(self, actor: str) -> str:
        return self.peer_models.get(actor) or self.model

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
    if raw.get("research_scheme") == "eva_minus":     # the former name, still written by deployments (proofTree)
        import warnings
        warnings.warn('research_scheme "eva_minus" is now "direct_eva" (E writes no synthesis, V reads the ledger)',
                      DeprecationWarning, stacklevel=2)
        raw = {**raw, "research_scheme": "direct_eva"}
    if raw.get("research_scheme") == "composable":
        n = raw.get("branches", 3)
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise ValueError(f"branches must be an integer of at least 1, got {n!r}")
        for block in ("branch", "joint"):
            if not isinstance(raw.get(block, {}), dict):
                raise ValueError(f"{block} must be an object of campaign keys, got {raw[block]!r}")
    from . import budget, pce, routing
    budget.limits(raw)                               # a malformed budget fails here, not at the first admission
    from . import actionability
    actionability.validate(raw)
    if "paper_reviewers" in raw:
        from types import SimpleNamespace as _NS
        from . import paper
        paper.reviewers(_NS(raw=raw))
    routing.validate(raw)                            # a malformed route fails here, not at the first call it routes
    pce.validate(raw)                                # edit_scheme and the PCE settings
    tb = raw.get("tool_call_budgets")
    if tb is not None and (not isinstance(tb, dict) or any(
            not isinstance(v, int) or isinstance(v, bool) or v < 1 for v in tb.values())):
        raise ValueError(f"tool_call_budgets must map role names (peer, consolidate, verify, editor, author) to positive integers, got {tb!r}")
    if "gc" in raw and not isinstance(raw["gc"], bool):
        raise ValueError(f"gc must be true or false, got {raw['gc']!r}")
    pb = raw.get("prompt_budgets")
    if pb is not None and (not isinstance(pb, dict) or any(
            not isinstance(v, int) or isinstance(v, bool) or v < 1 for v in pb.values())):
        raise ValueError(f"prompt_budgets must map stage names (or default) to positive integers, got {pb!r}")
    if raw.get("account"):
        from . import seats
        seats.account(SimpleNamespace(raw=raw))      # a malformed account fails here, not inside a call
    return campaign_from(root, raw)


def campaign_from(root: Path, raw: dict) -> Campaign:
    """The campaign a configuration describes; composable views build theirs from merged settings with it."""
    return Campaign(
        root=root, backend=raw["backend"], model=raw["model"],
        scan_model=raw.get("scan_model") or raw["model"],
        peer_search=raw.get("peer_search", True), seats=raw.get("seats", 4),
        cut=raw.get("cut", 1), rounds=raw.get("rounds", 3), allowances=raw["allowances"],
        budget_usd=float(raw.get("budget_usd", float("inf"))), prices=raw.get("prices", {}),
        scan_fulltext=(raw.get("scan") or {}).get("fulltext"),
        call_estimate_usd=raw.get("call_estimate_usd", 2.0), raw=raw,
        peers=tuple(p["name"] if isinstance(p, dict) else p for p in (raw.get("peers") or ("ada", "emmy"))),
        peer_models={p["name"]: p["model"] for p in (raw.get("peers") or ()) if isinstance(p, dict) and p.get("model")})

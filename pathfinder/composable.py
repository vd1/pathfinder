"""Composable EVA (phase 6): each pair is researched as N independent direct-EVA branches, each branch's
handoff is frozen as an immutable bundle, and one joint EVA thread then researches over all the bundles.

    "research_scheme": "composable", "branches": 3,
    "branch": {"rounds": 2, "ledger_reviews": 4},     # optional overrides for every branch
    "joint": {"rounds": 3}                            # optional overrides for the joint thread

Layout of a pair's thread directory: the joint thread lives in the directory itself (its ledger, peers,
account, edit and paper), each branch runs in branch-runs/<label>/ and is frozen into branches/<label>/.
Branches and the joint thread are views of the one campaign: the same root, receipts, events, stop marker
and admission, with their own research settings; a branch view also has its own thread directory and
names its branch on every receipt and event."""
from __future__ import annotations
import copy

SCHEME_KEYS = ("research_scheme", "research_bundles", "branches", "branch", "joint")


def labels(campaign) -> list[str]:
    return [f"branch-{n}" for n in range(1, int((campaign.raw or {}).get("branches", 3)) + 1)]


def _view(campaign, overrides: dict, scheme: dict):
    raw = {k: v for k, v in (campaign.raw or {}).items() if k not in SCHEME_KEYS}
    raw.update(overrides or {})
    raw.update(scheme)
    view = copy.copy(campaign)
    view.raw = raw
    view.rounds = raw.get("rounds", 3)
    if "allowances" in (overrides or {}):
        view.allowances = {**campaign.allowances, **overrides["allowances"]}
    return view


def branch_view(campaign, pair_id: str, label: str):
    view = _view(campaign, (campaign.raw or {}).get("branch"), {"research_scheme": "direct_eva"})
    base = campaign.thread_dir
    view.thread_dir = lambda pid: base(pid) / "branch-runs" / label
    view.branch = label
    return view


def joint_view(campaign, pair_id: str):
    return _view(campaign, (campaign.raw or {}).get("joint"),
                 {"research_scheme": "eva", "research_bundles": [f"branches/{label}" for label in labels(campaign)]})

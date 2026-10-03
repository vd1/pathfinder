"""Budgets in tokens and calls (R6; billing is a subscription, decision of 29 September).

    "budget": {"calls": 400, "input_tokens": 60000000, "output_tokens": 2000000}     # any subset

Every call that reached a model counts, interrupted ones (timed out, cancelled) included, since the model
worked on them; they are also reported apart. A call that never reached a model (refused, launch failed, no
session) is not charged. Admission projects the calls in flight at the mean usage of the calls so far. A
campaign that still sets "budget_usd" keeps the dollar guard as well."""
from __future__ import annotations
import math

FIELDS = ("calls", "input_tokens", "output_tokens")
UNCHARGED = ("no session", "launch failed", "refused")
INTERRUPTED = ("timeout", "cancelled", "killed", "stopped")


def limits(raw: dict) -> dict:
    """The campaign's budget, validated: a dict of non-negative integers under known names."""
    spec = (raw or {}).get("budget")
    if spec is None:
        return {}
    if not isinstance(spec, dict) or not spec or any(k not in FIELDS for k in spec) or any(
            not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in spec.values()):
        raise ValueError(f"budget must map some of {', '.join(FIELDS)} to non-negative integers, got {spec!r}")
    return dict(spec)


def usage(campaign) -> dict:
    from . import transport
    rows = [r for r in transport.receipts(campaign) if r.get("outcome") not in UNCHARGED]
    cut = [r for r in rows if r.get("outcome") in INTERRUPTED]
    total = lambda rs, k: sum(r.get(k) or 0 for r in rs)
    return {"calls": len(rows), "input_tokens": total(rows, "input_tokens"), "output_tokens": total(rows, "output_tokens"),
            "cache_read": total(rows, "cache_read"),
            "interrupted": {"calls": len(cut), "input_tokens": total(cut, "input_tokens"), "output_tokens": total(cut, "output_tokens")}}


def refusal(campaign, inflight: int) -> str | None:
    """Why admitting `inflight` more calls would exceed the budget, or None."""
    cap = limits(campaign.raw)
    reasons = []
    if cap:
        used = usage(campaign)
        mean = {k: (used[k] / used["calls"] if used["calls"] else 0) for k in ("input_tokens", "output_tokens")}
        projected = {"calls": used["calls"] + inflight,
                     **{k: used[k] + inflight * mean[k] for k in ("input_tokens", "output_tokens")}}
        for k, limit in cap.items():
            if projected[k] > limit:
                reasons.append(f"{k.replace('_', ' ')} {projected[k]:,.0f} projected against {limit:,}")
    if math.isfinite(campaign.budget_usd):
        from . import transport
        spent = transport.spend(campaign) + inflight * campaign.call_estimate_usd
        if spent > campaign.budget_usd:
            reasons.append(f"{spent:.2f} projected against cap {campaign.budget_usd:.2f}")
    return "budget: " + "; ".join(reasons) if reasons else None

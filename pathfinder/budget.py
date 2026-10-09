"""Budgets in tokens and calls (R6; billing is a subscription, decision of 29 September).

    "budget": {"calls": 400, "input_tokens": 60000000, "output_tokens": 2000000}     # any subset

Every call that reached a model counts, interrupted ones (timed out, cancelled) included, since the model
worked on them; they are also reported apart. A call that never reached a model (refused, launch failed, no
session) is not charged. Admission projects the calls in flight at the mean usage of the calls so far. A
campaign that still sets "budget_usd" keeps the dollar guard as well.

    "call_weights": {"scan": 0.25, "ledger_review": 0.25, "verify": 0.5}     # optional; any other stage counts 1

charges a call by its stage's weight, against "calls" and against the dollar guard's call_estimate_usd, so
cheap stages do not spend a budget at the rate of a peer call (proofTree planar: 74 scans used 74 of 91 calls).
Calls already in flight, whose stage admission does not know, count at the heaviest weight; failed attempts
count as before."""
from __future__ import annotations
import math

FIELDS = ("calls", "input_tokens", "output_tokens")
from .transport import UNCHARGED
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


def weights(raw: dict) -> dict:
    """The campaign's call weights, validated: stage name to a positive number; absent, every call counts 1."""
    spec = (raw or {}).get("call_weights")
    if spec is None:
        return {}
    if not isinstance(spec, dict) or any(not isinstance(k, str) for k in spec) or any(
            not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0 for v in spec.values()):
        raise ValueError(f"call_weights must map stage names to positive numbers, got {spec!r}")
    return {k: float(v) for k, v in spec.items()}


def weight(campaign, stage) -> float:
    """What one call of this stage counts against the call budget and the per-call estimate; a deployment's own
    call cap can count with it too."""
    return weights(getattr(campaign, "raw", None)).get(stage, 1.0)


def _heaviest(campaign) -> float:
    return max([1.0, *weights(getattr(campaign, "raw", None)).values()])


def usage(campaign) -> dict:
    from . import transport
    rows = [r for r in transport.receipts(campaign) if r.get("outcome") not in UNCHARGED]
    cut = [r for r in rows if r.get("outcome") in INTERRUPTED]
    total = lambda rs, k: sum(r.get(k) or 0 for r in rs)
    return {"calls": len(rows), "weighted_calls": sum(weight(campaign, r.get("stage")) for r in rows),
            "input_tokens": total(rows, "input_tokens"), "output_tokens": total(rows, "output_tokens"),
            "cache_read": total(rows, "cache_read"),
            "interrupted": {"calls": len(cut), "input_tokens": total(cut, "input_tokens"), "output_tokens": total(cut, "output_tokens")}}


def refusal(campaign, inflight: int, stage: str | None = None) -> str | None:
    """Why admitting `inflight` more calls would exceed the budget, or None. The last of them is this call, of
    `stage` (unknown when None); the others, already in flight, count at the heaviest weight."""
    cap = limits(campaign.raw)
    reasons = []
    charge = (inflight - 1) * _heaviest(campaign) + (weight(campaign, stage) if stage else _heaviest(campaign)) if inflight else 0
    if cap:
        used = usage(campaign)
        mean = {k: (used[k] / used["calls"] if used["calls"] else 0) for k in ("input_tokens", "output_tokens")}
        weighted = bool(weights(campaign.raw))
        projected = {"calls": (used["weighted_calls"] + charge) if weighted else used["calls"] + inflight,
                     **{k: used[k] + inflight * mean[k] for k in ("input_tokens", "output_tokens")}}
        for k, limit in cap.items():
            if projected[k] > limit:
                shown = f"{projected[k]:,.2f}".rstrip("0").rstrip(".") if k == "calls" else f"{projected[k]:,.0f}"
                reasons.append(f"{k.replace('_', ' ')} {shown} projected against {limit:,}")
    if math.isfinite(campaign.budget_usd):
        from . import transport
        spent = transport.spend(campaign) + charge * campaign.call_estimate_usd
        if spent > campaign.budget_usd:
            reasons.append(f"{spent:.2f} projected against cap {campaign.budget_usd:.2f}")
    return "budget: " + "; ".join(reasons) if reasons else None

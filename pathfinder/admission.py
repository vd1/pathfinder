"""Admission of model calls: an engine-owned reservation around every call, with an optional policy.

Every call runs inside `with admission(campaign, stage, role)`, entered before the call's active-call record
is written. Reservations are counted per campaign root. A campaign run under a coordinator also names its
parent root (campaign.raw["parent"]); the parent's stop marker is honoured, but reservations are not pooled.

Under one lock the engine checks the campaign's and the parent's stop markers, asks the policy, and on Admit
increments the reservation, so two concurrent calls cannot both pass a cap that admits one. Defer waits
outside the lock and wakes at a bounded interval, or at once when any reservation is released, then checks
again, stop markers first. Stop writes a stop marker with the policy's reason. A refused attempt gets a
receipt with outcome "refused" and no usage, and raises Refused; no active-call record exists for it.
The reservation is released however the call ends."""
from __future__ import annotations
import threading, time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


class Refused(Exception):
    """A call the engine did not admit: a stop marker, or a policy's Stop. A stop, never a health failure."""


@dataclass(frozen=True)
class Decision:
    kind: str                     # "admit", "defer" or "stop"
    reason: str = ""
    wait: float = 1.0             # for defer: longest wait before the policy is asked again


ADMIT = Decision("admit")


def defer(reason: str, wait: float = 1.0) -> Decision:
    return Decision("defer", reason, max(0.05, min(float(wait), 5.0)))


def stop(reason: str) -> Decision:
    return Decision("stop", reason)


STOP_POLL = 0.5                   # seconds: the longest a deferred call waits before it rechecks stop markers
_cond = threading.Condition()
_reserved: dict[str, int] = {}


def reserved(campaign) -> int:
    with _cond:
        return _reserved.get(str(Path(campaign.root)), 0)


def _stop_marker(campaign) -> str | None:
    """The reason of the first stop marker found on the campaign or its parent, or None."""
    roots = [Path(campaign.root)]
    parent = (campaign.raw or {}).get("parent")
    if parent:
        roots.append((Path(campaign.root) / parent).resolve())
    for root in roots:
        marker = root / "stop.json"
        if marker.exists():
            import json
            try:
                return json.loads(marker.read_text()).get("reason") or f"stop marker at {root}"
            except (ValueError, OSError):
                return f"stop marker at {root}"
    return None


def _cooldown_roots(campaign) -> list[Path]:
    roots = [Path(campaign.root)]
    parent = (campaign.raw or {}).get("parent")
    if parent:
        roots.append((Path(campaign.root) / parent).resolve())
    return roots


def cooldown_record(campaign) -> dict | None:
    """The longest active cooldown of the campaign or its coordinator parent: {remaining_seconds, reason}."""
    import json
    best = None
    for root in _cooldown_roots(campaign):
        try:
            data = json.loads((root / "cooldown.json").read_text())
            remaining = float(data.get("until", 0)) - time.time()
        except (OSError, ValueError, TypeError, AttributeError):
            continue
        if remaining > 0 and (best is None or remaining > best["remaining_seconds"]):
            best = {"remaining_seconds": round(remaining, 1), "reason": data.get("reason")}
    return best


def cooldown(campaign) -> float:
    """Seconds left in the cooldown after a rate limit, shared by the arms of one parent; 0 when none."""
    record = cooldown_record(campaign)
    return record["remaining_seconds"] if record else 0.0


def _refuse(campaign, thread, stage, actor, model, reason):
    from . import transport
    transport._receipt(campaign, thread, stage, actor, model, {
        "outcome": "refused", "seconds": 0.0, "usage": None, "input_tokens": None, "output_tokens": None,
        "cache_write": None, "cache_read": None, "prefix_read": None, "cost": None, "cost_basis": None,
        "error": reason})
    raise Refused(reason)


@contextmanager
def admission(campaign, stage: str, role: str, *, thread: str | None = None, model: str | None = None):
    from . import extensions, runner
    policy = extensions.load(campaign, "admission")
    key = str(Path(campaign.root))
    with _cond:
        while True:
            reason = _stop_marker(campaign)
            if reason is not None:
                break
            remaining = cooldown(campaign)
            if remaining > 0:                      # a rate limit holds every call, not only the one that hit it
                _cond.wait(timeout=min(remaining, STOP_POLL))
                continue
            decision = ADMIT if policy is None else policy(campaign, stage, role, _reserved.get(key, 0))
            if not isinstance(decision, Decision) or decision.kind not in ("admit", "defer", "stop"):
                raise TypeError(f"admission policy returned {decision!r}; expected admit, defer or stop")
            if decision.kind == "admit":
                _reserved[key] = _reserved.get(key, 0) + 1
                break
            if decision.kind == "stop":
                reason = decision.reason or "admission policy stop"
                if not runner.stopped(campaign):
                    runner.request_stop(campaign, reason)
                break
            _cond.wait(timeout=min(decision.wait, STOP_POLL))    # releases the lock; a stop is seen within STOP_POLL
    if reason is not None:
        _refuse(campaign, thread, stage, role, model, reason)
    try:
        yield
    finally:
        with _cond:
            _reserved[key] -= 1
            if not _reserved[key]:
                del _reserved[key]
            _cond.notify_all()


def budget_per_call(campaign, stage, role, reserved_now) -> Decision:
    """A built-in policy: admit a call only if recorded spend plus every reserved call, this one included,
    stays within the campaign budget; otherwise stop the campaign with the budget reason."""
    from . import transport
    projected = transport.spend(campaign) + (reserved_now + 1) * campaign.call_estimate_usd
    if projected > campaign.budget_usd:
        return stop(f"budget: {projected:.2f} projected against cap {campaign.budget_usd:.2f}")
    return ADMIT

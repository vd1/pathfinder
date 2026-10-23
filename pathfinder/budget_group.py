"""A pinned aggregate budget across sequential child campaigns.

The group lock spans a model call and its receipt, so separate controllers cannot
spend concurrently against the same observed balance. This uses the normal
projected-token convention, not a promise about the size of an in-flight reply.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
from . import budget


def load(campaign):
    spec = campaign.raw.get("budget_group")
    if not isinstance(spec, dict) or set(spec) != {"manifest", "sha256"}:
        raise ValueError("budget_group needs manifest and sha256")
    path = campaign.path(spec["manifest"]).resolve()
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        raise ValueError("budget group manifest hash differs")
    doc = json.loads(path.read_text())
    expected = {"version", "campaigns", "budget"} | ({"reservations"} if doc.get("version") == 2 else set())
    if set(doc) != expected or type(doc.get("version")) is not int or doc["version"] not in (1, 2):
        raise ValueError("unsupported budget group manifest")
    cap = budget.limits(doc)
    if not cap or not isinstance(doc["campaigns"], list) or not doc["campaigns"]:
        raise ValueError("budget group needs limits and campaign roots")
    roots = [Path(p) for p in doc["campaigns"]]
    if any(not p.is_absolute() or p != p.resolve() for p in roots) or len(set(roots)) != len(roots):
        raise ValueError("budget group roots must be canonical, absolute and unique")
    if Path(campaign.root).resolve() not in roots:
        raise ValueError("campaign is not in its budget group")
    from . import budget_reservation
    budget_reservation.records(doc)
    return path, roots, cap


def accounting(roots, reservations=None):
    """Keep measured usage, uncertain reservations and admission totals distinct."""
    from . import transport
    reservations = reservations or {}
    used = dict.fromkeys(budget.FIELDS, 0)
    reserved = dict.fromkeys(("input_tokens", "output_tokens"), 0)
    unknown = []
    unresolved = []
    for root in roots:
        if any((root / "active-calls").glob("*.json")):
            unresolved.append(str(root))
        rows = transport.receipts(SimpleNamespace(root=root, path=lambda n, root=root: root / n))
        for row in rows:
            if row.get("outcome") in transport.UNCHARGED:
                continue
            used["calls"] += 1
            missing = []
            estimate = reservations.get((str(root), row.get("call_id")), {})
            for key in ("input_tokens", "output_tokens"):
                value = row.get(key)
                if type(value) is not int or value < 0:
                    missing.append(key)
                    reserved[key] += estimate.get(key, 0)
                else:
                    used[key] += value
            if missing:
                unknown.append(dict(root=str(root), call_id=row.get("call_id"), fields=missing,
                                    reserved=all(k in estimate for k in missing)))
    effective = {k: v + reserved.get(k, 0) for k, v in used.items()}
    projected = {"calls": used["calls"] + 1}
    for key in ("input_tokens", "output_tokens"):
        projected[key] = effective[key] + (effective[key] / used["calls"] if used["calls"] else 0)
    return dict(measured=used, reserved=reserved, admission_total=effective, projected=projected,
                unknown_calls=unknown, unresolved_active_roots=unresolved,
                actual_total_certified=not unknown and not unresolved)


def refusal(roots, cap, reservations=None):
    report = accounting(roots, reservations)
    if report["unresolved_active_roots"]:
        return f"budget: shared group has unresolved active-call evidence in {report['unresolved_active_roots'][0]}"
    for row in report["unknown_calls"]:
        if not row["reserved"]:
            return f"budget: shared group has unknown or invalid {row['fields'][0]} in {row['root']}"
    used, projected = report["admission_total"], report["projected"]
    exceeded = [key for key, value in cap.items() if used[key] >= value or projected[key] > value]
    return ("budget: shared group " + ", ".join(
        f"{key} used/reserved {used[key]}, projected {projected[key]:g}, cap {cap[key]}" for key in exceeded)
            if exceeded else None)


def _reservations(campaign, path):
    from . import budget_reservation
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != campaign.raw["budget_group"]["sha256"]:
        raise ValueError("budget group manifest hash differs")
    return budget_reservation.records(json.loads(data))


def report(campaign):
    from . import budget_reservation
    path, roots, cap = load(campaign)
    reservations = _reservations(campaign, path)
    return dict(manifest=str(path), cap=cap, **accounting(roots, reservations),
                refusal=refusal(roots, cap, reservations),
                reservation_notice=budget_reservation.NOTICE if reservations else None)


@contextmanager
def admission(campaign, request):
    if "budget_group" not in campaign.raw:
        yield
        return
    from . import admission as ordinary, runner
    path, roots, cap = load(campaign)
    # Never unlink this lock: all group members must address the same inode.
    fd = os.open(str(path) + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        while True:
            reason = ordinary._stop_marker(campaign)
            if reason:
                ordinary._refuse(campaign, request.thread, request.stage, request.actor, request.model, reason)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                time.sleep(0.1)
        # Revalidate after waiting; a changed group is never silently accepted.
        load(campaign)
        reservations = _reservations(campaign, path)
        reason = refusal(roots, cap, reservations)
        if reason:
            runner.request_stop(campaign, reason)
            ordinary._refuse(campaign, request.thread, request.stage, request.actor, request.model, reason)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

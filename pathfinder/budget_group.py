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
    if set(doc) != {"version", "campaigns", "budget"} or doc["version"] != 1:
        raise ValueError("unsupported budget group manifest")
    cap = budget.limits(doc)
    if not cap or not isinstance(doc["campaigns"], list) or not doc["campaigns"]:
        raise ValueError("budget group needs limits and campaign roots")
    roots = [Path(p) for p in doc["campaigns"]]
    if any(not p.is_absolute() or p != p.resolve() for p in roots) or len(set(roots)) != len(roots):
        raise ValueError("budget group roots must be canonical, absolute and unique")
    if Path(campaign.root).resolve() not in roots:
        raise ValueError("campaign is not in its budget group")
    return path, roots, cap


def refusal(roots, cap):
    from . import transport
    used = dict.fromkeys(budget.FIELDS, 0)
    for root in roots:
        # An interrupted controller can leave a served call without its receipt.
        # Do not guess its spend or resume another member around that evidence.
        if any((root / "active-calls").glob("*.json")):
            return f"budget: shared group has unresolved active-call evidence in {root}"
        rows = transport.receipts(SimpleNamespace(root=root, path=lambda n, root=root: root / n))
        for row in rows:
            if row.get("outcome") in transport.UNCHARGED:
                continue
            used["calls"] += 1
            for key in ("input_tokens", "output_tokens"):
                value = row.get(key)
                if type(value) is not int or value < 0:
                    return f"budget: shared group has unknown or invalid {key} in {root}"
                used[key] += value
    projected = {"calls": used["calls"] + 1}
    for key in ("input_tokens", "output_tokens"):
        projected[key] = used[key] + (used[key] / used["calls"] if used["calls"] else 0)
    exceeded = [key for key, value in cap.items() if used[key] >= value or projected[key] > value]
    return ("budget: shared group " + ", ".join(
        f"{key} used {used[key]}, projected {projected[key]:g}, cap {cap[key]}" for key in exceeded)
            if exceeded else None)


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
        reason = refusal(roots, cap)
        if reason:
            runner.request_stop(campaign, reason)
            ordinary._refuse(campaign, request.thread, request.stage, request.actor, request.model, reason)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

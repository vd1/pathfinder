"""Small, read-only audit surface for an external supervising agent."""
from __future__ import annotations

import fcntl
import json
import os
import time
import uuid
import threading
from contextlib import contextmanager
from pathlib import Path


_held: dict = {}                  # (runner.lock path, thread) -> nesting depth and the run it serves


def bind_run(campaign, run_id):
    """Record which run the current thread's ownership serves; None clears it."""
    key = (str(campaign.path("runner.lock").resolve()), threading.get_ident())
    with _held_lock:
        if key not in _held:
            raise RuntimeError("bind_run outside ownership")
        _held[key]["run_id"] = run_id


def owned_run(campaign):
    """The run id this thread's ownership of the campaign serves, or None."""
    key = (str(campaign.path("runner.lock").resolve()), threading.get_ident())
    with _held_lock:
        return (_held.get(key) or {}).get("run_id")
_held_lock = threading.Lock()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(value, indent=2))
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def read(path):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return None


def alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


@contextmanager
def owner(campaign, nested: bool = False):
    """An OS-held lock protects research runs; metadata alone is not ownership. With nested=True, a thread
    that already owns the campaign may enter again without releasing it (a dispatch running its stages);
    any other thread, and any caller not asking for nesting, is refused as a second owner."""
    key = (str(campaign.path("runner.lock").resolve()), threading.get_ident())
    with _held_lock:
        mine = key in _held
        if mine and nested:
            _held[key]["depth"] += 1
    if mine and nested:
        try:
            yield
        finally:
            with _held_lock:
                _held[key]["depth"] -= 1
        return
    if mine:
        raise RuntimeError("campaign research runner already owns runner.lock")
    with campaign.path("runner.lock").open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("campaign research runner already owns runner.lock") from None
        try:
            # A crashed parent can leave model subprocesses alive. Do not overlap them.
            for path in campaign.path("active-calls").glob("*.json"):
                call = read(path)
                if call and (alive(call.get("pid")) or alive(call.get("child_pid"))):
                    raise RuntimeError(f"unresolved active call: inspect {path} before restarting")
            with _held_lock:
                _held[key] = {"depth": 1, "run_id": None}
            try:
                yield
            finally:
                with _held_lock:
                    _held.pop(key, None)
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


ALLOWANCE_KEYS = {"peer": "peer_seconds", "consolidate": "consolidate_seconds", "verify": "verify_seconds",
                  "edit": "edit_seconds", "author": "paper_seconds", "review": "review_seconds"}


def _allowances(campaign, receipts, warnings) -> list[dict]:
    """Per stage: the allowance, its timeouts, and the longest completed call, so a too-short allowance is visible."""
    out = []
    for stage, key in ALLOWANCE_KEYS.items():
        rows = [r for r in receipts[-50:] if r.get("stage") == stage]     # recent calls: advice about the present
        if not rows:
            continue
        timeouts = sum(r.get("outcome") == "timeout" for r in rows)
        completed = [r.get("seconds") or 0 for r in rows if r.get("outcome") == "completed"]
        longest = max(completed) if completed else None
        allowance = (campaign.allowances or {}).get(key)
        out.append({"stage": stage, "allowance": allowance, "timeouts": timeouts, "longest_completed_seconds": longest})
        if timeouts:
            warnings.append(f"{timeouts} {stage} call(s) timed out; the current {key} is "
                            + (f"{allowance} s" if allowance is not None else "unset")
                            + (f"; completed {stage} calls took up to {longest:.0f} s." if longest is not None else ".")
                            + "".join(f" One timed out at a deadline of {d:.0f} s, cut short by what was left of the allowance."
                                      for d in sorted({r["deadline_seconds"] for r in rows if r.get("outcome") == "timeout"
                                                       and r.get("deadline_seconds") is not None and allowance is not None
                                                       and r["deadline_seconds"] < min(allowance, 1200)})))
    return out


def snapshot(campaign):
    """Evidence only: overdue work is suspicious, not proof of deadlock."""
    from . import research

    now = time.time()
    warnings = []
    def inspect(path):
        try:
            return read(path)
        except (json.JSONDecodeError, OSError) as error:
            warnings.append(f"Cannot read {path}: {error}")
            return None
    metadata = inspect(campaign.path("runner.json"))
    if metadata:
        metadata = {**metadata, "pid_alive": alive(metadata.get("pid")),
                    "heartbeat_age_seconds": round(max(0, now - metadata["heartbeat_at"]), 1)}
        if metadata["status"] in {"running", "draining"}:
            if metadata["pid_alive"] is False:
                launch = metadata.get("launch") or {}
                warnings.append("Runner PID is absent: the run ended without recording a failure or a stop (killed from "
                                "outside, or ended with the session that launched it)."
                                + (f" It was launched under {launch.get('parent') or 'pid ' + str(launch.get('ppid'))} in "
                                   f"that process's group, so it ended when the group did; start long runs detached "
                                   "(README, Launching long runs)." if launch and not launch.get("own_group") else ""))
            elif metadata["heartbeat_age_seconds"] > 300:
                warnings.append("Runner heartbeat is older than five minutes; investigate before restarting.")
    else:
        warnings.append("No runner instrumentation recorded; liveness is unknown for legacy or external launchers.")
    from . import exhaustion
    backends = {campaign.backend, *(r.get("backend") for r in ((campaign.raw or {}).get("routes") or {}).values())}
    for pause in exhaustion.all_active():          # calls to this provider wait for its reset, in every campaign
        if pause["backend"] in backends:
            warnings.append(exhaustion.describe(pause) + "; calls to it wait until then")
    active = []
    for path in sorted(campaign.path("active-calls").glob("*.json")):
        call = inspect(path)
        if call is None:
            continue
        call = {**call, "record": str(path), "pid_alive": alive(call.get("pid")),
                "child_alive": alive(call.get("child_pid")),
                "age_seconds": round(max(0, now - call["started_at"]), 1),
                "overdue_seconds": round(max(0, now - call["deadline_at"]), 1)}
        active.append(call)
        if call["overdue_seconds"]:
            warnings.append(f"Overdue call {call['thread']}/{call['stage']}/{call['actor']}; inspect its process and logs.")
        if call["pid_alive"] is False:
            warnings.append(f"Orphaned call record {call['attempt_id']}; outcome unknown, inspect child before restart.")
    receipts = []
    receipt_path = campaign.path("receipts.jsonl")
    if receipt_path.exists():
        for number, line in enumerate(receipt_path.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"Incomplete or invalid receipt at {receipt_path}:{number}; retry audit before treating it as corruption.")
                continue
            if row.get("call_id") is None or row["call_id"] not in {r.get("call_id") for r in receipts[-200:]}:
                receipts.append(row)                 # a receipt written twice for one call is read once
    fields = ("at", "thread", "stage", "actor", "outcome", "error")
    failures = [{**{k: row.get(k) for k in fields}, "failure": row.get("failure")} for row in receipts
                if row.get("error") or row.get("outcome") in {"timeout", "error", "launch failed", "no session"}]
    by_class = {}
    for row in receipts:
        name = (row.get("failure") or {}).get("class")
        if name:
            by_class[name] = by_class.get(name, 0) + 1
    completed = [row for row in receipts if row.get("outcome") == "completed" and not row.get("error")]
    for role, budget in ((campaign.raw or {}).get("tool_call_budgets") or {}).items():
        stage = "edit" if role == "editor" else role
        rows = [r for r in receipts[-50:] if r.get("stage") == stage and r.get("tool_calls") is not None]
        over = [r for r in rows if r["tool_calls"] > 1.5 * budget]
        if over:
            warnings.append(f"{stage}: {len(over)} of {len(rows)} recent calls used more than 1.5 times their budget of "
                            f"{budget} tool calls (up to {max(r['tool_calls'] for r in over)}).")
    limits = {}                                    # sources that rate-limited the agents in the last 50 calls
    for row in receipts[-50:]:
        for source, n in (row.get("source_limits") or {}).items():
            limits[source] = limits.get(source, 0) + n
    if limits:
        warnings.append("Agents met rate limits in their own requests: "
                        + ", ".join(f"{source} {n}" for source, n in sorted(limits.items())) + " in the last 50 calls.")
    work = []
    for pair in (inspect(campaign.path("shortlist.json")) or {}).get("pairs", []):
        pid = pair["pair_id"]
        research_state = inspect(campaign.thread_dir(pid) / "status.json") or {}
        editor = inspect(campaign.thread_dir(pid) / "edited/edit.json") or {}
        paper = inspect(campaign.thread_dir(pid) / "paper/paper.json") or {}
        checks = {"editor": editor.get("checks", []), "paper": paper.get("checks", [])}
        for stage, findings in checks.items():
            if findings:
                warnings.append(f"{pid}/{stage}: unresolved reference/build checks; inspect the stage record.")
        work.append({"pair": pid, "research": research_state, "editor": editor, "paper": paper,
                     "checks": checks,
                     "needs_edit": research_state.get("status") in research.TERMINAL and editor.get("status") != "done"})
    failure = inspect(campaign.path("health.json"))
    if failure:
        warnings.append("Recorded operational failure requires diagnosis and an explicit restart.")
    from . import admission
    cooling = admission.cooldown_record(campaign)
    if cooling:
        warnings.append(f"Admission is cooling down for {cooling['remaining_seconds']:.0f} s after a rate limit: {cooling['reason']}")
    stop = inspect(campaign.path("stop.json"))
    stopped_by = (stop or {}).get("failure") or {}
    if stopped_by.get("scope") == "campaign":
        warnings.append(f"Stopped by a {stopped_by['class']} failure"
                        + (f"; resets {stopped_by['reset_at']}" if stopped_by.get("reset_at") else "")
                        + ". Retrying before that changes nothing; escalate to the operator if it needs a key or a repair.")
    out = {"generated_at": now, "campaign": str(campaign.root.resolve()), "runner": metadata,
            "active_calls": active, "last_completed_call": ({k: completed[-1].get(k) for k in fields} if completed else None),
            "failure_count": len(failures), "recent_failures": failures[-10:], "failure": failure,
            "stop": stop, "failures_by_class": by_class, "cooldown": cooling, "source_limits": limits, "allowances": _allowances(campaign, receipts, warnings), "work": work, "warnings": warnings,
            "evidence": {"receipts": str(campaign.path("receipts.jsonl")),
                         "runner": str(campaign.path("runner.json")),
                         "failures": str(campaign.path("failures.jsonl"))},
            "interpretation": "Compare with the previous audit. Heartbeat and call activity are not scientific progress. PID existence alone does not prove process identity or health."}
    return _with_extension(campaign, out)


def _with_extension(campaign, out):
    """A deployment's snapshot_extra sees a copy of the snapshot; what it returns is stored under
    "extensions" and can never replace a core field. A failing extension is a warning, not a failed audit."""
    import copy
    from . import extensions
    try:
        extra = extensions.load(campaign, "snapshot_extra")
        if extra is not None:
            value = extra(campaign, copy.deepcopy(out))
            if not isinstance(value, dict):
                raise TypeError(f"snapshot_extra returned {type(value).__name__}, expected dict")
            out["extensions"] = value
    except Exception as error:                 # evidence gathering must not hide the core snapshot
        out["warnings"].append(f"snapshot_extra failed: {error!r}")
    return out


def text(campaign):
    s = snapshot(campaign)
    r = s["runner"]
    lines = [f"campaign {s['campaign']}"]
    if r:
        lines.append(f"runner {r['run_id']} pid {r['pid']} alive={r['pid_alive']} status={r['status']} heartbeat_age={r['heartbeat_age_seconds']}s")
        lines.append(f"last completed investigation: {r.get('last_progress')}")
    lines.append(f"last completed call: {s['last_completed_call']}")
    for call in s["active_calls"]:
        lines.append(f"active {call['thread']}/{call['stage']}/{call['actor']} child={call.get('child_pid')} age={call['age_seconds']}s overdue={call['overdue_seconds']}s record={call['record']}")
    lines.append(f"failures {s['failure_count']} latest={s['recent_failures'][-1:]}")
    lines.append(f"unfinished editing: {[w['pair'] for w in s['work'] if w['needs_edit']]}")
    lines.extend(f"attention: {warning}" for warning in s["warnings"])
    if s["failure"]:
        lines.append(f"failure detail: {s['failure']}")
    return "\n".join(lines)

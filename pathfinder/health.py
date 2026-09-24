"""Small, read-only audit surface for an external supervising agent."""
from __future__ import annotations

import fcntl
import json
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


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
def owner(campaign):
    """An OS-held lock protects research runs; metadata alone is not ownership."""
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
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


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
                warnings.append("Runner PID is absent; recorded run did not finish normally.")
            elif metadata["heartbeat_age_seconds"] > 300:
                warnings.append("Runner heartbeat is older than five minutes; investigate before restarting.")
    else:
        warnings.append("No runner instrumentation recorded; liveness is unknown for legacy or external launchers.")
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
                receipts.append(json.loads(line))
            except json.JSONDecodeError:
                warnings.append(f"Incomplete or invalid receipt at {receipt_path}:{number}; retry audit before treating it as corruption.")
    fields = ("at", "thread", "stage", "actor", "outcome", "error")
    failures = [{k: row.get(k) for k in fields} for row in receipts
                if row.get("error") or row.get("outcome") in {"timeout", "error", "launch failed", "no session"}]
    completed = [row for row in receipts if row.get("outcome") == "completed" and not row.get("error")]
    work = []
    for pair in (inspect(campaign.path("shortlist.json")) or {}).get("pairs", []):
        pid = pair["pair_id"]
        research_state = inspect(campaign.thread_dir(pid) / "status.json") or {}
        editor = inspect(campaign.thread_dir(pid) / "edited/edit.json") or {}
        work.append({"pair": pid, "research": research_state, "editor": editor,
                     "needs_edit": research_state.get("status") in research.TERMINAL and editor.get("status") != "done"})
    failure = inspect(campaign.path("health.json"))
    if failure:
        warnings.append("Recorded operational failure requires diagnosis and an explicit restart.")
    return {"generated_at": now, "campaign": str(campaign.root.resolve()), "runner": metadata,
            "active_calls": active, "last_completed_call": ({k: completed[-1].get(k) for k in fields} if completed else None),
            "failure_count": len(failures), "recent_failures": failures[-10:], "failure": failure,
            "stop": inspect(campaign.path("stop.json")), "work": work, "warnings": warnings,
            "evidence": {"receipts": str(campaign.path("receipts.jsonl")),
                         "runner": str(campaign.path("runner.json")),
                         "failures": str(campaign.path("failures.jsonl"))},
            "interpretation": "Compare with the previous audit. Heartbeat and call activity are not scientific progress. PID existence alone does not prove process identity or health."}


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

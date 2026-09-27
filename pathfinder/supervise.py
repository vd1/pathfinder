"""Campaign-scoped foreground timer. Astra diagnoses; this module only schedules."""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import threading
import time
import uuid

from . import alerts, config, health, runner

SCHEMA = {"type": "object", "properties": {
    "status": {"type": "string", "enum": ["continue", "complete", "needs_operator"]},
    "summary": {"type": "string"}}, "required": ["status", "summary"], "additionalProperties": False}


def processes(pids):
    """Collect only the assigned PID/group tree, without command arguments or secrets."""
    observed = time.time()
    try:
        result = subprocess.run(["ps", "-axo", "pid=,ppid=,pgid=,comm="],
                                capture_output=True, text=True, timeout=5, check=True)
        rows = []
        for line in result.stdout.splitlines():
            pid, parent, group, name = line.split(None, 3)
            rows.append({"pid": int(pid), "ppid": int(parent), "pgid": int(group), "executable": name})
        related = {pid for pid in pids if isinstance(pid, int) and pid > 0}
        selected = []
        while True:
            selected = [r for r in rows if r["pid"] in related or r["ppid"] in related or r["pgid"] in related]
            expanded = related | {r["pid"] for r in selected}
            if expanded == related:
                break
            related = expanded
        return {"at": observed, "available": True, "requested_pids": sorted(p for p in pids if p),
                "related_processes": selected,
                "limits": "Point-in-time PID/group tree plus recorded call PIDs; PID reuse and unrecorded reparented independent groups are not resolved."}
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return {"at": observed, "available": False, "error": str(error)}


def audit(campaign, checkout, directory, resume, scope, timeout):
    before = health.snapshot(campaign)
    health.write(directory / "before.json", before)
    health.write(directory / "schema.json", SCHEMA)
    state = health.read(directory.parent / "session.json")
    pids = [state.get("runner_pid"), (before["runner"] or {}).get("pid")]
    for call in before["active_calls"]:
        pids.extend([call.get("pid"), call.get("child_pid")])
    health.write(directory / "processes.json", processes(pids))
    instructions = (checkout / "prompts/supervisor.md").read_text()
    prompt = instructions + "\n\nSession-local assignment:\n" + json.dumps({
        "campaign_directory": str(campaign.root), "checkout": str(checkout),
        "pipeline_scope": scope, "authorized_resume_argv": resume,
        "snapshot": str(directory / "before.json"),
        "process_evidence": str(directory / "processes.json"),
        "session": str(directory.parent / "session.json"),
        "runner_log": str(directory.parent / "runner.log"),
        "authorized_verdict_repair_argv_prefix": state.get("verdict_repair_command")}, indent=2) + """

Perform ONE audit now. The parent timer handles all waiting and scheduling.
Do not create, pause, or cancel any external schedule. Return the required JSON:
continue if work remains safely underway; complete only if the entire assigned
scope is finished with no active runner/call; needs_operator if input is needed.
Do not modify this checkout. Only campaign evidence and incident records may be
written. Do not use Shipshape or spawn additional agents. Never run git writes.
Use the supplied Python executable with -m pathfinder.cli for health commands,
from the supplied checkout. Avoid uv cache access during the audit.
The parent supplies read-only process evidence because this audit's sandbox
may deny ps. Use that evidence with the recorded calls, logs, and fixture or
runner code; do not request broader access or treat unavailable evidence as safe.
If recovery is safe, use ONLY authorized_resume_argv. A long-running resumed
runner must start in its own session with stdin DEVNULL and output appended to
runner_log, so it survives this audit. Do not wait for a long campaign to finish
inside the audit. Record the resume PID and verify its identity and progress on
the next audit. Never clear an operator stop or change the assigned scope.
This audit has a bounded duration. Uncertain state requires needs_operator.
If authorized_verdict_repair_argv_prefix is present, you may append the exact
blocked pair ID and run that guarded repair command after checking all owners
and descendants. Its checkpoint writes are authorized campaign-evidence repairs.
It makes no model call and cannot change the saved judgment. Do not bypass a
rejected guard; record the result and resume only through authorized_resume_argv.
"""
    prompt += f"\nPython executable: {sys.executable}\n"
    command = ["codex", "exec", "--model", "gpt-6-astra", "--ephemeral",
               "--ignore-user-config", "--sandbox", "workspace-write",
               "-c", 'approval_policy="never"', "-c", 'model_reasoning_effort="medium"',
               "--cd", str(checkout), "--add-dir", str(campaign.root),
               "--output-schema", str(directory / "schema.json"),
               "--output-last-message", str(directory / "result.json"), "--json", "-"]
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("HERDR_") and k not in {"CODEX_THREAD_ID", "CODEX_SESSION_ID"}}
    with (directory / "agent.jsonl").open("w") as out, (directory / "agent.stderr").open("w") as err:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                text=True, cwd=checkout, env=env, start_new_session=True)
        try:
            proc.communicate(prompt, timeout=timeout)
        except BaseException:
            # Only the audit's group; resumed runners must have their own session.
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
            except ProcessLookupError:
                proc.wait(timeout=5)
            raise
    if proc.returncode:
        raise RuntimeError(f"Astra audit exited {proc.returncode}; inspect {directory}")
    result = health.read(directory / "result.json")
    if not isinstance(result, dict) or result.get("status") not in {"continue", "complete", "needs_operator"} or not isinstance(result.get("summary"), str):
        raise RuntimeError(f"Missing or invalid Astra audit result: {directory}")
    health.write(directory / "after.json", health.snapshot(campaign))
    return result


def process_identity(pid):
    """Birth timestamp avoids silently attaching to a reused PID. Zombies are exited."""
    result = subprocess.run(["ps", "-p", str(pid), "-o", "lstart=", "-o", "stat="],
                            capture_output=True, text=True, timeout=5)
    if result.returncode == 1 and not result.stdout.strip() and not result.stderr.strip():
        return None
    if result.returncode:
        raise RuntimeError("Cannot establish runner process identity")
    fields = result.stdout.split()
    if len(fields) != 6:
        raise RuntimeError("Unexpected process identity response")
    return None if fields[5].startswith("Z") else " ".join(fields[:5])


class AttachedProcess:
    """Observation only: never spawn or signal the attached process."""
    def __init__(self, pid):
        self.pid = pid
        self.identity = process_identity(pid)
        if self.identity is None:
            raise RuntimeError("Attach PID is absent")

    def poll(self):
        return None if process_identity(self.pid) == self.identity else 0

    def wait(self, timeout):
        threading.Event().wait(min(timeout, 5))
        if self.poll() is None:
            raise subprocess.TimeoutExpired("attached runner", timeout)
        return 0


def extend(campaign, hours):
    """Explicit operator request; the running timer alone applies the new deadline."""
    if not math.isfinite(hours) or hours <= 0:
        raise ValueError("Extension hours must be positive and finite")
    supervision = campaign.path("supervision")
    supervision.mkdir(exist_ok=True)
    with (supervision / "extension.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = health.read(supervision / "latest-session.json") or {}
        if state.get("status") not in {"starting", "watching", "continue", "auditing"} or not health.alive(state.get("pid")):
            raise RuntimeError("No live watch to extend; use a new session or explicit --attach-pid")
        if state.get("deadline_at", 0) <= time.time():
            raise RuntimeError("Watch deadline already passed; start or attach a new session")
        previous = health.read(supervision / "extension-request.json")
        if previous and previous.get("session") == state["directory"] and previous.get("id") != state.get("extension_id"):
            raise RuntimeError("An extension request is already pending")
        request = {"id": uuid.uuid4().hex, "session": state["directory"], "at": time.time(),
                   "deadline_at": state["deadline_at"] + hours * 3600, "hours_added": hours}
        health.write(supervision / "extension-request.json", request)
        return request


def session(campaign, checkout, command, resume, scope, interval=300, hours=6, audit_timeout=240, attach_pid=None, allow_verdict_repair=False):
    if not all(math.isfinite(v) and v > 0 for v in (interval, hours, audit_timeout)):
        raise ValueError("Session limits must be positive and finite")
    if not resume or (attach_pid is None and not command) or (attach_pid is not None and command):
        raise ValueError("Supply a resume command and exactly one of start command or attach PID")
    supervision = campaign.path("supervision")
    supervision.mkdir(exist_ok=True)
    with (supervision / "timer.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("A supervision timer already owns this campaign") from None
        previous = health.read(supervision / "latest-session.json")
        if attach_pid is None and previous and health.alive(previous.get("runner_pid")):
            raise RuntimeError("Previous session's runner PID is still alive; inspect before starting another")
        snapshot = health.snapshot(campaign)
        if snapshot["stop"] or (attach_pid is None and any(c["pid_alive"] or c["child_alive"] for c in snapshot["active_calls"])):
            raise RuntimeError("Campaign is stopped or has live calls; inspect before starting")
        recorded = snapshot["runner"]
        if attach_pid is None and recorded and recorded["status"] in {"running", "draining"} and recorded["pid_alive"]:
            raise RuntimeError("Campaign already has a live runner")
        proc = None
        if attach_pid is not None:
            if not isinstance(attach_pid, int) or attach_pid <= 0:
                raise ValueError("Attach PID must be positive")
            known = (recorded or {}).get("pid") or (previous or {}).get("runner_pid")
            if attach_pid != known:
                raise RuntimeError("Attach PID does not match campaign evidence")
            proc = AttachedProcess(attach_pid)
        directory = supervision / uuid.uuid4().hex
        directory.mkdir()
        state = {"pid": os.getpid(), "status": "starting", "started_at": time.time(),
                 "interval_seconds": interval, "scope": scope, "command": command,
                 "resume_command": resume, "directory": str(directory),
                 "deadline_at": time.time() + hours * 3600, "attach_pid": attach_pid,
                 "previous_session": (previous or {}).get("directory"),
                 "verdict_repair_command": ([sys.executable, "-m", "pathfinder.cli", "--root", str(campaign.root),
                                             "repair-verdict"] if allow_verdict_repair else None)}
        if proc is not None:
            state["process_identity"] = proc.identity
            state["previous_runner_log"] = str(Path(previous["directory"]) / "runner.log") if previous else None

        def save(**changes):
            state.update(changes, updated_at=time.time())
            health.write(directory / "session.json", state)
            health.write(supervision / "latest-session.json", state)
            if changes.get("status") == "needs_operator":
                alerts.emit(campaign, "supervision needs operator", directory / "session.json")

        deadline = time.monotonic() + hours * 3600
        save()
        try:
            if proc is None:
                with (directory / "runner.log").open("a") as log:
                    proc = subprocess.Popen(command, cwd=checkout, stdin=subprocess.DEVNULL,
                                            stdout=log, stderr=log, start_new_session=True)
            save(status="watching", runner_pid=proc.pid)
            print(f"supervision {directory}; runner pid {proc.pid}; audit every {interval}s", flush=True)
            index = 0
            next_audit = time.monotonic() + interval
            while True:
                extension = health.read(supervision / "extension-request.json")
                if extension and extension.get("session") == str(directory) and extension.get("id") != state.get("extension_id"):
                    new_deadline = extension.get("deadline_at")
                    if not isinstance(new_deadline, (int, float)) or not math.isfinite(new_deadline) or new_deadline <= state["deadline_at"]:
                        raise RuntimeError("Invalid supervision extension request")
                    deadline += new_deadline - state["deadline_at"]
                    save(deadline_at=new_deadline, extension_id=extension["id"])
                if time.monotonic() >= deadline:
                    break
                remaining = max(0, min(next_audit, deadline) - time.monotonic())
                if proc.poll() is None:
                    try:
                        proc.wait(timeout=min(5, remaining))
                    except subprocess.TimeoutExpired:
                        if time.monotonic() < next_audit and time.monotonic() < deadline:
                            continue
                elif index:
                    threading.Event().wait(min(5, remaining))
                    if time.monotonic() < next_audit and time.monotonic() < deadline:
                        continue
                if time.monotonic() >= deadline:
                    break
                index += 1
                call_dir = directory / f"audit-{index:03d}"
                call_dir.mkdir()
                save(status="auditing", audit=index, runner_exit=proc.poll())
                result = audit(campaign, checkout, call_dir, resume, scope,
                               min(audit_timeout, max(.01, deadline - time.monotonic())))
                print(f"audit {index}: {result['status']}: {result['summary']}", flush=True)
                if result["status"] == "complete" and proc.poll() is None:
                    result = {"status": "needs_operator", "summary": "Astra reported completion but original runner is still alive"}
                if result["status"] == "complete":
                    latest = health.snapshot(campaign)
                    active_runner = latest["runner"] and latest["runner"]["status"] in {"running", "draining"} and latest["runner"]["pid_alive"]
                    if active_runner or any(c["pid_alive"] or c["child_alive"] for c in latest["active_calls"]):
                        result = {"status": "needs_operator", "summary": "Completion conflicts with recorded live runner/call; inspect before ending supervision"}
                save(status=result["status"], summary=result["summary"])
                if result["status"] != "continue":
                    return 0 if result["status"] == "complete" else 1
                next_audit = next_audit + interval
                if next_audit <= time.monotonic():
                    next_audit = time.monotonic() + interval  # Skip missed ticks, never overlap audits.
            save(status="needs_operator", summary="Supervision time limit reached; runner was not killed")
            print(state["summary"], flush=True)
            return 1
        except KeyboardInterrupt:
            runner.request_stop(campaign, "supervision interrupted by operator")
            save(status="needs_operator", summary="Timer interrupted; stop requested, active work may still be draining")
            return 130
        except Exception as error:
            save(status="needs_operator", summary=repr(error))
            print(f"supervision needs operator: {error}; runner was not killed", flush=True)
            return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--scope", help="what must finish, including paper stages if applicable")
    ap.add_argument("--resume-command", help="approved command, shell-quoted; executed without a shell")
    ap.add_argument("--attach-pid", type=int, help="monitor the recorded live runner without launching it again")
    ap.add_argument("--extend-hours", type=float, help="request more time for the current watch; launches no runner")
    ap.add_argument("--allow-verdict-repair", action="store_true", help="authorize guarded repair of saved terminal verdict escaping")
    ap.add_argument("--interval", type=float, default=300)
    ap.add_argument("--hours", type=float, default=6)
    ap.add_argument("--audit-timeout", type=float, default=240)
    ap.add_argument("command", nargs=argparse.REMAINDER, help="runner command after --")
    ns = ap.parse_args(argv)
    if ns.extend_hours is not None:
        if ns.command or ns.attach_pid is not None or ns.scope or ns.resume_command or ns.allow_verdict_repair:
            ap.error("--extend-hours only takes --root; it cannot launch or attach work")
        print(json.dumps(extend(config.load(ns.root), ns.extend_hours), indent=2))
        return 0
    command = ns.command[1:] if ns.command[:1] == ["--"] else ns.command
    resume = shlex.split(ns.resume_command or "")
    if not ns.scope or not resume or bool(command) == (ns.attach_pid is not None) or not all(math.isfinite(v) and v > 0 for v in (ns.interval, ns.hours, ns.audit_timeout)):
        ap.error("supply scope, resume command, start command OR attach PID, and positive finite limits")
    checkout = Path(__file__).resolve().parents[1]
    return session(config.load(ns.root), checkout, command, resume, ns.scope,
                   ns.interval, ns.hours, ns.audit_timeout, attach_pid=ns.attach_pid,
                   allow_verdict_repair=ns.allow_verdict_repair)


if __name__ == "__main__":
    sys.exit(main())

"""Campaign-scoped foreground timer. Astra diagnoses; this module only schedules."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import threading
import time
import uuid

from . import config, health, runner

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
        "runner_log": str(directory.parent / "runner.log")}, indent=2) + """

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


def session(campaign, checkout, command, resume, scope, interval=300, hours=6, audit_timeout=240):
    supervision = campaign.path("supervision")
    supervision.mkdir(exist_ok=True)
    with (supervision / "timer.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("A supervision timer already owns this campaign") from None
        previous = health.read(supervision / "latest-session.json")
        if previous and health.alive(previous.get("runner_pid")):
            raise RuntimeError("Previous session's runner PID is still alive; inspect before starting another")
        snapshot = health.snapshot(campaign)
        if snapshot["stop"] or any(c["pid_alive"] or c["child_alive"] for c in snapshot["active_calls"]):
            raise RuntimeError("Campaign is stopped or has live calls; inspect before starting")
        recorded = snapshot["runner"]
        if recorded and recorded["status"] in {"running", "draining"} and recorded["pid_alive"]:
            raise RuntimeError("Campaign already has a live runner")
        directory = supervision / uuid.uuid4().hex
        directory.mkdir()
        state = {"pid": os.getpid(), "status": "starting", "started_at": time.time(),
                 "interval_seconds": interval, "scope": scope, "command": command,
                 "resume_command": resume, "directory": str(directory)}

        def save(**changes):
            state.update(changes, updated_at=time.time())
            health.write(directory / "session.json", state)
            health.write(supervision / "latest-session.json", state)

        deadline = time.monotonic() + hours * 3600
        save()
        try:
            with (directory / "runner.log").open("a") as log:
                proc = subprocess.Popen(command, cwd=checkout, stdin=subprocess.DEVNULL,
                                        stdout=log, stderr=log, start_new_session=True)
            save(status="watching", runner_pid=proc.pid)
            print(f"supervision {directory}; runner pid {proc.pid}; audit every {interval}s", flush=True)
            index = 0
            next_audit = time.monotonic() + interval
            while time.monotonic() < deadline:
                remaining = max(0, min(next_audit, deadline) - time.monotonic())
                if proc.poll() is None:
                    try:
                        proc.wait(timeout=remaining)
                    except subprocess.TimeoutExpired:
                        pass
                elif index:
                    threading.Event().wait(remaining)
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
    ap.add_argument("--scope", required=True, help="what must finish, including paper stages if applicable")
    ap.add_argument("--resume-command", required=True, help="approved command, shell-quoted; executed without a shell")
    ap.add_argument("--interval", type=float, default=300)
    ap.add_argument("--hours", type=float, default=6)
    ap.add_argument("--audit-timeout", type=float, default=240)
    ap.add_argument("command", nargs=argparse.REMAINDER, help="runner command after --")
    ns = ap.parse_args(argv)
    command = ns.command[1:] if ns.command[:1] == ["--"] else ns.command
    resume = shlex.split(ns.resume_command)
    if not command or not resume or min(ns.interval, ns.hours, ns.audit_timeout) <= 0:
        ap.error("supply start/resume commands and positive time limits")
    checkout = Path(__file__).resolve().parents[1]
    return session(config.load(ns.root), checkout, command, resume, ns.scope,
                   ns.interval, ns.hours, ns.audit_timeout)


if __name__ == "__main__":
    sys.exit(main())

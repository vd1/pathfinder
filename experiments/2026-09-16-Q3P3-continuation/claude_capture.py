"""Capture native engine calls without altering prompts or CLI arguments."""
import datetime
import fcntl
import json
from pathlib import Path
import signal
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "doc/logs"
OUTPUTS = LOGS / "claude_outputs"
OUTPUTS.mkdir(parents=True, exist_ok=True)
call_id = "claude-" + uuid.uuid4().hex
child = None
cancelled = False

def record(status, terminal=False):
    with (LOGS / "calls.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        event = {"call_id": call_id, "owner": "research engine", "creativity": "CLI default",
            "purpose": "Q3P3 continuation", "status": status,
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        with (ROOT / "schedule.jsonl").open("a") as stream:
            stream.write(json.dumps(event) + "\n")
        if terminal:
            with (LOGS / "claude_call_log.md").open("a") as stream:
                stream.write(f"- `{call_id}`: Q3P3 continuation, {status}.\n")

def stop(signum, frame):
    global cancelled
    cancelled = True
    if child is not None and child.poll() is None:
        child.terminate()

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
record("running")
code = 1
try:
    with (OUTPUTS / f"{call_id}.txt").open("wb") as output:
        child = subprocess.Popen(["claude", *sys.argv[1:]], stdin=sys.stdin, stdout=subprocess.PIPE, stderr=sys.stderr)
        for line in child.stdout:
            output.write(line)
            output.flush()
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
        code = child.wait()
finally:
    record("cancelled" if cancelled else ("completed" if code == 0 else "failed"), terminal=True)
sys.exit(code)

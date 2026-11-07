"""Start a long Pathfinder command detached from the calling shell, then confirm it is alive.

A PID alone is not evidence: the launcher waits, checks the process is still running and reports the log tail
if it is not. The command runs in its own session with its output in <root>/logs/launch-<UTC>.log, and
launch.json records what was started. Ported from statarb's arxiv_drip.launch."""
from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path


def command(root: Path, args: list[str]) -> list[str]:
    return [sys.executable, "-u", "-m", "pathfinder.cli", "--root", str(root), *args]   # -u: the log fills as it runs


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def launch(argv: list[str], log: Path, settle_seconds: float, cwd: Path) -> int:
    log = Path(log); log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "ab") as stream:
        process = subprocess.Popen(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
    time.sleep(settle_seconds)
    if process.poll() is not None or not alive(process.pid):
        tail = log.read_text(errors="replace")[-2000:] if log.exists() else ""
        raise RuntimeError(f"exited within {settle_seconds} s (code {process.returncode}); log {log}:\n{tail}")
    return process.pid


def run(root: Path, args: list[str], settle_seconds: float = 20.0) -> dict:
    root = Path(root).resolve()
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    argv = command(root, args)
    log = root / "logs" / f"launch-{stamp}.log"
    pid = launch(argv, log, settle_seconds, root)
    record = {"pid": pid, "argv": argv, "log": str(log), "started_at": stamp}
    (root / "launch.json").write_text(json.dumps(record, indent=1))
    with (root / "launches.jsonl").open("a") as stream:        # concurrent launches keep every PID on record
        stream.write(json.dumps(record) + "\n")
    return record

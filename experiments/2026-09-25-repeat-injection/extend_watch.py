"""One authorized six-hour supervision handoff; never launches a second runner."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import launch

ROOT = Path(__file__).resolve().parent
RECORD = ROOT / "supervision/extension.json"
EXPIRY = "Supervision time limit reached; runner was not killed"


def eligible(state, directory):
    return state.get("directory") == directory and state.get("status") == "needs_operator" and state.get("summary") == EXPIRY


def live_work(snapshot):
    r = snapshot.get("runner") or {}
    return bool(r.get("pid_alive") or any(
        c.get("pid_alive") or c.get("child_alive") for c in snapshot["active_calls"]))


def watch():
    config, health, _ = launch.setup_runtime()
    from pathfinder import supervise
    campaign = config.load(ROOT)
    initial = launch.read(ROOT / "supervision/latest-session.json")
    directory = initial["directory"]
    deadline = initial["started_at"] + 12 * 3600
    record = {"pid": os.getpid(), "status": "waiting", "authorized_additional_hours": 6,
              "original_directory": directory, "deadline_at": deadline,
              "authorization": "User: let's grant the extension; supervision only, unchanged research caps"}
    def save(**kw):
        record.update(kw, updated_at=time.time())
        launch.save(RECORD, record)
    with (ROOT / "supervision/extension.lock").open("a+") as own:
        fcntl.flock(own, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save()
        with (ROOT / "supervision/timer.lock").open("a+") as lock:
            while time.time() < deadline:
                state = launch.read(ROOT / "supervision/latest-session.json")
                if state.get("directory") != directory or state.get("status") == "complete":
                    save(status="not_needed", summary="Original watch completed or was superseded")
                    return
                if state.get("status") == "needs_operator" and not eligible(state, directory):
                    save(status="needs_operator", summary="Original watch stopped for a reason other than expiry")
                    return
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    time.sleep(10)
                    continue
                state = launch.read(ROOT / "supervision/latest-session.json")
                if not eligible(state, directory):
                    save(status="needs_operator", summary="Watch lock released without a verified time-limit handoff")
                    return
                break
            else:
                save(status="needs_operator", summary="Extension deadline passed before handoff")
                return
            session_dir = Path(directory)
            state.update(pid=os.getpid(), status="watching", extension_deadline_at=deadline,
                         previous_supervisor_pid=state.get("pid"), extension_started_at=time.time())
            def session_save(**kw):
                state.update(kw, updated_at=time.time())
                health.write(session_dir / "session.json", state)
                health.write(ROOT / "supervision/latest-session.json", state)
            session_save()
            save(status="watching", summary="Took timer lock after expiry; existing runner untouched")
            index = state.get("audit", 0)
            try:
                while time.time() < deadline:
                    tick_started = time.time()
                    index += 1
                    call_dir = session_dir / f"audit-{index:03d}"
                    call_dir.mkdir()
                    session_save(status="auditing", audit=index)
                    result = supervise.audit(campaign, ROOT / "engine", call_dir,
                        state["resume_command"], state["scope"], min(240, deadline - time.time()))
                    if result["status"] == "complete" and live_work(health.snapshot(campaign)):
                        result = {"status": "needs_operator", "summary": "Completion conflicts with live work"}
                    session_save(**result)
                    save(**result, audit=index)
                    print(json.dumps(result), flush=True)
                    if result["status"] != "continue":
                        return
                    next_tick = min(deadline, max(tick_started + 300, time.time()))
                    while time.time() < next_tick:
                        time.sleep(max(0, min(10, next_tick - time.time())))
                result = {"status": "needs_operator", "summary": "Extended supervision limit reached; runner was not killed"}
                session_save(**result)
                save(**result)
            except BaseException as error:
                result = {"status": "needs_operator", "summary": repr(error)}
                session_save(**result)
                save(**result)
                raise


if __name__ == "__main__":
    if sys.argv[1:] == ["launch"]:
        with (ROOT / "supervision/extension-launch.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if RECORD.exists() or (ROOT / "supervision/extension-launch.json").exists():
                raise SystemExit("Extension already requested; inspect existing records")
            with (ROOT / "supervision/extension.log").open("x") as log:
                child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "watch"],
                    cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            launch.save(ROOT / "supervision/extension-launch.json", {"pid": child.pid, "at": time.time()})
            print(json.dumps({"extension_pid": child.pid}))
    elif sys.argv[1:] == ["watch"]:
        watch()
    else:
        raise SystemExit("Use launch or watch")

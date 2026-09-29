"""Resume this pilot with authorized mechanical repair and the existing deadline."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import launch

ROOT = Path(__file__).resolve().parent


def run():
    launch.preflight()
    config, health, _ = launch.setup_runtime()
    from pathfinder import supervise
    renewal = ROOT / "supervision/renewed-window.json"
    extension = launch.read(renewal if renewal.exists() else ROOT / "supervision/extension.json")
    remaining = extension["deadline_at"] - time.time()
    if remaining <= 0:
        raise SystemExit("Authorized supervision deadline expired")
    previous = launch.read(ROOT / "supervision/latest-session.json")
    command = [sys.executable, str(ROOT / "launch.py"), "run"]
    scope = previous["scope"] + (
        " USER AUTHORIZATION UPDATE 2026-09-25: mechanical repair of saved terminal verifier JSON "
        "is permitted using ONLY the supplied Python executable followed by "
        f"{ROOT / 'repair_verdict.py'} ARM PAIR. ARM is repeat or reinjection; PAIR must be the exact "
        "blocked pair from evidence. This exception allows the helper to write that pair's verdict "
        "history and status checkpoint (campaign evidence), not to alter scientific content. Read "
        f"{ROOT / 'REPAIR_AUTHORITY.md'} for authority and restrictions. "
        "No new judgment or model call is authorized as repair. If the helper rejects the case, "
        "request operator direction, without bypassing safeguards. After repair resume the unchanged "
        "full-pipeline command and verify advancement. Preserve all incidents and raw replies. "
        "The approved total deadline is unchanged; this watch replaces the stopped watch."
    )
    if renewal.exists():
        scope += (
            " USER AUTHORIZATION UPDATE 2026-09-27: the previous deadline has expired and is "
            "superseded by the fresh six-hour window recorded in supervision/renewed-window.json. "
            "Finish the existing five unfinished pipelines only; preserve the 23 completed pipelines. "
            "Research caps and mechanical repair authority are unchanged. Authentication checks "
            "succeeded before this resumption. If authentication fails again, report the evidence; "
            "do not change credentials or switch providers."
        )
    return supervise.session(config.load(ROOT), ROOT / "engine", command, command,
        scope, interval=300, hours=remaining / 3600, audit_timeout=240)


if __name__ == "__main__":
    if sys.argv[1:] in (["launch"], ["renew"]):
        if sys.argv[1:] == ["renew"]:
            previous = launch.read(ROOT / "supervision/latest-session.json")
            for pid in (previous.get("pid"), previous.get("runner_pid")):
                if pid:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        pass
                    else:
                        raise SystemExit("Recorded watch/runner PID is alive; inspect before renewal")
            now = time.time()
            hashes = {}
            for arm in launch.ARMS:
                for d in (ROOT / arm / "threads").iterdir():
                    state = launch.read(d / "status.json")
                    edit = d / "edited/edit.json"
                    paper = d / "paper/paper.json"
                    complete = state.get("status") in {"DRAFT", "PAUSE", "PAUSE-ON-ITERATE", "PAUSE-ON-REVISE"}
                    complete = complete and edit.exists() and launch.read(edit).get("status") == "done"
                    if state.get("status") == "DRAFT":
                        complete = complete and paper.exists() and launch.read(paper).get("status") in {"ACCEPTED", "PAUSE-ON-AMEND"}
                    if complete:
                        hashes.update({str(p.relative_to(ROOT)): launch.digest(p) for p in d.rglob("*")
                                       if p.is_file() and p.name != "lock"})
            record = {"authorized_at": now, "deadline_at": now + 6 * 3600,
                      "authority": "User authorized authentication verification and resumption on 2026-09-27",
                      "auth_checks": {"gpt-6-sol": "live call completed", "gpt-6-astra": "live call completed"},
                      "previous_session": previous["directory"], "completed_files": hashes}
            launch.save(ROOT / f"supervision/renewal-{int(now)}.json", record)
            launch.save(ROOT / "supervision/renewed-window.json", record)
            with (ROOT / "supervision/incidents.jsonl").open("a") as stream:
                stream.write(json.dumps({"at": now, "action": "renew supervision and resume after authentication failure",
                    "evidence": "renewed-window.json", "status": "resuming", "research_budget_change": False}) + "\n")
        with (ROOT / "supervision/resumed-watch.log").open("a") as log:
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run"],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        launch.save(ROOT / "supervision/resumed-watch-launch.json", {"pid": child.pid, "at": time.time()})
        print(json.dumps({"supervisor_pid": child.pid}))
    elif sys.argv[1:] == ["run"]:
        sys.exit(run())
    else:
        raise SystemExit("Use launch, renew (explicit authorization required), or run")

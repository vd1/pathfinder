"""A runner records how it was launched, and a runner that vanished without recording a failure is named as
such. proofTree planar S21 (8 October 2026): the controller, six peers and the drain watcher vanished together
with no receipt and no failure; health showed only six orphaned call records and the playbook was empty. The
cause, confirmed from Codex's logs: a Codex daemon's graceful restart tore down the tool sessions that owned
the controller and its watcher."""
import json, os, time
from pathfinder import health, playbook, runner
from stubcampaign import make


def test_the_runner_records_its_launch(tmp_path):
    c = make(tmp_path)
    launch = runner.launch_record()
    assert launch["ppid"] == os.getppid() and launch["pgid"] == os.getpgid(0) and launch["sid"] == os.getsid(0)
    assert launch["own_group"] == (os.getpgid(0) == os.getpid()) and "parent" in launch


def _vanished(c, own_group):
    now = time.time()
    health.write(c.path("runner.json"), {"run_id": "r", "pid": 999999, "status": "running", "heartbeat_at": now - 30,
                 "last_progress": None, "launch": {"ppid": 1234, "pgid": 1234, "sid": 1234, "own_group": own_group,
                                                   "parent": "codex exec --json"}})


def test_a_vanished_runner_inside_its_launchers_group_is_named_with_the_cause_to_check(tmp_path):
    c = make(tmp_path)
    _vanished(c, own_group=False)
    warnings = " ".join(health.snapshot(c)["warnings"])
    assert "without recording a failure" in warnings and "codex exec" in warnings and "detached" in warnings


def test_a_vanished_runner_gets_an_apex_action(tmp_path):
    c = make(tmp_path)
    _vanished(c, own_group=True)
    action = next(a for a in playbook.next_actions(c) if a["action"].startswith("runner gone"))
    assert action["owner"] == "apex" and "reconcile" in action["why"]


def test_launch_warns_when_the_runner_shares_an_agent_tool_sessions_group(capsys):
    runner.warn_if_attached({"own_group": False, "parent": "/usr/local/bin/codex exec --json"})
    assert "detached" in capsys.readouterr().err
    runner.warn_if_attached({"own_group": True, "parent": "/usr/local/bin/codex exec --json"})
    runner.warn_if_attached({"own_group": False, "parent": "-zsh"})
    assert capsys.readouterr().err == ""


def test_detach_starts_a_command_in_its_own_session_with_its_output_in_a_log(tmp_path):
    import subprocess, sys
    log = tmp_path / "run.log"
    probe = "import os; print(os.getsid(0), os.getpgid(0))"
    out = subprocess.run([sys.executable, "-m", "pathfinder.detach", str(log), "--", sys.executable, "-c", probe],
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0 and out.stdout.strip().isdigit()          # prints the detached process's pid
    deadline = time.time() + 10
    while time.time() < deadline and not (log.exists() and log.read_text().strip()):
        time.sleep(0.1)
    sid, pgid = map(int, log.read_text().split())
    assert sid != os.getsid(0) and pgid != os.getpgid(0)                   # out of the launcher's session and group

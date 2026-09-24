import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from pathfinder import cli, edit, health, monitor, research, runner, transport
from test_runner import make


def test_heartbeat_is_not_progress_and_deadline_is_not_deadlock(tmp_path):
    c = make(tmp_path)
    now = time.time()
    health.write(c.path("runner.json"), {"run_id": "r", "pid": os.getpid(), "status": "running",
                 "heartbeat_at": now - 301, "last_progress": None})
    health.write(c.path("active-calls/a.json"), {"attempt_id": "a", "pid": os.getpid(),
                 "thread": "Q1P1", "stage": "peer", "actor": "ada", "started_at": now - 400,
                 "deadline_at": now - 1})
    snapshot = health.snapshot(c)
    assert snapshot["runner"]["last_progress"] is None
    assert snapshot["active_calls"][0]["overdue_seconds"] >= 1
    assert any("heartbeat" in w for w in snapshot["warnings"])
    assert any("Overdue" in w for w in snapshot["warnings"])
    assert "deadlock" not in " ".join(snapshot["warnings"])


def test_campaign_owner_is_exclusive_and_released_on_crash(tmp_path):
    c = make(tmp_path)
    code = "from pathlib import Path; from types import SimpleNamespace; from pathfinder import health; import os; c=SimpleNamespace(path=lambda p:Path(os.environ['AUDIT_ROOT'])/p); ctx=health.owner(c); ctx.__enter__(); print('owned', flush=True); input()"
    child = subprocess.Popen([sys.executable, "-c", code], env={**os.environ, "AUDIT_ROOT": str(tmp_path)},
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "owned"
        with pytest.raises(RuntimeError, match="already owns"):
            with health.owner(c):
                pass
    finally:
        child.kill()
        child.wait(timeout=5)
        child.stdin.close()
        child.stdout.close()
    with health.owner(c):
        pass


def test_restart_refuses_live_orphan_child(tmp_path):
    c = make(tmp_path)
    health.write(c.path("active-calls/a.json"), {"child_pid": os.getpid()})
    with pytest.raises(RuntimeError, match="unresolved active call"):
        with health.owner(c):
            pass


def test_terminal_research_resumes_only_editing(tmp_path, monkeypatch):
    c = make(tmp_path, seats=1)
    health.write(c.path("shortlist.json"), {"pairs": [{"pair_id": "Q1P1"}]})
    health.write(c.thread_dir("Q1P1") / "status.json", {"status": "PAUSE", "stage": "done"})
    health.write(c.thread_dir("Q1P1") / "edited/edit.json", {"status": "stopped"})
    monkeypatch.setattr(research, "run_thread", lambda *a, **k: pytest.fail("research repeated"))
    calls = []
    def finish(campaign, pair_id, stop):
        calls.append(pair_id)
        edit._set(campaign, pair_id, status="done")
        return "done"
    monkeypatch.setattr(edit, "run", finish)
    assert runner.run(c, interval=.01) == 0
    assert calls == ["Q1P1"] and runner.pending(c) == []


def test_editor_failure_is_visible_and_restart_retains_incident(tmp_path, monkeypatch):
    c = make(tmp_path, seats=1)
    health.write(c.path("shortlist.json"), {"pairs": [{"pair_id": "Q1P1"}]})
    health.write(c.thread_dir("Q1P1") / "status.json", {"status": "DRAFT", "stage": "done"})
    def fail(*a, **kw):
        raise transport.TransportFailed("editor unavailable")
    monkeypatch.setattr(edit, "run", fail)
    assert runner.run(c, interval=.01) == 1
    assert health.snapshot(c)["failure"]["stage"] == "edit"
    assert health.snapshot(c)["work"][0]["needs_edit"]
    assert runner.run(c, interval=.01) == 1
    assert len(c.path("failures.jsonl").read_text().splitlines()) == 2
    assert health.read(c.path("runner.json"))["previous_failure"]["stage"] == "edit"


def test_unrelated_success_does_not_clear_failure(tmp_path, monkeypatch):
    c = make(tmp_path, seats=2)
    health.write(c.path("shortlist.json"), {"pairs": [{"pair_id": "Q1P1"}, {"pair_id": "Q1P2"}]})
    both_started = threading.Barrier(2)
    def work(campaign, pair_id):
        both_started.wait(timeout=5)
        if pair_id == "Q1P1":
            raise transport.TransportFailed("failed pair")
        deadline = time.monotonic() + 5
        while not runner.unhealthy(campaign) and time.monotonic() < deadline:
            time.sleep(.01)
        assert runner.unhealthy(campaign)
        return "PAUSE"
    monkeypatch.setattr(runner, "_work", work)
    assert runner.run(c, interval=.01) == 1
    assert health.read(c.path("health.json"))["pair"] == "Q1P1"


def test_cli_health_is_read_only_json(tmp_path, capsys):
    make(tmp_path)
    health.write(tmp_path / "campaign.json", {"model": "m", "backend": "claude", "allowances": {}, "budget_usd": 9})
    before = set(tmp_path.rglob("*"))
    cli.main(["--root", str(tmp_path), "health", "--json"])
    snapshot = json.loads(capsys.readouterr().out)
    assert snapshot["runner"] is None
    assert snapshot["warnings"] and set(tmp_path.rglob("*")) == before
    assert monitor.state(make(tmp_path))["operational"]["runner"] is None


def test_active_call_is_observable_while_child_is_running(tmp_path, monkeypatch):
    c = make(tmp_path)
    monkeypatch.setattr(transport, "_command", lambda *a: [sys.executable, "-c",
        'import json,sys; print(json.dumps({"session_id":"test"}),flush=True); sys.stdin.read(); input()'])
    # The real child waits for stdin EOF, then exits; observe the active record at launch.
    original = health.write
    seen = []
    def capture(path, data):
        original(path, data)
        if "child_pid" in data:
            seen.append(health.snapshot(c)["active_calls"][0])
    monkeypatch.setattr(health, "write", capture)
    transport.call("prompt", campaign=c, model="m", tools=False, search=False,
                   cwd=tmp_path, timeout=2, thread="Q1P1", stage="peer", actor="ada")
    assert seen[0]["child_alive"] and seen[0]["deadline_at"] > seen[0]["started_at"]
    assert health.snapshot(c)["active_calls"] == []


def test_partial_receipt_does_not_hide_health_snapshot(tmp_path):
    c = make(tmp_path)
    c.path("receipts.jsonl").write_text('{"outcome":"completed","at":"yesterday"}\n{"outcome":')
    (c.thread_dir("Q1P1")).mkdir(parents=True)
    (c.thread_dir("Q1P1") / "status.json").write_text('{"status":')
    s = health.snapshot(c)
    assert s["last_completed_call"]["at"] == "yesterday"
    assert any("receipt" in w for w in s["warnings"])
    assert any("status.json" in w for w in s["warnings"])


def test_dead_runner_is_reported_and_a_long_call_is_not_overdue(tmp_path):
    c = make(tmp_path)
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait(timeout=5)
    now = time.time()
    health.write(c.path("runner.json"), {"run_id": "crashed", "pid": child.pid,
                 "status": "running", "heartbeat_at": now})
    health.write(c.path("active-calls/a.json"), {"attempt_id": "a", "pid": child.pid,
                 "thread": "Q1P1", "stage": "peer", "actor": "ada", "started_at": now - 500,
                 "deadline_at": now + 500})
    s = health.snapshot(c)
    assert s["runner"]["pid_alive"] is False
    assert s["active_calls"][0]["overdue_seconds"] == 0
    assert any("PID is absent" in w for w in s["warnings"])
    assert not any("Overdue" in w for w in s["warnings"])


def test_research_cli_returns_nonzero_for_a_real_launch_failure(tmp_path):
    make(tmp_path)
    health.write(tmp_path / "campaign.json", {"model": "m", "backend": "claude",
                 "allowances": {"peer_seconds": 1, "peer_calls": 1}, "budget_usd": 99, "seats": 1})
    for side in ("Q", "P"):
        (tmp_path / f"{side}.jsonl").write_text('{"id":"a","title":"A","abstract":"aa","text":null}\n')
    health.write(tmp_path / "shortlist.json", {"pairs": [{"pair_id": "Q1P1"}]})
    result = subprocess.run([sys.executable, "-m", "pathfinder.cli", "--root", str(tmp_path), "research"],
                            env={**os.environ, "PATHFINDER_CLAUDE": str(tmp_path / "missing-binary")},
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 1, result.stderr
    assert "inspect `pathfinder health`" in result.stdout
    assert health.read(tmp_path / "health.json")["pair"] == "Q1P1"


def test_supervision_drill_crashes_and_resumes_only_the_fixture_editor(tmp_path):
    script = Path(__file__).with_name("supervision_trial.py")
    def run(action):
        return subprocess.run([sys.executable, str(script), action, str(tmp_path)],
                              capture_output=True, text=True, timeout=10)
    assert run("prepare").returncode == 0
    before = (tmp_path / "threads/Q1P1/status.json").read_bytes()
    assert run("crash").returncode == 23
    assert health.read(tmp_path / "runner.json")["status"] == "running"
    assert run("resume").returncode == 0
    assert health.read(tmp_path / "runner.json")["status"] == "finished"
    assert health.read(tmp_path / "resumed-stage.json")["stage"] == "edit"
    assert (tmp_path / "threads/Q1P1/status.json").read_bytes() == before

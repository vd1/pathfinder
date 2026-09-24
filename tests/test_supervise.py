import fcntl
from pathlib import Path
import subprocess
import sys
import time

import pytest

from pathfinder import config, health, supervise


def campaign(tmp_path):
    health.write(tmp_path / "campaign.json", {"backend": "claude", "model": "unused",
                 "allowances": {}, "budget_usd": 9})
    health.write(tmp_path / "shortlist.json", {"pairs": []})
    return config.load(tmp_path)


def run(c, command, **kw):
    return supervise.session(c, Path(__file__).resolve().parents[1], command, command,
                             "isolated test command", interval=.05, hours=.001, **kw)


def test_stops_after_complete_without_another_audit(tmp_path, monkeypatch):
    calls = []
    def audit(*a):
        calls.append(a)
        return {"status": "complete", "summary": "fixture complete"}
    monkeypatch.setattr(supervise, "audit", audit)
    c = campaign(tmp_path)
    assert run(c, [sys.executable, "-c", "pass"]) == 0
    assert len(calls) == 1
    assert health.read(tmp_path / "supervision/latest-session.json")["status"] == "complete"


def test_timer_fires_while_runner_is_alive_and_stops_for_operator(tmp_path, monkeypatch):
    c = campaign(tmp_path)
    def audit(*a):
        state = health.read(tmp_path / "supervision/latest-session.json")
        assert health.alive(state["runner_pid"])
        return {"status": "needs_operator", "summary": "test decision"}
    monkeypatch.setattr(supervise, "audit", audit)
    assert run(c, [sys.executable, "-c", "import time; time.sleep(.2)"]) == 1
    pid = health.read(tmp_path / "supervision/latest-session.json")["runner_pid"]
    # The timer must not kill the runner when asking for input; reap this test child.
    import os
    assert os.waitpid(pid, 0)[1] == 0


def test_no_successful_completion_over_a_live_runner(tmp_path, monkeypatch):
    monkeypatch.setattr(supervise, "audit", lambda *a: {"status": "complete", "summary": "incorrect claim"})
    c = campaign(tmp_path)
    assert run(c, [sys.executable, "-c", "import time; time.sleep(.2)"]) == 1
    state = health.read(tmp_path / "supervision/latest-session.json")
    assert "still alive" in state["summary"]
    import os
    os.waitpid(state["runner_pid"], 0)


def test_audit_failure_stops_the_timer(tmp_path, monkeypatch):
    def fail(*a):
        raise subprocess.TimeoutExpired("codex", 1)
    monkeypatch.setattr(supervise, "audit", fail)
    c = campaign(tmp_path)
    assert run(c, [sys.executable, "-c", "pass"]) == 1
    assert "TimeoutExpired" in health.read(tmp_path / "supervision/latest-session.json")["summary"]


def test_tick_repeats_then_ends(tmp_path, monkeypatch):
    times = []
    def audit(*a):
        times.append(time.monotonic())
        return {"status": "continue" if len(times) == 1 else "complete", "summary": "fixture"}
    monkeypatch.setattr(supervise, "audit", audit)
    assert run(campaign(tmp_path), [sys.executable, "-c", "pass"]) == 0
    assert len(times) == 2 and times[1] - times[0] >= .02


def test_stop_marker_prevents_launch(tmp_path):
    c = campaign(tmp_path)
    health.write(tmp_path / "stop.json", {"reason": "operator"})
    with pytest.raises(RuntimeError, match="stopped"):
        run(c, ["not-an-executable"])


def test_session_time_limit_is_visible(tmp_path, monkeypatch):
    monkeypatch.setattr(supervise, "audit", lambda *a: {"status": "continue", "summary": "fixture"})
    c = campaign(tmp_path)
    command = [sys.executable, "-c", "pass"]
    assert supervise.session(c, tmp_path, command, command, "test", interval=.01, hours=.00002) == 1
    assert "time limit" in health.read(tmp_path / "supervision/latest-session.json")["summary"]


def test_second_timer_cannot_launch_work(tmp_path):
    c = campaign(tmp_path)
    c.path("supervision").mkdir()
    with c.path("supervision/timer.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="already owns"):
            run(c, ["must-not-launch"])


def test_slow_audits_skip_ticks_instead_of_accumulating(tmp_path, monkeypatch):
    starts = []
    def audit(*a):
        starts.append(time.monotonic())
        if len(starts) == 1:
            time.sleep(.08)
            return {"status": "continue", "summary": "slow audit"}
        return {"status": "complete", "summary": "done"}
    monkeypatch.setattr(supervise, "audit", audit)
    assert run(campaign(tmp_path), [sys.executable, "-c", "pass"]) == 0
    assert starts[1] - starts[0] >= .12


def test_process_evidence_excludes_unrelated_processes(monkeypatch):
    rows = "20 1 20 runner\n21 20 21 child\n22 21 21 descendant\n99 1 99 unrelated\n"
    monkeypatch.setattr(supervise.subprocess, "run", lambda *a, **k:
                        subprocess.CompletedProcess(a[0], 0, stdout=rows))
    evidence = supervise.processes([20])
    assert evidence["available"]
    assert {p["pid"] for p in evidence["related_processes"]} == {20, 21, 22}


def test_unavailable_process_evidence_is_explicit(monkeypatch):
    def denied(*a, **kw):
        raise PermissionError("ps denied")
    monkeypatch.setattr(supervise.subprocess, "run", denied)
    assert supervise.processes([20])["available"] is False

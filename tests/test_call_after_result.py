"""A call ends at its final event (Atlas pilot 6, 24 October 2026): the Claude CLI emitted its result, then stayed
alive 38 minutes waiting on a shell job its agent had started and abandoned, until the operator killed the job.
Once the final event is in (Claude's result, Codex's turn.completed), the engine gives the CLI RESULT_GRACE seconds
to exit, then ends its process group and any descendant that left it, and the call stands as completed."""
import os, sys, time
from pathlib import Path
import pytest
from pathfinder import transport
from stubcampaign import make

FAKE = f"{sys.executable} {Path(__file__).parent / 'fake_cli.py'}"


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.mark.parametrize("backend, setsid", [("claude", False), ("claude", True), ("codex", False)])
def test_a_cli_lingering_after_its_final_event_is_ended_and_the_call_completes(tmp_path, monkeypatch, backend, setsid):
    c = make(tmp_path, backend=backend, model="m")
    monkeypatch.setenv("PATHFINDER_CLAUDE" if backend == "claude" else "PATHFINDER_CODEX", FAKE)
    monkeypatch.setenv("FAKE_MODE", backend); monkeypatch.setenv("FAKE_REPLY", "the answer")
    monkeypatch.setenv("FAKE_LINGER", "120"); monkeypatch.setenv("FAKE_LINGER_PID", str(tmp_path / "child.pid"))
    if setsid:
        monkeypatch.setenv("FAKE_LINGER_SETSID", "1")       # a job that left the CLI's process group
    monkeypatch.setattr(transport, "RESULT_GRACE", 1)
    started = time.time()
    r = transport.call("hi", campaign=c, model="m", tools=False, search=False, cwd=tmp_path, timeout=60,
                       thread="Q1P1", stage="peer", actor="ada")
    assert time.time() - started < 30
    assert r["outcome"] == "completed" and r["text"] == "the answer" and not r["transport_failed"]
    assert r["ended_after_final_event"] is True
    pid = int((tmp_path / "child.pid").read_text())
    for _ in range(20):
        if not _alive(pid):
            break
        time.sleep(0.1)
    assert not _alive(pid)


def test_a_cli_that_exits_after_its_final_event_is_not_ended(tmp_path, monkeypatch):
    c = make(tmp_path, backend="claude", model="m")
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setenv("FAKE_REPLY", "ok")
    r = transport.call("hi", campaign=c, model="m", tools=False, search=False, cwd=tmp_path, timeout=60,
                       thread="Q1P1", stage="peer", actor="ada")
    assert r["outcome"] == "completed" and r.get("ended_after_final_event") is False and r["exit_status"] == 0


def test_final_event_survives_trailing_diagnostics_and_error_stays_error(tmp_path, monkeypatch):
    c = make(tmp_path, backend="claude", model="m")
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE)
    monkeypatch.setenv("FAKE_LINGER", "120")
    monkeypatch.setenv("FAKE_AFTER_FINAL_EVENTS", "50")
    monkeypatch.setenv("FAKE_ERROR", "1")
    monkeypatch.setenv("FAKE_REPLY", "invalid request")
    monkeypatch.setattr(transport, "RESULT_GRACE", .1)
    r = transport.call("hi", campaign=c, model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=10, thread="Q1P1", stage="peer", actor="ada")
    assert r["ended_after_final_event"] and r["transport_failed"]
    assert r["outcome"] == "error" and "invalid request" in r["error"]

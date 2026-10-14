"""A call record whose runner and child are both dead is retired by `reconcile --retire-orphans`, which touches
no thread, and by `reconcile --apply` or `--repair-only` (nobel, 14 October 2026): a runner that ended with its agent session left five records in active-calls/, which
only a returning call removes, so health warned about them and the campaign state counted their threads as
active for good. Retiring one removes the record and appends a call_abandoned event that keeps what the record
held; a record with a live runner or child, or one whose liveness is unknown, stays."""
import json
import os
import subprocess
import sys
import time
from pathfinder import campaign_state, cli, events, health
from stubcampaign import make


def _dead_pid():
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait(timeout=5)
    return child.pid


def _record(c, attempt, pid, child_pid, thread="Q1P1"):
    now = time.time()
    health.write(c.path(f"active-calls/{attempt}.json"), {
        "attempt_id": attempt, "run_id": "dead-run", "pid": pid, "thread": thread, "stage": "peer", "actor": "ada",
        "started_at": now - 600, "deadline_at": now + 300, "timeout_seconds": 900, "cwd": None, "child_pid": child_pid})


def _abandoned(c):
    return [e for e in events.read(c)[0] if e["kind"] == "call_abandoned"]


def test_a_record_with_dead_runner_and_child_is_retired_with_an_event(tmp_path):
    c = make(tmp_path)
    dead = _dead_pid()
    _record(c, "gone", dead, dead)
    assert any("Orphaned call record gone" in w and "reconcile --retire-orphans" in w for w in health.snapshot(c)["warnings"])
    assert campaign_state.build(c)["units"][0]["controller"] == "running"
    retired = health.retire_orphans(c)
    assert [r["attempt_id"] for r in retired] == ["gone"]
    assert not c.path("active-calls/gone.json").exists()
    [event] = _abandoned(c)
    assert (event["attempt_id"], event["unit"], event["stage"], event["actor"]) == ("gone", "Q1P1", "peer", "ada")
    assert event["call_run_id"] == "dead-run" and event["child_pid"] == dead and event["receipt"] is None
    assert not any("Orphaned" in w for w in health.snapshot(c)["warnings"])
    assert campaign_state.build(c)["units"][0]["controller"] != "running"


def test_a_record_with_a_live_runner_or_child_or_unknown_liveness_stays(tmp_path):
    c = make(tmp_path)
    dead = _dead_pid()
    _record(c, "runner-alive", os.getpid(), dead)
    _record(c, "child-alive", dead, os.getpid())
    _record(c, "unknown", None, None)
    assert health.retire_orphans(c) == []
    assert len(list(c.path("active-calls").glob("*.json"))) == 3 and _abandoned(c) == []


def test_a_record_written_before_its_child_launched_is_retired_when_its_runner_is_dead(tmp_path):
    c = make(tmp_path)
    _record(c, "unlaunched", _dead_pid(), None)
    assert [r["attempt_id"] for r in health.retire_orphans(c)] == ["unlaunched"]


def test_reconcile_retires_only_on_apply_and_only_for_the_named_pair(tmp_path, capsys):
    c = make(tmp_path)
    dead = _dead_pid()
    _record(c, "mine", dead, dead, thread="Q1P1")
    _record(c, "other", dead, dead, thread="Q9P9")
    cli.main(["--root", str(tmp_path), "reconcile", "Q1P1"])
    assert "orphaned call record mine" in capsys.readouterr().out and c.path("active-calls/mine.json").exists()
    cli.main(["--root", str(tmp_path), "reconcile", "Q1P1", "--repair-only"])
    assert "retired orphaned call record mine" in capsys.readouterr().out
    assert not c.path("active-calls/mine.json").exists() and c.path("active-calls/other.json").exists()


def test_retire_orphans_alone_touches_no_thread_while_a_runner_holds_the_campaign(tmp_path, capsys, monkeypatch):
    from pathfinder import reconcile
    c = make(tmp_path)
    dead = _dead_pid()
    _record(c, "gone", dead, dead)
    monkeypatch.setattr(reconcile, "apply", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no thread action")))
    cli.main(["--root", str(tmp_path), "reconcile", "--retire-orphans"])
    out = capsys.readouterr().out
    assert "retired orphaned call record gone" in out and "start" not in out
    assert not c.path("active-calls/gone.json").exists()

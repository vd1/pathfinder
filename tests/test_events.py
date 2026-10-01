import json, threading
import pytest
from pathfinder import events
from stubcampaign import make


def test_emit_appends_one_typed_line(tmp_path):
    c = make(tmp_path)
    events.emit(c, "status_changed", unit="Q1P1", axis="research", to="running")
    rows, truncated = events.read(c)
    assert not truncated and len(rows) == 1
    assert rows[0]["kind"] == "status_changed" and rows[0]["unit"] == "Q1P1" and rows[0]["v"] == 1 and rows[0]["at"]


def test_unknown_kind_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        events.emit(make(tmp_path), "something_else")


def test_concurrent_emits_never_interleave(tmp_path):
    c = make(tmp_path)
    def burst(n):
        for i in range(200):
            events.emit(c, "call_started", unit=f"Q{n}P1", stage="peer", detail="x" * 500)
    threads = [threading.Thread(target=burst, args=(n,)) for n in range(4)]
    [t.start() for t in threads]; [t.join() for t in threads]
    rows, truncated = events.read(c)
    assert not truncated and len(rows) == 800


def test_a_partial_last_line_is_reported_as_truncation(tmp_path):
    c = make(tmp_path)
    events.emit(c, "run_started", execution_id="e1")
    with c.path("events.jsonl").open("a") as f:
        f.write('{"v": 1, "kind": "call_star')
    rows, truncated = events.read(c)
    assert truncated and len(rows) == 1


def test_a_write_error_does_not_raise(tmp_path, capsys):
    c = make(tmp_path)
    c.path("events.jsonl").mkdir()                    # a directory where the file should be
    events.emit(c, "run_started")
    assert "event not recorded" in capsys.readouterr().err

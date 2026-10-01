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


def test_a_stub_research_run_records_calls_and_transitions(tmp_path):
    from pathfinder import research
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    rows, _ = events.read(c)
    kinds = [r["kind"] for r in rows]
    assert kinds.count("call_started") == kinds.count("call_finished") > 0
    research_changes = [r for r in rows if r["kind"] == "status_changed" and r["axis"] == "research"]
    assert research_changes[0]["from"] in (None, "new") and research_changes[-1]["to"] == research.status(c, "Q1P1")["status"]
    assert all(r["unit"] == "Q1P1" for r in rows if r["kind"] in ("call_started", "call_finished"))


def test_status_changed_only_when_the_status_changes(tmp_path):
    from pathfinder import edit
    c = make(tmp_path)
    c.thread_dir("Q1P1").mkdir(parents=True)
    edit._set(c, "Q1P1", status="editing", attempt=1)
    edit._set(c, "Q1P1", status="editing", attempt=2)
    edit._set(c, "Q1P1", status="blocked", reason="r")
    changes = [r for r in events.read(c)[0] if r["kind"] == "status_changed"]
    assert [(r["axis"], r["from"], r["to"]) for r in changes] == [("editorial", "none", "editing"), ("editorial", "editing", "blocked")]


def test_stops_are_recorded_with_their_class(tmp_path):
    from pathfinder import failures, runner
    c = make(tmp_path)
    failures.stop_for(c, failures.classify("error", "You've hit your usage limit."), "usage limit")
    runner.request_stop(c, "operator")
    stops = [r for r in events.read(c)[0] if r["kind"] == "stop_requested"]
    assert stops[0]["failure_class"] == "quota" and stops[0]["scope"] == "campaign"
    assert stops[1]["failure_class"] is None and stops[1]["reason"] == "operator"

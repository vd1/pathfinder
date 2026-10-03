"""Fixes from the phase 9 review."""
import json, math, os, threading, time
from pathlib import Path
import pytest
from pathfinder import composable, config, import_eva2, monitor, probe, research, seats, supervise
from stubcampaign import make


def test_the_monitor_state_is_valid_json_without_a_dollar_cap(tmp_path):
    c = make(tmp_path, budget={"calls": 10})
    raw = json.loads((tmp_path / "campaign.json").read_text()); raw.pop("budget_usd", None)
    (tmp_path / "campaign.json").write_text(json.dumps(raw))
    c = config.load(tmp_path)
    text = json.dumps(monitor.state(c), allow_nan=False)            # raises on Infinity
    assert "Infinity" not in text and "no dollar cap" in monitor.status_text(c)


def test_a_branch_citing_its_papers_still_resolves_them_in_the_bundle(tmp_path):
    c = make(tmp_path, research_scheme="composable", branches=1, strict_evidence=True)
    b = composable.branch_view(c, "Q1P1", "branch-1")
    d = research.prepare(b, "Q1P1")
    from pathfinder.ledger import Ledger
    Ledger(d / "ledger.jsonl").add("ada", "finding", "Q states the bound in inputs/Q.txt.")
    assert research.run_thread(c, "Q1P1") == "DRAFT"


def test_a_state_poll_during_a_take_never_fails_the_call(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_ACCOUNTS", str(tmp_path / "accounts"))
    c = make(tmp_path / "c", account={"name": "main", "seats": 50})
    stop, errors = threading.Event(), []

    def poll():
        while not stop.is_set():
            seats.in_use(c)
    t = threading.Thread(target=poll); t.start()
    try:
        for _ in range(200):
            try:
                seats.release(seats.take(c, stage="peer", actor="ada", thread="Q1P1"))
            except RuntimeError as error:
                errors.append(error)
    finally:
        stop.set(); t.join()
    assert not errors


def test_retryable_failures_do_not_wake_an_audit_but_campaign_wide_ones_do(tmp_path):
    from pathfinder import events
    c = make(tmp_path)
    events.emit(c, "call_finished", unit="Q1P1", stage="peer", outcome="timeout", failure_class="timeout")
    events.emit(c, "call_finished", unit="Q1P1", stage="peer", outcome="error", failure_class="rate")
    assert supervise.wake_reason(c, 0)[0] is None
    events.emit(c, "call_finished", unit="Q1P1", stage="peer", outcome="error", failure_class="quota")
    assert "quota" in supervise.wake_reason(c, 0)[0]


def test_event_audits_keep_a_floor_between_them(tmp_path, monkeypatch):
    c = make(tmp_path)
    times = []
    def audit(*a):
        times.append(time.monotonic())
        from pathfinder import events
        events.emit(c, "stop_requested", reason="again")      # would wake the next audit at once
        return {"status": "continue", "summary": "x"} if len(times) < 2 else {"status": "needs_operator", "summary": "y"}
    monkeypatch.setattr(supervise, "audit", audit)
    monkeypatch.setattr(supervise, "WAKE_FLOOR", 1.0)
    from pathfinder import events
    script = ("import time; time.sleep(30)")
    def first_event():
        time.sleep(0.3); events.emit(c, "stop_requested", reason="first")
    threading.Thread(target=first_event).start()
    import sys
    supervise.session(c, Path(__file__).resolve().parents[1], [sys.executable, "-c", script], [sys.executable, "-c", script],
                      "floor test", interval=600, hours=.02)
    assert len(times) == 2 and times[1] - times[0] >= 1.0
    state = json.loads((tmp_path / "supervision/latest-session.json").read_text())
    try:
        os.kill(state["runner_pid"], 9)
    except ProcessLookupError:
        pass


def test_eva2_receipts_are_imported_from_the_runtime_store(tmp_path):
    from test_import_eva2 import _eva2
    exp = _eva2(tmp_path)
    store = exp / "runtime" / "receipts"; store.mkdir(parents=True)
    (store / "abc.json").write_text(json.dumps({
        "seconds": 12.0, "usage": {"input_tokens": 4000, "cached_input_tokens": 3000, "output_tokens": 50},
        "cost": None, "outcome": "completed", "route": {"model": "gpt-6-astra"},
        "identity": f"{exp.name}/branch-2/1/0/0/Q1P1:peers:ada:round-1:review-0:repair-0:call-0/retry-1"}))
    out = import_eva2.run(exp, tmp_path / "canon")
    rows = [json.loads(l) for l in (out / "receipts.jsonl").read_text().splitlines()]
    eva2 = [r for r in rows if r.get("call_id") == "abc"]
    assert eva2 and eva2[0]["branch"] == "branch-2" and eva2[0]["stage"] == "peer" and eva2[0]["input_tokens"] == 4000
    assert json.loads((out / "import.json").read_text())["receipts"]["eva2_runtime"] == 1


def test_the_probe_refuses_a_composable_source_and_drops_extensions(tmp_path):
    c = make(tmp_path / "composable", research_scheme="composable")
    with pytest.raises(SystemExit, match="composable"):
        probe.run(c, ["Q1P1"], tmp_path / "out1")
    from test_probe import _finished
    source = _finished(tmp_path / "plain")
    source.raw["extensions"] = {"path": "deploy", "admission": "nowhere:policy"}
    probe.run(source, ["Q1P1"], tmp_path / "out2")
    assert "extensions" not in json.loads((tmp_path / "out2" / "campaign.json").read_text())

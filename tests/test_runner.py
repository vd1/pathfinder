import json, os, threading, time
from pathfinder import research, runner
from pathfinder.config import Campaign


def make(tmp_path, seats=2, budget=99):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=False, seats=seats, cut=1,
                 rounds=1, allowances={"peer_seconds": 1, "peer_calls": 1, "consolidate_seconds": 1, "verify_seconds": 1},
                 budget_usd=budget, prices={}, scan_fulltext=None, call_estimate_usd=1.0)
    (tmp_path / "shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": f"Q1P{j}"} for j in (1, 2, 3)]}))
    return c


def test_guard_writes_stop_when_over_budget(tmp_path):
    c = make(tmp_path, budget=1.5)
    (tmp_path / "receipts.jsonl").write_text(json.dumps({"cost": 1.0}) + "\n")
    assert runner.guard_ok(c, inflight=0)
    assert not runner.guard_ok(c, inflight=1)            # 1.0 + 1 * 1.0 > 1.5
    assert runner.stopped(c) and json.loads((tmp_path / "stop.json").read_text())["reason"].startswith("budget")


def test_stop_drains_in_flight(tmp_path, monkeypatch):
    c = make(tmp_path, seats=1)
    calls = []

    def fake_thread(campaign, pair_id, stop=lambda: False):
        calls.append(pair_id); time.sleep(0.3)
        (campaign.thread_dir(pair_id)).mkdir(parents=True, exist_ok=True)
        (campaign.thread_dir(pair_id) / "status.json").write_text(json.dumps({"status": "PAUSE", "stage": "done", "round": 1}))
        return "PAUSE"
    monkeypatch.setattr(runner.research, "run_thread", fake_thread)
    threading.Timer(0.1, lambda: runner.request_stop(c, "test")).start()
    runner.run(c, interval=0.05)
    assert calls == ["Q1P1"]                           # first admitted, finished; nothing else admitted


def test_lock_and_reconcile_action(tmp_path):
    from pathfinder import reconcile
    c = make(tmp_path); d = c.thread_dir("Q1P1"); d.mkdir(parents=True)
    (d / "status.json").write_text(json.dumps({"pair_id": "Q1P1", "round": 1, "stage": "verify", "status": "stopped"}))
    assert reconcile.inspect(c, "Q1P1")["action"] == "run consolidate"   # no note yet: verify cannot run
    (d / "Q1P1.tex").write_text("x")
    assert reconcile.inspect(c, "Q1P1")["action"] == "run verify"
    with runner.Lock(d):
        assert runner.Lock.holder(d) == os.getpid()
        assert reconcile.inspect(c, "Q1P1")["action"] == "nothing: in progress"
    (d / "lock").write_text("999999")                  # dead pid
    assert runner.Lock.holder(d) is None


def test_first_interrupt_drains(tmp_path, monkeypatch):
    import signal
    c = make(tmp_path, seats=1)
    calls = []

    def fake_thread(campaign, pair_id, stop=lambda: False):
        calls.append(pair_id); time.sleep(0.3)
        (campaign.thread_dir(pair_id)).mkdir(parents=True, exist_ok=True)
        (campaign.thread_dir(pair_id) / "status.json").write_text(json.dumps({"status": "PAUSE", "stage": "done", "round": 1}))
        return "PAUSE"
    monkeypatch.setattr(runner.research, "run_thread", fake_thread)
    before = signal.getsignal(signal.SIGINT)
    threading.Timer(0.1, lambda: os.kill(os.getpid(), signal.SIGINT)).start()
    runner.run(c, interval=0.05)
    assert calls == ["Q1P1"] and json.loads((tmp_path / "stop.json").read_text())["reason"] == "interrupt"
    assert signal.getsignal(signal.SIGINT) is before


def test_two_transport_failures_set_health_and_probe_clears_it(tmp_path, monkeypatch):
    import sys
    from pathlib import Path
    from pathfinder import transport
    monkeypatch.setenv("PATHFINDER_CLAUDE", f"{sys.executable} {Path(__file__).parent / 'fake_cli.py'}")
    monkeypatch.setenv("FAKE_HANG", "1"); monkeypatch.setenv("FAKE_REPLY", "nothing")
    monkeypatch.setattr(transport, "SESSION_GRACE", 1); monkeypatch.setattr(runner, "PROBE_INTERVAL", 0.2)
    c = make(tmp_path, seats=1)
    (tmp_path / "shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": "Q1P1"}, {"pair_id": "Q1P2"}]}))
    (tmp_path / "Q.jsonl").write_text('{"id":"a","title":"A","abstract":"aa","text":null}\n')
    (tmp_path / "P.jsonl").write_text('{"id":"b","title":"B","abstract":"bb","text":null}\n{"id":"c","title":"C","abstract":"cc","text":null}\n')
    seen = {"health": False}

    def watch():
        for _ in range(200):
            if (tmp_path / "health.json").exists():
                seen["health"] = True; monkeypatch.delenv("FAKE_HANG"); return
            time.sleep(0.1)
    threading.Thread(target=watch, daemon=True).start()
    runner.run(c, interval=0.05)
    assert seen["health"] and not (tmp_path / "health.json").exists()
    assert {research.status(c, p)["status"] for p in ("Q1P1", "Q1P2")} == {"PAUSE"}


def test_blocked_threads_are_not_readmitted(tmp_path):
    c = make(tmp_path)
    d = c.thread_dir("Q1P1"); d.mkdir(parents=True)
    (d / "status.json").write_text(json.dumps({"pair_id": "Q1P1", "round": 1, "stage": "verify", "status": "BLOCKED"}))
    assert "Q1P1" not in runner.pending(c) and "Q1P2" in runner.pending(c)

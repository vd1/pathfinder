"""Seats shared across processes by account (H7)."""
import json, os, subprocess, sys, textwrap, threading, time
from pathlib import Path
import pytest
from pathfinder import admission, campaign_state, runner, seats
from pathfinder.admission import Refused
from stubcampaign import make

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def accounts(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_ACCOUNTS", str(tmp_path / "accounts"))
    return tmp_path / "accounts"


def test_a_seat_is_taken_and_released(tmp_path, accounts):
    c = make(tmp_path / "c", account={"name": "main", "seats": 2})
    a = seats.take(c, stage="peer", actor="ada", thread="Q1P1")
    b = seats.take(c, stage="peer", actor="emmy", thread="Q1P1")
    assert a and b and seats.take(c, stage="verify", actor="verifier", thread="Q1P1") is None
    seats.release(a)
    assert seats.in_use(c) == 1
    seats.release(b)
    assert seats.in_use(c) == 0


def test_a_dead_process_holds_no_seat(tmp_path, accounts):
    c = make(tmp_path / "c", account={"name": "main", "seats": 1})
    dead = subprocess.Popen([sys.executable, "-c", "pass"]); dead.wait()
    pool = accounts / "main"; pool.mkdir(parents=True)
    (pool / f"{dead.pid}-stale.json").write_text(json.dumps({"pid": dead.pid, "root": "x"}))
    assert seats.take(c, stage="peer", actor="ada", thread="Q1P1") is not None
    assert not (pool / f"{dead.pid}-stale.json").exists()


def test_no_account_no_pool(tmp_path, accounts):
    c = make(tmp_path / "c")
    with admission.admission(c, "peer", "ada", thread="Q1P1"):
        pass
    assert not accounts.exists()


def test_two_processes_on_one_seat_never_overlap(tmp_path, accounts):
    c = make(tmp_path / "c", account={"name": "main", "seats": 1})
    script = textwrap.dedent(f"""
        import json, sys, time
        sys.path[:0] = [{str(ROOT)!r}, {str(ROOT / 'tests')!r}]
        from pathfinder import admission, config
        c = config.load({str(tmp_path / 'c')!r})
        with admission.admission(c, "peer", sys.argv[1], thread="Q1P1"):
            start = time.time(); time.sleep(0.5); end = time.time()
        print(json.dumps([start, end]))
    """)
    env = {**os.environ, "PATHFINDER_ACCOUNTS": str(accounts)}
    procs = [subprocess.Popen([sys.executable, "-c", script, name], stdout=subprocess.PIPE, text=True, env=env)
             for name in ("ada", "emmy")]
    spans = sorted(json.loads(p.communicate(timeout=30)[0]) for p in procs)
    assert spans[0][1] <= spans[1][0]


def test_a_stop_refuses_a_call_waiting_for_a_seat(tmp_path, accounts):
    c = make(tmp_path / "c", account={"name": "main", "seats": 1})
    held = seats.take(c, stage="peer", actor="ada", thread="Q1P1")
    outcome = {}

    def wait():
        try:
            with admission.admission(c, "peer", "emmy", thread="Q1P1"):
                outcome["ran"] = True
        except Refused as refused:
            outcome["refused"] = str(refused)
    t = threading.Thread(target=wait); t.start()
    time.sleep(0.3)
    runner.request_stop(c, "operator stop")
    t.join(timeout=5)
    seats.release(held)
    assert "refused" in outcome and not t.is_alive()


def test_the_state_shows_the_account(tmp_path, accounts):
    c = make(tmp_path / "c", account={"name": "main", "seats": 3})
    held = seats.take(c, stage="peer", actor="ada", thread="Q1P1")
    assert campaign_state.build(c)["campaign"]["account"] == {"name": "main", "seats": 3, "in_use": 1}
    seats.release(held)

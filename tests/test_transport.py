import json, sys
from pathlib import Path
import pytest
from pathfinder import transport
from pathfinder.config import Campaign

FAKE = str(Path(__file__).parent / "fake_cli.py")


def campaign(tmp_path, backend="claude"):
    return Campaign(root=tmp_path, backend=backend, model="m", scan_model="m", peer_search=True, seats=1,
                    cut=1, rounds=1, allowances={}, budget_usd=9, prices={"m": {"input_per_m": 1.0, "output_per_m": 1.0}},
                    scan_fulltext=None)


@pytest.fixture(autouse=True)
def fake(monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", f"{sys.executable} {FAKE}")
    monkeypatch.setenv("PATHFINDER_CODEX", f"{sys.executable} {FAKE}")
    monkeypatch.setattr(transport, "SESSION_GRACE", 1)


def test_claude_call_returns_text_and_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "claude"); monkeypatch.setenv("FAKE_REPLY", "hello")
    r = transport.call("p", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="scan", actor="judge")
    assert r["text"] == "hello" and r["session"] == "fake-session" and r["cost"] == 0.5
    rows = [json.loads(l) for l in (tmp_path / "receipts.jsonl").read_text().splitlines()]
    assert rows[0]["stage"] == "scan" and transport.spend(campaign(tmp_path)) == 0.5


def test_codex_call_prices_from_table(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "codex"); monkeypatch.setenv("FAKE_REPLY", "hi")
    r = transport.call("p", campaign=campaign(tmp_path, "codex"), model="m", tools=True, search=True, cwd=tmp_path,
                       timeout=10, thread="T", stage="peer", actor="ada")
    assert r["text"] == "hi" and abs(r["cost"] - 110 / 1e6) < 1e-9


def test_no_session_is_transport_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_HANG", "1")
    r = transport.call("p", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="scan", actor="judge")
    assert r["transport_failed"] and r["cost"] == 0 and not (tmp_path / "receipts.jsonl").exists()


def test_timeout_after_session_is_an_error_not_transport(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_DELAY", "0"); monkeypatch.setenv("FAKE_RUN", "sleep 3")
    r = transport.call("p", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=1, thread="T", stage="scan", actor="judge")
    assert r["error"] == "timeout" and not r["transport_failed"]

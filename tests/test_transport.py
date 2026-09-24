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
    assert r["cache_write"] == 7 and r["cache_read"] == 3                      # cache counts travel into the receipt
    assert r["prefix_read"] == 2                                              # the first turn's cache hit, the shared-head measurement
    rows = [json.loads(l) for l in (tmp_path / "receipts.jsonl").read_text().splitlines()]
    assert rows[0]["stage"] == "scan" and transport.spend(campaign(tmp_path)) == 0.5


def test_tool_free_claude_command_uses_supported_flags(tmp_path):
    cmd = transport._command(campaign(tmp_path), "m", tools=False, search=False, cwd=tmp_path)
    assert cmd[-2:] == ["--tools", ""]
    assert "--permission-prompts" not in cmd


def test_claude_api_error_is_a_transport_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_ERROR", "1")
    monkeypatch.setenv("FAKE_REPLY", "You've hit your session limit")
    r = transport.call("p", campaign=campaign(tmp_path), model="m", tools=True, search=True, cwd=tmp_path,
                       timeout=10, thread="T", stage="peer", actor="ada")
    assert r["transport_failed"] and r["outcome"] == "error"
    assert r["error"] == "You've hit your session limit"


def test_codex_call_prices_from_table(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "codex"); monkeypatch.setenv("FAKE_REPLY", "hi")
    r = transport.call("p", campaign=campaign(tmp_path, "codex"), model="m", tools=True, search=True, cwd=tmp_path,
                       timeout=10, thread="T", stage="peer", actor="ada")
    assert r["text"] == "hi" and abs(r["cost"] - 110 / 1e6) < 1e-9


def rows(tmp_path):
    return [json.loads(l) for l in (tmp_path / "receipts.jsonl").read_text().splitlines()]


def test_no_session_is_transport_failure_with_a_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_HANG", "1")
    r = transport.call("p", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="scan", actor="judge")
    assert r["transport_failed"] and r["cost"] is None
    row = rows(tmp_path)[0]
    assert row["v"] == 2 and row["outcome"] == "no session" and row["usage"] is None and row["cost"] is None
    assert row["input_tokens"] is None and row["cost_basis"] is None
    assert transport.spend(campaign(tmp_path)) == 0                    # never reached a session: the guard does not charge it


def test_missing_executable_is_a_transport_failure_with_a_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", str(tmp_path / "no-such-binary"))
    r = transport.call("p", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="scan", actor="judge")
    assert r["transport_failed"] and r["error"].startswith("launch failed")
    row = rows(tmp_path)[0]
    assert row["outcome"] == "launch failed" and row["usage"] is None and row["cost"] is None


def test_killed_call_has_no_usage_and_no_estimate_in_the_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_RUN", "sleep 3")
    c = campaign(tmp_path)
    transport.call("p", campaign=c, model="m", tools=False, search=False, cwd=tmp_path,
                   timeout=1, thread="T", stage="scan", actor="judge")
    row = rows(tmp_path)[0]
    assert row["outcome"] == "timeout" and row["usage"] is None and row["cost"] is None
    assert transport.spend(c) == c.call_estimate_usd                   # the guard counts it; the receipt does not


def test_killed_call_keeps_the_usage_that_was_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_PARTIAL", "1"); monkeypatch.setenv("FAKE_RUN", "sleep 3")
    transport.call("p", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                   timeout=1, thread="T", stage="scan", actor="judge")
    row = rows(tmp_path)[0]
    assert row["outcome"] == "timeout" and row["usage"] == {"input_tokens": 4, "output_tokens": 1}
    assert row["cache_read"] is None                                   # not reported is not zero


@pytest.mark.parametrize("backend", ["claude", "codex"])
def test_missing_counter_is_unknown_and_reported_zero_is_zero(tmp_path, monkeypatch, backend):
    monkeypatch.setenv("FAKE_MODE", backend); c = campaign(tmp_path, backend)
    monkeypatch.setenv("FAKE_USAGE", json.dumps({"input_tokens": 100}))            # output not reported
    transport.call("p", campaign=c, model="m", tools=False, search=False, cwd=tmp_path, timeout=10, thread="T", stage="s", actor="a")
    monkeypatch.setenv("FAKE_USAGE", json.dumps({"input_tokens": 0, "output_tokens": 0}))
    transport.call("p", campaign=c, model="m", tools=False, search=False, cwd=tmp_path, timeout=10, thread="T", stage="s", actor="a")
    missing, zero = rows(tmp_path)
    assert missing["output_tokens"] is None and missing["cost"] is None and missing["cost_basis"] is None
    assert zero["output_tokens"] == 0 and zero["cost"] == 0 and zero["cost_basis"] == "priced"


def test_codex_receipt_keeps_the_raw_counters_and_the_rates(tmp_path, monkeypatch):
    raw = {"input_tokens": 85160, "cached_input_tokens": 9088, "cache_write_input_tokens": 0,
           "output_tokens": 1156, "reasoning_output_tokens": 796}
    monkeypatch.setenv("FAKE_MODE", "codex"); monkeypatch.setenv("FAKE_USAGE", json.dumps(raw))
    transport.call("p", campaign=campaign(tmp_path, "codex"), model="m", tools=False, search=False, cwd=tmp_path,
                   timeout=10, thread="T", stage="s", actor="a")
    row = rows(tmp_path)[0]
    assert row["usage"] == raw and row["cache_read"] == 9088 and row["cache_write"] == 0
    assert row["cost_basis"] == "priced" and row["rates"] == {"input_per_m": 1.0, "output_per_m": 1.0}


def test_codex_cached_input_is_priced_at_the_cached_rate_when_the_table_has_one(tmp_path, monkeypatch):
    raw = {"input_tokens": 1_000_000, "cached_input_tokens": 900_000, "output_tokens": 0}
    monkeypatch.setenv("FAKE_MODE", "codex"); monkeypatch.setenv("FAKE_USAGE", json.dumps(raw))
    c = campaign(tmp_path, "codex"); c.prices = {"m": {"input_per_m": 10.0, "cached_input_per_m": 1.0, "output_per_m": 50.0}}
    transport.call("p", campaign=c, model="m", tools=False, search=False, cwd=tmp_path, timeout=10, thread="T", stage="s", actor="a")
    row = rows(tmp_path)[0]
    assert abs(row["cost"] - 1.9) < 1e-9 and row["rates"]["cached_input_per_m"] == 1.0      # 0.1M at 10 plus 0.9M at 1, not 10.0


def test_reported_cost_is_marked_reported(tmp_path, monkeypatch):
    transport.call("p", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                   timeout=10, thread="T", stage="s", actor="a")
    row = rows(tmp_path)[0]
    assert row["cost"] == 0.5 and row["cost_basis"] == "reported" and "rates" not in row and row["outcome"] == "completed"


def test_timeout_after_session_is_an_operational_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_DELAY", "0"); monkeypatch.setenv("FAKE_RUN", "sleep 3")
    r = transport.call("p", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=1, thread="T", stage="scan", actor="judge")
    assert r["error"] == "timeout" and r["transport_failed"]


def test_codex_custom_provider_flags_and_key(tmp_path):
    (tmp_path / "keys.env").write_text("OTHER=1\nMY_KEY='secret'\n")
    c = campaign(tmp_path, "codex")
    c.raw = {"codex": {"name": "elm", "base_url": "https://example.org/api/v1", "env_key": "MY_KEY", "key_file": "keys.env"}}
    cmd = transport._command(c, "m", tools=True, search=False, cwd=tmp_path)
    assert 'model_provider="elm"' in cmd and 'model_providers.elm.base_url="https://example.org/api/v1"' in cmd and cmd[-1] == "-"
    assert transport._env(c)["MY_KEY"] == "secret"


def test_codex_search_opens_the_sandbox_network(tmp_path):
    c = campaign(tmp_path, "codex")
    search = transport._command(c, "m", tools=True, search=True, cwd=tmp_path)
    no_search = transport._command(c, "m", tools=True, search=False, cwd=tmp_path)
    assert "--search" in search and "sandbox_workspace_write.network_access=true" in search
    assert "--search" not in no_search and "sandbox_workspace_write.network_access=true" not in no_search

import json, sys
from pathlib import Path
import pytest
from pathfinder import transport
from pathfinder.config import Campaign

FAKE = str(Path(__file__).parent / "fake_cli.py")


def campaign(tmp_path, backend="claude"):
    return Campaign(root=tmp_path, backend=backend, model="m", scan_model="m", peer_search=True, seats=1,
                    cut=1, rounds=1, allowances={}, budget_usd=9, prices={"m": {"input_per_m": 1.0, "output_per_m": 1.0}},
                    scan_fulltext=None, raw={"unserved_retries": 0})   # retries are tested on their own


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
    assert row["v"] == 3 and row["outcome"] == "no session" and row["usage"] is None and row["cost"] is None
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


def test_reconnect_error_is_not_a_terminal_failure(tmp_path):
    c = campaign(tmp_path, "codex")
    events = [{"type": "error", "message": "Reconnecting..."},
              {"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}},
              {"type": "turn.completed", "usage": {"input_tokens": 1}}]
    result = transport._parse(c, "m", [json.dumps(x) for x in events])
    assert result[0] == "ok" and result[4] is None
    for event in [{"type": "turn.failed", "error": "denied"}, {"type": "error", "message": "final failure"}]:
        result = transport._parse(c, "m", [json.dumps(x) for x in events + [event]])
        assert result[4]
    events.insert(1, {"type": "turn.failed", "error": "terminal failure"})
    assert transport._parse(c, "m", [json.dumps(x) for x in events])[4]


@pytest.mark.parametrize("complete,exit_code,expected", [(True, 0, "completed"), (True, 1, "error"), (False, 0, "error")])
def test_transport_requires_successful_terminal_completion(tmp_path, monkeypatch, complete, exit_code, expected):
    import sys
    events = [{"type": "thread.started", "thread_id": "fixture"},
              {"type": "error", "message": "Reconnecting..."},
              {"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}}]
    if complete:
        events.append({"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}})
    code = "import sys; sys.stdin.read(); print(" + repr("\n".join(json.dumps(e) for e in events)) + f"); sys.exit({exit_code})"
    monkeypatch.setattr(transport, "_command", lambda *a: [sys.executable, "-c", code])
    result = transport.call("p", campaign=campaign(tmp_path, "codex"), model="m", tools=False,
                            search=False, cwd=tmp_path, timeout=2, thread="T", stage="verify", actor="judge")
    assert result["outcome"] == expected
    assert result["transport_failed"] == (expected != "completed")
    assert any("Reconnecting" in e for e in result["raw_events"])


def test_quota_failure_is_classified_from_structured_events(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "codex")
    monkeypatch.setenv("FAKE_FAIL", "You've hit your usage limit ... try again at Oct 4th, 2026 2:07 AM.")
    r = transport.call("p", campaign=campaign(tmp_path, "codex"), model="m", tools=True, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="peer", actor="ada")
    assert r["error"].startswith("You've hit your usage limit")          # the message, not a dict repr
    row = rows(tmp_path)[0]
    assert row["failure"] == {"class": "quota", "scope": "campaign", "retry": False, "reset_at": "Oct 4th, 2026 2:07 AM"}
    assert r["failure"] == row["failure"]


def test_completed_call_mentioning_limits_is_not_a_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "codex"); monkeypatch.setenv("FAKE_REPLY", "the usage limit and HTTP 429 in the paper")
    transport.call("p", campaign=campaign(tmp_path, "codex"), model="m", tools=True, search=False, cwd=tmp_path,
                   timeout=10, thread="T", stage="peer", actor="ada")
    assert rows(tmp_path)[0]["failure"] is None


def test_receipt_records_prompt_size_and_tool_calls(tmp_path, monkeypatch):
    for mode in ("codex", "claude"):
        (tmp_path / "receipts.jsonl").unlink(missing_ok=True)
        monkeypatch.setenv("FAKE_MODE", mode); monkeypatch.setenv("FAKE_TOOLS", "3")
        transport.call("x" * 1234, campaign=campaign(tmp_path, mode), model="m", tools=True, search=False,
                       cwd=tmp_path, timeout=10, thread="T", stage="peer", actor="ada")
        row = rows(tmp_path)[0]
        assert (row["prompt_chars"], row["tool_calls"]) == (1234, 3)


def test_no_session_receipt_is_classified_and_sized(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_HANG", "1")
    transport.call("abc", campaign=campaign(tmp_path), model="m", tools=False, search=False, cwd=tmp_path,
                   timeout=10, thread="T", stage="scan", actor="judge")
    row = rows(tmp_path)[0]
    assert row["failure"]["class"] == "no_session" and row["prompt_chars"] == 3 and row["tool_calls"] is None


def test_transient_error_then_completion_stays_unclassified(tmp_path):
    c = campaign(tmp_path, "codex")
    events = [{"type": "error", "message": "Reconnecting... 2/5 (stream disconnected before completion)"},
              {"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}},
              {"type": "turn.completed", "usage": {"input_tokens": 1}}]
    assert transport._parse(c, "m", [json.dumps(x) for x in events])[4] is None


def test_quota_receipt_stops_the_campaign(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "codex"); monkeypatch.setenv("FAKE_FAIL", "You've hit your usage limit.")
    transport.call("p", campaign=campaign(tmp_path, "codex"), model="m", tools=True, search=False, cwd=tmp_path,
                   timeout=10, thread="T", stage="peer", actor="ada")
    assert json.loads((tmp_path / "stop.json").read_text())["failure"]["class"] == "quota"


def test_prompt_at_limit_runs_and_one_over_is_refused_without_launch(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "codex")
    c = campaign(tmp_path, "codex"); c.raw["max_prompt_chars"] = 50
    r = transport.call("x" * 50, campaign=c, model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="verify", actor="judge")
    assert r["outcome"] == "completed"
    monkeypatch.setenv("PATHFINDER_CODEX", str(tmp_path / "must-not-launch"))
    with pytest.raises(transport.PromptTooLarge, match="51 characters exceed 50"):
        transport.call("x" * 51, campaign=c, model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="verify", actor="judge")
    row = rows(tmp_path)[-1]
    assert row["outcome"] == "refused" and row["prompt_chars"] == 51
    assert row["failure"]["class"] == "input_too_large" and row["usage"] is None
    assert not (tmp_path / "stop.json").exists()          # a call-scoped refusal, not a campaign stop
    assert len(rows(tmp_path)) == 2                       # no launch-failed receipt: nothing was launched


def test_default_limit():
    from pathfinder.config import Campaign
    assert transport.max_prompt_chars(Campaign(root=Path("."), backend="codex", model="m", scan_model="m",
                                               peer_search=False, seats=1, cut=1, rounds=1, allowances={},
                                               budget_usd=1, prices={}, scan_fulltext=None)) == 1_000_000


def test_a_broken_failure_rules_extension_still_writes_the_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_MODE", "codex")
    deploy = tmp_path / "deploy"; deploy.mkdir()
    (deploy / "bad_rules_pkg.py").write_text("RULES = [('contract', 'x')]\n")
    c = campaign(tmp_path, "codex"); c.raw["extensions"] = {"path": "deploy", "failure_rules": "bad_rules_pkg:RULES"}
    r = transport.call("p", campaign=c, model="m", tools=False, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="verify", actor="judge")
    assert r["outcome"] == "completed"
    row = rows(tmp_path)[0]
    assert row["outcome"] == "completed" and "unknown failure class" in row["failure_rules_error"]


def test_receipt_counts_tool_errors_with_samples(tmp_path, monkeypatch):
    for mode in ("codex", "claude"):
        (tmp_path / "receipts.jsonl").unlink(missing_ok=True)
        monkeypatch.setenv("FAKE_MODE", mode); monkeypatch.setenv("FAKE_TOOLS", "4"); monkeypatch.setenv("FAKE_TOOL_FAIL", "2")
        transport.call("p", campaign=campaign(tmp_path, mode), model="m", tools=True, search=False, cwd=tmp_path,
                       timeout=10, thread="T", stage="peer", actor="ada")
        row = rows(tmp_path)[0]
        assert row["tool_calls"] == 4 and row["tool_errors"] == 2
        assert all("No module named pathfinder.ledger" in s for s in row["tool_error_samples"])


def test_readers_get_read_only_tools(tmp_path):
    codex = transport._command(campaign(tmp_path, "codex"), "m", True, False, tmp_path, reads=True)
    assert codex[codex.index("--sandbox") + 1] == "read-only" and "features.shell_tool=false" not in " ".join(codex)
    claude = transport._command(campaign(tmp_path), "m", True, False, tmp_path, reads=True)
    assert claude[claude.index("--tools") + 1] == "Read,Glob,Grep"


def _results(*classes):
    out = []
    for cls in classes:
        if cls is None:
            out.append({"text": "ok", "transport_failed": False, "error": None, "outcome": "completed", "failure": None})
        else:
            out.append({"text": "", "transport_failed": True, "error": cls, "outcome": "error",
                        "failure": {"class": cls, "scope": "call", "retry": cls != "timeout", "reset_at": None}})
    return out


def test_an_unserved_call_is_retried_once(tmp_path, monkeypatch):
    c = campaign(tmp_path, "codex"); c.raw.update(retry_backoff_seconds=0, unserved_retries=1)
    queue = _results("rate", None)
    monkeypatch.setattr(transport, "_attempt", lambda campaign, request: queue.pop(0))
    r = transport.execute(c, transport.ModelRequest(identity="i", prompt="p", model="m", tools=False, search=False,
                                                    timeout=5, thread="T", stage="verify", actor="judge"))
    assert r["outcome"] == "completed" and queue == []


def test_timeouts_and_second_failures_are_not_retried(tmp_path, monkeypatch):
    c = campaign(tmp_path, "codex"); c.raw.update(retry_backoff_seconds=0, unserved_retries=1)
    for classes, calls in ((("timeout", None), 1), (("no_session", "no_session", None), 2)):
        queue = _results(*classes)
        monkeypatch.setattr(transport, "_attempt", lambda campaign, request: queue.pop(0))
        r = transport.execute(c, transport.ModelRequest(identity="i", prompt="p", model="m", tools=False, search=False,
                                                        timeout=5, thread="T", stage="verify", actor="judge"))
        assert r["transport_failed"] and len(classes) - len(queue) == calls


def test_a_rate_limit_after_the_session_started_is_not_retried(tmp_path, monkeypatch):
    c = campaign(tmp_path, "codex"); c.raw.update(retry_backoff_seconds=0, unserved_retries=1)
    served = _results("rate", None); served[0]["session"] = "thread-1"
    monkeypatch.setattr(transport, "_attempt", lambda campaign, request: served.pop(0))
    r = transport.execute(c, transport.ModelRequest(identity="i", prompt="p", model="m", tools=False, search=False,
                                                    timeout=5, thread="T", stage="verify", actor="judge"))
    assert r["transport_failed"] and len(served) == 1


def _filesystem(cmd):
    from pathfinder import sandbox
    value = next(v for v in cmd if v.startswith(f"permissions.{sandbox.NAME}.filesystem="))
    return value.split("=", 1)[1]


def test_the_sandbox_profile_writes_only_the_workspace_and_reads_its_control_files(tmp_path, monkeypatch):
    from pathfinder import sandbox
    monkeypatch.setenv("TMPDIR", str(tmp_path / "parent-tmp"))
    d = tmp_path / "threads" / "Q1P1"
    branch = d / "branch-runs" / "branch-1"
    branch.mkdir(parents=True)
    engine = Path(transport.__file__).resolve().parent.parent
    joint = sandbox.profile(d, engine, tools=True, read=["/opt/tex"], deny=[tmp_path / "secret"])
    fs = joint[f"permissions.{sandbox.NAME}.filesystem"]
    assert joint["default_permissions"] == sandbox.NAME and joint[f"permissions.{sandbox.NAME}.network.enabled"] is False
    assert fs[str(d.resolve())] == "write" and fs[str(engine / "pathfinder")] == "read"
    for name in ("inputs", "branches", "branch-runs", "status.json", "handoff.json", "external-references.json"):
        assert fs[str(d.resolve() / name)] == "read", name      # joint peers never write into the branches' record
    assert fs["/tmp"] == fs["/private/tmp"] == fs[str((tmp_path / "parent-tmp").resolve())] == "none"
    assert fs["/opt/tex"] == "read" and fs[str((tmp_path / "secret").resolve())] == "none"
    one = sandbox.profile(branch, engine, tools=True)[f"permissions.{sandbox.NAME}.filesystem"]
    assert str(branch.resolve()) in one and not any("branch-2" in p or p == str(d.resolve()) for p in one)
    reader = sandbox.profile(d, engine, tools=False)[f"permissions.{sandbox.NAME}.filesystem"]
    assert reader[str(d.resolve())] == "read" and str(d.resolve() / "branches") not in reader
    assert sandbox.toml({"a": {"b c": "read"}, "n": False}) == '{"a" = {"b c" = "read"}, "n" = false}'
    monkeypatch.setenv("TMPDIR", str(branch / ".pathfinder" / "tmp"))      # the agent's own, as transport sets it
    assert str((branch / ".pathfinder" / "tmp").resolve()) not in sandbox.profile(branch, engine, tools=True)[
        f"permissions.{sandbox.NAME}.filesystem"]


def test_a_campaign_filesystem_profile_replaces_the_sandbox_mode_per_request(tmp_path):
    from pathfinder import sandbox
    c = campaign(tmp_path, "codex")
    plain = transport._command(c, "m", True, True, tmp_path)
    c.raw = {"codex": {"filesystem_profile": {"read": ["/opt/tex"]}}}
    work = transport._command(c, "m", True, True, tmp_path / "w")
    reader = transport._command(c, "m", True, False, tmp_path / "r", reads=True)
    assert "--sandbox" in plain and "--sandbox" not in work and "--sandbox" not in reader and work[-1] == "-"
    assert f'default_permissions="{sandbox.NAME}"' in work and "sandbox_workspace_write.network_access=true" not in work
    assert '"write"' in _filesystem(work) and str(tmp_path / "w") in _filesystem(work)
    assert '"/opt/tex" = "read"' in _filesystem(work)
    assert '"write"' not in _filesystem(reader)                  # a reader's workspace is read-only
    assert f"permissions.{sandbox.NAME}.network.enabled=true" in work      # searching peers keep their network

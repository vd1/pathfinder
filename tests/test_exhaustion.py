"""A provider subscription exhausted for one campaign pauses every campaign's calls to that provider (Codex or
Claude) until the reset time the provider gave, then they go on by themselves."""
import json, threading, time
from datetime import datetime, timedelta, timezone
import pytest
from pathfinder import admission, cli, events, exhaustion, health, transport
from stubcampaign import make


def _iso(seconds):
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.parametrize("text, check", [
    ("You've hit your usage limit. Try again at 2026-10-04T02:07:00Z.", lambda u, s: u.startswith("2026-10-04T02:07") and s == "provider"),
    ("Claude usage limit reached. Your limit will reset in 2 hours.", lambda u, s: s == "provider"),
    ("usage limit", lambda u, s: s == "default"),
])
def test_the_reset_time_is_read_from_the_providers_message(text, check):
    until, source = exhaustion.reset_time(text)
    assert check(until, source)


def test_a_quota_failure_records_a_pause_for_its_provider(tmp_path):
    c = make(tmp_path, backend="codex")
    transport._receipt(c, "Q1P1", "peer", "ada", "gpt-6.1-sol",
                       {"outcome": "failed", "error": f"You've hit your usage limit. Try again at {_iso(3600)}."})
    pause = exhaustion.active("codex")
    assert pause and pause["campaign"] == str(tmp_path) and exhaustion.active("claude") is None


def _admit(campaign, stage="peer", seen=None):
    with admission.admission(campaign, stage, "ada", thread="Q1P1", model="m"):
        if seen is not None:
            seen.append(time.time())


def test_another_campaign_on_the_same_provider_waits_until_the_reset(tmp_path):
    other = make(tmp_path / "other", backend="codex")
    exhaustion.record("codex", f"usage limit; try again at {_iso(2)}", campaign=tmp_path / "first")
    start, seen = time.time(), []
    _admit(other, seen=seen)
    assert seen[0] - start >= 1.0                       # held until the reset, then admitted without anyone's help
    deferred = [e for e in events.read(other)[0] if e.get("kind") == "admission_deferred"]
    assert deferred and "codex subscription exhausted" in deferred[0]["reason"]


def test_a_campaign_on_another_provider_is_not_held(tmp_path):
    exhaustion.record("codex", f"try again at {_iso(3600)}")
    c = make(tmp_path, backend="claude")
    start = time.time(); _admit(c)
    assert time.time() - start < 1.0


def test_a_stop_marker_still_ends_the_wait(tmp_path):
    exhaustion.record("codex", f"try again at {_iso(3600)}")
    c = make(tmp_path, backend="codex")
    threading.Timer(0.3, lambda: (tmp_path / "stop.json").write_text(json.dumps({"reason": "operator"}))).start()
    with pytest.raises(admission.Refused):
        _admit(c)


def test_health_shows_the_pause_and_the_operator_can_clear_it(tmp_path, capsys):
    c = make(tmp_path, backend="codex")
    exhaustion.record("codex", f"try again at {_iso(3600)}")
    assert any("codex subscription exhausted" in w for w in health.snapshot(c)["warnings"])
    assert cli.main(["--root", str(tmp_path), "pauses"]) in (0, None) and "codex" in capsys.readouterr().out
    assert cli.main(["--root", str(tmp_path), "pauses", "--clear", "codex"]) in (0, None)
    assert exhaustion.active("codex") is None


def test_an_expired_pause_is_no_pause(tmp_path):
    exhaustion.record("codex", f"try again at {_iso(-5)}")
    assert exhaustion.active("codex") is None

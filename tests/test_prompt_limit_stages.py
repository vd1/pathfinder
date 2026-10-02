"""An oversized prompt blocks its pair with the reason; it does not fail the campaign."""
import json
import pytest
from pathfinder import edit, research, transport
from stubcampaign import make


def test_research_blocks_the_pair_on_an_oversized_prompt(tmp_path):
    c = make(tmp_path, max_prompt_chars=10)
    assert research.run_thread(c, "Q1P1") == "BLOCKED"
    assert "input too large" in research.status(c, "Q1P1")["reason"]


def test_composable_research_blocks_the_pair_on_an_oversized_prompt(tmp_path):
    c = make(tmp_path, max_prompt_chars=10, research_scheme="direct_eva")
    assert research.run_thread(c, "Q1P1") == "BLOCKED"
    assert "input too large" in research.status(c, "Q1P1")["reason"]


def test_composable_research_reissues_a_call_stopped_by_a_campaign_scoped_failure(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="direct_eva")
    real, calls = transport.execute, []

    def once_quota(campaign, request):
        calls.append(request.identity)
        if len(calls) == 1:
            return {"text": "", "seconds": 0.0, "transport_failed": True, "error": "You've hit your usage limit.",
                    "failure": {"class": "quota", "scope": "campaign", "retry": False, "reset_at": None}}
        return real(campaign, request)
    monkeypatch.setattr(research.transport, "execute", once_quota)
    with pytest.raises(transport.TransportFailed):
        research.run_thread(c, "Q1P1")
    research.run_thread(c, "Q1P1")      # the stub's direct_eva review later blocks on its own; irrelevant here
    assert calls[1] == calls[0]                           # the same request was issued again
    assert "usage limit" not in (research.status(c, "Q1P1").get("reason") or "")


def test_edit_blocks_the_pair_on_an_oversized_prompt(tmp_path):
    c = make(tmp_path)
    assert research.run_thread(c, "Q1P1") in research.TERMINAL
    c.raw["max_prompt_chars"] = 10
    assert edit.run(c, "Q1P1") == "blocked"
    assert "input too large" in json.loads((c.thread_dir("Q1P1") / "edited/edit.json").read_text())["reason"]


def test_a_stopped_thread_records_the_failure_class(tmp_path, monkeypatch):
    c = make(tmp_path)
    timeout = {"text": "", "seconds": 1.0, "transport_failed": True, "error": "timeout", "outcome": "timeout",
               "failure": {"class": "timeout", "scope": "call", "retry": True, "reset_at": None}}
    monkeypatch.setattr(research.transport, "execute", lambda campaign, request: timeout)
    with pytest.raises(transport.TransportFailed) as raised:
        research.run_thread(c, "Q1P1")
    assert raised.value.failure["class"] == "timeout"
    s = research.status(c, "Q1P1")
    assert s["status"] == "stopped" and s["failure"]["class"] == "timeout" and s["reason"] == "transport failed: timeout"

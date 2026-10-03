"""Tool-call budgets: an agent session resends its context on every turn, so fewer turns is the lever on tokens."""
import json
import pytest
from pathfinder import health, research, transport
from stubcampaign import make


def test_a_role_with_a_budget_is_told_it(tmp_path, monkeypatch):
    c = make(tmp_path, tool_call_budgets={"peer": 15, "consolidate": 6})
    seen = {}
    real = transport.execute
    monkeypatch.setattr(transport, "execute", lambda campaign, request: seen.setdefault(request.stage, request.prompt) and None or real(campaign, request))
    research.run_thread(c, "Q1P1")
    assert "about 15 tool calls" in seen["peer"] and "about 6 tool calls" in seen["consolidate"]
    assert "tool calls" not in seen["verify"].split("## your task")[-1] or "about" not in seen["verify"]


@pytest.mark.parametrize("bad", [{"peer": 0}, {"peer": "many"}, "15"])
def test_a_bad_budget_is_refused_at_load(tmp_path, bad):
    with pytest.raises(ValueError, match="tool_call_budgets"):
        make(tmp_path, tool_call_budgets=bad)


def test_health_names_stages_that_overrun_their_budget(tmp_path):
    c = make(tmp_path, tool_call_budgets={"peer": 10})
    with c.path("receipts.jsonl").open("a") as stream:
        for n, calls in enumerate((8, 30, 35)):
            stream.write(json.dumps({"call_id": f"c{n}", "stage": "peer", "outcome": "completed", "tool_calls": calls}) + "\n")
    warnings = health.snapshot(c)["warnings"]
    assert any("peer" in w and "tool calls" in w and "2 of 3" in w for w in warnings)

"""Budgets in tokens and calls under subscription billing (R6)."""
import json
import pytest
from pathfinder import campaign_state, config, research, runner, transport
from stubcampaign import make


def _receipt(c, **row):
    with c.path("receipts.jsonl").open("a") as stream:
        stream.write(json.dumps({"v": 3, "thread": "Q1P1", "stage": "peer", "actor": "ada", "outcome": "completed",
                                 "input_tokens": 1000, "output_tokens": 100, **row}) + "\n")


def test_every_receipt_names_its_call_and_a_call_is_read_once(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    rows = transport.receipts(c)
    assert rows and all(r.get("call_id") for r in rows) and len({r["call_id"] for r in rows}) == len(rows)
    with c.path("receipts.jsonl").open("a") as stream:          # a receipt written twice (a replayed append)
        stream.write(json.dumps(rows[0]) + "\n")
    assert len(transport.receipts(c)) == len(rows)


def test_a_call_budget_stops_admission_with_its_reason(tmp_path):
    c = make(tmp_path, budget={"calls": 3})
    for n in range(3):
        _receipt(c, call_id=f"c{n}")
    assert runner.guard_ok(c, inflight=1) is False
    assert "calls 4 projected against 3" in json.loads(c.path("stop.json").read_text())["reason"]


def test_a_token_budget_projects_in_flight_calls_at_the_mean(tmp_path):
    c = make(tmp_path, budget={"input_tokens": 5000})
    for n in range(4):
        _receipt(c, call_id=f"c{n}")                      # 4000 used, 1000 per call
    assert runner.guard_ok(c, inflight=1) is True       # 5000 projected: at the cap, not over
    assert runner.guard_ok(c, inflight=2) is False
    assert "input tokens" in json.loads(c.path("stop.json").read_text())["reason"]


def test_calls_that_never_reached_a_model_are_not_charged(tmp_path):
    c = make(tmp_path, budget={"calls": 1})
    _receipt(c, call_id="a", outcome="launch failed", input_tokens=None, output_tokens=None)
    _receipt(c, call_id="b", outcome="refused", input_tokens=None, output_tokens=None)
    assert runner.guard_ok(c, inflight=1) is True


def test_cancelled_and_timed_out_calls_are_counted_and_shown_apart(tmp_path):
    c = make(tmp_path, budget={"input_tokens": 100000})
    _receipt(c, call_id="a")
    _receipt(c, call_id="b", outcome="timeout", input_tokens=700)
    b = campaign_state.build(c)["campaign"]["budget"]
    assert b["input_tokens"] == 1700 and b["interrupted"] == {"calls": 1, "input_tokens": 700, "output_tokens": 100}
    assert b["limits"] == {"input_tokens": 100000}


def test_without_a_dollar_cap_a_subscription_campaign_has_no_dollar_guard(tmp_path):
    raw = json.loads(json.dumps({"backend": "stub", "model": "stub", "allowances": {"peer_seconds": 1, "peer_calls": 1,
           "consolidate_seconds": 1, "verify_seconds": 1}, "budget": {"calls": 10}}))
    (tmp_path / "campaign.json").write_text(json.dumps(raw))
    c = config.load(tmp_path)
    assert c.budget_usd == float("inf")


@pytest.mark.parametrize("bad", [{"calls": -1}, {"calls": "ten"}, {"tokens": 5}, "lots"])
def test_a_malformed_budget_is_refused_at_load(tmp_path, bad):
    with pytest.raises(ValueError, match="budget"):
        make(tmp_path, budget=bad)


def test_a_refusal_after_a_call_on_the_same_thread_is_its_own_receipt(tmp_path):
    from pathfinder.admission import Refused
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    before = len(transport.receipts(c))
    runner.request_stop(c, "operator")
    with pytest.raises(Refused):
        transport.execute(c, transport.ModelRequest(identity="x", prompt="p", model="stub", tools=False, search=False,
                                                    timeout=5, thread="Q1P1", stage="verify", actor="verifier"))
    assert len(transport.receipts(c)) == before + 1

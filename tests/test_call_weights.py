"""Calls are charged by their stage's weight (call_weights): a cheap stage spends less of a call budget and of
the dollar guard's per-call estimate than a peer call. proofTree planar, 9 October 2026: medians of 72k input
tokens for a scan against 1.3M for a peer call, yet 74 scans used 74 of 91 remaining calls and stopped S8
mid-research. Without call_weights every call counts 1, as before."""
import json
import pytest
from pathfinder import admission, budget, config
from stubcampaign import make

WEIGHTS = {"scan": 0.25, "ledger_review": 0.25, "carrie": 0.25, "verify": 0.5}


def _receipts(c, stage, n, **row):
    with c.path("receipts.jsonl").open("a") as stream:
        for i in range(n):
            stream.write(json.dumps({"v": 3, "call_id": f"{stage}-{i}-{len(row)}", "thread": "Q1P1", "stage": stage,
                                     "actor": "a", "outcome": "completed", "input_tokens": 1, "output_tokens": 1,
                                     **row}) + "\n")


def test_a_stage_without_a_weight_counts_one_and_a_weighted_one_its_weight(tmp_path):
    c = make(tmp_path, call_weights=WEIGHTS)
    assert budget.weight(c, "scan") == 0.25 and budget.weight(c, "peer") == 1.0 and budget.weight(c, None) == 1.0
    assert budget.weight(make(tmp_path / "plain"), "scan") == 1.0


def test_cheap_calls_spend_a_call_budget_by_their_weight(tmp_path):
    c = make(tmp_path, budget={"calls": 10}, call_weights=WEIGHTS)
    _receipts(c, "scan", 39)                                      # 9.75 weighted calls
    assert budget.usage(c)["calls"] == 39 and budget.usage(c)["weighted_calls"] == 9.75
    assert budget.refusal(c, 1, stage="scan") is None             # 10.0 projected: at the cap
    assert "calls 10.75 projected against 10" in budget.refusal(c, 1, stage="peer")


def test_calls_already_in_flight_are_charged_at_the_heaviest_weight(tmp_path):
    c = make(tmp_path, budget={"calls": 10}, call_weights=WEIGHTS)
    _receipts(c, "scan", 36)                                      # 9 weighted
    assert budget.refusal(c, 1, stage="scan") is None             # 9.25
    assert budget.refusal(c, 2, stage="scan") is not None         # 9 + 1 (unknown stage in flight) + 0.25


def test_the_admission_policy_charges_the_calls_stage(tmp_path):
    c = make(tmp_path, budget={"calls": 10}, call_weights=WEIGHTS)
    _receipts(c, "scan", 39)
    assert admission.budget_per_call(c, "scan", None, 0) == admission.ADMIT
    assert admission.budget_per_call(c, "peer", None, 0) != admission.ADMIT


def test_the_dollar_estimate_is_weighted_too(tmp_path):
    c = make(tmp_path, budget_usd=10, call_estimate_usd=2.0, call_weights=WEIGHTS)
    _receipts(c, "scan", 16, cost=None)                           # unknown cost: 16 x 2.0 x 0.25 = 8.0
    assert budget.refusal(c, 1, stage="peer") is None             # 8 + 2 = 10
    assert budget.refusal(c, 1, stage="peer") is None and budget.refusal(c, 2, stage="scan") is not None


def test_failed_attempts_still_count_and_unreached_calls_still_do_not(tmp_path):
    c = make(tmp_path, budget={"calls": 10}, call_weights=WEIGHTS)
    _receipts(c, "scan", 4, outcome="timeout")
    _receipts(c, "scan", 4, outcome="no session")
    assert budget.usage(c)["weighted_calls"] == 1.0


@pytest.mark.parametrize("bad", [{"scan": -1}, {"scan": "cheap"}, {"scan": 0}, ["scan"]])
def test_malformed_weights_are_refused_at_load(tmp_path, bad):
    with pytest.raises(ValueError, match="call_weights"):
        make(tmp_path, call_weights=bad)

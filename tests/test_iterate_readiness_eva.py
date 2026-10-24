"""ITERATE reopens readiness in the review-driven (eva) scheme as in the classic one (nobel pilot 6, 24 October 2026:
on the classic path a peer's ready from before the verifier's ITERATE skipped the next round's research). The eva
round after ITERATE always dispatches its peers once; a ready written before the verifier's review must not count
when deciding whether a peer gets a further call in that round."""
import json
import pytest
from pathfinder import research, stub
from pathfinder.ledger import Ledger
from stubcampaign import make

ALLOW = {"peer_seconds": 600, "peer_calls": 2, "consolidate_seconds": 60, "verify_seconds": 60,
         "edit_seconds": 60, "paper_seconds": 60, "review_seconds": 60}


def _script(monkeypatch, verdicts, silent_rounds=()):
    """Peers declare ready, except their first call in a round of `silent_rounds`, which writes nothing."""
    calls, real = [], stub.reply
    verdicts = iter(verdicts)
    def reply(campaign, request):
        if request.stage == "peer":
            d = campaign.thread_dir("Q1P1")
            rnd = json.loads((d / "status.json").read_text())["round"]
            calls.append((rnd, request.actor))
            ledger = Ledger(d / "ledger.jsonl")
            if rnd in silent_rounds and sum(1 for r, a in calls if (r, a) == (rnd, request.actor)) == 1:
                return "still working"                    # nothing in the ledger yet: no fresh ready
            ledger.add(request.actor, "ready", "ready", seen=ledger.count())
            return "ready"
        if request.stage == "verify":
            return json.dumps({"decision": next(verdicts), "reason": "gap", "action": "check the boundary"})
        return real(campaign, request)
    monkeypatch.setattr(stub, "reply", reply)
    return calls


@pytest.mark.parametrize("peers", [["ada"], ["ada", "emmy"]])
def test_iterate_dispatches_every_peer_again_in_the_eva_scheme(tmp_path, monkeypatch, peers):
    c = make(tmp_path, research_scheme="eva", peers=peers, rounds=2, allowances=ALLOW)
    calls = _script(monkeypatch, ["ITERATE", "DRAFT"])
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert sorted(a for r, a in calls if r == 2) == sorted(peers)


def test_a_ready_from_before_the_iterate_review_does_not_end_the_next_round(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva", peers=["ada"], rounds=2, allowances=ALLOW)
    calls = _script(monkeypatch, ["ITERATE", "DRAFT"], silent_rounds=(2,))
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert [a for r, a in calls if r == 2] == ["ada", "ada"]    # the first call left no fresh ready: a second follows


def test_revise_in_the_eva_scheme_still_consolidates_without_peers(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva", peers=["ada"], rounds=2, repairs=1, allowances=ALLOW)
    calls = _script(monkeypatch, ["REVISE", "DRAFT"])
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert {r for r, a in calls} == {1}

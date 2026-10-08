"""The peers' time allowance runs out without a failure. proofTree planar S20 (PF-09, 8 October 2026): peer_seconds
900, two calls; the first parallel calls used 372.3 + 492.7 = 865 s, the second calls were sent with the 35 s left
(65 s with grace), Ada timed out, and the branch stopped as a transport failure instead of going to its review."""
import json
import pytest
from pathfinder import composable, research, transport
from stubcampaign import make

FIRST = {"ada": 372.3, "emmy": 492.7}


def _branch(tmp_path, **raw):
    raw.setdefault("allowances", {"peer_seconds": 900, "peer_calls": 2, "consolidate_seconds": 60,
                                  "verify_seconds": 60, "edit_seconds": 60})
    return make(tmp_path, research_scheme="composable", branches=1, peers=["ada", "emmy"], **raw)


def _timed(monkeypatch, timeout_second_call_of=None):
    real, seen = transport.execute, []

    def execute(campaign, request):
        r = real(campaign, request)
        seen.append(request)
        if request.stage == "peer":
            first = sum(1 for q in seen if q.stage == "peer" and q.actor == request.actor and q.cwd == request.cwd) == 1
            if first:
                return {**r, "seconds": FIRST[request.actor]}
            if request.actor == timeout_second_call_of and str(request.cwd).endswith("branch-1"):
                return {**r, "text": "", "seconds": float(request.timeout), "transport_failed": True, "error": "timeout",
                        "outcome": "timeout", "failure": {"class": "timeout", "scope": "call", "retry": True, "reset_at": None}}
        return r
    monkeypatch.setattr(transport, "execute", execute)
    return seen


def test_a_residual_below_the_floor_is_not_sent_and_the_branch_goes_to_its_review(tmp_path, monkeypatch):
    c = _branch(tmp_path)
    seen = _timed(monkeypatch)
    research.run_thread(c, "Q1P1")
    branch = [q for q in seen if str(q.cwd).endswith("branch-1")]
    assert sorted(q.actor for q in branch if q.stage == "peer") == ["ada", "emmy"]      # no second call on 35 s
    assert any(q.stage == "ledger_review" for q in branch)


def test_a_peer_timing_out_at_the_residual_deadline_ends_the_peers_turn_not_the_branch(tmp_path, monkeypatch):
    c = _branch(tmp_path, peer_min_seconds=0)            # the floor off: the 35 s call is sent, as in S20
    seen = _timed(monkeypatch, timeout_second_call_of="ada")
    try:
        research.run_thread(c, "Q1P1")
    except transport.TransportFailed:
        research.run_thread(c, "Q1P1")                   # S20's recovery: resume, nothing is reissued
    view = composable.branch_view(c, "Q1P1", "branch-1")
    s = research.status(view, "Q1P1")
    assert s["status"] != "BLOCKED" and s.get("peer_seconds_exhausted")
    branch = [q for q in seen if str(q.cwd).endswith("branch-1")]
    assert [q.actor for q in branch if q.stage == "peer"].count("ada") == 2       # the timed-out call is not asked again
    assert any(q.stage == "ledger_review" for q in branch)
    retained = list((view.thread_dir("Q1P1") / "research-requests").glob("*.json"))
    assert sum("result" in json.loads(p.read_text()) for p in retained) >= 4      # the paid replies are kept


def test_a_full_length_peer_timeout_is_still_a_failure(tmp_path, monkeypatch):
    c = _branch(tmp_path, allowances={"peer_seconds": 3600, "peer_calls": 2, "consolidate_seconds": 60,
                                      "verify_seconds": 60, "edit_seconds": 60})
    real = transport.execute

    def execute(campaign, request):
        r = real(campaign, request)
        if request.stage == "peer" and request.actor == "ada":
            return {**r, "text": "", "seconds": float(request.timeout), "transport_failed": True, "error": "timeout",
                    "outcome": "timeout", "failure": {"class": "timeout", "scope": "call", "retry": True, "reset_at": None}}
        return r
    monkeypatch.setattr(transport, "execute", execute)
    with pytest.raises(transport.TransportFailed):
        research.run_thread(c, "Q1P1")

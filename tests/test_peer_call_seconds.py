"""One peer call's deadline (nobel's single EV loop, 19 October 2026): a peer call was capped at 1200 s whatever
peer_seconds said, so long single calls by a high-effort proposer were impossible. allowances.peer_call_seconds
sets the cap (default 1200, plus 30 s of grace), in the classic and the composable schemes; verify_seconds sets
the verifier's deadline as it stands."""
import pytest
from pathfinder import composable_research, health, research, thread, transport
from stubcampaign import make

ALLOW = {"peer_seconds": 7200, "peer_calls": 1, "consolidate_seconds": 60, "verify_seconds": 5400,
         "edit_seconds": 60, "paper_seconds": 60, "review_seconds": 60}


def _deadlines(monkeypatch):
    seen, real = [], transport.execute
    monkeypatch.setattr(transport, "execute", lambda campaign, request: seen.append(request) or real(campaign, request))
    return seen


@pytest.mark.parametrize("extra, peer", [({}, 1230), ({"peer_call_seconds": 3600}, 3630)])
def test_a_peer_call_lasts_up_to_the_configured_cap(tmp_path, monkeypatch, extra, peer):
    c = make(tmp_path, allowances={**ALLOW, **extra})
    seen = _deadlines(monkeypatch)
    research.run_thread(c, "Q1P1")
    peers = [r for r in seen if r.stage == "peer"]
    assert peers and {r.timeout for r in peers} == {peer}
    assert f"You have {peer - 30} seconds in this call" in peers[0].prompt
    assert {r.timeout for r in seen if r.stage == "verify"} == {5400}


def test_the_composable_scheme_honours_the_cap_too(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="composable", branches=1, allowances={**ALLOW, "peer_call_seconds": 3600})
    seen = _deadlines(monkeypatch)
    research.run_thread(c, "Q1P1")
    assert {r.timeout for r in seen if r.stage == "peer"} == {3630}


def test_a_timeout_at_the_configured_cap_is_a_transport_failure_not_a_spent_allowance(tmp_path):
    c = make(tmp_path, allowances={**ALLOW, "peer_call_seconds": 3600})
    timeout = {"class": "timeout"}
    assert not thread.residual_timeout(c, 3630, timeout)
    assert thread.residual_timeout(c, 1230, timeout)            # cut short by what was left of the allowance


@pytest.mark.parametrize("value", [0, -5, "long", 12.5])
def test_a_bad_cap_is_refused(tmp_path, value):
    with pytest.raises(ValueError, match="peer_call_seconds"):
        make(tmp_path, allowances={**ALLOW, "peer_call_seconds": value})

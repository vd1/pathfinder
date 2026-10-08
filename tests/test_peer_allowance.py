"""The peers' time allowance is clock time (the user's decision, 8 October 2026): peers working side by side spend
the slowest one's seconds, not their sum. And it runs out without a failure. proofTree planar S20 (PF-09, 8 October 2026): peer_seconds
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


def test_peers_side_by_side_spend_clock_time(tmp_path, monkeypatch):
    c = _branch(tmp_path)                                # 900 s: 492.7 s of clock time leaves 407.3 s for a second call
    seen = _timed(monkeypatch)
    research.run_thread(c, "Q1P1")
    second = [q for q in seen if str(q.cwd).endswith("branch-1") and q.stage == "peer"][2:]
    assert sorted(q.actor for q in second) == ["ada", "emmy"] and {q.timeout for q in second} == {407 + 30}
    view = composable.branch_view(c, "Q1P1", "branch-1")
    assert research.status(view, "Q1P1")["peer_seconds"] == pytest.approx(492.7 + 0.0, abs=1)


def _short(**raw):
    return {"allowances": {"peer_seconds": 600, "peer_calls": 2, "consolidate_seconds": 60, "verify_seconds": 60,
                           "edit_seconds": 60}, **raw}


def test_a_residual_below_the_floor_is_not_sent_and_the_branch_goes_to_its_review(tmp_path, monkeypatch):
    c = _branch(tmp_path, **_short())                    # 600 s: 107.3 s left, under the 120 s floor
    seen = _timed(monkeypatch)
    research.run_thread(c, "Q1P1")
    branch = [q for q in seen if str(q.cwd).endswith("branch-1")]
    assert sorted(q.actor for q in branch if q.stage == "peer") == ["ada", "emmy"]      # no second call on 35 s
    assert any(q.stage == "ledger_review" for q in branch)


def test_a_peer_timing_out_at_the_residual_deadline_ends_the_peers_turn_not_the_branch(tmp_path, monkeypatch):
    c = _branch(tmp_path, **_short(peer_min_seconds=0))  # the floor off: the 107 s call is sent, as S20's 35 s was
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


def test_a_peers_stage_resumed_with_too_little_left_sends_no_call(tmp_path, monkeypatch):
    """The recurrence guard: however the thread got back to its peers (a reissue, an older engine's state), a
    remainder below the floor is not dispatched."""
    c = _branch(tmp_path)
    view = composable.branch_view(c, "Q1P1", "branch-1")
    research.prepare(view, "Q1P1")
    research._set(view, "Q1P1", status="running", stage="peers", round=1, peer_call=1, peer_seconds=865.0, pending=[])
    seen = _timed(monkeypatch)
    research.run_thread(view, "Q1P1")
    assert not [q for q in seen if q.stage == "peer"] and any(q.stage == "ledger_review" for q in seen)


def test_reconcile_lets_a_peer_block_at_the_residual_deadline_end_the_peers_turn(tmp_path, monkeypatch):
    from pathfinder import reconcile
    c = _branch(tmp_path, **_short(peer_min_seconds=0))
    _timed(monkeypatch, timeout_second_call_of="ada")
    with pytest.raises(transport.TransportFailed):
        research.run_thread(c, "Q1P1")
    view = composable.branch_view(c, "Q1P1", "branch-1")
    research._set(view, "Q1P1", status="BLOCKED", reason="peers: timeout",
                  failure={"class": "timeout", "scope": "call", "retry": True, "reset_at": None})
    assert reconcile.inspect(c, "Q1P1")["action"] == "branch-1: unblock: the peers' allowance ran out"
    reconcile.apply(c, "Q1P1")
    assert research.status(view, "Q1P1").get("peer_seconds_exhausted")


def test_a_peer_timing_out_at_the_full_deadline_is_asked_again_alone(tmp_path, monkeypatch):
    """proofTree planar S20 joint thread: Emmy completed in 772 s, Ada timed out at the full 930 s deadline. The
    reissue moved both pending requests, so Emmy's paid reply would have been asked again. Only Ada's is."""
    from pathfinder import reconcile
    c = _branch(tmp_path, allowances={"peer_seconds": 3600, "peer_calls": 2, "consolidate_seconds": 60,
                                      "verify_seconds": 60, "edit_seconds": 60})
    real, armed, identities = transport.execute, {"on": True}, []

    def execute(campaign, request):
        r = real(campaign, request)
        joint = not str(request.cwd).rstrip("/").split("/")[-1].startswith("branch-")
        if joint:                                       # a branch's calls carry the same identities in their own threads
            identities.append(request.identity)
        if armed["on"] and joint and request.stage == "peer" and request.actor == "ada":
            armed["on"] = False
            return {**r, "text": "", "seconds": float(request.timeout), "transport_failed": True, "error": "timeout",
                    "outcome": "timeout", "failure": {"class": "timeout", "scope": "call", "retry": True, "reset_at": None}}
        return r
    monkeypatch.setattr(transport, "execute", execute)
    with pytest.raises(transport.TransportFailed):
        research.run_thread(c, "Q1P1")
    ada = next(i for i in reversed(identities) if ":peers:ada:" in i or ":peer:ada:" in i)
    emmy = next(i for i in reversed(identities) if (":peers:emmy:" in i or ":peer:emmy:" in i) and i.split(":")[-1] == ada.split(":")[-1])
    assert reconcile.inspect(c, "Q1P1")["action"] == "reissue: the reply failed in transport"
    reconcile.apply(c, "Q1P1")
    assert identities.count(emmy) == 1 and identities.count(ada) == 2
    joint = composable.joint_view(c, "Q1P1")
    assert list((joint.thread_dir("Q1P1") / "research-requests" / "superseded").glob("*.json"))   # the failure is kept


def test_the_peer_prompt_asks_for_one_log_per_trial_and_names_the_digit_limit(tmp_path):
    """proofTree S20 (OBS-10, OBS-11): a peer's repeated trials overwrote the first failure's stderr, and a large
    Fraction hit Python's 4300-digit limit on converting an integer to text."""
    from pathfinder import resources
    text = resources.prompt(make(tmp_path), "peer")
    assert "own log file" in text and "sys.set_int_max_str_digits(0)" in text


def test_a_classic_thread_also_spends_clock_time(tmp_path, monkeypatch):
    """Without a scheme the peers run their own call loops side by side; 500 s each is 500 s of clock time, so
    with 600 s both get a second call (summed, 1000 s, neither would)."""
    c = make(tmp_path, peers=["ada", "emmy"])
    real, calls = transport.execute, []

    def execute(campaign, request):
        r = real(campaign, request)
        if request.stage == "peer":
            calls.append(request.actor)
            return {**r, "seconds": 500.0 if calls.count(request.actor) == 1 else r["seconds"]}
        return r
    monkeypatch.setattr(transport, "execute", execute)
    from pathfinder import ledger as ledger_module
    monkeypatch.setattr(ledger_module.Ledger, "ready", lambda self, actors: False)
    research.run_thread(c, "Q1P1")
    assert sorted(calls) == ["ada", "ada", "emmy", "emmy"]

"""Exercise actual classic peer dispatch, including ready declarations across rounds."""
from collections import Counter
import json
import threading

import pytest

from pathfinder import config, research, transport
from pathfinder.ledger import Ledger
from stubcampaign import make


@pytest.mark.parametrize("peers", [["ada"], ["ada", "emmy"]])
@pytest.mark.parametrize("resume", [False, True])
def test_iterate_calls_every_peer_again_after_ready(tmp_path, monkeypatch, peers, resume):
    c = make(tmp_path, peers=peers, rounds=2)
    d = research.prepare(c, "Q1P1")
    ledger = Ledger(d / "ledger.jsonl")
    ledger.add("ada", "finding", "initial result")
    for actor in peers:
        ledger.add(actor, "ready", "finished initial research", seen=ledger.count())
    research._set(c, "Q1P1", stage="consolidate")
    calls = []
    verdicts = iter(["ITERATE", "DRAFT"])
    stop = threading.Event()
    real = transport.execute

    def execute(campaign, request):
        if request.stage == "peer":
            calls.append(request.actor)
            rows = ledger.read()
            review = next(r for r in reversed(rows) if r["kind"] == "review")
            assert review["text"].startswith("ITERATE:")
            # No new result is required to declare readiness: the peer may conclude
            # the requested gap is still open, but must have read the new review.
            ledger.add(request.actor, "ready", "gap remains open", seen=ledger.count())
            return {"text": "done", "seconds": 0, "transport_failed": False}
        result = real(campaign, request)
        if request.stage == "verify":
            decision = next(verdicts)
            result["text"] = json.dumps({"decision": decision, "reason": "gap", "action": "check boundary"})
            if resume and decision == "ITERATE":
                stop.set()
        return result

    monkeypatch.setattr(transport, "execute", execute)
    if resume:
        assert research.run_thread(c, "Q1P1", stop.is_set) == "stopped"
        assert calls == []
        assert research.status(c, "Q1P1")["stage"] == "peers"
        c = config.load(c.root)  # Resume from durable state, not an in-memory round flag.
        stop.clear()
    assert research.run_thread(c, "Q1P1", stop.is_set) == "DRAFT"
    assert Counter(calls) == Counter(peers)


def test_revise_does_not_dispatch_peers(tmp_path, monkeypatch):
    c = make(tmp_path, repairs=1, rounds=2)
    d = research.prepare(c, "Q1P1")
    ledger = Ledger(d / "ledger.jsonl")
    ledger.add("ada", "finding", "initial result")
    ledger.add("ada", "ready", "done", seen=1)
    research._set(c, "Q1P1", stage="consolidate")
    stages = []
    verdicts = iter(["REVISE", "DRAFT"])
    real = transport.execute

    def execute(campaign, request):
        stages.append(request.stage)
        result = real(campaign, request)
        if request.stage == "verify":
            result["text"] = json.dumps({"decision": next(verdicts), "reason": "typo", "action": "correct notation"})
        return result

    monkeypatch.setattr(transport, "execute", execute)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert stages == ["consolidate", "verify", "consolidate", "verify"]


def test_resume_does_not_recall_peers_already_ready_for_this_iteration(tmp_path, monkeypatch):
    c = make(tmp_path, peers=["ada", "emmy"], rounds=2)
    d = research.prepare(c, "Q1P1")
    ledger = Ledger(d / "ledger.jsonl")
    ledger.add("ada", "finding", "result")
    ledger.add("ada", "ready", "old ready", seen=1)
    ledger.add("emmy", "ready", "old ready", seen=1)
    review = ledger.add("verifier", "review", "ITERATE: check boundary")
    ledger.add("ada", "ready", "checked, gap remains", seen=review)
    research._set(c, "Q1P1", stage="peers", round=2)
    calls = []

    def execute(campaign, request):
        calls.append(request.actor)
        ledger.add(request.actor, "ready", "checked", seen=ledger.count())
        return {"text": "done", "seconds": 0, "transport_failed": False}

    monkeypatch.setattr(transport, "execute", execute)
    research._peers(config.load(c.root), "Q1P1", lambda: False)
    assert calls == ["emmy"]
    research._peers(config.load(c.root), "Q1P1", lambda: False)
    assert calls == ["emmy"]


def test_each_iterate_reopens_research_in_a_complete_thread(tmp_path, monkeypatch):
    c = make(tmp_path, rounds=3)
    stages = []
    verdicts = iter(["ITERATE", "ITERATE", "DRAFT"])
    real = transport.execute

    def execute(campaign, request):
        stages.append(request.stage)
        result = real(campaign, request)
        if request.stage == "verify":
            result["text"] = json.dumps({"decision": next(verdicts), "reason": "gap", "action": "investigate"})
        return result

    monkeypatch.setattr(transport, "execute", execute)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert stages == ["peer", "consolidate", "verify"] * 3

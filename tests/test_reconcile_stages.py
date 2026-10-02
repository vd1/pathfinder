"""Reconcile names and applies the one safe action at every stage, and records each transition."""
import json
from pathfinder import edit, paper, reconcile, research, transport
from stubcampaign import make

TIMEOUT = {"class": "timeout", "scope": "call", "retry": True, "reset_at": None}


def _drafted(tmp_path):
    c = make(tmp_path)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    return c


def test_a_stopped_edit_is_rerun_without_redoing_research(tmp_path):
    c = _drafted(tmp_path)
    edit._set(c, "Q1P1", status="stopped", reason="transport failed: timeout", failure=TIMEOUT)
    assert reconcile.inspect(c, "Q1P1")["action"] == "run edit"
    research_calls = [r for r in transport.receipts(c) if r["stage"] in ("peer", "consolidate", "verify")]
    assert reconcile.apply(c, "Q1P1") == "done"
    assert [r for r in transport.receipts(c) if r["stage"] in ("peer", "consolidate", "verify")] == research_calls
    history = edit.status(c, "Q1P1")["history"]
    assert history[0]["from_status"] == "stopped" and history[0]["action"] == "run edit"


def test_a_stopped_paper_is_rerun_and_an_amend_pause_needs_the_operator(tmp_path):
    c = _drafted(tmp_path)
    edit._set(c, "Q1P1", status="done")
    paper._set(c, "Q1P1", status="stopped", reason="transport failed: timeout", failure=TIMEOUT)
    assert reconcile.inspect(c, "Q1P1")["action"] == "run paper"
    paper._set(c, "Q1P1", status="PAUSE-ON-AMEND", reason="amend")
    assert reconcile.inspect(c, "Q1P1")["action"] == "nothing: paper needs the operator"


def test_a_stale_retained_review_is_superseded_and_reissued(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva_minus", imported_research=True)
    d = research.prepare(c, "Q1P1")
    real = transport.execute

    def execute_then_change_evidence(campaign, request):
        result = real(campaign, request)
        (d / "ada" / "late.txt").write_text("evidence written after the request was built")
        return result
    monkeypatch.setattr(research.transport, "execute", execute_then_change_evidence)
    research.run_thread(c, "Q1P1")
    s = research.status(c, "Q1P1")
    assert s["status"] == "BLOCKED" and s["reason"] == "stale review: research evidence changed"
    monkeypatch.setattr(research.transport, "execute", real)
    assert reconcile.inspect(c, "Q1P1")["action"] == "reissue: evidence changed since the request"
    reconcile.apply(c, "Q1P1")
    superseded = list((d / "research-requests" / "superseded").glob("*.json"))
    assert len(superseded) == 1 and "result" in json.loads(superseded[0].read_text())
    s = research.status(c, "Q1P1")
    assert s.get("reason") != "stale review: research evidence changed"
    entry = s["history"][-1]
    assert entry["action"] == "reissue: evidence changed since the request" and len(entry["superseded"]) == 1

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

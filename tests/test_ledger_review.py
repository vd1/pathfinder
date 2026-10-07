"""The direct ledger review reads the branch and returns its review; the engine records it. The reviewer never writes
to the workspace it reviews (its own ledger entry would make its review stale), and only the requests the engine
accepted can be disposed of (proofTree planar S1, 7 October 2026: PF-01 and PF-02)."""
import pytest
from pathfinder import composable_research, research, transport
from stubcampaign import make


def _requests(tmp_path, monkeypatch, **raw):
    c = make(tmp_path, research_scheme="composable", branches=1, **raw)
    seen = []
    real = transport.execute
    monkeypatch.setattr(transport, "execute", lambda campaign, request: seen.append(request) or real(campaign, request))
    research.run_thread(c, "Q1P1")
    return seen


def test_the_ledger_reviewer_reads_and_the_peers_write(tmp_path, monkeypatch):
    seen = _requests(tmp_path, monkeypatch)
    reviews = [r for r in seen if r.stage == "ledger_review"]
    peers = [r for r in seen if r.stage == "peer"]
    assert reviews and all(r.reads for r in reviews)
    assert peers and not any(r.reads for r in peers)


def test_the_ledger_reviewer_is_told_the_briefs_ledger_instruction_is_the_peers(tmp_path, monkeypatch):
    reviews = [r.prompt for r in _requests(tmp_path, monkeypatch) if r.stage == "ledger_review"]
    assert reviews and all("applies to the peers only" in p and "Do not write any file or ledger entry" in p for p in reviews)
    assert all("direct-EVA branch of a composable investigation" in p for p in reviews)


def test_the_review_prompt_says_the_engines_record_is_the_only_one(tmp_path, monkeypatch):
    reviews = [r.prompt for r in _requests(tmp_path, monkeypatch) if r.stage == "ledger_review"]
    assert reviews and all("only ids in this record may receive a disposition" in p for p in reviews)


def test_a_disposition_of_a_request_the_engine_never_accepted_names_it_and_the_allowed_ids():
    review = {"requests": [{"id": "B1-R2", "action": "ITERATE", "text": "Check the bound."}],
              "dispositions": [{"id": "B1-R1", "status": "resolved", "reason": "superseded"}]}
    with pytest.raises(ValueError, match=r"B1-R1.*none: dispositions must be an empty list"):
        composable_research._direct_requests(review, {})
    with pytest.raises(ValueError, match=r"B1-R1.*allowed: B1-R0"):
        composable_research._direct_requests(review, {"B1-R0": {"id": "B1-R0", "status": "resolved"}})


def test_a_new_request_with_no_dispositions_is_accepted_when_the_record_is_empty():
    review = {"requests": [{"id": "B1-R2", "action": "ITERATE", "text": "Check the bound."}], "dispositions": []}
    assert composable_research._direct_requests(review, {})["B1-R2"]["status"] == "active"

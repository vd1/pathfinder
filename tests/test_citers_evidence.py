"""A novelty citers file mentioned in a ledger (nobel, Q481-P496): a reviewer's request naming a path is not cited
evidence, the citers file is a source registered for its pair (also in a composable branch), and novelty_citers
must name a file inside the campaign."""
import json
import pytest
from pathfinder import evidence, research
from pathfinder.ledger import Ledger
from stubcampaign import make


def test_a_path_named_in_a_review_request_is_not_cited_evidence(tmp_path):
    c = make(tmp_path, research_scheme="direct_eva")
    d = research.prepare(c, "Q1P1")
    Ledger(d / "ledger.jsonl").add("verifier", "review", json.dumps(
        {"review_id": "r1", "response": {"requests": [{"id": "R1", "action": "ITERATE",
                                                      "text": "use ../data/citers_pairs/Q1P1.md if readable"}]}}))
    research._review_material(c, "Q1P1")                    # no EvidenceUnavailable


def test_a_peer_citing_a_path_outside_the_thread_still_blocks(tmp_path):
    c = make(tmp_path, research_scheme="direct_eva")
    d = research.prepare(c, "Q1P1")
    Ledger(d / "ledger.jsonl").add("ada", "finding", "see ../data/citers_pairs/Q1P1.md")
    with pytest.raises(research.EvidenceUnavailable, match="aliased"):
        research._review_material(c, "Q1P1")


def _citers(tmp_path, **raw):
    c = make(tmp_path, novelty_stage=True, novelty_citers="sources/citers/{pair}.md", **raw)
    f = tmp_path / "sources/citers/Q1P1.md"; f.parent.mkdir(parents=True); f.write_text("Citing both: Smith 2025\n")
    return c, f


def test_the_citers_file_is_a_source_registered_for_its_pair(tmp_path):
    c, f = _citers(tmp_path, research_scheme="eva")
    assert evidence.registered_sources(c, "Q1P1")["sources/citers/Q1P1.md"] == f.resolve()
    d = research.prepare(c, "Q1P1")
    Ledger(d / "ledger.jsonl").add("ada", "finding", "the citers are in sources/citers/Q1P1.md")
    assert "Citing both: Smith 2025" in research._review_material(c, "Q1P1")


def test_a_composable_branch_resolves_its_pairs_sources(tmp_path):
    from pathfinder import composable
    c, f = _citers(tmp_path, research_scheme="composable", branches=1)
    view = composable.branch_view(c, "Q1P1", "branch-1")
    d = research.prepare(view, "Q1P1")
    Ledger(d / "ledger.jsonl").add("ada", "finding", "the citers are in sources/citers/Q1P1.md")
    assert "Citing both: Smith 2025" in research._review_material(view, "Q1P1")


@pytest.mark.parametrize("path", ["../data/citers/{pair}.md", "/abs/citers/{pair}.md"])
def test_novelty_citers_outside_the_campaign_is_refused(tmp_path, path):
    with pytest.raises(ValueError, match="inside the campaign"):
        make(tmp_path, research_scheme="eva", novelty_stage=True, novelty_citers=path)

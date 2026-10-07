"""Pair ids people read are the engine's ids. A corpus row may carry its deployment's own number ("n"); a pair is
then Q<n>-P<m>, zero-padded to three digits (julien-2's Q002-P072), and the engine finds its papers by number. A
corpus without numbers keeps Q<i>P<j> by line, as before."""
import json
import pytest
from pathfinder import campaign_state, config, corpus, monitor, research, scan
from stubcampaign import make


@pytest.mark.parametrize("pid, numbers", [("Q1P15", (1, 15)), ("Q002-P072", (2, 72)), ("Q002P072", (2, 72))])
def test_a_pair_id_names_two_numbers(pid, numbers):
    assert corpus.numbers(pid) == numbers


@pytest.mark.parametrize("bad", ["Q1", "P1Q2", "Q1-P", "Q-1P2", "q1p2"])
def test_a_malformed_pair_id_is_refused(bad):
    with pytest.raises(ValueError, match="pair id"):
        corpus.numbers(bad)


def _numbered(tmp_path):
    c = make(tmp_path)
    for side, numbers in (("Q", (2, 10)), ("P", (11, 72))):
        rows = [{"id": f"{side.lower()}{n}", "n": n, "title": f"{side} paper {n}", "abstract": f"Abstract {side}{n}."}
                for n in numbers]
        (tmp_path / f"{side}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp_path / "shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": "Q002-P072"}]}))
    return config.load(tmp_path)


def test_a_numbered_corpus_finds_papers_by_their_number(tmp_path):
    c = _numbered(tmp_path)
    q, p = corpus.pair_rows(c, "Q002-P072")
    assert q["title"] == "Q paper 2" and p["title"] == "P paper 72"
    assert corpus.pair_id_for(c, 0, 1) == "Q002-P072"         # the first Q row and the second P row


def test_a_numbered_pair_runs_and_is_shown_with_its_papers(tmp_path):
    c = _numbered(tmp_path)
    d = research.prepare(c, "Q002-P072")
    assert "P paper 72" in (d / "inputs" / "P.json").read_text()
    assert research.run_thread(c, "Q002-P072") in research.TERMINAL
    unit = campaign_state.build(c)["units"][0]
    assert unit["unit"] == "Q002-P072" and unit["q"].get("title") == "Q paper 2"
    assert monitor.state(c)["threads"]["Q002-P072"]["p_title"] == "P paper 72"


def test_an_unnumbered_corpus_keeps_positions(tmp_path):
    c = make(tmp_path)
    q, p = corpus.pair_rows(c, "Q1P1")
    assert q["id"] == "q1" and corpus.pair_id_for(c, 0, 0) == "Q1P1"

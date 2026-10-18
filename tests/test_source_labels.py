"""Source papers by their authors, in full text (nobel presentation pilot, 18 October 2026). Accepted papers named the
source papers "Q" and "P" in their prose and bibliography keys, labels that mean something only inside the pipeline:
the author prompt framed the work as "the pair of papers Q and P". A thread whose corpus row had no stored text gave
every stage the abstract only; with "fetch_sources": true the thread fetches the full text when it opens, and
`pathfinder sources PAIR` fetches it for a thread already open, into the campaign's sources/ only."""
import json
import pytest
from pathfinder import cli, config, corpus, research, thread
from stubcampaign import make


def _author_prompt(c):
    return " ".join(research._prompt(c, "author", Q_INPUT="inputs/Q.txt", P_INPUT="inputs/P.txt", NOTE="Q1P1.tex",
                                     NOTE_STEM="Q1P1", ROUND=1, FINDINGS="").split())


def test_the_author_names_the_source_papers_by_their_authors_never_q_or_p(tmp_path):
    p = _author_prompt(make(tmp_path))
    assert "pair of papers Q and P" not in p and "Q and P are cited" not in p
    assert "never as Q or P" in p and "by their authors and a citation" in p
    assert "keys from the first author's surname and the year" in p


def test_the_reviewer_treats_a_pipeline_label_in_the_paper_as_a_finding(tmp_path):
    p = " ".join(research._prompt(make(tmp_path), "review").split())
    assert "on two papers, Q and P" not in p
    assert "any other label that means something only inside the pipeline" in p and "is a minor finding" in p


def _fake_fetch(calls):
    def flatten(aid, out_dir):
        calls.append(aid)
        (out_dir / f"{aid}.tex").parent.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{aid}.tex").write_text(f"\\documentclass{{article}} full text of {aid}")
        return f"sources/{aid}.tex"
    return flatten


def test_a_thread_opens_with_full_text_when_the_campaign_fetches_sources(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(corpus, "flatten", _fake_fetch(calls))
    c = make(tmp_path, fetch_sources=True)
    d = thread.prepare(c, "Q1P1")
    assert calls == ["q1", "p1"]
    assert (d / "inputs" / "Q.tex").read_text().endswith("full text of q1") and not (d / "inputs" / "Q.txt").exists()
    assert json.loads((d / "inputs" / "P.json").read_text())["text"] == "sources/p1.tex"
    assert "Abstract of Q1" in (c.root / "Q.jsonl").read_text() and '"text"' not in (c.root / "Q.jsonl").read_text()


def test_a_source_already_fetched_is_not_fetched_again(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(corpus, "flatten", _fake_fetch(calls))
    c = make(tmp_path, fetch_sources=True)
    (c.root / "sources").mkdir()
    (c.root / "sources" / "q1.txt").write_text("cached text of q1")
    d = thread.prepare(c, "Q1P1")
    assert calls == ["p1"] and (d / "inputs" / "Q.txt").read_text() == "cached text of q1"


def test_a_failed_fetch_leaves_the_abstract(tmp_path, monkeypatch):
    def fail(aid, out_dir):
        raise RuntimeError("no e-print")
    monkeypatch.setattr(corpus, "flatten", fail)
    d = thread.prepare(make(tmp_path, fetch_sources=True), "Q1P1")
    assert "Abstract: Abstract of Q1." in (d / "inputs" / "Q.txt").read_text()


def test_without_the_setting_a_thread_makes_no_download(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, "flatten", lambda *a: pytest.fail("no download"))
    d = thread.prepare(make(tmp_path), "Q1P1")
    assert (d / "inputs" / "Q.txt").exists()


def test_fetch_sources_must_be_true_or_false(tmp_path):
    with pytest.raises(ValueError, match="fetch_sources"):
        make(tmp_path, fetch_sources="yes")


def test_sources_for_an_open_thread_fetch_into_the_campaign_and_leave_its_inputs(tmp_path, monkeypatch, capsys):
    calls = []
    c = make(tmp_path)
    d = thread.prepare(c, "Q1P1")
    before = sorted(p.name for p in (d / "inputs").iterdir())
    monkeypatch.setattr(corpus, "flatten", _fake_fetch(calls))
    cli.main(["--root", str(c.root), "sources", "Q1P1"])
    assert calls == ["q1", "p1"] and (c.root / "sources" / "p1.tex").exists()
    assert sorted(p.name for p in (d / "inputs").iterdir()) == before
    assert corpus.source_text(c, json.loads((d / "inputs" / "Q.json").read_text()), fetch=False) == c.root / "sources" / "q1.tex"
    assert "Q1P1 Q q1: sources/q1.tex" in capsys.readouterr().out

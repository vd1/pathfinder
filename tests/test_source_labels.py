"""Source papers by their authors (nobel presentation pilot, 18 October 2026). Accepted papers named the source
papers "Q" and "P" in their prose and bibliography keys, labels that mean something only inside the pipeline: the
author prompt framed the work as "the pair of papers Q and P". (Full texts: tests/test_paper_source.py.)"""
from pathfinder import research
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

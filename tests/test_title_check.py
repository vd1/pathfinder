"""The arXiv title check (nobel, Q410-P491 and Q080-P422, 15 October 2026): a bib title that is a shortened form
of the arXiv title, or contains it, matches; TeX macros are not words. A title that differs entirely while the
entry's authors are the arXiv record's authors (a paper renamed for its journal version) is a note that does not
fail the edit; a different title with other authors still fails it, as a wrong identifier would."""
import pytest
from pathfinder import edit, paper, research, transport
from stubcampaign import make

LONG = "Around Uncertainty Principles of Ingham-type on $\\R^n$, $\\T^n$ and Two Step Nilpotent Lie Groups"
SHORT = "Around Uncertainty Principles of Ingham-type on \\(\\mathbb{R}^n\\)"
ANDOR_BIB = ("@article{andor,\n  author = {Ambainis, Andris and Childs, Andrew M. and Reichardt, Ben W. and {\\v{S}palek}, Robert"
             " and Zhang, Shengyu},\n  title = {{Any AND-OR Formula of Size N Can Be Evaluated in Time \\(N^{1/2+o(1)}\\) on a"
             " Quantum Computer}},\n  eprint = {0704.3628},\n  year = {2010}\n}\n")
ANDOR_ARXIV = {"0704.3628": {"title": "A nearly optimal discrete query quantum algorithm for evaluating NAND formulas",
                             "authors": ["Andris Ambainis", "Andrew M. Childs", "Ben W. Reichardt", "Robert Špalek",
                                         "Shengyu Zhang"]}}


def _bib(title, key="k", aid="1605.09616", author="Bais, S. R."):
    return f"@article{{{key},\n  author = {{{author}}},\n  title = {{{title}}},\n  eprint = {{{aid}}}\n}}\n"


def _check(bib, arxiv, key="k"):
    return paper.check_references(f"\\cite{{{key}}}", bib, fetch=lambda ids: arxiv)


def test_a_shortened_bib_title_with_tex_math_matches():
    assert _check(_bib(SHORT), {"1605.09616": LONG}) == []


def test_a_bib_title_containing_the_arxiv_title_matches():
    assert _check(_bib(LONG + ": with an appendix on lattices"), {"1605.09616": SHORT}) == []


def test_containment_of_a_title_of_two_words_is_not_a_match():
    notes = _check(_bib("Lie Groups"), {"1605.09616": LONG})
    assert notes and "does not match" in notes[0] and not edit._clean(notes)


def test_a_renamed_title_by_the_same_authors_is_a_note_that_does_not_fail_the_edit():
    notes = paper.check_references("\\cite{andor}", ANDOR_BIB, fetch=lambda ids: ANDOR_ARXIV)
    assert len(notes) == 1 and "title differs from arXiv 0704.3628" in notes[0] and "authors match" in notes[0]
    assert edit._clean(notes)


def test_a_different_title_by_other_authors_still_fails():
    arxiv = {"0704.3628": {**ANDOR_ARXIV["0704.3628"], "authors": ["Jane Roe", "John Doe"]}}
    notes = paper.check_references("\\cite{andor}", ANDOR_BIB, fetch=lambda ids: arxiv)
    assert "does not match" in notes[0] and not edit._clean(notes)


def test_a_title_only_lookup_cannot_excuse_a_different_title():
    notes = paper.check_references("\\cite{andor}", ANDOR_BIB, fetch=lambda ids: {"0704.3628": ANDOR_ARXIV["0704.3628"]["title"]})
    assert "does not match" in notes[0]


def test_an_edit_blocked_on_a_shortened_title_finishes_without_an_editor_call(tmp_path, monkeypatch):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    ed = c.thread_dir("Q1P1") / "edited"
    (ed / "references.bib").write_text((ed / "references.bib").read_text() + _bib(SHORT, key="bais"))
    (ed / "note.tex").write_text((ed / "note.tex").read_text().replace("\\end{document}", "\\cite{bais}\n\\end{document}"))
    edit._set(c, "Q1P1", status="blocked", reason="build or citations failed twice")
    monkeypatch.setattr(paper, "_arxiv_titles", lambda ids: {i: LONG for i in ids})
    monkeypatch.setattr(transport, "execute", lambda *a, **k: pytest.fail("no editor call"))
    assert edit.run(c, "Q1P1") == "done"
    assert edit.status(c, "Q1P1")["status"] == "done"


def test_every_author_counts_even_inside_nested_braces():
    assert paper.bib_entries(ANDOR_BIB)["andor"]["author"].endswith("Zhang, Shengyu")
    arxiv = {"0704.3628": {**ANDOR_ARXIV["0704.3628"], "authors": ["Andris Ambainis", "John Doe"]}}
    notes = paper.check_references("\\cite{andor}", ANDOR_BIB, fetch=lambda ids: arxiv)
    assert "does not match" in notes[0]


MERGED_BIB = ANDOR_BIB.replace("  eprint = {0704.3628},\n",
                               "  note = {Merged journal version of the preprints arXiv:0704.3628 and arXiv:quant-ph/0703015},\n")
PREPRINTS = {"0704.3628": {"title": ANDOR_ARXIV["0704.3628"]["title"], "authors": ["Andris Ambainis"]},
             "quant-ph/0703015": {"title": "Every NAND formula of size N can be evaluated in time N^{1/2+o(1)} on a quantum computer",
                                  "authors": ["Andrew M. Childs", "Ben W. Reichardt", "Robert Spalek", "Shengyu Zhang"]}}


def test_an_entry_naming_several_preprints_is_checked_against_all_of_them():
    asked = []
    def fetch(ids):
        asked.extend(ids); return PREPRINTS
    notes = paper.check_references("\\cite{andor}", MERGED_BIB, fetch=fetch)
    assert sorted(asked) == ["0704.3628", "quant-ph/0703015"]
    assert notes == []                               # its title is close to the second preprint's
    renamed = {**PREPRINTS, "quant-ph/0703015": {**PREPRINTS["quant-ph/0703015"], "title": "Quantum formula evaluation"}}
    notes = paper.check_references("\\cite{andor}", MERGED_BIB, fetch=lambda ids: renamed)
    assert len(notes) == 1 and "authors match" in notes[0] and edit._clean(notes)   # five of five, across both
    alone = paper.check_references("\\cite{andor}", MERGED_BIB, fetch=lambda ids: {"0704.3628": PREPRINTS["0704.3628"]})
    assert any("quant-ph/0703015 not found" in n for n in alone)


def test_an_old_style_identifier_is_read_and_looked_up_by_its_full_name(monkeypatch):
    from pathfinder import corpus
    assert paper._arxiv_ids({"eprint": "quant-ph/0703015v2"}) == ["quant-ph/0703015"]
    atom = ('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/quant-ph/0703015v1'
            '</id><title>Every NAND formula</title><summary>s</summary><published>2007-03-01T00:00:00Z</published>'
            '<author><name>Andrew M. Childs</name></author></entry></feed>')
    monkeypatch.setattr(corpus, "query", lambda params: atom)
    assert paper._arxiv_titles(["quant-ph/0703015"]) == {"quant-ph/0703015": {"title": "Every NAND formula", "authors": ["Andrew M. Childs"]}}

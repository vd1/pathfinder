"""The release export (nobel pilot, 18 October 2026): `pathfinder release PAIR` turns a CLEARED paper into a clean
article in paper/release/, with no trace of the pipeline: standard article class, every comment removed without a
stray "%", ledger pointers moved to paper/provenance.json (never published), bibliography keys renamed to author
initials and year, and the operator's plain-language AI-use acknowledgement. A leak check on the source and on the
PDF text blocks the release on any pipeline term outside the acknowledgement. The paper ends RELEASED."""
import json, shutil
import pytest
from pathfinder import paper, presentation, release, research, edit, stub
from stubcampaign import make

needs_tex = pytest.mark.skipif(not (shutil.which("latexmk") and shutil.which("pdftotext")), reason="TeX or pdftotext missing")
DISCLOSURE = ("# DRAFT for the operator\n"
              "This paper was produced with Pathfinder (\\url{https://github.com/vd1/pathfinder}), which proposed the\n"
              "question by combining two earlier papers~\\cite{Q,P}.\n")


def test_comments_go_without_leaving_a_percent_sign_and_spacing_is_kept():
    tex = ("\\begin{document}\nWe show% ledger 3\n"
           "ed it.\nA claim. % ledger 4, 5\nNext line.\n% a whole-line comment\n"
           "\\foo% joined\nbar and 50\\% of it.\n\\end{document}\n")
    out, pointers = release.strip_comments(tex)
    assert "%" not in out.replace("\\%", "")
    assert "We showed it." in out and "A claim.\nNext line." in out and "\\foo bar and 50\\% of it." in out
    assert [p["pointer"] for p in pointers] == ["ledger 3", "ledger 4, 5"]


def test_a_comment_before_a_blank_line_keeps_the_paragraph_break():
    out, _ = release.strip_comments("First paragraph.%\n\nSecond.\n")
    assert out == "First paragraph.\n\nSecond.\n"


def test_keys_become_author_initials_and_year():
    bib = ("@article{Q,\n  author = {Luongo, Alessandro and Shao, Changpeng},\n  year = {2020}\n}\n"
           "@article{somma,\n  author = {{\\v{S}}omma, Rolando},\n  year = {2019}\n}\n"
           "@article{other,\n  author = {Luongo, A. and Shao, C.},\n  year = {2020}\n}\n")
    assert release.new_keys(bib) == {"Q": "LS20a", "somma": "S19", "other": "LS20b"}


LEAKY = ("\\begin{document}\nIn P's convention, and by paper Q, the ledger shows it; pair Q12-P34; ada agreed in round 2.\n"
         "Each walk branches twice.\n\\section*{Use of artificial intelligence}\nMade with Pathfinder.\n\\end{document}\n")


def test_the_leak_check_finds_pipeline_terms_outside_the_acknowledgement(tmp_path):
    c = make(tmp_path)
    hits = " ".join(h.split(" in ...")[0] for h in release.leak_check(c, LEAKY, ""))   # the terms, not their context
    for term in ("P's", "paper Q", "ledger", "Q12-P34", "ada", "round 2"):
        assert term in hits
    assert "branches" not in hits and "Pathfinder" not in hits


def test_the_leak_check_reads_the_campaigns_own_peer_names(tmp_path):
    c = make(tmp_path, peers=["vera", "otto"])
    assert any("otto" in h for h in release.leak_check(c, "\\begin{document}\nAs otto noted.\n\\end{document}\n", ""))


def _cleared(tmp_path, monkeypatch, **kw):
    c = make(tmp_path, presentation=True, release={"disclosure": "disclosure.tex"}, **kw)
    (c.root / "disclosure.tex").write_text(DISCLOSURE)
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    real = stub.reply
    def author(campaign, request):                   # a paper that cites both source papers under Q and P
        text = real(campaign, request)
        if request.stage == "author":
            pd = campaign.thread_dir("Q1P1") / "paper"
            (pd / "references.bib").write_text(
                (pd / "references.bib").read_text()
                + "@article{Q,\n  author = {Doe, Jane},\n  title = {Q paper 1},\n  eprint = {q1},\n  year = {2020}\n}\n"
                + "@article{P,\n  author = {Roe, Richard},\n  title = {P paper 1},\n  eprint = {p1},\n  year = {2021}\n}\n")
            (pd / "paper.tex").write_text((pd / "paper.tex").read_text().replace(
                "\\cite{stub}.", "\\cite{stub}, building on \\cite{Q} and \\cite{P}. % ledger 1, 2"))
        return text
    monkeypatch.setattr(stub, "reply", author)
    monkeypatch.setattr(paper, "_arxiv_titles", lambda ids: {})
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    monkeypatch.setattr(stub, "reply", real)
    assert presentation.run(c, "Q1P1") == "CLEARED"
    return c


@needs_tex
def test_a_cleared_paper_is_released_as_a_clean_article(tmp_path, monkeypatch):
    c = _cleared(tmp_path, monkeypatch)
    out = release.run(c, "Q1P1")
    pd = c.thread_dir("Q1P1") / "paper"
    tex = (pd / "release/paper.tex").read_text()
    assert out["status"] == "RELEASED" and paper.status(c, "Q1P1")["status"] == "RELEASED"
    assert (pd / "release/paper.pdf").exists() and "pathfinder-paper" not in tex and "%" not in tex.replace("\\%", "")
    assert "\\section*{Use of artificial intelligence}" in tex and "\\cite{D20,R21}" in tex
    assert "\\cite{D20}" in tex and "@article{R21," in (pd / "release/references.bib").read_text()
    prov = json.loads((pd / "provenance.json").read_text())
    assert prov["keys"]["Q"] == "D20" and prov["pointers"][0]["pointer"] == "ledger 1, 2"
    assert not (pd / "release/provenance.json").exists()


@needs_tex
def test_a_release_with_a_leak_stops_and_the_paper_stays_cleared(tmp_path, monkeypatch):
    c = _cleared(tmp_path, monkeypatch)
    st = presentation.state(c, "Q1P1")
    final = c.thread_dir("Q1P1") / "paper/presentation" / st["stage"] / "paper.tex"
    final.write_text(final.read_text().replace("building on", "building, as the ledger shows, on"))
    paper._set(c, "Q1P1", cleared_sha256=presentation.sha(final.read_text()))
    with pytest.raises(SystemExit, match="ledger"):
        release.run(c, "Q1P1")
    assert paper.status(c, "Q1P1")["status"] == "CLEARED"


def test_release_refuses_a_paper_that_is_not_cleared(tmp_path):
    c = make(tmp_path, release={"disclosure": "disclosure.tex"})
    with pytest.raises(SystemExit, match="not CLEARED"):
        release.run(c, "Q1P1")


@needs_tex
def test_release_refuses_a_manuscript_changed_since_clearance(tmp_path, monkeypatch):
    c = _cleared(tmp_path, monkeypatch)
    final = c.thread_dir("Q1P1") / "paper/presentation" / presentation.state(c, "Q1P1")["stage"] / "paper.tex"
    final.write_text(final.read_text() + "\n")
    with pytest.raises(SystemExit, match="changed since"):
        release.run(c, "Q1P1")


@needs_tex
def test_release_refuses_without_an_acknowledgement_or_with_its_placeholder(tmp_path, monkeypatch):
    c = _cleared(tmp_path, monkeypatch)
    (c.root / "disclosure.tex").write_text(DISCLOSURE + "[TO BE CHOSEN by the operator]\n")
    with pytest.raises(SystemExit, match="TO BE CHOSEN"):
        release.run(c, "Q1P1")
    (c.root / "disclosure.tex").unlink()
    with pytest.raises(SystemExit, match="disclosure"):
        release.run(c, "Q1P1")

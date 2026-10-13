"""`edit PAIR --recheck` (nobel): the reference checks of a done edit run again without a model call, so a
transient note such as an arXiv 429 does not stay attached to it."""
import json
import pytest
from pathfinder import cli, edit, paper, research, transport
from stubcampaign import make


def _edited(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    ed = c.thread_dir("Q1P1") / "edited"
    (ed / "references.bib").write_text((ed / "references.bib").read_text()
                                       + "@misc{lkw,\n  title = {Halving the cost of quantum addition},\n  eprint = {1907.11679},\n  year = {2019}\n}\n")
    (ed / "note.tex").write_text((ed / "note.tex").read_text().replace("\\end{document}", "\\cite{lkw}\n\\end{document}"))
    edit._set(c, "Q1P1", checks=["arXiv lookup failed: HTTP Error 429: Unknown Error"])
    return c


def test_a_recheck_replaces_a_stale_lookup_failure_without_a_model_call(tmp_path, monkeypatch):
    c = _edited(tmp_path)
    monkeypatch.setattr(paper, "_arxiv_titles", lambda ids: {i: "Halving the cost of quantum addition" for i in ids})
    monkeypatch.setattr(transport, "execute", lambda *a, **k: pytest.fail("no model call"))
    before = transport.receipts(c)
    checks = edit.recheck(c, "Q1P1")
    s = edit.status(c, "Q1P1")
    assert s["status"] == "done" and s["checks"] == checks and not any("lookup failed" in x or "lkw" in x for x in checks)
    assert s["rechecked"] and transport.receipts(c) == before


def test_a_recheck_still_failing_keeps_the_note(tmp_path, monkeypatch):
    c = _edited(tmp_path)
    def fail(ids):
        raise OSError("HTTP Error 429")
    monkeypatch.setattr(paper, "_arxiv_titles", fail)
    assert any("lookup failed" in x for x in edit.recheck(c, "Q1P1"))


def test_a_pair_without_an_edited_note_is_refused(tmp_path):
    c = make(tmp_path)
    with pytest.raises(SystemExit, match="no edited note"):
        edit.recheck(c, "Q1P1")


def test_the_command_line_rechecks(tmp_path, monkeypatch, capsys):
    c = _edited(tmp_path)
    monkeypatch.setattr(paper, "_arxiv_titles", lambda ids: {i: "whatever" for i in ids})
    cli.main(["--root", str(c.root), "edit", "Q1P1", "--recheck"])
    assert "Q1P1: references rechecked" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="needs a pair"):
        cli.main(["--root", str(c.root), "edit", "--recheck"])

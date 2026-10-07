"""Every shared document (the edited note and the paper) ends with a short protocol section written by the engine,
not by an agent: how the research was run, which models proposed and which verified, how it was edited, the
engine release, and the date and time of production as dd-mm-yyyy-hh-mm (UTC)."""
import json, re, shutil
import pytest
from pathfinder import edit, paper, protocol, research
from stubcampaign import make

needs_tex = pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")


def _edited(tmp_path, **kw):
    c = make(tmp_path, **kw)
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    return c


def test_the_protocol_names_the_scheme_the_proposers_the_verifiers_and_the_date(tmp_path):
    c = _edited(tmp_path, peers=["ada", "emmy"], routes={"verify": {"model": "verifier-model"}})
    text = protocol.describe(c, "Q1P1")
    assert "two peers" in text and "ada" in text
    assert "Proposers" in text and "stub" in text and "Verifiers" in text and "verifier-model" in text
    assert re.search(r"\d{2}-\d{2}-\d{4}-\d{2}-\d{2} UTC", text)
    assert "single editor" in text


def test_a_composable_pair_describes_its_branches(tmp_path):
    c = make(tmp_path, research_scheme="composable", branches=3)
    assert "three independent branches" in protocol.describe(c, "Q1P1")


def test_the_edited_note_and_the_paper_carry_it_and_the_research_note_does_not(tmp_path):
    c = _edited(tmp_path)
    d = c.thread_dir("Q1P1")
    assert "\\pathfinderprotocol{" in (d / "edited" / "pathfinder-meta.tex").read_text()
    assert "\\pathfinderprotocol{" not in (d / "pathfinder-meta.tex").read_text()


def test_it_can_be_turned_off(tmp_path):
    c = _edited(tmp_path, protocol_section=False)
    assert "\\pathfinderprotocol{" not in (c.thread_dir("Q1P1") / "edited" / "pathfinder-meta.tex").read_text()


@needs_tex
def test_the_built_note_shows_the_protocol(tmp_path):
    import subprocess
    c = _edited(tmp_path)
    pdf = c.thread_dir("Q1P1") / "edited" / "note.pdf"
    text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
    assert "Protocol" in text and "Proposers" in text


def test_a_rebuilt_note_is_dated_when_it_was_produced(tmp_path):
    c = _edited(tmp_path)
    text = protocol.describe(c, "Q1P1", produced="2026-10-06T09:41:00Z")
    assert "Produced 06-10-2026-09-41 UTC" in text

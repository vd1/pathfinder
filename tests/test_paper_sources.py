"""A document's header links each paper to where it comes from: arXiv for an arXiv record, its own URL and kind
otherwise. proofTree's planar manuscript is a pinned GitHub source; its header was labelled arXiv and linked to an
abstract that does not exist (PF-05, 7 October 2026)."""
import json, shutil, subprocess
import pytest
from pathfinder import edit, research, thread
from stubcampaign import make

needs_tex = pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
GITHUB = {"id": "openai-math-planar-packing-2026-09-23", "title": "A sharp Fourier certificate for planar circle packing",
          "abstract": "We resolve the planar Cohn-Elkies sharpness conjecture.", "source_type": "github",
          "url": "https://github.com/openai/math/blob/adc7f12/planar.pdf"}


@pytest.mark.parametrize("row, url, label", [
    ({"id": "2401.00001v2"}, "https://arxiv.org/abs/2401.00001v2", "arXiv:2401.00001v2"),
    ({"id": "math/0601001"}, "https://arxiv.org/abs/math/0601001", "arXiv:math/0601001"),
    (GITHUB, GITHUB["url"], "GitHub: openai-math-planar-packing-2026-09-23"),
    ({"id": "local-notes-1"}, "", "local-notes-1"),
])
def test_a_paper_is_linked_to_its_own_source(row, url, label):
    assert thread.paper_source(row) == (url, label)


def _github_pair(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    (c.thread_dir("Q1P1") / "inputs" / "Q.json").write_text(json.dumps(GITHUB))
    return c


def test_an_arxiv_pair_writes_no_source_overrides(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    d = c.thread_dir("Q1P1")
    for side in "QP":
        (d / "inputs" / f"{side}.json").write_text(json.dumps({"id": "2401.0000" + ("1" if side == "Q" else "2"), "title": side}))
    assert "\\pathfindersources" not in thread.write_meta(c, "Q1P1", d).read_text()


def test_a_github_paper_gets_its_url_and_kind_in_the_header(tmp_path):
    c = _github_pair(tmp_path)
    meta = thread.write_meta(c, "Q1P1", c.thread_dir("Q1P1")).read_text()
    assert "\\pathfindersources{https://github.com/openai/math/blob/adc7f12/planar.pdf}{GitHub: openai-math-planar-packing-2026-09-23}" in meta


@needs_tex
def test_the_built_note_names_the_github_source_and_not_arxiv(tmp_path):
    c = _github_pair(tmp_path)
    assert edit.run(c, "Q1P1") == "done"
    pdf = c.thread_dir("Q1P1") / "edited" / "note.pdf"
    text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
    assert "GitHub: openai-math-planar-packing" in text and "arXiv:openai" not in text

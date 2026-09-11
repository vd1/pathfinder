import json, shutil, sys
from pathlib import Path
import pytest
from pathfinder import edit, research, transport
from pathfinder.config import Campaign

FAKE = f"{sys.executable} {Path(__file__).parent / 'fake_cli.py'}"


@pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
def test_editor_writes_a_readable_note(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    (tmp_path / "campaign.json").write_text("{}")
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=False, seats=1, cut=1, rounds=1,
                 allowances={"edit_seconds": 60}, budget_usd=9, prices={}, scan_fulltext=None)
    (tmp_path / "Q.jsonl").write_text('{"id":"a","title":"A","abstract":"aa","text":null}\n')
    (tmp_path / "P.jsonl").write_text('{"id":"b","title":"B","abstract":"bb","text":null}\n')
    d = research.prepare(c, "Q1P1"); (d / "ledger.jsonl").write_text("{}\n"); (d / "Q1P1.tex").write_text("note")
    research._set(c, "Q1P1", status="PAUSE", stage="done")
    tex = "\\documentclass{article}\\usepackage{url}\\begin{document}Plain words \\cite{q}.\\bibliographystyle{plain}\\bibliography{references}\\end{document}"
    bib = "@misc{q, title={T}, author={A}, year={2024}, howpublished={\\url{https://x.org}}}"
    monkeypatch.setenv("FAKE_RUN", f"mkdir -p edited && printf '%s' '{tex}' > edited/note.tex && printf '%s' '{bib}' > edited/references.bib")
    monkeypatch.setenv("FAKE_REPLY", "done")
    monkeypatch.setattr(edit, "check_references", lambda tex, bib: [])
    assert edit.run(c, "Q1P1") == "done"
    assert (d / "edited" / "note.pdf").exists() and edit.status(c, "Q1P1")["build_ok"]

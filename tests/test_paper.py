import json, shutil, sys
from pathlib import Path
import pytest
from pathfinder import paper, research, transport
from pathfinder.config import Campaign

FAKE = f"{sys.executable} {Path(__file__).parent / 'fake_cli.py'}"
BIB = """@misc{q, title = {A Title}, author = {Ann}, year = {2024}, howpublished = {arXiv:2409.00001. \\url{https://arxiv.org/abs/2409.00001}} }
@misc{p, title = {Other}, author = {Bob}, year = {2024}, note = {no identifier} }
@misc{unused, title = {Never cited}, author = {Cy}, year = {2020}, howpublished = {\\url{https://x.org}} }
"""


def test_check_references_offline():
    tex = "text \\cite{q} and \\cite{p,missing}"
    notes = paper.check_references(tex, BIB, fetch=lambda ids: {"2409.00001": "a totally different title here"})
    assert any("missing" in n for n in notes) and any("unused" in n for n in notes)
    assert any("p: no URL" in n for n in notes) and any("q: title does not match" in n for n in notes)
    assert not paper.check_references("\\cite{q}", BIB.split("@misc{p")[0], fetch=lambda ids: {"2409.00001": "A title"})


@pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
def test_paper_round_trip_accepts(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    (tmp_path / "campaign.json").write_text("{}")
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=False, seats=1, cut=1, rounds=1,
                 allowances={"paper_seconds": 60, "review_seconds": 60}, budget_usd=9, prices={}, scan_fulltext=None, raw={"paper_rounds": 2})
    (tmp_path / "Q.jsonl").write_text('{"id":"a","title":"A","abstract":"aa","text":null}\n')
    (tmp_path / "P.jsonl").write_text('{"id":"b","title":"B","abstract":"bb","text":null}\n')
    d = research.prepare(c, "Q1P1"); (d / "ledger.jsonl").write_text(json.dumps({"seq": 1, "actor": "ada", "kind": "finding", "text": "x", "at": "t"}) + "\n")
    (d / "Q1P1.tex").write_text("note"); research._set(c, "Q1P1", status="DRAFT", stage="done")
    tex = "\\documentclass{article}\\usepackage{url}\\begin{document}Hello \\cite{q}.\\bibliographystyle{plain}\\bibliography{references}\\end{document}"
    bib = "@misc{q, title={T}, author={A}, year={2024}, howpublished={\\url{https://x.org}}}"
    monkeypatch.setenv("FAKE_RUN", f"mkdir -p paper && printf '%s' '{tex}' > paper/paper.tex && printf '%s' '{bib}' > paper/references.bib")
    real = transport.call

    def fake_call(prompt, **kw):
        if kw["stage"] == "review":
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", '{"decision":"ACCEPT","summary":"fine","findings":[]}')
        else:
            monkeypatch.setenv("FAKE_REPLY", "wrote it")
        return real(prompt, **kw)
    monkeypatch.setattr(paper.transport, "call", fake_call)
    monkeypatch.setattr(paper, "_arxiv_titles", lambda ids: {})
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    s = paper.status(c, "Q1P1")
    assert s["status"] == "ACCEPTED" and s["build_ok"] and (d / "paper" / "paper.pdf").exists()
    assert json.loads((d / "paper" / "review.json").read_text())[0]["decision"] == "ACCEPT"

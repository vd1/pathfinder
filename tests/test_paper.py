import json, shutil, subprocess, sys
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
            # static material first, the paper after it, the instruction last
            assert prompt.index("## ledger.jsonl") < prompt.index("## paper.tex") < prompt.index("## your task")
            assert prompt.rstrip().endswith("}") and "independent reviewer" in prompt[prompt.index("## your task"):]
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


@pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
def test_review_only_round_on_hand_edited_paper(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    (tmp_path / "campaign.json").write_text("{}")
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=False, seats=1, cut=1, rounds=1,
                 allowances={"review_seconds": 60}, budget_usd=9, prices={}, scan_fulltext=None, raw={"paper_rounds": 1})
    (tmp_path / "Q.jsonl").write_text('{"id":"a","title":"A","abstract":"aa","text":null}\n')
    (tmp_path / "P.jsonl").write_text('{"id":"b","title":"B","abstract":"bb","text":null}\n')
    d = research.prepare(c, "Q1P1"); (d / "ledger.jsonl").write_text(json.dumps({"seq": 1, "actor": "ada", "kind": "finding", "text": "x", "at": "t"}) + "\n")
    (d / "Q1P1.tex").write_text("note"); research._set(c, "Q1P1", status="DRAFT", stage="done")
    pd = d / "paper"; pd.mkdir()
    (pd / "paper.tex").write_text("\\documentclass{article}\\usepackage{url}\\begin{document}Edited by hand \\cite{q}.\\bibliographystyle{plain}\\bibliography{references}\\end{document}")
    (pd / "references.bib").write_text("@misc{q, title={T}, author={A}, year={2024}, howpublished={\\url{https://x.org}}}")
    (pd / "review.json").write_text(json.dumps([{"round": 1, "decision": "AMEND", "summary": "old", "findings": []}]))
    paper._set(c, "Q1P1", status="PAUSE-ON-AMEND", round=1)
    monkeypatch.setattr(paper, "_arxiv_titles", lambda ids: {})
    calls = []
    real = transport.call

    def fake_call(prompt, **kw):
        calls.append(kw["stage"]); monkeypatch.setenv("FAKE_REPLY", '{"decision":"ACCEPT","summary":"fine now","findings":[]}')
        return real(prompt, **kw)
    monkeypatch.setattr(paper.transport, "call", fake_call)
    assert paper.review(c, "Q1P1") == "ACCEPTED"          # beyond paper_rounds: the owner's round is not budgeted
    assert calls == ["review"]                            # no author call
    s = paper.status(c, "Q1P1"); assert s["status"] == "ACCEPTED" and s["round"] == 2
    assert [r["round"] for r in json.loads((pd / "review.json").read_text())] == [1, 2]


def test_tex_env_exposes_the_style_files():
    env = paper.tex_env()
    assert str(paper.STYLES) in env["TEXINPUTS"] and (paper.STYLES / "pathfinder-paper.sty").exists()


@pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
@pytest.mark.parametrize("style,body", [
    ("pathfinder-note", "\\pathfinderpapers{2608.29130}{A Title with \\& and \\%}{2609.04460}{Other}\\section{The pair}\\begin{claim}x\\end{claim} see \\ledger{3}"),
    ("pathfinder-readable", "\\begin{abstract}a\\end{abstract}\\section{One}\\begin{theorem}t\\end{theorem}"),
    ("pathfinder-paper", "\\begin{abstract}a\\end{abstract}\\section{One}\\begin{assumption}t\\end{assumption}\\begin{remark}r\\end{remark}"),
])
def test_each_style_builds(tmp_path, style, body):
    (tmp_path / "doc.tex").write_text(f"\\documentclass{{article}}\\usepackage{{{style}}}\\pathfinderpair{{Q1P1}}\\title{{T}}"
                                     f"\\begin{{document}}\\maketitle {body} \\(x\\) \\end{{document}}")
    ok, log = paper.build(tmp_path, "doc.tex")
    assert ok, log


def test_paper_meta_escapes_titles(tmp_path):
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs" / "Q.json").write_text(json.dumps({"id": "2608.29130", "title": "Alpha & Beta: 50% of $x_1$"}))
    (tmp_path / "inputs" / "P.json").write_text(json.dumps({"id": "2609.04460", "title": "Plain"}))
    m = research.paper_meta(tmp_path)
    assert m["Q_ID"] == "2608.29130" and m["Q_TITLE"] == "Alpha \\& Beta: 50\\% of \\$x\\_1\\$" and m["P_TITLE"] == "Plain"


@pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
def test_meta_file_opens_the_document(tmp_path):
    from pathfinder import research
    (tmp_path / "campaign.json").write_text("{}")
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=False, seats=1, cut=1, rounds=1,
                 allowances={}, budget_usd=9, prices={}, scan_fulltext=None)
    d = tmp_path / "threads" / "Q1P1"; (d / "inputs").mkdir(parents=True)
    (d / "inputs" / "Q.json").write_text(json.dumps({"id": "2608.29130", "title": "Alpha & Beta"}))
    (d / "inputs" / "P.json").write_text(json.dumps({"id": "2609.04460", "title": "Gamma"}))
    (d / "status.json").write_text(json.dumps({"status": "DRAFT", "round": 3, "stage": "done"}))
    (d / "Q1P1.verdict.json").write_text(json.dumps([{"round": 1, "decision": "ITERATE"}, {"round": 2, "decision": "REVISE"}, {"round": 2, "decision": "DRAFT"}]))
    meta = research.write_meta(c, "Q1P1", d)
    t = meta.read_text()
    assert "\\pathfinderpair{Q1P1}" in t and "Alpha \\& Beta" in t and "Research phase: DRAFT after 3 rounds, 1 ITERATE, 1 REVISE" in t
    (d / "doc.tex").write_text("\\documentclass{article}\\usepackage{pathfinder-note}\\title{T}\\begin{document}\\maketitle x\\end{document}")
    ok, log = paper.build(d, "doc.tex"); assert ok, log
    txt = subprocess.run(["pdftotext", str(d / "doc.pdf"), "-"], capture_output=True, text=True).stdout
    assert "Alpha & Beta" in txt and "arXiv:2608.29130" in txt and "1 ITERATE, 1 REVISE" in txt

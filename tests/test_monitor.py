import json
from pathfinder import monitor
from pathfinder.config import Campaign


def test_state_and_status_text(tmp_path):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=2, cut=50,
                 rounds=3, allowances={}, budget_usd=10, prices={}, scan_fulltext=None)
    (tmp_path / "Q.jsonl").write_text('{"id":"a","title":"A"}\n'); (tmp_path / "P.jsonl").write_text('{"id":"b","title":"B"}\n{"id":"c","title":"C"}\n')
    (tmp_path / "scan.jsonl").write_text(json.dumps({"pair_id": "Q1P1", "feasibility": 80, "gain": 50, "cost": 0.1}) + "\n")
    (tmp_path / "shortlist.json").write_text(json.dumps({"cut": 50, "pairs": [{"pair_id": "Q1P1", "score": 4000}]}))
    (tmp_path / "receipts.jsonl").write_text(json.dumps({"thread": "Q1P1", "stage": "peers", "cost": 2.5, "seconds": 30}) + "\n")
    d = tmp_path / "threads" / "Q1P1"; d.mkdir(parents=True)
    (d / "status.json").write_text(json.dumps({"pair_id": "Q1P1", "round": 1, "stage": "peers", "status": "running"}))
    (d / "ledger.jsonl").write_text(json.dumps({"seq": 1, "actor": "ada", "kind": "idea", "text": "x", "at": "t"}) + "\n")
    s = monitor.state(c)
    assert s["campaign"]["spend"] == 2.5 and s["campaign"]["phase"] == "research"
    assert s["scan"]["done"] == 1 and s["scan"]["total"] == 2 and s["scan"]["grid"][0][0] == 4000
    assert s["threads"]["Q1P1"]["entries"] == 1 and s["shortlist"][0]["spend"] == 2.5
    assert "Q1P1" in monitor.status_text(c)


def test_pdf_compiles_a_note(tmp_path):
    import shutil, pytest
    if not shutil.which("pdflatex"):
        pytest.skip("pdflatex not installed")
    tex = tmp_path / "Q1P1.tex"
    tex.write_text("\\documentclass{article}\\begin{document}hello\\end{document}\n")
    data, log = monitor.pdf(tex)
    assert data[:4] == b"%PDF" and "Output written" in log
    tex.write_text("\\documentclass{article}\\begin{document}\\undefinedmacro\\end{document}\n")
    data, log = monitor.pdf(tex)
    assert data == b"" and "Undefined control sequence" in log


def test_export_writes_a_static_page_and_thread_files(tmp_path):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=2, cut=50,
                 rounds=3, allowances={}, budget_usd=10, prices={}, scan_fulltext=None)
    (tmp_path / "Q.jsonl").write_text('{"id":"a","title":"A"}\n'); (tmp_path / "P.jsonl").write_text('{"id":"b","title":"B"}\n')
    (tmp_path / "shortlist.json").write_text(json.dumps({"cut": 50, "pairs": [{"pair_id": "Q1P1", "q": "a", "p": "b", "score": 1}]}))
    d = tmp_path / "threads" / "Q1P1"; (d / "inputs").mkdir(parents=True); (d / "edited").mkdir()
    (d / "status.json").write_text(json.dumps({"pair_id": "Q1P1", "round": 1, "stage": "done", "status": "PAUSE"}))
    (d / "ledger.jsonl").write_text(json.dumps({"seq": 1, "actor": "ada", "kind": "idea", "text": "x", "at": "t"}) + "\n")
    (d / "inputs" / "Q.tex").write_text("source"); (d / "inputs" / "Q.json").write_text("{}")
    (d / "edited" / "note.pdf").write_bytes(b"%PDF-fake"); (d / "Q1P1.aux").write_text("noise")
    out = monitor.export(c, tmp_path / "bundle")
    page = (out / "index.html").read_text()
    assert "window.STATIC = true" in page and '"pair_id": "Q1P1"' in page
    assert (out / "threads" / "Q1P1" / "edited" / "note.pdf").exists() and (out / "threads" / "Q1P1" / "inputs" / "Q.json").exists()
    assert not (out / "threads" / "Q1P1" / "inputs" / "Q.tex").exists() and not (out / "threads" / "Q1P1" / "Q1P1.aux").exists()
    z = monitor.export(c, tmp_path / "bundle2", zip_it=True)
    assert z.suffix == ".zip" and z.exists()

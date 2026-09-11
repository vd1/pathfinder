from pathfinder import corpus
from pathfinder.config import Campaign

ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><id>http://arxiv.org/abs/2409.00001v2</id><title>A  title
 wrapped</title><summary> The abstract. </summary><published>2024-09-01T00:00:00Z</published>
<author><name>Ann</name></author><author><name>Bob</name></author></entry></feed>"""


def test_parse_atom():
    rows = corpus.parse_atom(ATOM)
    assert rows == [{"id": "2409.00001", "title": "A title wrapped", "abstract": "The abstract.",
                     "authors": ["Ann", "Bob"], "date": "2024-09-01", "text": None}]


def test_body_falls_back_to_abstract(tmp_path):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=1, cut=1,
                 rounds=1, allowances={}, budget_usd=1, prices={}, scan_fulltext=None)
    row = {"id": "x", "title": "t", "abstract": "abs", "text": None}
    assert corpus.body(c, row, fulltext=True) == "abs"
    (tmp_path / "sources").mkdir(); (tmp_path / "sources" / "x.tex").write_text("full")
    row["text"] = "sources/x.tex"
    assert corpus.body(c, row, fulltext=True) == "full" and corpus.body(c, row, fulltext=False) == "abs"
    assert corpus.pair_id(2, 3) == "Q2P3"


def test_sources_survive_a_bad_eprint(tmp_path, monkeypatch, capsys):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=1, cut=1,
                 rounds=1, allowances={}, budget_usd=1, prices={}, scan_fulltext=None)
    (tmp_path / "Q.jsonl").write_text('{"id":"bad","title":"t","abstract":"a","text":null}\n{"id":"good","title":"t","abstract":"a","text":null}\n')
    (tmp_path / "sources").mkdir(); (tmp_path / "sources" / "good.tex").write_text("x")
    monkeypatch.setattr(corpus.time, "sleep", lambda s: None)
    monkeypatch.setattr(corpus, "flatten", lambda aid, out: (_ for _ in ()).throw(RuntimeError("boom")) if aid == "bad" else f"sources/{aid}.tex")
    corpus.sources(c, "Q")
    rows = corpus.read(tmp_path / "Q.jsonl")
    assert rows[0]["text"] is None and rows[1]["text"] == "sources/good.tex" and "no source" in capsys.readouterr().out

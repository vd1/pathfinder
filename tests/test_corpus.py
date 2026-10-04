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


def _arxiv(monkeypatch, replies):
    """The arXiv API as a queue of replies: an HTTP status code is an error, text is a response body."""
    import io, urllib.error
    calls, sleeps = [], []

    def urlopen(request, timeout):
        calls.append((request, timeout))
        reply = replies.pop(0)
        if isinstance(reply, int):
            raise urllib.error.HTTPError(request.full_url, reply, "status", {}, None)
        return io.BytesIO(reply.encode())
    monkeypatch.setattr(corpus.net, "urlopen", urlopen)
    monkeypatch.setattr(corpus.time, "sleep", sleeps.append)
    return calls, sleeps


def test_an_arxiv_query_backs_off_on_rate_limits_and_names_its_client(monkeypatch):
    import urllib.error, pytest
    calls, sleeps = _arxiv(monkeypatch, [429, 429, ATOM])
    assert corpus.query({"id_list": "2409.00001", "max_results": 1}) == ATOM
    request, timeout = calls[0]
    assert request.full_url == corpus.API + "id_list=2409.00001&max_results=1" and timeout == 60
    assert request.get_header("User-agent", "").startswith("pathfinder") and sleeps == [10, 20]
    calls, sleeps = _arxiv(monkeypatch, [429, 429, 429])
    with pytest.raises(urllib.error.HTTPError):
        corpus.query({"id_list": "x"}, timeout=5)
    assert len(calls) == 3 and sleeps == [10, 20] and calls[0][1] == 5
    calls, sleeps = _arxiv(monkeypatch, [503])
    with pytest.raises(urllib.error.HTTPError):                     # only a rate limit is asked again
        corpus.query({"id_list": "x"})
    assert len(calls) == 1 and sleeps == []


def test_paper_title_checks_use_the_same_query(monkeypatch):
    from pathfinder import paper
    calls, _ = _arxiv(monkeypatch, [429, ATOM])
    assert paper._arxiv_titles(["2409.00001"]) == {"2409.00001": "A title wrapped"}
    assert len(calls) == 2 and calls[0][0].get_header("User-agent")

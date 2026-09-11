import json
from pathfinder import corpus, select
from pathfinder.config import Campaign


def make(tmp_path):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=1, cut=1,
                 rounds=1, allowances={}, budget_usd=1, prices={}, scan_fulltext=None)
    (tmp_path / "fetch.json").write_text(json.dumps({"q": "alpha", "p": "beta", "n": 2, "q_start": 2, "p_start": 2}))
    (tmp_path / "Q.jsonl").write_text('{"id":"q1","title":"A"}\n{"id":"q2","title":"B"}\n')
    return c


def test_more_appends_without_reordering_and_dedupes(tmp_path):
    c = make(tmp_path)
    calls = []

    def fake(query, n, start=0):
        calls.append((query, n, start))
        return [{"id": "q2", "title": "B"}, {"id": "q3", "title": "C"}]
    new = corpus.more(c, "Q", 2, fetch_fn=fake)
    assert [r["id"] for r in new] == ["q3"] and calls == [("alpha", 2, 2)]
    assert [r["id"] for r in corpus.read(tmp_path / "Q.jsonl")] == ["q1", "q2", "q3"]
    assert json.loads((tmp_path / "fetch.json").read_text())["q_start"] == 4


def test_select_by_threshold_ignores_completeness(tmp_path):
    c = make(tmp_path)
    (tmp_path / "P.jsonl").write_text('{"id":"p1"}\n{"id":"p2"}\n')
    rows = [{"pair_id": "Q1P1", "q": "q1", "p": "p1", "feasibility": 50, "gain": 40},
            {"pair_id": "Q2P1", "q": "q2", "p": "p1", "feasibility": 10, "gain": 10}]
    (tmp_path / "scan.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    out = select.run(c, min_score=1500)
    assert out["n_selected"] == 1 and out["pairs"][0]["pair_id"] == "Q1P1" and out["cut"] is None and out["min_score"] == 1500


def test_select_keeps_pairs_whose_thread_started(tmp_path):
    c = make(tmp_path)
    (tmp_path / "P.jsonl").write_text('{"id":"p1"}\n{"id":"p2"}\n')
    rows = [{"pair_id": "Q1P1", "q": "q1", "p": "p1", "feasibility": 50, "gain": 40},
            {"pair_id": "Q2P1", "q": "q2", "p": "p1", "feasibility": 10, "gain": 10}]
    (tmp_path / "scan.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp_path / "threads" / "Q2P1").mkdir(parents=True); (tmp_path / "threads" / "Q2P1" / "status.json").write_text("{}")
    out = select.run(c, min_score=1500)
    assert [p["pair_id"] for p in out["pairs"]] == ["Q1P1", "Q2P1"]

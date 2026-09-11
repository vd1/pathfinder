import json
from pathfinder import select
from pathfinder.config import Campaign


def rows():
    return [{"pair_id": "Q1P1", "q": "a", "p": "b", "feasibility": 90, "gain": 10},
            {"pair_id": "Q1P2", "q": "a", "p": "c", "feasibility": 50, "gain": 50},
            {"pair_id": "Q2P1", "q": "d", "p": "b", "feasibility": 30, "gain": 30},
            {"pair_id": "Q2P2", "q": "d", "p": "c", "feasibility": None, "gain": None, "error": "x"}]


def test_rank_by_product_then_min_then_id():
    # 2500 first; then the 900 tie is broken by the larger minimum axis (30 over 10)
    assert [r["pair_id"] for r in select.rank(rows())] == ["Q1P2", "Q2P1", "Q1P1"]


def test_cut_rounds_up_without_tie_expansion(tmp_path):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=1, cut=1,
                 rounds=1, allowances={}, budget_usd=1, prices={}, scan_fulltext=None)
    (tmp_path / "Q.jsonl").write_text('{"id":"a"}\n{"id":"d"}\n'); (tmp_path / "P.jsonl").write_text('{"id":"b"}\n{"id":"c"}\n')
    (tmp_path / "scan.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows()))
    out = select.run(c, cut=30)
    assert out["n_selected"] == 1 and out["pairs"][0]["pair_id"] == "Q1P2" and len(out["digest"]) == 64

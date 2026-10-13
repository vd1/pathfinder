"""Per-pair weights in the ranking (nobel, 13 October 2026): an optional campaign file maps pair ids to numbers in
[0, 1]; the ranking orders pairs by scan score times weight, a pair absent from the file weighing 1. Without the
file the ranking is as it was. The file's digest is in the shortlist and the run record, so new weights are a
change the next run asks to accept, and the status shows both scores. How the weights were made is the
deployment's business."""
import json
import pytest
from pathfinder import campaign_state, config, provenance, scan, select
from stubcampaign import make

SCORES = {"Q1P1": (90, 90), "Q1P2": (80, 80), "Q2P1": (70, 70), "Q2P2": (60, 60)}
PAIRS = tuple(SCORES)


def _scanned(tmp_path, weights=None, **raw):
    if weights is not None:
        raw["rank_weights"] = "rank-weights.json"
        (tmp_path / "rank-weights.json").write_text(json.dumps(weights))
    c = make(tmp_path, pairs=PAIRS, **raw)
    scan.run(c)
    rows = [json.loads(line) for line in c.path("scan.jsonl").read_text().splitlines()]
    for r in rows:
        r["feasibility"], r["gain"] = SCORES[r["pair_id"]]
    c.path("scan.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return c


def test_without_a_weights_file_the_ranking_and_the_shortlist_are_unchanged(tmp_path):
    c = _scanned(tmp_path)
    out = select.run(c, cut=50)
    assert [p["pair_id"] for p in out["pairs"]] == ["Q1P1", "Q1P2"]
    assert "weights" not in out and set(out["pairs"][0]) == {"pair_id", "q", "p", "score", "feasibility", "gain"}
    assert provenance.record(c, "r")["weights"] is None


def test_the_ranking_orders_by_score_times_weight_and_shows_both(tmp_path):
    c = _scanned(tmp_path, {"revision": "cocitation-1", "weights": {"Q1P1": 0.5, "Q2P1": 1}})
    out = select.run(c, cut=50)
    assert [p["pair_id"] for p in out["pairs"]] == ["Q1P2", "Q2P1"]          # 6400, 4900 over 8100 x 0.5 = 4050
    best = out["pairs"][0]
    assert (best["score"], best["weight"], best["weighted"]) == (6400, 1, 6400)
    assert out["weights"]["revision"] == "cocitation-1" and len(out["weights"]["sha256"]) == 64
    assert out["weights"]["path"] == "rank-weights.json"


def test_a_minimum_score_applies_to_the_weighted_score(tmp_path):
    c = _scanned(tmp_path, {"revision": "r", "weights": {"Q1P1": 0.5}})
    out = select.run(c, min_score=4500)
    assert [p["pair_id"] for p in out["pairs"]] == ["Q1P2", "Q2P1"]


@pytest.mark.parametrize("doc, message", [
    ({"revision": "r", "weights": {"Q1P1": 1.5}}, "between 0 and 1"),
    ({"revision": "r", "weights": {"Q1P1": -0.1}}, "between 0 and 1"),
    ({"revision": "r", "weights": {"Q1P1": True}}, "between 0 and 1"),
    ({"revision": "r", "weights": {"Q1P1": "0.5"}}, "between 0 and 1"),
    ({"weights": {"Q1P1": 0.5}}, "revision"),
    ({"revision": "r", "weights": {}, "note": "x"}, "revision"),
    ([0.5], "revision")])
def test_a_bad_weights_file_is_refused(tmp_path, doc, message):
    c = _scanned(tmp_path, doc)
    with pytest.raises(ValueError, match=message):
        select.run(c, cut=50)


def test_a_named_file_that_is_missing_is_refused(tmp_path):
    c = _scanned(tmp_path, {"revision": "r", "weights": {}})
    c.path("rank-weights.json").unlink()
    with pytest.raises(ValueError, match="rank-weights.json"):
        select.run(c, cut=50)


@pytest.mark.parametrize("value", ["../w.json", "/tmp/w.json", 3, ""])
def test_the_setting_must_name_a_file_inside_the_campaign(tmp_path, value):
    with pytest.raises(ValueError, match="rank_weights"):
        make(tmp_path, rank_weights=value)


def test_new_weights_are_a_change_the_next_run_asks_to_accept(tmp_path):
    c = _scanned(tmp_path, {"revision": "r1", "weights": {"Q1P1": 0.5}})
    provenance.start(c, "first")
    assert provenance.start(c, "same")[1] == []
    c.path("rank-weights.json").write_text(json.dumps({"revision": "r2", "weights": {"Q1P1": 0.4}}))
    rec, changed = provenance.start(c, "second")
    assert rec is None and changed == ["weights"]
    rec, changed = provenance.start(c, "third", accept_change="co-citation prior refit")
    assert changed == ["weights"] and rec["weights"]["revision"] == "r2"


def test_a_record_from_before_weights_existed_is_not_a_change(tmp_path):
    c = _scanned(tmp_path)
    provenance.start(c, "first")
    rec = json.loads(c.path("run.json").read_text()); del rec["weights"]
    c.path("run.json").write_text(json.dumps(rec))
    assert provenance.start(c, "second")[1] == []


def test_the_status_and_the_scan_page_show_both_scores(tmp_path):
    c = _scanned(tmp_path, {"revision": "r", "weights": {"Q1P1": 0.5}})
    select.run(c, cut=100)
    state = campaign_state.build(c)
    u = next(u for u in state["units"] if u["unit"] == "Q1P1")
    assert (u["score"], u["weight"], u["weighted"]) == (8100, 0.5, 4050)
    assert "weighted 4050" in campaign_state.text(state)
    doc = campaign_state.scan_document(c)
    rows = [dict(zip(doc["columns"], r)) for r in doc["rows"]]
    assert [r["pair_id"] for r in rows] == ["Q1P2", "Q2P1", "Q1P1", "Q2P2"]
    assert (rows[2]["score"], rows[2]["weighted"]) == (8100, 4050) and doc["weights"]["revision"] == "r"

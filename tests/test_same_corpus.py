"""A campaign whose Q and P are the same papers (Zoo x Zoo, 10 October 2026) sets "same_corpus": true: the
scan takes each unordered pair once, the lower number on the Q side, and never a paper with itself. Without it
the scan made N² calls: the diagonal, and every pair twice."""
import json
import pytest
from pathfinder import config, scan
from stubcampaign import make


def _same(tmp_path, numbers=None, **raw):
    c = make(tmp_path, **raw)
    rows = [{"id": f"2401.0000{i}", "title": f"Paper {i}", "abstract": f"Abstract {i}.",
             **({"n": numbers[i - 1]} if numbers else {})} for i in (1, 2, 3)]
    for side in "QP":
        (tmp_path / f"{side}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return config.load(tmp_path)


def _scanned(c):
    scan.run(c)
    return sorted(json.loads(line)["pair_id"] for line in c.path("scan.jsonl").read_text().splitlines())


def test_a_same_corpus_scan_takes_each_unordered_pair_once(tmp_path):
    assert _scanned(_same(tmp_path, numbers=[433, 265, 294], same_corpus=True)) == ["Q265-P294", "Q265-P433", "Q294-P433"]


def test_an_unnumbered_same_corpus_orders_by_position(tmp_path):
    assert _scanned(_same(tmp_path, same_corpus=True)) == ["Q1P2", "Q1P3", "Q2P3"]


def test_without_the_setting_every_ordered_pair_is_scanned(tmp_path):
    assert len(_scanned(_same(tmp_path, numbers=[433, 265, 294]))) == 9


def test_a_same_corpus_campaign_whose_sides_differ_is_refused(tmp_path):
    c = _same(tmp_path, same_corpus=True)
    (tmp_path / "P.jsonl").write_text(json.dumps({"id": "2401.99999", "title": "Other", "abstract": "x"}) + "\n")
    with pytest.raises(ValueError, match="same_corpus"):
        scan.run(config.load(tmp_path))


@pytest.mark.parametrize("bad", ["yes", 1])
def test_a_malformed_setting_is_refused_at_load(tmp_path, bad):
    with pytest.raises(ValueError, match="same_corpus"):
        make(tmp_path, same_corpus=bad)

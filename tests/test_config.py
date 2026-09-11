import json
from pathlib import Path
from pathfinder.config import load


def test_load_reads_campaign_and_prices(tmp_path: Path):
    (tmp_path / "campaign.json").write_text(json.dumps({
        "backend": "claude", "model": "m", "seats": 2, "cut": 1, "rounds": 3,
        "allowances": {"peer_seconds": 10, "peer_calls": 1, "consolidate_seconds": 5, "verify_seconds": 5},
        "budget_usd": 1.0, "prices": {"m": {"input_per_m": 1.0, "output_per_m": 2.0}}}))
    c = load(tmp_path)
    assert c.seats == 2 and c.scan_model == "m" and c.peer_search is True
    assert c.price("m", 1_000_000, 500_000) == 2.0
    assert c.thread_dir("Q1P2") == tmp_path / "threads" / "Q1P2"

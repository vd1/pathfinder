from pathlib import Path
from pathfinder import scan
from pathfinder.config import Campaign


def test_campaign_prompts_override_the_package_ones(tmp_path):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=1, cut=1,
                 rounds=1, allowances={}, budget_usd=1, prices={}, scan_fulltext=None)
    default = scan.prompts_dir(c)
    assert (default / "peer.md").exists() and default == Path(__file__).resolve().parent.parent / "prompts"
    (tmp_path / "prompts").mkdir()
    assert scan.prompts_dir(c) == tmp_path / "prompts"

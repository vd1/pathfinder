from pathlib import Path
from pathfinder import resources
from pathfinder.config import Campaign


def test_campaign_prompts_override_the_package_ones(tmp_path):
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=True, seats=1, cut=1,
                 rounds=1, allowances={}, budget_usd=1, prices={}, scan_fulltext=None)
    default = resources.engine_prompts()
    assert (default / "peer.md").exists() and default == Path(__file__).resolve().parent.parent / "prompts"
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "peer.md").write_text("LOCAL")
    assert resources.prompt_template(c, "peer") == "LOCAL"

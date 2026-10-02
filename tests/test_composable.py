"""Composable EVA: N direct-EVA branches, frozen as bundles, then a joint EVA thread (phase 6)."""
import json
import pytest
from pathfinder import composable, config, research, transport
from stubcampaign import make


def test_the_old_scheme_name_is_refused(tmp_path):
    make(tmp_path)
    raw = json.loads((tmp_path / "campaign.json").read_text()); raw["research_scheme"] = "eva_minus"
    (tmp_path / "campaign.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="direct_eva"):
        config.load(tmp_path)

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


def _composable(tmp_path, **raw):
    return make(tmp_path, research_scheme="composable", **raw)


def test_views_have_their_own_scheme_and_directories(tmp_path):
    c = _composable(tmp_path, branch={"rounds": 1}, joint={"rounds": 2})
    assert composable.labels(c) == ["branch-1", "branch-2", "branch-3"]
    b = composable.branch_view(c, "Q1P1", "branch-2")
    assert b.thread_dir("Q1P1") == c.thread_dir("Q1P1") / "branch-runs" / "branch-2"
    assert b.raw["research_scheme"] == "direct_eva" and not b.raw.get("research_bundles") and b.rounds == 1
    assert b.branch == "branch-2" and c.raw["research_scheme"] == "composable"
    j = composable.joint_view(c, "Q1P1")
    assert j.thread_dir("Q1P1") == c.thread_dir("Q1P1") and j.rounds == 2
    assert j.raw["research_scheme"] == "eva" and j.raw["research_bundles"] == [f"branches/branch-{n}" for n in (1, 2, 3)]
    assert getattr(j, "branch", None) is None


def test_branch_calls_are_attributed_to_their_branch(tmp_path):
    c = _composable(tmp_path, branches=2)
    b = composable.branch_view(c, "Q1P1", "branch-2")
    research.prepare(b, "Q1P1")
    research.run_thread(b, "Q1P1")
    rows = transport.receipts(c)
    assert rows and all(r["thread"] == "Q1P1" and r["branch"] == "branch-2" for r in rows)
    events = [json.loads(l) for l in c.path("events.jsonl").read_text().splitlines()]
    assert any(e.get("branch") == "branch-2" for e in events)

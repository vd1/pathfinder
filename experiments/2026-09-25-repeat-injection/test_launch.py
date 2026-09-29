"""No-model-call checks for the pilot coordinator."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from pathfinder import config, edit, health, paper, research, runner

spec = importlib.util.spec_from_file_location("pilot_launch", Path(__file__).with_name("launch.py"))
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


@pytest.fixture
def staged(tmp_path, monkeypatch):
    settings = json.loads((pilot.OLD / "campaign.json").read_text())
    for folder in (tmp_path, tmp_path / "repeat", tmp_path / "reinjection"):
        folder.mkdir(exist_ok=True)
        pilot.save(folder / "campaign.json", settings)
        pilot.save(folder / "shortlist.json", {"pairs": [{"pair_id": "Q1P1"}]})
    schedule = [{"block": 1, "arm": a, "pair": "Q1P1"} for a in pilot.ARMS]
    pilot.save(tmp_path / "manifest.json", {"schedule": schedule})
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    monkeypatch.setattr(pilot, "preflight", lambda: None)
    monkeypatch.setattr(pilot, "setup_runtime", lambda: (config, health, runner))
    monkeypatch.setattr(research, "status", lambda *a: {"status": "DRAFT"})
    monkeypatch.setattr(edit, "status", lambda *a: {"status": "done"})
    monkeypatch.setattr(paper, "status", lambda *a: {"status": "ACCEPTED"})
    monkeypatch.setattr(paper, "run", Mock(side_effect=AssertionError("Accepted paper was rerun")))
    return tmp_path


def test_resume_skips_accepted_papers_and_preserves_order(staged, monkeypatch):
    seen = []
    original_pending = runner.pending
    monkeypatch.setattr(runner, "run", lambda c: seen.append(c.root.name) or 0)
    pilot.run()
    assert seen == ["repeat", "reinjection"]
    assert runner.pending is original_pending
    assert pilot.read(staged / "progress.json")["status"] == "complete"
    assert set(pilot.read(staged / "outcomes.json")) == set(pilot.ARMS)


def test_research_failure_stops_before_next_arm(staged, monkeypatch):
    run = Mock(return_value=1)
    monkeypatch.setattr(runner, "run", run)
    with pytest.raises(RuntimeError, match="Research/edit failed"):
        pilot.run()
    assert run.call_count == 1
    assert pilot.read(staged / "progress.json")["status"] == "failed"


def test_budget_censoring_does_not_stop_other_arm(staged, monkeypatch):
    pilot.save(staged / "repeat/stop.json", {"reason": "budget: test cap"})
    seen = []
    monkeypatch.setattr(runner, "run", lambda c: seen.append(c.root.name) or 0)
    pilot.run()
    assert seen == ["reinjection"]
    assert pilot.read(staged / "progress.json")["status"] == "censored"


def test_operator_stop_is_not_cleared(staged, monkeypatch):
    pilot.save(staged / "stop.json", {"reason": "operator"})
    run = Mock()
    monkeypatch.setattr(runner, "run", run)
    with pytest.raises(RuntimeError, match="Pilot stop"):
        pilot.run()
    run.assert_not_called()
    assert (staged / "stop.json").exists()


def test_incomplete_editor_prevents_paper_and_next_arm(staged, monkeypatch):
    monkeypatch.setattr(runner, "run", lambda c: 0)
    monkeypatch.setattr(edit, "status", lambda *a: {"status": "failed"})
    with pytest.raises(RuntimeError, match="Incomplete research/edit"):
        pilot.run()
    paper.run.assert_not_called()


def test_paper_failure_propagates(staged, monkeypatch):
    monkeypatch.setattr(runner, "run", lambda c: 0)
    monkeypatch.setattr(paper, "status", lambda *a: {"status": "none"})
    monkeypatch.setattr(paper, "run", lambda *a, **kw: "blocked")
    with pytest.raises(RuntimeError, match="Paper incomplete"):
        pilot.run()
    assert pilot.read(staged / "progress.json")["status"] == "failed"

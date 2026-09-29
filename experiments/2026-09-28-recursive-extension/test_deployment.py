"""Model-free checks for the experiment-specific admission window."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from pathfinder import admission

SPEC = importlib.util.spec_from_file_location(
    "extension_policy_tests", Path(__file__).parent / "deploy/recursive_extension.py")
POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY)


def campaign(tmp_path):
    root = tmp_path / "repeat"
    root.mkdir()
    return SimpleNamespace(root=root, path=lambda name: root / name)


def test_no_launch_means_no_admission(tmp_path):
    c = campaign(tmp_path)
    assert POLICY.admit(c, "peer", "ada", 0).kind == "stop"


def test_expiry_stops_parent_and_does_not_consult_budget(tmp_path, monkeypatch):
    c = campaign(tmp_path)
    (tmp_path / "launch.json").write_text(json.dumps({"admission_deadline": 10}))
    monkeypatch.setattr(POLICY.time, "time", lambda: 11)
    monkeypatch.setattr(admission, "budget_per_call", lambda *args: (_ for _ in ()).throw(AssertionError()))
    assert POLICY.admit(c, "peer", "ada", 0).kind == "stop"
    assert "window" in json.loads((tmp_path / "stop.json").read_text())["reason"]


def test_live_window_preserves_budget_decision_and_reservations(tmp_path, monkeypatch):
    c = campaign(tmp_path)
    (tmp_path / "launch.json").write_text(json.dumps({"admission_deadline": 20}))
    monkeypatch.setattr(POLICY.time, "time", lambda: 11)
    seen = []
    def budget(campaign, stage, role, reserved):
        seen.append((campaign, stage, role, reserved))
        return admission.stop("budget: test")
    monkeypatch.setattr(admission, "budget_per_call", budget)
    assert POLICY.admit(c, "paper", "author", 2).reason == "budget: test"
    assert seen == [(c, "paper", "author", 2)]

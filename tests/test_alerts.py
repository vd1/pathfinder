import subprocess

from pathfinder import alerts, health
from test_runner import make


def test_failure_alert_is_durable_without_model_access(tmp_path, monkeypatch, capsys):
    def denied(*args):
        raise subprocess.TimeoutExpired("osascript", 5)
    monkeypatch.setattr(alerts, "_desktop", denied)
    c = make(tmp_path)
    alerts.emit(c, "supervision needs operator", c.path("supervision/session.json"))
    assert health.read(c.path("alert.json"))["desktop"] == "failed"
    assert c.path("alerts.jsonl").exists()
    assert "needs attention" in capsys.readouterr().err


def test_desktop_can_be_disabled(tmp_path, monkeypatch):
    c = make(tmp_path)
    c.raw["notifications"] = {"desktop": False}
    monkeypatch.setattr(alerts, "_desktop", lambda *args: (_ for _ in ()).throw(AssertionError()))
    alerts.emit(c, "runner failed", c.path("runner.json"))
    assert health.read(c.path("alert.json"))["desktop"] == "disabled"


def test_alert_storage_failure_does_not_mask_original_error(tmp_path, monkeypatch, capsys):
    def fail(*args):
        raise OSError("disk unavailable")
    monkeypatch.setattr(health, "write", fail)
    alerts.emit(make(tmp_path), "runner failed", "runner.json")
    assert "Cannot persist" in capsys.readouterr().err

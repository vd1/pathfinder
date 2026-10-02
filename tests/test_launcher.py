"""pathfinder launch: a long command started detached, confirmed alive, or reported with its log tail."""
import json, sys
from pathlib import Path
import pytest
from pathfinder import cli, launch


def test_a_command_that_exits_at_once_is_a_failure_with_its_log(tmp_path):
    with pytest.raises(RuntimeError, match="boom"):
        launch.launch([sys.executable, "-c", "print('boom'); raise SystemExit(3)"], tmp_path / "x.log", 1.0, tmp_path)


def test_a_running_command_is_confirmed(tmp_path):
    pid = launch.launch([sys.executable, "-c", "import time; time.sleep(5)"], tmp_path / "x.log", 0.5, tmp_path)
    assert launch.alive(pid)


def test_command_line_targets_the_campaign():
    assert launch.command(Path("/c"), ["research"])[-3:] == ["--root", "/c", "research"]


def test_cli_launch_reports_a_short_command_as_exited(tmp_path, capsys):
    from stubcampaign import make
    make(tmp_path)
    assert cli.main(["--root", str(tmp_path), "launch", "--settle", "1", "--", "health"]) == 1
    out = capsys.readouterr().out
    assert "exited" in out and (tmp_path / "logs").is_dir()


def test_the_child_writes_its_log_unbuffered():
    assert "-u" in launch.command(Path("/c"), ["research"])

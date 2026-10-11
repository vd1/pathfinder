"""The command line's own behaviour, apart from the stages it runs."""
import io, sys
from pathfinder import cli
from stubcampaign import make


def test_output_to_a_log_is_written_line_by_line(tmp_path, monkeypatch):
    """nobel, 12 October 2026: a detached runner's stdout went to its log block-buffered, so the log showed no
    'admitted' lines while the run was live."""
    make(tmp_path, pairs=("Q1P1",))
    out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")             # a file, as under detach or nohup
    monkeypatch.setattr(sys, "stdout", out)
    cli.main(["--root", str(tmp_path), "scan"])
    assert sys.stdout.line_buffering

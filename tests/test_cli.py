"""The command line's own behaviour, apart from the stages it runs."""
import io, sys
import pytest
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


@pytest.mark.parametrize("option", ["--amend", "--review"])
def test_paper_exception_handlers_use_module_transport(tmp_path, monkeypatch, capsys, option):
    make(tmp_path, pairs=("Q1P1",))
    def failed(*args):
        raise cli.transport.TransportFailed("retained provider failure")
    monkeypatch.setattr(cli.paper, "amend" if option == "--amend" else "review", failed)
    argv = ["--root", str(tmp_path), "paper", "Q1P1", option]
    if option == "--amend":
        argv.append("retained-findings.json")
    cli.main(argv)
    assert "transport failure" in capsys.readouterr().out


def test_paper_amend_preserves_admission_runtime_error(tmp_path, monkeypatch):
    make(tmp_path, pairs=("Q1P1",))
    original = RuntimeError("cannot open shared seat-pool lock")
    def failed(*args):
        raise original
    monkeypatch.setattr(cli.paper, "amend", failed)
    with pytest.raises(RuntimeError) as caught:
        cli.main(["--root", str(tmp_path), "paper", "Q1P1", "--amend", "retained-findings.json"])
    assert caught.value is original

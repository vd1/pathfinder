import json, os, subprocess, sys
from pathlib import Path
from pathfinder import research, ledger
from stubcampaign import make


def test_helper_is_copied_and_runs_without_importing_pathfinder(tmp_path):
    c = make(tmp_path)
    d = research.prepare(c, "Q1P1")
    script = d / ".pathfinder" / "ledger.py"
    assert script.read_bytes() == Path(ledger.__file__).read_bytes()
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH",)}
    run = lambda *a: subprocess.run([sys.executable, "-I", ".pathfinder/ledger.py", "--root", ".", *a],
                                    cwd=d, env=env, capture_output=True, text=True)
    assert run("--actor", "ada", "add", "--kind", "idea", "--text", "x").returncode == 0
    out = run("--actor", "ada", "read")
    assert out.returncode == 0 and "[ada/idea] x" in out.stdout


def test_peer_prompts_use_the_workspace_helper(tmp_path, monkeypatch):
    c = make(tmp_path)
    prompts = []
    real = research.transport.execute
    def capture(campaign, request):
        prompts.append(request.prompt)
        return real(campaign, request)
    monkeypatch.setattr(research.transport, "execute", capture)
    research.run_thread(c, "Q1P1")
    peer = [p for p in prompts if ".pathfinder/ledger.py" in p]
    assert peer and not any("-m pathfinder.ledger" in p for p in prompts)


def test_agent_environment_keeps_temporary_files_and_tex_caches_in_the_workspace(tmp_path):
    from pathfinder import transport
    c = make(tmp_path)
    env = transport._env(c, tmp_path / "threads" / "Q1P1")
    base = tmp_path / "threads" / "Q1P1" / ".pathfinder"
    assert env["TMPDIR"] == str(base / "tmp") and (base / "tmp").is_dir()
    assert env["TMPPREFIX"] == str(base / "tmp" / "zsh")
    assert env["TEXMFVAR"] == str(base / "texmf-var") and (base / "texmf-var").is_dir()
    assert "TEXINPUTS" in env

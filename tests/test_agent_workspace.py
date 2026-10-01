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


import pytest


def _composable(tmp_path, **raw):
    c = make(tmp_path, research_scheme="eva_minus", **raw)
    d = research.prepare(c, "Q1P1")
    (d / "ada").mkdir(exist_ok=True)
    (d / "ada" / "derivation.txt").write_text("the derivation " * 1000)
    return c, d


def test_review_material_lists_evidence_by_size_and_digest(tmp_path):
    import hashlib
    c, d = _composable(tmp_path)
    material = research._review_material(c, "Q1P1")
    data = (d / "ada" / "derivation.txt").read_bytes()
    assert hashlib.sha256(data).hexdigest() in material and "the derivation the derivation" not in material
    assert research.READING in material


def test_one_changed_byte_changes_the_material(tmp_path):
    c, d = _composable(tmp_path)
    before = research._review_material(c, "Q1P1")
    (d / "ada" / "derivation.txt").write_text("the derivatioN " * 1000)
    assert research._review_material(c, "Q1P1") != before


def test_aliased_evidence_still_blocks_by_reference(tmp_path):
    c, d = _composable(tmp_path)
    (tmp_path / "outside.txt").write_text("secret")
    os.symlink(tmp_path / "outside.txt", d / "ada" / "link.txt")
    with pytest.raises(research.EvidenceUnavailable):
        research._review_material(c, "Q1P1")


def test_inline_evidence_switch_restores_the_text(tmp_path):
    c, d = _composable(tmp_path, inline_evidence=True)
    assert "the derivation the derivation" in research._review_material(c, "Q1P1")


def test_papers_are_referenced_only_above_the_budget(tmp_path):
    c = make(tmp_path, inline_papers_max_chars=1000)
    d = research.prepare(c, "Q1P1"); inp = research._inputs(d)
    (d / "inputs" / inp["Q"]).write_text("q" * 400); (d / "inputs" / inp["P"]).write_text("p" * 599)
    assert "q" * 400 in research.thread_head(d, inp, inline_limit=research.papers_limit(c))
    (d / "inputs" / inp["P"]).write_text("p" * 601)
    head = research.thread_head(d, inp, inline_limit=research.papers_limit(c))
    assert "q" * 400 not in head and "sha256" in head and f"inputs/{inp['Q']}" in head


def test_verification_requests_are_read_only(tmp_path, monkeypatch):
    seen = []
    real = research.transport.execute
    def capture(campaign, request):
        seen.append((request.stage, request.reads))
        return real(campaign, request)
    monkeypatch.setattr(research.transport, "execute", capture)
    research.run_thread(make(tmp_path), "Q1P1")
    assert ("verify", True) in seen and all(reads is False for stage, reads in seen if stage != "verify")

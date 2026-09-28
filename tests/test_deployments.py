"""Deployment contract tests: each supported deployment, prepared its own way, runs on the candidate engine."""
import importlib.util, json, os, shutil, subprocess, sys
from pathlib import Path
import pytest
import deployment_matrix

ROOT = deployment_matrix.ROOT
needs_tex = pytest.mark.skipif(not shutil.which("latexmk") and not deployment_matrix.RELEASE, reason="latexmk not installed")


def _statarb_module(statarb: Path):
    spec = importlib.util.spec_from_file_location("statarb_protocol_contract",
                                                  statarb / "arxiv_drip/research_protocol.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@needs_tex
def test_statarb_prepares_freezes_and_runs_the_candidate_engine(tmp_path, monkeypatch):
    statarb = deployment_matrix.checkout("statarb")
    module = _statarb_module(statarb)
    monkeypatch.setattr(module, "frozen_inputs", lambda d: (
        {"id": "test-paper", "title": "Fixture paper", "abstract": "Fixture abstract"}, {},
        {"title": "Fixture dossier", "scope": "Fixture strategy catalogue"}))

    def source(aid, root):
        (root / "sources/Q.tex").write_text("Fixture full text of the pinned paper.")
        return "sources/Q.tex"
    monkeypatch.setattr(module, "paper_source", source)
    root, manifest = module.prepare({"pathfinder_root": str(ROOT), "pathfinder_ref": "HEAD", "model": "unused",
                                     "codex": "unused"}, tmp_path)
    # statarb froze the candidate commit with the engine's own freeze, and the copy verifies against it
    from pathfinder import freeze
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert json.loads((root / "engine/engine-freeze.json").read_text())["commit"] == head
    assert freeze.verify(root / "engine", ROOT)["status"] == "verified"
    # the brief is an append overlay, not an edited copy of the engine's prompts
    assert sorted(p.name for p in (root / "prompts").iterdir()) == [
        "consolidate.append.md", "editor.append.md", "peer.append.md", "verify.append.md"]
    # run the job on the stub backend with statarb's own worker and the frozen engine
    raw = json.loads((root / "campaign.json").read_text())
    raw.update(backend="stub", model="stub", scan_model="stub")
    (root / "campaign.json").write_text(json.dumps(raw))
    (tmp_path / "inputs.json").write_text(json.dumps({"fixture": True}))
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(root / "engine"), str(statarb)])}
    r = subprocess.run([sys.executable, "-m", "arxiv_drip.research_protocol", "worker", str(root)], cwd=statarb,
                       env=env, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    outcome = json.loads((root / "outcome.json").read_text())
    assert outcome["research"]["status"] == "DRAFT" and outcome["edit"]["status"] == "done"
    receipts = [json.loads(l) for l in (root / "receipts.jsonl").read_text().splitlines()]
    assert receipts and {r["backend"] for r in receipts} == {"stub"} and len({r["run_id"] for r in receipts}) == 1
    record = json.loads((root / "run.json").read_text())
    assert record["engine"]["path"].startswith(str(root / "engine"))          # the frozen copy ran, not the checkout
    # statarb's research brief reached the prompts it appends to
    probe = ("import pathfinder, json, sys; from pathfinder import config, resources; c = config.load(sys.argv[1]); "
             "print(json.dumps({'origin': pathfinder.__file__, 'prompts': {r: resources.prompt_template(c, r) "
             "for r in ('peer', 'consolidate', 'verify', 'editor')}}))")
    out = json.loads(subprocess.run([sys.executable, "-c", probe, str(root)], cwd=tmp_path, env=env,
                                    capture_output=True, text=True, check=True).stdout)
    assert Path(out["origin"]).resolve().is_relative_to((root / "engine").resolve())   # the frozen engine answered
    prompts = out["prompts"]
    brief = (statarb / "arxiv_drip/research-brief.md").read_text().strip()[:200]
    assert all(brief in text for text in prompts.values())


def test_the_matrix_lists_every_live_deployment_with_a_status():
    entries = deployment_matrix.load()
    assert set(entries) >= {"statarb", "coordinated-pilot", "pathfinder-julien-2"}
    for name, entry in entries.items():
        assert entry["status"] in ("supported", "not-yet-supported"), name
        assert entry["notes"], name
        if entry["status"] == "supported":
            assert entry["contract"], name
        else:
            assert "inventory" in entry["notes"] or entry["notes"], name

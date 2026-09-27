"""The real engine stages, end to end, on the model-free stub backend."""
import json, shutil, subprocess, sys
from pathlib import Path
import pytest
from pathfinder import edit, paper, research, runner, transport
from stubcampaign import make

needs_tex = pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
ROOT = Path(__file__).resolve().parent.parent


@needs_tex
def test_stub_campaign_runs_research_edit_and_paper(tmp_path):
    c = make(tmp_path)
    assert runner.run(c, interval=0.05) == 0
    assert research.status(c, "Q1P1")["status"] == "DRAFT"
    assert edit.status(c, "Q1P1")["status"] == "done" and (tmp_path / "threads/Q1P1/edited/note.pdf").exists()
    assert paper.run(c, "Q1P1") == "ACCEPTED" and (tmp_path / "threads/Q1P1/paper/paper.pdf").exists()
    rows = transport.receipts(c)
    assert {r["stage"] for r in rows} >= {"peer", "consolidate", "verify", "edit", "author", "review"}
    assert all(r["backend"] == "stub" and r["cost"] == 0 for r in rows)


@needs_tex
def test_stub_pause_verdict_skips_the_paper(tmp_path):
    c = make(tmp_path, stub={"verify": "PAUSE"})
    assert runner.run(c, interval=0.05) == 0
    assert research.status(c, "Q1P1")["status"] == "PAUSE" and edit.status(c, "Q1P1")["status"] == "done"


SMOKE = r'''
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
from pathfinder import config, edit, research, resources, runner
raw = {"backend": "stub", "model": "stub", "peers": ["ada"], "seats": 1, "rounds": 1, "repairs": 0,
       "budget_usd": 100, "call_estimate_usd": 1,
       "allowances": {"peer_seconds": 600, "peer_calls": 2, "consolidate_seconds": 60, "verify_seconds": 60,
                      "edit_seconds": 60}}
root.mkdir(parents=True)
(root / "campaign.json").write_text(json.dumps(raw))
for side in "QP":
    (root / f"{side}.jsonl").write_text(json.dumps({"id": side.lower() + "1", "title": side + " one", "abstract": "A."}) + "\n")
(root / "shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": "Q1P1"}]}))
(root / "prompts").mkdir()
(root / "prompts" / "peer.append.md").write_text("DEPLOYMENT-BRIEF for {{ACTOR}}")
c = config.load(root)
peer = research._prompt(c, "peer", ACTOR="ada")
verify = resources.prompt_template(c, "verify")
code = runner.run(c, interval=0.05)
print(json.dumps({"code": code, "research": research.status(c, "Q1P1")["status"],
                  "edit": edit.status(c, "Q1P1")["status"], "overlay": "DEPLOYMENT-BRIEF for ada" in peer,
                  "engine_verify": verify == (resources.engine_prompts() / "verify.md").read_text(),
                  "prompts": str(resources.engine_prompts())}))
'''


@needs_tex
@pytest.mark.skipif(not shutil.which("uv"), reason="uv not installed")
def test_installed_wheel_runs_research_and_edit_outside_the_checkout(tmp_path):
    dist = tmp_path / "dist"
    r = subprocess.run(["uv", "build", "--wheel", "--out-dir", str(dist)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    venv = tmp_path / "venv"
    subprocess.run(["uv", "venv", "--quiet", str(venv)], check=True, capture_output=True)
    py = venv / "bin" / "python"
    subprocess.run(["uv", "pip", "install", "--quiet", "--python", str(py), str(next(dist.glob("*.whl")))],
                   check=True, capture_output=True)
    work = tmp_path / "outside"; work.mkdir()
    out = subprocess.run([str(py), "-c", SMOKE, str(work / "campaign")], cwd=work, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-3000:]
    info = json.loads(out.stdout.strip().splitlines()[-1])
    assert info == {**info, "code": 0, "research": "DRAFT", "edit": "done", "overlay": True, "engine_verify": True}
    assert "site-packages" in info["prompts"]

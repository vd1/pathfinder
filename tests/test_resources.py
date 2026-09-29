import json, os, shutil, subprocess, sys
from pathlib import Path
import pytest
from pathfinder import paper, resources, research, scan
from pathfinder.config import Campaign

ROOT = Path(__file__).resolve().parent.parent


def _campaign(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / "campaign.json").write_text("{}")
    return Campaign(root=root, backend="claude", model="m", scan_model="m", peer_search=True, seats=1, cut=1,
                    rounds=1, allowances={}, budget_usd=1, prices={}, scan_fulltext=None)


def test_append_overlay_for_one_role_leaves_the_others_on_the_engine_prompts(tmp_path):
    c = _campaign(tmp_path)
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "peer.append.md").write_text("Deployment brief for {{ACTOR}}.\n")
    engine_peer = (resources.engine_prompts() / "peer.md").read_text()
    composed = resources.prompt_template(c, "peer")
    assert composed.startswith(engine_peer.rstrip("\n")) and composed.endswith("Deployment brief for {{ACTOR}}.\n")
    assert resources.prompt_template(c, "verify") == (resources.engine_prompts() / "verify.md").read_text()
    assert "Deployment brief for ada." in research._prompt(c, "peer", ACTOR="ada")


def test_replacement_then_append_then_substitution(tmp_path):
    c = _campaign(tmp_path)
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "verify.md").write_text("Replaced {{NOTE}}")
    (tmp_path / "prompts" / "verify.append.md").write_text("Also {{NOTE}}")
    assert resources.prompt(c, "verify", NOTE="n.tex") == "Replaced n.tex\n\nAlso n.tex"


def test_scan_prompt_resolves_per_file(tmp_path):
    c = _campaign(tmp_path)
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "scan.append.md").write_text("Extra rubric.")
    text = scan.render(c, {"title": "A", "abstract": "a"}, {"title": "B", "abstract": "b"})
    assert "Extra rubric." in text and "{{Q_TITLE}}" not in text


def test_prompt_digests_follow_overlays(tmp_path):
    c = _campaign(tmp_path)
    before = resources.prompt_digests(c)
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "peer.append.md").write_text("x")
    after = resources.prompt_digests(c)
    assert before["peer"] != after["peer"] and before["verify"] == after["verify"]


def test_campaign_styles_come_first_for_builds_and_agents(tmp_path):
    c = _campaign(tmp_path)
    (tmp_path / "styles").mkdir()
    thread = tmp_path / "threads" / "Q1P1" / "paper"; thread.mkdir(parents=True)
    env = paper.tex_env(thread)["TEXINPUTS"].split(os.pathsep)
    assert env[0] == str(tmp_path / "styles") and env[1] == str(resources.engine_styles())
    assert resources.texinputs(c, "").split(os.pathsep)[0] == str(tmp_path / "styles")
    (tmp_path / "styles" / "pathfinder-common.sty").write_text("% override\n")
    assert resources.style_digests(where=thread)["pathfinder-common.sty"] != \
        resources.style_digests()["pathfinder-common.sty"]


@pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
def test_campaign_style_overlay_reaches_a_build(tmp_path):
    _campaign(tmp_path)
    styles = tmp_path / "styles"; styles.mkdir()
    common = (resources.engine_styles() / "pathfinder-common.sty").read_text()
    (styles / "pathfinder-common.sty").write_text(common + "\n\\newcommand{\\overlaymarker}{OVERLAYMARKER}\n")
    d = tmp_path / "threads" / "Q1P1"; d.mkdir(parents=True)
    (d / "Q1P1.tex").write_text("\\documentclass{article}\\usepackage{pathfinder-note}\\title{T}\\begin{document}\\maketitle \\overlaymarker\\end{document}\n")
    ok, log = paper.build(d, "Q1P1.tex")
    assert ok, log
    txt = subprocess.run(["pdftotext", str(d / "Q1P1.pdf"), "-"], capture_output=True, text=True).stdout
    assert "OVERLAYMARKER" in txt


@pytest.mark.skipif(not shutil.which("uv"), reason="uv not installed")
def test_installed_wheel_carries_prompts_and_styles(tmp_path):
    """Build the wheel, install it outside the checkout, and read prompts and styles from the installed package."""
    dist = tmp_path / "dist"
    r = subprocess.run(["uv", "build", "--wheel", "--out-dir", str(dist)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    wheel = next(dist.glob("*.whl"))
    venv = tmp_path / "venv"
    subprocess.run(["uv", "venv", "--quiet", str(venv)], check=True, capture_output=True)
    py = venv / "bin" / "python"
    subprocess.run(["uv", "pip", "install", "--quiet", "--python", str(py), str(wheel)], check=True, capture_output=True)
    probe = ("from pathfinder import resources; p = resources.engine_prompts(); "
             "import json; print(json.dumps({'prompts': str(p), 'peer': (p / 'peer.md').is_file(), "
             "'styles': (resources.engine_styles() / 'pathfinder-common.sty').is_file()}))")
    out = subprocess.run([str(py), "-c", probe], cwd=tmp_path, capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    assert info["peer"] and info["styles"] and "site-packages" in info["prompts"]

"""Run one owner-authorised research continuation in an isolated campaign."""
import datetime
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / "engine"
sys.path.insert(0, str(ENGINE))
os.environ["PYTHONPATH"] = str(ENGINE)
os.environ["PATHFINDER_CLAUDE"] = shlex.join([sys.executable, str(ROOT / "claude_capture.py")])
from pathfinder import config, research
from pathfinder.ledger import Ledger

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")

if (ROOT / "manifest.json").exists():
    raise SystemExit("Already initialised; refusing a duplicate continuation.")
thread = ROOT / "threads/Q3P3"
state = json.loads((thread / "status.json").read_text())
if state["status"] != "PAUSE-ON-ITERATE":
    raise SystemExit("Expected PAUSE-ON-ITERATE.")
cfg = json.loads((ROOT / "campaign.json").read_text())
cfg["rounds"] = state["round"] + 1
save(ROOT / "campaign.json", cfg)
save(ROOT / "manifest.json", {
    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "pair": "Q3P3", "model": cfg["model"], "backend": cfg["backend"],
    "previous_round": state["round"], "last_authorised_round": cfg["rounds"],
    "scope": "One additional research iteration, consolidation and verification; no automatic paper or readable-note production.",
    "original": "../../threads/Q3P3", "pid": os.getpid(),
    "preservation": "Original campaign and thread are untouched; inputs, ledger, outputs, engine and prompts copied here."})
state.update(round=cfg["rounds"], stage="peers", status="running", repair=None,
    reason="Owner authorised one additional research iteration in a separate copy.")
save(thread / "status.json", state)
Ledger(thread / "ledger.jsonl").add("owner", "intention",
    "One additional research iteration is authorised. Address the latest verifier request for a matched P ablation. "
    "Recheck whether the original tasks, implementation and necessary access are now publicly obtainable. "
    "Preserve the supported Q result. If an exact reproduction is unavailable, distinguish any feasible new "
    "controlled experiment from a reproduction or explanation of P's reported outcomes. Do not invent data "
    "or claim the causal gap is resolved without evidence. Do not purchase resources or launch further "
    "paid model campaigns. Record the remaining obstacle explicitly if it cannot be resolved within this round. "
    "Only modify this continuation directory; do not modify the original campaign or other experiments.")
campaign = config.load(ROOT)
try:
    outcome = research.run_thread(campaign, "Q3P3", stop=lambda: (ROOT / "STOP").exists())
    print(json.dumps({"outcome": outcome, "state": research.status(campaign, "Q3P3")}), flush=True)
finally:
    save(ROOT / "outcome.json", research.status(campaign, "Q3P3"))
    changed_artifacts = [str(thread / "Q3P3.tex"), str(thread / "ada/notes.md"), str(thread / "emmy/notes.md")]
    with (ROOT / "artifact-gates.log").open("w") as output:
        ban = subprocess.run(["/Users/v/.local/bin/style-ban-artifacts", *changed_artifacts], stdout=output, stderr=subprocess.STDOUT)
        gate = subprocess.run([sys.executable, "/Users/v/.codex/skills/style-gates/scripts/style_gate.py", *changed_artifacts], stdout=output, stderr=subprocess.STDOUT)
        build = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "Q3P3.tex"], cwd=thread, stdout=output, stderr=subprocess.STDOUT)
        pdf = subprocess.run([sys.executable, "/Users/v/.codex/skills/style-gates/scripts/style_gate.py", str(thread / "Q3P3.pdf")], stdout=output, stderr=subprocess.STDOUT)
    save(ROOT / "artifact-gates.json", {"style_ban": ban.returncode, "style_gate": gate.returncode,
        "build": build.returncode, "pdf_gate": pdf.returncode})

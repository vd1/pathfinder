"""Prepare and supervise one fresh pass over the original shortlist."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def save(name, value):
    target = ROOT / name
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(target)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    if (ROOT / "manifest.json").exists():
        raise SystemExit("Already prepared; use status records, do not overwrite this run.")
    selection = json.loads((REPO / "shortlist.json").read_text())
    assert len(selection["pairs"]) == 14
    paths = [REPO / name for name in ("Q.jsonl", "P.jsonl", "scan.jsonl", "shortlist.json")]
    for side in ("Q", "P"):
        rows = [json.loads(line) for line in (REPO / f"{side}.jsonl").read_text().splitlines() if line.strip()]
        assert len(rows) == 10
        for row in rows:
            source = REPO / row["text"]
            assert source.is_file(), source
            target = ROOT / row["text"]
            assert target.resolve().is_relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            paths.append(source)
    for source in paths[:4]:
        shutil.copy2(source, ROOT / source.name)
    shutil.copytree(REPO / "pathfinder", ROOT / "engine" / "pathfinder", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(REPO / "prompts", ROOT / "prompts")
    paths += list((REPO / "pathfinder").glob("*.py")) + list((REPO / "prompts").glob("*.md"))
    original = {str(p.relative_to(REPO)): digest(p) for p in paths}
    for pair in selection["pairs"]:
        for p in (REPO / "threads" / pair["pair_id"]).rglob("*"):
            if p.is_file():
                original[str(p.relative_to(REPO))] = digest(p)
    save("original-hashes.json", original)
    save("manifest.json", {
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "model": "gpt-6-sol", "reasoning_effort": "high", "backend": "codex",
        "replicate": 1, "pairs": [p["pair_id"] for p in selection["pairs"]],
        "scope": "Fresh research, readable accounts, and paper author/reviewer stage for DRAFT outcomes. No reinjection.",
        "inputs": {name: digest(ROOT / name) for name in ("Q.jsonl", "P.jsonl", "scan.jsonl", "shortlist.json")},
        "prompts": {p.name: digest(p) for p in (ROOT / "prompts").glob("*.md")},
        "configuration": json.loads((ROOT / "campaign.json").read_text()),
        "blinding": "Fresh thread directories, unchanged source prompts, disabled inherited project documents, and explicit restriction against reading prior campaign outputs. This is instruction-based isolation, not an OS read barrier. Web access may expose prior public findings.",
        "cost_basis": "Official GPT-6-sol standard token prices checked 2026-09-23; API-equivalent accounting, not subscription charges.",
        "pricing_source": "https://developers.openai.com/api/docs/models/gpt-6-sol",
    })
    print(json.dumps({"prepared": str(ROOT), "pairs": len(selection["pairs"])}), flush=True)


def run():
    # Avoid macOS SystemConfiguration fork handlers after bibliography HTTP checks.
    # https://docs.python.org/3/library/urllib.request.html
    os.environ["no_proxy"] = "*"
    engine = str(ROOT / "engine")
    sys.path.insert(0, engine)
    os.environ["PYTHONPATH"] = engine
    os.environ["PYTHONUNBUFFERED"] = "1"
    for key in list(os.environ):
        if key.startswith("HERDR_") or key in ("CODEX_THREAD_ID", "CODEX_SESSION_ID"):
            os.environ.pop(key)
    instructions = (
        "You are executing one assigned role in a fixed two-peer scientific experiment. "
        "Use only this thread's supplied source papers, scan seed, ledger, and working files, "
        "plus external literature when your role permits search. Keep filesystem research reads "
        "inside the assigned thread. Installed tools and the provided pathfinder ledger helper "
        "may be executed. Do not inspect parent directories, other threads, earlier campaign "
        "outputs, CAPTAIN.md, or the Pathfinder repository online. Do not spawn additional agents. "
        "If prior campaign results appear in external search, record that exposure explicitly. "
        "Carry out the assigned role using its provided protocol and time allowance."
    )
    os.environ["PATHFINDER_CODEX"] = shlex.join([
        sys.executable, str(ROOT / "codex_adapter.py"), "-c", 'model_reasoning_effort="high"',
        "-c", "project_doc_max_bytes=0", "-c", "developer_instructions=" + json.dumps(instructions),
    ])
    from pathfinder import config, edit, paper, research, runner
    campaign = config.load(ROOT)
    pairs = json.loads((ROOT / "shortlist.json").read_text())["pairs"]
    save("process.json", {"pid": os.getpid(), "status": "running", "stage": "research"})
    failed = None
    try:
        for pair in pairs:
            pid = pair["pair_id"]
            if runner.stopped(campaign):
                break
            if research.status(campaign, pid)["status"] in research.TERMINAL and edit.status(campaign, pid).get("status") != "done":
                print(f"recover readable account: {pid}", flush=True)
                edit.run(campaign, pid, stop=lambda: runner.stopped(campaign))
        runner.run(campaign)
        save("process.json", {"pid": os.getpid(), "status": "running", "stage": "papers"})
        for pair in pairs:
            pid = pair["pair_id"]
            if runner.stopped(campaign) or not runner.guard_ok(campaign, inflight=1):
                break
            if research.status(campaign, pid)["status"] == "DRAFT":
                print(f"paper stage: {pid}", flush=True)
                paper.run(campaign, pid, stop=lambda: runner.stopped(campaign))
    except BaseException as exc:
        failed = repr(exc)
        raise
    finally:
        outcomes = {p["pair_id"]: {"research": research.status(campaign, p["pair_id"]),
                    "editor": edit.status(campaign, p["pair_id"]),
                    "paper": paper.status(campaign, p["pair_id"])} for p in pairs}
        save("outcomes.json", outcomes)
        original = json.loads((ROOT / "original-hashes.json").read_text())
        changed = [name for name, value in original.items() if not (REPO / name).is_file() or digest(REPO / name) != value]
        save("originals-verification.json", {"unchanged": not changed, "changed_paths": changed})
        incomplete = [pid for pid, result in outcomes.items() if result["research"]["status"] not in research.TERMINAL
                      or result["editor"].get("status") != "done"
                      or (result["research"]["status"] == "DRAFT" and result["paper"].get("status") not in ("ACCEPTED", "PAUSE-ON-AMEND"))]
        save("process.json", {"pid": os.getpid(), "status": "incomplete" if failed or incomplete else "complete",
                              "error": failed, "incomplete_pairs": incomplete})
        print(json.dumps({"finished": True, "error": failed, "incomplete_pairs": incomplete}), flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
    elif sys.argv[1:] == ["run"]:
        run()
    elif sys.argv[1:] in (["launch"], ["resume"]):
        resuming = sys.argv[1:] == ["resume"]
        if resuming:
            previous = json.loads((ROOT / "process.json").read_text())
            if previous["status"] != "incomplete":
                raise SystemExit("Only an incomplete, exited run may resume.")
            try:
                os.kill(previous["pid"], 0)
            except ProcessLookupError:
                pass
            else:
                raise SystemExit("Previous process is still alive.")
        elif (ROOT / "process.json").exists():
            raise SystemExit("A process record already exists; inspect it before any further launch.")
        with (ROOT / "run.log").open("a" if resuming else "x") as log:
            proc = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()), "run"],
                                    cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
        print(json.dumps({"launched_pid": proc.pid, "log": str(ROOT / "run.log")}), flush=True)
    else:
        raise SystemExit("Use prepare, launch, resume, or run.")

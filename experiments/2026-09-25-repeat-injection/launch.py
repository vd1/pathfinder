"""Frozen, interleaved repeat/reinjection pilot. No production engine edits."""
import argparse
from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OLD = REPO / "experiments/2026-09-23-gpt-6-sol-rerun-01"
PLAN = REPO / "plans/2026-09-25-1623-repeat-versus-reinjection.md"
ARMS = ("repeat", "reinjection")
SEEDS = [(REPO, "Q4P6"), (REPO, "Q1P2"), (OLD, "Q3P10"),
         (OLD, "Q7P1"), (OLD, "Q8P8")]


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(value, indent=2) + "\n")
    tmp.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def jsonlines(path, values):
    path.write_text("".join(json.dumps(x) + "\n" for x in values))


def prepare():
    if any((ROOT / a).exists() for a in ARMS) or (ROOT / "manifest.json").exists():
        raise RuntimeError("Already staged or partially staged; inspect instead of overwriting")
    allocation = re.findall(r"\| (\d{2}) \| (Q\d+)P(\d+) \| (Q\d+) (S\d) \|", PLAN.read_text())
    assert len(allocation) == 14
    assert Counter(r[1] for r in allocation) == Counter(r[3] for r in allocation)
    assert len({(r[3], r[4]) for r in allocation}) == 14
    parents = dict(zip([f"S{i}" for i in range(1, 6)], ["Q4", "Q1", "Q3", "Q7", "Q8"]))
    assert all(r[3] != parents[r[4]] for r in allocation)
    qrows, prows = rows(OLD / "Q.jsonl"), rows(OLD / "P.jsonl")
    old_manifest = read(OLD / "manifest.json")
    for name in ("Q.jsonl", "P.jsonl"):
        assert digest(OLD / name) == old_manifest["inputs"][name]
    seed_rows, ancestry = [], {}
    for n, (origin, pair) in enumerate(SEEDS, 1):
        source = origin / "threads" / pair / "paper"
        assert read(source / "paper.json")["status"].upper() == "ACCEPTED"
        assert read(source / "paper.json")["build_ok"]
        assert digest(source / "paper.tex") in PLAN.read_text()
        dest = ROOT / "seed-archive" / f"S{n}"
        dest.mkdir(parents=True)
        names = ["paper.tex", "paper.pdf", "references.bib", "paper.bbl", "paper.json", "review.json"]
        for name in names:
            shutil.copy2(source / name, dest / name)
        text = (source / "paper.tex").read_text()
        title = re.search(r"\\title\{([^}]+)\}", text).group(1).replace("\\\\", " ")
        abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.S).group(1)
        # Inline compiled references, preserving all scientific prose and mathematics.
        text = re.sub(r"\\bibliographystyle\{[^}]+\}", "", text)
        text = re.sub(r"\\bibliography\{[^}]+\}", lambda _: (source / "paper.bbl").read_text(), text)
        assert not re.search(r"\\(?:input|include)\s*\{", text)
        assert "\\begin{thebibliography}" in text and "\\end{document}" in text
        rendered = dest / "fulltext.tex"
        rendered.write_text(text)
        seed_rows.append({"id": f"pathfinder-local-S{n}", "title": title,
                          "abstract": abstract, "authors": ["Pathfinder research campaign"],
                          "date": "2026-09-25", "text": f"sources/S{n}.tex",
                          "source_kind": "local manuscript", "arxiv_id": None})
        ancestry[f"S{n}"] = {"source": str(source.relative_to(REPO)), "parent_pair": pair,
                              "hashes": {name: digest(dest / name) for name in names + ["fulltext.tex"]}}
    shutil.copytree(REPO / "pathfinder", ROOT / "engine/pathfinder",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(REPO / "prompts", ROOT / "engine/prompts")
    peer = ROOT / "engine/prompts/peer.md"
    prompt = peer.read_text()
    start = prompt.index("{{MATERIAL}} The scan")
    end = prompt.index("Then look for an advance", start)
    prompt = prompt[:start] + "{{MATERIAL}} This pair was assigned in advance without a scan hypothesis. " + prompt[end:]
    peer.write_text(prompt)
    settings = json.loads(json.dumps(old_manifest["configuration"]))
    settings["pair_kind"] = "paper-strategy"  # Existing metadata switch: no fabricated arXiv links.
    settings["codex"] = {"reasoning_effort": "high", "disable_toolless_shell": True}
    settings["budget_usd"] = 200
    # Coordinator is not a third research arm.
    save(ROOT / "campaign.json", settings)
    save(ROOT / "shortlist.json", {"pairs": []})
    schedule = []
    for block, qi, pi, qj, seed in allocation:
        task = {"repeat": f"{qi}P{pi}", "reinjection": f"{qj}P{seed[1:]}"}
        order = ARMS if int(block) % 2 else ARMS[::-1]
        schedule.extend({"block": int(block), "arm": a, "pair": task[a]} for a in order)
    for arm in ARMS:
        dest = ROOT / arm
        dest.mkdir()
        save(dest / "campaign.json", settings)
        shutil.copytree(ROOT / "engine/prompts", dest / "prompts")
        (dest / "sources").mkdir()
        shutil.copy2(OLD / "Q.jsonl", dest / "Q.jsonl")
        if arm == "repeat":
            shutil.copy2(OLD / "P.jsonl", dest / "P.jsonl")
        else:
            jsonlines(dest / "P.jsonl", seed_rows)
        for row in qrows + (prows if arm == "repeat" else []):
            target = dest / row["text"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(OLD / row["text"], target)
        if arm == "reinjection":
            for n in range(1, 6):
                shutil.copy2(ROOT / f"seed-archive/S{n}/fulltext.tex", dest / f"sources/S{n}.tex")
        prs = prows if arm == "repeat" else seed_rows
        pairs = []
        for task in schedule:
            if task["arm"] != arm:
                continue
            i, j = (int(x) for x in task["pair"][1:].split("P"))
            pairs.append({"pair_id": task["pair"], "q": qrows[i-1]["id"], "p": prs[j-1]["id"],
                          "score": None, "feasibility": None, "gain": None})
        save(dest / "shortlist.json", {"pairs": pairs, "n_selected": 14, "selection": "prespecified"})
    frozen = [p for p in ROOT.rglob("*") if p.is_file() and p.name != "manifest.json"
              and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts]
    manifest = {"created_at": time.time(), "base_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "plan_sha256": digest(PLAN), "schedule": schedule, "ancestry": ancestry,
        "configuration": settings, "budget_basis": "API-equivalent workload, ChatGPT login, not API billing",
        "pricing_checked": "2026-09-25", "pricing_source": "https://developers.openai.com/api/docs/models/gpt-6-sol",
        "pricing_limitations": "Standard short-context equivalent; CLI aggregates requests and does not expose cache writes. Not an invoice.",
        "blinding": "Instruction-based read isolation; workspace-write sandbox is not a read barrier. External search can leak prior findings.",
        "adaptations": ["Neutral no-scan peer prompt in BOTH arms", "No automatic arXiv title links in BOTH arms",
                        "No shell tools on nominally tool-less calls in BOTH arms", "Serial pair admission in alternating blocks; seats remains 2",
                        "Per-call admission budget check in BOTH arms", "Compiled seed bibliographies inlined; archival originals unchanged"],
        "frozen_hashes": {str(p.relative_to(ROOT)): digest(p) for p in frozen}}
    save(ROOT / "manifest.json", manifest)
    preflight()


def environment():
    os.environ["no_proxy"] = "*"
    os.environ["PYTHONPATH"] = str(ROOT / "engine")
    os.environ["PYTHONUNBUFFERED"] = "1"
    for key in list(os.environ):
        if key.startswith("HERDR_") or key in ("CODEX_THREAD_ID", "CODEX_SESSION_ID"):
            os.environ.pop(key)
    sys.path.insert(0, str(ROOT / "engine"))
    instruction = (
        "Execute only the assigned scientific role. Read only the assigned thread's supplied papers, "
        "ledger and working files, plus external literature when permitted. Do not read parent directories, "
        "other threads, previous campaign outputs, plans, reviews of input manuscripts, or the Pathfinder "
        "repository online. Do not spawn additional agents. Record any external exposure to prior campaign "
        "results. Installed tools and the provided ledger helper may be executed. A source labelled local "
        "manuscript is not an arXiv deposit: cite its title and local identifier without inventing a URL. "
        "Q/P labels inside a supplied manuscript refer to that manuscript's own sources, not necessarily "
        "the present pair. Preserve conditional assumptions and distinguish proposed experiments from results."
    )
    os.environ["PATHFINDER_CODEX"] = shlex.join([
        sys.executable, str(ROOT / "codex_adapter.py"), "-c", "project_doc_max_bytes=0",
        "-c", "developer_instructions=" + json.dumps(instruction)])


def preflight():
    manifest = read(ROOT / "manifest.json")
    for name, expected in manifest["frozen_hashes"].items():
        assert digest(ROOT / name) == expected, name
    for arm in ARMS:
        for row in rows(ROOT / arm / "Q.jsonl") + rows(ROOT / arm / "P.jsonl"):
            assert (ROOT / arm / row["text"]).stat().st_size > 1000
    print("Preflight passed: frozen files, corpora, complete source texts, 28 scheduled pairs", flush=True)


def setup_runtime():
    environment()
    from pathfinder import config, health, runner, transport
    original_snapshot = health.snapshot
    def snapshot(campaign):
        out = original_snapshot(campaign)
        if campaign.root == ROOT:
            children = {a: original_snapshot(config.load(ROOT / a)) for a in ARMS}
            out["arms"] = children
            out["active_calls"] = [dict(c, arm=a) for a, s in children.items() for c in s["active_calls"]]
            out["work"] = [dict(w, arm=a) for a, s in children.items() for w in s["work"]]
            out["warnings"] += [f"{a}: {w}" for a, s in children.items() for w in s["warnings"]]
        return out
    health.snapshot = snapshot
    original_call = transport.call
    reserved, mutex = Counter(), threading.Lock()
    def call(*args, **kwargs):
        campaign = kwargs["campaign"]
        key = str(campaign.root)
        with mutex:
            if runner.stopped(config.load(ROOT)) or runner.stopped(campaign):
                raise RuntimeError("Explicit pilot/arm stop; no call admitted")
            if not runner.guard_ok(campaign, reserved[key] + 1):
                raise RuntimeError("API-equivalent admission cap reached")
            reserved[key] += 1
        try:
            return original_call(*args, **kwargs)
        finally:
            with mutex:
                reserved[key] -= 1
    transport.call = call
    return config, health, runner


def run():
    preflight()
    config, health, runner = setup_runtime()
    from pathfinder import edit, paper, research
    parent = config.load(ROOT)
    campaigns = {a: config.load(ROOT / a) for a in ARMS}
    state = {"pid": os.getpid(), "run_id": uuid.uuid4().hex, "status": "running",
             "started_at": time.time(), "heartbeat_at": time.time(), "last_progress": None}
    stop_event = threading.Event()
    def heartbeat():
        while not stop_event.is_set():
            health.write(ROOT / "runner.json", dict(state, heartbeat_at=time.time()))
            stop_event.wait(5)
    with health.owner(parent):
        for c in campaigns.values():
            if any(x["pid_alive"] or x["child_alive"] for x in health.snapshot(c)["active_calls"]):
                raise RuntimeError("Live child calls require diagnosis before resumption")
        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        try:
            for task in read(ROOT / "manifest.json")["schedule"]:
                c, pid = campaigns[task["arm"]], task["pair"]
                if runner.stopped(parent):
                    raise RuntimeError("Pilot stop marker exists")
                if runner.stopped(c):
                    if "budget:" in str(read(c.path("stop.json")).get("reason")):
                        continue
                    raise RuntimeError(f"Operator stop in {task['arm']}")
                state.update(task=task)
                print(json.dumps({"starting": task}), flush=True)
                pending = runner.pending
                # Keep immutable full shortlists; limit only this invocation's admissions.
                runner.pending = lambda campaign: [p for p in pending(campaign) if p == pid]
                try:
                    result = runner.run(c)
                finally:
                    runner.pending = pending
                if result or runner.stopped(c):
                    if runner.stopped(c) and "budget:" in str(read(c.path("stop.json")).get("reason")):
                        continue
                    raise RuntimeError(f"Research/edit failed: {task}")
                if research.status(c, pid)["status"] not in research.TERMINAL or edit.status(c, pid).get("status") != "done":
                    raise RuntimeError(f"Incomplete research/edit: {task}")
                if research.status(c, pid)["status"] == "DRAFT" and paper.status(c, pid)["status"] not in {"ACCEPTED", "PAUSE-ON-AMEND"}:
                    state.update(stage="paper")
                    with health.owner(c), runner.Lock(c.thread_dir(pid)):
                        result = paper.run(c, pid, stop=lambda: runner.stopped(c) or runner.stopped(parent))
                    if result not in {"ACCEPTED", "PAUSE-ON-AMEND"}:
                        raise RuntimeError(f"Paper incomplete: {task}: {result}")
                state.update(last_progress=dict(task, at=time.time()), stage="between-pairs")
                save(ROOT / "progress.json", state)
            censored = [a for a, c in campaigns.items() if runner.stopped(c)]
            state.update(status="censored" if censored else "complete", censored_arms=censored)
        except BaseException as exc:
            state.update(status="failed", error=repr(exc))
            raise
        finally:
            stop_event.set()
            thread.join()
            state.update(heartbeat_at=time.time(), finished_at=time.time())
            save(ROOT / "runner.json", state)
            save(ROOT / "progress.json", state)
            save(ROOT / "outcomes.json", {a: {p["pair_id"]: {
                "research": research.status(c, p["pair_id"]), "editor": edit.status(c, p["pair_id"]),
                "paper": paper.status(c, p["pair_id"])} for p in read(c.path("shortlist.json"))["pairs"]}
                for a, c in campaigns.items()})


def supervise():
    preflight()
    config, health, runner = setup_runtime()
    from pathfinder import supervise as supervisor
    command = [sys.executable, str(ROOT / "launch.py"), "run"]
    scope = (
        "Complete all 28 scheduled research/edit threads and DRAFT author/reviewer pipelines in BOTH "
        "repeat and reinjection child campaigns. Read manifest.json, progress.json and outcomes.json. "
        "The root shortlist is intentionally empty: NEVER infer completion from it. The supplied snapshot "
        "aggregates child calls/work under arms. For current aggregate status use the supplied Python "
        f"executable {ROOT / 'launch.py'} status. A healthy root heartbeat alone is not scientific progress. "
        "Treat final censored or failed states as needs_operator, not complete. No new generation, "
        "budget increase, protocol change or source/code modification is authorized. Diagnose child "
        "failure records too. Resume only through the supplied full-pipeline command after checking "
        "all child processes; record each incident."
    )
    return supervisor.session(config.load(ROOT), ROOT / "engine", command, command,
                              scope, interval=300, hours=6, audit_timeout=240)


def launch():
    preflight()
    with (ROOT / "launch.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT / "launch.json").exists():
            raise RuntimeError("Already launched; inspect the supervision session before resuming")
        with (ROOT / "supervisor.log").open("x") as log:
            proc = subprocess.Popen([sys.executable, str(ROOT / "launch.py"), "supervise"],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        save(ROOT / "launch.json", {"supervisor_pid": proc.pid, "at": time.time(),
                                    "command": [sys.executable, str(ROOT / "launch.py"), "supervise"]})
        print(json.dumps({"supervisor_pid": proc.pid, "log": str(ROOT / "supervisor.log")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "preflight", "run", "supervise", "launch", "status"])
    action = parser.parse_args().action
    if action == "status":
        config, health, _ = setup_runtime()
        print(json.dumps(health.snapshot(config.load(ROOT)), indent=2))
    else:
        result = globals()[action]()
        if isinstance(result, int):
            sys.exit(result)

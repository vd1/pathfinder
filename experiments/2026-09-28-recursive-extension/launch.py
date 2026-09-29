"""Prepare and run a four-thread, frozen recursive-extension experiment.

Only this new experiment is written. Historical campaigns are read-only inputs.
The production coordinator owns execution, locking, admission and provenance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OLD = REPO / "experiments/2026-09-23-gpt-6-sol-rerun-01"
PILOT = REPO / "experiments/2026-09-25-repeat-injection"
ENGINE_COMMIT = "01b0f87"
PLAN = REPO / "plans/2026-09-28-1322-recursive-extension.md"
QUESTIONS = {
    1: "Under shared or correlated observation noise, what can a peer-scoring mechanism certify "
       "about its intended target, and what additional information or restrictions are necessary? "
       "Separate statistical identification from strategic truthfulness.",
    2: "Can finite-sample risk advice support a costed, verifiable downstream decision guarantee? "
       "Distinguish expected surrogate error, realised sampling error and exact feasibility; "
       "state the additional assumptions or an impossibility result.",
}
PAIRS = {"repeat": [(1, "Q4P6"), (2, "Q1P1")],
         "recursive": [(1, "Q4P1"), (2, "Q1P2")]}


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def lines(path, values):
    path.write_text("".join(json.dumps(value) + "\n" for value in values))


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f"Expected exactly one correction target: {before!r}")
    return text.replace(before, after, 1)


def prepare_seed(number, pair):
    source = PILOT / "reinjection/threads" / pair
    paper = source / "paper"
    status = read(paper / "paper.json")
    assert status["status"] == "ACCEPTED" and status["build_ok"]
    dest = ROOT / "seeds" / f"R{number}-v2"
    dest.mkdir(parents=True)
    text = (paper / "paper.tex").read_text()
    bib = (paper / "references.bib").read_text()
    text = replace_once(text, "\\begin{document}",
                        "\\date{28 September 2026; clarified version 2}\n\\begin{document}")
    bib = re.sub(r"^\s*url = \{(?:\.\./inputs/P\.tex|referee/pathfinder-local-S4/P\.tex)\}\s*\n", "\n", bib, flags=re.M)
    if number == 1:
        text = replace_once(text, r"Suppose \(a_r\geq\alpha>0\), \(p_e\in[\tau,1-\tau]\),",
                            r"Suppose \(a_r\geq\alpha>0\), \(0<\tau\leq1/2\), \(p_e\in[\tau,1-\tau]\),")
        text = replace_once(text, "With \\(N\\) independent items per measured population,",
                            "On every measured overlap link both observers label the same realised draw.\n"
                            "With \\(N\\) independent items per measured population,")
        bib = replace_once(bib, "Supplied local manuscript, dated 25 September 2026; no public identifier found",
                           "Supplied unpublished manuscript; package item local-source/P.tex; original pilot seed S1")
    else:
        text = replace_once(text, "the second tests whether one chosen reward works across the entire box",
                            "the second tests whether there exists a single common reward that works across the entire box")
        bib = replace_once(bib, "Supplied manuscript, 25 September 2026. Referee package item pathfinder-local-S4; file referee/pathfinder-local-S4/P.tex",
                           "Supplied unpublished manuscript; package item local-source/P.tex; original pilot seed S4")
    (dest / "paper.tex").write_text(text)
    (dest / "references.bib").write_text(bib)
    (dest / "local-source").mkdir()
    shutil.copy2(source / "inputs/P.tex", dest / "local-source/P.tex")
    env = dict(os.environ, TEXINPUTS=str(ROOT / "engine/pathfinder/styles") + os.pathsep)
    build = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
                           cwd=dest, env=env, capture_output=True, text=True)
    (dest / "build.log").write_text(build.stdout + build.stderr)
    build.check_returncode()
    full = re.sub(r"\\bibliographystyle\{[^}]+\}", "", text)
    full = re.sub(r"\\bibliography\{[^}]+\}", lambda _: (dest / "paper.bbl").read_text(), full)
    assert not re.search(r"\\(?:input|include)\s*\{", full)
    assert "\\begin{thebibliography}" in full and "\\end{document}" in full
    (dest / "fulltext.tex").write_text(full)
    provenance = {"version": 2, "parent": str(paper.relative_to(REPO)),
                  "parent_status": status, "new_external_review": False,
                  "changes": "Reviewer-requested local citation and assumption clarifications; "
                             "R2 also clarifies common-reward existence wording.",
                  "parent_hashes": {name: sha(paper / name) for name in
                                    ("paper.tex", "references.bib", "paper.json", "review.json")},
                  "immediate_local_source_sha256": sha(dest / "local-source/P.tex")}
    save(dest / "provenance.json", provenance)
    return {"id": f"pathfinder-recursive-R{number}-v2", "source_kind": "local manuscript",
            "title": re.search(r"\\title\{([^}]+)\}", text).group(1),
            "abstract": re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.S).group(1),
            "authors": ["Pathfinder research campaign"], "date": "2026-09-28",
            "text": f"sources/R{number}-v2.tex", "arxiv_id": None}


def prepare():
    if any((ROOT / name).exists() for name in ("manifest.json", "engine", "seeds", "repeat", "recursive")):
        raise RuntimeError("Already or partially prepared; inspect, never overwrite")
    from pathfinder import freeze
    frozen = freeze.freeze(REPO, ENGINE_COMMIT, ROOT / "engine")
    seeds = [prepare_seed(1, "Q1P1"), prepare_seed(2, "Q4P4")]
    qrows, prows = rows(OLD / "Q.jsonl"), rows(OLD / "P.jsonl")
    prior = read(OLD / "manifest.json")
    for name in ("Q.jsonl", "P.jsonl"):
        assert sha(OLD / name) == prior["inputs"][name]
    settings = read(PILOT / "repeat/campaign.json")
    settings.update(parent="..", budget_usd=50,
                    extensions={"path": "../deploy", "admission": "recursive_extension:admit"})
    settings["codex"]["search"] = "config"
    peer = (ROOT / "engine/prompts/peer.md").read_text()
    start, end = peer.index("{{MATERIAL}} The scan"), peer.index("Then look for an advance")
    peer = peer[:start] + ("{{MATERIAL}} This pair was prespecified without a scan score.\n"
                          "The assigned starting question is: {{CONNEXION}}\n"
                          "This is a question, not a desired conclusion; sharpen or reject it with reasons.\n") + peer[end:]
    for arm in PAIRS:
        dest = ROOT / arm
        (dest / "sources").mkdir(parents=True)
        (dest / "prompts").mkdir()
        (dest / "prompts/peer.md").write_text(peer)
        save(dest / "campaign.json", settings)
        shutil.copy2(OLD / "Q.jsonl", dest / "Q.jsonl")
        p = prows if arm == "repeat" else seeds
        lines(dest / "P.jsonl", p)
        for row in qrows + (prows if arm == "repeat" else []):
            target = dest / row["text"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(OLD / row["text"], target)
        if arm == "recursive":
            for n in (1, 2):
                shutil.copy2(ROOT / f"seeds/R{n}-v2/fulltext.tex", dest / f"sources/R{n}-v2.tex")
        pairs, questions = [], []
        for block, pair in PAIRS[arm]:
            i, j = map(int, pair[1:].split("P"))
            pairs.append({"pair_id": pair, "q": qrows[i-1]["id"], "p": p[j-1]["id"], "score": None})
            questions.append({"pair_id": pair, "connexion": QUESTIONS[block],
                              "rationale": "Prespecified incremental question; no scan performed."})
        save(dest / "shortlist.json", {"pairs": pairs, "selection": "prespecified extension follow-up"})
        lines(dest / "scan.jsonl", questions)
    parent = dict(settings)
    parent.pop("parent")
    parent["extensions"] = {"path": "deploy", "snapshot_extra": "recursive_extension:snapshot"}
    save(ROOT / "campaign.json", parent)
    save(ROOT / "shortlist.json", {"pairs": []})
    save(ROOT / "schedule.json", {"arms": {a: a for a in PAIRS}, "stages": ["research", "edit", "paper"],
                                  "schedule": [{"arm": a, "pair": p} for a, p in
                                               [("repeat", "Q4P6"), ("recursive", "Q4P1"),
                                                ("recursive", "Q1P2"), ("repeat", "Q1P1")]]})
    protected = {}
    for n, pair in ((1, "Q1P1"), (2, "Q4P4")):
        for name in ("paper.tex", "paper.pdf", "references.bib", "paper.json", "review.json"):
            path = PILOT / "reinjection/threads" / pair / "paper" / name
            protected[str(path.relative_to(REPO))] = sha(path)
    immutable = [p for p in ROOT.rglob("*") if p.is_file() and
                 "engine" not in p.relative_to(ROOT).parts and "__pycache__" not in p.parts and
                 p.suffix not in (".log", ".aux", ".out", ".fls", ".fdb_latexmk", ".blg")]
    save(ROOT / "manifest.json", {"created_at": time.time(), "engine_commit": frozen["commit"],
         "plan_sha256": sha(PLAN), "frozen_hashes": {str(p.relative_to(ROOT)): sha(p) for p in immutable},
         "protected_archives": protected, "questions": QUESTIONS, "limits": {"per_arm_usd_equivalent": 50,
         "watch_hours": 3, "admission_hours": 2.5}, "source_audit": "plans/2026-09-28-source-audit.md",
         "authorization": "User: do all fixes, then all nexts autonomously, 28 September 2026",
         "isolation": "Instruction-based read restriction, not an enforced read barrier"})
    preflight()


def environment():
    os.environ.update(PYTHONPATH=str(ROOT / "engine"), PYTHONUNBUFFERED="1", no_proxy="*")
    for key in list(os.environ):
        if key.startswith("HERDR_") or key in ("CODEX_THREAD_ID", "CODEX_SESSION_ID"):
            os.environ.pop(key)
    sys.path.insert(0, str(ROOT / "engine"))
    instruction = ("Execute only the assigned scientific role. Read only the assigned thread's supplied "
                   "papers, ledger and working files, plus permitted external literature. Do not read parent "
                   "directories, other threads, historical campaigns, experiment plans or manuscript reviews. "
                   "Do not search for the Pathfinder repository online. Do not spawn additional agents. "
                   "Installed tools and the ledger helper may be executed. Local manuscripts are unpublished "
                   "inputs, not arXiv deposits; do not invent public identifiers. Internal Q/P names in a "
                   "manuscript need not name this pair. State assumptions and distinguish results from proposals. "
                   "Record any exposure to historical campaign results. Do not use Shipshape.")
    os.environ["PATHFINDER_CODEX"] = shlex.join(["codex", "-c", "project_doc_max_bytes=0", "-c",
                                                "developer_instructions=" + json.dumps(instruction)])


def preflight():
    from pathfinder import freeze, coordinator, resources
    record = read(ROOT / "manifest.json")
    assert freeze.verify(ROOT / "engine", REPO)["status"] == "verified"
    assert sha(PLAN) == record["plan_sha256"]
    for name, digest in record["frozen_hashes"].items():
        assert sha(ROOT / name) == digest, name
    for name, digest in record["protected_archives"].items():
        assert sha(REPO / name) == digest, name
    _, arms, schedule = coordinator.load(ROOT / "schedule.json")
    assert len(schedule["schedule"]) == 4
    assert resources.prompt_digests(arms["repeat"]) == resources.prompt_digests(arms["recursive"])
    for name, c in arms.items():
        assert c.budget_usd == 50 and c.model == "gpt-6-sol"
        for row in rows(c.path("Q.jsonl")) + rows(c.path("P.jsonl")):
            assert c.path(row["text"]).stat().st_size > 1000
        question_rows = {r["pair_id"]: r for r in rows(c.path("scan.jsonl"))}
        for block, pair in PAIRS[name]:
            assert question_rows[pair]["connexion"] == QUESTIONS[block]
    print("Preflight passed: verified engine, immutable inputs, four identities, matched questions and prompts", flush=True)


def run():
    preflight()
    from pathfinder import coordinator
    state = coordinator.run(ROOT / "schedule.json")
    print(json.dumps(state), flush=True)
    return 0 if state["status"] == "complete" else 1


def supervise():
    preflight()
    from pathfinder import config, supervise as watch
    command = [sys.executable, str(ROOT / "launch.py"), "run"]
    scope = ("Complete only the FOUR schedule.json entries across repeat and recursive, including readable "
             "editing and DRAFT author/reviewer papers. The root shortlist is intentionally empty. Read the "
             "snapshot extensions.arms and progress/outcomes; never infer completion from the root shortlist. "
             f"For aggregate status run {sys.executable} {ROOT / 'launch.py'} status. "
             "Inspect active calls and process owners in BOTH children before any restart or completion. "
             "A live root heartbeat alone is not progress. Censored, stopped or failed is not complete. "
             "The launch admission window is 2.5 hours; do not clear its stop or extend it. No budget, "
             "source, engine, prompt or schedule changes; no new pairs or generations. You may resume the "
             "exact workload only after verifying it is safe. For a saved-verdict escaping failure only, "
             "you are explicitly authorized to run the frozen Python -m pathfinder.cli --root EXACT_ARM "
             "repair-verdict EXACT_PAIR, using one of the two recorded arm paths and scheduled pair IDs; "
             "its guards must pass. Log the incident and result. Other uncertainty requires needs_operator.")
    return watch.session(config.load(ROOT), ROOT / "engine", command, command, scope,
                         interval=300, hours=3, audit_timeout=240)


def launch():
    preflight()
    record = {"started_at": time.time(), "admission_deadline": time.time() + 2.5 * 3600,
              "command": [sys.executable, str(ROOT / "launch.py"), "supervise"]}
    # Exclusive creation is the launch-once guard, including concurrent attempts.
    with (ROOT / "launch.json").open("x") as stream:
        json.dump(record, stream, indent=2)
    with (ROOT / "supervisor.log").open("x") as log:
        proc = subprocess.Popen(record["command"], cwd=ROOT / "engine", stdin=subprocess.DEVNULL,
                                stdout=log, stderr=log, start_new_session=True)
    save(ROOT / "launch.json", dict(record, supervisor_pid=proc.pid))
    print(json.dumps({"supervisor_pid": proc.pid, "log": str(ROOT / "supervisor.log")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "preflight", "run", "supervise", "launch", "status"))
    action = parser.parse_args().action
    if action != "prepare":
        environment()
    if action == "status":
        from pathfinder import config, health
        print(json.dumps(health.snapshot(config.load(ROOT)), indent=2))
    else:
        result = globals()[action]()
        if isinstance(result, int):
            sys.exit(result)

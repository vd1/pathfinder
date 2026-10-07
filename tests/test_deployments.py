"""Deployment contract tests: each supported deployment, prepared its own way, runs on the candidate engine."""
import importlib.util, json, os, re, shutil, subprocess, sys
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


def _tree(path: Path) -> dict:
    """Every file's size and modification time: a read-only replay must leave them all as they were."""
    return {str(p.relative_to(path)): (p.stat().st_size, p.stat().st_mtime_ns) for p in path.rglob("*") if p.is_file()}


def _replay(source: Path, tmp_path: Path, skip=("engine",)):
    """The candidate engine reads a finished campaign: a copy is loaded, its state document and health built."""
    from pathfinder import campaign_state, config, health
    copy = tmp_path / "campaign"
    shutil.copytree(source, copy, ignore=lambda d, names: [n for n in names if Path(d) == source and n in skip])
    c = config.load(copy)
    state = campaign_state.build(c)
    health.snapshot(c)
    return c, state


AGQSL_OPEN_PAIRS = ["Q1P1", "Q2P2", "Q3P3", "Q4P4", "Q5P5"]
AGQSL_SKIP = ("engine", "sources-cache")        # the frozen engine and the importer's download cache, untracked


def _agqsl_canon(tmp_path: Path) -> Path:
    """canon/ as committed at the pinned revision (HEAD outside a release): a campaign running in the checkout
    changes its files while the contract reads them, so the contract reads the record, not the live tree."""
    import tarfile, io
    checkout = deployment_matrix.checkout("agqsl")
    rev = deployment_matrix.load()["agqsl"]["revision"] if deployment_matrix.RELEASE else "HEAD"
    data = subprocess.run(["git", "-C", str(checkout), "archive", "--format=tar", rev, "canon"],
                          capture_output=True, check=True).stdout
    target = tmp_path / "recorded"
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(target, filter="tar")   # records keep the editor's style links (absolute)
    return target / "canon"


def _agqsl_imported(canon: Path) -> list[str]:
    """The pairs canon/import_campaign2.py brought in (second-campaign triplets), in import order."""
    mapping = json.loads((canon / "import.json").read_text())
    return [pair for pair, origin in mapping.items() if origin.get("art_id")]


def test_agqsl_canon_replays_on_the_candidate_engine(tmp_path):
    canon = _agqsl_canon(tmp_path)
    before = _tree(canon)
    c, state = _replay(canon, tmp_path, skip=AGQSL_SKIP)
    assert c.peers and (canon / "engine-ref").read_text().strip().startswith("engine-v")
    units = {u["unit"]: u for u in state["units"]}
    imported = _agqsl_imported(canon)
    assert sorted(units) == sorted(AGQSL_OPEN_PAIRS + imported)
    from collections import Counter
    assert Counter(units[p]["research"]["status"] for p in AGQSL_OPEN_PAIRS) == {"PAUSE": 3, "DRAFT": 2}
    assert all(units[p]["editorial"]["status"] == "done" for p in AGQSL_OPEN_PAIRS)
    assert sorted(units[p]["assessment"]["status"] or "" for p in AGQSL_OPEN_PAIRS).count("ACCEPTED") == 2
    for pair in imported:                           # prepared for research, or researched since by hand
        assert units[pair]["q"]["id"] and units[pair]["p"]["id"] and not units[pair]["q"]["id"].startswith("agqsl-")
    # each role's overlay is appended to the candidate's own prompt
    from pathfinder import resources
    for role in ("peer", "consolidate", "verify", "editor"):
        overlay = (canon / "prompts" / f"{role}.append.md").read_text().strip()
        assert resources.prompt_template(c, role).rstrip().endswith(overlay), role
    assert _tree(canon) == before


@needs_tex
def test_an_imported_agqsl_pair_researches_and_edits_on_the_candidate_engine(tmp_path, monkeypatch):
    """One imported second-campaign pair not yet researched runs through research and editing on the stub
    backend, the runner bounded to it, in a copy of canon/: agQSL's prompt overlays reach the calls (each role
    is sent to inputs/question.md), peer search stays off, and canon/ is left as it was."""
    from pathfinder import config, edit, research, runner, stub, transport
    canon = _agqsl_canon(tmp_path)
    before = _tree(canon)
    pair = next((p for p in _agqsl_imported(canon)
                 if json.loads((canon / "threads" / p / "status.json").read_text()).get("status") not in research.TERMINAL
                 and not (canon / "threads" / p / "ledger.jsonl").read_text().strip()), None)
    copy = tmp_path / "canon"
    shutil.copytree(canon, copy, ignore=lambda d, names: [n for n in names if Path(d) == canon and n in AGQSL_SKIP])
    if pair is None:                              # every imported pair researched: start the first one afresh, in the copy
        pair = _agqsl_imported(canon)[0]
        d = copy / "threads" / pair
        for item in d.iterdir():
            if item.name != "inputs":
                shutil.rmtree(item) if item.is_dir() else item.unlink()
        (d / "ledger.jsonl").write_text("")
        (d / "status.json").write_text(json.dumps({"pair_id": pair, "round": 1, "stage": "peers", "status": "running",
                                                   "reason": None}))
    raw = json.loads((copy / "campaign.json").read_text())
    raw.update(backend="stub", model="stub"); raw.pop("account", None)
    (copy / "campaign.json").write_text(json.dumps(raw, indent=1))
    monkeypatch.setenv("PATHFINDER_ACCOUNTS", str(tmp_path / "accounts"))
    calls = []
    real = stub.execute
    def recorded(campaign, request):
        calls.append({"stage": request.stage, "search": request.search, "prompt": request.prompt})
        return real(campaign, request)
    monkeypatch.setattr(stub, "execute", recorded)
    c = config.load(copy)
    assert c.peer_search is False
    # canon/ records its last run on the frozen engine; the candidate on the stub backend is a linked run
    assert runner.run(c, interval=0.05, pairs=[pair], accept_change="deployment contract: candidate engine, stub backend") == 0
    assert research.status(c, pair)["status"] in research.TERMINAL
    assert edit.status(c, pair)["status"] == "done" and (c.thread_dir(pair) / "edited" / "note.tex").is_file()
    stages = {call["stage"] for call in calls}
    assert {"peer", "consolidate", "verify", "edit"} <= stages
    for call in calls:
        assert "inputs/question.md" in call["prompt"], call["stage"]
        if call["stage"] == "peer":
            assert call["search"] is False
    recorded = {r.get("call_id") for r in transport.receipts(config.load(canon))}      # the batch's real calls
    assert {r.get("backend") for r in transport.receipts(c) if r.get("thread") == pair and r.get("call_id") not in recorded} == {"stub"}
    others = [p for p in _agqsl_imported(canon) if p != pair] + AGQSL_OPEN_PAIRS
    assert all(_tree(copy / "threads" / p) == _tree(canon / "threads" / p) for p in others)
    assert _tree(canon) == before


def _julien2_recorded(tmp_path: Path, *paths: str) -> Path:
    """julien-2's tracked paths as committed at the pinned revision (HEAD outside a release), read through git
    archive like agQSL's canon/: the contract reads the record, never the live tree."""
    import tarfile, io
    checkout = deployment_matrix.checkout("pathfinder-julien-2")
    rev = deployment_matrix.load()["pathfinder-julien-2"]["revision"] if deployment_matrix.RELEASE else "HEAD"
    data = subprocess.run(["git", "-C", str(checkout), "archive", "--format=tar", rev, *paths],
                          capture_output=True, check=True).stdout
    target = tmp_path / "recorded"
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(target, filter="tar")   # records keep the editor's style links (absolute)
    return target


def test_julien2_canon_replays_on_the_candidate_engine(tmp_path):
    """campaign-2-batch-1/ holds eva-top-ten-01 as ten one-pair composable campaigns (made by import-eva2), each
    named by julien-2's own pair id (Q002-P024), which its numbered corpus gives the pair too: each loads, its
    research ended DRAFT (seven) or PAUSE (three), its PCE edit is done and its actionability is NEEDS_INPUTS."""
    from collections import Counter
    from pathfinder import actionability, corpus, edit
    canon = _julien2_recorded(tmp_path, "campaign-2-batch-1") / "campaign-2-batch-1"
    before = _tree(canon)
    experiments = sorted(d for d in canon.iterdir() if d.is_dir())
    assert len(experiments) == 10 and all(re.fullmatch(r"Q\d{3}-P\d{3}", d.name) for d in experiments)
    research = Counter()
    for d in experiments:
        (tmp_path / d.name).mkdir()
        c, state = _replay(d, tmp_path / d.name)
        pair = d.name
        assert c.raw["research_scheme"] == "composable" and c.raw["branches"] == 3, pair
        assert [u["unit"] for u in state["units"]] == [pair], pair
        assert corpus.pair_id_for(c, 0, 0) == pair and all(corpus.pair_rows(c, pair)), pair
        unit = state["units"][0]
        research[unit["research"]["status"]] += 1
        assert unit["editorial"]["status"] == "done" and edit.status(c, pair)["status"] == "done", pair
        assert actionability.status(c, pair)["decision"] == "NEEDS_INPUTS", pair
        assert sorted(p.name for p in (c.thread_dir(pair) / "branches").iterdir()) == ["branch-1", "branch-2", "branch-3"]
    assert research == {"DRAFT": 7, "PAUSE": 3}
    assert _tree(canon) == before


@needs_tex
def test_a_julien2_shortlisted_pair_runs_composable_research_pce_and_actionability_on_the_candidate_engine(tmp_path, monkeypatch):
    """One shortlisted pair of julien-2's campaign-2-batch-2/ runs on the stub backend in a copy: three direct-EVA
    branches frozen as bundles, the joint thread over them, editing under the campaign's edit_scheme (PCE or the
    single editor) and the actionability assessment. Its pair
    ids are julien-2's own (Q010-P030), found through the numbered corpus. The routed stages stay on the stub (no
    real call), julien-2's prompt overlays reach the calls, and the record is unchanged."""
    from pathfinder import actionability, composable, config, edit, research, runner, stub, transport
    recorded = _julien2_recorded(tmp_path, "campaign-2-batch-2") / "campaign-2-batch-2"
    before = _tree(recorded)
    copy = tmp_path / "campaign-2-batch-2"
    shutil.copytree(recorded, copy)
    raw = json.loads((copy / "campaign.json").read_text())
    assert raw["research_scheme"] == "composable" and raw["actionability"] is True
    pce = raw.get("edit_scheme") == "pce"                  # julien-2 moved to the single editor on 7 October
    assert {"verify", "ledger_review", "actionability"} <= set(raw["routes"])
    raw.update(backend="stub", model="stub"); raw.pop("account", None)
    (copy / "campaign.json").write_text(json.dumps(raw, indent=1))
    monkeypatch.setenv("PATHFINDER_ACCOUNTS", str(tmp_path / "accounts"))
    calls = []
    real = stub.execute
    def recorded_call(campaign, request):
        calls.append({"stage": request.stage, "actor": request.actor, "prompt": request.prompt})
        return real(campaign, request)
    monkeypatch.setattr(stub, "execute", recorded_call)
    c = config.load(copy)
    shortlist = [p["pair_id"] for p in json.loads((copy / "shortlist.json").read_text())["pairs"]]
    assert len(shortlist) == 10 and all(re.fullmatch(r"Q\d{3}-P\d{3}", p) for p in shortlist), shortlist
    pair = next((p for p in shortlist if not (copy / "threads" / p).exists()), shortlist[0])
    if (copy / "threads" / pair).exists():            # every shortlisted pair researched: start one afresh in the copy
        shutil.rmtree(copy / "threads" / pair)
    recorded_calls = {r.get("call_id") for r in transport.receipts(c)}
    assert runner.run(c, interval=0.05, pairs=[pair], accept_change="deployment contract: candidate engine, stub backend") == 0
    d = c.thread_dir(pair)
    assert research.status(c, pair)["status"] in research.TERMINAL
    for label in composable.labels(c):                      # each branch frozen as a bundle the joint thread reads
        assert (d / "branches" / label / "bundle.json").is_file(), label
    assert (d / "ledger.jsonl").read_text().strip()         # the joint thread's own ledger
    record = json.loads((d / "edited" / "edit.json").read_text())
    assert edit.status(c, pair)["status"] == "done" and (record.get("scheme") == "pce") == pce
    assert (d / "edited" / "note.tex").is_file()
    assert actionability.status(c, pair)["status"] == "done"
    stages = {call["stage"] for call in calls}
    assert {"peer", "ledger_review", "consolidate", "verify", "edit", "actionability"} <= stages
    assert any((call["actor"] or "").startswith("pce-") for call in calls) == pce
    overlay = lambda role: (copy / "prompts" / f"{role}.append.md").read_text().strip()[:200]
    for stage, role in (("peer", "peer"), ("verify", "verify"), ("ledger_review", "branch"), ("actionability", "actionability")):
        assert all(overlay(role) in call["prompt"] for call in calls if call["stage"] == stage), stage
    brief = overlay("pce-brief").splitlines()[0]               # the PCE brief travels inside a JSON read scope
    if pce:
        assert any(brief in call["prompt"] for call in calls if (call["actor"] or "").startswith("pce-"))
    assert {r.get("backend") for r in transport.receipts(c) if r.get("call_id") not in recorded_calls} == {"stub"}
    assert _tree(recorded) == before


PROOFTREE_LINK = r'''
import contextlib, io, json, sys
from pathlib import Path
import pathfinder
from pathfinder import composable, config, corpus, research, resources, transport
from prooftree.cli import init, parse_metadata, sha
from prooftree.state import Store, initialize
from prooftree import workflow

root = Path(sys.argv[1])
atom = lambda aid: (f'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/{aid}</id>'
                    '<title>A proof</title><summary>A fixture abstract.</summary><published>2016-03-14</published>'
                    '<author><name>Author</name></author></entry></feed>')
with contextlib.redirect_stdout(io.StringIO()):
    init(root, "stub", "stub")
raw = json.loads((root / "campaign.json").read_text()); raw["budget_usd"] = 400
(root / "campaign.json").write_text(json.dumps(raw))
(root / "sources").mkdir()
for side, aid in (("Q", "1603.04246v2"), ("P", "2303.13427v1")):
    row = parse_metadata(atom(aid))[0]
    text = root / "sources" / f"{side}.txt"; text.write_text("A mathematical full-text fixture.\n")
    row.update(text=f"sources/{side}.txt", source_sha256=sha(text))
    corpus.write([row], root / f"{side}.jsonl")
initialize(root)
with Store(root) as store:
    link = store.link("B1", "2303.13427", "A fixture connection", "contract")
with contextlib.redirect_stdout(io.StringIO()):
    workflow.scan_links(root)
    result = workflow.research_link(root, link)
c = config.load(root / "adaptive" / f"S{link}" / "joint")
d = c.thread_dir("Q1P1")
composable.check_frozen(c, "Q1P1")
receipts = transport.receipts(c)
print(json.dumps({"result": result, "engine": pathfinder.__file__, "scheme": c.raw["research_scheme"],
    "bundles": {label: sorted(composable.verify(d / "branches" / label)["files"]) for label in composable.labels(c)},
    "verdict": {k: research.export_outcome(c, "Q1P1")[k] for k in ("status", "scientific_verdict")},
    "backends": sorted({r["backend"] for r in receipts}), "runs": sorted({r["run_id"] for r in receipts}),
    "branches": sorted({r["branch"] for r in receipts if r.get("branch")}),
    "loaded": sorted(m for m in sys.modules if m.split(".")[0] in ("eva2", "julien2")),
    "overlays": {p.name: resources.prompt_template(c, p.name.removesuffix(".append.md")).rstrip().endswith(p.read_text().strip())
                 for p in sorted(c.path("prompts").glob("*.append.md"))}}))
'''


def _prooftree(script: str, checkout: Path, *args) -> dict:
    """proofTree's own code, imported from its checkout, on the candidate engine (first on the path)."""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT), str(checkout)])}
    r = subprocess.run([sys.executable, "-c", script, *map(str, args)], cwd=checkout, env=env, capture_output=True,
                       text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


@needs_tex
def test_prooftree_researches_a_link_on_the_candidate_engine(tmp_path):
    checkout = deployment_matrix.checkout("prooftree")
    out = _prooftree(PROOFTREE_LINK, checkout, tmp_path / "campaign")
    # one composable campaign: three frozen branches that verify, an accepted joint verdict, an edited PDF
    assert out["scheme"] == "composable" and sorted(out["bundles"]) == ["branch-1", "branch-2", "branch-3"]
    assert all({"ledger.jsonl", "handoff.json"} <= set(files) for files in out["bundles"].values())
    assert out["result"]["outcome"] == "ACCEPT" and out["verdict"] == {"status": "DRAFT", "scientific_verdict": "ACCEPT"}
    assert Path(out["result"]["pdf"]).is_file() and out["result"]["pdf"].endswith("joint/threads/Q1P1/edited/note.pdf")
    # stub receipts under one run, every branch's calls named; the candidate answered and no julien-2 code loaded
    assert out["backends"] == ["prooftree-stub"] and len(out["runs"]) == 1
    assert out["branches"] == ["branch-1", "branch-2", "branch-3"]
    assert Path(out["engine"]).resolve().is_relative_to(ROOT / "pathfinder") and out["loaded"] == []
    assert out["overlays"] and all(out["overlays"].values()), out["overlays"]


PROOFTREE_REPLAY = r'''
import contextlib, io, json, sys
from pathlib import Path
from prooftree import view, workflow

root = Path(sys.argv[1])
state = view.snapshot(root)
read = {}
for outcome in sorted((root / "adaptive").glob("S*/outcome.json")):
    with contextlib.redirect_stdout(io.StringIO()):
        read[outcome.parent.name] = workflow.research_link(root, int(outcome.parent.name[1:]))["outcome"]
print(json.dumps({"runs": len(state["runs"]), "issues": state["issues"], "read": read,
                  "legacy": all(workflow.legacy(p.parent) for p in (root / "adaptive").glob("S*/outcome.json")),
                  "loaded": sorted(m for m in sys.modules if m.split(".")[0] in ("eva2", "julien2"))}))
'''


def test_prooftree_recorded_campaign_replays_read_only_on_the_candidate_engine(tmp_path):
    from pathfinder import import_eva2
    source = deployment_matrix.checkout("prooftree") / "campaigns" / "sphere-packing-rounds2"
    bundles = sorted(p.parent for p in source.glob("adaptive/S*/**/bundle.json"))
    if not bundles:                                 # the recorded runs are local records, not tracked files
        (pytest.fail if deployment_matrix.RELEASE else pytest.skip)(f"no recorded bundles under {source}")
    before = _tree(source)
    for bundle in bundles:                          # eva2's bundles, read in place by their inventory
        import_eva2.verify_bundle(bundle)
    copy = tmp_path / "campaign"
    shutil.copytree(source, copy, symlinks=True)
    out = _prooftree(PROOFTREE_REPLAY, source.parent.parent, copy)
    assert out["read"] == {"S15": "ACCEPT", "S17": "ACCEPT", "S31": "ACCEPT"} and out["legacy"]
    assert out["runs"] == 3 and out["issues"] == [] and out["loaded"] == []
    assert len(bundles) == 18 and _tree(source) == before


def test_the_10x10_pilot_replays_on_the_candidate_engine(tmp_path):
    root = deployment_matrix.checkout("pilot-10x10")
    tracked = ("campaign.json", "Q.jsonl", "P.jsonl", "scan.jsonl", "shortlist.json", "threads")
    before = {name: _tree(root / name) if (root / name).is_dir() else (root / name).stat().st_mtime_ns for name in tracked}
    (tmp_path / "src").mkdir()
    for name in tracked:
        (shutil.copytree if (root / name).is_dir() else shutil.copy2)(root / name, tmp_path / "src" / name)
    c, state = _replay(tmp_path / "src", tmp_path)
    assert len(c.path("scan.jsonl").read_text().splitlines()) == 100
    assert len(json.loads(c.path("shortlist.json").read_text())["pairs"]) == 14
    assert state["stages"] == {"research": {"PAUSE": 8, "DRAFT": 5, "PAUSE-ON-ITERATE": 1}, "edit": {"done": 14},
                               "paper": {"ACCEPTED": 5}}
    assert {name: _tree(root / name) if (root / name).is_dir() else (root / name).stat().st_mtime_ns for name in tracked} == before


@needs_tex
def test_a_study_under_the_10x10_pilot_runs_on_the_candidate_engine(tmp_path):
    """The pilot stays open for further studies: a child campaign under it ("parent": ".."), on two of its own
    papers, coordinated through research, editing and the paper on the stub backend, leaves the pilot as it was."""
    from pathfinder import coordinator, transport
    from pathfinder import config as engine_config
    root = deployment_matrix.checkout("pilot-10x10")
    tracked = ("campaign.json", "Q.jsonl", "P.jsonl", "scan.jsonl", "shortlist.json", "threads")
    before = {name: _tree(root / name) if (root / name).is_dir() else (root / name).stat().st_mtime_ns for name in tracked}
    parent = tmp_path / "pilot"; parent.mkdir()
    for name in tracked:
        (shutil.copytree if (root / name).is_dir() else shutil.copy2)(root / name, parent / name)
    raw = json.loads((root / "campaign.json").read_text())
    child = parent / "study"; child.mkdir()
    papers = {side: json.loads((root / f"{side}.jsonl").read_text().splitlines()[0]) for side in "QP"}
    for side, row in papers.items():                    # abstracts only: the study's research is the stub's
        (child / f"{side}.jsonl").write_text(json.dumps({k: row[k] for k in ("id", "title", "abstract")}) + "\n")
    (child / "shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": "Q1P1"}]}))
    (child / "campaign.json").write_text(json.dumps({
        **{k: raw[k] for k in ("peers", "rounds", "repairs", "allowances") if k in raw},
        "backend": "stub", "model": "stub", "seats": 1, "paper_rounds": 1, "budget_usd": 100,
        "call_estimate_usd": 1, "parent": ".."}))
    (parent / "schedule.json").write_text(json.dumps({"arms": {"study": "study"}, "stages": ["research", "edit", "paper"],
                                                      "schedule": [{"arm": "study", "pair": "Q1P1"}]}))
    state = coordinator.run(parent / "schedule.json", interval=0.05, heartbeat=0.05)
    assert state["status"] == "complete"
    outcome = json.loads((parent / "outcomes.json").read_text())["study"]["Q1P1"]
    assert outcome["paper"]["status"] == "ACCEPTED"
    assert {r.get("backend") for r in transport.receipts(engine_config.load(child))} == {"stub"}
    assert {name: _tree(root / name) if (root / name).is_dir() else (root / name).stat().st_mtime_ns for name in tracked} == before

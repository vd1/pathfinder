"""julien-2's eva2 experiments (three direct-EVA branch campaigns and a joint campaign) as one canonical composable pair."""
import json, shutil
from pathfinder import composable, config, edit, import_eva2, reconcile, research, transport
from stubcampaign import make


def _eva2(tmp_path):
    exp = tmp_path / "experiments" / "eva-top-ten-01-q002-p024"
    for k in (1, 2, 3):
        c = make(exp / "runs" / f"branch-{k}", research_scheme="direct_eva", ledger_reviews=4, rounds=3)
        research.run_thread(c, "Q1P1")
        assert research.status(c, "Q1P1")["status"] == "HANDOFF"
    joint = make(exp / "runs" / "joint", research_scheme="eva", rounds=2,
                 research_bundles=[f"branches/branch-{k}" for k in (1, 2, 3)])
    d = research.prepare(joint, "Q1P1")
    for k in (1, 2, 3):                                  # eva2 copies each frozen handoff into the joint thread
        src = exp / "runs" / f"branch-{k}" / "threads" / "Q1P1"
        shutil.copytree(src, d / "branches" / f"branch-{k}", ignore=shutil.ignore_patterns(".pathfinder"))
        (d / "branches" / f"branch-{k}" / "bundle.json").write_text(json.dumps({"eva2": True, "label": f"branch-{k}"}))
    research._set(joint, "Q1P1", status="running", stage="peers", round=1)
    assert research.run_thread(joint, "Q1P1") == "DRAFT"
    (exp / "runs" / "joint" / "prompts").mkdir(exist_ok=True)
    (exp / "runs" / "joint" / "prompts" / "peer.md").write_text("julien-2 joint peer prompt {{ACTOR}}")
    return exp


def test_an_eva2_experiment_becomes_a_canonical_composable_pair(tmp_path):
    exp = _eva2(tmp_path)
    out = tmp_path / "canon"
    import_eva2.run(exp, out)
    c = config.load(out)
    assert c.raw["research_scheme"] == "composable" and c.raw["branches"] == 3
    assert c.raw["branch"]["ledger_reviews"] == 4 and c.raw["branch"]["rounds"] == 3 and c.raw["rounds"] == 2
    composable.check_frozen(c, "Q1P1")                            # canonical inventories over eva2's exact files
    s = research.status(c, "Q1P1")
    assert s["status"] == "DRAFT" and set(s["branches_frozen"]) == {"branch-1", "branch-2", "branch-3"}
    d = c.thread_dir("Q1P1")
    assert (d / "branches" / "branch-1" / "eva2-bundle.json").exists()
    assert (d / "branch-runs" / "branch-2" / "status.json").exists()
    assert (out / "prompts" / "peer.md").read_text().startswith("julien-2 joint")
    assert json.loads((out / "import.json").read_text())["experiment"] == str(exp)


def test_the_imported_pair_goes_on_to_edit_without_new_research(tmp_path):
    exp = _eva2(tmp_path)
    out = tmp_path / "canon"
    import_eva2.run(exp, out)
    c = config.load(out)
    before = len(transport.receipts(c))
    from pathfinder import runner
    assert runner.pending(c) == ["Q1P1"]                          # research done, edit to do
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert len(transport.receipts(c)) == before
    assert edit.run(c, "Q1P1") == "done"

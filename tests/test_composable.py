"""Composable EVA: N direct-EVA branches, frozen as bundles, then a joint EVA thread (phase 6)."""
import json
import pytest
from pathfinder import composable, config, research, transport
from stubcampaign import make


def test_the_old_scheme_name_is_refused(tmp_path):
    make(tmp_path)
    raw = json.loads((tmp_path / "campaign.json").read_text()); raw["research_scheme"] = "eva_minus"
    (tmp_path / "campaign.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="direct_eva"):
        config.load(tmp_path)


def _composable(tmp_path, **raw):
    return make(tmp_path, research_scheme="composable", **raw)


def test_views_have_their_own_scheme_and_directories(tmp_path):
    c = _composable(tmp_path, branch={"rounds": 1}, joint={"rounds": 2})
    assert composable.labels(c) == ["branch-1", "branch-2", "branch-3"]
    b = composable.branch_view(c, "Q1P1", "branch-2")
    assert b.thread_dir("Q1P1") == c.thread_dir("Q1P1") / "branch-runs" / "branch-2"
    assert b.raw["research_scheme"] == "direct_eva" and not b.raw.get("research_bundles") and b.rounds == 1
    assert b.branch == "branch-2" and c.raw["research_scheme"] == "composable"
    j = composable.joint_view(c, "Q1P1")
    assert j.thread_dir("Q1P1") == c.thread_dir("Q1P1") and j.rounds == 2
    assert j.raw["research_scheme"] == "eva" and j.raw["research_bundles"] == [f"branches/branch-{n}" for n in (1, 2, 3)]
    assert getattr(j, "branch", None) is None


def test_branch_calls_are_attributed_to_their_branch(tmp_path):
    c = _composable(tmp_path, branches=2)
    b = composable.branch_view(c, "Q1P1", "branch-2")
    research.prepare(b, "Q1P1")
    research.run_thread(b, "Q1P1")
    rows = transport.receipts(c)
    assert rows and all(r["thread"] == "Q1P1" and r["branch"] == "branch-2" for r in rows)
    events = [json.loads(l) for l in c.path("events.jsonl").read_text().splitlines()]
    assert any(e.get("branch") == "branch-2" for e in events)


def _handed_off(tmp_path, label="branch-1", **raw):
    c = _composable(tmp_path, **raw)
    b = composable.branch_view(c, "Q1P1", label)
    research.prepare(b, "Q1P1")
    assert research.run_thread(b, "Q1P1") == "HANDOFF"
    return c, b


def test_a_handoff_freezes_into_a_read_only_verified_bundle(tmp_path):
    import os, stat
    c, b = _handed_off(tmp_path)
    bundle = composable.freeze(c, "Q1P1", "branch-1")
    assert bundle == c.thread_dir("Q1P1") / "branches" / "branch-1"
    inventory = json.loads((bundle / "bundle.json").read_text())
    assert {"ledger.jsonl", "status.json", "handoff.json"} <= set(inventory["files"])
    assert any(name.startswith("ada/") for name in inventory["files"]) or (bundle / "ada").is_dir()
    assert json.loads((bundle / "handoff.json").read_text())["scientific_verdict"] is None
    assert not os.stat(bundle / "ledger.jsonl").st_mode & stat.S_IWUSR
    composable.verify(bundle)
    assert composable.freeze(c, "Q1P1", "branch-1") == bundle          # twice: the same bundle, unchanged
    assert json.loads((bundle / "bundle.json").read_text()) == inventory


def test_only_a_handoff_freezes(tmp_path):
    c = _composable(tmp_path)
    b = composable.branch_view(c, "Q1P1", "branch-1")
    research.prepare(b, "Q1P1")
    with pytest.raises(composable.BundleError, match="HANDOFF"):
        composable.freeze(c, "Q1P1", "branch-1")


def test_verify_names_a_changed_or_an_extra_file(tmp_path):
    import os
    c, b = _handed_off(tmp_path)
    bundle = composable.freeze(c, "Q1P1", "branch-1")
    os.chmod(bundle / "ledger.jsonl", 0o644); (bundle / "ledger.jsonl").write_text("rewritten\n")
    with pytest.raises(composable.BundleError, match="ledger.jsonl"):
        composable.verify(bundle)
    c2, _ = _handed_off(tmp_path / "two")
    bundle2 = composable.freeze(c2, "Q1P1", "branch-1")
    (bundle2 / "ada" / "late.txt").write_text("added after the freeze")
    with pytest.raises(composable.BundleError, match="ada/late.txt"):
        composable.verify(bundle2)


def test_a_composable_pair_runs_its_branches_then_the_joint_thread(tmp_path):
    from pathfinder import runner
    c = _composable(tmp_path)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    d = c.thread_dir("Q1P1")
    for label in composable.labels(c):
        composable.verify(d / "branches" / label)
    assert (d / "ledger.jsonl").exists() and (d / "Q1P1.tex").exists()
    s = research.status(c, "Q1P1")
    assert set(s["branches_frozen"]) == {"branch-1", "branch-2", "branch-3"}
    joint = [r for r in transport.receipts(c) if r["branch"] is None]
    assert {"consolidate", "verify"} <= {r["stage"] for r in joint}
    assert {r["branch"] for r in transport.receipts(c)} == {None, "branch-1", "branch-2", "branch-3"}


def test_the_runner_takes_a_composable_pair_through_edit(tmp_path):
    from pathfinder import edit, runner
    c = _composable(tmp_path, branches=2)
    runner._work(c, "Q1P1")
    assert research.status(c, "Q1P1")["status"] == "DRAFT" and edit.status(c, "Q1P1")["status"] == "done"


@pytest.mark.parametrize("n", [1, 5])
def test_any_number_of_branches(tmp_path, n):
    c = _composable(tmp_path, branches=n)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert len(list((c.thread_dir("Q1P1") / "branches").glob("branch-*/bundle.json"))) == n


@pytest.mark.parametrize("bad", [0, -1, "three"])
def test_a_bad_branch_count_is_refused(tmp_path, bad):
    with pytest.raises(ValueError, match="branches"):
        _composable(tmp_path, branches=bad)              # make() loads the campaign it writes


def _stop_where(monkeypatch, where):
    from pathfinder.admission import Refused
    real, calls, armed = transport.execute, [], {"on": True}

    def execute(campaign, request):
        calls.append(str(request.cwd))
        if armed["on"] and where(str(request.cwd)):
            armed["on"] = False
            raise Refused("stop requested")
        return real(campaign, request)
    monkeypatch.setattr(transport, "execute", execute)
    return calls


def test_a_stop_in_one_branch_resumes_without_paying_finished_branches_again(tmp_path, monkeypatch):
    c = _composable(tmp_path)
    calls = _stop_where(monkeypatch, lambda cwd: cwd.endswith("branch-runs/branch-2"))
    assert research.run_thread(c, "Q1P1") == "stopped"
    done = {label: len([x for x in calls if x.endswith(label)]) for label in ("branch-1", "branch-3")}
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert {label: len([x for x in calls if x.endswith(label)]) for label in ("branch-1", "branch-3")} == done


def test_a_bundle_changed_after_the_freeze_blocks_the_joint_thread(tmp_path, monkeypatch):
    import os
    c = _composable(tmp_path)
    d = c.thread_dir("Q1P1")
    _stop_where(monkeypatch, lambda cwd: cwd == str(d))
    assert research.run_thread(c, "Q1P1") == "stopped"
    ledger = d / "branches" / "branch-2" / "ledger.jsonl"
    os.chmod(ledger, 0o644); ledger.write_text(ledger.read_text() + "\n")
    assert research.run_thread(c, "Q1P1") == "BLOCKED"
    assert research.status(c, "Q1P1")["reason"].startswith("frozen bundle changed: branch-2: ledger.jsonl")

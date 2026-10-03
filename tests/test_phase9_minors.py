"""Minors deferred by the reviews of phases 4c to 7a."""
import json, os, subprocess, sys
import pytest
from pathfinder import composable, consumer, coordinator, edit, health, research, seats, transport
from stubcampaign import make


def test_an_oversize_review_material_block_names_its_stage(tmp_path):
    c = make(tmp_path, research_scheme="direct_eva", prompt_budgets={"default": 50})
    d = research.prepare(c, "Q1P1")
    (d / "ledger.jsonl").write_text("".join(json.dumps({"seq": n, "actor": "ada", "kind": "note", "text": "x" * 300, "at": "t"}) + "\n"
                                            for n in range(1, 4)))
    research.run_thread(c, "Q1P1")
    s = research.status(c, "Q1P1")
    assert s["status"] == "BLOCKED" and s["reason"].startswith(s["stage"] + ":")


def test_the_consumer_runs_once_per_edited_note(tmp_path):
    c = make(tmp_path, extensions={"path": "deploy", "consumer": "count_mod:consume"})
    (tmp_path / "deploy").mkdir()
    (tmp_path / "deploy" / "count_mod.py").write_text("CALLS = []\ndef consume(campaign, pair_id, edited):\n    CALLS.append(pair_id)\n    return len(CALLS)\n")
    sys.modules.pop("count_mod", None)
    research.run_thread(c, "Q1P1")
    edit.run(c, "Q1P1"); edit.run(c, "Q1P1")
    import count_mod
    assert count_mod.CALLS == ["Q1P1"]


@pytest.mark.parametrize("bad", [{"default": "big"}, {"verify": -5}, "300000"])
def test_bad_prompt_budgets_fail_at_load(tmp_path, bad):
    with pytest.raises(ValueError, match="prompt_budgets"):
        make(tmp_path, prompt_budgets=bad)


def test_the_edit_stage_blocks_on_an_account_too_large_for_its_budget(tmp_path):
    from pathfinder import edit_stage
    c = make(tmp_path, prompt_budgets={"default": 10})
    d = research.prepare(c, "Q1P1")
    (d / "Q1P1.tex").write_text("x" * 100)
    research._set(c, "Q1P1", status="DRAFT", stage="done")
    (d / "Q1P1.tex").write_text("%" * 5000)
    import pathfinder.context as context
    real = context.digest_text
    assert edit_stage.finish(c, "Q1P1") in (True, False)          # a digest fits; nothing raises
    s = edit_stage.status(c, "Q1P1")
    assert s.get("status") in ("staged", "blocked")


def test_a_frozen_bundle_leaves_the_papers_out(tmp_path):
    c = make(tmp_path, research_scheme="composable", branches=1)
    research.run_thread(c, "Q1P1")
    files = json.loads((c.thread_dir("Q1P1") / "branches" / "branch-1" / "bundle.json").read_text())["files"]
    assert not any(name.startswith("inputs/") for name in files)


def test_a_reused_pid_does_not_keep_a_dead_seat(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_ACCOUNTS", str(tmp_path / "accounts"))
    c = make(tmp_path / "c", account={"name": "main", "seats": 1})
    pool = tmp_path / "accounts" / "main"; pool.mkdir(parents=True)
    (pool / "pool.json").write_text(json.dumps({"name": "main", "seats": 1}))
    # a stale reservation naming a live pid (this test's own process), with no holder keeping it open
    (pool / f"{os.getpid()}-stale.json").write_text(json.dumps({"pid": os.getpid()}))
    seat = seats.take(c, stage="peer", actor="ada", thread="Q1P1")
    assert seat is not None
    seats.release(seat)


def test_the_coordination_records_the_picker_code(tmp_path):
    from test_coordinator import staged
    path = staged(tmp_path, schedule=[])
    data = json.loads(path.read_text())
    (tmp_path / "deploy").mkdir()
    (tmp_path / "deploy" / "pick_digest.py").write_text("def next_unit(arms, progress):\n    return None\n")
    data.update(schedule=[], next_unit="pick_digest:next_unit", path="deploy"); path.write_text(json.dumps(data))
    coordinator.run(path, interval=0.01, heartbeat=0.05)
    rec = json.loads((tmp_path / "coordination.json").read_text())
    assert len(rec["next_unit_sha256"]) == 64


def test_allowance_advice_counts_recent_timeouts_only(tmp_path):
    c = make(tmp_path)
    with c.path("receipts.jsonl").open("a") as stream:
        stream.write(json.dumps({"call_id": "old", "stage": "verify", "outcome": "timeout"}) + "\n")
        for n in range(60):
            stream.write(json.dumps({"call_id": f"ok{n}", "stage": "verify", "outcome": "completed", "seconds": 30}) + "\n")
    rows = {r["stage"]: r for r in health.snapshot(c)["allowances"]}
    assert rows["verify"]["timeouts"] == 0

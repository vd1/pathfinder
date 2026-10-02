"""pathfinder coordinate: the repeat and reinjection pilot's semantics, on stub campaigns."""
import json, shutil
import pytest
from pathfinder import coordinator, edit, paper, research, runner, transport
from stubcampaign import make

needs_tex = pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
ARMS = ("repeat", "reinjection")


def staged(tmp_path, schedule=None, **overrides):
    for arm in ARMS:
        make(tmp_path / arm, pairs=("Q1P1", "Q1P2"), parent="..", **overrides)
    entries = schedule or [{"arm": a, "pair": p} for p in ("Q1P1",) for a in ARMS]
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps({"arms": {a: a for a in ARMS}, "schedule": entries}))
    return path


def _receipts(tmp_path, arm):
    from pathfinder import config
    return transport.receipts(config.load(tmp_path / arm))


def test_arms_must_name_the_parent(tmp_path):
    make(tmp_path / "repeat"); make(tmp_path / "reinjection", parent="..")
    (tmp_path / "schedule.json").write_text(json.dumps({"arms": {a: a for a in ARMS}, "schedule": []}))
    with pytest.raises(ValueError, match="parent"):
        coordinator.load(tmp_path / "schedule.json")


@needs_tex
def test_complete_schedule_then_resume_skips_finished_entries_in_order(tmp_path, monkeypatch):
    path = staged(tmp_path)
    state = coordinator.run(path, interval=0.05, heartbeat=0.05)
    assert state["status"] == "complete"
    outcomes = json.loads((tmp_path / "outcomes.json").read_text())
    assert {a: outcomes[a]["Q1P1"]["paper"]["status"] for a in ARMS} == {a: "ACCEPTED" for a in ARMS}
    before = {a: len(_receipts(tmp_path, a)) for a in ARMS}
    seen = []
    real = runner.run_pair
    monkeypatch.setattr(runner, "run_pair", lambda c, pair, **kw: seen.append(c.root.name) or real(c, pair, **kw))
    assert coordinator.run(path, interval=0.05, heartbeat=0.05)["status"] == "complete"
    assert seen == list(ARMS) and {a: len(_receipts(tmp_path, a)) for a in ARMS} == before     # nothing redone


@needs_tex
def test_budget_censoring_does_not_stop_the_other_arm(tmp_path):
    path = staged(tmp_path)
    (tmp_path / "repeat/stop.json").write_text(json.dumps({"reason": "budget: test cap"}))
    state = coordinator.run(path, interval=0.05, heartbeat=0.05)
    assert state["status"] == "censored" and state["censored_arms"] == ["repeat"]
    assert _receipts(tmp_path, "repeat") == [] and _receipts(tmp_path, "reinjection")


def test_a_parent_stop_halts_everything_and_is_not_cleared(tmp_path):
    path = staged(tmp_path)
    (tmp_path / "stop.json").write_text(json.dumps({"reason": "operator"}))
    state = coordinator.run(path, interval=0.05, heartbeat=0.05)
    assert state["status"] == "stopped" and (tmp_path / "stop.json").exists()
    assert all(_receipts(tmp_path, a) == [] for a in ARMS)


def test_an_operator_stop_in_an_arm_halts_everything(tmp_path):
    path = staged(tmp_path)
    (tmp_path / "reinjection/stop.json").write_text(json.dumps({"reason": "operator"}))
    state = coordinator.run(path, interval=0.05, heartbeat=0.05)
    assert state["status"] == "stopped" and "reinjection" in state["reason"]


@needs_tex
def test_a_research_failure_stops_before_the_next_entry(tmp_path, monkeypatch):
    path = staged(tmp_path)
    calls = []
    monkeypatch.setattr(runner, "run_pair", lambda c, pair, **kw: calls.append(c.root.name) or
                        {"code": 1, "research": "BLOCKED", "edit": "none", "paper": "none", "complete": False})
    with pytest.raises(RuntimeError, match="research or edit failed"):
        coordinator.run(path, interval=0.05, heartbeat=0.05)
    assert calls == ["repeat"] and json.loads((tmp_path / "progress.json").read_text())["status"] == "failed"


def test_an_unfinished_paper_stops_before_the_next_entry(tmp_path, monkeypatch):
    path = staged(tmp_path)
    monkeypatch.setattr(runner, "run_pair", lambda c, pair, **kw:
                        {"code": 0, "research": "DRAFT", "edit": "done", "paper": "blocked", "complete": False})
    with pytest.raises(RuntimeError, match="paper incomplete"):
        coordinator.run(path, interval=0.05, heartbeat=0.05)


def test_the_aggregated_snapshot_lists_every_arm(tmp_path):
    path = staged(tmp_path)
    snap = coordinator.snapshot(path)
    assert set(snap["arms"]) == set(ARMS) and snap["schedule_length"] == 2


def test_every_entry_is_validated_before_any_dispatch(tmp_path):
    path = staged(tmp_path, schedule=[{"arm": "repeat", "pair": "Q1P1"}, {"arm": "reinjection", "pair": "Q9P9"}])
    with pytest.raises(ValueError, match="not on the shortlist"):
        coordinator.run(path, interval=0.05, heartbeat=0.05)
    assert _receipts(tmp_path, "repeat") == []


@needs_tex
def test_a_changed_schedule_is_refused_until_accepted_and_child_runs_link_to_it(tmp_path):
    path = staged(tmp_path)
    first = coordinator.run(path, interval=0.05, heartbeat=0.05)
    child = json.loads((tmp_path / "repeat/run.json").read_text())
    assert child["links"]["coordination"]["coordination_id"] == first["coordination_id"]
    data = json.loads(path.read_text()); data["schedule"].reverse(); path.write_text(json.dumps(data))
    with pytest.raises(coordinator.ScheduleChanged):
        coordinator.run(path, interval=0.05, heartbeat=0.05)
    second = coordinator.run(path, interval=0.05, heartbeat=0.05, accept_change="order swapped on purpose")
    rec = json.loads((tmp_path / "coordination.json").read_text())
    assert rec["previous_coordination_id"] == first["coordination_id"] and rec["accepted_change"]["reason"]
    assert second["status"] == "complete"


@needs_tex
def test_coordinate_can_accept_a_child_record_change(tmp_path):
    path = staged(tmp_path)
    coordinator.run(path, interval=0.05, heartbeat=0.05)
    (tmp_path / "repeat/prompts").mkdir(); (tmp_path / "repeat/prompts/peer.append.md").write_text("new brief")
    from pathfinder import provenance
    with pytest.raises(provenance.ChangeRefused):
        coordinator.run(path, interval=0.05, heartbeat=0.05)
    assert coordinator.run(path, interval=0.05, heartbeat=0.05, accept_change="brief agreed")["status"] == "complete"


def _batch(tmp_path, batch, entries=None):
    path = staged(tmp_path, schedule=entries or [{"arm": "repeat", "pair": "Q1P1"}, {"arm": "repeat", "pair": "Q1P2"}])
    data = json.loads(path.read_text()); data["batch"] = batch; path.write_text(json.dumps(data))
    return path


def _fake_pairs(monkeypatch, outcomes, seen=None, sleep=0.0):
    import time
    def run_pair(c, pair, **kw):
        if seen is not None:
            seen.append(pair)
        time.sleep(sleep)
        ok = outcomes.pop(0)
        return {"code": 0 if ok else 1, "complete": ok, "research": "PAUSE", "edit": "done", "paper": None}
    monkeypatch.setattr(runner, "run_pair", run_pair)


def test_batch_deadline_stops_admitting_without_interrupting(tmp_path, monkeypatch):
    import datetime
    deadline = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=0.2)).isoformat()
    seen = []
    _fake_pairs(monkeypatch, [True, True], seen, sleep=0.4)
    state = coordinator.run(_batch(tmp_path, {"deadline": deadline}), interval=0.01, heartbeat=0.05)
    assert state["status"] == "deadline" and seen == ["Q1P1"]


def test_batch_unit_limit(tmp_path, monkeypatch):
    seen = []
    _fake_pairs(monkeypatch, [True, True], seen)
    state = coordinator.run(_batch(tmp_path, {"max_units": 1}), interval=0.01, heartbeat=0.05)
    assert state["status"] == "unit limit" and seen == ["Q1P1"]


def test_batch_tolerates_one_failed_entry_and_fails_on_two(tmp_path, monkeypatch):
    _fake_pairs(monkeypatch, [False, True])
    state = coordinator.run(_batch(tmp_path, {"max_consecutive_failures": 2}), interval=0.01, heartbeat=0.05)
    assert state["status"] == "complete" and len(state["failed_entries"]) == 1
    _fake_pairs(monkeypatch, [False, False])
    with pytest.raises(RuntimeError):
        coordinator.run(_batch(tmp_path / "again", {"max_consecutive_failures": 2}), interval=0.01, heartbeat=0.05)


def test_without_batch_the_first_failure_still_fails(tmp_path, monkeypatch):
    _fake_pairs(monkeypatch, [False, True])
    with pytest.raises(RuntimeError):
        coordinator.run(_batch(tmp_path, {}), interval=0.01, heartbeat=0.05)


def test_a_tolerated_failure_does_not_leave_the_arm_unhealthy_for_the_next_entry(tmp_path, monkeypatch):
    from pathfinder import health
    seen = []
    def run_pair(c, pair, **kw):
        seen.append(runner.unhealthy(c))
        if pair == "Q1P1":
            health.write(c.path("health.json"), {"pair": pair, "reason": "failed twice"})
            return {"code": 1, "complete": False, "research": "PAUSE", "edit": "done", "paper": None}
        return {"code": 0, "complete": True, "research": "PAUSE", "edit": "done", "paper": None}
    monkeypatch.setattr(runner, "run_pair", run_pair)
    state = coordinator.run(_batch(tmp_path, {"max_consecutive_failures": 2}), interval=0.01, heartbeat=0.05)
    assert seen == [False, False] and state["status"] == "complete"
    assert state["failed_entries"][0]["health"]["pair"] == "Q1P1"


def test_a_naive_deadline_is_utc(tmp_path, monkeypatch):
    import datetime
    later = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)).replace(tzinfo=None).isoformat()
    seen = []
    _fake_pairs(monkeypatch, [True, True], seen)
    assert coordinator.run(_batch(tmp_path, {"deadline": later}), interval=0.01, heartbeat=0.05)["status"] == "complete"


def _picker(tmp_path, body):
    (tmp_path / "deploy").mkdir(exist_ok=True)
    (tmp_path / "deploy" / f"picker_{tmp_path.name.replace('-', '_')}.py").write_text(body)
    return f"picker_{tmp_path.name.replace('-', '_')}:next_unit"


def _dynamic(tmp_path, body, batch=None):
    path = staged(tmp_path, schedule=[])
    data = json.loads(path.read_text())
    data.update(schedule=[], next_unit=_picker(tmp_path, body), path="deploy", batch=batch or {"max_consecutive_failures": 1})
    path.write_text(json.dumps(data))
    return path


QUEUE = """
QUEUE = [{"arm": "repeat", "pair": "Q1P1"}, {"arm": "reinjection", "pair": "Q1P2"}]
def next_unit(arms, progress):
    done = {(e["arm"], e["pair"]) for e in progress["done"]}
    return next((e for e in QUEUE if (e["arm"], e["pair"]) not in done), None)
"""


def test_next_unit_drives_the_coordination_until_it_returns_none(tmp_path, monkeypatch):
    seen = []
    _fake_pairs(monkeypatch, [True, True], seen)
    state = coordinator.run(_dynamic(tmp_path, QUEUE), interval=0.01, heartbeat=0.05)
    assert state["status"] == "complete" and seen == ["Q1P1", "Q1P2"]
    assert [(e["arm"], e["pair"]) for e in state["done"]] == [("repeat", "Q1P1"), ("reinjection", "Q1P2")]


def test_next_unit_respects_the_unit_limit(tmp_path, monkeypatch):
    seen = []
    _fake_pairs(monkeypatch, [True, True], seen)
    state = coordinator.run(_dynamic(tmp_path, QUEUE, {"max_units": 1}), interval=0.01, heartbeat=0.05)
    assert state["status"] == "unit limit" and seen == ["Q1P1"]


@pytest.mark.parametrize("body, reason", [
    ("def next_unit(arms, progress):\n    return {'arm': 'repeat', 'pair': 'Q1P1'}\n", "already"),
    ("def next_unit(arms, progress):\n    return {'arm': 'nowhere', 'pair': 'Q1P1'}\n", "arm"),
    ("def next_unit(arms, progress):\n    return {'arm': 'repeat', 'pair': 'Q9P9'}\n", "shortlist"),
])
def test_a_bad_next_unit_fails_the_coordination(tmp_path, monkeypatch, body, reason):
    _fake_pairs(monkeypatch, [True, True, True])
    with pytest.raises(RuntimeError, match=reason):
        coordinator.run(_dynamic(tmp_path, body), interval=0.01, heartbeat=0.05)


def test_the_schedule_digest_covers_the_next_unit_target(tmp_path):
    path = _dynamic(tmp_path, QUEUE)
    parent, arms, schedule = coordinator.load(path)
    assert coordinator.normalized(parent, arms, schedule)["next_unit"] == schedule["next_unit"]

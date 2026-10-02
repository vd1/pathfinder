import json, sys, threading, time
from pathlib import Path
import pytest
from pathfinder import admission, edit, extensions, research, runner, transport
from pathfinder.admission import Refused
from stubcampaign import make



def _request(stage="scan", actor="judge", cwd=None):
    return transport.ModelRequest(identity="t", prompt="p", model="m", tools=False, search=False,
                                  cwd=cwd, timeout=30, thread="Q1P1", stage=stage, actor=actor)


def _policy_module(root: Path, package: str, body: str):
    d = root / "deploy" / package; d.mkdir(parents=True)
    (d / "__init__.py").write_text(body)


def test_concurrent_admissions_respect_a_cap_of_one(tmp_path):
    c = make(tmp_path, extensions={"path": "deploy", "admission": "capone:policy"})
    _policy_module(tmp_path, "capone", "from pathfinder.admission import ADMIT, defer\n"
                   "def policy(c, stage, role, reserved):\n    return ADMIT if reserved == 0 else defer('cap', 0.05)\n")
    inside, peak, lock = [0], [0], threading.Lock()

    def work():
        with admission.admission(c, "scan", "judge"):
            with lock:
                inside[0] += 1; peak[0] = max(peak[0], inside[0])
            time.sleep(0.15)
            with lock:
                inside[0] -= 1

    threads = [threading.Thread(target=work) for _ in range(4)]
    for t in threads: t.start()
    for t in threads: t.join(5)
    assert peak[0] == 1 and admission.reserved(c) == 0


def test_a_failing_call_releases_its_reservation(tmp_path):
    c = make(tmp_path)
    with pytest.raises(RuntimeError):
        with admission.admission(c, "scan", "judge"):
            assert admission.reserved(c) == 1
            raise RuntimeError("provider failure")
    assert admission.reserved(c) == 0


def test_a_deferral_is_woken_by_a_parent_stop(tmp_path):
    parent = tmp_path / "parent"; parent.mkdir()
    c = make(parent / "arm", parent="..", extensions={"path": "deploy", "admission": "alwaysdefer:policy"})
    _policy_module(parent / "arm", "alwaysdefer", "from pathfinder.admission import defer\n"
                   "def policy(c, stage, role, reserved):\n    return defer('waiting', 5)\n")
    threading.Timer(0.3, lambda: (parent / "stop.json").write_text(json.dumps({"reason": "operator"}))).start()
    started = time.time()
    with pytest.raises(Refused, match="operator"):
        with admission.admission(c, "scan", "judge"):
            pass
    assert time.time() - started < 3 and admission.reserved(c) == 0


def test_repeated_refusals_make_no_call_reserve_nothing_and_cost_nothing(tmp_path, monkeypatch):
    c = make(tmp_path, backend="claude")
    monkeypatch.setenv("PATHFINDER_CLAUDE", str(tmp_path / "no-such-cli"))    # any real attempt would fail loudly
    runner.request_stop(c, "operator")
    for _ in range(3):
        with pytest.raises(Refused):
            transport.execute(c, _request(cwd=tmp_path))
    rows = transport.receipts(c)
    assert [r["outcome"] for r in rows] == ["refused"] * 3
    assert all(r["usage"] is None and r["cost"] is None for r in rows)
    assert transport.spend(c) == 0 and admission.reserved(c) == 0
    assert not list((tmp_path / "active-calls").glob("*.json")) if (tmp_path / "active-calls").exists() else True


def test_a_policy_stop_writes_the_marker_with_its_reason(tmp_path):
    c = make(tmp_path, extensions={"admission": "pathfinder.admission:budget_per_call"}, budget_usd=0.5,
             call_estimate_usd=1)
    with pytest.raises(Refused, match="budget"):
        transport.execute(c, _request(cwd=tmp_path))
    assert "budget" in json.loads((tmp_path / "stop.json").read_text())["reason"]


def test_same_module_name_from_two_deployments_is_rejected(tmp_path):
    a = make(tmp_path / "a", extensions={"path": "deploy", "admission": "clashpolicy:rule"})
    b = make(tmp_path / "b", extensions={"path": "deploy", "admission": "clashpolicy:rule"})
    _policy_module(tmp_path / "a", "clashpolicy", "rule = 'a'\n")
    _policy_module(tmp_path / "b", "clashpolicy", "rule = 'b'\n")
    assert extensions.load(a, "admission") == "a"
    with pytest.raises(ImportError, match="uniquely named"):
        extensions.load(b, "admission")


def test_uniquely_named_deployments_load_their_own_code(tmp_path):
    a = make(tmp_path / "a", extensions={"path": "deploy", "admission": "uniq_a:rule"})
    b = make(tmp_path / "b", extensions={"path": "deploy", "admission": "uniq_b:rule"})
    _policy_module(tmp_path / "a", "uniq_a", "rule = 'a'\n")
    _policy_module(tmp_path / "b", "uniq_b", "rule = 'b'\n")
    assert [extensions.load(a, "admission"), extensions.load(b, "admission")] == ["a", "b"]


def test_parent_stop_during_edit_is_a_stop_not_a_health_failure(tmp_path):
    """Research is DRAFT, the edit unfinished, the parent stops: the real wrappers, _work and _loop agree."""
    parent = tmp_path / "parent"; parent.mkdir()
    c = make(parent / "arm", parent="..")
    research.prepare(c, "Q1P1")
    research._set(c, "Q1P1", stage="done", status="DRAFT")
    (parent / "stop.json").write_text(json.dumps({"reason": "operator"}))
    assert runner.stopped(c)
    assert edit.run(c, "Q1P1", stop=lambda: False) == "stopped"          # admission refuses the editor call
    (parent / "stop.json").unlink()
    edit._set(c, "Q1P1", status="editing")
    # the marker appears only once the loop has admitted the pair, so _work's editor call is the one refused
    real_edit = edit._run
    def edit_after_stop(campaign, pair_id, stop):
        (parent / "stop.json").write_text(json.dumps({"reason": "operator"}))
        return real_edit(campaign, pair_id, stop)
    edit._run = edit_after_stop
    try:
        assert runner.run(c, interval=0.05) == 0
    finally:
        edit._run = real_edit
    assert not (c.root / "health.json").exists() and not (c.root / "failures.jsonl").exists()
    assert edit.status(c, "Q1P1")["status"] == "stopped"
    assert json.loads((c.root / "runner.json").read_text())["status"] == "stopped"


def test_snapshot_extra_cannot_replace_core_fields(tmp_path):
    from pathfinder import health
    c = make(tmp_path, extensions={"path": "deploy", "admission": "", "snapshot_extra": "snapextra_mod:extra"})
    _policy_module(tmp_path, "snapextra_mod", "def extra(c, snap):\n    snap['work'] = 'clobbered'\n"
                   "    return {'arms': 2}\n")
    snap = health.snapshot(c)
    assert snap["extensions"] == {"arms": 2} and snap["work"] != "clobbered"


def test_codex_search_as_configuration(tmp_path):
    c = make(tmp_path, backend="codex", codex={"search": "config"})
    live = transport._command(c, "m", True, True, tmp_path)
    off = transport._command(c, "m", True, False, tmp_path)
    assert 'web_search="live"' in live and "--search" not in live and 'web_search="disabled"' in off
    assert "--search" in transport._command(make(tmp_path / "flag", backend="codex"), "m", True, True, tmp_path)


def test_a_transport_extension_answers_inside_admission_and_engine_receipts(tmp_path):
    c = make(tmp_path, backend="claude", extensions={"path": "deploy", "transport": "hostdispatch_mod:execute"})
    _policy_module(tmp_path, "hostdispatch_mod",
                   "seen = []\n"
                   "def execute(campaign, request):\n"
                   "    seen.append((request.stage, request.actor))\n"
                   "    return {'text': 'answer', 'session': 'host-1', 'cost': 0.25}\n")
    r = transport.execute(c, _request(cwd=tmp_path))
    rows = transport.receipts(c)
    assert r["text"] == "answer" and r["outcome"] == "completed" and not r["transport_failed"]
    assert rows[-1]["outcome"] == "completed" and rows[-1]["cost"] == 0.25 and rows[-1]["cost_basis"] == "reported"
    assert admission.reserved(c) == 0 and not list((tmp_path / "active-calls").glob("*.json"))
    import hostdispatch_mod
    assert hostdispatch_mod.seen == [("scan", "judge")]


def test_a_failing_transport_extension_leaves_a_receipt_and_the_evidence(tmp_path):
    c = make(tmp_path, backend="claude", extensions={"path": "deploy", "transport": "hostfail_mod:execute"})
    _policy_module(tmp_path, "hostfail_mod", "def execute(campaign, request):\n    raise OSError('host down')\n")
    with pytest.raises(OSError):
        transport.execute(c, _request(cwd=tmp_path))
    assert transport.receipts(c)[-1]["outcome"] == "error" and admission.reserved(c) == 0
    assert list((tmp_path / "active-calls").glob("*.json"))          # the abrupt-exit evidence stays, as for any call


def test_quota_failure_stops_campaign_and_parent_and_keeps_first_reason(tmp_path, monkeypatch):
    from pathfinder import failures
    parent = tmp_path / "parent"; parent.mkdir()
    c = make(tmp_path / "arm", parent="../parent")
    quota = failures.classify("error", "You've hit your usage limit ... try again at Oct 4th, 2026 2:07 AM.")
    failures.stop_for(c, quota, "usage limit")
    first = json.loads((c.root / "stop.json").read_text())
    assert first["failure"]["class"] == "quota" and first["reason"].startswith("quota")
    assert json.loads((parent / "stop.json").read_text())["failure"]["reset_at"] == "Oct 4th, 2026 2:07 AM"
    failures.stop_for(c, failures.classify("error", "401 Unauthorized"), "401")
    assert json.loads((c.root / "stop.json").read_text()) == first
    with pytest.raises(Refused):
        with admission.admission(c, "peer", "ada"):
            pass


def test_call_scoped_failure_does_not_stop(tmp_path):
    from pathfinder import failures
    c = make(tmp_path)
    failures.stop_for(c, failures.classify("timeout", "timeout"), "timeout")
    assert not (c.root / "stop.json").exists()


def test_a_rate_limit_cools_the_whole_campaign_down(tmp_path):
    c = make(tmp_path, retry_backoff_seconds=0.4)
    transport._receipt(c, "Q1P1", "peer", "ada", "m", {"outcome": "error", "error": "HTTP 429 Too Many Requests"})
    assert 0 < admission.cooldown(c) <= 0.4
    started = time.time()
    with admission.admission(c, "peer", "emmy"):
        waited = time.time() - started
    assert waited >= 0.3


def test_a_cooldown_in_one_arm_holds_its_siblings_and_is_shown(tmp_path):
    from pathfinder import health
    (tmp_path / "parent").mkdir()
    arm1 = make(tmp_path / "arm1", parent="../parent", retry_backoff_seconds=5)
    arm2 = make(tmp_path / "arm2", parent="../parent", retry_backoff_seconds=5)
    transport._receipt(arm1, "Q1P1", "peer", "ada", "m", {"outcome": "error", "error": "HTTP 429 Too Many Requests"})
    assert admission.cooldown(arm2) > 0
    snap = health.snapshot(arm2)
    assert snap["cooldown"]["remaining_seconds"] > 0 and any("cooling down" in w for w in snap["warnings"])


def test_a_rate_limit_with_a_missing_parent_still_cools_the_campaign(tmp_path):
    c = make(tmp_path / "arm", parent="../missing-parent", retry_backoff_seconds=5)
    transport._receipt(c, "Q1P1", "peer", "ada", "m", {"outcome": "error", "error": "HTTP 429 Too Many Requests"})
    assert admission.cooldown(c) > 0 and not (tmp_path / "missing-parent").exists()

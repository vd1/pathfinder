"""Phase 6 review fixes: bundle integrity on every path, and every composable failure has a way out."""
import json, os
import pytest
from pathfinder import composable, config, playbook, reconcile, research, transport
from pathfinder.admission import Refused
from stubcampaign import make


def _c(tmp_path, **raw):
    return make(tmp_path, research_scheme="composable", **raw)


def _stop_once(monkeypatch, where):
    real, armed = transport.execute, {"on": True}

    def execute(campaign, request):
        if armed["on"] and where(request):
            armed["on"] = False
            raise Refused("stop requested")
        return real(campaign, request)
    monkeypatch.setattr(transport, "execute", execute)


def _frozen_then_stopped(tmp_path, monkeypatch, **raw):
    c = _c(tmp_path, **raw)
    d = c.thread_dir("Q1P1")
    _stop_once(monkeypatch, lambda r: str(r.cwd) == str(d))
    assert research.run_thread(c, "Q1P1") == "stopped"
    return c, d


def _rewrite(bundle, name, text, consistent=False):
    path = bundle / name
    os.chmod(path, 0o644); path.write_text(text)
    if consistent:                                 # patch the inventory too, as a careful forger would
        record_path = bundle / "bundle.json"; os.chmod(record_path, 0o644)
        record = json.loads(record_path.read_text())
        import hashlib
        record["files"][name] = {"sha256": hashlib.sha256(text.encode()).hexdigest(), "bytes": len(text.encode())}
        record_path.write_text(json.dumps(record))


def test_a_consistently_forged_inventory_is_caught(tmp_path, monkeypatch):
    c, d = _frozen_then_stopped(tmp_path, monkeypatch)
    _rewrite(d / "branches" / "branch-1", "ledger.jsonl", "forged\n", consistent=True)
    with pytest.raises(composable.BundleError):
        composable.verify(d / "branches" / "branch-1")
    assert research.run_thread(c, "Q1P1") == "BLOCKED"


def test_a_bundle_matching_itself_but_not_the_recorded_freeze_is_caught(tmp_path, monkeypatch):
    c, d = _frozen_then_stopped(tmp_path, monkeypatch)
    s = research.status(c, "Q1P1")
    research._set(c, "Q1P1", branches_frozen={**s["branches_frozen"], "branch-2": "0" * 64})
    assert research.run_thread(c, "Q1P1") == "BLOCKED"
    assert "branch-2" in research.status(c, "Q1P1")["reason"]


def test_reconcile_verifies_bundles_before_the_joint_thread(tmp_path, monkeypatch):
    c, d = _frozen_then_stopped(tmp_path, monkeypatch)
    _rewrite(d / "branches" / "branch-1", "ledger.jsonl", "planted\n")
    assert reconcile.apply(c, "Q1P1") == "BLOCKED"
    assert research.status(c, "Q1P1")["reason"].startswith("frozen bundle changed")


def test_a_restored_bundle_lifts_the_block(tmp_path, monkeypatch):
    c, d = _frozen_then_stopped(tmp_path, monkeypatch)
    path = d / "branches" / "branch-1" / "ledger.jsonl"
    original = path.read_text()
    _rewrite(d / "branches" / "branch-1", "ledger.jsonl", "planted\n")
    assert research.run_thread(c, "Q1P1") == "BLOCKED"
    _rewrite(d / "branches" / "branch-1", "ledger.jsonl", original)
    assert reconcile.inspect(c, "Q1P1")["action"] == "unblock: bundles verified"
    assert reconcile.apply(c, "Q1P1") == "DRAFT"


def test_changing_the_branch_count_after_the_freeze_is_refused(tmp_path, monkeypatch):
    c, d = _frozen_then_stopped(tmp_path, monkeypatch)
    raw = json.loads((tmp_path / "campaign.json").read_text()); raw["branches"] = 2
    (tmp_path / "campaign.json").write_text(json.dumps(raw))
    c = config.load(tmp_path)
    assert research.run_thread(c, "Q1P1") == "BLOCKED"
    assert "branches" in research.status(c, "Q1P1")["reason"]


def test_a_new_composable_pair_is_started_by_the_runner_not_the_apex(tmp_path):
    c = _c(tmp_path)
    assert reconcile.inspect(c, "Q1P1")["action"] == "start"
    assert not [a for a in playbook.next_actions(c) if a["action"].startswith("Q1P1")]


def test_a_branch_stopped_in_its_review_can_be_resumed(tmp_path, monkeypatch):
    c = _c(tmp_path)
    _stop_once(monkeypatch, lambda r: r.stage == "ledger_review" and str(r.cwd).endswith("branch-2"))
    assert research.run_thread(c, "Q1P1") == "stopped"
    assert reconcile.inspect(c, "Q1P1")["action"] == "branch-2: run review"
    assert reconcile.apply(c, "Q1P1") == "DRAFT"


def test_a_branch_whose_review_failed_in_transport_is_reissued(tmp_path, monkeypatch):
    c = _c(tmp_path)
    real, armed = transport.execute, {"on": True}

    def execute(campaign, request):
        r = real(campaign, request)
        if armed["on"] and request.stage == "ledger_review" and str(request.cwd).endswith("branch-2"):
            armed["on"] = False
            return {**r, "text": "", "transport_failed": True, "error": "timeout", "outcome": "timeout",
                    "failure": {"class": "timeout", "scope": "call", "retry": True, "reset_at": None}}
        return r
    monkeypatch.setattr(transport, "execute", execute)
    with pytest.raises(transport.TransportFailed):
        research.run_thread(c, "Q1P1")
    research.run_thread(c, "Q1P1")                   # the retained failed reply blocks the branch
    assert reconcile.inspect(c, "Q1P1")["action"] == "branch-2: " + reconcile.REISSUE
    assert reconcile.apply(c, "Q1P1") == "DRAFT"


def test_a_branch_evidence_block_reaches_the_playbook(tmp_path):
    c = _c(tmp_path, strict_evidence=True)
    b = composable.branch_view(c, "Q1P1", "branch-1")
    d = research.prepare(b, "Q1P1")
    from pathfinder.ledger import Ledger
    Ledger(d / "ledger.jsonl").add("ada", "finding", "see ada/missing.json")
    research.run_thread(c, "Q1P1")
    assert "evidence still blocked" in reconcile.inspect(c, "Q1P1")["action"]
    match = [a for a in playbook.next_actions(c) if a["action"].startswith("Q1P1")]
    assert match and match[0]["command"].endswith("evidence Q1P1")


def test_the_evidence_command_reads_the_view_that_owns_the_evidence(tmp_path):
    from pathfinder import evidence
    c = _c(tmp_path, strict_evidence=True)
    b = composable.branch_view(c, "Q1P1", "branch-1")
    d = research.prepare(b, "Q1P1")
    from pathfinder.ledger import Ledger
    Ledger(d / "ledger.jsonl").add("ada", "finding", "see ada/missing.json")
    research.run_thread(c, "Q1P1")
    view = composable.resolve(c, "Q1P1")
    assert view.thread_dir("Q1P1") == d
    assert any(e["path"] == "ada/missing.json" for e in evidence.manifest(view, "Q1P1")["errors"])


def test_a_freeze_failure_goes_to_the_operator(tmp_path):
    c = _c(tmp_path, branches=1)
    b = composable.branch_view(c, "Q1P1", "branch-1")
    research.prepare(b, "Q1P1")
    research.run_thread(b, "Q1P1")
    (b.thread_dir("Q1P1") / "ada" / "alias.txt").symlink_to(b.thread_dir("Q1P1") / "ledger.jsonl")
    assert research.run_thread(c, "Q1P1") == "BLOCKED"
    assert research.status(c, "Q1P1")["reason"].startswith("freeze: branch-1:")
    assert reconcile.inspect(c, "Q1P1")["action"].startswith("nothing: freeze failed")
    match = [a for a in playbook.next_actions(c) if a["action"].startswith("Q1P1")]
    assert match and match[0]["owner"] == "operator"


def test_branch_overrides_reach_resolved_fields(tmp_path):
    c = _c(tmp_path, branch={"model": "cheap", "peers": ["emmy"], "peer_search": False, "allowances": {"peer_calls": 1}})
    b = composable.branch_view(c, "Q1P1", "branch-1")
    assert b.model == "cheap" and b.peers == ("emmy",) and b.peer_search is False
    assert b.allowances["peer_calls"] == 1 and b.allowances["verify_seconds"] == c.allowances["verify_seconds"]
    assert b.raw["allowances"] == b.allowances


def test_an_override_block_must_be_an_object(tmp_path):
    with pytest.raises(ValueError, match="branch"):
        _c(tmp_path, branch="cheap")


def test_a_frozen_bundle_is_read_only_even_when_complete(tmp_path):
    import stat
    c = _c(tmp_path, branches=1)
    research.run_thread(c, "Q1P1")
    bundle = c.thread_dir("Q1P1") / "branches" / "branch-1"
    assert all(not os.stat(p).st_mode & stat.S_IWUSR for p in bundle.rglob("*") if p.is_file())

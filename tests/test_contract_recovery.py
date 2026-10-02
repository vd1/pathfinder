"""Phase 5 review fixes: recovery guarantees hold under contracts and budgets."""
import json
import pytest
from pathfinder import contracts, edit, paper, reconcile, research, transport
from pathfinder.admission import Refused
from stubcampaign import make


def _patch(monkeypatch, fn):
    monkeypatch.setattr(research.transport, "execute", fn)      # one module object: contracts sees it too


def test_replaying_a_retained_review_under_a_shrunk_ledger_is_not_stale(tmp_path):
    c = make(tmp_path, research_scheme="eva_minus", prompt_budgets={"default": 4000})
    d = research.prepare(c, "Q1P1")
    (d / "ledger.jsonl").write_text("".join(json.dumps({"seq": n, "actor": "ada", "kind": "note", "text": "x" * 100, "at": "t"}) + "\n"
                                            for n in range(1, 60)))
    research.run_thread(c, "Q1P1")
    ident = next(json.loads(f.read_text())["request"]["identity"] for f in (d / "research-requests").glob("*.json")
                 if json.loads(f.read_text())["request"]["stage"] == "ledger_review")
    research._set(c, "Q1P1", status="running", stage="ledger_review", pending=[ident], reviews=0, requests={})
    research.next_requests(c, "Q1P1")                       # a restart before the review transition was persisted
    assert research.status(c, "Q1P1").get("reason") != reconcile.STALE


def test_a_stop_during_a_composable_repair_keeps_the_paid_reply(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva_minus")
    real, calls, stop = transport.execute, [], {"on": True}

    def execute(campaign, request):
        calls.append(request.identity)
        if request.identity.endswith(":contract-repair") and stop["on"]:
            raise Refused("stop requested")
        r = real(campaign, request)
        return {**r, "text": "looks fine"} if request.stage == "ledger_review" and not request.identity.endswith("repair") else r
    _patch(monkeypatch, execute)
    assert research.run_thread(c, "Q1P1") == "stopped"
    review = [i for i in calls if ":ledger_review:" in i and not i.endswith("repair")]
    stop["on"] = False
    research.run_thread(c, "Q1P1")
    assert [i for i in calls if ":ledger_review:" in i and not i.endswith("repair")] == review   # not paid again
    assert research.status(c, "Q1P1")["status"] == "HANDOFF"


def test_a_stop_during_a_verifier_repair_keeps_the_paid_reply(tmp_path, monkeypatch):
    c = make(tmp_path)
    real, calls, stop = transport.execute, [], {"on": True}

    def execute(campaign, request):
        calls.append(request.identity)
        if request.identity.endswith(":contract-repair") and stop["on"]:
            raise Refused("stop requested")
        r = real(campaign, request)
        return {**r, "text": "the account is fine"} if request.stage == "verify" and not request.identity.endswith("repair") else r
    _patch(monkeypatch, execute)
    assert research.run_thread(c, "Q1P1") == "stopped"
    stop["on"] = False
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert len([i for i in calls if ":verify:" in i and not i.endswith("repair")]) == 1


def test_a_successful_repair_keeps_the_first_reply(tmp_path, monkeypatch):
    c = make(tmp_path)
    monkeypatch.setattr(contracts.transport, "execute", lambda campaign, request: {"transport_failed": False, "text": '{"decision": "DRAFT"}'})
    request = transport.ModelRequest(identity="Q1P1:verify:0", prompt="p", model="m", tools=True, search=False, timeout=60,
                                     thread="Q1P1", stage="verify", actor="verifier")
    value, result = contracts.ensure(c, request, {"transport_failed": False, "text": "it is fine"}, "verify")
    assert value["decision"] == "DRAFT" and result["first_text"] == "it is fine" and result["repaired"] is True


def test_a_repair_prompt_over_the_limit_is_a_contract_failure(tmp_path, monkeypatch):
    c = make(tmp_path)
    def refuse(campaign, request):
        raise transport.PromptTooLarge("input too large")
    monkeypatch.setattr(contracts.transport, "execute", refuse)
    request = transport.ModelRequest(identity="Q1P1:verify:0", prompt="p", model="m", tools=True, search=False, timeout=60,
                                     thread="Q1P1", stage="verify", actor="verifier")
    value, result = contracts.ensure(c, request, {"transport_failed": False, "text": "prose"}, "verify")
    assert value is None and result["failure"]["class"] == "contract"


def test_a_verdict_under_direct_eva_is_not_repaired_away(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva_minus")
    real, calls = transport.execute, []

    def execute(campaign, request):
        calls.append(request.identity)
        r = real(campaign, request)
        return {**r, "text": '{"decision": "PAUSE", "reason": "the question is closed"}'} if request.stage == "ledger_review" else r
    _patch(monkeypatch, execute)
    research.run_thread(c, "Q1P1")
    s = research.status(c, "Q1P1")
    assert not any(i.endswith(":contract-repair") for i in calls)
    assert s["status"] == "BLOCKED" and "EVA-minus requires a request review without a scientific verdict" in s["reason"]


def test_a_misconfigured_consumer_is_recorded_not_raised(tmp_path):
    c = make(tmp_path, extensions={"consumer": "no_such_module_here:consume"})
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    record = json.loads((c.thread_dir("Q1P1") / "consumer.json").read_text())
    assert record["status"] == "failed" and "no_such_module_here" in record["error"]


def test_a_paper_contract_block_resumes_at_the_review(tmp_path, monkeypatch):
    c = make(tmp_path)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    edit._set(c, "Q1P1", status="done")
    monkeypatch.setattr(paper, "_arxiv_titles", lambda ids: {})
    real_call, stages, prose = paper.transport.call, [], {"on": True}

    def call(prompt, **kw):
        stages.append(kw["stage"])
        r = real_call(prompt, **kw)
        return {**r, "text": "fine"} if kw["stage"] == "review" and prose["on"] else r
    monkeypatch.setattr(paper.transport, "call", call)
    real_execute = contracts.transport.execute
    monkeypatch.setattr(contracts.transport, "execute",
                        lambda campaign, request: {**real_execute(campaign, request), "text": "still fine"} if prose["on"] else real_execute(campaign, request))
    assert paper.run(c, "Q1P1") == "blocked"
    prose["on"] = False
    assert reconcile.inspect(c, "Q1P1")["action"] == "run paper"
    reconcile.apply(c, "Q1P1")
    assert stages == ["author", "review", "review"] and paper.status(c, "Q1P1")["status"] == "ACCEPTED"


def test_composable_consolidation_evidence_is_within_the_budget(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva", research_bundles=["b1"], inline_evidence=True, imported_research=True,
             prompt_budgets={"default": 8000})
    d = research.prepare(c, "Q1P1")
    (d / "b1").mkdir(exist_ok=True)
    (d / "b1" / "ledger.jsonl").write_text(json.dumps({"seq": 1, "actor": "ada", "kind": "finding", "text": "see b1/ada/big.txt", "at": "t"}) + "\n")
    seen = []
    real = transport.execute
    _patch(monkeypatch, lambda campaign, request: seen.append((request.stage, len(request.prompt))) or real(campaign, request))
    (d / "b1" / "ledger.jsonl").write_text("".join(json.dumps({"seq": n, "actor": "ada", "kind": "note", "text": "y" * 300, "at": "t"}) + "\n" for n in range(1, 80)))
    research.run_thread(c, "Q1P1")
    assert all(size <= 8000 for stage, size in seen if stage == "consolidate") and any(stage == "consolidate" for stage, _ in seen)


def test_non_finite_scores_break_the_contract():
    with pytest.raises(contracts.ContractViolation):
        contracts.parse("scan", '{"feasibility": NaN, "gain": 50}')

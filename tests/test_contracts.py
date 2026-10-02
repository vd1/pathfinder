"""Contracts over parsers: one declared schema per structured reply (D5, R4, H8)."""
import json
import pytest
from pathfinder import contracts, failures, stub


def test_extract_json_tolerates_tex_backslashes():
    assert contracts.extract_json('{"decision": "PAUSE", "reason": "the bound \\( e_s/\\delta \\) fails", "action": null}')["reason"].startswith("the bound")
    assert contracts.extract_json('{"a": "line\\nbreak", "b": 1}') == {"a": "line\nbreak", "b": 1}
    v = contracts.extract_json('{"decision": "ITERATE", "reason": "needs \\beta and \\upsilon and \\frac{1}{2}", "action": "x"}')
    assert v["reason"] == "needs \\beta and \\upsilon and \\frac{1}{2}"


def test_each_schema_accepts_the_stub_replies():
    assert contracts.parse("scan", json.dumps({"feasibility": 50, "gain": 50, "connexion": "stub", "rationale": "stub"}))
    assert contracts.parse("verify", json.dumps({"decision": "DRAFT", "reason": "stub verdict", "action": ""}))
    assert contracts.parse("paper_review", json.dumps({"decision": "ACCEPT", "summary": "stub review", "findings": []}))
    assert contracts.parse("request_review", json.dumps({"requests": [], "dispositions": []}))


def test_a_lower_case_decision_is_accepted():
    assert contracts.parse("verify", '{"decision": "draft"}')["decision"] == "DRAFT"


@pytest.mark.parametrize("name, reply, field", [
    ("verify", '{"reason": "x"}', "decision"),
    ("verify", '{"decision": "MAYBE"}', "decision"),
    ("request_review", '{"requests": "none", "dispositions": []}', "requests"),
    ("scan", '{"feasibility": 140, "gain": 3}', "feasibility"),
])
def test_violations_name_the_field(name, reply, field):
    with pytest.raises(contracts.ContractViolation) as caught:
        contracts.parse(name, reply)
    assert any(field in e for e in caught.value.errors)


def test_prose_is_not_a_reply():
    with pytest.raises(contracts.ContractViolation) as caught:
        contracts.parse("verify", "I think the draft is fine.")
    assert caught.value.errors[0].startswith("no readable JSON object")


def test_check_errors_are_violations():
    def check(value):
        raise ValueError("missing disposition for active requests: r1")
    with pytest.raises(contracts.ContractViolation) as caught:
        contracts.parse("request_review", '{"requests": [], "dispositions": []}', check=check)
    assert caught.value.errors == ["missing disposition for active requests: r1"]


def test_strict_closes_every_object_and_requires_every_property():
    s = contracts.strict(contracts.SCHEMAS["verify"])
    assert s["additionalProperties"] is False and set(s["required"]) == {"decision", "reason", "action"}
    assert "null" in s["properties"]["reason"]["type"]


def test_contract_is_a_call_scoped_failure_class():
    assert failures.SCOPES["contract"] == ("call", False)


# --- one repair turn ---------------------------------------------------------------------------------

from pathfinder import research, transport
from stubcampaign import make


def _request(stage="verify"):
    return transport.ModelRequest(identity="Q1P1:verify:0", prompt="judge it", model="stub", tools=True, search=False,
                                  timeout=60, thread="Q1P1", stage=stage, actor="verifier", reads=True)


def test_a_transport_failure_is_never_repaired(tmp_path, monkeypatch):
    c = make(tmp_path)
    monkeypatch.setattr(contracts.transport, "execute", lambda *a: pytest.fail("no repair call"))
    failed = {"transport_failed": True, "text": "", "failure": {"class": "timeout"}}
    assert contracts.ensure(c, _request(), failed, "verify") == (None, failed)


def test_a_violation_is_repaired_once_with_the_check(tmp_path, monkeypatch):
    c = make(tmp_path)
    asked = []

    def execute(campaign, request):
        asked.append(request)
        return {"transport_failed": False, "text": '{"requests": [], "dispositions": [{"id": "r1", "status": "deferred", "reason": "later"}]}'}
    monkeypatch.setattr(contracts.transport, "execute", execute)

    def check(value):
        if not value["dispositions"]:
            raise ValueError("missing disposition for active requests: r1")
    value, result = contracts.ensure(c, _request(), {"transport_failed": False, "text": '{"requests": [], "dispositions": []}'},
                                     "request_review", check=check)
    assert value["dispositions"][0]["id"] == "r1" and len(asked) == 1
    repair = asked[0]
    assert repair.identity == "Q1P1:verify:0:contract-repair" and repair.tools is False and repair.stage == "verify"
    assert "missing disposition for active requests: r1" in repair.prompt and '"dispositions": []' in repair.prompt


def test_two_violations_are_a_contract_failure(tmp_path, monkeypatch):
    c = make(tmp_path)
    monkeypatch.setattr(contracts.transport, "execute", lambda campaign, request: {"transport_failed": False, "text": "still prose"})
    value, result = contracts.ensure(c, _request(), {"transport_failed": False, "text": "prose"}, "verify")
    assert value is None and result["failure"]["class"] == "contract" and result["error"].startswith("contract: ")
    kinds = [json.loads(l)["kind"] for l in c.path("events.jsonl").read_text().splitlines()]
    assert "contract_repair" in kinds and "contract_failed" in kinds


def _prose_verifier(monkeypatch, times):
    real, seen = research.transport.execute, []

    judged = []

    def execute(campaign, request):
        seen.append(request.identity)
        result = real(campaign, request)
        if request.stage in ("verify", "ledger_review"):
            judged.append(request.identity)
            if len(judged) <= times:
                result = {**result, "text": "The account looks fine to me."}
        return result
    monkeypatch.setattr(research.transport, "execute", execute)
    monkeypatch.setattr(contracts.transport, "execute", execute)
    return seen


def test_the_verifier_reply_is_repaired_into_a_verdict(tmp_path, monkeypatch):
    c = make(tmp_path)
    seen = _prose_verifier(monkeypatch, 1)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert any(i.endswith(":contract-repair") for i in seen)


def test_a_verifier_that_never_answers_in_form_blocks_on_its_contract(tmp_path, monkeypatch):
    c = make(tmp_path)
    _prose_verifier(monkeypatch, 2)
    assert research.run_thread(c, "Q1P1") == "BLOCKED"
    s = research.status(c, "Q1P1")
    assert s["reason"].startswith("contract: verify:") and s["failure"]["class"] == "contract"


def test_a_composable_review_is_repaired_before_it_is_retained(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva_minus")
    seen = _prose_verifier(monkeypatch, 1)
    research.run_thread(c, "Q1P1")
    assert any(i.endswith(":contract-repair") for i in seen)
    assert not (research.status(c, "Q1P1").get("reason") or "").startswith("contract")


def test_a_composable_review_that_never_answers_in_form_blocks_on_its_contract(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva_minus")
    _prose_verifier(monkeypatch, 2)
    research.run_thread(c, "Q1P1")
    s = research.status(c, "Q1P1")
    assert s["status"] == "BLOCKED" and s["reason"].startswith("contract: review:") and s["failure"]["class"] == "contract"


def test_a_paper_review_in_prose_twice_blocks_on_its_contract(tmp_path, monkeypatch):
    from pathfinder import edit, paper
    c = make(tmp_path)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    edit._set(c, "Q1P1", status="done")
    monkeypatch.setattr(paper, "_arxiv_titles", lambda ids: {})
    real_call, real_execute = paper.transport.call, contracts.transport.execute
    monkeypatch.setattr(paper.transport, "call", lambda prompt, **kw: {**real_call(prompt, **kw), "text": "fine"} if kw["stage"] == "review" else real_call(prompt, **kw))
    monkeypatch.setattr(contracts.transport, "execute", lambda campaign, request: {**real_execute(campaign, request), "text": "still fine"})
    assert paper.run(c, "Q1P1") == "blocked"
    s = paper.status(c, "Q1P1")
    assert s["reason"].startswith("contract: review:") and s["failure"]["class"] == "contract"


def test_a_scan_reply_in_prose_is_repaired(tmp_path, monkeypatch):
    from pathfinder import scan
    c = make(tmp_path)
    real = scan.transport.execute
    calls = []

    def execute(campaign, request):
        calls.append(request.identity)
        result = real(campaign, request)
        return {**result, "text": "about fifty"} if len(calls) == 1 else result
    monkeypatch.setattr(scan.transport, "execute", execute)
    scan.run(c)
    row = json.loads(c.path("scan.jsonl").read_text().splitlines()[0])
    assert row["feasibility"] == 50 and row["error"] is None and calls[1].endswith(":contract-repair")

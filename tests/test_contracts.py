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

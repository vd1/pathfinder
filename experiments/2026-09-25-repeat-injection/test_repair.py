"""Deterministic repair tests; never call a model."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repair_verdict import decode


def test_actual_saved_response_preserves_decision_and_valid_escapes():
    raw = (Path(__file__).parent / "reinjection/threads/Q3P2/verify-unreadable.txt").read_text()
    corrected, verdict, count = decode(raw)
    assert verdict["decision"] == "PAUSE"
    assert verdict["action"] is None
    assert r"\(44.9\%\)" in verdict["reason"]
    assert r"\(k=11>10\)" in verdict["reason"]
    assert count == 6
    assert json.loads(corrected) == verdict


def test_valid_json_is_not_a_repair():
    with pytest.raises(ValueError):
        decode(json.dumps({"decision": "PAUSE", "reason": "already valid", "action": None}))


@pytest.mark.parametrize("decision", ["ITERATE", "REVISE", "UNKNOWN"])
def test_nonterminal_or_unknown_decisions_rejected(decision):
    with pytest.raises(ValueError):
        decode('{"decision":"' + decision + r'","reason":"\(x\)","action":null}')


def test_duplicate_decision_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        decode(r'{"decision":"PAUSE","decision":"DRAFT","reason":"\(x\)","action":null}')


def test_extra_fields_rejected():
    with pytest.raises(ValueError):
        decode(r'{"decision":"PAUSE","reason":"\(x\)","action":null,"extra":1}')


def test_missing_quote_not_repaired():
    with pytest.raises(ValueError):
        decode(r'{"decision":"PAUSE","reason":"\(x\),"action":null}')


def test_valid_quote_and_backslash_escapes_preserved():
    _, value, _ = decode(r'{"decision":"DRAFT","reason":"\(x\) and \"quote\" and \\alpha","action":null}')
    assert value["reason"] == '\\(x\\) and "quote" and \\alpha'

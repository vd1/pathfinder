"""Consolidation revisions and inline evidence, brought in from pathfinder-julien-2 (inventory rows J1 to J13)."""
import hashlib, json, os
import pytest
from pathfinder import research, transport
from pathfinder.ledger import Ledger
from stubcampaign import make

DOC = "\\documentclass{article}\\begin{document}\n%s\n\\end{document}\n"


def thread(tmp_path, **overrides):
    c = make(tmp_path, **overrides)
    d = research.prepare(c, "Q1P1")
    Ledger(d / "ledger.jsonl").add("ada", "finding", "a finding")
    return c, d


def drive(monkeypatch, replies, prompts=None):
    """Replace _stage_call with scripted replies per stage; record prompts and calls."""
    calls = []
    def stage_call(campaign, pair_id, stage, prompt, tools, seconds, done=lambda: False):
        calls.append(stage)
        if prompts is not None:
            prompts.setdefault(stage, []).append(prompt)
        reply = replies[stage].pop(0)
        return {"text": "", "error": None, "transport_failed": False, **reply}
    monkeypatch.setattr(research, "_stage_call", stage_call)
    return calls


def at_repair(c, d, old="old account"):
    (d / "Q1P1.tex").write_text(DOC % old)
    research._set(c, "Q1P1", stage="consolidate", repairs=1,
                  repair={"decision": "REVISE", "reason": "claim too strong", "action": "narrow the claim"})


def test_an_empty_repair_blocks_instead_of_reverifying_the_old_account(tmp_path, monkeypatch):
    c, d = thread(tmp_path); at_repair(c, d)
    calls = drive(monkeypatch, {"consolidate": [{"text": ""}]})
    assert research.run_thread(c, "Q1P1") == "BLOCKED"
    assert calls == ["consolidate"] and "old account" in (d / "Q1P1.tex").read_text()


def test_an_errored_repair_reply_is_not_an_account(tmp_path, monkeypatch):
    c, d = thread(tmp_path); at_repair(c, d)
    calls = drive(monkeypatch, {"consolidate": [{"text": DOC % "partial", "error": "no completed turn"}]})
    assert research.run_thread(c, "Q1P1") == "BLOCKED" and calls == ["consolidate"]
    assert "partial" not in (d / "Q1P1.tex").read_text()


def test_a_returned_repair_replaces_and_archives_the_account(tmp_path, monkeypatch):
    c, d = thread(tmp_path); at_repair(c, d)
    old = (d / "Q1P1.tex").read_bytes()
    prompts = {}
    drive(monkeypatch, {"consolidate": [{"text": DOC % "repaired"}],
                        "verify": [{"text": json.dumps({"decision": "DRAFT", "reason": "ok", "action": ""})}]}, prompts)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert "repaired" in (d / "Q1P1.tex").read_text()
    assert (d / "account-versions" / f"{hashlib.sha256(old).hexdigest()}.tex").read_bytes() == old
    assert "old account" in prompts["consolidate"][0]            # the tool-less consolidator sees what it repairs
    retained = json.loads((d / "consolidation/round-1-repair-1.json").read_text())
    assert "repaired" in retained["text"]


def test_a_restart_applies_the_retained_response_without_another_call(tmp_path, monkeypatch):
    c, d = thread(tmp_path); at_repair(c, d)
    (d / "consolidation").mkdir()
    (d / "consolidation/round-1-repair-1.json").write_text(json.dumps({"text": DOC % "retained"}))
    calls = drive(monkeypatch, {"verify": [{"text": json.dumps({"decision": "PAUSE", "reason": "r", "action": ""})}]})
    assert research.run_thread(c, "Q1P1") == "PAUSE"
    assert calls == ["verify"] and "retained" in (d / "Q1P1.tex").read_text()


def test_a_verifier_reply_with_an_error_is_not_read_as_a_verdict(tmp_path, monkeypatch):
    c, d = thread(tmp_path)
    (d / "Q1P1.tex").write_text(DOC % "account"); research._set(c, "Q1P1", stage="verify")
    calls = []
    def execute(campaign, request):
        calls.append(request.stage)
        return {"text": json.dumps({"decision": "DRAFT"}), "error": "stream cut", "transport_failed": False,
                "seconds": 0}
    monkeypatch.setattr(transport, "execute", execute)
    with pytest.raises(transport.TransportFailed):              # stopped and resumable, as a transport failure
        research.run_thread(c, "Q1P1")
    assert research.status(c, "Q1P1")["status"] == "stopped" and calls == ["verify"]
    assert not (d / "Q1P1.verdict.json").exists()


def test_stage_attempts_bound_retries_and_invalid_values_fail_first(tmp_path, monkeypatch):
    c, d = thread(tmp_path, stage_attempts=1); at_repair(c, d)
    calls = []
    monkeypatch.setattr(transport, "execute", lambda campaign, request: calls.append(1) or
                        {"text": "", "error": None, "transport_failed": False, "seconds": 0})
    assert research.run_thread(c, "Q1P1") == "BLOCKED" and len(calls) == 1
    bad, _ = thread(tmp_path / "bad", stage_attempts=0)
    with pytest.raises(ValueError, match="stage_attempts"):
        research.run_thread(bad, "Q1P1")


def test_assessors_read_evidence_with_tools_instead_of_inlining_it(tmp_path, monkeypatch):
    c, d = thread(tmp_path)
    (d / "ada/calc.py").write_text("print(42)  # peer calculation\n")
    (d / "work").mkdir(); (d / "work/out.txt").write_text("result 42\n")
    Ledger(d / "ledger.jsonl").add("ada", "finding", "see work/out.txt and missing/gone.txt")
    research._set(c, "Q1P1", stage="consolidate")
    calls = []
    def stage_call(campaign, pair_id, stage, prompt, tools, seconds, done=lambda: False):
        calls.append((stage, tools, prompt))
        text = DOC % "account" if stage == "consolidate" else json.dumps({"decision": "PAUSE", "reason": "r", "action": ""})
        return {"text": text, "error": None, "transport_failed": False}
    monkeypatch.setattr(research, "_stage_call", stage_call)
    assert research.run_thread(c, "Q1P1") == "PAUSE"
    assert [(stage, tools) for stage, tools, _ in calls] == [("consolidate", True), ("verify", True)]
    for _, _, prompt in calls:
        assert all(f"{peer}/" in prompt for peer in c.peers)
        assert "peer calculation" not in prompt and "result 42" not in prompt


def test_an_account_written_to_the_file_is_accepted(tmp_path, monkeypatch):
    c, d = thread(tmp_path)
    research._set(c, "Q1P1", stage="consolidate")
    def stage_call(campaign, pair_id, stage, prompt, tools, seconds, done=lambda: False):
        if stage == "consolidate":
            (d / "Q1P1.tex").write_text(DOC % "written by the consolidator")
            return {"text": "Done: wrote Q1P1.tex.", "error": None, "transport_failed": False}
        return {"text": '{"decision":"PAUSE"}', "error": None, "transport_failed": False}
    monkeypatch.setattr(research, "_stage_call", stage_call)
    assert research.run_thread(c, "Q1P1") == "PAUSE"
    assert "written by the consolidator" in (d / "Q1P1.tex").read_text()


@pytest.mark.parametrize("retained", ['{"text":', '{}', '{"text":null}', '{"text":"quota exceeded"}'])
def test_invalid_retained_response_blocks_without_replacing_account_or_calling_model(tmp_path, monkeypatch, retained):
    c, d = thread(tmp_path); at_repair(c, d)
    response = d / "consolidation/round-1-repair-1.json"
    response.parent.mkdir(); response.write_text(retained)
    calls = drive(monkeypatch, {})
    assert research.run_thread(c, "Q1P1") == "BLOCKED"
    assert calls == [] and "old account" in (d / "Q1P1.tex").read_text()
    assert response.read_text() == retained


def test_interrupted_account_replace_preserves_old_account_and_reuses_paid_response(tmp_path, monkeypatch):
    c, d = thread(tmp_path); at_repair(c, d)
    note = d / "Q1P1.tex"; old = note.read_bytes()
    calls = drive(monkeypatch, {"consolidate": [{"text": DOC % "replacement"}],
                               "verify": [{"text": '{"decision":"PAUSE"}'}]})
    replace = os.replace
    def interrupt(source, target):
        if target == note:
            raise OSError("simulated interruption before account replacement")
        return replace(source, target)
    monkeypatch.setattr(os, "replace", interrupt)
    with pytest.raises(OSError, match="simulated interruption"):
        research.run_thread(c, "Q1P1")
    assert note.read_bytes() == old
    assert (d / "account-versions" / f"{hashlib.sha256(old).hexdigest()}.tex").read_bytes() == old
    monkeypatch.setattr(os, "replace", replace)
    assert research.run_thread(c, "Q1P1") == "PAUSE"
    assert calls == ["consolidate", "verify"]
    assert "replacement" in note.read_text()

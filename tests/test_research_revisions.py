"""Consolidation revisions and inline evidence, brought in from pathfinder-julien-2 (inventory rows J1 to J13)."""
import hashlib, json, os
from pathlib import Path
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


def test_peer_files_and_cited_calculations_are_inlined_for_both_assessors(tmp_path, monkeypatch):
    c, d = thread(tmp_path)
    (d / "ada/calc.py").write_text("print(42)  # peer calculation\n")
    (d / "work").mkdir(); (d / "work/out.txt").write_text("result 42\n")
    Ledger(d / "ledger.jsonl").add("ada", "finding", "see work/out.txt; cf. doi 10.1234/abc.def and Nature/Fig.3")
    research._set(c, "Q1P1", stage="consolidate")
    prompts = {}
    drive(monkeypatch, {"consolidate": [{"text": DOC % "account"}],
                        "verify": [{"text": json.dumps({"decision": "PAUSE", "reason": "r", "action": ""})}]}, prompts)
    assert research.run_thread(c, "Q1P1") == "PAUSE"
    for stage in ("consolidate", "verify"):
        text = prompts[stage][0]
        assert "## ada/calc.py" in text and "peer calculation" in text and "## work/out.txt" in text
        assert "10.1234/abc.def\n" not in text and "## 10.1234" not in text and "## Nature/Fig.3" not in text


@pytest.mark.parametrize("make_alias", ["dotdot", "symlink"])
def test_evidence_aliases_block_before_any_call(tmp_path, monkeypatch, make_alias):
    c, d = thread(tmp_path)
    (tmp_path / "secret.txt").write_text("another investigation")
    if make_alias == "dotdot":
        Ledger(d / "ledger.jsonl").add("ada", "finding", "compare ada/../../../secret.txt")
    else:
        os.symlink(tmp_path / "secret.txt", d / "ada/link.txt")
    research._set(c, "Q1P1", stage="consolidate")
    calls = drive(monkeypatch, {})
    assert research.run_thread(c, "Q1P1") == "BLOCKED" and calls == []
    assert "evidence" in research.status(c, "Q1P1")["reason"]


def test_missing_and_binary_evidence_are_listed_or_block_in_strict_mode(tmp_path, monkeypatch):
    for strict in (False, True):
        c, d = thread(tmp_path / str(strict), strict_evidence=strict)
        (d / "ada/figure.png").write_bytes(b"\x89PNG\x00\xff")
        Ledger(d / "ledger.jsonl").add("ada", "finding", "see work/missing.txt")
        research._set(c, "Q1P1", stage="consolidate")
        prompts = {}
        drive(monkeypatch, {"consolidate": [{"text": DOC % "account"}],
                            "verify": [{"text": json.dumps({"decision": "PAUSE", "reason": "r", "action": ""})}]}, prompts)
        result = research.run_thread(c, "Q1P1")
        if strict:
            assert result == "BLOCKED" and "evidence" in research.status(c, "Q1P1")["reason"]
        else:
            assert result == "PAUSE"
            text = prompts["consolidate"][0]
            assert "no such file" in text and "not inlined: 6 bytes, sha256" in text


@pytest.mark.parametrize("strict", [False, True])
def test_unreadable_evidence_is_reported_without_an_unhandled_exception(tmp_path, monkeypatch, strict):
    c, d = thread(tmp_path, strict_evidence=strict); at_repair(c, d)
    evidence = d / "ada/calc.txt"; evidence.write_text("42")
    original = Path.read_bytes
    def read(path):
        if path == evidence:
            raise PermissionError("denied")
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", read)
    prompts = {}
    calls = drive(monkeypatch, {"consolidate": [{"text": DOC % "account"}],
                               "verify": [{"text": '{"decision":"PAUSE"}'}]}, prompts)
    assert research.run_thread(c, "Q1P1") == ("BLOCKED" if strict else "PAUSE")
    if strict:
        assert calls == [] and "unreadable evidence" in research.status(c, "Q1P1")["reason"]
    else:
        assert all("unreadable file" in prompts[stage][0] for stage in ("consolidate", "verify"))


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

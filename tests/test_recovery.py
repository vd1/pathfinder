import json

import pytest

from pathfinder import cli, health, recovery, research, runner, transport
from test_runner import make


RAW = r'{"decision":"PAUSE","reason":"The \(44.9\\%\) bound is conditional.","action":null}'


def blocked(tmp_path):
    c = make(tmp_path)
    d = c.thread_dir("Q1P1")
    health.write(d / "status.json", {"status": "BLOCKED", "stage": "verify", "round": 1,
                                   "reason": "verify: unreadable decision (escape)"})
    (d / "Q1P1.tex").write_text("Existing scientific note")
    (d / "verify-unreadable.txt").write_text(RAW)
    receipt = {"thread": "Q1P1", "stage": "verify", "model": "m", "outcome": "completed",
               "at": "2026-09-27T00:00:00Z", "raw_events": [json.dumps({"type": "result", "result": RAW})]}
    c.path("receipts.jsonl").write_text(json.dumps(receipt) + "\n")
    return c, d


def test_escape_repair_preserves_valid_pairs():
    fixed, verdict, count = recovery.decode_verdict(RAW)
    assert count == 2
    assert json.loads(fixed) == verdict
    assert verdict["reason"] == r"The \(44.9\%\) bound is conditional."


@pytest.mark.parametrize("raw", [
    RAW.replace('"PAUSE"', '"ITERATE"'), RAW.replace('"PAUSE"', '"REVISE"'),
    RAW.replace('"action":null', '"action":"invent a result"'),
    RAW.replace('"decision":"PAUSE"', '"decision":"PAUSE","decision":"DRAFT"'),
    RAW[:-1], '{"decision":"PAUSE","reason":"valid","action":null}',
])
def test_ambiguous_or_nonterminal_repairs_rejected(raw):
    with pytest.raises(ValueError):
        recovery.decode_verdict(raw)


def test_saved_judgment_repaired_without_model_or_note_changes(tmp_path, monkeypatch):
    c, d = blocked(tmp_path)
    before = {p.name: p.read_bytes() for p in [d / "Q1P1.tex", d / "verify-unreadable.txt", c.path("receipts.jsonl")]}
    monkeypatch.setattr(transport, "call", lambda *a, **k: pytest.fail("repair made a model call"))
    result = recovery.repair_verdict(c, "Q1P1")
    assert result["status"] == "repaired"
    assert research.status(c, "Q1P1")["status"] == "PAUSE"
    assert health.read(d / "Q1P1.verdict.json")[0]["at"] == "2026-09-27T00:00:00Z"
    assert (d / "Q1P1.tex").read_bytes() == before["Q1P1.tex"]
    assert (d / "verify-unreadable.txt").read_bytes() == before["verify-unreadable.txt"]
    assert c.path("receipts.jsonl").read_bytes() == before["receipts.jsonl"]
    assert len(c.path("supervision/incidents.jsonl").read_text().splitlines()) == 2
    assert "Q1P1" in runner.pending(c)  # Editing remains pending, not another investigation.
    with pytest.raises(ValueError):
        recovery.repair_verdict(c, "Q1P1")


def test_stops_and_live_owners_prevent_repair(tmp_path):
    c, _ = blocked(tmp_path)
    health.write(c.path("stop.json"), {"reason": "operator"})
    with pytest.raises(RuntimeError, match="Stop"):
        recovery.repair_verdict(c, "Q1P1")
    c.path("stop.json").unlink()
    with health.owner(c), pytest.raises(RuntimeError, match="already owns"):
        recovery.repair_verdict(c, "Q1P1")


def test_receipt_mismatch_and_duplicate_round_refused(tmp_path):
    c, d = blocked(tmp_path)
    (d / "verify-unreadable.txt").write_text(RAW.replace("conditional", "different"))
    with pytest.raises(ValueError, match="receipt"):
        recovery.repair_verdict(c, "Q1P1")
    (d / "verify-unreadable.txt").write_text(RAW)
    health.write(d / "Q1P1.verdict.json", [{"round": 1, "decision": "DRAFT"}])
    with pytest.raises(ValueError, match="already has"):
        recovery.repair_verdict(c, "Q1P1")


def test_cli_uses_explicit_repair_command(tmp_path, capsys):
    c, _ = blocked(tmp_path)
    health.write(c.path("campaign.json"), {"backend": "claude", "model": "m", "allowances": {}, "budget_usd": 10})
    cli.main(["--root", str(tmp_path), "repair-verdict", "Q1P1"])
    assert json.loads(capsys.readouterr().out)["decision"] == "PAUSE"

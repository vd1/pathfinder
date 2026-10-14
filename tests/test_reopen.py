"""Reopening a finished thread with a bounded grant (nobel, 14 October 2026): `pathfinder reopen PAIR --grant
repair|round --reason TEXT [--note TEXT]` gives a PAUSE-ON-REVISE thread one more repair, or a PAUSE-ON-ITERATE or
PAUSE thread one more peer round; the next verdict ends the thread whatever it decides. The reopen is recorded
in the thread with the engine of that moment; verdicts, ledger and novelty reports are appended to, and the
earlier edit is kept under reopened/<n>/ so the new outcome is edited afresh. A DRAFT is never reopened."""
import json
import pytest
from pathfinder import config, edit, reopen, research, runner, stub, transport
from pathfinder.ledger import Ledger
from stubcampaign import make


def _finished(tmp_path, verdict, **raw):
    c = make(tmp_path, research_scheme="eva", stub={"verify": verdict}, **raw)
    assert research.run_thread(c, "Q1P1") == {"REVISE": "PAUSE-ON-REVISE", "ITERATE": "PAUSE-ON-ITERATE"}.get(verdict, verdict)
    ed = c.thread_dir("Q1P1") / "edited"; ed.mkdir()
    (ed / "edit.json").write_text(json.dumps({"status": "done"})); (ed / "note.tex").write_text("old edit")
    (c.thread_dir("Q1P1") / "actionability.json").write_text(json.dumps({"status": "done"}))
    return c


def _verdict(c, decision):
    raw = json.loads(c.path("campaign.json").read_text()); raw["stub"] = {"verify": decision}
    c.path("campaign.json").write_text(json.dumps(raw))
    return config.load(c.root)


def _seen(monkeypatch, notes=None):
    seen, real = [], transport.execute
    def execute(campaign, request):
        seen.append(request)
        r = real(campaign, request)
        if request.stage == "consolidate" and notes:
            r = {**r, "text": notes.pop(0)}
        return r
    monkeypatch.setattr(transport, "execute", execute)
    return seen


def _records(c):
    return json.loads((c.thread_dir("Q1P1") / "Q1P1.reopen.json").read_text())


def test_a_repair_grant_consolidates_with_the_last_action_then_verifies(tmp_path, monkeypatch):
    c = _finished(tmp_path, "REVISE", repairs=1)
    verdicts = json.loads((c.thread_dir("Q1P1") / "Q1P1.verdict.json").read_text())
    out = reopen.reopen(c, "Q1P1", "repair", reason="attribution only")
    assert out["n"] == 1 and out["from"]["status"] == "PAUSE-ON-REVISE"
    s = research.status(c, "Q1P1")
    assert (s["status"], s["stage"], s["grant"]["grant"]) == ("running", "consolidate", "repair")
    assert s["repair"]["action"] == verdicts[-1]["action"]
    rec = _records(c)[0]
    assert rec["reason"] == "attribution only" and rec["grant"] == "repair" and rec["engine"]["runtime_sha256"]
    d = c.thread_dir("Q1P1")
    assert not (d / "edited").exists() and (d / "reopened/1/edited/note.tex").read_text() == "old edit"
    assert (d / "reopened/1/actionability.json").exists() and edit.status(c, "Q1P1")["status"] == "none"
    c = _verdict(c, "DRAFT")
    seen = _seen(monkeypatch, notes=[stub.NOTE + "\nWith the citation.\n"])
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert [r.stage for r in seen] == ["consolidate", "verify"]
    assert "Repair the existing account" in seen[0].prompt and verdicts[-1]["action"] in seen[0].prompt
    after = json.loads((d / "Q1P1.verdict.json").read_text())
    assert after[:len(verdicts)] == verdicts and len(after) == len(verdicts) + 1
    assert "grant" not in research.status(c, "Q1P1") or research.status(c, "Q1P1")["grant"] is None


@pytest.mark.parametrize("decision, ending", [("REVISE", "PAUSE-ON-REVISE"), ("ITERATE", "PAUSE-ON-ITERATE")])
def test_the_verdict_after_a_grant_ends_the_thread(tmp_path, monkeypatch, decision, ending):
    c = _finished(tmp_path, "REVISE", repairs=1, rounds=3)
    reopen.reopen(c, "Q1P1", "repair", reason="one more repair")
    c = _verdict(c, decision)
    seen = _seen(monkeypatch, notes=[stub.NOTE + "\nchanged\n"])
    assert research.run_thread(c, "Q1P1") == ending
    assert [r.stage for r in seen] == ["consolidate", "verify"]


def test_a_round_grant_runs_one_peer_round_from_the_last_action(tmp_path, monkeypatch):
    c = _finished(tmp_path, "ITERATE", rounds=1)
    before = research.status(c, "Q1P1")["round"]
    reopen.reopen(c, "Q1P1", "round", reason="the gap is closable")
    s = research.status(c, "Q1P1")
    assert (s["stage"], s["round"], s["peer_call"], s["peer_seconds"]) == ("peers", before + 1, 0, 0)
    c = _verdict(c, "ITERATE")
    seen = _seen(monkeypatch)
    assert research.run_thread(c, "Q1P1") == "PAUSE-ON-ITERATE"
    assert [r.stage for r in seen][0] == "peer" and [r.stage for r in seen][-2:] == ["consolidate", "verify"]


def test_a_paused_thread_reopens_with_the_operators_note_in_the_ledger(tmp_path, monkeypatch):
    c = _finished(tmp_path, "PAUSE")
    with pytest.raises(ValueError, match="--note"):
        reopen.reopen(c, "Q1P1", "round", reason="data supplied")
    reopen.reopen(c, "Q1P1", "round", reason="data supplied", note="The dataset is now in sources/extra.csv.")
    rows = Ledger(c.thread_dir("Q1P1") / "ledger.jsonl").read()
    assert (rows[-1]["actor"], rows[-1]["kind"]) == ("operator", "operator")
    assert _records(c)[0]["ledger_seq"] == rows[-1]["seq"]
    c = _verdict(c, "DRAFT")
    seen = _seen(monkeypatch)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert "sources/extra.csv" in next(r for r in seen if r.stage == "peer").prompt


@pytest.mark.parametrize("verdict, grant, message", [
    ("DRAFT", "round", "DRAFT"), ("REVISE", "round", "repair"), ("ITERATE", "repair", "round"), ("PAUSE", "repair", "round")])
def test_a_grant_that_does_not_fit_the_ending_is_refused(tmp_path, verdict, grant, message):
    c = _finished(tmp_path, verdict, repairs=0 if verdict == "REVISE" else 1, rounds=1)
    with pytest.raises(ValueError, match=message):
        reopen.reopen(c, "Q1P1", grant, reason="r", note="n")
    assert not (c.thread_dir("Q1P1") / "Q1P1.reopen.json").exists()


def test_a_reason_is_required_and_a_held_thread_is_refused(tmp_path):
    c = _finished(tmp_path, "REVISE", repairs=0)
    with pytest.raises(ValueError, match="reason"):
        reopen.reopen(c, "Q1P1", "repair", reason="  ")
    with runner.Lock(c.thread_dir("Q1P1")):
        with pytest.raises(RuntimeError, match="held"):
            reopen.reopen(c, "Q1P1", "repair", reason="r")
    reopen.reopen(c, "Q1P1", "repair", reason="r")
    with pytest.raises(ValueError, match="running"):           # one grant per call: a reopened thread is not finished
        reopen.reopen(c, "Q1P1", "repair", reason="again")


def test_a_pair_no_longer_on_the_shortlist_is_listed_again_and_runs(tmp_path):
    c = _finished(tmp_path, "REVISE", repairs=0)
    c.path("shortlist.json").write_text(json.dumps({"pairs": []}))
    reopen.reopen(c, "Q1P1", "repair", reason="left the cut")
    listed = json.loads(c.path("shortlist.json").read_text())["pairs"]
    assert listed == [{"pair_id": "Q1P1", "reopened": True}]
    assert runner._validate_selection(c, ["Q1P1"]) == ["Q1P1"]


def test_status_and_playbook_show_the_grant(tmp_path):
    from pathfinder import campaign_state, playbook
    c = _finished(tmp_path, "REVISE", repairs=0)
    reopen.reopen(c, "Q1P1", "repair", reason="attribution only")
    state = campaign_state.build(c)
    u = state["units"][0]
    assert u["reopened"] == [{"n": 1, "at": u["reopened"][0]["at"], "grant": "repair", "reason": "attribution only"}]
    assert "reopened 1 (repair)" in campaign_state.text(state)
    actions = playbook.next_actions(c)
    assert any("Q1P1: reopened" in a["action"] and "--pairs Q1P1" in (a["command"] or "") for a in actions)


def test_a_composable_joint_thread_reopens_after_collection_and_runs(tmp_path, monkeypatch):
    from pathfinder import gc
    c = make(tmp_path, research_scheme="composable", branches=1, repairs=0, stub={"verify": "REVISE"})
    assert research.run_thread(c, "Q1P1") == "PAUSE-ON-REVISE"
    ed = c.thread_dir("Q1P1") / "edited"; ed.mkdir(); (ed / "edit.json").write_text(json.dumps({"status": "done"}))
    assert gc.collect_thread(c, "Q1P1") is not None
    reopen.reopen(c, "Q1P1", "repair", reason="attribution only")
    c = _verdict(c, "DRAFT")
    seen = _seen(monkeypatch, notes=[stub.NOTE + "\nfixed\n"])
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert [r.stage for r in seen] == ["consolidate", "verify"]

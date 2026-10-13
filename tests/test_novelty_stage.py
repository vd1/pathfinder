"""A novelty stage between consolidate and verify (nobel, NEVA): with "novelty_stage": true one fresh call with web
search reads the note, the two abstracts and an optional list of citers, and its JSON report goes into verify's
prompt as evidence; it runs again when the note changes, and a failed check never blocks verify."""
import json
import pytest
from pathfinder import research, stub, transport
from stubcampaign import make

REPORT = {"results": [{"result": "the main bound", "status": "partly_known", "closest": "arXiv:2404.03644",
                       "note": "same bound under another name"}],
          "missing": ["arXiv:2404.03644"], "overclaims": [], "queries": ["block encoding rounding bound"]}


def _seen(monkeypatch, novelty=None, notes=None):
    """Every request in order; novelty(request) replaces the novelty call's result, notes the consolidations' texts."""
    seen, real, n = [], transport.execute, {"consolidate": 0}
    def execute(campaign, request):
        seen.append(request)
        if request.stage == "novelty" and novelty is not None:
            return novelty(request)
        r = real(campaign, request)
        if request.stage == "consolidate" and notes:
            r = {**r, "text": notes[min(n["consolidate"], len(notes) - 1)]}; n["consolidate"] += 1
        return r
    monkeypatch.setattr(transport, "execute", execute)
    return seen


def _record(c):
    return json.loads((c.thread_dir("Q1P1") / "Q1P1.novelty.json").read_text())


def test_without_the_setting_there_is_no_novelty_call(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva")
    seen = _seen(monkeypatch)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert "novelty" not in [r.stage for r in seen]


def test_the_check_runs_between_consolidate_and_verify_and_its_report_reaches_verify(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva", novelty_stage=True, routes={"novelty": {"model": "opus-like"}})
    monkeypatch.setattr(stub, "reply", lambda campaign, request, real=stub.reply: json.dumps(REPORT)
                        if request.stage == "novelty" else real(campaign, request))
    seen = _seen(monkeypatch)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    stages = [r.stage for r in seen if r.stage != "peer"]
    assert stages == ["consolidate", "novelty", "verify"]
    n = next(r for r in seen if r.stage == "novelty")
    assert (n.actor, n.tools, n.reads, n.search, n.timeout) == ("novelty", True, True, True, 900)
    assert "Abstract of Q1" in n.prompt and "Abstract of P1" in n.prompt and stub.NOTE[:40] in n.prompt
    assert "stub finding by ada" not in n.prompt                      # neither the ledger nor the full papers
    v = next(r for r in seen if r.stage == "verify")
    assert "arXiv:2404.03644" in v.prompt and "Treat it as evidence" in v.prompt
    rec = _record(c)
    assert len(rec) == 1 and rec[0]["report"] == REPORT and rec[0]["note_sha256"]
    assert research.status(c, "Q1P1")["novelty"]["status"] == "ok"
    assert [r["model"] for r in transport.receipts(c) if r.get("stage") == "novelty"] == ["opus-like"]


def test_a_deployment_list_of_citers_is_given_to_the_check(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva", novelty_stage=True, novelty_citers="citers/{pair}.md",
             allowances={"peer_seconds": 600, "peer_calls": 2, "consolidate_seconds": 60, "verify_seconds": 60,
                         "novelty_seconds": 300})
    (c.root / "citers").mkdir(); (c.root / "citers/Q1P1.md").write_text("Citing both: Smith 2025, arXiv:2501.00001\n")
    seen = _seen(monkeypatch)
    research.run_thread(c, "Q1P1")
    n = next(r for r in seen if r.stage == "novelty")
    assert "Smith 2025" in n.prompt and n.timeout == 300


def test_a_missing_citers_file_is_said_not_fatal(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva", novelty_stage=True, novelty_citers="citers/{pair}.md")
    seen = _seen(monkeypatch)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert "no list of citers" in next(r for r in seen if r.stage == "novelty").prompt


@pytest.mark.parametrize("result", [
    {"text": "", "seconds": 1.0, "transport_failed": True, "error": "timeout", "failure": {"class": "timeout", "scope": "call", "retry": True}},
    {"text": "I could not decide.", "seconds": 1.0, "transport_failed": False}])
def test_a_failed_or_unreadable_check_does_not_block_verify(tmp_path, monkeypatch, result):
    c = make(tmp_path, research_scheme="eva", novelty_stage=True)
    seen = _seen(monkeypatch, novelty=lambda request: result)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert [r.stage for r in seen if r.stage != "peer"] == ["consolidate", "novelty", "verify"]
    v = next(r for r in seen if r.stage == "verify")
    assert "novelty check" in v.prompt and "no report" in v.prompt
    rec = _record(c)
    assert rec[0]["report"] is None and rec[0]["error"]
    assert research.status(c, "Q1P1")["novelty"]["status"] == "failed"


def test_the_check_runs_again_only_when_the_note_changes(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="eva", novelty_stage=True, repairs=2, stub={"verify": "REVISE"})
    seen = _seen(monkeypatch, notes=[stub.NOTE, stub.NOTE, stub.NOTE + "\nA corrected sentence.\n"])
    assert research.run_thread(c, "Q1P1") == "PAUSE-ON-REVISE"
    assert [r.stage for r in seen if r.stage != "peer"] == [
        "consolidate", "novelty", "verify", "consolidate", "verify", "consolidate", "novelty", "verify"]
    assert len(_record(c)) == 2
    verifies = [r for r in seen if r.stage == "verify"]
    assert all("Novelty check" in v.prompt for v in verifies)          # the report for the unchanged note is reused


@pytest.mark.parametrize("raw, message", [({"novelty_stage": "yes"}, "novelty_stage must be true or false"),
                                          ({"novelty_stage": True}, "novelty_stage needs"),
                                          ({"novelty_stage": True, "research_scheme": "eva", "novelty_citers": 3}, "novelty_citers")])
def test_bad_novelty_settings_are_refused(tmp_path, raw, message):
    with pytest.raises(ValueError, match=message):
        make(tmp_path, **raw)


def test_in_a_composable_campaign_only_the_joint_thread_checks(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="composable", branches=1, novelty_stage=True)
    seen = _seen(monkeypatch)
    research.run_thread(c, "Q1P1")
    novelty = [r for r in seen if r.stage == "novelty"]
    assert len(novelty) == 1 and novelty[0].cwd == c.thread_dir("Q1P1")
    assert (c.thread_dir("Q1P1") / "Q1P1.novelty.json").exists()

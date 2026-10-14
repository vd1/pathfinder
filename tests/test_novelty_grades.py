"""Graded novelty findings (nobel, 14 October 2026): every missing work and overclaim the check reports is
essential (it changes or limits the novelty or scope of a result the note presents as new) or background; the
verifier decides REVISE on essential items only; and a repaired note is checked against the previous report,
which the check receives, so each repair does not meet a fresh list."""
import json
import pytest
from pathfinder import contracts, research, stub, transport
from stubcampaign import make

GRADED = {"results": [{"result": "the bound", "status": "partly_known", "closest": "arXiv:2404.03644", "note": "n"}],
          "missing": [{"work": "arXiv:2404.03644", "why": "same bound", "grade": "essential"},
                      {"work": "arXiv:1111.11111", "why": "general survey", "grade": "background"}],
          "overclaims": [{"claim": "first such bound", "support": "2404.03644 has it", "grade": "essential"}],
          "queries": ["q"]}


def test_the_report_must_grade_every_missing_work_and_overclaim():
    assert contracts.parse("novelty", json.dumps(GRADED))["missing"][1]["grade"] == "background"
    old = {**GRADED, "missing": ["arXiv:2404.03644: same bound"]}
    with pytest.raises(contracts.ContractViolation, match="missing"):
        contracts.parse("novelty", json.dumps(old))
    ungraded = {**GRADED, "overclaims": [{"claim": "c", "support": "s"}]}
    with pytest.raises(contracts.ContractViolation, match="grade"):
        contracts.parse("novelty", json.dumps(ungraded))
    assert contracts.parse("novelty", json.dumps({**GRADED, "missing": [], "overclaims": []}))["missing"] == []


def _run(tmp_path, monkeypatch, reports):
    c = make(tmp_path, research_scheme="eva", novelty_stage=True, repairs=1, stub={"verify": "REVISE"})
    seen, real, n = [], transport.execute, {"consolidate": 0, "novelty": 0}
    def execute(campaign, request):
        seen.append(request)
        if request.stage == "novelty":
            n["novelty"] += 1
            return {**real(campaign, request), "text": json.dumps(reports[n["novelty"] - 1])}
        r = real(campaign, request)
        if request.stage == "consolidate":
            n["consolidate"] += 1
            r = {**r, "text": stub.NOTE + "\n" * n["consolidate"]}       # each repair changes the note
        return r
    monkeypatch.setattr(transport, "execute", execute)
    research.run_thread(c, "Q1P1")
    return [r for r in seen if r.stage == "novelty"], [r for r in seen if r.stage == "verify"]


def test_a_repaired_note_is_checked_against_the_previous_report(tmp_path, monkeypatch):
    second = {**GRADED, "missing": [], "overclaims": [],
              "previous": [{"item": "arXiv:2404.03644", "addressed": True, "note": "now cited"}]}
    checks, verifies = _run(tmp_path, monkeypatch, [GRADED, second])
    assert len(checks) == 2
    assert "## your previous report" not in checks[0].prompt
    assert "## your previous report" in checks[1].prompt and "arXiv:1111.11111" in checks[1].prompt
    assert '"addressed": true' in verifies[1].prompt


def test_the_verifier_is_told_to_revise_on_essential_items_only(tmp_path, monkeypatch):
    _, verifies = _run(tmp_path, monkeypatch, [GRADED, GRADED])
    p = verifies[0].prompt
    assert "essential" in p and "Background items alone never call for REVISE" in p


def test_the_check_is_asked_to_grade_and_may_report_nothing(tmp_path, monkeypatch):
    checks, _ = _run(tmp_path, monkeypatch, [GRADED, GRADED])
    p = checks[0].prompt
    assert '"grade": "essential|background"' in p and "Empty lists are a valid outcome" in p
    assert "already concedes" in p


def test_each_record_keeps_the_grade_counts_beside_the_verdict(tmp_path, monkeypatch):
    second = {**GRADED, "missing": [], "overclaims": [{"claim": "c", "support": "s", "grade": "background"}]}
    _run(tmp_path, monkeypatch, [GRADED, second])
    d = tmp_path / "threads" / "Q1P1"
    records = json.loads((d / "Q1P1.novelty.json").read_text())
    assert records[0]["counts"] == {"missing": {"essential": 1, "background": 1}, "overclaims": {"essential": 1, "background": 0}}
    assert records[1]["counts"] == {"missing": {"essential": 0, "background": 0}, "overclaims": {"essential": 0, "background": 1}}
    verdicts = json.loads((d / "Q1P1.verdict.json").read_text())
    assert [v["novelty_counts"] for v in verdicts] == [records[0]["counts"], records[1]["counts"]]
    assert verdicts[0]["decision"] == "REVISE" and "action" in verdicts[0]

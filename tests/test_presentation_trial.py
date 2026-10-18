"""Fixes from nobel's engine trial of the presentation pass (engine-v1.16.0 on copies of Q472-P527 and Q138-P465,
18 October 2026). Neither paper cleared: the lookup returned an escalation as a plain string and the pass blocked
on the contract; a finding asking to update search.md could not be closed by any stage; and four unclear sentences
of the accepted text, labelled "meaning", went to the claims review and stopped Q138 at RETURNED where a reword
would have fixed them. Also: the playbook named nothing for an accepted paper awaiting its pass, and a call routed
to another provider took a seat of the campaign's account."""
import copy, json
import pytest
from pathfinder import paper, playbook, presentation, seats
from stubcampaign import make
from test_presentation import _accepted, _script, check, edited, manuscript, needs_tex, F1_APPLIED, NOTATION


@needs_tex
def test_a_string_escalation_is_kept_as_an_issue_not_a_contract_failure(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    def lookup(request):
        tex = manuscript(request.prompt)
        assert '"escalations": [{"where":' in " ".join(request.prompt.split())     # the prompt shows the object form
        return ("===PAPER===\n" + tex + "\n===REPORT===\n" + json.dumps({
            "changelog": ["F1 cited after reading it"], "title": None, "findings": [F1_APPLIED],
            "escalations": ["F1 also asks to record the query in search.md"]}))
    _script(monkeypatch, {"present/editor": [edited(findings=[{"id": "F1", "status": "needs lookup", "reason": "metadata"}])],
                          "present_lookup/lookup": [lookup], "present_check/checker": [check()],
                          "review/claims": [json.dumps({"items": [{"id": "C1", "decision": "dismissed", "reason": "a pipeline file"}]})]})
    assert presentation.run(c, "Q1P1") == "CLEARED"
    s = presentation.state(c, "Q1P1")
    assert s["escalations"] == [{"where": None, "issue": "F1 also asks to record the query in search.md"}]


@needs_tex
def test_a_finding_about_a_pipeline_file_is_closed_as_out_of_scope(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    seen = _script(monkeypatch, {"present/editor": [edited(findings=[
        {"id": "F1", "status": "out of scope", "reason": "asks to update search.md, a pipeline file"}])],
        "present_check/checker": [check()]})
    assert presentation.run(c, "Q1P1") == "CLEARED"
    assert "out of scope" in " ".join(seen[0].prompt.split()) and "search.md" in seen[0].prompt


@needs_tex
def test_out_of_scope_needs_a_reason(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    _script(monkeypatch, {"present/editor": [edited(findings=[{"id": "F1", "status": "out of scope", "reason": ""}])],
                          "present_check/checker": [check()]})
    assert presentation.run(c, "Q1P1") == "PAUSE-ON-PRESENT"
    assert "F1" in presentation.state(c, "Q1P1")["reason"]


UNCLEAR = {"kind": "unclear", "where": "\"The stub cites one source\"", "issue": "which source is meant is unclear",
           "fix": "name the source"}


@needs_tex
def test_an_unclear_sentence_goes_to_the_corrector_who_may_reword_it(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    seen = _script(monkeypatch, {
        "present/editor": [edited(findings=[F1_APPLIED])],
        "present/corrector": [edited(("The stub cites one source", "The stub refers to its single source"))],
        "present_check/checker": [check(UNCLEAR), check()]})
    assert presentation.run(c, "Q1P1") == "CLEARED"
    assert not [r for r in seen if r.actor == "claims"]             # no claims review for wording
    recheck = [r for r in seen if r.stage == "present_check"][1]
    assert "sentences the last correction reworded" in recheck.prompt and "refers to its single source" in recheck.prompt


@needs_tex
def test_a_reword_of_an_accepted_sentence_no_finding_names_is_still_refused(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch, presentation_cycles=1)
    _script(monkeypatch, {
        "present/editor": [edited(findings=[F1_APPLIED])],
        "present/corrector": [edited(("A stub account for contract tests.", "An account for tests."))],
        "present_check/checker": [check(UNCLEAR)]})
    assert presentation.run(c, "Q1P1") == "PAUSE-ON-PRESENT"
    assert "changes accepted wording" in presentation.state(c, "Q1P1")["reason"]


@needs_tex
def test_a_meaning_finding_the_claims_review_calls_presentation_goes_to_the_corrector(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    meaning = {"kind": "meaning", "where": "\"The stub cites one source\"", "issue": "ambiguous", "fix": "reword"}
    seen = _script(monkeypatch, {
        "present/editor": [edited(findings=[F1_APPLIED])],
        "present/corrector": [edited(("The stub cites one source", "The stub cites exactly one source"))],
        "present_check/checker": [check(meaning), check()],
        "review/claims": [json.dumps({"items": [{"id": "C1", "decision": "presentation", "reason": "a reword fixes it"}]})]})
    assert presentation.run(c, "Q1P1") == "CLEARED"
    assert [r.stage for r in seen].count("author") == 0 and paper.status(c, "Q1P1").get("presentation_amends") is None


@needs_tex
def test_the_playbook_names_the_pass_for_an_accepted_paper(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    actions = playbook.next_actions(c)
    assert any((a["command"] or "").endswith("present Q1P1") for a in actions)


def test_a_call_routed_to_another_provider_takes_no_seat_of_the_campaigns_account(tmp_path):
    c = make(tmp_path, account={"name": "codex-subscription", "seats": 6})
    routed = copy.copy(c); routed.backend = "claude"
    assert seats.account(c)["name"] == "codex-subscription" and seats.account(routed) is None


def test_a_routed_provider_can_name_its_own_account(tmp_path):
    c = make(tmp_path, account={"name": "codex-subscription", "seats": 6},
             accounts={"claude": {"name": "claude-max", "seats": 2}})
    routed = copy.copy(c); routed.backend = "claude"
    assert seats.account(routed) == {"name": "claude-max", "seats": 2}


def test_a_malformed_accounts_map_is_refused(tmp_path):
    with pytest.raises(ValueError, match="accounts"):
        make(tmp_path, accounts={"claude": {"name": "x"}})

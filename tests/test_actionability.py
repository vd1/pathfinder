"""Actionability, the end of the pipeline: once a pair is edited, one tool-less assessor call decides whether the
result can be acted on (ACTIONABLE, NEEDS_INPUTS or NO_CASE), with the inputs still missing, the next experiment
and what would falsify it. Opt-in with "actionability": true; the deployment's rubric is an append overlay."""
import json
import pytest
from pathfinder import actionability, campaign_state, config, edit, research, runner, transport
from stubcampaign import make


def _calls(c, stage):
    return [r for r in transport.receipts(c) if r.get("stage") == stage]


def test_off_by_default(tmp_path):
    c = make(tmp_path)
    runner.run(c, interval=0)
    assert not _calls(c, "actionability")
    assert actionability.status(c, "Q1P1") == {"status": "none"}


def test_an_edited_pair_is_assessed_at_the_end(tmp_path):
    c = make(tmp_path, actionability=True)
    runner.run(c, interval=0)
    assert edit.status(c, "Q1P1")["status"] == "done"
    s = actionability.status(c, "Q1P1")
    assert s["status"] == "done" and s["decision"] in ("ACTIONABLE", "NEEDS_INPUTS", "NO_CASE")
    for key in ("rationale", "evidence", "required_inputs", "next_experiment", "falsification"):
        assert key in s["assessment"]
    [call] = _calls(c, "actionability")
    assert call["actor"] == "assessor"
    assert runner.pending(c) == []


def test_the_assessor_reads_the_papers_the_ledger_and_the_edited_note_with_the_deployments_rubric(tmp_path, monkeypatch):
    c = make(tmp_path, actionability=True)
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts/actionability.append.md").write_text("Judge as a computational chemist.\n")
    c = config.load(tmp_path)
    seen = {}
    real = transport.execute
    def spy(campaign, request):
        if request.stage == "actionability":
            seen["request"] = request
        return real(campaign, request)
    monkeypatch.setattr(transport, "execute", spy)
    runner.run(c, interval=0)
    request = seen["request"]
    note = (c.thread_dir("Q1P1") / "edited/note.tex").read_text()
    assert not request.tools and request.schema == actionability.SCHEMA
    assert "Judge as a computational chemist." in request.prompt and note[:200] in request.prompt
    assert "ledger.jsonl" in request.prompt and "Q.txt" in request.prompt


def test_routes_apply_to_the_assessor(tmp_path):
    c = make(tmp_path, actionability=True, routes={"actionability": {"model": "assessor-model"}})
    runner.run(c, interval=0)
    assert _calls(c, "actionability")[0]["model"] == "assessor-model"


def test_an_unreadable_assessment_is_recorded_and_does_not_hold_the_campaign(tmp_path, monkeypatch):
    c = make(tmp_path, actionability=True)
    from pathfinder import stub
    real = stub.reply
    monkeypatch.setattr(stub, "reply", lambda campaign, request: "no JSON here" if request.stage == "actionability"
                        else real(campaign, request))
    runner.run(c, interval=0)
    s = actionability.status(c, "Q1P1")
    assert s["status"] == "blocked" and "JSON" in s["reason"]
    assert len(_calls(c, "actionability")) == 2          # the call and its one repair turn
    assert runner.pending(c) == []


def test_a_pair_edited_before_actionability_was_turned_on_is_assessed_by_the_next_run(tmp_path):
    c = make(tmp_path)
    runner.run(c, interval=0)
    raw = json.loads((tmp_path / "campaign.json").read_text()); raw["actionability"] = True
    (tmp_path / "campaign.json").write_text(json.dumps(raw))
    c = config.load(tmp_path)
    assert runner.pending(c) == ["Q1P1"]
    peers = len(_calls(c, "peer"))
    runner.run(c, interval=0, accept_change="turn on actionability")      # a config change starts a linked run
    assert actionability.status(c, "Q1P1")["status"] == "done"
    assert len(_calls(c, "peer")) == peers                                # research and editing are not redone


def test_the_state_document_shows_the_decision(tmp_path):
    c = make(tmp_path, actionability=True)
    runner.run(c, interval=0)
    unit = campaign_state.build(c)["units"][0]
    assert unit["actionability"]["decision"] == actionability.status(c, "Q1P1")["decision"]


@pytest.mark.parametrize("bad", ["yes", 1, {"enabled": True}])
def test_a_bad_setting_is_refused(tmp_path, bad):
    with pytest.raises(ValueError, match="actionability"):
        make(tmp_path, actionability=bad)

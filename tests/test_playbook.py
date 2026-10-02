"""The supervision playbook: next actions from the campaign state, with an owner and an exact command."""
import json
from pathfinder import edit, failures, playbook, research
from stubcampaign import make

TIMEOUT = {"class": "timeout", "scope": "call", "retry": True, "reset_at": None}


def test_a_quota_stop_is_escalated_to_the_operator_with_its_reset_and_never_retried(tmp_path):
    c = make(tmp_path)
    failures.stop_for(c, failures.classify("error", "You've hit your usage limit ... try again at Oct 4th, 2026 2:07 AM."), "usage limit")
    actions = playbook.next_actions(c)
    assert actions[0]["owner"] == "operator" and "Oct 4th, 2026 2:07 AM" in actions[0]["why"]
    assert not any("retry" in (a["action"] + (a["command"] or "")).lower() for a in actions)


def test_a_stopped_edit_gets_an_apex_reconcile_command(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    edit._set(c, "Q1P1", status="stopped", reason="transport failed: timeout", failure=TIMEOUT)
    actions = playbook.next_actions(c)
    match = [a for a in actions if a["command"] and "reconcile Q1P1 --apply" in a["command"]]
    assert match and match[0]["owner"] == "apex"


def test_an_evidence_block_points_at_the_evidence_command(tmp_path):
    c = make(tmp_path, research_scheme="direct_eva", strict_evidence=True, imported_research=True)
    d = research.prepare(c, "Q1P1")
    from pathfinder.ledger import Ledger
    Ledger(d / "ledger.jsonl").add("ada", "finding", "see ada/result.json")
    research.run_thread(c, "Q1P1")
    assert any(a["command"] and "evidence Q1P1" in a["command"] for a in playbook.next_actions(c))


def test_cli_playbook_json(tmp_path, capsys):
    from pathfinder import cli
    make(tmp_path)
    assert cli.main(["--root", str(tmp_path), "playbook", "--json"]) in (0, None)
    assert isinstance(json.loads(capsys.readouterr().out), list)


def test_a_blocked_edit_goes_to_the_operator(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    edit._set(c, "Q1P1", status="blocked", reason="prompt too large", failure=research.OVERSIZE_FAILURE)
    match = [a for a in playbook.next_actions(c) if a["action"].startswith("Q1P1")]
    assert match and match[0]["owner"] == "operator" and "input too large" in match[0]["why"]


def test_no_pair_is_reconciled_while_the_campaign_is_stopped(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    edit._set(c, "Q1P1", status="stopped", reason="transport failed: timeout", failure=TIMEOUT)
    failures.stop_for(c, failures.classify("error", "You've hit your usage limit ... try again at Oct 4th, 2026 2:07 AM."), "usage limit")
    actions = playbook.next_actions(c)
    assert not any(a["command"] and " reconcile Q1P1" in a["command"] for a in actions)
    pair = [a for a in actions if a["action"].startswith("Q1P1")]
    assert pair and pair[0]["owner"] == "engine" and pair[0]["command"] is None


def test_a_contract_block_is_an_apex_reconcile(tmp_path):
    c = make(tmp_path, research_scheme="direct_eva")
    research.prepare(c, "Q1P1")
    research._set(c, "Q1P1", status="BLOCKED", stage="ledger_review", reason="contract: review: no readable JSON object",
                  failure={"class": "contract", "scope": "call", "retry": False, "reset_at": None})
    match = [a for a in playbook.next_actions(c) if a["command"] and " reconcile Q1P1 --apply" in a["command"]]
    assert match and match[0]["owner"] == "apex"

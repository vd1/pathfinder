"""reconcile --repair-only makes the state repair a recovery needs and calls no model: the deployment's own
command then resumes the run inside its own transport. proofTree's sandbox wraps the engine's transport, and
reconcile --apply resumed outside it, so its recovery instruction had no way to reissue or unblock (9 October 2026)."""
import pytest
from pathfinder import cli, composable, reconcile, research, transport
from stubcampaign import make

TIMEOUT = {"class": "timeout", "scope": "call", "retry": True, "reset_at": None}


def _branch_review_timed_out(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="composable")
    real, armed = transport.execute, {"on": True}

    def execute(campaign, request):
        r = real(campaign, request)
        if armed["on"] and request.stage == "ledger_review" and str(request.cwd).endswith("branch-2"):
            armed["on"] = False
            return {**r, "text": "", "transport_failed": True, "error": "timeout", "outcome": "timeout", "failure": TIMEOUT}
        return r
    monkeypatch.setattr(transport, "execute", execute)
    with pytest.raises(transport.TransportFailed):
        research.run_thread(c, "Q1P1")
    return c


def test_repair_only_reissues_without_a_model_call_and_the_deployment_resumes(tmp_path, monkeypatch):
    c = _branch_review_timed_out(tmp_path, monkeypatch)
    assert reconcile.inspect(c, "Q1P1")["action"] == "branch-2: reissue: the reply failed in transport"
    calls = []
    real = transport.execute
    monkeypatch.setattr(transport, "execute", lambda campaign, request: calls.append(request) or real(campaign, request))
    outcome = reconcile.apply(c, "Q1P1", resume=False)
    assert outcome.startswith("repaired: branch-2: reissue") and calls == []
    view = composable.branch_view(c, "Q1P1", "branch-2")
    assert research.status(view, "Q1P1")["status"] == "running" and research.status(view, "Q1P1")["pending"] == []
    assert list((view.thread_dir("Q1P1") / "research-requests" / "superseded").glob("*.json"))
    assert research.run_thread(c, "Q1P1") == "DRAFT"                  # the deployment's own resume
    assert calls


def test_repair_only_unblocks_a_blocked_thread_without_resuming(tmp_path, monkeypatch):
    c = make(tmp_path, research_scheme="direct_eva")
    research.prepare(c, "Q1P1")
    research._set(c, "Q1P1", status="BLOCKED", stage="ledger_review", reason="contract: review: no readable JSON object",
                  failure={"class": "contract", "scope": "call", "retry": False, "reset_at": None})
    calls = []
    monkeypatch.setattr(transport, "execute", lambda campaign, request: calls.append(request))
    assert reconcile.apply(c, "Q1P1", resume=False).startswith("repaired: reissue: the reply broke its contract twice")
    assert research.status(c, "Q1P1")["status"] == "running" and calls == []


def test_the_cli_repairs_only(tmp_path, monkeypatch, capsys):
    c = _branch_review_timed_out(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(transport, "execute", lambda campaign, request: calls.append(request))
    cli.main(["--root", str(tmp_path), "reconcile", "Q1P1", "--repair-only"])
    assert "repaired: branch-2: reissue" in capsys.readouterr().out and calls == []

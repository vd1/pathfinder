"""Bounded recovery preserves the old editorial and scientific records."""
import json
import pytest
from pathfinder import account_release, edit, paper, pce, pce_recovery, presentation, reconcile, research, stub
from test_pce import ready, script


def prepare(tmp_path, monkeypatch, *, owner=False):
    c = ready(tmp_path, pce={"passes": 2, "fact_checks": 1})
    calls = script(monkeypatch, c, fact_checker=["fail"])
    assert pce.run(c, "Q1P1")["status"] == "review_required"
    edit._set(c, "Q1P1", status="done", editorial_status="owner-accepted" if owner else "review_required",
              accepted_note=owner)
    c.raw["edit_scheme"] = "single"
    return c, calls


def test_explicit_grant_preserves_history_and_resumes_without_duplicate_calls(tmp_path, monkeypatch):
    c, _ = prepare(tmp_path, monkeypatch)
    old = pce.workflow(c, "Q1P1")
    before = pce_recovery.hashes(old)
    scientific = (c.thread_dir("Q1P1") / "status.json").read_bytes()
    assert reconcile.inspect(c, "Q1P1")["action"].startswith("grant PCE")
    assert "explicit" in reconcile.apply(c, "Q1P1")
    calls = script(monkeypatch, c)
    root = pce_recovery.grant(c, "Q1P1", "recovery-1", 2, 2, "finish independent gates")
    assert reconcile.inspect(c, "Q1P1")["action"] == "resume PCE continuation"
    assert pce_recovery.grant(c, "Q1P1", "recovery-1", 2, 2, "finish independent gates") == root
    from pathfinder.thread import Stopped
    with pytest.raises(Stopped):
        pce.run(c, "Q1P1", stop=lambda: len(calls) >= 2)
    assert len(calls) == 2
    assert pce.run(c, "Q1P1")["status"] == "accepted"
    assert len(calls) == 5
    assert pce.run(c, "Q1P1")["status"] == "accepted"
    assert len(calls) == 5
    assert pce_recovery.hashes(old) == before
    assert (c.thread_dir("Q1P1") / "status.json").read_bytes() == scientific
    with pytest.raises(pce.Changed, match="identity"):
        pce_recovery.grant(c, "Q1P1", "recovery-1", 3, 3, "finish independent gates")


def test_owner_baseline_and_acceptance_are_preserved(tmp_path, monkeypatch):
    c, _ = prepare(tmp_path, monkeypatch, owner=True)
    ed = c.thread_dir("Q1P1") / "edited"
    (ed / "note.tex").write_text(stub.READABLE + "\n% owner correction\n")
    previous = (ed / "edit.json").read_bytes()
    root = pce_recovery.grant(c, "Q1P1", "owner-gates", 2, 2, "complete missing gates")
    grant = json.loads((root / "grant.json").read_text())
    assert grant["previous_edit"]["editorial_status"] == "owner-accepted"
    assert grant["baseline"] == "note.tex"
    assert (ed / "edit.json").read_bytes() == previous
    assert "owner correction" in json.loads((root / "frozen-inputs.json").read_text())[pce.BASELINE]


def test_single_editor_can_enter_pce(tmp_path, monkeypatch):
    c = ready(tmp_path)
    c.raw["edit_scheme"] = "single"
    script(monkeypatch, c)
    pce_recovery.grant(c, "Q1P1", "first-pce", 1, 1, "owner requested PCE")
    assert pce.run(c, "Q1P1")["status"] == "accepted"


def test_reviewers_get_science_without_previous_verdicts(tmp_path, monkeypatch):
    c = ready(tmp_path)
    d = c.thread_dir("Q1P1")
    with (d / "ledger.jsonl").open("a") as f:
        f.write(json.dumps({"seq": 999, "actor": "vera", "kind": "review", "text": "SECRET_OLD_VERDICT"}) + "\n")
        f.write(json.dumps({"seq": 1000, "actor": "ada", "kind": "derivation", "text": "SCIENTIFIC_DERIVATION"}) + "\n")
    calls = script(monkeypatch, c)
    pce.run(c, "Q1P1")
    for call in calls:
        if call["role"] in ("critic", "fact-checker"):
            assert "SECRET_OLD_VERDICT" not in call["prompt"]
            assert "SCIENTIFIC_DERIVATION" in call["prompt"]
    assert "SECRET_OLD_VERDICT" in calls[0]["prompt"]


@pytest.mark.parametrize("bad", ["role", "fallback", "tail"])
def test_excluded_routes_refused_before_writes(tmp_path, monkeypatch, bad):
    c = ready(tmp_path)
    c.backend = "codex"; c.model = "gpt-6-astra"
    if bad == "fallback":
        c.raw["refusal_fallback"] = {"backend": "claude", "model": "claude-opus-5"}
    else:
        c.raw["routes"] = {"edit/pce-critic" if bad == "role" else "present_check/checker":
                           {"backend": "claude", "model": "claude-opus-5"}}
    before = pce_recovery.hashes(c.root)
    with pytest.raises(pce.Changed):
        pce_recovery.preflight(c, presentation=True)
    assert before == pce_recovery.hashes(c.root)


def accepted(tmp_path, monkeypatch):
    c = ready(tmp_path)
    script(monkeypatch, c)
    assert pce.run(c, "Q1P1")["status"] == "accepted"
    ed = c.thread_dir("Q1P1") / "edited"
    (ed / "note.tex").write_text((pce.workflow(c, "Q1P1") / pce.DRAFT).read_text())
    edit._set(c, "Q1P1", status="done", accepted_note=True, editorial_status="accepted")
    return c


def test_account_tail_has_separate_state_and_never_amends_science(tmp_path, monkeypatch):
    c = accepted(tmp_path, monkeypatch)
    original = (c.thread_dir("Q1P1") / "status.json").read_bytes()
    v = account_release.view(c, "Q1P1", create=True)
    assert paper.folder(v, "Q1P1").is_relative_to(c.thread_dir("Q1P1") / "edited")
    assert paper.status(c, "Q1P1")["status"] == "none"
    assert paper.status(v, "Q1P1")["acceptance_kind"] == "PCE editorial acceptance"
    presentation.folder(v, "Q1P1").mkdir()
    monkeypatch.setattr(paper, "amend", lambda *a, **k: pytest.fail("must not commission research"))
    assert presentation._return(v, "Q1P1", [{"where": "intro", "issue": "meaning", "fix": "needs evidence"}]) == "RETURNED"
    assert original == (c.thread_dir("Q1P1") / "status.json").read_bytes()


def test_account_requires_completed_gates_and_unchanged_note(tmp_path, monkeypatch):
    c, _ = prepare(tmp_path, monkeypatch, owner=True)
    with pytest.raises(pce.Changed, match="completed PCE"):
        account_release.view(c, "Q1P1", create=True)


def test_account_tail_end_to_end_on_stub(tmp_path, monkeypatch):
    from test_presentation import _script, edited, check
    c = accepted(tmp_path, monkeypatch)
    c.raw["release"] = {"disclosure": "disclosure.tex"}
    (c.root / "disclosure.tex").write_text("Prepared with Pathfinder; the scientific limitations remain those of the account.")
    monkeypatch.setattr(paper, "_arxiv_titles", lambda ids: {})
    before = (c.thread_dir("Q1P1") / "status.json").read_bytes()
    prior_edit = (c.thread_dir("Q1P1") / "edited" / "edit.json").read_bytes()
    seen = _script(monkeypatch, {"present/editor": [edited()], "present_check/checker": [check()]})
    assert account_release.present(c, "Q1P1") == "CLEARED"
    assert {r.stage for r in seen} == {"present", "present_check"}
    assert all("Acceptance in this task means PCE editorial approval only" in r.prompt for r in seen)
    assert all("Referees have accepted its mathematics" not in r.prompt for r in seen)
    assert account_release.present(c, "Q1P1") == "CLEARED"
    out = account_release.release(c, "Q1P1")
    assert out["status"] == "RELEASED"
    v = account_release.view(c, "Q1P1")
    assert (paper.folder(v, "Q1P1") / "release" / "paper.pdf").exists()
    assert before == (c.thread_dir("Q1P1") / "status.json").read_bytes()
    assert prior_edit == (c.thread_dir("Q1P1") / "edited" / "edit.json").read_bytes()
    assert paper.status(c, "Q1P1")["status"] == "none"


def test_reconcile_apply_uses_transport_and_keeps_old_charges(tmp_path, monkeypatch):
    from pathfinder import consumer
    c = ready(tmp_path)
    pce_recovery.grant(c, 'Q1P1', 'transport-check', 1, 1, 'complete PCE')
    old_status = (c.thread_dir('Q1P1') / 'status.json').read_bytes()
    charges = c.path('receipts.jsonl').read_bytes() if c.path('receipts.jsonl').exists() else b''
    monkeypatch.setattr(edit, '_install', lambda *a: None)
    monkeypatch.setattr(consumer, 'run', lambda *a: pytest.fail('no downstream consumer in continuation'))
    assert reconcile.apply(c, 'Q1P1') == 'done'
    assert len(pce.dispatches(c, 'Q1P1')) == 5
    assert all(r['receipt']['backend'] == 'stub' for r in pce.dispatches(c, 'Q1P1'))
    assert c.path('receipts.jsonl').read_bytes().startswith(charges)
    assert old_status == (c.thread_dir('Q1P1') / 'status.json').read_bytes()


def test_stop_and_grant_publication_crash_are_resumable(tmp_path, monkeypatch):
    c = ready(tmp_path)
    root = pce_recovery.grant(c, 'Q1P1', 'crash', 1, 1, 'record before activation')
    (root.parent.parent / 'pce-active.json').unlink()
    assert pce_recovery.grant(c, 'Q1P1', 'crash', 1, 1, 'record before activation') == root
    c.path('stop.json').write_text('{"reason":"operator stop"}')
    assert pce_recovery.apply(c, 'Q1P1').startswith('stopped')
    assert not (root / 'dispatch').exists()
    assert c.path('stop.json').exists()


def test_cli_grant_is_explicit_and_repair_only_calls_no_model(tmp_path, monkeypatch, capsys):
    from pathfinder import cli
    c = ready(tmp_path)
    monkeypatch.setattr(pce, '_dispatch', lambda *a, **k: pytest.fail('repair-only must not call a model'))
    cli.main(['--root', str(c.root), 'reconcile', 'Q1P1', '--pce-grant', 'cli-grant',
              '--passes', '2', '--fact-checks', '2', '--reason', 'finish editorial review', '--repair-only'])
    assert 'no calls' in capsys.readouterr().out
    assert pce_recovery.active(c, 'Q1P1')

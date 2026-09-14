import json, sys
from pathlib import Path
from pathfinder import research, transport
from pathfinder.config import Campaign

FAKE = f"{sys.executable} {Path(__file__).parent / 'fake_cli.py'}"


def make(tmp_path, rounds=3):
    (tmp_path / "campaign.json").write_text("{}")
    c = Campaign(root=tmp_path, backend="claude", model="m", scan_model="m", peer_search=False, seats=1, cut=1,
                 rounds=rounds, allowances={"peer_seconds": 100, "peer_calls": 2, "consolidate_seconds": 10, "verify_seconds": 10},
                 budget_usd=99, prices={}, scan_fulltext=None)
    (tmp_path / "Q.jsonl").write_text('{"id":"a","title":"A","abstract":"aa","text":null}\n')
    (tmp_path / "P.jsonl").write_text('{"id":"b","title":"B","abstract":"bb","text":null}\n')
    return c


def test_thread_reaches_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    c = make(tmp_path)
    helper = f"{sys.executable} -m pathfinder.ledger --root . "
    # peers: each call adds an idea then declares ready at the latest entry
    monkeypatch.setenv("FAKE_RUN", helper + "--actor $FAKE_ACTOR add --kind idea --text hi >/dev/null; "
                       + helper + "--actor $FAKE_ACTOR ready --seen $(" + helper + "--actor x read | grep -c '^#')")
    real = transport.call

    def fake_call(prompt, **kw):
        monkeypatch.setenv("FAKE_ACTOR", kw["actor"])
        # by default the researchers get links, not the papers; the verifier gets everything inline, instruction last
        if kw["stage"] == "peers":
            assert "## ledger.jsonl" not in prompt and "Read inputs/" in prompt and "--since 0" in prompt
        if kw["stage"] == "verify":
            assert prompt.index("## ledger.jsonl") < prompt.index("## your task")
        if kw["stage"] == "consolidate":
            (kw["cwd"] / "Q1P1.tex").write_text("\\documentclass{article}\\begin{document}x\\end{document}")
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", "wrote it")
        elif kw["stage"] == "verify":
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", '{"decision":"DRAFT","reason":"fine","action":null}')
        else:
            monkeypatch.setenv("FAKE_REPLY", "peer")
        return real(prompt, **kw)
    monkeypatch.setattr(research.transport, "call", fake_call)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    s = research.status(c, "Q1P1")
    assert s["status"] == "DRAFT" and s["round"] == 1
    v = json.loads((tmp_path / "threads" / "Q1P1" / "Q1P1.verdict.json").read_text())
    assert v[0]["decision"] == "DRAFT"


def test_iterate_cap_becomes_pause_on_iterate(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    c = make(tmp_path, rounds=2)
    real = transport.call

    def fake_call(prompt, **kw):
        if kw["stage"] == "peers":
            monkeypatch.setenv("FAKE_RUN", f"{sys.executable} -m pathfinder.ledger --root . --actor {kw['actor']} add --kind idea --text x >/dev/null")
            monkeypatch.setenv("FAKE_REPLY", "p")
        elif kw["stage"] == "consolidate":
            (kw["cwd"] / "Q1P1.tex").write_text("x"); monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", "ok")
        else:
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", '{"decision":"ITERATE","reason":"more","action":"check"}')
        return real(prompt, **kw)
    monkeypatch.setattr(research.transport, "call", fake_call)
    assert research.run_thread(c, "Q1P1") == "PAUSE-ON-ITERATE"
    assert research.status(c, "Q1P1")["round"] == 2


def test_empty_ledger_pauses_without_note(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    monkeypatch.setenv("FAKE_REPLY", "nothing"); monkeypatch.setenv("FAKE_RUN", "true")
    c = make(tmp_path)
    assert research.run_thread(c, "Q1P1") == "PAUSE"
    assert research.status(c, "Q1P1")["reason"] == "empty ledger"
    assert not (tmp_path / "threads" / "Q1P1" / "Q1P1.tex").exists()


def test_blocked_on_unreadable_verdict_and_reconcile_clears_it(tmp_path, monkeypatch):
    from pathfinder import reconcile
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    c = make(tmp_path)
    real = transport.call
    replies = {"verify": "I cannot decide."}

    def fake_call(prompt, **kw):
        if kw["stage"] == "peers":
            monkeypatch.setenv("FAKE_RUN", f"{sys.executable} -m pathfinder.ledger --root . --actor {kw['actor']} add --kind idea --text x >/dev/null")
            monkeypatch.setenv("FAKE_REPLY", "p")
        elif kw["stage"] == "consolidate":
            (kw["cwd"] / "Q1P1.tex").write_text("x"); monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", "ok")
        else:
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", replies["verify"])
        return real(prompt, **kw)
    monkeypatch.setattr(research.transport, "call", fake_call)
    assert research.run_thread(c, "Q1P1") == "BLOCKED"
    assert research.status(c, "Q1P1")["reason"].startswith("verify: unreadable")
    assert reconcile.inspect(c, "Q1P1")["action"] == "run verify"
    replies["verify"] = '{"decision":"DRAFT","reason":"fine","action":null}'
    assert reconcile.apply(c, "Q1P1") == "DRAFT"


def test_blocked_when_consolidation_writes_nothing(tmp_path, monkeypatch):
    from pathfinder import reconcile
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    c = make(tmp_path)
    real = transport.call
    state = {"write_note": False}

    def fake_call(prompt, **kw):
        if kw["stage"] == "peers":
            monkeypatch.setenv("FAKE_RUN", f"{sys.executable} -m pathfinder.ledger --root . --actor {kw['actor']} add --kind idea --text x >/dev/null")
            monkeypatch.setenv("FAKE_REPLY", "p")
        elif kw["stage"] == "consolidate":
            if state["write_note"]:
                (kw["cwd"] / "Q1P1.tex").write_text("x")
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", "")
        else:
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", '{"decision":"PAUSE","reason":"thin","action":null}')
        return real(prompt, **kw)
    monkeypatch.setattr(research.transport, "call", fake_call)
    assert research.run_thread(c, "Q1P1") == "BLOCKED"
    assert research.status(c, "Q1P1")["reason"].startswith("consolidate:")
    assert reconcile.inspect(c, "Q1P1")["action"] == "run consolidate"
    state["write_note"] = True
    assert reconcile.apply(c, "Q1P1") == "PAUSE"


def test_revise_repairs_the_note_once_then_caps(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    c = make(tmp_path, rounds=3); c.raw = {"repairs": 1}
    real = transport.call
    seen = {"consolidate": 0, "verify": 0, "prompts": []}

    def fake_call(prompt, **kw):
        if kw["stage"] == "peers":
            monkeypatch.setenv("FAKE_RUN", f"{sys.executable} -m pathfinder.ledger --root . --actor {kw['actor']} add --kind idea --text x >/dev/null")
            monkeypatch.setenv("FAKE_REPLY", "p")
        elif kw["stage"] == "consolidate":
            seen["consolidate"] += 1; seen["prompts"].append(prompt)
            (kw["cwd"] / "Q1P1.tex").write_text(f"note v{seen['consolidate']}"); monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", "ok")
        else:
            seen["verify"] += 1; monkeypatch.setenv("FAKE_RUN", "true")
            monkeypatch.setenv("FAKE_REPLY", '{"decision":"REVISE","reason":"overclaims","action":"soften the claim"}')
        return real(prompt, **kw)
    monkeypatch.setattr(research.transport, "call", fake_call)
    assert research.run_thread(c, "Q1P1") == "PAUSE-ON-REVISE"
    s = research.status(c, "Q1P1")
    assert s["round"] == 1 and s["repairs"] == 1
    assert seen["consolidate"] == 2 and seen["verify"] == 2 and "This is a repair" in seen["prompts"][1]
    hist = json.loads((tmp_path / "threads" / "Q1P1" / "Q1P1.verdict.json").read_text())
    assert [h["decision"] for h in hist] == ["REVISE", "REVISE"] and hist[0]["note_sha256"] != hist[1]["note_sha256"]


def test_three_peers_share_the_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    c = make(tmp_path); c.peers = ("ada", "emmy", "grace"); c.allowances["peer_calls"] = 1
    real = transport.call
    actors = []

    def fake_call(prompt, **kw):
        if kw["stage"] == "peers":
            actors.append(kw["actor"]); assert "partner of" in prompt
            monkeypatch.setenv("FAKE_RUN", f"{sys.executable} -m pathfinder.ledger --root . --actor {kw['actor']} add --kind idea --text x >/dev/null")
            monkeypatch.setenv("FAKE_REPLY", "p")
        elif kw["stage"] == "consolidate":
            (kw["cwd"] / "Q1P1.tex").write_text("x"); monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", "ok")
        else:
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", '{"decision":"PAUSE","reason":"thin","action":null}')
        return real(prompt, **kw)
    monkeypatch.setattr(research.transport, "call", fake_call)
    assert research.run_thread(c, "Q1P1") == "PAUSE"
    assert sorted(actors) == ["ada", "emmy", "grace"] and (tmp_path / "threads" / "Q1P1" / "grace").is_dir()
    from pathfinder.ledger import Ledger
    assert Ledger(tmp_path / "threads" / "Q1P1" / "ledger.jsonl").count() == 3


def test_inline_papers_is_a_setting(tmp_path, monkeypatch):
    """With inline_papers on, researchers and consolidator get the shared head first and their brief after it."""
    monkeypatch.setenv("PATHFINDER_CLAUDE", FAKE); monkeypatch.setattr(transport, "SESSION_GRACE", 2)
    c = make(tmp_path); c.raw["inline_papers"] = True
    helper = f"{sys.executable} -m pathfinder.ledger --root . "
    monkeypatch.setenv("FAKE_RUN", helper + "--actor $FAKE_ACTOR add --kind idea --text hi >/dev/null; "
                       + helper + "--actor $FAKE_ACTOR ready --seen $(" + helper + "--actor x read | grep -c '^#')")
    seen = {}
    real = transport.call

    def fake_call(prompt, **kw):
        monkeypatch.setenv("FAKE_ACTOR", kw["actor"]); seen.setdefault(kw["stage"], prompt)
        if kw["stage"] == "consolidate":
            (kw["cwd"] / "Q1P1.tex").write_text("\\documentclass{article}\\begin{document}x\\end{document}")
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", "wrote it")
        elif kw["stage"] == "verify":
            monkeypatch.setenv("FAKE_RUN", "true"); monkeypatch.setenv("FAKE_REPLY", '{"decision":"DRAFT","reason":"fine","action":null}')
        else:
            monkeypatch.setenv("FAKE_REPLY", "peer")
        return real(prompt, **kw)
    monkeypatch.setattr(research.transport, "call", fake_call)
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    for stage in ("peers", "consolidate", "verify"):
        p = seen[stage]; assert p.index("## ledger.jsonl") < p.index("## your task"), stage
    assert "You are ada" in seen["peers"][seen["peers"].index("## your task"):]

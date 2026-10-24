"""Reopening a classic thread (research_scheme absent; nobel pilot 9 and Atlas pilots 1 to 6, 24 October 2026).
reopen refused the classic scheme, and an operator who forced it found the classic loop ignored the grant: the repair
consolidated without the verifier's corrections, an ITERATE after it opened further rounds up to `rounds` instead of
ending the thread, and a round grant reused the peers' old ready and skipped their research. Now a classic thread
reopens like an eva one: a repair is briefed with the last verdict, a round or extend dispatches every peer again,
and the verdict that follows ends the thread."""
import json
import pytest
from pathfinder import config, reopen, research, transport
from stubcampaign import make


def _finished(tmp_path, verdict, **raw):
    c = make(tmp_path, stub={"verify": verdict}, **{"rounds": 6, **raw})
    assert research.run_thread(c, "Q1P1") == {"REVISE": "PAUSE-ON-REVISE", "ITERATE": "PAUSE-ON-ITERATE"}.get(verdict, verdict)
    return c


def _verdict(c, decision):
    raw = json.loads(c.path("campaign.json").read_text()); raw["stub"] = {"verify": decision}
    c.path("campaign.json").write_text(json.dumps(raw))
    return config.load(c.root)


def _seen(monkeypatch):
    seen, real = [], transport.execute
    monkeypatch.setattr(transport, "execute", lambda campaign, request: seen.append(request) or real(campaign, request))
    return seen


def test_a_classic_repair_grant_is_briefed_with_the_last_verdict_and_its_verdict_ends_the_thread(tmp_path, monkeypatch):
    c = _finished(tmp_path, "REVISE", repairs=1)
    last = json.loads((c.thread_dir("Q1P1") / "Q1P1.verdict.json").read_text())[-1]
    reopen.reopen(c, "Q1P1", "repair", reason="one more repair")
    assert research.status(c, "Q1P1")["repair"]["action"] == last["action"]
    c = _verdict(c, "ITERATE")
    seen = _seen(monkeypatch)
    assert research.run_thread(c, "Q1P1") == "PAUSE-ON-ITERATE"          # one grant, one verdict: no further rounds
    stages = [r.stage for r in seen]
    assert stages == ["consolidate", "verify"]
    assert "This is a repair" in seen[0].prompt and str(last["action"]) in seen[0].prompt
    assert research.status(c, "Q1P1").get("grant") is None


@pytest.mark.parametrize("peers", [["ada"], ["ada", "emmy"]])
def test_a_classic_round_grant_dispatches_every_peer_again(tmp_path, monkeypatch, peers):
    c = _finished(tmp_path, "ITERATE", peers=peers, rounds=1)
    reopen.reopen(c, "Q1P1", "round", reason="one more round", note="look at the boundary case")
    c = _verdict(c, "ITERATE")
    seen = _seen(monkeypatch)
    assert research.run_thread(c, "Q1P1") == "PAUSE-ON-ITERATE"
    assert sorted(r.actor for r in seen if r.stage == "peer") == sorted(peers)


def test_a_classic_extend_grant_names_the_target_and_ends_on_its_verdict(tmp_path, monkeypatch):
    c = _finished(tmp_path, "DRAFT")
    reopen.reopen(c, "Q1P1", "extend", reason="top paper", note="prove the matching lower bound")
    c = _verdict(c, "ITERATE")
    seen = _seen(monkeypatch)
    assert research.run_thread(c, "Q1P1") == "PAUSE-ON-ITERATE"
    peer = [r for r in seen if r.stage == "peer"][0]
    assert "granted one extend round" in peer.prompt


def test_direct_eva_still_refuses_a_reopen(tmp_path):
    c = make(tmp_path, research_scheme="direct_eva")
    with pytest.raises(ValueError, match="research_scheme"):
        reopen.reopen(c, "Q1P1", "round", reason="x", note="y")


def test_stopped_repair_resumes_only_verifier_and_consumes_grant_once(tmp_path, monkeypatch):
    c = _finished(tmp_path, 'REVISE')
    reopen.reopen(c, 'Q1P1', 'repair', reason='one repair')
    c = _verdict(c, 'ITERATE'); seen = _seen(monkeypatch)
    checks = iter([False, True])
    assert research.run_thread(c, 'Q1P1', stop=lambda: next(checks)) == 'stopped'
    assert [r.stage for r in seen] == ['consolidate']
    assert research.status(c, 'Q1P1')['grant']
    assert research.run_thread(c, 'Q1P1') == 'PAUSE-ON-ITERATE'
    assert [r.stage for r in seen] == ['consolidate', 'verify']
    assert research.run_thread(c, 'Q1P1') == 'PAUSE-ON-ITERATE'
    assert len(seen) == 2


def test_changed_judged_note_refuses_reopen_without_side_effects(tmp_path):
    c = _finished(tmp_path, 'REVISE')
    d = c.thread_dir('Q1P1')
    (d/'Q1P1.tex').write_text('different note')
    before = (d/'status.json').read_bytes()
    with pytest.raises(ValueError, match='differs from the last judged'):
        reopen.reopen(c, 'Q1P1', 'repair', reason='one repair')
    assert (d/'status.json').read_bytes() == before
    assert not (d/'Q1P1.reopen.json').exists()

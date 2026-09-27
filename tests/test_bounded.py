"""Bounded runs and run_pair: exactly the listed pairs, resuming at the right stage."""
import shutil
import pytest
from pathfinder import edit, paper, research, runner, transport
from stubcampaign import make

needs_tex = pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")


def _stages(c, pair):
    return [r["stage"] for r in transport.receipts(c) if r["thread"] == pair]


def test_selection_is_validated(tmp_path):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    with pytest.raises(ValueError, match="duplicate"):
        runner.run(c, pairs=["Q1P1", "Q1P1"])
    with pytest.raises(ValueError, match="not on the shortlist"):
        runner.run(c, pairs=["Q2P2"])
    assert not hasattr(c, "selection")


@needs_tex
def test_bounded_run_ignores_unlisted_pairs_including_blocked_ones(tmp_path):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2", "Q1P3"))
    research.prepare(c, "Q1P2"); research._set(c, "Q1P2", status="BLOCKED", reason="unrelated")
    assert runner.run(c, interval=0.05, pairs=["Q1P1"]) == 0
    assert research.status(c, "Q1P1")["status"] == "DRAFT" and edit.status(c, "Q1P1")["status"] == "done"
    assert not (tmp_path / "threads/Q1P3").exists() and _stages(c, "Q1P2") == []


@needs_tex
def test_a_listed_blocked_pair_is_reported_and_the_others_still_run(tmp_path):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    research.prepare(c, "Q1P2"); research._set(c, "Q1P2", status="BLOCKED", reason="listed")
    assert runner.run(c, interval=0.05, pairs=["Q1P1", "Q1P2"]) == 1
    assert research.status(c, "Q1P1")["status"] == "DRAFT" and edit.status(c, "Q1P1")["status"] == "done"
    assert not (tmp_path / "health.json").exists()


@needs_tex
def test_nothing_to_run_returns_at_once(tmp_path, capsys):
    c = make(tmp_path)
    assert runner.run(c, interval=0.05, pairs=["Q1P1"]) == 0
    before = len(transport.receipts(c))
    assert runner.run(c, interval=0.05, pairs=["Q1P1"]) == 0
    assert "nothing to run" in capsys.readouterr().out and len(transport.receipts(c)) == before


@needs_tex
def test_run_pair_resumes_a_draft_at_edit(tmp_path):
    c = make(tmp_path)
    assert runner.run(c, interval=0.05, pairs=["Q1P1"]) == 0
    shutil.rmtree(tmp_path / "threads/Q1P1/edited")                    # DRAFT, edit unfinished
    before = _stages(c, "Q1P1")
    out = runner.run_pair(c, "Q1P1", interval=0.05)
    new = _stages(c, "Q1P1")[len(before):]
    assert "peer" not in new and "consolidate" not in new and new[0] == "edit"
    assert out["research"] == "DRAFT" and out["edit"] == "done" and out["paper"] == "ACCEPTED" and out["complete"]


@needs_tex
def test_run_pair_resumes_a_draft_at_paper(tmp_path):
    c = make(tmp_path)
    assert runner.run(c, interval=0.05, pairs=["Q1P1"]) == 0          # DRAFT, edit done, no paper
    before = _stages(c, "Q1P1")
    out = runner.run_pair(c, "Q1P1", interval=0.05)
    assert set(_stages(c, "Q1P1")[len(before):]) == {"author", "review"}
    assert out["paper"] == "ACCEPTED" and out["complete"]
    assert runner.run_pair(c, "Q1P1", interval=0.05)["complete"]       # complete: nothing more happens


@needs_tex
def test_run_pair_without_paper_stops_after_edit(tmp_path):
    c = make(tmp_path)
    out = runner.run_pair(c, "Q1P1", stages=("research", "edit"), interval=0.05)
    assert out["complete"] and out["paper"] == "none" and "author" not in _stages(c, "Q1P1")
    with pytest.raises(ValueError):
        runner.run_pair(c, "Q1P1", stages=("paper",))


@needs_tex
def test_run_pair_rejects_an_off_shortlist_pair_even_when_complete(tmp_path, monkeypatch):
    c = make(tmp_path, pairs=("Q1P1", "Q1P2"))
    assert runner.run(c, interval=0.05, pairs=["Q1P2"]) == 0          # Q1P2 DRAFT, edit done
    (tmp_path / "shortlist.json").write_text('{"pairs": [{"pair_id": "Q1P1"}]}')
    monkeypatch.setattr(paper, "run", lambda *a, **k: pytest.fail("paper dispatched for an unlisted pair"))
    with pytest.raises(ValueError, match="not on the shortlist"):
        runner.run_pair(c, "Q1P2", interval=0.05)


@needs_tex
def test_run_pair_rechecks_paper_state_under_the_lock(tmp_path, monkeypatch):
    c = make(tmp_path)
    assert runner.run(c, interval=0.05, pairs=["Q1P1"]) == 0          # DRAFT, edit done, paper due
    real_owner = runner.health.owner

    from contextlib import contextmanager
    @contextmanager
    def owner_after_another_finished(campaign):
        paper._set(campaign, "Q1P1", status="ACCEPTED", round=1)    # finished elsewhere before we own the campaign
        with real_owner(campaign):
            yield
    monkeypatch.setattr(runner.health, "owner", owner_after_another_finished)
    monkeypatch.setattr(paper, "run", lambda *a, **k: pytest.fail("paper rerun after it finished"))
    out = runner.run_pair(c, "Q1P1", interval=0.05)
    assert out["paper"] == "ACCEPTED" and out["complete"]

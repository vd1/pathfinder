"""Two independent paper reviewers, as a programme committee: "paper_reviewers": 2 runs two reviewer calls each
round, neither seeing the other; the paper is accepted only when both accept, and otherwise the author answers
both reviews' findings."""
import json, shutil
import pytest
from pathfinder import edit, paper, research, stub, transport
from stubcampaign import make

needs_tex = pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")


def _drafted(tmp_path, **kw):
    c = make(tmp_path, **kw)
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    return c


def _reviews(c, stage="review"):
    return [r for r in transport.receipts(c) if r.get("stage") == stage]


def _decide(monkeypatch, decisions):
    """The stub's review reply per reviewer actor: decisions["reviewer-2"] = ["AMEND", "ACCEPT"], one per round."""
    seen, real = {}, stub.reply
    def reply(campaign, request):
        if request.stage == "review":
            n = seen[request.actor] = seen.get(request.actor, 0) + 1
            plan = decisions.get(request.actor, ["ACCEPT"])
            d = plan[min(n, len(plan)) - 1]
            return json.dumps({"decision": d, "summary": f"{request.actor} round {n}: {d}",
                               "findings": [] if d == "ACCEPT" else [{"severity": "major", "issue": f"{request.actor} wants a fix",
                                                                      "where": "Section 2", "fix": "state the assumption"}]})
        return real(campaign, request)
    monkeypatch.setattr(stub, "reply", reply)


@needs_tex
def test_one_reviewer_stays_the_default(tmp_path):
    c = _drafted(tmp_path)
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    assert [r["actor"] for r in _reviews(c)] == ["reviewer"]


@needs_tex
def test_two_reviewers_must_both_accept(tmp_path, monkeypatch):
    c = _drafted(tmp_path, paper_reviewers=2, paper_rounds=2)
    _decide(monkeypatch, {"reviewer-2": ["AMEND", "ACCEPT"]})
    seen = []
    real = transport.execute
    monkeypatch.setattr(transport, "execute", lambda campaign, request: seen.append(request) or real(campaign, request))
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    assert [r["actor"] for r in _reviews(c)] == ["reviewer-1", "reviewer-2", "reviewer-1", "reviewer-2"]
    rounds = json.loads((c.thread_dir("Q1P1") / "paper/review.json").read_text())
    assert [r["decision"] for r in rounds] == ["AMEND", "ACCEPT"]
    assert [v["decision"] for v in rounds[0]["reviewers"]] == ["ACCEPT", "AMEND"]
    assert rounds[0]["findings"][0]["reviewer"] == "reviewer-2"
    second_author = [r for r in seen if r.stage == "author"][1]
    assert "reviewer-2 wants a fix" in second_author.prompt                # the author answers the amending review
    reviewer_2 = [r for r in seen if r.stage == "review" and r.actor == "reviewer-2"][0]
    assert "reviewer-1 round 1" not in reviewer_2.prompt                   # neither reviewer sees the other


@needs_tex
def test_a_disagreement_left_at_the_last_round_returns_the_paper(tmp_path, monkeypatch):
    c = _drafted(tmp_path, paper_reviewers=2, paper_rounds=1)
    _decide(monkeypatch, {"reviewer-1": ["AMEND"]})
    assert paper.run(c, "Q1P1") == "PAUSE-ON-AMEND"


@needs_tex
def test_each_reviewer_takes_its_own_route(tmp_path):
    c = _drafted(tmp_path, paper_reviewers=2, routes={"review/reviewer-1": {"model": "opus-like"},
                                                      "review/reviewer-2": {"model": "sol-like"}})
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    assert {r["actor"]: r["model"] for r in _reviews(c)} == {"reviewer-1": "opus-like", "reviewer-2": "sol-like"}


@pytest.mark.parametrize("bad", [0, 4, "2", True])
def test_a_bad_reviewer_count_is_refused(tmp_path, bad):
    with pytest.raises(ValueError, match="paper_reviewers"):
        make(tmp_path, paper_reviewers=bad)

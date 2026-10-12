"""A literature check before ACCEPT and an amend round from outside findings (nobel): "paper_review_search": true
gives the first reviewer web search and a prior-art duty, and `paper PAIR --amend FINDINGS.json` sends findings
found outside the stage to the author as the previous review, followed by a reviewer round."""
import json, shutil
import pytest
from pathfinder import cli, edit, paper, research, stub, transport
from stubcampaign import make

needs_tex = pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
OUTSIDE = [{"id": "N1", "severity": "major", "where": "Related work",
            "issue": "misses Zlokapa and Somma (arXiv:2404.03644)", "fix": "cite it and narrow the novelty claim"}]


def _drafted(tmp_path, **kw):
    c = make(tmp_path, **kw)
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    return c


def _seen(monkeypatch):
    seen, real = [], transport.execute
    monkeypatch.setattr(transport, "execute", lambda campaign, request: seen.append(request) or real(campaign, request))
    return seen


def _findings(tmp_path, value=None):
    f = tmp_path / "findings.json"
    f.write_text(json.dumps({"summary": "prior-art pass", "findings": OUTSIDE} if value is None else value))
    return f


@needs_tex
def test_reviewers_have_no_search_by_default(tmp_path, monkeypatch):
    c = _drafted(tmp_path)
    seen = _seen(monkeypatch)
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    r = [x for x in seen if x.stage == "review"][0]
    assert (r.tools, r.search) == (False, False) and "closest prior work" not in r.prompt


@needs_tex
def test_review_search_gives_the_first_reviewer_web_search_and_a_prior_art_duty(tmp_path, monkeypatch):
    c = _drafted(tmp_path, paper_review_search=True, paper_reviewers=2)
    seen = _seen(monkeypatch)
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    first, second = [x for x in seen if x.stage == "review"]
    assert (first.actor, first.tools, first.reads, first.search) == ("reviewer-1", True, True, True)
    assert "closest prior work" in first.prompt and "cite both" in first.prompt
    assert (second.tools, second.search) == (False, False) and "closest prior work" not in second.prompt


def test_a_bad_review_search_value_is_refused(tmp_path):
    with pytest.raises(ValueError, match="paper_review_search"):
        make(tmp_path, paper_review_search="yes")


@needs_tex
def test_outside_findings_reopen_an_accepted_paper_for_one_author_and_review_round(tmp_path, monkeypatch):
    c = _drafted(tmp_path)
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    seen = _seen(monkeypatch)
    assert paper.amend(c, "Q1P1", _findings(tmp_path)) == "ACCEPTED"
    assert [x.stage for x in seen] == ["author", "review"]
    author, reviewer = seen
    assert "Zlokapa and Somma" in author.prompt and "outside" in author.prompt
    assert "Zlokapa and Somma" in reviewer.prompt                     # the reviewer checks each was answered
    rounds = json.loads((c.thread_dir("Q1P1") / "paper/review.json").read_text())
    assert [(r["round"], r.get("source"), r["decision"]) for r in rounds] == [
        (1, None, "ACCEPT"), (2, "outside", "AMEND"), (3, None, "ACCEPT")]
    assert rounds[1]["findings"] == OUTSIDE and rounds[1]["summary"] == "prior-art pass"
    assert paper.status(c, "Q1P1")["status"] == "ACCEPTED" and paper.status(c, "Q1P1")["round"] == 3


@needs_tex
def test_a_bare_list_of_findings_is_accepted(tmp_path):
    c = _drafted(tmp_path)
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    assert paper.amend(c, "Q1P1", _findings(tmp_path, OUTSIDE)) == "ACCEPTED"


@needs_tex
def test_an_amend_the_reviewer_still_returns_pauses_on_amend(tmp_path, monkeypatch):
    c = _drafted(tmp_path)
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    real = stub.reply
    monkeypatch.setattr(stub, "reply", lambda campaign, request: json.dumps(
        {"decision": "AMEND", "summary": "still overclaims", "findings": [{"severity": "major", "issue": "x"}]})
        if request.stage == "review" else real(campaign, request))
    assert paper.amend(c, "Q1P1", _findings(tmp_path)) == "PAUSE-ON-AMEND"
    assert paper.status(c, "Q1P1")["reason"] == "still overclaims"


@needs_tex
def test_an_interrupted_amend_resumes_through_paper_without_a_second_outside_round(tmp_path, monkeypatch):
    c = _drafted(tmp_path)
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    real = transport.execute
    def fail_author(campaign, request):
        if request.stage == "author":
            return {"transport_failed": True, "failure": {"class": "launch", "scope": "call", "retry": True}, "text": ""}
        return real(campaign, request)
    monkeypatch.setattr(transport, "execute", fail_author)
    with pytest.raises(transport.TransportFailed):
        paper.amend(c, "Q1P1", _findings(tmp_path))
    assert paper.status(c, "Q1P1")["status"] == "stopped"
    with pytest.raises(SystemExit, match="in progress"):
        paper.amend(c, "Q1P1", _findings(tmp_path))
    monkeypatch.setattr(transport, "execute", real)
    assert paper.run(c, "Q1P1") == "ACCEPTED"                         # past paper_rounds: the amend's round still runs
    rounds = json.loads((c.thread_dir("Q1P1") / "paper/review.json").read_text())
    assert [r.get("source") for r in rounds] == [None, "outside", None]


@needs_tex
@pytest.mark.parametrize("value, message", [([], "no findings"), ({"findings": "x"}, "findings"),
                                            ([{"issue": 3}], "issue")])
def test_bad_findings_are_refused_before_anything_changes(tmp_path, value, message):
    c = _drafted(tmp_path)
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    with pytest.raises(SystemExit, match=message):
        paper.amend(c, "Q1P1", _findings(tmp_path, value))
    assert len(json.loads((c.thread_dir("Q1P1") / "paper/review.json").read_text())) == 1


def test_a_pair_without_a_finished_paper_is_refused(tmp_path):
    c = _drafted(tmp_path)
    with pytest.raises(SystemExit, match="ACCEPTED or PAUSE-ON-AMEND"):
        paper.amend(c, "Q1P1", _findings(tmp_path))


@needs_tex
def test_the_command_line_runs_the_amend(tmp_path, capsys):
    c = _drafted(tmp_path)
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    cli.main(["--root", str(c.root), "paper", "Q1P1", "--amend", str(_findings(tmp_path))])
    assert "Q1P1: ACCEPTED" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="needs a pair"):
        cli.main(["--root", str(c.root), "paper", "--amend", str(_findings(tmp_path))])

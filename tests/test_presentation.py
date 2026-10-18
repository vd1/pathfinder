"""The presentation pass after ACCEPT (nobel pilot on Q472-P527 and Q138-P465, 18 October 2026). Reviewers accept
papers with unbound notation, pipeline labels in the prose and minor findings left open. With "presentation": true
an accepted paper goes through an editor (notation, calibrated background, salience, framing, and closing the open
findings), a lookup stage with web search for what needs one, a fresh check by one or two checkers, at most two
restricted correction cycles behind a guard, and ends CLEARED, tied to the hash of the manuscript it cleared. A
meaning or claim problem in the accepted text goes to one targeted review call; a confirmed one is amended
automatically once per paper (an author round and a review round), then the pass starts again; a second one stops
at RETURNED for the operator."""
import json, shutil
import pytest
from pathfinder import campaign_state, config, edit, paper, playbook, presentation, research, runner, stub, transport
from stubcampaign import make

needs_tex = pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
MINOR = {"id": "F1", "severity": "minor", "where": "Introduction", "issue": "cite arXiv:2605.31430", "fix": "cite it"}


def _accepted(tmp_path, monkeypatch, review_findings=(MINOR,), **kw):
    c = make(tmp_path, presentation=True, **kw)
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    real = stub.reply
    def accept_with_findings(campaign, request):
        if request.stage == "review" and request.actor in ("reviewer", "reviewer-1", "reviewer-2"):
            return json.dumps({"decision": "ACCEPT", "summary": "fine", "findings": list(review_findings)})
        return real(campaign, request)
    monkeypatch.setattr(stub, "reply", accept_with_findings)
    assert paper.run(c, "Q1P1") == "ACCEPTED"
    monkeypatch.setattr(stub, "reply", real)
    return c


def _script(monkeypatch, replies):
    """replies: {"stage/actor": [reply or function of the request, ...]}; other calls go to the stub."""
    seen, real = [], stub.reply
    def reply(campaign, request):
        seen.append(request)
        queue = replies.get(f"{request.stage}/{request.actor}")
        if queue:
            r = queue.pop(0)
            return r(request) if callable(r) else r
        return real(campaign, request)
    monkeypatch.setattr(stub, "reply", reply)
    return seen


def manuscript(prompt):
    return prompt.split("## manuscript\n\n", 1)[1].split("\n\n## ", 1)[0]


def edited(change=None, title=None, findings=(), escalations=(), bib=None):
    def make_reply(request):
        tex = manuscript(request.prompt)
        if change:
            tex = tex.replace(*change)
        report = {"changelog": ["Introduction, job 1: defined U"], "title": title, "findings": list(findings),
                  "escalations": list(escalations)}
        return ("===PAPER===\n" + tex + ("\n===BIBTEX===\n" + bib if bib else "")
                + "\n===REPORT===\n" + json.dumps(report))
    return make_reply


def check(*findings):
    return json.dumps({"findings": list(findings), "clear": not findings})


NOTATION = {"kind": "notation", "where": "Introduction", "issue": "U is unbound", "fix": "define U"}
CLAIM = {"kind": "claim", "where": "Abstract", "issue": "exact calibration claimed, body is approximate", "fix": "say approximate"}
F1_APPLIED = {"id": "F1", "status": "applied", "reason": "cited"}


def _final(c):
    return (c.thread_dir("Q1P1") / "paper/presentation" / presentation.state(c, "Q1P1")["stage"] / "paper.tex").read_text()


@needs_tex
def test_a_clear_check_clears_the_paper_with_the_hash_of_its_manuscript(tmp_path, monkeypatch):
    import hashlib
    c = _accepted(tmp_path, monkeypatch)
    seen = _script(monkeypatch, {"present/editor": [edited(("The stub cites", "We cite"), findings=[F1_APPLIED])],
                                 "present_check/checker": [check()]})
    assert presentation.run(c, "Q1P1") == "CLEARED"
    s = paper.status(c, "Q1P1")
    assert s["status"] == "CLEARED" and s["cleared_sha256"] == hashlib.sha256(_final(c).encode()).hexdigest()
    assert "We cite one source" in _final(c)
    assert (c.thread_dir("Q1P1") / "paper/paper.tex").read_text().count("The stub cites") == 1   # the accepted paper stays
    editor, checker = seen
    assert (editor.stage, editor.actor, editor.search) == ("present", "editor", False)
    assert "cite arXiv:2605.31430" in editor.prompt and "Abstract of Q1." in editor.prompt   # open findings, the source papers
    assert "stub finding by ada" not in editor.prompt                                       # never the ledger
    assert "Abstract of Q1." not in checker.prompt and "defined U" in checker.prompt        # the check reads the change log


@needs_tex
def test_the_editor_reads_the_full_text_of_the_source_papers(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    (c.root / "sources").mkdir()
    (c.root / "sources" / "q1.tex").write_text("Full text of the first source paper.")
    (c.root / "sources" / "p1.txt").write_text("Full text of the second source paper.")
    seen = _script(monkeypatch, {"present/editor": [edited(findings=[F1_APPLIED])], "present_check/checker": [check()]})
    assert presentation.run(c, "Q1P1") == "CLEARED"
    assert "Full text of the first source paper." in seen[0].prompt and "Full text of the second" in seen[0].prompt


@needs_tex
def test_the_editor_may_retitle_the_paper(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    _script(monkeypatch, {"present/editor": [edited(title="Whole-measure learning at inverse-square cost", findings=[F1_APPLIED])],
                          "present_check/checker": [check()]})
    assert presentation.run(c, "Q1P1") == "CLEARED"
    assert "\\title{Whole-measure learning at inverse-square cost}" in _final(c) and "Stub paper" not in _final(c)


@needs_tex
def test_a_finding_that_needs_a_lookup_goes_to_a_stage_with_search(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    seen = _script(monkeypatch, {
        "present/editor": [edited(findings=[{"id": "F1", "status": "needs lookup", "reason": "citation metadata"}])],
        "present_lookup/lookup": [edited(("The stub cites", "The stub, as checked, cites"), findings=[F1_APPLIED])],
        "present_check/checker": [check()]})
    assert presentation.run(c, "Q1P1") == "CLEARED"
    lookup = [r for r in seen if r.stage == "present_lookup"][0]
    assert lookup.search and "needs lookup" in lookup.prompt and "as checked" in _final(c)


@needs_tex
def test_a_lookup_left_open_stops_the_paper_short_of_clearance(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    still = [{"id": "F1", "status": "needs lookup", "reason": "no record found"}]
    _script(monkeypatch, {"present/editor": [edited(findings=still)], "present_lookup/lookup": [edited(findings=still)],
                          "present_check/checker": [check()]})
    assert presentation.run(c, "Q1P1") == "PAUSE-ON-PRESENT"
    assert "F1" in presentation.state(c, "Q1P1")["reason"] and paper.status(c, "Q1P1")["status"] == "ACCEPTED"


@needs_tex
def test_an_open_finding_left_silent_is_reported_and_blocks_clearance(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    _script(monkeypatch, {"present/editor": [edited()], "present_check/checker": [check()]})
    assert presentation.run(c, "Q1P1") == "PAUSE-ON-PRESENT"
    assert "F1" in presentation.state(c, "Q1P1")["reason"]


@needs_tex
def test_notation_findings_go_to_a_correction_cycle_that_sees_the_accepted_text(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    seen = _script(monkeypatch, {
        "present/editor": [edited(findings=[F1_APPLIED])],
        "present/corrector": [edited(("\\cite{stub}.", "\\cite{stub}. Here U denotes the unitary."))],
        "present_check/checker": [check(NOTATION), check()]})
    assert presentation.run(c, "Q1P1") == "CLEARED"
    corrector = [r for r in seen if r.actor == "corrector"][0]
    assert "U is unbound" in corrector.prompt and "## accepted manuscript" in corrector.prompt
    s = presentation.state(c, "Q1P1")
    assert s["stage"] == "correct-1" and s["cycles"] == 1 and "Here U denotes" in _final(c)


@needs_tex
def test_a_correction_the_guard_refuses_is_discarded(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch, presentation_cycles=1)
    _script(monkeypatch, {
        "present/editor": [edited(findings=[F1_APPLIED])],
        "present/corrector": [edited(("\\cite{stub}.", "\\cite{stub}. Its constant is 7."))],
        "present_check/checker": [check(NOTATION)]})
    assert presentation.run(c, "Q1P1") == "PAUSE-ON-PRESENT"
    s = presentation.state(c, "Q1P1")
    assert s["stage"] == "pass" and "number 7" in s["reason"] and "constant is 7" not in _final(c)


@needs_tex
def test_findings_left_at_the_cycle_limit_stop_short_of_clearance(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    _script(monkeypatch, {"present/editor": [edited(findings=[F1_APPLIED])],
                          "present/corrector": [edited(), edited()],
                          "present_check/checker": [check(NOTATION)] * 3})
    assert presentation.run(c, "Q1P1") == "PAUSE-ON-PRESENT"
    assert presentation.state(c, "Q1P1")["cycles"] == 2


@needs_tex
def test_two_checkers_report_the_union_of_their_findings(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch, presentation_checkers=2)
    seen = _script(monkeypatch, {"present/editor": [edited(findings=[F1_APPLIED])],
                                 "present/corrector": [edited(("\\cite{stub}.", "\\cite{stub}. U is the unitary."))],
                                 "present_check/checker-1": [check(), check()],
                                 "present_check/checker-2": [check(NOTATION), check()]})
    assert presentation.run(c, "Q1P1") == "CLEARED"
    assert [r.actor for r in seen if r.stage == "present_check"] == ["checker-1", "checker-2"] * 2
    first = json.loads((c.thread_dir("Q1P1") / "paper/presentation/pass/check.json").read_text())
    assert [f["checker"] for f in first["findings"]] == ["checker-2"]


def _amend_accepts(replies):
    replies.setdefault("review/reviewer", []).append(json.dumps({"decision": "ACCEPT", "summary": "amended", "findings": []}))
    return replies


@needs_tex
def test_a_confirmed_overclaim_is_amended_once_and_the_pass_starts_again(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    seen = _script(monkeypatch, _amend_accepts({
        "present/editor": [edited(findings=[F1_APPLIED]), edited(findings=[F1_APPLIED])],
        "present_check/checker": [check(CLAIM), check()],
        "review/claims": [json.dumps({"items": [{"id": "C1", "decision": "confirmed", "reason": "the body calibrates approximately",
                                                 "fix": "say approximate"}]})]}))
    assert presentation.run(c, "Q1P1") == "CLEARED"
    stages = [(r.stage, r.actor) for r in seen]
    assert stages[:4] == [("present", "editor"), ("present_check", "checker"), ("review", "claims"), ("author", "author")]
    assert stages[4:] == [("review", "reviewer"), ("present", "editor"), ("present_check", "checker")]
    author = [r for r in seen if r.stage == "author"][0]
    assert "exact calibration claimed" in author.prompt
    s = paper.status(c, "Q1P1")
    assert s["status"] == "CLEARED" and len(s["presentation_amends"]) == 1
    assert s["presentation_amends"][0]["result"] == "ACCEPTED" and s["presentation_amends"][0]["findings"] == 1


@needs_tex
def test_a_second_confirmed_overclaim_stops_at_returned_with_the_findings_ready(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    confirmed = json.dumps({"items": [{"id": "C1", "decision": "confirmed", "reason": "r", "fix": "f"}]})
    seen = _script(monkeypatch, _amend_accepts({
        "present/editor": [edited(findings=[F1_APPLIED])] * 2,
        "present_check/checker": [check(CLAIM), check(CLAIM)],
        "review/claims": [confirmed, confirmed]}))
    assert presentation.run(c, "Q1P1") == "RETURNED"
    assert [r.stage for r in seen].count("author") == 1
    found = json.loads((c.thread_dir("Q1P1") / "paper/presentation/amend-findings.json").read_text())
    assert found["findings"][0]["issue"].startswith("exact calibration claimed")
    assert paper.status(c, "Q1P1")["status"] == "ACCEPTED"
    actions = playbook.next_actions(c)
    assert any("--amend" in (a["command"] or "") and "amend-findings.json" in a["command"] for a in actions)


@needs_tex
def test_an_editor_escalation_goes_to_the_targeted_review_and_a_dismissed_one_clears(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    seen = _script(monkeypatch, {
        "present/editor": [edited(findings=[F1_APPLIED], escalations=[{"where": "Lemma 1", "issue": "two plausible meanings of r"}])],
        "present_check/checker": [check()],
        "review/claims": [json.dumps({"items": [{"id": "C1", "decision": "dismissed", "reason": "the body fixes r"}]})]})
    assert presentation.run(c, "Q1P1") == "CLEARED"
    claims = [r for r in seen if r.actor == "claims"][0]
    assert "two plausible meanings" in claims.prompt and "## accepted paper" in claims.prompt


@needs_tex
def test_a_problem_the_pass_introduced_stops_short_of_clearance(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch, presentation_cycles=0)
    _script(monkeypatch, {"present/editor": [edited(findings=[F1_APPLIED])], "present_check/checker": [check(CLAIM)],
                          "review/claims": [json.dumps({"items": [{"id": "C1", "decision": "introduced", "reason": "added by the edit"}]})]})
    assert presentation.run(c, "Q1P1") == "PAUSE-ON-PRESENT"
    assert "introduced" in presentation.state(c, "Q1P1")["reason"]


@needs_tex
def test_a_changed_accepted_paper_starts_the_pass_afresh(tmp_path, monkeypatch):
    c = _accepted(tmp_path, monkeypatch)
    _script(monkeypatch, {"present/editor": [edited(findings=[F1_APPLIED]), edited(findings=[F1_APPLIED])],
                          "present_check/checker": [check(), check()]})
    assert presentation.run(c, "Q1P1") == "CLEARED"
    assert presentation.run(c, "Q1P1") == "CLEARED"                 # cleared already: no call
    pd = c.thread_dir("Q1P1") / "paper"
    (pd / "paper.tex").write_text((pd / "paper.tex").read_text().replace("Stub paper", "Stub paper, amended"))
    paper._set(c, "Q1P1", status="ACCEPTED")
    assert presentation.run(c, "Q1P1") == "CLEARED"
    assert "Stub paper, amended" in _final(c)


@needs_tex
def test_the_runner_takes_an_accepted_paper_through_the_pass(tmp_path, monkeypatch):
    c = make(tmp_path, presentation=True)
    seen = _script(monkeypatch, {"present/editor": [edited()], "present_check/checker": [check()]})
    out = runner.run_pair(c, "Q1P1")
    assert out["paper"] == "CLEARED" and out["complete"]
    assert ("present", "editor") in [(r.stage, r.actor) for r in seen]
    assert campaign_state.lifecycle({"status": "DRAFT"}, {"status": "done"}, {"status": "CLEARED"}, "idle") == "cleared"


@needs_tex
def test_without_the_setting_no_pass_runs(tmp_path, monkeypatch):
    c = make(tmp_path)
    seen = _script(monkeypatch, {})
    assert runner.run_pair(c, "Q1P1")["paper"] == "ACCEPTED"
    assert not [r for r in seen if r.stage.startswith("present")]


@pytest.mark.parametrize("key, value", [("presentation", "yes"), ("presentation_checkers", 3), ("presentation_cycles", 3),
                                        ("release", {"disclosure": 4})])
def test_bad_presentation_settings_are_refused(tmp_path, key, value):
    with pytest.raises(ValueError, match=key):
        make(tmp_path, **{key: value})

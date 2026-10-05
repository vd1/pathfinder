"""PCE editing in the engine ("edit_scheme": "pce"): julien-2's role loop over the single editor's note."""
import json, shutil
from pathlib import Path
import pytest
from pathfinder import edit, pce, research, stub, transport
from pathfinder.thread import Stopped
from stubcampaign import make

needs_tex = pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
ORDER = ["author", "archivist", "fact-checker", "critic", "editor"]


def ready(tmp_path, **kw):
    """A terminal pair whose single editor has written its note: the PCE round's baseline, no TeX needed."""
    c = make(tmp_path, edit_scheme="pce", **kw)
    research.run_thread(c, "Q1P1")
    ed = c.thread_dir("Q1P1") / "edited"; ed.mkdir(exist_ok=True)
    (ed / "note.tex").write_text(stub.READABLE); (ed / "references.bib").write_text(stub.BIB)
    return c


def script(monkeypatch, campaign, **replies):
    """pce._dispatch answered by the stub's role replies; replies["fact_checker"] etc. is a list, one entry per
    call of that role: a verdict for the stub reply, a callable on the prompt, or None for the default."""
    calls = []

    def dispatch(c, pair_id, role, prompt, seconds=None):
        n = sum(1 for call in calls if call["role"] == role)
        planned = (replies.get(role.replace("-", "_")) or [])
        entry = planned[n] if n < len(planned) else None
        text = entry(prompt) if callable(entry) else stub.pce_reply(campaign, role, prompt, verdict=entry)
        calls.append({"role": role, "prompt": prompt})
        return {"role": role, "outcome": "completed", "text": text}

    monkeypatch.setattr(pce, "_dispatch", dispatch)
    return calls


@pytest.mark.parametrize("raw, match", [
    ({"edit_scheme": "pce-loop"}, "edit_scheme"),
    ({"pce": {"passes": 0}}, "pce.passes"),
    ({"pce": {"passes": True}}, "pce.passes"),
    ({"pce": {"fact_checks": 9}}, "pce.fact_checks"),
    ({"pce": {"critic": {"profile": "Computational Chemist", "remit": "x"}}}, "pce.critic"),
    ({"pce": {"critic": {"profile": "chemist"}}}, "pce.critic"),
    ({"pce": {"rounds": 2}}, "pce must be an object"),
])
def test_a_malformed_edit_scheme_or_pce_setting_fails_at_load(tmp_path, raw, match):
    with pytest.raises(ValueError, match=match):
        make(tmp_path, **raw)


def test_one_pass_runs_every_role_in_order_and_the_editor_accepts(tmp_path, monkeypatch):
    c = ready(tmp_path)
    calls = script(monkeypatch, c)
    out = pce.run(c, "Q1P1")
    assert out["status"] == "accepted" and out["passes"] == 1
    assert [call["role"] for call in calls] == ORDER
    root = pce.workflow(c, "Q1P1")
    for name in ("brief.md", "state.json", "references.bib", "input-manifest.json", "result.json", pce.DRAFT,
                 pce.CLAIMS, pce.BASELINE, "sources/internal/account.tex", "sources/external/Q.txt",
                 "sources/external/P.txt", "sources/external/research-supplement.md",
                 "reviews/current/fact-check.json", "reviews/current/critic-reader.md", "reviews/editor-feedback.md",
                 "reviews/history/pass-01-fact-check.json", "reviews/history/pass-01-reader-critic.md",
                 "reviews/history/pass-01-editor.json"):
        assert (root / name).is_file(), name
    hist = pce.history(c, "Q1P1")
    assert len(hist) == 1 and hist[0]["draft"] == (root / pce.DRAFT).read_text()
    assert "Revised by the stub PCE author, pass 1." in hist[0]["draft"]
    assert len(list((root / "revisions/history").glob("*-pass-01-custody.json"))) == 1
    assert [d["role"] for d in pce.dispatches(c, "Q1P1")] == ORDER
    supplement = (root / "sources/external/research-supplement.md").read_text()
    assert "## ledger.jsonl" in supplement and "stub finding by ada" in supplement


def test_each_role_sees_exactly_its_read_scope(tmp_path, monkeypatch):
    c = ready(tmp_path)
    calls = script(monkeypatch, c, fact_checker=["fail"])         # a second pass, so history exists
    pce.run(c, "Q1P1")
    seen = {}
    for call in calls:
        seen.setdefault(call["role"], []).append(set(json.loads(call["prompt"].split("Allowed input files:\n", 1)[1])))
    account, baseline = "sources/internal/account.tex", pce.BASELINE
    for role in ("fact-checker", "critic"):
        for files in seen[role]:
            assert account not in files and baseline not in files
            assert not any(n.startswith(("reviews/", "revisions/")) for n in files), role
            assert {"sources/external/Q.txt", "sources/external/P.txt", pce.DRAFT} <= files
    assert {account, baseline} <= seen["author"][0] and "reviews/history/pass-01-fact-check.json" in seen["author"][1]
    assert {account, baseline, "reviews/history/pass-02-fact-check.json"} <= seen["editor"][0]
    assert not any(n.startswith("sources/") for n in seen["archivist"][0])


def test_a_failed_gate_sends_the_next_pass_back_to_the_author(tmp_path, monkeypatch):
    c = ready(tmp_path)
    calls = script(monkeypatch, c, critic=["revise"])
    out = pce.run(c, "Q1P1")
    assert out["status"] == "accepted" and out["passes"] == 2
    assert [call["role"] for call in calls] == ORDER[:4] + ORDER
    assert [h["pass"] for h in pce.history(c, "Q1P1")] == [1, 2]
    assert "pass 1." in pce.history(c, "Q1P1")[0]["draft"] and "pass 2." in pce.history(c, "Q1P1")[1]["draft"]


def test_the_pass_allowance_ends_the_round_without_acceptance(tmp_path, monkeypatch):
    c = ready(tmp_path, pce={"passes": 3})
    calls = script(monkeypatch, c, editor=["revise"] * 3)
    out = pce.run(c, "Q1P1")
    assert out["status"] == "review_required" and "pass allowance exhausted" in out["reason"] and out["passes"] == 3
    assert [call["role"] for call in calls] == ORDER * 3
    assert pce.run(c, "Q1P1") == out and len(calls) == 15        # an ended round is read back, not rerun


@pytest.mark.parametrize("replies, reason", [
    ({"author": [lambda prompt: "I could not do it."]}, "pass-01: reply holds no JSON"),
    ({"author": [lambda prompt: json.dumps({"files": {pce.DRAFT: "plain words", pce.CLAIMS: "[]"}})]}, "whole LaTeX document"),
    ({"fact_checker": ["contaminated"]}, "fact-checker's context was contaminated"),
    ({"critic": ["contaminated"]}, "critic's context was contaminated"),
    ({"editor": [lambda prompt: json.dumps({"files": {"reviews/editor-feedback.md": json.dumps(
        {"decision": "accept", "findings": ["x"], "feedback": "y", "evidence_change_requested": True})}})]}, "evidence change"),
    ({"fact_checker": [lambda prompt: stub.pce_reply(None, "fact-checker", prompt).replace(
        "sources/external/research-supplement.md", "sources/internal/account.tex")]}, "outside the approved external sources"),
])
def test_a_reply_the_contract_refuses_ends_the_round_for_review(tmp_path, monkeypatch, replies, reason):
    c = ready(tmp_path)
    script(monkeypatch, c, **replies)
    out = pce.run(c, "Q1P1")
    assert out["status"] == "review_required" and reason in out["reason"]


def test_a_stopped_round_resumes_without_paying_for_a_call_twice(tmp_path, monkeypatch):
    c = ready(tmp_path)
    calls = script(monkeypatch, c)
    with pytest.raises(Stopped):
        pce.run(c, "Q1P1", stop=lambda: any(call["role"] == "archivist" for call in calls))
    assert [call["role"] for call in calls] == ["author", "archivist"] and not (pce.workflow(c, "Q1P1") / "result.json").exists()
    assert pce.run(c, "Q1P1")["status"] == "accepted"
    assert [call["role"] for call in calls] == ORDER


def test_changed_inputs_under_a_begun_round_refuse_to_resume(tmp_path, monkeypatch):
    c = ready(tmp_path)
    calls = script(monkeypatch, c)
    with pytest.raises(Stopped):
        pce.run(c, "Q1P1", stop=lambda: bool(calls))
    (c.thread_dir("Q1P1") / "edited" / "note.tex").write_text(stub.READABLE.replace("one source", "two sources"))
    with pytest.raises(pce.Changed, match="changed since it began"):
        pce.run(c, "Q1P1")


def test_an_append_overlay_reaches_its_role(tmp_path, monkeypatch):
    c = ready(tmp_path, pce={"critic": {"profile": "computational-chemist", "remit": "Next decision for a chemist."}})
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "pce-critic.append.md").write_text("Read as a computational chemist would.\n")
    calls = script(monkeypatch, c)
    assert pce.run(c, "Q1P1")["status"] == "accepted"
    critic = next(call["prompt"] for call in calls if call["role"] == "critic")
    assert "Read as a computational chemist would." in critic and "- Profile: computational-chemist" in critic
    assert (pce.workflow(c, "Q1P1") / "reviews/current/critic-computational-chemist.md").exists()


def test_pce_calls_go_through_transport_with_routes_and_receipts(tmp_path):
    c = ready(tmp_path, routes={"edit/pce-critic": {"model": "stub-critic"}})
    assert pce.run(c, "Q1P1")["status"] == "accepted"
    rows = [r for r in transport.receipts(c) if r["stage"] == "edit"]
    assert [r["actor"] for r in rows] == [f"pce-{role}" for role in ORDER]
    critic = next(r for r in rows if r["actor"] == "pce-critic")
    assert critic["model"] == "stub-critic" and critic["route"]["key"] == "edit/pce-critic"
    receipt = next(d for d in pce.dispatches(c, "Q1P1") if d["role"] == "critic")["receipt"]
    required = {"role", "backend", "model", "execution_class", "prompt_digest", "provider_job_id", "raw_response",
                "outcome", "latency", "token_usage", "cost"}
    assert required <= set(receipt) and receipt["model"] == "stub-critic"


def test_a_prompt_over_the_limit_ends_the_round_for_review_without_a_call(tmp_path):
    c = ready(tmp_path, max_prompt_chars=2000)
    out = pce.run(c, "Q1P1")
    assert out["status"] == "review_required" and "input too large" in out["reason"]
    assert all(r["outcome"] == "refused" for r in transport.receipts(c) if r["stage"] == "edit")


@needs_tex
def test_the_single_editor_stays_the_default(tmp_path):
    c = make(tmp_path)
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    assert not (c.thread_dir("Q1P1") / "edited" / "pce").exists() and "scheme" not in edit.status(c, "Q1P1")


@needs_tex
def test_edit_runs_the_round_and_the_accepted_draft_becomes_the_note(tmp_path):
    c = make(tmp_path, edit_scheme="pce")
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    s = edit.status(c, "Q1P1")
    assert s["status"] == "done" and s["scheme"] == "pce" and s["editorial_status"] == "accepted"
    ed = c.thread_dir("Q1P1") / "edited"
    assert (ed / "note.tex").read_text() == (ed / "pce" / pce.DRAFT).read_text() and (ed / "note.pdf").exists()
    assert (ed / "pce" / pce.BASELINE).read_text() == stub.READABLE
    actors = [r["actor"] for r in transport.receipts(c) if r["stage"] == "edit"]
    assert actors == ["editor"] + [f"pce-{role}" for role in ORDER]
    before = len(transport.receipts(c))
    assert edit.run(c, "Q1P1") == "done" and len(transport.receipts(c)) == before        # done stays done


@needs_tex
def test_an_unaccepted_round_keeps_the_single_editor_note(tmp_path):
    c = make(tmp_path, edit_scheme="pce", stub={"pce_editor": "revise"})
    research.run_thread(c, "Q1P1")
    assert edit.run(c, "Q1P1") == "done"
    s = edit.status(c, "Q1P1")
    assert s["editorial_status"] == "review_required" and "pass allowance exhausted" in s["editorial_reason"]
    assert (c.thread_dir("Q1P1") / "edited" / "note.tex").read_text() == stub.READABLE


@needs_tex
def test_an_accepted_draft_that_does_not_build_keeps_the_baseline(tmp_path, monkeypatch):
    c = make(tmp_path, edit_scheme="pce")
    research.run_thread(c, "Q1P1")
    broken = lambda prompt: json.loads(stub.pce_reply(c, "author", prompt))["files"] | {
        pce.DRAFT: stub.READABLE.replace("\\section", "\\nosuchcommand\\section")}
    script(monkeypatch, c, author=[lambda prompt: json.dumps({"files": broken(prompt)})])
    assert edit.run(c, "Q1P1") == "done"
    s = edit.status(c, "Q1P1")
    assert s["editorial_status"] == "accepted" and s["accepted_note"] is False and "build" in s["presentation_error"]
    assert (c.thread_dir("Q1P1") / "edited" / "note.tex").read_text() == stub.READABLE


@needs_tex
def test_a_transport_failure_stops_the_edit_and_a_rerun_resumes(tmp_path, monkeypatch):
    c = make(tmp_path, edit_scheme="pce")
    research.run_thread(c, "Q1P1")
    real = pce._dispatch

    def fail_at_critic(campaign, pair_id, role, prompt, seconds=None):
        if role == "critic":
            raise transport.TransportFailed(pair_id, failure={"class": "timeout"})
        return real(campaign, pair_id, role, prompt, seconds)
    monkeypatch.setattr(pce, "_dispatch", fail_at_critic)
    with pytest.raises(transport.TransportFailed):
        edit.run(c, "Q1P1")
    s = edit.status(c, "Q1P1")
    assert s["status"] == "stopped" and s["failure"]["class"] == "timeout"
    monkeypatch.setattr(pce, "_dispatch", real)
    assert edit.run(c, "Q1P1") == "done" and edit.status(c, "Q1P1")["editorial_status"] == "accepted"
    pce_actors = [r["actor"] for r in transport.receipts(c) if r["actor"].startswith("pce-")]
    assert pce_actors == [f"pce-{role}" for role in ORDER]   # author, archivist and fact-checker were not paid twice


@needs_tex
def test_changed_inputs_block_the_edit_for_the_operator(tmp_path, monkeypatch):
    c = make(tmp_path, edit_scheme="pce")
    research.run_thread(c, "Q1P1")
    monkeypatch.setattr(pce, "run", lambda *a, **k: (_ for _ in ()).throw(pce.Changed("inputs changed")))
    assert edit.run(c, "Q1P1") == "blocked"
    assert edit.status(c, "Q1P1")["status"] == "blocked" and "inputs changed" in edit.status(c, "Q1P1")["reason"]


# The research supplement: the research record as the fact-checker's evidence, each entry with its standing

def _ledger(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps({"seq": i, "actor": "ada", "kind": k, "text": t, "supersedes": s, "seen": None}) + "\n"
                            for i, (k, t, s) in enumerate(rows, 1)))


def test_the_supplement_marks_each_entrys_standing(tmp_path):
    c = ready(tmp_path)
    d = c.thread_dir("Q1P1")
    _ledger(d / "ledger.jsonl", [("finding", "The bound is 3.", None),
                                 ("finding", "The bound is 2.", 1),                       # supersedes #1
                                 ("objection", "#2 assumes independence.", None),
                                 ("correction", "#2 holds only for n > 5.", None),
                                 ("finding", "Answering #3: independence is shown in eq. 4.", None),
                                 ("objection", "#5 cites the wrong equation.", None),
                                 ("ready", "ready", None)])
    _ledger(d / "branches/branch-1/ledger.jsonl", [("finding", "A branch result.", None)])
    text = pce._supplement(c, "Q1P1", 100_000)
    joint, branch = text.split("## branches/branch-1/ledger.jsonl")
    assert "the joint thread: the research the account reports" in joint
    lines = {l.split(" ", 1)[0]: l for l in joint.splitlines() if l.startswith("#") and not l.startswith("##")}
    assert "superseded by #2" in lines["#1"]
    assert "objected to by #3" in lines["#2"] and "corrected by #4" in lines["#2"]
    assert "answered by #5" in lines["#3"]
    assert "unanswered" in lines["#6"] and "objected to by #6" in lines["#5"]
    assert "#7" not in lines                                                             # ready entries carry no evidence
    assert joint.index("## ledger.jsonl") < text.index("## branches/branch-1/ledger.jsonl")
    assert "not adopted unless the joint ledger cites it" in branch[:300]


def test_the_fact_checker_is_told_how_standing_limits_support(tmp_path, monkeypatch):
    c = ready(tmp_path)
    calls = script(monkeypatch, c)
    pce.run(c, "Q1P1")
    prompt = next(call["prompt"] for call in calls if call["role"] == "fact-checker")
    assert "superseded" in prompt and "basis" in prompt and "research record" in prompt


def _fact(basis, evidence):
    def reply(prompt):
        out = json.loads(stub.pce_reply(None, "fact-checker", prompt))
        for name, text in out["files"].items():
            report = json.loads(text)
            for claim in report["claims"]:
                claim["basis"], claim["evidence"] = basis, evidence
            out["files"][name] = json.dumps(report)
        return json.dumps(out)
    return reply


@pytest.mark.parametrize("basis, evidence", [
    ("papers", ["sources/external/research-supplement.md"]),            # a papers basis needs a paper
    ("research record", ["sources/external/Q.txt"]),                    # a record basis needs the supplement
    ("both", ["sources/external/Q.txt"]),
])
def test_a_claims_basis_must_match_its_evidence(tmp_path, monkeypatch, basis, evidence):
    c = ready(tmp_path)
    script(monkeypatch, c, fact_checker=[_fact(basis, evidence)])
    out = pce.run(c, "Q1P1")
    assert out["status"] == "review_required" and "does not match its evidence" in out["reason"]


def test_the_round_counts_the_basis_of_its_supported_claims(tmp_path, monkeypatch):
    c = ready(tmp_path)
    script(monkeypatch, c, fact_checker=[_fact("both", ["sources/external/Q.txt", "sources/external/research-supplement.md"])])
    out = pce.run(c, "Q1P1")
    assert out["status"] == "accepted" and out["basis"] == {"papers": 0, "research record": 0, "both": 1}


def test_the_edit_record_carries_the_claim_basis(tmp_path, monkeypatch):
    c = ready(tmp_path)
    script(monkeypatch, c)
    monkeypatch.setattr(edit, "_install", lambda campaign, pair_id: None)
    edit._pce(c, "Q1P1", lambda: False)
    assert edit.status(c, "Q1P1")["claim_basis"] == {"papers": 0, "research record": 1, "both": 0}

"""edit-stage.feature: PCE editing in the engine, on the stub backend or a scripted dispatcher."""
import json
from pathlib import Path

from behave import given, then, when

from pathfinder import config, edit, paper, pce, research, resources, runner, stub, transport
from pathfinder.thread import Stopped

ORDER = ["author", "archivist", "fact-checker", "critic", "editor"]


def pce_campaign(context, pair_id, **raw):
    """A stub-backend campaign with "edit_scheme": "pce" and the pair's papers fetched in full."""
    root = Path(context.config.base_dir).parent / ".shipshape" / "behave" / context.scenario.name
    root.mkdir(parents=True, exist_ok=True)
    for path in sorted(root.rglob("*"), reverse=True):
        path.unlink() if path.is_file() or path.is_symlink() else path.rmdir()
    i, j = (int(n) for n in pair_id[1:].split("P"))
    for side, count, mine in (("Q", i, i), ("P", j, j)):
        rows = []
        for n in range(1, count + 1):
            row = {"id": f"{side.lower()}{n}", "title": f"{side} paper {n}", "abstract": f"Abstract of {side}{n}."}
            if n == mine:
                (root / "sources").mkdir(exist_ok=True)
                (root / "sources" / f"{row['id']}.tex").write_text(f"Full text of {row['id']}.\n")
                row["text"] = f"sources/{row['id']}.tex"
            rows.append(row)
        (root / f"{side}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (root / "shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": pair_id}]}))
    settings = {"backend": "stub", "model": "stub", "peers": ["ada"], "seats": 1, "rounds": 1, "repairs": 0,
                "budget_usd": 100, "call_estimate_usd": 1, "edit_scheme": "pce",
                "allowances": {"peer_seconds": 600, "peer_calls": 2, "consolidate_seconds": 60,
                               "verify_seconds": 60, "edit_seconds": 60}}
    settings.update(raw)
    (root / "campaign.json").write_text(json.dumps(settings, indent=1))
    context.campaign = config.load(root)
    context.pair_id = pair_id
    return context.campaign


def finished(context, pair_id, **raw):
    c = pce_campaign(context, pair_id, **raw)
    assert research.run_thread(c, pair_id) == "DRAFT"
    return c


def with_baseline(context, pair_id, **raw):
    """A finished pair whose single editor has written its note, the round's baseline."""
    c = finished(context, pair_id, **raw)
    ed = c.thread_dir(pair_id) / "edited"; ed.mkdir(exist_ok=True)
    (ed / "note.tex").write_text(stub.READABLE); (ed / "references.bib").write_text(stub.BIB)
    return c


# @exceptional-double: a scripted dispatcher stands in for the model behind each role; the replies are the
# stub backend's, so the engine's own envelope, scope and verdict checks run on them.
def script(context, **verdicts):
    calls = getattr(context, "dispatch_calls", None)
    if calls is None:
        calls = context.dispatch_calls = []
        original = pce._dispatch
        context.add_cleanup(lambda: setattr(pce, "_dispatch", original))

    def dispatch(campaign, pair_id, role, prompt, seconds=None):
        n = sum(1 for call in calls if call["role"] == role)
        planned = verdicts.get(role.replace("-", "_")) or []
        text = stub.pce_reply(campaign, role, prompt, verdict=planned[n] if n < len(planned) else None)
        calls.append({"role": role, "prompt": prompt, "files": json.loads(prompt.split("Allowed input files:\n", 1)[1])})
        return {"role": role, "outcome": "completed", "text": text}

    pce._dispatch = dispatch
    return calls


def run_until(context, done):
    """Run the round until done(calls) holds before the next dispatch; the round stops there, resumable."""
    try:
        context.round_result = pce.run(context.campaign, context.pair_id, stop=lambda: done(context.dispatch_calls))
    except Stopped:
        context.round_result = None


def count(context, role):
    return sum(1 for call in context.dispatch_calls if call["role"] == role)


def last_call(context, role):
    return [call for call in context.dispatch_calls if call["role"] == role][-1]


@given('pair "{pair_id}" finished research on a PCE campaign')
def pair_finished_on_pce_campaign(context, pair_id):
    finished(context, pair_id)


@given('pair "{pair_id}" is still in research on a PCE campaign')
def pair_still_in_research(context, pair_id):
    c = pce_campaign(context, pair_id)
    research.prepare(c, pair_id)


@when('Pathfinder runs the edit stage for pair "{pair_id}"')
def runs_edit_stage(context, pair_id):
    try:
        context.edit_result = edit.run(context.campaign, pair_id)
    except SystemExit as refused:
        context.edit_result = f"refused: {refused}"


@when('the campaign processes pair "{pair_id}" to completion')
def campaign_processes_pair_to_completion(context, pair_id):
    runner._work(context.campaign, pair_id)


@then('the edit stage starts for pair "{pair_id}"')
def edit_stage_started(context, pair_id):
    assert edit.status(context.campaign, pair_id)["status"] == "done"
    assert pce.result(context.campaign, pair_id)["status"] != "none"


@then("the round's frozen baseline is the readable note the single editor wrote from the research account")
def baseline_is_editor_note(context):
    c, p = context.campaign, context.pair_id
    baseline = (pce.workflow(c, p) / pce.BASELINE).read_text()
    editor = [r for r in transport.receipts(c) if r["stage"] == "edit" and r["actor"] == "editor"]
    assert baseline == stub.READABLE and len(editor) == 1          # the stub editor wrote exactly this note
    assert (pce.workflow(c, p) / "sources/internal/account.tex").read_text() == (c.thread_dir(p) / f"{p}.tex").read_text()


@then("that baseline is the editor's own note, not a copy of the account itself")
def baseline_is_not_account(context):
    c, p = context.campaign, context.pair_id
    assert (pce.workflow(c, p) / pce.BASELINE).read_text() != (c.thread_dir(p) / f"{p}.tex").read_text()


@then('pair "{pair_id}" does not enter the edit stage')
def pair_not_entered(context, pair_id):
    assert str(context.edit_result).startswith("refused") and "not terminal" in context.edit_result
    assert edit.status(context.campaign, pair_id)["status"] == "none"


@then('pair "{pair_id}" has no edited artifact recorded')
def pair_no_edited_artifact(context, pair_id):
    assert not (context.campaign.thread_dir(pair_id) / "edited").exists()
    assert pce.result(context.campaign, pair_id)["status"] == "none"


@given('pair "{pair_id}" enters the edit stage')
def pair_enters_edit_stage(context, pair_id):
    with_baseline(context, pair_id)


@when("Pathfinder runs one PCE pass through the assigned runtime")
def runs_one_pce_pass(context):
    context.round_result = pce.run(context.campaign, context.pair_id)


@then("the PCE workflow directory contains its current draft, archived draft, gate reviews, and state")
def pce_workflow_contains_outputs(context):
    root = pce.workflow(context.campaign, context.pair_id)
    assert context.round_result["status"] == "accepted"
    assert (root / pce.DRAFT).is_file() and list((root / "revisions/history").glob("*-pass-01-draft.tex"))
    assert (root / "reviews/history/pass-01-fact-check.json").is_file()
    assert list((root / "reviews/history").glob("pass-01-*-critic.md"))
    assert (root / "state.json").is_file() and (root / "result.json").is_file()


@then("the campaign receipts record the author, archivist, fact-checker, critic, and editor dispatches in workflow order")
def receipts_in_workflow_order(context):
    rows = [r for r in transport.receipts(context.campaign) if r["stage"] == "edit"]
    assert [r["actor"] for r in rows] == [f"pce-{role}" for role in ORDER]


@then("each role's prompt is an engine prompt a campaign extends with an append overlay")
def role_prompts_are_engine_prompts(context):
    c = context.campaign
    (c.path("prompts")).mkdir(exist_ok=True)
    for role in ORDER:
        engine = (resources.engine_prompts() / f"pce-{role}.md").read_text()
        assert resources.prompt_template(c, f"pce-{role}") == engine
        (c.path("prompts") / f"pce-{role}.append.md").write_text(f"Deployment note for the {role}.\n")
        assert resources.prompt_template(c, f"pce-{role}").endswith(f"Deployment note for the {role}.\n")


@when("the editor stage begins")
def editor_stage_begins(context):
    context.brief = pce.sources(context.campaign, context.pair_id)


@then("the editor's brief cites the accepted research account as internal source")
def brief_cites_internal(context):
    account = (context.campaign.thread_dir(context.pair_id) / f"{context.pair_id}.tex").read_text()
    assert context.brief["sources/internal/account.tex"] == account
    assert not any(n.startswith("sources/external/") and t == account for n, t in context.brief.items())


@then('the editor\'s brief cites the fetched full text of "Q" and "P" as external source')
def brief_cites_external(context):
    assert context.brief["sources/external/Q.tex"] == "Full text of q3.\n"
    assert context.brief["sources/external/P.tex"] == "Full text of p10.\n"


@given('pair "{pair_id}" has a staged brief and source set')
def pair_has_staged_brief(context, pair_id):
    with_baseline(context, pair_id)
    script(context)


@when("the author role executes")
def author_role_executes(context):
    run_until(context, lambda calls: any(call["role"] == "archivist" for call in calls))


@then("a draft is produced")
def draft_is_produced(context):
    draft = (pce.workflow(context.campaign, context.pair_id) / pce.DRAFT).read_text()
    assert "Revised by the stub PCE author, pass 1." in draft


@then("the archivist records the draft in its revision history before review")
def archivist_records_draft(context):
    root = pce.workflow(context.campaign, context.pair_id)
    hist = pce.history(context.campaign, context.pair_id)
    assert hist and hist[-1]["draft"] == (root / pce.DRAFT).read_text()
    assert list((root / "revisions/history").glob("*-pass-01.md")), "no archivist note"
    assert [call["role"] for call in context.dispatch_calls] == ["author", "archivist"]


@given('pair "{pair_id}" has an archived draft')
def pair_has_archived_draft(context, pair_id):
    pair_has_staged_brief(context, pair_id)
    author_role_executes(context)


@when("the fact-checker gate runs")
def fact_checker_gate_runs(context):
    run_until(context, lambda calls: any(call["role"] == "fact-checker" for call in calls))


@then('it checks the draft\'s claims against the fetched full text of "Q" and "P"')
def fact_checker_checks_external(context):
    files = last_call(context, "fact-checker")["files"]
    assert files["sources/external/Q.tex"] == "Full text of q3.\n" and files["sources/external/P.tex"] == "Full text of p10.\n"
    assert pce.DRAFT in files and pce.CLAIMS in files
    assert (pce.workflow(context.campaign, context.pair_id) / "reviews/history/pass-01-fact-check.json").is_file()


@then("it does not read the accepted research account")
def fact_checker_no_internal(context):
    account = (context.campaign.thread_dir(context.pair_id) / f"{context.pair_id}.tex").read_text()
    files = last_call(context, "fact-checker")["files"]
    assert account not in files.values() and not any(n.startswith("sources/internal/") for n in files)


@when("the critic gate runs")
def critic_gate_runs(context):
    run_until(context, lambda calls: any(call["role"] == "critic" for call in calls))


@then("the critic's review has no access to the internal sources or prior reviews")
def critic_no_internal_access(context):
    files = last_call(context, "critic")["files"]
    assert not any(n.startswith(("sources/internal/", "reviews/", "revisions/")) for n in files), sorted(files)
    assert (pce.workflow(context.campaign, context.pair_id) / "reviews/current/critic-reader.md").is_file()


@given('pair "{pair_id}"\'s staged brief and source set exceeds its assigned context limit')
def oversized_edit_stage_brief(context, pair_id):
    with_baseline(context, pair_id)
    context.campaign.raw["max_prompt_chars"] = 2000      # after research, whose own prompts are larger


@when("the edit stage prepares a role dispatch")
def edit_stage_prepares_dispatch(context):
    context.round_result = pce.run(context.campaign, context.pair_id)


@then("Pathfinder blocks the dispatch and the round ends for review")
def oversized_dispatch_is_blocked(context):
    assert context.round_result["status"] == "review_required" and "input too large" in context.round_result["reason"]
    rows = [r for r in transport.receipts(context.campaign) if r["stage"] == "edit"]
    assert rows and all(r["outcome"] == "refused" and r["prompt_chars"] > 2000 for r in rows)


@then("the round keeps the whole evidence rather than truncating it")
def evidence_not_truncated(context):
    root = pce.workflow(context.campaign, context.pair_id)
    inputs = context.campaign.thread_dir(context.pair_id) / "inputs"
    for side in "QP":
        assert (root / f"sources/external/{side}.tex").read_text() == (inputs / f"{side}.tex").read_text()
    assert (root / pce.BASELINE).read_text() == stub.READABLE
    assert not (root / pce.DRAFT).exists()


@then('PCE produces pair "{pair_id}"\'s edited artifact')
def pce_produces_edited_artifact(context, pair_id):
    ed = context.campaign.thread_dir(pair_id) / "edited"
    assert (ed / "note.tex").read_text() == (ed / "pce" / pce.DRAFT).read_text() and (ed / "note.pdf").exists()


@then("the campaign records PCE's final edit outcome")
def campaign_records_pce_outcome(context):
    s = edit.status(context.campaign, context.pair_id)
    assert s["scheme"] == "pce" and s["editorial_status"] == "accepted" and s["accepted_note"] is True
    assert pce.result(context.campaign, context.pair_id)["status"] == "accepted"


@given('PCE has produced pair "{pair_id}"\'s edited paper and references')
def pce_produced_paper_and_references(context, pair_id):
    c = finished(context, pair_id)
    assert edit.run(c, pair_id) == "done" and edit.status(c, pair_id)["accepted_note"] is True
    context.edited_dir = c.thread_dir(pair_id) / "edited"


@when("Pathfinder validates the edited artifact")
def validates_edited_artifact(context):
    d = context.edited_dir
    context.build_ok, context.build_log = paper.build(d, main="note.tex")
    context.reference_findings = paper.check_references((d / "note.tex").read_text(), (d / "references.bib").read_text())


@then("the edited paper builds successfully with its bibliography")
def edited_paper_builds(context):
    assert context.build_ok, context.build_log
    assert "Revised by the stub PCE author" in (context.edited_dir / "note.tex").read_text()


@then("every cited reference passes Pathfinder's reference checks")
def edited_references_pass(context):
    assert edit._clean(context.reference_findings), context.reference_findings


@given('pair "{pair_id}" is in its edit stage')
def pair_is_in_edit_stage(context, pair_id):
    with_baseline(context, pair_id)


@when('the editor accepts the draft on or before pass "{limit}"')
def editor_accepts_within_limit(context, limit):
    context.campaign.raw["pce"] = {"passes": int(limit)}
    context.edit_result = edit.run(context.campaign, context.pair_id)


@when('the editor asks for a revision on every pass up to the limit of "{limit}"')
def editor_revises_every_pass(context, limit):
    context.campaign.raw["pce"] = {"passes": int(limit)}
    context.campaign.raw["stub"] = {"pce_editor": "revise"}
    context.edit_result = edit.run(context.campaign, context.pair_id)


@then('the edit stage finishes with outcome "{outcome}"')
def edit_stage_finishes_with(context, outcome):
    assert context.edit_result == "done"
    assert pce.result(context.campaign, context.pair_id)["status"] == outcome
    assert edit.status(context.campaign, context.pair_id)["editorial_status"] == outcome


@then("the accepted draft is recorded as the pair's edited artifact")
def accepted_draft_recorded(context):
    ed = context.campaign.thread_dir(context.pair_id) / "edited"
    draft = (ed / "pce" / pce.DRAFT).read_text()
    assert pce.result(context.campaign, context.pair_id)["passes"] <= 3
    assert (ed / "note.tex").read_text() == draft and "Revised by the stub PCE author" in draft


@then("the last produced draft stays in the round while the editor's note remains the pair's edited artifact")
def last_draft_kept(context):
    ed = context.campaign.thread_dir(context.pair_id) / "edited"
    hist = pce.history(context.campaign, context.pair_id)
    assert [h["pass"] for h in hist] == [1, 2, 3]
    assert (ed / "pce" / pce.DRAFT).read_text() == hist[-1]["draft"] and "pass 3." in hist[-1]["draft"]
    assert (ed / "note.tex").read_text() == stub.READABLE


@given("the edit stage dispatches the author, archivist, fact-checker, critic, and editor for one pass")
def dispatches_one_pass(context):
    with_baseline(context, "Q3P10")


@when("each dispatch finishes")
def each_dispatch_finishes(context):
    context.round_result = pce.run(context.campaign, context.pair_id)


@then("each dispatch's receipt records role, backend, model, execution class, prompt digest, provider job identifier, raw response, outcome, latency, token usage, and cost")
def receipts_have_required_fields(context):
    required = {"role", "backend", "model", "execution_class", "prompt_digest", "provider_job_id",
                "raw_response", "outcome", "latency", "token_usage", "cost"}
    records = pce.dispatches(context.campaign, context.pair_id)
    assert [r["role"] for r in records] == ORDER
    for record in records:
        assert required <= set(record["receipt"]), sorted(required - set(record["receipt"]))
        assert record["receipt"]["prompt_digest"] == record["prompt_sha256"]


@given('PCE completes one edit pass for pair "{pair_id}"')
def pce_completes_edit_pass(context, pair_id):
    with_baseline(context, pair_id)
    assert pce.run(context.campaign, pair_id)["status"] == "accepted"


@when("the campaign is inspected after the edit stage")
def inspect_campaign_after_edit(context):
    context.persisted_receipts = transport.receipts(context.campaign)


@then("every PCE role dispatch remains recorded in the campaign receipts")
def pce_receipts_remain_recorded(context):
    actors = [r["actor"] for r in context.persisted_receipts if r["stage"] == "edit"]
    assert actors == [f"pce-{role}" for role in ORDER]
    assert all(r["backend"] == "stub" and r["thread"] == context.pair_id for r in context.persisted_receipts
               if r["stage"] == "edit")


@given('pair "{pair_id}" has an archived pass "{n}" draft')
def pair_has_archived_pass_draft(context, pair_id, n):
    with_baseline(context, pair_id)
    script(context, critic=["revise"] * int(n))
    run_until(context, lambda calls: count(context, "critic") >= int(n))


@when('the author produces a pass "{n}" draft')
def author_produces_pass_draft(context, n):
    run_until(context, lambda calls: count(context, "author") >= int(n))


@then('the pass "{n}" draft remains recorded in revision history')
def pass_draft_in_history(context, n):
    hist = pce.history(context.campaign, context.pair_id)
    assert any(h["pass"] == int(n) and f"pass {n}." in h["draft"] for h in hist), hist


@then('the pass "{n}" draft becomes the current draft')
def pass_draft_is_current(context, n):
    current = (pce.workflow(context.campaign, context.pair_id) / pce.DRAFT).read_text()
    assert f"pass {n}." in current and current == pce.history(context.campaign, context.pair_id)[-1]["draft"]

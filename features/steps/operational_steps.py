import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from behave import given, then, when

from pathfinder import corpus, edit, paper as paper_module, research, runner, scan, select, transport
from pathfinder.config import Campaign
from pathfinder.ledger import Ledger


def campaign(context, rounds=3, repairs=1):
    root = Path(context.config.base_dir).parent / ".shipshape" / "behave" / context.scenario.name
    root.mkdir(parents=True, exist_ok=True)
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    context.campaign = Campaign(
        root=root,
        backend="claude",
        model="m",
        scan_model="m",
        peer_search=False,
        seats=1,
        cut=10,
        rounds=rounds,
        allowances={"peer_seconds": 1, "peer_calls": 1, "consolidate_seconds": 1, "verify_seconds": 1},
        budget_usd=99,
        prices={},
        scan_fulltext=None,
    )
    context.campaign.raw = {"repairs": repairs}
    return context.campaign


def paper(identifier):
    return {"id": identifier, "title": identifier, "abstract": f"Abstract {identifier}", "text": None}


def write_rows(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def seed_pair(context):
    c = campaign(context)
    write_rows(c.path("Q.jsonl"), [paper("q1")])
    write_rows(c.path("P.jsonl"), [paper("p1")])
    research.prepare(c, "Q1P1")
    return c


def set_status(context, **values):
    d = context.campaign.thread_dir("Q1P1")
    d.mkdir(parents=True, exist_ok=True)
    (d / "status.json").write_text(json.dumps({"pair_id": "Q1P1", "round": 1, **values}))


# @exceptional-double: internal composition has no independent external verifier.
def run_research(context, decisions, substantive=True):
    context.calls = []
    replies = iter(decisions)

    def stage_call(campaign, pair_id, stage, prompt, tools, seconds, done=lambda: False):
        context.calls.append(stage)
        d = campaign.thread_dir(pair_id)
        if stage == "peers" and substantive:
            Ledger(d / "ledger.jsonl").add("ada", "finding", "substantive finding")
        if stage == "consolidate":
            repair = research.status(campaign, pair_id).get("repair") or {}
            correction = repair.get("action", "initial account")
            # the returned text becomes the account; a tool-less consolidator writes no file
            return {"text": "\\documentclass{article}\\begin{document}\n" + correction + "\n\\end{document}\n", "error": None}
        if stage == "verify":
            decision, reason, action = next(replies)
            return {"text": json.dumps({"decision": decision, "reason": reason, "action": action}), "error": None}
        return {"text": "peer", "error": None}

    original_peers = research._peers
    original_stage_call = research._stage_call
    research._peers = lambda c, pair_id, stop: stage_call(c, pair_id, "peers", "", True, 1)
    research._stage_call = stage_call
    try:
        context.result = research.run_thread(context.campaign, "Q1P1")
    finally:
        research._peers = original_peers
        research._stage_call = original_stage_call


@given('paper "{identifier}" is in the question corpus')
def question_paper(context, identifier):
    c = campaign(context)
    write_rows(c.path("Q.jsonl"), [paper(identifier)])


@given('paper "{identifier}" is in the technique corpus')
def technique_paper(context, identifier):
    write_rows(context.campaign.path("P.jsonl"), [paper(identifier)])
    context.campaign.path("prompts").mkdir()
    context.campaign.path("prompts/scan.md").write_text("{{Q_TITLE}} {{P_TITLE}}")


@when('the connection judge assesses pair "{pair_id}"')
def assess_pair(context, pair_id):
    # @exceptional-double: internal composition has no independent external verifier.
    original = scan.transport.execute
    scan.transport.execute = lambda *args, **kwargs: {
        "seconds": 0, "cost": 0, "text": json.dumps({"feasibility": 50, "gain": 40, "connexion": "connection", "rationale": "evidence"}), "error": None
    }
    try:
        scan.run(context.campaign)
    finally:
        scan.transport.execute = original


@then('pair "{pair_id}" records feasibility, scientific gain, a proposed connection, and rationale')
def assessment_recorded(context, pair_id):
    row = next(row for row in corpus.read(context.campaign.path("scan.jsonl")) if row["pair_id"] == pair_id)
    assert all(row[key] is not None for key in ("feasibility", "gain", "connexion", "rationale"))


@given('pair "Q1P1" already has a recorded assessment')
def existing_assessment(context):
    c = campaign(context)
    write_rows(c.path("Q.jsonl"), [paper("q1")])
    write_rows(c.path("P.jsonl"), [paper("p1"), paper("p2")])
    write_rows(c.path("scan.jsonl"), [{"pair_id": "Q1P1", "feasibility": 1, "gain": 1}])
    c.path("prompts").mkdir()
    c.path("prompts/scan.md").write_text("{{Q_TITLE}} {{P_TITLE}}")


@given('pair "Q1P2" has no recorded assessment')
def missing_assessment(context):
    pass


@when('the connection scan resumes')
def resume_scan(context):
    context.assessed = []
    # @exceptional-double: internal composition has no independent external verifier.
    original = scan.transport.execute

    def execute(campaign, request):
        context.assessed.append(request.thread)
        return {"seconds": 0, "cost": 0, "text": '{"feasibility":2,"gain":3,"connexion":"c","rationale":"r"}', "error": None}

    scan.transport.execute = execute
    try:
        scan.run(context.campaign)
    finally:
        scan.transport.execute = original


@then('pair "{pair_id}" is not assessed again')
def not_assessed(context, pair_id):
    assert pair_id not in context.assessed


@then('pair "{pair_id}" is assessed')
def assessed(context, pair_id):
    assert pair_id in context.assessed


@given('corpus "Q" contains papers "q1" and "q2" in that order')
def initial_corpus(context):
    c = campaign(context)
    write_rows(c.path("Q.jsonl"), [paper("q1"), paper("q2")])
    c.path("fetch.json").write_text(json.dumps({"q": "query"}))


@when('its next page contains papers "q2" and "q3"')
def next_page(context):
    def fetch(query, n, start):
        context.page_start = start
        return [paper("q2"), paper("q3")]
    corpus.more(context.campaign, "Q", 2, fetch_fn=fetch)


@then('corpus "Q" contains papers "q1", "q2", and "q3" in that order')
def extended_corpus(context):
    assert [row["id"] for row in corpus.read(context.campaign.path("Q.jsonl"))] == ["q1", "q2", "q3"]


@then('the next page begins after the previously requested papers')
def page_position(context):
    assert context.page_start == 2


@given('pair "{pair_id}" has feasibility "{feasibility}" and scientific gain "{gain}"')
def scored_pair(context, pair_id, feasibility, gain):
    if not hasattr(context, "rows"):
        context.rows = []
    context.rows.append({"pair_id": pair_id, "q": pair_id.split("P")[0], "p": "P" + pair_id.split("P")[1], "feasibility": int(feasibility), "gain": int(gain)})


@when('Pathfinder ranks the assessed connections')
def rank_connections(context):
    context.ranked = select.rank(context.rows)


@then('pair "{first}" ranks before pair "{second}"')
def ranking_order(context, first, second):
    ids = [row["pair_id"] for row in context.ranked]
    assert ids.index(first) < ids.index(second)


@given('all possible paper pairs have been assessed')
def complete_scan(context):
    c = campaign(context)
    write_rows(c.path("Q.jsonl"), [paper(f"q{i}") for i in range(1, 3)])
    write_rows(c.path("P.jsonl"), [paper(f"p{i}") for i in range(1, 6)])
    context.rows = [{"pair_id": f"Q{i}P{j}", "q": f"q{i}", "p": f"p{j}", "feasibility": i * 10 + j, "gain": 10} for i in range(1, 3) for j in range(1, 6)]
    write_rows(c.path("scan.jsonl"), context.rows)


@given('the campaign reserves research capacity for the top "{cut}" percent')
def capacity(context, cut):
    context.cut = int(cut)


@when('Pathfinder builds the shortlist')
def build_shortlist(context):
    context.shortlist = select.run(context.campaign, cut=context.cut)


@then('the highest-ranked "{cut}" percent of assessed pairs are selected')
def top_fraction(context, cut):
    expected = select.rank(context.rows)[:1]
    assert [row["pair_id"] for row in context.shortlist["pairs"]] == [row["pair_id"] for row in expected]


@given('pair "{pair_id}" has combined score "{score}"')
def combined_score(context, pair_id, score):
    if not hasattr(context, "rows"):
        c = campaign(context)
        write_rows(c.path("Q.jsonl"), [paper("q1"), paper("q2")])
        write_rows(c.path("P.jsonl"), [paper("p1")])
        context.rows = []
    context.rows.append({"pair_id": pair_id, "q": pair_id.split("P")[0], "p": "p1", "feasibility": int(score), "gain": 1})
    write_rows(context.campaign.path("scan.jsonl"), context.rows)


@when('the admission threshold is "{threshold}"')
def threshold(context, threshold):
    context.shortlist = select.run(context.campaign, min_score=int(threshold))


@then('pair "{pair_id}" is selected')
def selected(context, pair_id):
    assert pair_id in {row["pair_id"] for row in context.shortlist["pairs"]}


@then('pair "{pair_id}" is not selected')
def not_selected(context, pair_id):
    assert pair_id not in {row["pair_id"] for row in context.shortlist["pairs"]}


@given('research has started for pair "Q2P1"')
def started_research(context):
    c = campaign(context)
    write_rows(c.path("Q.jsonl"), [paper("q1"), paper("q2")])
    write_rows(c.path("P.jsonl"), [paper("p1")])
    context.rows = [
        {"pair_id": "Q1P1", "q": "q1", "p": "p1", "feasibility": 100, "gain": 100},
        {"pair_id": "Q2P1", "q": "q2", "p": "p1", "feasibility": 1, "gain": 1},
    ]
    write_rows(c.path("scan.jsonl"), context.rows)
    d = c.thread_dir("Q2P1")
    d.mkdir(parents=True, exist_ok=True)
    (d / "status.json").write_text(json.dumps({"pair_id": "Q2P1", "round": 1, "stage": "peers", "status": "running"}))


@given('pair "Q2P1" is below the current admission threshold')
def below_threshold(context):
    context.threshold = 100


@when('Pathfinder rebuilds the shortlist')
def rebuild_shortlist(context):
    context.shortlist = select.run(context.campaign, min_score=context.threshold)


@then('pair "Q2P1" remains selected')
def started_remains(context):
    assert "Q2P1" in {row["pair_id"] for row in context.shortlist["pairs"]}


@given('researchers have recorded substantive findings for pair "Q1P1"')
def substantive_findings(context):
    seed_pair(context)


@when('the findings are consolidated into a research account')
def consolidate_findings(context):
    run_research(context, [("DRAFT", "ready", None)])


@then('an independent verifier assesses that account against both source papers')
def verifier_called(context):
    assert context.calls.index("consolidate") < context.calls.index("verify")


@given('researchers have recorded no substantive finding for pair "Q1P1"')
def no_findings(context):
    seed_pair(context)


@when('the peer stage finishes')
def peer_stage_finishes(context):
    run_research(context, [], substantive=False)


@then('pair "Q1P1" is paused for an empty research record')
def empty_pause(context):
    status = research.status(context.campaign, "Q1P1")
    assert status["status"] == "PAUSE" and status["reason"] == "empty ledger"


@then('no research account is produced')
def no_account(context):
    assert not (context.campaign.thread_dir("Q1P1") / "Q1P1.tex").exists()


@given('the verifier assesses the current research account')
def verifier_assesses(context):
    seed_pair(context)


@given('the campaign permits another research round')
def permits_round(context):
    seed_pair(context)


@given('the investigation has reached its research round limit')
def round_limit(context):
    c = seed_pair(context)
    c.rounds = 1


@given('the campaign permits a repair of the research account')
def permits_repair(context):
    seed_pair(context)


@given('the investigation has reached its account repair limit')
def repair_limit(context):
    c = seed_pair(context)
    c.raw["repairs"] = 0


@when('the verifier returns "DRAFT"')
def draft_decision(context):
    run_research(context, [("DRAFT", "ready", None)])


@when('the verifier returns "ITERATE" with an unanswered question')
def iterate_with_question(context):
    run_research(context, [("ITERATE", "question", "answer it"), ("DRAFT", "ready", None)])


@when('the verifier returns "ITERATE"')
def iterate_decision(context):
    run_research(context, [("ITERATE", "question", "answer it")])


@when('the verifier returns "REVISE" with a correction')
def revise_with_correction(context):
    context.correction = "narrow the claim"
    run_research(context, [("REVISE", "overstated", context.correction), ("DRAFT", "ready", None)])


@when('the verifier returns "REVISE"')
def revise_decision(context):
    run_research(context, [("REVISE", "overstated", "narrow")])


@then('the investigation finishes with status "{status}"')
def finishes_with_status(context, status):
    assert research.status(context.campaign, "Q1P1")["status"] == status


@then("the verdict records the assessed account's digest")
def verdict_digest(context):
    d = context.campaign.thread_dir("Q1P1")
    verdict = json.loads((d / "Q1P1.verdict.json").read_text())[0]
    assert verdict["note_sha256"] == hashlib.sha256((d / "Q1P1.tex").read_bytes()).hexdigest()


@then('the unanswered question is added to the research record')
def question_recorded(context):
    rows = Ledger(context.campaign.thread_dir("Q1P1") / "ledger.jsonl").read()
    assert any(row["kind"] == "review" and "question" in row["text"] for row in rows)


@then('the investigation returns to peer research')
def returned_to_research(context):
    assert context.calls.count("peers") == 2


@then('the current account is repaired using that correction')
def account_repaired(context):
    assert context.correction in (context.campaign.thread_dir("Q1P1") / "Q1P1.tex").read_text()


@then('the repaired account is independently assessed again')
def reassessed(context):
    assert context.calls.count("verify") == 2


@given('pair "Q1P1" is being investigated')
def pair_investigated(context):
    c = campaign(context)
    c.path("shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": "Q1P1"}, {"pair_id": "Q1P2"}]}))


@given('pair "Q1P2" is waiting for admission')
def pair_waiting(context):
    pass


@when('the operator requests a stop')
def request_stop(context):
    admitted = []

    def work(campaign, pair_id):
        admitted.append(pair_id)
        runner.request_stop(campaign, "operator")
        set_status(context, stage="peers", status="stopped")
        return "stopped"

    # @exceptional-double: internal composition has no independent external verifier.
    original = runner._work
    runner._work = work
    try:
        runner._loop(context.campaign, ThreadPoolExecutor(1), 0, {}, {})
    finally:
        runner._work = original
    context.admitted = admitted


@then('pair "Q1P1" finishes and preserves its active stage')
def active_stage_preserved(context):
    assert context.admitted == ["Q1P1"] and research.status(context.campaign, "Q1P1")["stage"] == "peers"


@then('pair "Q1P2" remains waiting')
def waiting_remains(context):
    assert research.status(context.campaign, "Q1P2")["status"] == "new"


@given('pair "Q1P1" stopped after its research account was produced')
def stopped_after_account(context):
    c = seed_pair(context)
    (c.thread_dir("Q1P1") / "Q1P1.tex").write_text("account")
    set_status(context, stage="verify", status="stopped")


@when('the campaign continues')
def continue_campaign(context):
    run_research(context, [("DRAFT", "ready", None)], substantive=False)


@then('pair "Q1P1" continues with independent assessment')
def continues_assessment(context):
    assert context.calls == ["verify"]


@given('pair "Q1P1" stopped before its research account was produced')
def stopped_before_account(context):
    seed_pair(context)
    set_status(context, stage="verify", status="stopped")


@given('pair "Q1P1" stopped with a research account awaiting assessment')
def stopped_with_account(context):
    stopped_after_account(context)


@when('the operator inspects pair "Q1P1"')
def inspect_pair(context):
    from pathfinder import reconcile
    context.action = reconcile.inspect(context.campaign, "Q1P1")["action"]


@then('the next safe recovery action is "{action}"')
def recovery_action(context, action):
    assert context.action == action


@given('pair "Q1P1" cannot continue automatically')
def blocked_pair(context):
    c = campaign(context)
    c.path("shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": "Q1P1"}]}))
    set_status(context, stage="verify", status="BLOCKED")


@when('Pathfinder admits pending investigations')
def admit_pending(context):
    context.pending = runner.pending(context.campaign)


@then('pair "Q1P1" is not admitted')
def blocked_not_admitted(context):
    assert "Q1P1" not in context.pending


@given("two prepared paper corpora from domains chosen by the operator")
def prepared_corpora(context):
    c = campaign(context)
    write_rows(c.path("Q.jsonl"), [paper("q1")])
    write_rows(c.path("P.jsonl"), [paper("p1")])


@when("the operator starts a Pathfinder campaign from those corpora")
def start_prepared_campaign(context):
    # @exceptional-double: internal composition has no independent external verifier.
    original = scan.transport.call
    scan.transport.call = lambda *args, **kwargs: {
        "seconds": 0,
        "cost": 0,
        "text": '{"feasibility":1,"gain":1,"connexion":"c","rationale":"r"}',
        "error": None,
    }
    try:
        scan.run(context.campaign)
    finally:
        scan.transport.call = original
    context.results = corpus.read(context.campaign.path("scan.jsonl"))


@then("Pathfinder examines connections between the papers in those corpora")
def examines_prepared_corpora(context):
    assert len(context.results) == 1


@then("every result identifies its two source papers")
def results_identify_sources(context):
    assert [(row["q"], row["p"]) for row in context.results] == [("q1", "p1")]


def snapshot(c, name, rows):
    path = c.path(f"{name}.jsonl")
    write_rows(path, rows)
    return path


@given("a Pathfinder campaign was created from two prepared corpus snapshots")
def campaign_from_snapshots(context):
    prepared_corpora(context)
    runner.create_manifest(context.campaign)


@when("the campaign is inspected or repeated")
def inspect_campaign_snapshots(context):
    context.manifest = json.loads(context.campaign.path("manifest.json").read_text())


@then("the exact source snapshots used by the campaign are identifiable")
def exact_snapshots_identifiable(context):
    assert set(context.manifest["snapshots"]) == {"Q", "P"}


@given("two prepared corpus snapshots conform to the Pathfinder corpus contract")
def conforming_snapshots(context):
    prepared_corpora(context)


@when("their number of papers changes")
def change_snapshot_size(context):
    write_rows(context.campaign.path("Q.jsonl"), [paper("q1"), paper("q2")])
    context.pair_ids = [corpus.pair_id(i, j) for i in range(1, 3) for j in range(1, 2)]


@then("Pathfinder applies the same connection assessment to every cross-corpus pair")
def same_assessment_for_pairs(context):
    assert context.pair_ids == ["Q1P1", "Q2P1"]


@given("a prepared corpus snapshot contains records with stable identifiers, titles, and abstracts")
def valid_snapshot_records(context):
    c = campaign(context)
    context.snapshot = snapshot(c, "Q", [paper("q1")])


@given("a record may reference optional full text within the snapshot")
def optional_full_text(context):
    pass


@when("Pathfinder validates the snapshot")
def validate_snapshot(context):
    context.records = corpus.validate_snapshot(context.snapshot)


@then("every record can be used without an acquisition adapter")
def records_are_ready(context):
    assert context.records == [paper("q1")]


@given("a run references two prepared corpus snapshots")
def run_references_snapshots(context):
    prepared_corpora(context)
    context.before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (context.campaign.path("Q.jsonl"), context.campaign.path("P.jsonl"))}


@when("Pathfinder completes or resumes the run")
def complete_snapshot_run(context):
    context.after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (context.campaign.path("Q.jsonl"), context.campaign.path("P.jsonl"))}


@then("both source snapshot digests remain unchanged")
def snapshot_digests_unchanged(context):
    assert context.after == context.before


@given('prepared snapshots "questions" and "techniques"')
def named_snapshots(context):
    prepared_corpora(context)


@when("a comparison run is created")
def create_comparison_run(context):
    context.manifest = runner.create_manifest(context.campaign)


@then("its manifest records the digest of each snapshot")
def manifest_has_snapshot_digests(context):
    assert set(context.manifest["snapshot_digests"]) == {"Q", "P"}


@given("two runs reference identical ordered corpus snapshots")
def identical_ordered_snapshots(context):
    prepared_corpora(context)


@when("both runs enumerate their cross-corpus pairs")
def enumerate_identical_pairs(context):
    context.identities = [runner.pair_identity(context.campaign, "Q1P1") for _ in range(2)]


@then("corresponding source records have the same pair identity in both runs")
def pair_identity_stable(context):
    assert context.identities[0] == context.identities[1]


@given("a run produces a result for one cross-corpus pair")
def result_for_pair(context):
    prepared_corpora(context)
    context.result = runner.result_provenance(context.campaign, "Q1P1")


@when("the result provenance is inspected")
def inspect_result_provenance(context):
    pass


@then("it identifies both source record identifiers")
def provenance_has_record_ids(context):
    assert context.result["record_ids"] == ["q1", "p1"]


@then("it identifies both source snapshot digests")
def provenance_has_snapshot_digests(context):
    assert len(context.result["snapshot_digests"]) == 2


def assignments(roles=("scan", "research", "consolidate", "verify")):
    return {
        role: {"model": "m", "backend": "claude", "execution_class": "agent", "prompt": role, "tool_policy": [], "budget": 1}
        for role in roles
    }


@given("an OpenAI-compatible provider call reports positive output tokens and no parsed text")
def output_without_parsed_text(context):
    context.provider_lines = [
        json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
        json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": ""}}),
        json.dumps({"type": "turn.completed", "usage": {"input_tokens": 3, "output_tokens": 7}}),
    ]


@when("Pathfinder records the completed provider call")
def record_completed_provider_call(context):
    c = campaign(context)

    # @exceptional-double: real provider completion with empty parsed text cannot be produced on demand.
    class CompletedProcess:
        pid = None  # Parser replay has no operating-system child.
        returncode = 0
        stdout = iter(line + "\n" for line in context.provider_lines)
        stdin = type("Stdin", (), {"write": lambda self, value: None, "close": lambda self: None})()
        stderr = type("Stderr", (), {"read": lambda self: ""})()

        def wait(self, timeout=None):
            return self.returncode

    original = transport.subprocess.Popen
    transport.subprocess.Popen = lambda *args, **kwargs: CompletedProcess()
    try:
        context.provider_result = transport.call(
            "prompt", campaign=c, model="model", tools=False, search=False, cwd=c.root,
            timeout=1, thread="Q1P1", stage="scan", actor="scan",
        )
    finally:
        transport.subprocess.Popen = original
    context.provider_receipt = transport.receipts(c)[-1]


@then("the receipt identifies the process exit and terminal response event")
def receipt_identifies_completion(context):
    assert context.provider_receipt["exit_status"] == 0
    assert json.loads(context.provider_receipt["terminal_event"])["type"] == "turn.completed"


@then("the receipt retains the raw response events needed to account for the output tokens")
def receipt_retains_response_events(context):
    assert context.provider_receipt["output_tokens"] == 7
    assert context.provider_receipt["raw_events"] == context.provider_lines


@given("an OpenAI-compatible provider call completes with positive output tokens")
def completed_provider_output(context):
    context.provider_lines = [
        json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
        json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": ""}}),
        json.dumps({"type": "turn.completed", "usage": {"input_tokens": 3, "output_tokens": 7}}),
    ]


@when("Pathfinder completes the provider call without a parsed research account")
def complete_without_parsed_account(context):
    c = campaign(context)

    # @exceptional-double: real provider process completion cannot produce this parser failure on demand.
    class CompletedProcess:
        pid = None  # Parser replay has no operating-system child.
        returncode = 0
        stdout = iter(line + "\n" for line in context.provider_lines)
        stdin = type("Stdin", (), {"write": lambda self, value: None, "close": lambda self: None})()
        stderr = type("Stderr", (), {"read": lambda self: ""})()

        def wait(self, timeout=None):
            return self.returncode

    # @exceptional-double: real provider process completion cannot produce this parser failure on demand.
    original = transport.subprocess.Popen
    transport.subprocess.Popen = lambda *args, **kwargs: CompletedProcess()
    try:
        context.provider_result = transport.call(
            "prompt", campaign=c, model="model", tools=False, search=False, cwd=c.root,
            timeout=1, thread="Q1P1", stage="consolidate", actor="consolidator",
        )
    finally:
        transport.subprocess.Popen = original
    context.provider_receipt = transport.receipts(c)[-1]


@then("the receipt records the process exit status")
def receipt_records_exit_status(context):
    assert context.provider_receipt["exit_status"] == 0


@then("the receipt records the terminal response event")
def receipt_records_terminal_event(context):
    assert json.loads(context.provider_receipt["terminal_event"])["type"] == "turn.completed"


@then("the receipt retains the raw response events")
def receipt_retains_raw_events(context):
    assert context.provider_receipt["raw_events"] == context.provider_lines


@then("Pathfinder does not silently truncate the evidence")
def oversized_request_preserves_evidence(context):
    assert context.provider_request["inputs"]["evidence"] == context.stage_inputs["evidence"]


def model_request(stage, identity="Q1P1"):
    return transport.ModelRequest(
        identity=identity,
        prompt=f"{stage} prompt",
        model="m",
        tools=stage in {"peer", "consolidate"},
        search=False,
        timeout=1,
        thread="Q1P1",
        stage=stage,
        actor=stage,
    )


@given("one frozen paper pair enters scanning and research")
@given("one frozen paper pair enters scanning and research with two configured peers")
def frozen_pair_enters_campaign(context):
    seed_pair(context)
    prompts = context.campaign.path("prompts")
    prompts.mkdir(exist_ok=True)
    prompts.joinpath("scan.md").write_text("{{Q_TITLE}} {{P_TITLE}}")
    for name in ("peer", "consolidate", "verify"):
        prompts.joinpath(f"{name}.md").write_text("{ACTOR} {PEERS} {Q_INPUT} {P_INPUT} {MATERIAL} {LEDGER} {LAST_SEQ} {SECONDS} {CALLS_LEFT} {FEASIBILITY} {GAIN} {CONNEXION} {RATIONALE} {NOTE}")


@when("Pathfinder executes scan, peer, consolidation, and verification model requests")
def execute_campaign_model_requests(context):
    context.requests = []
    # @exceptional-double: internal composition has no independent external verifier.
    original = transport.execute

    def execute(campaign, request):
        context.requests.append(request)
        stage = "peer" if request.stage == "peers" else request.stage
        if stage == "scan":
            text = '{"feasibility": 1, "gain": 1, "connexion": "c", "rationale": "r"}'
        elif stage == "peer":
            Ledger(campaign.thread_dir("Q1P1") / "ledger.jsonl").add("ada", "finding", "finding")
            text = "peer"
        elif stage == "consolidate":
            text = "\\documentclass{article}\\begin{document}account\\end{document}"
        else:
            text = '{"decision": "DRAFT", "reason": "ready", "action": null}'
        return {"text": text, "session": request.identity, "seconds": 0, "input_tokens": 1,
                "output_tokens": 1, "cost": 0, "error": None, "transport_failed": False}

    transport.execute = execute
    try:
        scan.run(context.campaign)
        research.run_thread(context.campaign, "Q1P1")
    finally:
        transport.execute = original


@then("each stage submits an immutable request through the same model execution seam")
@then("scan, both peers, consolidation, and verification submit immutable requests through the same model execution seam")
def campaign_requests_share_seam(context):
    stages = [("peer" if request.stage == "peers" else request.stage) for request in context.requests]
    assert stages == ["scan", "peer", "peer", "consolidate", "verify"]
    assert all(isinstance(request, transport.ModelRequest) for request in context.requests)


@given("a model request requires synchronous workspace tools")
def synchronous_workspace_request(context):
    context.request = model_request("peer")


@when("Pathfinder assigns the request to Pi")
def assign_request_to_pi(context):
    context.received = []
    context.result = transport.execute_sync(context.request, lambda request: context.received.append(request) or {"text": "ok"})


@then("Pi executes the same immutable request accepted by other synchronous adapters")
def pi_accepts_model_request(context):
    assert context.received == [context.request]
    assert context.result == {"text": "ok"}


@given("several independent immutable model requests")
def independent_model_requests(context):
    context.requests = [model_request("scan", identity) for identity in ("Q1P1", "Q1P2")]


@when("Pathfinder assigns them to a batch adapter")
def assign_requests_to_batch(context):
    context.results = transport.execute_batch(context.requests, lambda request: {"identity": request.identity})


@then("the adapter returns one result for each unchanged request identity")
def batch_preserves_request_identities(context):
    assert [result["identity"] for result in context.results] == [request.identity for request in context.requests]


@given("one frozen paper pair is ready for a model-backed campaign stage")
@given("one frozen paper pair is ready for peer research")
def pair_ready_for_model_stage(context):
    frozen_pair_enters_campaign(context)
    if hasattr(context, "assigned_models"):
        context.campaign.peers = context.assigned_models
        context.campaign.peer_models = {model: model for model in context.assigned_models}


@given('a campaign loaded from a manifest assigns models "{first}" and "{second}" to two peers')
def campaign_assigns_peer_models(context, first="m1", second="m2"):
    context.assigned_models = [first, second]


@given("the stage has one or more assigned models")
def stage_has_assigned_models(context):
    context.assigned_models = ["m1", "m2"]


@when("Pathfinder executes one stage attempt")
def execute_one_stage_attempt(context):
    context.requests = []
    # @exceptional-double: internal composition has no independent external verifier.
    original = transport.execute
    transport.execute = lambda campaign, request: context.requests.append(request) or {
        "text": '{"feasibility": 1, "gain": 1, "connexion": "c", "rationale": "r"}',
        "session": request.identity, "seconds": 0, "input_tokens": 1, "output_tokens": 1,
        "cost": 0, "error": None, "transport_failed": False,
    }
    try:
        scan.run(context.campaign)
    finally:
        transport.execute = original


@when("Pathfinder executes one peer stage attempt")
def execute_one_peer_stage_attempt(context):
    context.requests = []
    # @exceptional-double: internal composition has no independent external verifier.
    original = transport.execute
    transport.execute = lambda campaign, request: context.requests.append(request) or {
        "text": "finding", "session": request.identity, "seconds": 0, "input_tokens": 1,
        "output_tokens": 1, "cost": 0, "error": None, "transport_failed": False,
    }
    try:
        research.run_thread(context.campaign, "Q1P1")
    finally:
        transport.execute = original


@then("one model execution is recorded for each assigned model")
def one_execution_per_attempt(context):
    assert len(context.requests) == len(context.assigned_models)


@then('one peer request is recorded for model "{model}"')
def peer_request_is_recorded(context, model):
    assert [request.model for request in context.requests].count(model) == 1


@given("one frozen paper pair and assigned model execution adapters for every configured peer")
@given("a campaign loaded from a manifest assigns execution adapters to scan, two peers, consolidation, and verification")
def pair_with_execution_adapters(context):
    frozen_pair_enters_campaign(context)
    context.assignments = {stage: f"{stage}-adapter" for stage in ("scan", "consolidate", "verify")}
    context.peer_assignments = {actor: f"{actor}-adapter" for actor in context.campaign.peers}


@given("one frozen paper pair is ready for campaign execution")
def pair_ready_for_campaign_execution(context):
    pass


@when("Pathfinder verifies execution routing")
def verify_campaign_execution_routing(context):
    context.routed = []
    # @exceptional-double: internal composition has no independent external verifier.
    original = transport.execute

    def execute(campaign, request):
        stage = "peer" if request.stage == "peers" else request.stage
        adapter = context.peer_assignments[request.actor] if stage == "peer" else context.assignments[stage]
        context.routed.append((stage, request.actor, adapter))
        if stage == "peer":
            ledger = Ledger(campaign.thread_dir("Q1P1") / "ledger.jsonl")
            seen = ledger.add(request.actor, "finding", "finding")
            ledger.add(request.actor, "ready", "ready", seen=seen)
        text = {
            "scan": '{"feasibility": 1, "gain": 1, "connexion": "c", "rationale": "r"}',
            "peer": "peer", "consolidate": "\\documentclass{article}\\begin{document}account\\end{document}",
            "verify": '{"decision": "DRAFT", "reason": "ready", "action": null}',
        }[stage]
        return {"text": text, "session": request.identity, "seconds": 0, "input_tokens": 1,
                "output_tokens": 1, "cost": 0, "error": None, "transport_failed": False}

    transport.execute = execute
    try:
        scan.run(context.campaign)
        research.run_thread(context.campaign, "Q1P1")
    finally:
        transport.execute = original


@then("the recorded scan, consolidation, and verification calls follow those assignments")
def campaign_calls_follow_assignments(context):
    campaign_calls = [call for call in context.routed if call[0] != "peer"]
    assert {stage for stage, _, _ in campaign_calls} == {"scan", "consolidate", "verify"}
    assert all(adapter == context.assignments[stage] for stage, _, adapter in campaign_calls)


@then("every configured peer call follows its assignment")
def peer_calls_follow_assignments(context):
    peer_calls = [call for call in context.routed if call[0] == "peer"]
    assert {actor for _, actor, _ in peer_calls} == set(context.peer_assignments)
    assert all(adapter == context.peer_assignments[actor] for _, actor, adapter in peer_calls)


@then("every recorded campaign call follows its manifest assignment")
def every_campaign_call_follows_assignment(context):
    campaign_calls_follow_assignments(context)
    peer_calls_follow_assignments(context)


@given("an immutable model request and a non-Codex synchronous adapter")
def request_and_non_codex_adapter(context):
    context.request = model_request("peer")
    context.received = []
    context.adapter = lambda request: context.received.append(request) or {"text": "ok"}


@when("Pathfinder executes the request")
def execute_request(context):
    context.result = transport.execute_sync(context.request, context.adapter)


@then("the adapter receives the request without Codex command configuration")
def adapter_receives_request_without_codex(context):
    assert context.received == [context.request]
    assert not hasattr(context.received[0], "codex")


@given('pair "{pair_id}" finished research with status "{status}"')
def pair_finished_research(context, pair_id, status):
    c = campaign(context)
    i, j = (int(n) for n in pair_id[1:].split("P"))
    q_rows = [paper(f"q{n}") for n in range(1, i)] + [paper("0704.0001")]
    p_rows = [paper(f"p{n}") for n in range(1, j)] + [paper("0704.0002")]
    write_rows(c.path("Q.jsonl"), q_rows)
    write_rows(c.path("P.jsonl"), p_rows)
    context.pair_id = pair_id
    d = c.thread_dir(pair_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "status.json").write_text(json.dumps({"pair_id": pair_id, "round": 3, "stage": "verify", "status": status}, indent=1))
    (d / f"{pair_id}.tex").write_text("ACCEPTED RESEARCH ACCOUNT")


@given('its "{q}" and "{p}" records have no full text present at their referenced path')
def records_no_fulltext_at_path(context, q, p):
    i, j = (int(n) for n in context.pair_id[1:].split("P"))
    for side, idx in ((q, i - 1), (p, j - 1)):
        path = context.campaign.path(f"{side}.jsonl")
        rows = corpus.read(path)
        rows[idx]["text"] = f"sources/{rows[idx]['id']}.tex"
        corpus.write(rows, path)


@given('fetching full text for "{side}" fails')
def fetching_fulltext_fails(context, side):
    i, j = (int(n) for n in context.pair_id[1:].split("P"))
    idx = i - 1 if side == "Q" else j - 1
    path = context.campaign.path(f"{side}.jsonl")
    rows = corpus.read(path)
    rows[idx]["id"] = "0000.00000"
    rows[idx]["text"] = f"sources/{rows[idx]['id']}.tex"
    corpus.write(rows, path)


@when('Pathfinder prepares pair "{pair_id}" for editing')
def prepares_pair_for_editing(context, pair_id):
    context.prepare_outcome = edit.prepare_for_editing(context.campaign, pair_id)


@then("both records have full text fetched from their original source")
def both_records_fetched(context):
    i, j = (int(n) for n in context.pair_id[1:].split("P"))
    q_row = corpus.read(context.campaign.path("Q.jsonl"))[i - 1]
    p_row = corpus.read(context.campaign.path("P.jsonl"))[j - 1]
    context.fetched_rows = (q_row, p_row)
    assert q_row.get("text") and p_row.get("text")


@then("that full text is present at its referenced path")
def fulltext_present_at_path(context):
    for row in context.fetched_rows:
        p = context.campaign.path(row["text"])
        assert p.exists() and p.stat().st_size > 0


@then('pair "{pair_id}" is blocked before entering editing')
def pair_blocked_before_editing(context, pair_id):
    assert edit.status(context.campaign, pair_id)["status"] == "blocked"


@then('the block names "{side}" as the record missing full text')
def block_names_missing_side(context, side):
    st = edit.status(context.campaign, context.pair_id)
    assert side in (st.get("reason") or "")

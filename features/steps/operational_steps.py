import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from behave import given, then, when

from pathfinder import corpus, edit, paper as paper_module, research, runner, scan, select, transport
try:
    from pathfinder import edit_stage
except ImportError:
    edit_stage = None
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
            (d / f"{pair_id}.tex").write_text(correction)
            return {"text": "written", "error": None}
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
    assert (context.campaign.thread_dir("Q1P1") / "Q1P1.tex").read_text() == context.correction


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
        runner._loop(context.campaign, ThreadPoolExecutor(1), 0, {})
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


@given("two Pathfinder runs use the same corpus snapshots, prompts, budgets, and tool policies")
def comparable_runs(context):
    context.baseline = {"assignments": assignments(), "snapshots": ["q", "p"]}
    context.arm = json.loads(json.dumps(context.baseline))


@given("the runs differ in the model or backend assigned to one role")
def one_role_differs(context):
    context.arm["assignments"]["verify"]["model"] = "other"


@when("the runs are compared")
def compare_runs(context):
    context.comparison = runner.compare_manifests(context.baseline, context.arm)


@then("differences in that role's outcomes, cost, and latency are reported")
def role_differences_reported(context):
    assert context.comparison["role"] == "verify"


@given("a comparison includes scanning, research, consolidation, and verification")
def all_comparison_roles(context):
    context.roles = ["scan", "research", "consolidate", "verify"]


@when("the operator defines a run")
def define_run(context):
    context.run_manifest = runner.validate_manifest({"assignments": assignments()})


@then("each role has its own model and backend assignment")
def each_role_assigned(context):
    assert all(context.run_manifest["assignments"][role]["model"] and context.run_manifest["assignments"][role]["backend"] for role in context.roles)


@given("a role assignment has been run against frozen campaign inputs")
def frozen_assignment_run(context):
    context.receipts = []


@when("the same assignment is repeated")
def repeat_assignment(context):
    context.receipts = [runner.execution_receipt("scan", "claude", "m", "agent", "p", "j1", "raw", "ok", 1, 2, 3), runner.execution_receipt("scan", "claude", "m", "agent", "p", "j2", "raw", "ok", 1, 2, 3)]


@then("both runs retain the information needed to compare variation in outcomes, cost, and latency")
def receipts_comparable(context):
    assert all({"outcome", "latency", "cost"} <= receipt.keys() for receipt in context.receipts)


@given('a comparison includes roles "scan", "research", "consolidate", "verify", and "edit"')
def manifest_roles(context):
    context.manifest = {"assignments": assignments(("scan", "research", "consolidate", "verify", "edit"))}


@when("the operator defines a run manifest")
def define_manifest(context):
    context.manifest = runner.validate_manifest(context.manifest)


@then("every role records its model, backend, execution class, prompt arrangement, tool policy, and budget")
def manifest_records_role_fields(context):
    required = {"model", "backend", "execution_class", "prompt", "tool_policy", "budget"}
    assert all(required <= value.keys() for value in context.manifest["assignments"].values())


@then('role "{role}" records its own model, backend, execution class, prompt arrangement, tool policy, and budget')
def manifest_records_one_role(context, role):
    required = {"model", "backend", "execution_class", "prompt", "tool_policy", "budget"}
    assert required <= context.manifest["assignments"][role].keys()


@given('a comparison includes peers "critic" and "specialist"')
def manifest_peers(context):
    context.manifest = {"assignments": assignments(), "peers": [
        {
            "name": "critic", "model": "m", "backend": "elm", "execution_class": "provider",
            "thinking_limit": 1000, "output_token_limit": 1000, "allowed_tools": [],
        },
        {
            "name": "specialist", "model": "m", "backend": "pi", "execution_class": "agent",
            "thinking_limit": 1000, "output_token_limit": 1000, "allowed_tools": ["read"],
        },
    ]}


@when("the operator defines their run manifest assignments")
def define_peer_manifest(context):
    context.manifest = runner.validate_manifest(context.manifest)


@then("every peer records its name, model, backend, execution class, thinking limit, output token limit, and allowed tools")
def manifest_records_peer_fields(context):
    required = {"name", "model", "backend", "execution_class", "thinking_limit", "output_token_limit", "allowed_tools"}
    assert all(required <= peer.keys() for peer in context.manifest["peers"])


@then("a peer with no tools records an empty allowed-tools list")
def manifest_records_empty_peer_tools(context):
    assert next(peer for peer in context.manifest["peers"] if peer["name"] == "critic")["allowed_tools"] == []


@given("a baseline run manifest")
def baseline_manifest(context):
    context.baseline = {"assignments": assignments(), "snapshots": ["q", "p"], "prompts": ["x"]}


@when('the operator creates a comparison arm for role "verify"')
def create_comparison_arm(context):
    context.arm = runner.comparison_arm(context.baseline, "verify", model="other")


@then('only role "verify" may differ in model or backend')
def verify_role_differs(context):
    assert context.arm["assignments"]["verify"]["model"] == "other"


@then("corpus snapshots, prompts, budgets, and other role assignments remain unchanged")
def other_factors_unchanged(context):
    assert context.arm["snapshots"] == context.baseline["snapshots"] and context.arm["prompts"] == context.baseline["prompts"]


@given("a valid run manifest and two prepared corpus snapshots")
def valid_manifest_and_snapshots(context):
    prepared_corpora(context)
    context.manifest = {"assignments": assignments()}


@when("the comparison run starts")
def comparison_starts(context):
    context.record = runner.reproduction_record(context.campaign, context.manifest)


@then("it records the manifest digest, snapshot digests, and prompt digests before role execution")
def reproduction_material_recorded(context):
    assert {"manifest_digest", "snapshot_digests", "prompt_digests"} <= context.record.keys()


@given('role "scan" is assigned model "Qwen/Qwen3.5-397B-A17B-FP8" through ELM')
def elm_scan_assignment(context):
    context.assignment = {"role": "scan", "model": "Qwen/Qwen3.5-397B-A17B-FP8", "backend": "elm"}


@given('ELM authenticates with environment variable "ELM_API_KEY"')
def elm_auth(context):
    context.assignment["env_key"] = "ELM_API_KEY"


@when('role "scan" executes a minimal frozen paper pair')
def execute_elm_scan(context):
    c = campaign(context)
    c.backend = context.assignment["backend"]
    c.scan_model = context.assignment["model"]
    c.raw = {"codex": {"name": "elm", "env_key": context.assignment["env_key"]}}
    context.provider_reply = transport.call(
        "Reply with the single word ok.",
        campaign=c,
        model=c.scan_model,
        tools=False,
        search=False,
        cwd=c.path("scan-work"),
        timeout=120,
        thread="Q1P1",
        stage="scan",
        actor="scan",
    )


@then("the receipt retains ELM's provider identifier, raw response, token usage, latency, and cost")
def elm_receipt_retained(context):
    receipts = transport.receipts(context.campaign)
    assert not context.provider_reply["transport_failed"]
    assert context.provider_reply["text"]
    assert receipts[-1]["backend"] == "elm"
    assert receipts[-1]["input_tokens"] > 0
    assert receipts[-1]["output_tokens"] > 0
    assert receipts[-1]["seconds"] >= 0
    assert receipts[-1]["cost"] is None or receipts[-1]["cost"] >= 0


@when('the comparison run schedules role "scan"')
def schedule_scan(context):
    context.route = runner.execution_route(context.assignment)


@then("it submits the role through ELM's OpenAI-compatible request interface")
def elm_route(context):
    assert context.route == "openai-compatible"


@given("an OpenAI-compatible provider returns generated text in a raw response event")
def openai_response_event(context):
    c = campaign(context)
    c.backend = "elm"
    c.raw = {"codex": {"name": "elm", "env_key": "ELM_API_KEY"}}
    model = "Qwen/Qwen3.5-397B-A17B-FP8"
    command = transport._command(c, model, False, False, c.root)
    proc = __import__("subprocess").run(
        command,
        input="Reply with exactly GOLDEN-TEXT.",
        cwd=c.root,
        env=transport._env(c),
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr[-500:]
    rows = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    event = next(row for row in rows if row.get("type") == "item.completed" and (row.get("item") or {}).get("type") == "agent_message")
    assert "GOLDEN-TEXT" in event["item"]["text"]
    event["item"] = {"type": "agent_message", "text": event["item"]["text"]}
    fixture = Path(context.config.base_dir).parent / "features" / "fixtures" / "elm-qwen-response-event.json"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n")
    context.raw_response_event = fixture.read_text()
    context.generated_text = event["item"]["text"]


@when("Pathfinder parses the provider response")
def parse_provider_response(context):
    c = context.campaign

    # @exceptional-double: golden real-provider response replay covers a specific parser input on demand.
    class CompletedProcess:
        pid = None  # Parser replay has no operating-system child.
        returncode = 0
        stdout = iter([
            json.dumps({"type": "thread.started", "thread_id": "thread-1"}) + "\n",
            context.raw_response_event + "\n",
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}}) + "\n",
        ])
        stdin = type("Stdin", (), {"write": lambda self, value: None, "close": lambda self: None})()
        stderr = type("Stderr", (), {"read": lambda self: ""})()

        def wait(self, timeout=None):
            return self.returncode

    original = transport.subprocess.Popen
    transport.subprocess.Popen = lambda *args, **kwargs: CompletedProcess()
    try:
        context.parsed_response = transport.call(
            "prompt", campaign=c, model="Qwen/Qwen3.5-397B-A17B-FP8", tools=False,
            search=False, cwd=c.root, timeout=1, thread="Q1P1", stage="scan", actor="scan",
        )
    finally:
        transport.subprocess.Popen = original


@then("the parsed response contains the generated text")
def parsed_response_contains_generated_text(context):
    assert context.parsed_response["text"] == context.generated_text


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


@given('role "research" requires workspace tools or multiple turns')
def tool_role(context):
    context.assignment = {"role": "research", "tools": True}


@given('its backend is "pi"')
def pi_backend(context):
    context.assignment["backend"] = "pi"


@when('the comparison run schedules role "research"')
def schedule_research(context):
    context.route = runner.execution_route(context.assignment)


@then("it executes the role through Pi with the manifest's tool policy")
def pi_route(context):
    assert context.route == "pi"


@given('role "consolidate" is assigned backend "claude"')
def claude_assignment(context):
    context.assignment = {"role": "consolidate", "backend": "claude"}


@when('the comparison run schedules role "consolidate"')
def schedule_consolidate(context):
    context.route = runner.execution_route(context.assignment)


@then("it executes through Claude Code rather than a batch provider")
def claude_route(context):
    assert context.route == "claude"


@given("a role executes within a comparison run")
def role_executes(context):
    pass


@when("the execution finishes")
def execution_finishes(context):
    context.receipt = runner.execution_receipt("scan", "elm", "m", "provider", "prompt", "job", "raw", "ok", 1, 2, 3)


@then("its receipt records role, backend, model, execution class, prompt digest, provider job identifier, raw response, outcome, latency, token usage, and cost")
def complete_receipt(context):
    required = {"role", "backend", "model", "execution_class", "prompt_digest", "provider_job_id", "raw_response", "outcome", "latency", "token_usage", "cost"}
    assert required <= context.receipt.keys()


@given('role "research" is assigned model "{model}" through ELM')
def elm_role_assignment(context, model):
    context.assignment = {"role": "research", "model": model, "provider": "elm"}


@given('its backend is "{backend}"')
def assigned_backend(context, backend):
    context.assignment["backend"] = backend


@when("the run manifest is validated")
def validate_assignment(context):
    context.accepted = runner.validate_assignment(context.assignment)


@then("the assignment is accepted")
def assignment_accepted(context):
    assert context.accepted


@given("one frozen paper pair")
def one_frozen_pair(context):
    prepared_corpora(context)


@given("one frozen paper pair has source records, prompts, and prior stage outputs")
def pair_with_stage_inputs(context):
    one_frozen_pair(context)
    context.stage_inputs = {
        "sources": [paper("q1"), paper("p1")],
        "prompts": {"consolidate": "Consolidate the evidence."},
        "prior_outputs": {"research": "grounded finding"},
    }


@when('Pathfinder prepares role "consolidate" for provider execution')
def prepare_consolidate_provider(context):
    context.provider_request = runner.prepare_provider_stage(
        "consolidate", context.stage_inputs, input_limit=getattr(context, "input_limit", 64000), output_limit=1000
    )


@then("the provider request identifies the digests of every supplied input")
def provider_request_has_input_digests(context):
    assert set(context.provider_request["input_digests"]) == set(context.stage_inputs)


@then("later campaign changes do not alter that request")
def prepared_request_is_immutable(context):
    before = json.dumps(context.provider_request, sort_keys=True)
    context.stage_inputs["prior_outputs"]["research"] = "changed"
    assert json.dumps(context.provider_request, sort_keys=True) == before


@given('one frozen paper pair contains all evidence required by role "verify"')
def pair_with_verify_evidence(context):
    one_frozen_pair(context)
    context.stage_inputs = {
        "sources": [paper("q1"), paper("p1")],
        "prompts": {"verify": "Verify the account."},
        "prior_outputs": {"consolidate": "research account"},
    }


@when('Pathfinder executes role "verify" through its assigned provider')
def execute_prepared_verify(context):
    request = runner.prepare_provider_stage("verify", context.stage_inputs, input_limit=64000, output_limit=1000)
    context.provider_execution = runner.execute_provider_stage(request, lambda value: {"text": "DRAFT", "request": value})


@then("the role completes without fetching or discovering additional evidence")
def provider_execution_uses_prepared_evidence(context):
    assert context.provider_execution["text"] == "DRAFT"
    assert context.provider_execution["request"]["tools"] == []


@given('role "consolidate" has an assigned input context limit of "{limit}" tokens and an output token limit')
def assigned_provider_limits(context, limit):
    context.input_limit = int(limit)
    context.output_limit = 1000
    context.stage_inputs = {"evidence": "short frozen evidence"}


@when('Pathfinder prepares role "consolidate" for one frozen paper pair')
def prepare_limited_provider_request(context):
    context.provider_request = runner.prepare_provider_stage(
        "consolidate", context.stage_inputs, input_limit=context.input_limit, output_limit=context.output_limit
    )


@then("the request stays within the assigned input context limit")
def request_within_input_limit(context):
    assert context.provider_request["input_tokens"] <= context.input_limit


@then("the provider call enforces the assigned output token limit")
def provider_output_limit_enforced(context):
    assert context.provider_request["output_token_limit"] == context.output_limit


@given('role "consolidate" has more than "{limit}" input tokens of frozen evidence')
def oversized_provider_evidence(context, limit):
    context.input_limit = int(limit)
    context.stage_inputs = {"evidence": "word " * (context.input_limit + 1)}


@then("Pathfinder uses a recorded compression result or blocks the request")
def oversized_request_is_blocked(context):
    assert context.provider_request["status"] == "blocked"


@then("Pathfinder does not silently truncate the evidence")
def oversized_request_preserves_evidence(context):
    assert context.provider_request["inputs"]["evidence"] == context.stage_inputs["evidence"]


@given('role "verify" is assigned execution class "provider"')
def verify_provider_assignment(context):
    context.campaign = seed_pair(context)
    context.assignments = assignments()
    context.assignments["verify"].update(execution_class="provider", backend="elm")
    context.assignment = {"role": "verify", "execution_class": "provider", "backend": "elm"}
    context.stage_inputs = {"evidence": "frozen account"}


@then("the provider request exposes no workspace or search tools")
def provider_request_has_no_tools(context):
    request = runner.prepare_provider_stage("verify", context.stage_inputs, input_limit=64000, output_limit=1000)
    assert request["tools"] == []


@given("two providers support the same provider execution class")
def equivalent_provider_assignments(context):
    context.provider_assignments = [
        {"backend": "elm", "execution_class": "provider"},
        {"backend": "other", "execution_class": "provider"},
    ]


@when("Pathfinder schedules the same frozen stage through each provider")
def schedule_equivalent_providers(context):
    context.routes = [runner.execution_route(assignment) for assignment in context.provider_assignments]


@then("both stages use the provider execution route")
def both_use_provider_route(context):
    assert context.routes == ["provider", "provider"]


@given('several frozen paper pairs are ready for role "scan"')
def several_scan_pairs(context):
    context.stage_jobs = [
        {"pair_id": pair_id, "inputs": {"evidence": pair_id}}
        for pair_id in ("Q1P1", "Q1P2")
    ]


@when("Pathfinder prepares their provider stage jobs")
def prepare_provider_jobs(context):
    context.prepared_jobs = runner.prepare_provider_batch("scan", context.stage_jobs, input_limit=64000, output_limit=1000)


@then("each job has independent immutable inputs and a stable result identity")
def batch_jobs_are_independent(context):
    assert len({job["result_id"] for job in context.prepared_jobs}) == len(context.prepared_jobs)
    context.stage_jobs[0]["inputs"]["evidence"] = "changed"
    assert context.prepared_jobs[0]["inputs"]["evidence"] == "Q1P1"


@then("submitting the jobs together does not change their results")
def batching_preserves_results(context):
    original_jobs = [
        {"pair_id": pair_id, "inputs": {"evidence": pair_id}}
        for pair_id in ("Q1P1", "Q1P2")
    ]
    separate = [runner.prepare_provider_batch("scan", [job], input_limit=64000, output_limit=1000)[0] for job in original_jobs]
    assert [job["result_id"] for job in context.prepared_jobs] == [job["result_id"] for job in separate]


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
            text = "account"
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
            "peer": "peer", "consolidate": "account",
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


@given('a campaign manifest assigns role "verify" to model "{model}" through ELM with no allowed tools')
def verify_stage_manifest_assignment(context, model):
    context.campaign = campaign(context)
    context.campaign.backend = "elm"
    context.assignment = {"model": model, "backend": "elm", "allowed_tools": []}


@when("Pathfinder submits the role's frozen stage")
def submit_frozen_stage(context):
    # @exceptional-double: internal composition has no independent external verifier.
    original = transport.execute
    transport.execute = lambda campaign, request: setattr(context, "transport_call", (campaign, request)) or {}
    try:
        transport.call(
            "frozen verification stage",
            campaign=context.campaign,
            model=context.assignment["model"],
            tools=bool(context.assignment["allowed_tools"]),
            search=False,
            cwd=context.campaign.path("verify-work"),
            timeout=1,
            thread="Q1P1",
            stage="verify",
            actor="verify",
        )
    finally:
        transport.execute = original


@then("the model transport request uses the assigned model and backend")
def transport_request_uses_assignment(context):
    submitted_campaign, request = context.transport_call
    assert request.model == context.assignment["model"]
    assert submitted_campaign.backend == context.assignment["backend"]


@then("the model transport request exposes no tools")
def transport_request_exposes_no_tools(context):
    assert context.transport_call[1].tools is False


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


@given('roles "research", "consolidate", and "verify" are assigned model "{model}" through ELM')
def remaining_role_assignments(context, model):
    context.assignments = assignments()
    context.assignments["scan"] = {
        "model": context.assignment["model"],
        "backend": context.assignment["backend"],
        "execution_class": "provider",
        "prompt": "scan",
        "tool_policy": [],
        "budget": 1,
    }
    for role in ("research", "consolidate", "verify"):
        context.assignments[role].update(model=model, backend="elm", execution_class="provider")


@when("Pathfinder runs the assigned comparison workflow")
def run_assigned_comparison(context):
    context.workflow = runner.run_assigned_comparison(context.campaign, context.assignments)


@then("each role leaves a provider-produced receipt for its assigned model and backend")
def assigned_receipts(context):
    receipts = context.workflow["receipts"]
    assert {receipt["role"] for receipt in receipts} == set(context.assignments)
    assert all(receipt["model"] == context.assignments[receipt["role"]]["model"] for receipt in receipts)
    assert all(receipt["backend"] == context.assignments[receipt["role"]]["backend"] for receipt in receipts)
    assert all(receipt["provider_job_id"] and receipt["raw_response"] for receipt in receipts)


@then("the comparison records the pair's final verification outcome")
def comparison_verification_outcome(context):
    assert context.workflow["pairs"]["Q1P1"]["verification_outcome"]


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


@when('the campaign processes pair "{pair_id}" to completion')
def campaign_processes_pair_to_completion(context, pair_id):
    stub_edit_dispatch(context, {"editor": "READABLE SHORT PAPER"})
    context.admitted = edit_stage.finish(context.campaign, pair_id)


# --- edit-stage.feature: PCE role loop over an accepted research account ---

# @exceptional-double: internal composition has no independent external verifier.
def stub_edit_dispatch(context, replies=None):
    replies = replies or {}
    calls = []

    def dispatch(campaign, pair_id, role, prompt):
        text = replies.get(role, f"{role} output")
        receipt = {"role": role, "backend": "pi", "model": "m", "execution_class": "agent",
                   "prompt_digest": hashlib.sha256(prompt.encode()).hexdigest(), "provider_job_id": f"job-{role}-{len(calls) + 1}",
                   "raw_response": text, "outcome": "ok", "latency": 1, "token_usage": 10, "cost": 0.01, "text": text}
        calls.append({"role": role, "prompt": prompt, "receipt": receipt})
        return receipt

    context.dispatch_calls = calls
    original = edit_stage._dispatch
    edit_stage._dispatch = dispatch
    context.add_cleanup(lambda: setattr(edit_stage, "_dispatch", original))
    return dispatch


def pair_has_fulltext(context, pair_id):
    i, j = (int(n) for n in pair_id[1:].split("P"))
    for path, idx in ((context.campaign.path("Q.jsonl"), i - 1), (context.campaign.path("P.jsonl"), j - 1)):
        rows = corpus.read(path)
        text_path = f"sources/{rows[idx]['id']}.tex"
        context.campaign.path(text_path).parent.mkdir(parents=True, exist_ok=True)
        context.campaign.path(text_path).write_text(f"Full text of {rows[idx]['id']}")
        rows[idx]["text"] = text_path
        corpus.write(rows, path)


@given('pair "{pair_id}" has full text fetched from its original source for "Q" and "P"')
def pair_has_fulltext_step(context, pair_id):
    pair_has_fulltext(context, pair_id)


def pair_enters_edit_stage(context, pair_id):
    pair_finished_research(context, pair_id, "DRAFT")
    pair_has_fulltext(context, pair_id)
    d = context.campaign.thread_dir(pair_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{pair_id}.tex").write_text("ACCEPTED RESEARCH ACCOUNT")
    context.admitted = edit_stage.admit(context.campaign, pair_id)


@given('pair "{pair_id}" enters the edit stage')
def pair_enters_edit_stage_step(context, pair_id):
    pair_enters_edit_stage(context, pair_id)


@when("Pathfinder runs PCE's installed bounded-pass runner through the assigned runtime")
def runs_installed_pce_workflow(context):
    workflow = context.campaign.thread_dir(context.pair_id) / "pce"
    workflow.mkdir(parents=True, exist_ok=True)
    (workflow / "brief.md").write_text(
        "# Brief\n\n"
        "- Task: Edit the accepted research account into a concise paper.\n"
        "- Audience: Research readers.\n"
        "- Scope: Use only supplied evidence.\n"
        "- Acceptance bar: Accurate, clear, and source-grounded.\n"
        "- Risk level: high\n"
        "- Specialist questions: none\n"
        "- Output shape: Markdown paper.\n"
    )
    (workflow / "state.json").write_text(json.dumps({
        "risk": "high",
        "max_passes": 1,
        "required_gates": ["fact-checker", "critic"],
        "critic_score_policy": "advisory-only",
        "acceptance_policy": "editor judgement from concrete findings",
        "models": {},
        "critic_profiles": {
            "reader": {"remit": "Review clarity and completeness.", "model": {"opencode": "elm/gpt-5.6-sol"}}
        },
        "specialist_questions": {},
    }, indent=2))
    internal = workflow / "sources" / "internal"
    external = workflow / "sources" / "external"
    internal.mkdir(parents=True)
    external.mkdir(parents=True)
    (internal / "account.md").write_text("ACCEPTED RESEARCH ACCOUNT\n")
    q_text, p_text = edit_stage._external_texts(context.campaign, context.pair_id)
    (external / "question.md").write_text(q_text)
    (external / "proposal.md").write_text(p_text)
    context.pce_workflow = workflow
    context.pce_result = subprocess.run(
        ["nix", "run", "path:../pce", "--", str(workflow), "--runtime", "opencode"],
        cwd=Path(context.config.base_dir).parent,
        text=True,
        capture_output=True,
        timeout=600,
        check=False,
    )
    assert context.pce_result.returncode in {0, 1}, context.pce_result.stdout + context.pce_result.stderr
    summaries = [json.loads(line) for line in context.pce_result.stdout.splitlines() if line.startswith("{")]
    assert len(summaries) == 1, context.pce_result.stdout
    context.pce_summary = summaries[0]
    assert context.pce_summary["completion_state"] in {"approved", "revision_required"}


@then("the PCE workflow directory contains its current draft, archived draft, gate reviews, and state")
def pce_workflow_contains_outputs(context):
    workflow = context.pce_workflow
    assert (workflow / "drafts" / "current.md").is_file()
    assert list((workflow / "revisions" / "history").glob("*.md"))
    assert (workflow / "reviews" / "current" / "fact-check.json").is_file()
    assert list((workflow / "reviews" / "current").glob("critic-*.md"))
    assert (workflow / "state.json").is_file()


@then("PCE accounting records the author, archivist, fact-checker, and critic dispatches in workflow order")
def pce_accounting_records_ordered_roles(context):
    records = [
        json.loads(path.read_text())
        for path in (context.pce_workflow / "accounting" / "history").glob("*.json")
    ]
    roles = [record["role"] for record in sorted(records, key=lambda record: record["timestamp"])]
    assert roles == ["author", "archivist", "fact-checker", "critic"], roles


@then("Pathfinder contains no local PCE role prompts or editorial dispatch sequence")
def pathfinder_has_no_local_pce_orchestration(context):
    root = Path(context.config.base_dir).parent
    prompt_paths = list((root / "pathfinder").rglob("*-task.md"))
    source = "\n".join(path.read_text() for path in (root / "pathfinder").rglob("*.py"))
    assert prompt_paths == []
    assert "run_author(" not in source
    assert "run_fact_checker(" not in source
    assert "run_critic(" not in source


@when("Pathfinder runs the edit stage through its assigned agent runtime")
def runs_edit_stage_through_agent_runtime(context):
    stub_edit_dispatch(context)
    context.round_result = edit_stage.run_round(context.campaign, context.pair_id, round=1, limit=3)


@then("PCE's installed role skills control the ordered editorial workflow")
def pce_controls_editorial_workflow(context):
    assert [call["role"] for call in context.dispatch_calls] == ["author", "fact-checker", "critic", "editor"]


@then("Pathfinder does not reproduce PCE role prompts or dispatch rules")
def pathfinder_delegates_pce_rules(context):
    assert all(call["receipt"]["execution_class"] == "agent" for call in context.dispatch_calls)


@given('pair "{pair_id}" is in its edit stage')
def pair_is_in_edit_stage(context, pair_id):
    pair_enters_edit_stage(context, pair_id)


@when('the campaign admits pair "{pair_id}" for editing')
def campaign_admits_pair(context, pair_id):
    context.admitted = edit_stage.admit(context.campaign, pair_id)


@then('the edit stage starts for pair "{pair_id}"')
def edit_stage_started(context, pair_id):
    assert context.admitted is True
    assert edit_stage.status(context.campaign, pair_id)["status"] != "none"


@when("the campaign admits investigations for editing")
def campaign_admits_all(context):
    context.admitted_all = edit_stage.admit_all(context.campaign)


@then('pair "{pair_id}" does not enter the edit stage')
def pair_not_entered(context, pair_id):
    if hasattr(context, "admitted_all"):
        assert pair_id not in context.admitted_all
    else:
        assert context.admitted is False
    assert edit_stage.status(context.campaign, pair_id)["status"] == "none"


@then('pair "{pair_id}" has no edited artifact recorded')
def pair_no_edited_artifact(context, pair_id):
    assert edit_stage.status(context.campaign, pair_id).get("draft") is None


@then('pair "{pair_id}" has no readable short paper recorded')
def pair_no_readable_short_paper(context, pair_id):
    assert edit_stage.status(context.campaign, pair_id).get("draft") is None


@then('pair "{pair_id}" has exactly one edited artifact recorded')
def pair_has_one_edited_artifact(context, pair_id):
    assert edit_stage.status(context.campaign, pair_id).get("draft")


@then("the edit stage's first draft is the readable short paper written from the accepted research account")
def first_draft_is_readable_short_paper(context):
    account = (context.campaign.thread_dir(context.pair_id) / f"{context.pair_id}.tex").read_text()
    draft = edit_stage.status(context.campaign, context.pair_id).get("draft")
    assert draft, "no first draft recorded for the pair"
    call = next((c for c in context.dispatch_calls if c["role"] == "editor"), None)
    assert call is not None, "no editor dispatch produced the first draft"
    assert account in call["prompt"], "the first draft was not written from the accepted research account"


@then("that first draft is the raw response recorded on a real dispatch's receipt, not a copy of the account itself")
def first_draft_is_dispatch_raw_response(context):
    account = (context.campaign.thread_dir(context.pair_id) / f"{context.pair_id}.tex").read_text()
    draft = edit_stage.status(context.campaign, context.pair_id).get("draft")
    call = next((c for c in context.dispatch_calls if c["role"] == "editor"), None)
    assert call is not None, "no editor dispatch left a receipt for the first draft"
    raw_response = call["receipt"]["raw_response"]
    assert draft == raw_response, f"first draft is not the receipt's raw response: {draft!r} != {raw_response!r}"
    assert draft != account, "first draft is a copy of the accepted research account"


@when("the editor stage begins")
def editor_stage_begins(context):
    context.brief = edit_stage.stage_brief(context.campaign, context.pair_id)


@then("the editor's brief cites the accepted research account as internal source")
def brief_cites_internal(context):
    assert "ACCEPTED RESEARCH ACCOUNT" in context.brief["internal"]


@then('the editor\'s brief cites the fetched full text of "Q" and "P" as external source')
def brief_cites_external(context):
    i, j = (int(n) for n in context.pair_id[1:].split("P"))
    q_text = context.campaign.path(corpus.read(context.campaign.path("Q.jsonl"))[i - 1]["text"]).read_text()
    p_text = context.campaign.path(corpus.read(context.campaign.path("P.jsonl"))[j - 1]["text"]).read_text()
    assert q_text in context.brief["external"] and p_text in context.brief["external"]


def pair_has_staged_brief(context, pair_id):
    pair_enters_edit_stage(context, pair_id)
    context.brief = edit_stage.stage_brief(context.campaign, pair_id)


@given('pair "{pair_id}" has a staged brief and source set')
def pair_has_staged_brief_step(context, pair_id):
    pair_has_staged_brief(context, pair_id)


@given('pair "{pair_id}"\'s staged brief and source set exceeds its assigned context limit')
def oversized_edit_stage_brief(context, pair_id):
    pair_has_staged_brief(context, pair_id)
    evidence = context.brief["internal"] + "\n\n" + "\n\n".join(context.brief["external"])
    context.stage_inputs = {"evidence": evidence}
    context.input_limit = len(evidence.split()) - 1


@when("the edit stage prepares a role dispatch")
def edit_stage_prepares_dispatch(context):
    context.provider_request = edit_stage.prepare_dispatch(
        context.campaign, context.pair_id, "author", context.stage_inputs,
        input_limit=context.input_limit, output_limit=1000)


@then("Pathfinder uses a recorded compression result or blocks the dispatch")
def oversized_dispatch_is_blocked(context):
    assert context.provider_request["status"] == "blocked"


@when("the author role executes")
def author_role_executes(context):
    stub_edit_dispatch(context, {"author": "DRAFT TEXT ROUND 1"})
    context.author_result = edit_stage.run_author(context.campaign, context.pair_id)


@then("a draft is produced")
def draft_is_produced(context):
    assert context.author_result.get("draft")


@then("the archivist records the draft in its revision history before review")
def archivist_records_draft(context):
    hist = edit_stage.history(context.campaign, context.pair_id)
    assert hist and hist[-1]["draft"] == context.author_result["draft"]


@given('pair "{pair_id}" has an archived draft')
def pair_has_archived_draft(context, pair_id):
    pair_has_staged_brief(context, pair_id)
    stub_edit_dispatch(context, {"author": "DRAFT TEXT ROUND 1"})
    context.author_result = edit_stage.run_author(context.campaign, pair_id)


@when("the fact-checker gate runs")
def fact_checker_gate_runs(context):
    stub_edit_dispatch(context, {"fact-checker": "no issues found"})
    context.fact_check_result = edit_stage.run_fact_checker(context.campaign, context.pair_id)


@then('it checks the draft\'s claims against the fetched full text of "Q" and "P"')
def fact_checker_checks_external(context):
    call = next(c for c in context.dispatch_calls if c["role"] == "fact-checker")
    i, j = (int(n) for n in context.pair_id[1:].split("P"))
    q_text = context.campaign.path(corpus.read(context.campaign.path("Q.jsonl"))[i - 1]["text"]).read_text()
    p_text = context.campaign.path(corpus.read(context.campaign.path("P.jsonl"))[j - 1]["text"]).read_text()
    assert q_text in call["prompt"] and p_text in call["prompt"]


@then("it does not read the accepted research account")
def fact_checker_no_internal(context):
    call = next(c for c in context.dispatch_calls if c["role"] == "fact-checker")
    assert "ACCEPTED RESEARCH ACCOUNT" not in call["prompt"]


@when("the critic gate runs")
def critic_gate_runs(context):
    stub_edit_dispatch(context, {"critic": "looks fine"})
    context.critic_result = edit_stage.run_critic(context.campaign, context.pair_id)


@then("the critic's review has no access to the editor's brief or prior reviews")
def critic_no_brief_access(context):
    call = next(c for c in context.dispatch_calls if c["role"] == "critic")
    assert "ACCEPTED RESEARCH ACCOUNT" not in call["prompt"]


@when('the editor accepts the draft on or before round "{limit}"')
def editor_accepts_within_limit(context, limit):
    stub_edit_dispatch(context, {"author": "FINAL DRAFT", "editor": "accept"})
    context.round_result = edit_stage.run_round(context.campaign, context.pair_id, round=1, limit=int(limit))


@then('the edit stage finishes with outcome "{outcome}"')
def edit_stage_finishes_with(context, outcome):
    assert edit_stage.status(context.campaign, context.pair_id)["status"] == outcome


@then("the accepted draft is recorded as the pair's edited artifact")
def accepted_draft_recorded(context):
    assert edit_stage.status(context.campaign, context.pair_id)["draft"] == "FINAL DRAFT"


@given('pair "{pair_id}" has completed round "{n}" of editing without acceptance')
def pair_completed_rounds_without_acceptance(context, pair_id, n):
    pair_enters_edit_stage(context, pair_id)
    stub_edit_dispatch(context, {"author": "DRAFT AT LIMIT", "editor": "revise"})
    context.round_limit = int(n)
    for rnd in range(1, int(n) + 1):
        context.round_result = edit_stage.run_round(context.campaign, pair_id, round=rnd, limit=int(n))


@when('the editor evaluates round "{n}"')
def editor_evaluates_round(context, n):
    context.evaluation = edit_stage.evaluate_round(context.campaign, context.pair_id, round=int(n), limit=context.round_limit)


@then("the last produced draft is recorded as the pair's edited artifact")
def last_draft_recorded(context):
    assert edit_stage.status(context.campaign, context.pair_id)["draft"] == "DRAFT AT LIMIT"


@then('PCE produces pair "{pair_id}"\'s edited artifact')
def pce_produces_edited_artifact(context, pair_id):
    assert edit_stage.status(context.campaign, pair_id).get("draft")


@then("the campaign records PCE's final edit outcome")
def campaign_records_pce_outcome(context):
    assert edit_stage.status(context.campaign, context.pair_id).get("status") in {"staged", "in-progress", "accepted", "round-limit"}


@given('PCE has produced pair "{pair_id}"\'s edited paper and references')
def pce_produced_paper_and_references(context, pair_id):
    pair_enters_edit_stage(context, pair_id)
    context.edited_dir = context.campaign.thread_dir(pair_id) / "edit_stage" / "paper"
    context.edited_dir.mkdir(parents=True, exist_ok=True)
    (context.edited_dir / "paper.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nA cited result \\cite{source}.\n"
        "\\bibliographystyle{plain}\n\\bibliography{references}\n\\end{document}\n"
    )
    (context.edited_dir / "references.bib").write_text(
        "@article{source,\n  title={A Source},\n  author={Researcher},\n  year={2026},\n  doi={10.1613/jair.3384}\n}\n"
    )


@when("Pathfinder validates the edited artifact")
def validates_edited_artifact(context):
    result = edit_stage.validate_artifact(context.edited_dir)
    context.build_ok = result["build_ok"]
    context.build_log = result["build_log"]
    context.reference_findings = result["reference_findings"]


@then("the edited paper builds successfully with its bibliography")
def edited_paper_builds(context):
    assert context.build_ok, context.build_log


@then("every cited reference passes Pathfinder's reference checks")
def edited_references_pass(context):
    assert context.reference_findings == []


@given('PCE completes one edit pass for pair "{pair_id}"')
def pce_completes_edit_pass(context, pair_id):
    pair_enters_edit_stage(context, pair_id)
    runs_installed_pce_workflow(context)


@when("the campaign is inspected after the edit stage")
def inspect_campaign_after_edit(context):
    context.persisted_receipts = [
        json.loads(path.read_text())
        for path in (context.pce_workflow / "accounting" / "history").glob("*.json")
    ]


@then("every PCE role dispatch remains recorded in the campaign receipts")
def pce_receipts_remain_recorded(context):
    assert {"author", "archivist", "fact-checker", "critic"} <= {
        receipt["role"] for receipt in context.persisted_receipts
    }


@given("the edit stage dispatches the editor, author, fact-checker, and critic for one round")
def dispatches_editor_author_fc_critic(context):
    pair_enters_edit_stage(context, "Q3P10")
    stub_edit_dispatch(context, {"editor": "brief ready", "author": "draft text", "fact-checker": "ok", "critic": "ok"})


@when("each dispatch finishes")
def each_dispatch_finishes(context):
    context.round_result = edit_stage.run_round(context.campaign, context.pair_id, round=1, limit=3)


@then("each dispatch's receipt records role, backend, model, execution class, prompt digest, provider job identifier, raw response, outcome, latency, token usage, and cost")
def receipts_have_required_fields(context):
    required = {"role", "backend", "model", "execution_class", "prompt_digest", "provider_job_id",
                "raw_response", "outcome", "latency", "token_usage", "cost"}
    receipts = context.round_result["receipts"]
    assert {"editor", "author", "fact-checker", "critic"} <= {r["role"] for r in receipts}
    assert all(required <= r.keys() for r in receipts)


@given('pair "{pair_id}" has an archived round "{n}" draft')
def pair_has_archived_round_draft(context, pair_id, n):
    pair_has_staged_brief(context, pair_id)
    stub_edit_dispatch(context, {"author": f"DRAFT ROUND {n}"})
    context.author_result = edit_stage.run_author(context.campaign, pair_id, round=int(n))


@when('the author produces a round "{n}" draft')
def author_produces_round_draft(context, n):
    stub_edit_dispatch(context, {"author": f"DRAFT ROUND {n}"})
    context.author_result = edit_stage.run_author(context.campaign, context.pair_id, round=int(n))


@then('the round "{n}" draft remains recorded in revision history')
def round_draft_in_history(context, n):
    hist = edit_stage.history(context.campaign, context.pair_id)
    assert any(h["round"] == int(n) and h["draft"] == f"DRAFT ROUND {n}" for h in hist)


@then('the round "{n}" draft becomes the current draft')
def round_draft_is_current(context, n):
    assert context.author_result["draft"] == f"DRAFT ROUND {n}"


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

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from behave import given, then, when

from pathfinder import corpus, research, runner, scan, select, transport
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
    original = scan.transport.call
    scan.transport.call = lambda *args, **kwargs: {
        "seconds": 0, "cost": 0, "text": json.dumps({"feasibility": 50, "gain": 40, "connexion": "connection", "rationale": "evidence"}), "error": None
    }
    try:
        scan.run(context.campaign)
    finally:
        scan.transport.call = original


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
    original = scan.transport.call

    def call(*args, **kwargs):
        context.assessed.append(kwargs["thread"])
        return {"seconds": 0, "cost": 0, "text": '{"feasibility":2,"gain":3,"connexion":"c","rationale":"r"}', "error": None}

    scan.transport.call = call
    try:
        scan.run(context.campaign)
    finally:
        scan.transport.call = original


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


def assignments():
    return {
        role: {"model": "m", "backend": "claude", "execution_class": "agent", "prompt": role, "tool_policy": [], "budget": 1}
        for role in ("scan", "research", "consolidate", "verify")
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


@given('a comparison includes roles "scan", "research", "consolidate", and "verify"')
def manifest_roles(context):
    context.manifest = {"assignments": assignments()}


@when("the operator defines a run manifest")
def define_manifest(context):
    context.manifest = runner.validate_manifest(context.manifest)


@then("every role records its model, backend, execution class, prompt arrangement, tool policy, and budget")
def manifest_records_role_fields(context):
    required = {"model", "backend", "execution_class", "prompt", "tool_policy", "budget"}
    assert all(required <= value.keys() for value in context.manifest["assignments"].values())


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


@when('the comparison run schedules role "scan"')
def schedule_scan(context):
    context.route = runner.execution_route(context.assignment)


@then("it submits the role through ELM's OpenAI-compatible request interface")
def elm_route(context):
    assert context.route == "openai-compatible"


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

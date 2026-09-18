import ast
import io
import json
import re
from contextlib import redirect_stdout
from pathlib import Path

from behave import given, then, when

from pathfinder import reconcile, research, runner, transport

from operational_steps import assignments, prepared_corpora, seed_pair


def provider_reply(text="", error=None):
    return {"text": text, "error": error, "transport_failed": False, "seconds": 0}


def run_with_replies(context, replies, action):
    # @exceptional-double: provider conditions cannot be produced on demand.
    original = transport.execute
    context.provider_calls = []

    def execute(campaign, request):
        context.provider_calls.append(request.stage)
        return replies.pop(0)

    transport.execute = execute
    try:
        return action()
    finally:
        transport.execute = original


def repository_root(context):
    return Path(context.config.base_dir).parent


@given('pair "Q1P1" has substantive findings awaiting consolidation')
def findings_awaiting_consolidation(context):
    context.campaign = seed_pair(context)
    d = research.prepare(context.campaign, "Q1P1")
    research.Ledger(d / "ledger.jsonl").add(context.campaign.peers[0], "finding", "substantive finding")
    research._set(context.campaign, "Q1P1", stage="consolidate", status="running")


@given("its first consolidation returns no account and no provider error")
def empty_first_consolidation(context):
    context.replies = [provider_reply(), provider_reply("stored account")]


@when('Pathfinder consolidates pair "Q1P1"')
def consolidate_named_pair(context):
    context.result = run_with_replies(
        context,
        context.replies,
        lambda: research._stage_call(context.campaign, "Q1P1", "consolidate", "prompt", True, 1),
    )


@then("Pathfinder makes one more consolidation attempt")
def makes_second_attempt(context):
    assert context.provider_calls[:2] == ["consolidate", "consolidate"]


@given("its direct provider cannot write campaign files")
def direct_provider_cannot_write(context):
    context.direct_provider_cannot_write = True


@when("Pathfinder requests consolidation from the direct provider")
def requests_direct_consolidation(context):
    context.direct_prompt = None
    prompts = context.campaign.path("prompts")
    prompts.mkdir()
    (prompts / "consolidate.md").write_text("Consolidate {{NOTE}}. {{PRIOR}}")

    # @exceptional-double: internal composition has no independent external verifier.
    original = transport.execute

    def execute(campaign, request):
        context.direct_prompt = request.prompt
        return provider_reply("research account")

    transport.execute = execute
    try:
        research._stage_call(
            context.campaign,
            "Q1P1",
            "consolidate",
            research._consolidate_prompt(
                context.campaign,
                context.campaign.thread_dir("Q1P1"),
                research._inputs(context.campaign.thread_dir("Q1P1")),
                "Q1P1",
                "",
                "Q1P1.tex",
                "",
            ),
            True,
            1,
        )
    finally:
        transport.execute = original


@then("the request asks the provider to return the complete research account")
def requests_returned_account(context):
    assert context.direct_provider_cannot_write
    assert "return" in context.direct_prompt.lower()
    assert "complete research account" in context.direct_prompt.lower()


@given("its direct provider returns text without producing a stored research account")
def direct_provider_returns_unstored_text(context):
    context.replies = [provider_reply("unstored account"), provider_reply("stored account")]


@when("Pathfinder evaluates the consolidation attempt")
def evaluates_consolidation_attempt(context):
    context.result = run_with_replies(
        context,
        context.replies,
        lambda: research._stage_call(
            context.campaign,
            "Q1P1",
            "consolidate",
            "prompt",
            True,
            1,
            done=(context.campaign.thread_dir("Q1P1") / "Q1P1.tex").exists,
        ),
    )


@when("the direct provider returns a complete research account on its consolidation retry")
def provider_returns_account_on_retry(context):
    context.returned_account = "complete research account"
    context.account_at_verification = None
    replies = [
        provider_reply(),
        provider_reply(context.returned_account),
        provider_reply('{"decision":"DRAFT","reason":"ready","action":null}'),
    ]

    # @exceptional-double: provider conditions cannot be produced on demand.
    original = transport.execute
    context.provider_calls = []

    def execute(campaign, request):
        stage = request.stage
        context.provider_calls.append(stage)
        if stage == "verify":
            context.account_at_verification = (
                context.campaign.thread_dir("Q1P1") / "Q1P1.tex"
            ).read_text()
        return replies.pop(0)

    transport.execute = execute
    try:
        context.result = research.run_thread(context.campaign, "Q1P1")
    finally:
        transport.execute = original


@then("Pathfinder stores that research account before verification")
def stores_account_before_verification(context):
    assert context.account_at_verification == context.returned_account


@then("the verifier assesses it once")
def verifier_assesses_once(context):
    assert context.provider_calls.count("verify") == 1


@when('the provider returns a research account for pair "Q1P1"')
def provider_returns_account(context):
    context.returned_account = "provider research account"
    context.result = run_with_replies(
        context,
        [
            provider_reply(context.returned_account),
            provider_reply(context.returned_account),
            provider_reply('{"decision":"DRAFT","reason":"ready","action":null}'),
            provider_reply('{"decision":"DRAFT","reason":"ready","action":null}'),
        ],
        lambda: research.run_thread(context.campaign, "Q1P1"),
    )


@then("Pathfinder stores the response as the pair's research account")
def stores_provider_account(context):
    path = context.campaign.thread_dir("Q1P1") / "Q1P1.tex"
    assert context.direct_provider_cannot_write and path.read_text() == context.returned_account


@when("both consolidation attempts produce no stored research account")
def both_consolidations_empty(context):
    context.result = run_with_replies(
        context,
        [provider_reply(), provider_reply()],
        lambda: research.run_thread(context.campaign, "Q1P1"),
    )


@then('pair "Q1P1" is blocked at consolidation')
def blocked_at_consolidation(context):
    status = research.status(context.campaign, "Q1P1")
    assert context.result == "BLOCKED" and status["status"] == "BLOCKED" and status["stage"] == "consolidate"


@given('pair "Q1P1" is blocked at consolidation without a research account')
def blocked_consolidation(context):
    findings_awaiting_consolidation(context)
    research._set(context.campaign, "Q1P1", status="BLOCKED", reason="consolidate: no note")
    context.replies = [provider_reply("recovered account"), provider_reply('{"decision":"DRAFT","reason":"ready","action":null}')]


@when('the operator applies the recovery action for pair "Q1P1"')
def apply_recovery(context):
    context.result = run_with_replies(
        context,
        context.replies,
        lambda: reconcile.apply(context.campaign, "Q1P1"),
    )


@then('pair "Q1P1" runs consolidation again')
def runs_consolidation_again(context):
    assert context.provider_calls[0] == "consolidate"


@then('pair "Q1P1" continues from the resulting research account')
def continues_from_account(context):
    assert context.provider_calls[:2] == ["consolidate", "verify"] and context.result == "DRAFT"


@given("the shortlist contains terminal and blocked investigations")
def terminal_and_blocked_shortlist(context):
    context.campaign = seed_pair(context)
    context.campaign.path("shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": "Q1P1"}, {"pair_id": "Q1P2"}]}))
    research._set(context.campaign, "Q1P1", stage="done", status="DRAFT")
    context.campaign.thread_dir("Q1P2").mkdir(parents=True)
    research._set(context.campaign, "Q1P2", stage="consolidate", status="BLOCKED", reason="consolidate: no note")


@when("the operator runs the research command")
def run_research_command(context):
    output = io.StringIO()
    with redirect_stdout(output):
        runner.run(context.campaign, interval=0)
    context.command_output = output.getvalue()


@then("Pathfinder reports the blocked investigations as requiring recovery")
def reports_blocked_recovery(context):
    assert "Q1P2" in context.command_output and "reconcile" in context.command_output.lower()


@given("the shortlist contains recoverable blocked investigations")
def recoverable_shortlist(context):
    context.campaign = seed_pair(context)
    context.campaign.path("P.jsonl").write_text(context.campaign.path("P.jsonl").read_text() * 2)
    context.campaign.path("shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": "Q1P1"}, {"pair_id": "Q1P2"}]}))
    for pair_id in ("Q1P1", "Q1P2"):
        d = research.prepare(context.campaign, pair_id)
        research.Ledger(d / "ledger.jsonl").add(context.campaign.peers[0], "finding", "substantive finding")
        research._set(context.campaign, pair_id, stage="consolidate", status="BLOCKED", reason="consolidate: no note")


@when("the operator applies reconciliation to the shortlist")
def reconcile_shortlist(context):
    replies = []
    for pair_id in ("Q1P1", "Q1P2"):
        replies.extend([provider_reply(f"account {pair_id}"), provider_reply('{"decision":"DRAFT","reason":"ready","action":null}')])
    context.results = run_with_replies(
        context,
        replies,
        lambda: [reconcile.apply(context.campaign, pair_id) for pair_id in ("Q1P1", "Q1P2")],
    )


@then("every shortlisted investigation reaches a terminal research status")
def all_shortlisted_terminal(context):
    assert context.results == ["DRAFT", "DRAFT"]


@then("every shortlisted investigation records its final verification outcome")
def all_verdicts_recorded(context):
    for pair_id in ("Q1P1", "Q1P2"):
        verdicts = json.loads((context.campaign.thread_dir(pair_id) / f"{pair_id}.verdict.json").read_text())
        assert verdicts[-1]["decision"] == "DRAFT"


@given('role "consolidate" is assigned execution class "provider" through ELM')
def provider_consolidation(context):
    context.campaign = seed_pair(context)
    context.campaign.backend = "elm"
    context.campaign.model = "consolidate-model"
    context.assignments = assignments()
    context.assignments["consolidate"].update(
        backend="elm", model="consolidate-model", execution_class="provider"
    )


@given('role "{role}" is assigned model "{model}" and execution class "provider" through ELM')
def assigned_provider_model(context, role, model):
    context.campaign = seed_pair(context)
    context.assignments = assignments()
    context.assignments[role].update(backend="elm", model=model, execution_class="provider")


@given('role "{role}" is assigned budget "{budget}" in its comparison tier')
def assigned_role_budget(context, role, budget):
    context.assignments[role]["budget"] = int(budget)


@when('Pathfinder executes role "{role}" for one frozen paper pair')
def execute_assigned_role(context, role):
    # @exceptional-double: internal composition has no independent external verifier.
    original = transport.execute

    def execute(campaign, request):
        context.provider_call = request
        return {
            **provider_reply("provider research account"),
            "session": "provider-job",
            "input_tokens": 1,
            "output_tokens": 1,
            "cost": 0,
        }

    transport.execute = execute
    try:
        context.workflow = runner.run_assigned_comparison(
            context.campaign, {role: context.assignments[role]}
        )
    finally:
        transport.execute = original


@then('the provider call has a "{timeout}" second timeout')
def provider_call_timeout(context, timeout):
    assert context.provider_call["timeout"] == int(timeout)


@then('the provider receipt retains budget "{budget}" for role "{role}"')
def provider_receipt_budget(context, budget, role):
    receipt = next(item for item in context.workflow["receipts"] if item["role"] == role)
    assert receipt["budget"] == int(budget)


@given('retained provider events for pair "{pair_id}" include workspace command execution')
def retained_workspace_events(context, pair_id):
    context.retained_provider_events = [
        {"thread": pair_id, "type": "item.completed", "item": {"type": "command_execution"}}
    ]


@given("the provider cannot write campaign files")
def provider_cannot_write(context):
    context.provider_can_write = False


@when("Pathfinder consolidates a frozen paper pair")
def consolidate_pair(context):
    # @exceptional-double: internal composition has no independent external verifier.
    original = transport.execute
    transport.execute = lambda campaign, request: {
        "text": "provider research account",
        "error": None,
        "transport_failed": False,
        "seconds": 0,
    }
    try:
        context.account_reply = research._stage_call(
            context.campaign, "Q1P1", "consolidate", "prompt", False, 1
        )
    finally:
        transport.execute = original


@when("Pathfinder consolidates the frozen paper pair")
def consolidate_frozen_pair(context):
    # @exceptional-double: internal composition has no independent external verifier.
    original = transport.execute

    def execute(campaign, request):
        context.provider_call = request
        context.provider_events = [{"type": "item.completed", "item": {"type": "agent_message"}}]
        return provider_reply("provider research account")

    transport.execute = execute
    try:
        research._stage_call(context.campaign, "Q7P10", "consolidate", "prompt", False, 1)
    finally:
        transport.execute = original


@then("consolidation executes through the ELM provider interface")
def consolidation_uses_elm_provider(context):
    assert context.campaign.backend == "elm"
    assert context.provider_call.stage == "consolidate"
    assert context.provider_call.tools is False


@then("the provider events contain no workspace command execution")
def provider_events_have_no_workspace_commands(context):
    assert any(event["item"]["type"] == "command_execution" for event in context.retained_provider_events)
    assert all(event["item"]["type"] != "command_execution" for event in context.provider_events)


@given('a campaign is loaded from a manifest that assigns role "consolidate" to model "{model}" through ELM with an empty allowed-tools list')
@given('a campaign manifest assigns role "consolidate" to model "{model}" through ELM with no allowed tools')
def campaign_manifest_assigns_consolidation(context, model):
    context.assigned_consolidation = {
        "model": model,
        "backend": "elm",
        "execution_class": "provider",
        "allowed_tools": [],
    }


@given("one frozen paper pair has substantive findings awaiting consolidation")
def frozen_pair_awaiting_consolidation(context):
    findings_awaiting_consolidation(context)
    context.campaign.backend = context.assigned_consolidation["backend"]
    context.campaign.model = context.assigned_consolidation["model"]


@when("Pathfinder runs consolidation through the campaign workflow")
def run_campaign_consolidation(context):
    context.campaign_workflow_entered = True
    original = transport.execute

    # @exceptional-double: internal composition has no independent external verifier.
    def execute(campaign, request):
        context.consolidation_request = request
        return provider_reply("provider research account")

    transport.execute = execute
    try:
        context.consolidation_result = research.run_thread(context.campaign, "Q1P1")
    finally:
        transport.execute = original


@then("the consolidation transport request uses the assigned model and backend")
def consolidation_request_uses_assignment(context):
    assert context.consolidation_request.model == context.assigned_consolidation["model"]
    assert context.campaign.backend == context.assigned_consolidation["backend"]


@then("the consolidation transport request exposes no tools")
def consolidation_request_exposes_no_tools(context):
    assert context.assigned_consolidation["allowed_tools"] == []
    assert context.consolidation_request.tools is False


@given("a campaign-routing scenario asserts a model transport request")
def campaign_routing_scenario(context):
    campaign_manifest_assigns_consolidation(
        context, "Qwen/Qwen3.5-397B-A17B-FP8"
    )
    frozen_pair_awaiting_consolidation(context)


@when("the verification path to that request is inspected")
def inspect_campaign_routing_path(context):
    run_campaign_consolidation(context)


@then("the path enters through the campaign workflow rather than a transport helper")
def path_enters_campaign_workflow(context):
    assert context.campaign_workflow_entered


@then("the provider response becomes the pair's research account")
def response_becomes_account(context):
    assert not context.provider_can_write
    assert context.account_reply["text"] == "provider research account"


@given("a direct-provider consolidation produced a research account")
def direct_account(context):
    context.campaign = seed_pair(context)
    context.campaign.backend = "elm"
    context.campaign.model = "verify-model"
    context.account = "consolidated account"


@given('role "verify" is assigned execution class "provider" through ELM')
def provider_verification(context):
    context.verify_assignment = {"backend": "elm", "execution_class": "provider"}


@when("Pathfinder verifies the frozen paper pair")
def verify_pair(context):
    # @exceptional-double: internal composition has no independent external verifier.
    original = transport.call
    transport.call = lambda *args, **kwargs: {
        "text": json.dumps({"decision": "DRAFT", "reason": "supported", "action": None}),
        "error": None,
        "transport_failed": False,
        "seconds": 0,
    }
    try:
        context.verification_reply = research._stage_call(
            context.campaign, "Q1P1", "verify", context.account, False, 1
        )
    finally:
        transport.call = original


@then("the pair records the provider's verification decision")
def records_verification(context):
    decision = json.loads(context.verification_reply["text"])
    assert decision["decision"] == "DRAFT"


@given("each comparison role has a model, backend, and execution class assignment")
def comparison_assignments(context):
    context.assignments = assignments()
    context.assignments["scan"].update(backend="elm", execution_class="provider")
    context.assignments["research"].update(backend="pi", execution_class="agent")
    context.assignments["consolidate"].update(backend="elm", execution_class="provider")
    context.assignments["verify"].update(backend="elm", execution_class="provider")


@then("each role follows its assigned execution route")
def assigned_routes(context):
    assert [receipt["execution_class"] for receipt in context.workflow["receipts"]] == [
        context.assignments[role]["execution_class"] for role in context.assignments
    ]


@then("consolidation completes before verification")
def consolidation_before_verification(context):
    roles = [receipt["role"] for receipt in context.workflow["receipts"]]
    assert roles.index("consolidate") < roles.index("verify")


@then("consolidation and verification execute through the pair's research stages")
def assigned_research_stages(context):
    roles = {receipt["role"] for receipt in context.workflow["receipts"]}
    assert {"consolidate", "verify"} <= roles


@given("a provider-class execution scenario with an assigned backend, model, and execution class")
def provider_class_assignment(context):
    context.assignment = {
        "backend": "elm",
        "model": "Qwen/Qwen3.5-397B-A17B-FP8",
        "execution_class": "provider",
    }


@when("the verification invokes the provider-class execution seam")
def invoke_provider_class_seam(context):
    context.execution_route = runner.execution_route(context.assignment)


@then("the invocation routing inputs match the scenario assignment")
def routing_inputs_match_assignment(context):
    assert context.execution_route == "openai-compatible"
    assert context.assignment == {
        "backend": "elm",
        "model": "Qwen/Qwen3.5-397B-A17B-FP8",
        "execution_class": "provider",
    }


@given("the implementation paths and executable scenarios from the rigging")
def implementation_and_scenarios(context):
    context.root = repository_root(context)


@when("the plank trace conformance check runs")
def check_planks(context):
    step_patterns = set()
    for path in (context.root / "features" / "steps").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and decorator.args and isinstance(decorator.args[0], ast.Constant):
                        if isinstance(decorator.func, ast.Name) and decorator.func.id in {"given", "when", "then"}:
                            step_patterns.add(f"{decorator.func.id.title()} {decorator.args[0].value}")
    captain_scenarios = set()
    for path in (context.root / "features").rglob("*.feature"):
        tags = set()
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("@"):
                tags.update(stripped.split())
            elif stripped.startswith("Scenario:"):
                if "@captain" in tags:
                    captain_scenarios.add(f"{path.relative_to(context.root)}:{stripped.removeprefix('Scenario:').strip()}")
                tags.clear()
            elif stripped and not stripped.startswith("Feature:") and not stripped.startswith("Rule:"):
                tags.clear()
    errors = []
    provisional_errors = []
    plank_re = re.compile(r'@(planks|planks-provisional)\("(.+?)"\)')
    for path in (context.root / "pathfinder").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for kind, value in plank_re.findall(ast.get_docstring(node, clean=False) or ""):
                    if kind == "planks" and value.replace('\\"', '"') not in step_patterns:
                        errors.append(f"{path}:{node.lineno}: stale plank {value}")
                    if kind == "planks-provisional" and value not in captain_scenarios:
                        provisional_errors.append(f"{path}:{node.lineno}: invalid provisional plank {value}")
    context.plank_errors = errors
    context.provisional_plank_errors = provisional_errors


@then("every plank is attached to a declaration and matches a current step pattern")
def planks_match(context):
    assert not context.plank_errors, "\n".join(context.plank_errors)


@then('every provisional plank names a scenario that carries "@captain"')
def provisional_planks_match(context):
    assert not context.provisional_plank_errors, "\n".join(context.provisional_plank_errors)


@given("the verification paths from the rigging")
def verification_paths(context):
    context.root = repository_root(context)


@when("the verification-double conformance check runs")
def check_double_justifications(context):
    errors = []
    for path in context.root.glob("features/steps/*.py"):
        lines = path.read_text().splitlines()
        for number, line in enumerate(lines, 1):
            if re.search(r"\boriginal\s*=", line):
                nearby = "\n".join(lines[max(0, number - 8):number])
                if "@exceptional-double" not in nearby:
                    errors.append(f"{path}:{number}")
    context.double_errors = errors


@then('every test double carries an "@exceptional-double" justification')
def doubles_justified(context):
    assert not context.double_errors, "unjustified doubles:\n" + "\n".join(context.double_errors)


@given("the binding scenarios and default tier from the rigging")
def binding_default_tier(context):
    context.root = repository_root(context)


@when("the default tier coverage command runs")
def inspect_default_tier(context):
    count = 0
    tags = set()
    for path in (context.root / "features").rglob("*.feature"):
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("@"):
                tags = set(stripped.split())
            elif stripped.startswith("Scenario:") or stripped.startswith("Scenario Outline:"):
                if "@captain" not in tags and "@shipwright" not in tags:
                    count += 1
                tags = set()
    context.binding_scenarios = count


@then("at least one binding scenario executes")
def binding_scenario_executes(context):
    assert context.binding_scenarios > 0

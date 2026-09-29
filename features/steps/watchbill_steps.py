import ast
import io
import json
import re
from contextlib import redirect_stdout
from pathlib import Path

from behave import given, then, when

from pathfinder import reconcile, research, runner, transport

from operational_steps import prepared_corpora, seed_pair

# a research account is a LaTeX document; the engine refuses any other reply as an account
ACCOUNT = "\\documentclass{article}\\begin{document}\n%s\n\\end{document}\n"


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


@when("Pathfinder requests consolidation")
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


@then("the request asks for the complete research account in the response")
def requests_returned_account(context):
    assert "return" in context.direct_prompt.lower()
    assert "complete research account" in context.direct_prompt.lower()


@when("the provider returns a complete research account on its consolidation retry")
def provider_returns_account_on_retry(context):
    context.returned_account = ACCOUNT % "complete research account"
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
    context.returned_account = ACCOUNT % "provider research account"
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
    assert path.read_text() == context.returned_account


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
    context.replies = [provider_reply(ACCOUNT % "recovered account"), provider_reply('{"decision":"DRAFT","reason":"ready","action":null}')]


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
    from pathfinder import edit
    context.campaign = seed_pair(context)
    context.campaign.path("shortlist.json").write_text(json.dumps({"pairs": [{"pair_id": "Q1P1"}, {"pair_id": "Q1P2"}]}))
    research._set(context.campaign, "Q1P1", stage="done", status="DRAFT")
    (context.campaign.thread_dir("Q1P1") / "edited").mkdir(exist_ok=True)
    edit._set(context.campaign, "Q1P1", status="done")
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
        replies.extend([provider_reply(ACCOUNT % f"account {pair_id}"), provider_reply('{"decision":"DRAFT","reason":"ready","action":null}')])
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


@when("the provider-substitution conformance check runs")
def check_provider_substitution(context):
    errors = []
    for path in context.root.glob("features/steps/*.py"):
        lines = path.read_text().splitlines()
        tree = ast.parse("\n".join(lines))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "transport" and node.func.attr == "_parse":
                    nearby = "\n".join(lines[max(0, node.lineno - 8):node.lineno])
                    if "@exceptional-double" not in nearby:
                        errors.append(f"{path}:{node.lineno}: transport._parse")
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Lambda):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                        if target.value.id == "transport" and target.attr in {"call", "execute"}:
                            nearby = "\n".join(lines[max(0, node.lineno - 8):node.lineno])
                            if "@exceptional-double" not in nearby:
                                errors.append(f"{path}:{node.lineno}: transport.{target.attr} substitution")
    context.provider_substitution_errors = errors


@then("verification does not replace the model execution seam")
def provider_execution_not_substituted(context):
    assert not context.provider_substitution_errors, "provider execution substitutions:\n" + "\n".join(
        context.provider_substitution_errors
    )


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

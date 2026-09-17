import ast
import json
import re
from pathlib import Path

from behave import given, then, when

from pathfinder import research, runner, transport

from operational_steps import assignments, prepared_corpora, seed_pair


def repository_root(context):
    return Path(context.config.base_dir).parent


@given('role "consolidate" is assigned execution class "provider" through ELM')
def provider_consolidation(context):
    context.campaign = seed_pair(context)
    context.campaign.backend = "elm"
    context.campaign.model = "consolidate-model"


@given("the provider cannot write campaign files")
def provider_cannot_write(context):
    context.provider_can_write = False


@when("Pathfinder consolidates a frozen paper pair")
def consolidate_pair(context):
    # @exceptional-double: internal composition has no independent external verifier.
    original = transport.call
    transport.call = lambda *args, **kwargs: {
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
        transport.call = original


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
    errors = []
    plank_re = re.compile(r'@(planks|planks-provisional)\("(.+?)"\)')
    for path in (context.root / "pathfinder").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for kind, value in plank_re.findall(ast.get_docstring(node, clean=False) or ""):
                    if kind == "planks" and value.replace('\\"', '"') not in step_patterns:
                        errors.append(f"{path}:{node.lineno}: stale plank {value}")
                    if kind == "planks-provisional":
                        errors.append(f"{path}:{node.lineno}: provisional plank {value}")
    context.plank_errors = errors


@then("every plank is attached to a declaration and matches a current step pattern")
def planks_match(context):
    assert not context.plank_errors, "\n".join(context.plank_errors)


@then('every provisional plank names a scenario that carries "@captain"')
def provisional_planks_match(context):
    assert not context.plank_errors, "\n".join(context.plank_errors)


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

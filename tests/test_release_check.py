"""The release checker itself, on synthetic JUnit reports."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("release_check", ROOT / "scripts/release_check.py")
rc = importlib.util.module_from_spec(spec); spec.loader.exec_module(rc)

DEPLOYMENTS = {
    "statarb": {"status": "supported", "contract": "tests/test_deployments.py::test_statarb_contract", "revision": "abc", "notes": "n"},
    "pilot": {"status": "supported", "contract": "tests/test_coordinator.py", "revision": "candidate", "notes": "n"},
    "fork": {"status": "not-yet-supported", "contract": "", "revision": "def", "notes": "n"},
}
CLEAN = ("c0ffee", True)


def junit(tmp_path, cases):
    body = "".join(f'<testcase classname="{cls}" name="{name}">{extra}</testcase>' for cls, name, extra in cases)
    (tmp_path / "j.xml").write_text(f'<testsuites><testsuite name="pytest">{body}</testsuite></testsuites>')
    return rc.node_ids(tmp_path / "j.xml", ROOT)


def test_all_contracts_passing(tmp_path):
    nodes = junit(tmp_path, [("tests.test_deployments", "test_statarb_contract", ""),
                             ("tests.test_coordinator", "test_a", ""), ("tests.test_coordinator", "test_b", "")])
    problems, results = rc.evaluate(nodes, 0, DEPLOYMENTS, CLEAN, CLEAN)
    assert problems == [] and results == {"statarb": "passed", "pilot": "passed", "fork": "not yet supported"}


def test_a_same_named_test_elsewhere_does_not_satisfy_a_contract(tmp_path):
    nodes = junit(tmp_path, [("tests.test_stub_flow", "test_statarb_contract", ""), ("tests.test_coordinator", "test_a", "")])
    problems, results = rc.evaluate(nodes, 0, DEPLOYMENTS, CLEAN, CLEAN)
    assert results["statarb"] == "missing" and any("statarb" in p for p in problems)


def test_a_skipped_or_failed_contract_fails_the_release(tmp_path):
    nodes = junit(tmp_path, [("tests.test_deployments", "test_statarb_contract", '<skipped message="absent"/>'),
                             ("tests.test_coordinator", "test_a", ""), ("tests.test_coordinator", "test_b", '<failure message="x"/>')])
    problems, results = rc.evaluate(nodes, 1, DEPLOYMENTS, CLEAN, CLEAN)
    assert results == {"statarb": "skipped", "pilot": "failed", "fork": "not yet supported"} and problems


def test_parameterized_cases_and_classes_resolve_to_exact_nodes(tmp_path):
    nodes = junit(tmp_path, [("tests.test_deployments", "test_statarb_contract[a]", ""),
                             ("tests.test_deployments", "test_statarb_contract[b]", '<failure message="x"/>'),
                             ("tests.test_coordinator.TestGroup", "test_c", "")])
    assert "tests/test_coordinator.py::TestGroup::test_c" in nodes
    assert rc.contract_result("tests/test_deployments.py::test_statarb_contract", nodes) == "failed"
    assert rc.contract_result("tests/test_deployments.py::test_statarb", nodes) == "missing"


def test_a_candidate_changed_or_dirty_during_the_run_fails(tmp_path):
    nodes = junit(tmp_path, [("tests.test_deployments", "test_statarb_contract", ""), ("tests.test_coordinator", "test_a", "")])
    assert rc.evaluate(nodes, 0, DEPLOYMENTS, CLEAN, ("beef", True))[0]
    assert rc.evaluate(nodes, 0, DEPLOYMENTS, CLEAN, ("c0ffee", False))[0]
    assert rc.evaluate(nodes, 0, DEPLOYMENTS, ("c0ffee", False), ("c0ffee", False))[0]


def test_notes_state_actual_results(tmp_path):
    text = rc.notes(DEPLOYMENTS, {"statarb": "skipped", "pilot": "passed", "fork": "not yet supported"})
    assert "statarb (abc): skipped" in text and "pilot (candidate): supported, contract passed" in text


def test_a_failing_behaviour_suite_fails_the_release(tmp_path):
    nodes = junit(tmp_path, [("tests.test_deployments", "test_statarb_contract", ""), ("tests.test_coordinator", "test_a", "")])
    problems, _ = rc.evaluate(nodes, 0, DEPLOYMENTS, CLEAN, CLEAN, behave_returncode=1)
    assert any("behave" in p for p in problems)


def test_the_behaviour_suite_runs_with_the_rigging_tags():
    assert rc.broad_tags() == "not @sandbox and not @captain and not @shipwright and not @pce"

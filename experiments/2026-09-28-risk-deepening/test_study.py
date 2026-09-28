import importlib.util
import json
import random
from itertools import product
from pathlib import Path

spec = importlib.util.spec_from_file_location("risk_deepening", Path(__file__).with_name("study.py"))
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def test_exact_examples():
    assert study.risk(0.3) == 1.2
    assert study.risk(0.7) == 2
    assert abs(study.reward(0.2, 0.6) - 0.2) < 1e-12
    assert study.reward(0.4, 0.2) is None
    assert study.decide(1.2, 0.4, 0)[0] == "deploy"
    assert study.decide(1.4, 0.8, 0)[0] == "refute"
    assert study.decide(1.4, 0.6, 0.01)[0] == "abstain"
    assert study.decide(1.8, 0.0, 0)[0] == "budget_uncertain"


def test_confidence_corners():
    for c0, c1 in product((0.0, 0.4, 1.2, 1.4, 2.0), repeat=2):
        oracle = study.reward(c0 - 1, 1 - c1)
        for e in (0.01, 0.05, 0.2):
            for x, y in product((-e, e), repeat=2):
                for padding in (e, 2*e):
                    status, d = study.decide(c0+x, c1+y, padding)
                    if status == "deploy":
                        assert study.obeys(c0, c1, d)
                        assert abs(d) <= study.CAP + 1e-12
                        assert abs(d) <= abs(oracle) + 2*padding + 1e-12
                    elif status == "refute":
                        assert oracle is None


def test_bounds_and_access_accounting():
    assert study.parameters(1000, "uniform")[0] == 4000
    assert study.parameters(1000, "known_safe")[0] == 2000
    assert study.expected_bound(1.2, 0.4, 250, "uniform", 1e-6) is None
    assert study.expected_bound(1.2, 0.4, 64000, "uniform", 1e-6) < 1
    assert study.expected_bound(1.4, 0.6, 256000, "known_safe", 1e-6) is None


def test_all_coverage_deployment_premise():
    for mode in ("uniform", "known_safe"):
        for p in study.SCENARIOS.values():
            c0, c1 = map(study.risk, p)
            for m in study.BATCHES:
                bound = study.expected_bound(c0, c1, m, mode, 1e-6)
                if bound is None:
                    continue
                _, e, padding = study.parameters(m, mode)
                for x, y in product((-e, e), repeat=2):
                    assert study.decide(c0+x, c1+y, padding)[0] == "deploy"


def test_saved_results_reproduce():
    saved = json.loads(Path(__file__).with_name("results.json").read_text())
    assert json.loads(json.dumps(study.run())) == saved
    assert sum(row["false_definitive"] for row in saved["rows"]) == 6
    assert sum(row["coverage_failures"] for row in saved["rows"]) == 106


def test_simulated_errors_are_outside_coverage():
    rng = random.Random(20260928)
    checked = 0
    for probabilities in study.SCENARIOS.values():
        true = tuple(map(study.risk, probabilities))
        oracle = study.reward(true[0]-1, 1-true[1])
        for m in study.BATCHES:
            for _ in range(2000):
                empirical = tuple(study.risk(rng.binomialvariate(m, p)/m)
                                  for p in probabilities)
                for mode in ("uniform", "known_safe"):
                    _, e, padding = study.parameters(m, mode)
                    status, d = study.decide(*empirical, padding)
                    covered = max(abs(a-b) for a, b in zip(empirical, true)) <= e
                    if covered and status == "deploy":
                        assert study.obeys(*true, d)
                    if covered and status == "refute":
                        assert oracle is None
                    checked += 1
    assert checked == 120000

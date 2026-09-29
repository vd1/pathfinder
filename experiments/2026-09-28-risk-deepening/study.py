"""Fixed-batch synthetic deepening; standard library only, no model calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import random

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / "2026-09-28-recursive-extension/reviewed/recursive-Q1P2-v2/paper.tex"
DELTA, CAP, OPERATING, FALLBACK, SURCHARGE = 0.05, 0.6, 0.2, 1.0, 2.0
SCENARIOS = {"free": (0.1, 0.1), "paid": (0.3, 0.1),
             "near_boundary": (0.35, 0.149), "boundary": (0.35, 0.15),
             "infeasible": (0.35, 0.2)}
BATCHES = (250, 1000, 4000, 16000, 64000, 256000)
PRICES = (1e-6, 1e-5)


def risk(p):
    return min(4 * p, 2.0)


def reward(lower, upper):
    """Return minimum-cap difference r(A)-r(B), or None if infeasible."""
    if lower > upper + 1e-12:
        return None
    return lower if lower > 0 else upper if upper < 0 else 0.0


def decide(c0, c1, padding):
    difference = reward(c0 - 1 + padding, 1 - c1 - padding)
    if difference is not None:
        if abs(difference) <= CAP + 1e-12:
            return "deploy", difference
        return "budget_uncertain", None
    if c0 + c1 - 2 * padding > 2 + 1e-12:
        return "refute", None
    return "abstain", None


def obeys(c0, c1, difference):
    return c0 - 1 - 1e-12 <= difference <= 1 - c1 + 1e-12


def parameters(m, mode):
    cells = 4 if mode == "uniform" else 2
    e = 4 * math.sqrt(math.log(2 * cells / DELTA) / (2 * m))
    padding = 2 * e if mode == "uniform" else e
    return cells * m, e, padding


def expected_bound(c0, c1, m, mode, price):
    """Sufficient all-coverage deployment bound, not fitted to simulation."""
    oracle = reward(c0 - 1, 1 - c1)
    if oracle is None:
        return None
    draws, e, padding = parameters(m, mode)
    # Unknown risky risk error <= e; uniform safe risk error also <= e.
    inflation = 4 * e if mode == "uniform" else 2 * e
    gamma = (2 - c0 - c1) / 2
    if inflation >= gamma or abs(oracle) + inflation > CAP:
        return None
    good = OPERATING + (abs(oracle) + inflation) / 2
    worst = OPERATING + CAP / 2 + SURCHARGE
    return price * draws + (1 - DELTA) * good + DELTA * worst


def run(trials=2000, seed=20260928):
    rng = random.Random(seed)
    rows = []
    for name, probabilities in SCENARIOS.items():
        true = tuple(map(risk, probabilities))
        oracle = reward(true[0] - 1, 1 - true[1])
        for m in BATCHES:
            stats = {mode: {"counts": {key: 0 for key in
                     ("deploy", "refute", "abstain", "budget_uncertain")},
                     "false_definitive": 0, "coverage_failures": 0,
                     "cost_sum": 0.0, "cost_square_sum": 0.0}
                     for mode in ("uniform", "known_safe")}
            for _ in range(trials):
                empirical = tuple(risk(rng.binomialvariate(m, p) / m)
                                  for p in probabilities)
                for mode, record in stats.items():
                    draws, e, padding = parameters(m, mode)
                    status, d = decide(*empirical, padding)
                    record["counts"][status] += 1
                    record["coverage_failures"] += int(
                        max(abs(a-b) for a, b in zip(empirical, true)) > e)
                    wrong = (status == "deploy" and not obeys(*true, d)) or (
                        status == "refute" and oracle is not None)
                    record["false_definitive"] += int(wrong)
                    cost = (OPERATING + abs(d)/2 + SURCHARGE * int(wrong)
                            if status == "deploy" else FALLBACK)
                    record["cost_sum"] += cost
                    record["cost_square_sum"] += cost * cost
            for mode, record in stats.items():
                draws, e, padding = parameters(m, mode)
                mean = record.pop("cost_sum") / trials
                second = record.pop("cost_square_sum") / trials
                se = math.sqrt(max(0, second-mean*mean) / (trials-1))
                rows.append({"scenario": name, "p": probabilities, "m": m,
                    "mode": mode, "draws": draws, "radius": e,
                    "padding": padding, "oracle_cap": None if oracle is None else abs(oracle),
                    "mean_downstream_cost": mean, "mc_standard_error": se,
                    "prices": [{"per_draw": price, "mean_total": price*draws+mean,
                                "sufficient_expected_bound": expected_bound(*true, m, mode, price)}
                               for price in PRICES], **record})
    return {"seed": seed, "trials_per_cell": trials, "python": platform.python_version(),
            "parent_sha256": hashlib.sha256(PARENT.read_bytes()).hexdigest(),
            "protocol_sha256": hashlib.sha256((ROOT / "PROTOCOL.md").read_bytes()).hexdigest(),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "delta_per_trial": DELTA, "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(run(), indent=2) + "\n"
    if args.output:
        with args.output.open("x") as handle:
            handle.write(result)
    else:
        print(result, end="")

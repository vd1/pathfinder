"""Exact finite-distribution audit of repeated comparison evidence."""

from fractions import Fraction as F
from math import comb
import json
from pathlib import Path


def binomial(k, p):
    return [F(comb(k, j)) * p**j * (1 - p)**(k - j) for j in range(k + 1)]


def tv(p, q):
    return sum(abs(x - y) for x, y in zip(p, q)) / 2


rows = []
for k in [1, 2, 4, 8, 16, 32, 64]:
    hi, lo = binomial(k, F(9, 10)), binomial(k, F(1, 10))
    desired = [F(3, 5) * h + F(2, 5) * l for h, l in zip(hi, lo)]
    deviation = [F(2, 5) * h + F(3, 5) * l for h, l in zip(hi, lo)]
    assert sum(desired) == sum(deviation) == 1
    shared_tv = tv(desired, deviation)
    assert shared_tv == F(1, 5) * tv(hi, lo)
    assert shared_tv <= F(1, 5)
    # The likelihood-ratio event attains the variational upper bound.
    event_gap = sum(p - q for p, q in zip(desired, deviation) if p > q)
    assert event_gap == shared_tv
    # Reacquiring an independent image for every query changes the experiment.
    fresh_tv = tv(binomial(k, F(29, 50)), binomial(k, F(21, 50)))
    # Paying empirical win frequency has the same gap for every query count.
    score_gap = sum(F(j, k) * (p - q) for j, (p, q) in enumerate(zip(desired, deviation)))
    assert score_gap == F(4, 25)
    rows.append({"queries": k, "shared_image_tv": float(shared_tv),
                 "fresh_image_tv": float(fresh_tv), "score_payment_gap": float(score_gap),
                 "shared_min_budget_gain_0.3": float(F(3, 10) / shared_tv),
                 "fresh_min_budget_gain_0.3": float(F(3, 10) / fresh_tv)})

out = {"model": "Exact binary shared-evidence calculation; no MARS-Bench data",
       "checks": "Rational arithmetic; TV identity, budget ceiling, optimal event, score gap",
       "rows": rows}
Path(__file__).with_name("information_results.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))

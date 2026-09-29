"""Reproduce selected recursive-science witnesses; no campaign files are changed.

Run with: uv run --no-sync python notes/check_recursive_claims.py
These checks are not a proof of the general theorems or simulator equivalence.
"""

from fractions import Fraction as F
from itertools import combinations
from math import atanh, comb, isclose, sqrt, tanh


def symmetric(values, degree):
    result = F(0)
    for subset in combinations(values, degree):
        product = F(1)
        for value in subset:
            product *= value
        result += product
    return result


def check_rankings():
    transformed = sum(2 * atanh(0.5 * tanh(d / 2)) for d in (4, -1.5, -1.5))
    assert transformed < 0 and sum((4, -1.5, -1.5)) == 1
    print(f"Path: intended endpoint difference 1, fitted {transformed:.12f}")

    # Six-cycle closure: S1*b^4 + S3*b^2 + S5 = 0.
    w = tuple(F(x, 100) for x in (-65, 60, -52, -23, 62, 16))
    a, b, c = (symmetric(w, degree) for degree in (1, 3, 5))
    discriminant = b * b - 4 * a * c
    roots = sorted(sqrt(float((-b + sign * sqrt(float(discriminant))) / (2 * a)))
                   for sign in (-1, 1))
    scores = []
    for rate in roots:
        assert max(map(abs, w)) < rate < 1
        edges = [2 * atanh(float(value) / rate) for value in w]
        assert abs(sum(edges)) < 1e-10
        vector = [0.0]
        for edge in edges[:-1]:
            vector.append(vector[-1] - edge)
        scores.append(vector)
    flips = [(i + 1, j + 1) for i, j in combinations(range(6), 2)
             if (scores[0][i] - scores[0][j]) * (scores[1][i] - scores[1][j]) < 0]
    assert flips
    print(f"Six-cycle: rates {roots}; reversed vertex pairs {flips}")

    # A nondegenerate triangle recovers the common scale.
    rate = 0.6
    a, b, c = (rate * tanh(d / 2) for d in (0.8, 1.1, 1.9))
    assert isclose(a * b * c / (a + b - c), rate**2, abs_tol=1e-12)


def check_cvar():
    # h=1. K is the number of high losses in the batch. Fractional tail
    # weighting handles odd m as well as even m.
    for m in range(1, 65):
        expected = sum((F(comb(m, k), 2**m) * min(F(2), F(4 * k, m))
                        for k in range(m + 1)), F(0))
        safe = F(2) - F(1, 2**m)
        assert expected <= 2 * (1 - F(1, 2**m)) < safe < 2
        assert 2 * (safe - expected) >= F(2, 2**m)
    assert (F(1, 2) * F(2, 5) + F(1, 2) * 3) == F(17, 10)
    ex_ante = (F(1, 2000) * 100 + (F(1, 4) - F(1, 2000)) * 3) / F(1, 4)
    assert ex_ante == F(1597, 500) > 3
    print("CVaR: exact batch inequalities pass for m=1..64; ex-ante reversal 3.194 > 3")


def check_auctions():
    crossing = F(3, 2)
    waiting = (F(5, 2), F(1))
    local = max(crossing, sum(waiting) / 2)
    informed = sum(max(crossing, value) for value in waiting) / 2
    assert informed - local == F(1, 4)
    r = 1 - F(7, 8)**6
    regret = min(2 * r - F(3, 4), F(1, 2) * (1 - r)) / 2
    assert 2 * r > F(110, 100) and r / 2 < F(28, 100)
    assert regret > F(11, 100)
    print(f"Auctions: conditional information value 0.25; invitation bound {float(regret):.12f}")


if __name__ == "__main__":
    check_rankings()
    check_cvar()
    check_auctions()
    print("All selected witness checks passed.")

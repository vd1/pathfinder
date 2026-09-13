"""Exact checks for the research note; run with uv run --no-project."""

from fractions import Fraction as F
from itertools import product


def masked_return(gamma, mask, potential):
    return sum(
        gamma**t * m * (gamma * potential[t + 1] - potential[t])
        for t, m in enumerate(mask)
    )


def boundary_return(gamma, mask, potential):
    horizon = len(mask)
    return (
        -mask[0] * potential[0]
        + sum(
            gamma**t * (mask[t - 1] - mask[t]) * potential[t]
            for t in range(1, horizon)
        )
        + gamma**horizon * mask[-1] * potential[-1]
    )


checks = 0
for gamma in (F(1), F(99, 100), F(1, 2)):
    for mask in product((0, 1), repeat=4):
        for potential in product((F(0), F(1, 2), F(1)), repeat=5):
            actual = masked_return(gamma, mask, potential)
            assert actual == boundary_return(gamma, mask, potential)
            checks += 1
            if potential[-1] == 0:
                settlement = sum(
                    gamma**t * (mask[t] - mask[t - 1]) * potential[t]
                    for t in range(1, 4)
                )
                assert actual + settlement == -mask[0] * potential[0]

gamma = F(99, 100)
returns = []
for p in (F(1, 2), F(1, 10)):
    potential = (F(1, 2), F(0), p, F(0))
    masked = masked_return(gamma, (1, 0, 1), potential)
    complete = masked_return(gamma, (1, 1, 1), potential)
    repaired = masked + gamma**2 * p
    assert complete == repaired == -F(1, 2)
    returns.append(masked)
    print(f"p={p}: masked={float(masked):.5f}, complete={float(complete):.5f}")

assert returns[1] - returns[0] == F(9801, 25000)
print(f"Concealment gain: {float(returns[1] - returns[0]):.5f}")
print(f"Exact boundary identities checked: {checks}")

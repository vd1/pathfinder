"""Exact arithmetic checks of the research note's illustrative mechanisms."""

from fractions import Fraction as F


def score(row, event):
    return 2 * row[event] - sum(x * x for x in row)


def mean(row, values):
    return sum(p * v for p, v in zip(row, values))


original_h = (F(3, 4), F(1, 4))
original_l = (F(1, 4), F(3, 4))
survival = (F(1, 10), F(1))
full_rows = []
selected_rows = []
for row in (original_h, original_l):
    observed = tuple(p * s for p, s in zip(row, survival))
    mass = sum(observed)
    selected_rows.append(tuple(p / mass for p in observed))
    full_rows.append(observed + (1 - mass,))

stale_difference = tuple(score(original_h, y) - score(original_l, y) for y in range(2))
assert mean(selected_rows[0], stale_difference) == -F(7, 13)
assert sum((h - l) ** 2 for h, l in zip(*full_rows)) == F(91, 200)
assert sum((h - l) ** 2 for h, l in zip(*selected_rows)) == 2 * F(80, 403) ** 2

for epsilon in (F(1), F(1, 2), F(1, 10), F(1, 100)):
    h = (F(1, 2), F(2, 5) * epsilon, F(1, 10) * epsilon, (1 - epsilon) / 2)
    l = (F(1, 2), F(1, 10) * epsilon, F(2, 5) * epsilon, (1 - epsilon) / 2)
    tv = sum(abs(x - y) for x, y in zip(h, l)) / 2
    assert tv == F(3, 10) * epsilon
    assert sum((x - y) ** 2 for x, y in zip(h, l)) == F(9, 50) * epsilon ** 2
    temptation = F(1)
    cap = temptation / tv
    difference = (0, cap, -cap, 0)
    assert mean(h, difference) == temptation
    assert mean(l, difference) == -temptation
    assert h[1] * cap == F(4, 3) * temptation
    # Every vertex of the difference-payment box obeys the TV upper bound.
    for bits in range(16):
        vertex = tuple(cap if bits & (1 << i) else -cap for i in range(4))
        assert mean(tuple(x - y for x, y in zip(h, l)), vertex) <= 2 * cap * tv

print("Exact checks passed: selection reversal, full/selected separation, TV bound, attaining contract, expected payment.")

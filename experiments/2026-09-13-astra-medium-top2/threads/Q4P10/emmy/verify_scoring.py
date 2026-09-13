"""Exact checks of the finite examples in survival_scoring.md."""

from fractions import Fraction as F


def score(row, outcome):
    return 2 * row[outcome] - sum(x * x for x in row)


def expectation(law, values):
    return sum(p * v for p, v in zip(law, values, strict=True))


def score_gap(law, true_row, other_row):
    return expectation(
        law,
        [score(true_row, j) - score(other_row, j) for j in range(len(law))],
    )


def observe(row, survival):
    observed = tuple(p * s for p, s in zip(row, survival, strict=True))
    return observed + (1 - sum(observed),)


def tv(first, second):
    return sum(abs(a - b) for a, b in zip(first, second, strict=True)) / 2


p_h, p_l = (F(1, 4), F(3, 4)), (F(3, 4), F(1, 4))
survival = (F(1), F(1, 10))
q_h, q_l = observe(p_h, survival), observe(p_l, survival)
availability_h, availability_l = 1 - q_h[-1], 1 - q_l[-1]
selected_h = tuple(x / availability_h for x in q_h[:-1])
selected_l = tuple(x / availability_l for x in q_l[:-1])
assert selected_h[1] == F(3, 13)
assert selected_l[1] == F(1, 31)
assert score_gap(p_h, p_h, p_l) == F(1, 2)
assert score_gap(selected_h, p_h, p_l) == -F(7, 13)
assert availability_h * score_gap(selected_h, p_h, p_l) == -F(7, 40)
assert score_gap(selected_h, selected_h, selected_l) == 2 * F(80, 403) ** 2
assert score_gap(q_h, q_h, q_l) == F(91, 200)
assert tv(q_h, q_l) == tv(p_h, p_l)
print("Selection reversal, corrected scores, and informative nonresponse: PASS")

p_h, p_l = (F(1, 2), F(2, 5), F(1, 10)), (F(1, 2), F(1, 10), F(2, 5))
for epsilon in (F(1), F(1, 2), F(1, 10), F(1, 100), F(0)):
    q_h = observe(p_h, (F(1), epsilon, epsilon))
    q_l = observe(p_l, (F(1), epsilon, epsilon))
    separation = tv(q_h, q_l)
    assert separation == F(3, 10) * epsilon
    assert score_gap(q_h, q_h, q_l) == F(9, 50) * epsilon**2
    if not epsilon:
        assert q_h == q_l
        continue
    temptation = F(1)
    bonus = temptation / separation
    rewards_h, rewards_l = (F(0), bonus, F(0), F(0)), (F(0), F(0), bonus, F(0))
    diff = tuple(a - b for a, b in zip(rewards_h, rewards_l, strict=True))
    assert expectation(q_h, diff) == temptation
    assert expectation(q_l, diff) == -temptation
    assert expectation(q_h, rewards_h) == F(4, 3) * temptation
    assert expectation(q_l, rewards_l) == F(4, 3) * temptation
    scale = temptation / (F(9, 50) * epsilon**2)
    baseline = tuple(min(score(q_h, j), score(q_l, j)) for j in range(4))
    normalized_h = tuple(scale * (score(q_h, j) - baseline[j]) for j in range(4))
    normalized_l = tuple(scale * (score(q_l, j) - baseline[j]) for j in range(4))
    assert normalized_h == rewards_h
    assert normalized_l == rewards_l
    print(f"availability={epsilon}, total_variation={separation}, minimum_peak_bonus={bonus}: PASS")

print("Exact peak-payment boundary and constant expected payout: PASS")
print("Normalized quadratic score attains the optimal peak-payment boundary: PASS")

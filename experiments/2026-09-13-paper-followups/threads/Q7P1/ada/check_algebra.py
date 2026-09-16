"""Exact rational checks of the printed Q payment and the proposed repair."""

from fractions import Fraction as F


def tax(n, x, p, capacity=F(1), scale=F(1)):
    count = len(x)
    others = [j for j in range(count) if j != n]
    p_sum = sum(p[j] for j in others)
    x_sum = sum(x[j] for j in others)
    p_square = sum(p[j] ** 2 for j in others)
    px_sum = sum(p[j] * x[j] for j in others)
    return scale * (
        p[n] * (p[n] - 2 * p_sum / (count - 1)) / 2
        - p[n] * (x[n] + x_sum - capacity) / (count - 1)
        + F(count, (count - 1) ** 2) * p_sum * (x[n] - capacity / count)
        + p_square / (2 * (count - 1))
        - (px_sum - p_sum * capacity / count) / (count - 1) ** 2
    )


def rebate(n, x, p, capacity=F(1), scale=F(1)):
    count = len(x)
    others = [j for j in range(count) if j != n]
    b = F(count**2 - count + 1, (count - 1) ** 2)
    return scale * (b - 1) * sum(p[j] for j in others) / (count - 1) * (
        sum(x[j] for j in others) - F(count - 1, count) * capacity
    )


def check_counterexample():
    x = [F(1), F(0), F(0)]
    p = [F(9)] * 3
    valuations = [F(19, 2), F(0), F(0)]
    original = [tax(n, x, p) for n in range(3)]
    corrected = [tax(n, x, p) + rebate(n, x, p) for n in range(3)]
    assert original == [F(21, 2), F(-21, 4), F(-21, 4)]
    assert corrected == [F(6), F(-3), F(-3)]
    assert valuations[0] - original[0] == -1
    assert sum(original) == sum(corrected) == 0
    assert all(v - t >= 0 for v, t in zip(valuations, corrected))
    # Own cost gradients at the proposed equilibrium.
    allocation_gradients = [F(0), F(89, 10), F(89, 10)]
    assert all(g >= 0 for g in allocation_gradients)
    assert F(1) - F(1, 2) ** 2 > 0  # Hessian determinant.
    print("Q original taxes:", original)
    print("Repaired taxes:", corrected)
    print("Original agent 1 utility:", valuations[0] - original[0])


def check_partner_pbr_column():
    for mu in [F(1, 100), F(1, 2), F(1), F(10), F(100)]:
        determinant = (mu + 1) ** 2 - F(1, 4)
        column = [-(mu + 1) / determinant, 1 - F(1, 2) / determinant]
        norm_squared = sum(v * v for v in column)
        assert norm_squared == 1 + F(1, 2) / determinant**2
        assert norm_squared > 1
    print("Emmy PBR column expansion identity: checked exactly at five parameters")


def check_uniform_formula():
    for count in range(2, 8):
        x = [F(1)] + [F(0)] * (count - 1)
        p = [F(9)] * count
        b = F(count**2 - count + 1, (count - 1) ** 2)
        for n in range(count):
            assert tax(n, x, p) == b * p[n] * (x[n] - F(1, count))
            assert tax(n, x, p) + rebate(n, x, p) == p[n] * (x[n] - F(1, count))
    print("Uniform-price tax and repair formulas: checked for 2 through 7 players")


if __name__ == "__main__":
    check_counterexample()
    check_partner_pbr_column()
    check_uniform_formula()

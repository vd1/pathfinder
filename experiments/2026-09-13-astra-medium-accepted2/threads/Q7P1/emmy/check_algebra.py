"""Exact rational checks for the mechanism and PBR counterexamples."""

from fractions import Fraction as F


def tax(n, x, p, c=F(1), scale=F(1)):
    count = len(x)
    others = [j for j in range(count) if j != n]
    bp = sum(p[j] for j in others)
    bx = sum(x[j] for j in others)
    sp = sum(p[j] ** 2 for j in others)
    spx = sum(p[j] * x[j] for j in others)
    r = count - 1
    return scale * (
        p[n] * (p[n] - 2 * bp / r) / 2
        - p[n] * (x[n] + bx - c) / r
        + F(count, r**2) * bp * (x[n] - c / count)
        + sp / (2 * r)
        - (spx - bp * c / count) / r**2
    )


def correction(n, x, p, c=F(1), scale=F(1)):
    count = len(x)
    others = [j for j in range(count) if j != n]
    return scale * F(count, (count - 1) ** 3) * sum(
        p[j] for j in others
    ) * (sum(x[j] for j in others) - F(count - 1, count) * c)


def dot(a, b):
    return sum(v * w for v, w in zip(a, b))


def projected(v):
    avg = sum(v) / len(v)
    return [avg] * len(v), [w - avg for w in v]


def run():
    x, p = [F(1), F(0), F(0)], [F(9)] * 3
    payments = [tax(n, x, p) for n in range(3)]
    fixed = [payments[n] + correction(n, x, p) for n in range(3)]
    assert payments == [F(21, 2), F(-21, 4), F(-21, 4)]
    assert fixed == [F(6), F(-3), F(-3)]
    assert F(19, 2) - payments[0] == -1
    assert sum(payments) == sum(fixed) == 0
    print("IR counterexample: original taxes", payments, "corrected", fixed)

    for count in range(3, 21):
        r = count - 1
        kappa = F(2 * count - 1, r**2)
        assert 1 - kappa**2 / 4 > 0
        # Binding capacity and a common positive price.
        x = [F(j + 1, count * (count + 1) // 2) for j in range(count)]
        p = [F(7)] * count
        for n in range(count):
            assert tax(n, x, p) + correction(n, x, p) == 7 * (
                x[n] - F(1, count)
            )
        # The weighted operator identity uses arbitrary signed differences.
        dx = [F((-1) ** j * (j + 1), count) for j in range(count)]
        dp = [F((j * 3) % 7 - 2, count + 1) for j in range(count)]
        px, qx = projected(dx)
        pp, qp = projected(dp)
        gx = [dx[j] + pp[j] - kappa * qp[j] for j in range(count)]
        gp = [qp[j] - px[j] for j in range(count)]
        lhs = dot(dx, gx) + dot(dp, gp)
        rhs = dot(dx, dx) + dot(qp, qp) - kappa * dot(qx, qp)
        square = [qp[j] - kappa * qx[j] / 2 for j in range(count)]
        completed = dot(px, px) + (1 - kappa**2 / 4) * dot(qx, qx)
        completed += dot(square, square)
        assert lhs == rhs == completed
    print("Payment correction and weighted identity passed for N=3,...,20")

    for mu in [F(1, 10), F(1), F(3, 2), F(2), F(100)]:
        det = (mu + 1) ** 2 - F(1, 4)
        col = [-(mu + 1) / det, 1 - 1 / (2 * det)]
        # Directly multiply by the own proximal Hessian.
        assert (mu + 1) * col[0] - col[1] / 2 == F(-3, 2)
        assert -col[0] / 2 + (mu + 1) * col[1] == mu + 1
        assert dot(col, col) - 1 == 1 / (2 * det**2) > 0
    print("PBR price-column expansion identity passed for five positive mu values")


if __name__ == "__main__":
    run()

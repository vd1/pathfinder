"""Exact finite-instance checks for Q7-repair.tex; no campaign files modified."""

from fractions import Fraction as F
import json


def dot(a, b):
    return sum((x * y for x, y in zip(a, b)), F(0))


def tax_q(i, x, p, c=F(1), gamma=F(1)):
    n = len(x)
    k = n - 1
    others = [j for j in range(n) if j != i]
    ps = sum(p[j] for j in others)
    px = sum(p[j] * x[j] for j in others)
    pp = sum(p[j] ** 2 for j in others)
    return gamma * (
        p[i] ** 2 / 2 - p[i] * ps / k
        - p[i] * (sum(x) - c) / k
        + n * ps * (x[i] - c / n) / k**2
        + pp / (2 * k) - (px - ps * c / n) / k**2
    )


def correction(i, x, p, c=F(1), gamma=F(1)):
    n = len(x)
    others = [j for j in range(n) if j != i]
    return gamma * (
        c * sum(p[j] for j in others)
        - n * sum(p[j] * x[j] for j in others)
    ) / (n - 1)**2


def tax_r(i, x, p, c=F(1), gamma=F(1)):
    return tax_q(i, x, p, c, gamma) - correction(i, x, p, c, gamma)


def tax_hat_printed(i, x, p, c=F(1), gamma=F(1)):
    n = len(x)
    k = n - 1
    ps = sum(p[j] for j in range(n) if j != i)
    xs = sum(x[j] for j in range(n) if j != i)
    return gamma * (
        -p[i] * x[i] / k - p[i]**2 / 2
        - x[i] * ps / k + p[i] * n * xs / k**2
        - p[i] * ps / k + p[i] * c / k
    )


def derivative(fun, i, x, p, block):
    h = F(1, 100)
    xp, xm, pp, pm = x[:], x[:], p[:], p[:]
    if block == "x":
        xp[i] += h
        xm[i] -= h
    else:
        pp[i] += h
        pm[i] -= h
    return (fun(i, xp, pp) - fun(i, xm, pm)) / (2 * h)


def price_curvature(fun, i, x, p):
    h = F(1, 100)
    pp, pm = p[:], p[:]
    pp[i] += h
    pm[i] -= h
    return (fun(i, x, pp) - 2 * fun(i, x, p) + fun(i, x, pm)) / h**2


def check_counterexample():
    x = [F(1), F(0), F(0)]
    p = [F(9)] * 3
    values = [F(19, 2), F(0), F(0)]
    tq = [tax_q(i, x, p) for i in range(3)]
    tr = [tax_r(i, x, p) for i in range(3)]
    assert tq == [F(21, 2), F(-21, 4), F(-21, 4)]
    assert tr == [F(6), F(-3), F(-3)]
    assert sum(tq) == sum(tr) == 0
    assert values[0] - tq[0] == -1
    assert [values[i] - tr[i] for i in range(3)] == [F(7, 2), F(3), F(3)]
    # The own negative-utility Hessian [[1,-1/2],[-1/2,1]] is positive definite.
    assert F(1) > 0 and F(1) - F(1, 2)**2 > 0
    for price in [F(1, 10), F(1, 2), F(1), F(5), F(9)]:
        prices = [price] * 3
        marginals = [F(9), F(1, 10), F(1, 10)]
        for i in range(3):
            grad = derivative(tax_q, i, x, prices, "x") - marginals[i]
            assert (grad <= 0 if i == 0 else grad >= 0)
            assert derivative(tax_q, i, x, prices, "p") == 0
    assert price_curvature(tax_q, 0, x, p) == 1
    assert price_curvature(tax_hat_printed, 0, x, p) == -1
    return {
        "original_taxes": [str(t) for t in tq],
        "corrected_taxes": [str(t) for t in tr],
        "original_first_utility": "-1",
        "corrected_utilities": ["7/2", "3", "3"],
        "common_price_equilibrium_interval": "[1/10, 9]",
        "original_vs_printed_reduced_price_curvature": ["1", "-1"],
    }


def check_tax_identities():
    checks = 0
    for n in range(2, 13):
        k = n - 1
        x = [F(j + 1, n + 1) for j in range(n)]
        p = [F(2 * j + 1, n + 2) for j in range(n)]
        for i in range(n):
            gx = -p[i] / k + n * (sum(p) - p[i]) / k**2
            gp = (n * p[i] - sum(p) - sum(x) + 1) / k
            assert derivative(tax_q, i, x, p, "x") == gx
            assert derivative(tax_r, i, x, p, "x") == gx
            assert derivative(tax_q, i, x, p, "p") == gp
            assert derivative(tax_r, i, x, p, "p") == gp
            # Opponent-only correction cannot depend on either own coordinate.
            assert derivative(correction, i, x, p, "x") == 0
            assert derivative(correction, i, x, p, "p") == 0
            for price in [F(0), F(1, 3), F(9)]:
                common = [price] * n
                assert tax_r(i, x, common) == price * (x[i] - F(1, n))
                zero = x[:]
                zero[i] = F(0)
                assert tax_r(i, zero, common) == -price / n
                checks += 2
            # Expansion of the original payment's linear-price coefficients.
            a_self = F(1, k)
            a_other = -F(1, n * k)
            assert a_self + k * a_other == F(1, n * k) > 0
            checks += 7
    return checks


def project_disagreement(v):
    mean = sum(v) / len(v)
    return [x - mean for x in v]


def check_matrices():
    cases = 0
    for n in range(2, 13):
        k = n - 1
        gamma = F(1)
        m = F(3)
        weight = F(k, n)
        a = gamma * F(2 * n - 1, k**2)
        assert m > a**2 / (4 * gamma)
        assert m >= gamma / k**2
        # Jacobian of the negative-utility pseudogradient for quadratic costs.
        j = [[F(0) for _ in range(2 * n)] for _ in range(2 * n)]
        for i in range(n):
            j[i][i] = m
            for l in range(n):
                j[i][n + l] = gamma * F(n - (2 * n - 1) * (i == l), k**2)
                j[n + i][l] = -gamma / k
                j[n + i][n + l] = gamma * F(n * (i == l) - 1, k)
        common = [F(0)] * n + [F(1)] * n
        jc = [dot(row, common) for row in j]
        assert dot(common, jc) == 0
        assert jc[:n] == [gamma] * n  # Zero quadratic form is NOT a full null vector.
        assert jc[n:] == [F(0)] * n
        for offset in range(7):
            dx = [F((3 * i + offset) % 9 - 4, 7) for i in range(n)]
            dp = [F((5 * i + 2 * offset) % 11 - 5, 8) for i in range(n)]
            z = dx + dp
            jz = [dot(row, z) for row in j]
            gjz = jz[:n] + [weight * v for v in jz[n:]]
            px, pp = project_disagreement(dx), project_disagreement(dp)
            target = m * dot(dx, dx) + gamma * dot(pp, pp) - a * dot(px, pp)
            lower = (m - a**2 / (4 * gamma)) * dot(dx, dx)
            shifted = [p - a * x / (2 * gamma) for x, p in zip(px, pp)]
            lower += gamma * dot(shifted, shifted)
            assert dot(z, gjz) == target
            assert target >= lower >= 0
            cases += 1
    return cases


def expected_empirical_cvar(y):
    # Two independent samples, each taking xi=0 or xi=2 equiprobably.
    # At tail mass 1/2, the two-sample CVaR is their maximum.
    losses = [y**2, (y - 2)**2]
    return sum(max(a, b) for a in losses for b in losses) / 4


def inward_surrogate(x, eps=F(1, 10), delta=F(1, 20), kappa=F(1)):
    center = (1 - eps) * x + eps
    z = center - 1
    mean_abs = abs(z) if abs(z) >= delta else (z*z + delta*delta) / (2 * delta)
    return center**2 - 2*center + 2 + delta**2 / 3 + mean_abs + kappa*x*x / 2


def check_cvar_oracle():
    eps, delta, kappa = F(1, 10), F(1, 20), F(1)
    assert delta < eps  # Interior ball: center=1, radius=1 in [0,2].
    cases = 0
    for i in range(9):
        x = F(i, 4)
        center = (1 - eps) * x + eps
        lo, hi = center - delta, center + delta
        assert 0 <= lo <= hi <= 2
        for y in [lo, center, hi]:
            ec = expected_empirical_cvar(y)
            truth = max(y*y, (y - 2)**2)
            assert ec == y*y - 2*y + 2 + abs(y - 1)
            assert ec - truth == -abs(y - 1)
        expected_gradient = (1 - eps) * (
            expected_empirical_cvar(hi) - expected_empirical_cvar(lo)
        ) / (2 * delta) + kappa*x
        # The surrogate is quadratic on each region; these points and increments
        # remain in one region, making this central difference exact.
        h = F(1, 10000)
        derivative_exact = (inward_surrogate(x + h) - inward_surrogate(x - h)) / (2*h)
        assert expected_gradient == derivative_exact
        cases += 1
    return cases


if __name__ == "__main__":
    result = {
        "status": "PASS",
        "arithmetic": "exact rational arithmetic; no floating-point tolerances",
        "counterexample": check_counterexample(),
        "tax_identity_checks": check_tax_identities(),
        "monotonicity_instances": check_matrices(),
        "cvar_oracle_instances": check_cvar_oracle(),
        "scope": "Finite-instance checks support, but do not replace, the general proofs.",
    }
    print(json.dumps(result, indent=2))
